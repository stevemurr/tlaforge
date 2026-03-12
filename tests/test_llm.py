import json

import pytest

from tlaforge.draft import ConversationMessage, MachineDraft, StateDraft
from tlaforge.errors import StructuredOutputError
from tlaforge.llm import OpenAICompatibleStructuredClient


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_openai_structured_client_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TLAFORGE_OPENAI_API_KEY", raising=False)
    client = OpenAICompatibleStructuredClient(model="test-model", api_key=None)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        client.complete_turn(draft=MachineDraft(), transcript=[], user_message="hi")


def test_openai_structured_client_builds_request_and_parses_turn(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": json.dumps(
                                {
                                    "reply": "I added the initial state.",
                                    "patch": {
                                        "operations": [
                                            {
                                                "op": "set_module_name",
                                                "module_name": "TrafficLight",
                                            }
                                        ]
                                    },
                                }
                            ),
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("tlaforge.llm.urllib.request.urlopen", fake_urlopen)

    client = OpenAICompatibleStructuredClient(
        model="test-model",
        api_key="secret-key",
        base_url="http://example.test:4000",
    )
    turn = client.complete_turn(
        draft=MachineDraft(states=[StateDraft(name="red")]),
        transcript=[ConversationMessage(role="assistant", content="What states do you need?")],
        user_message="Let's start with red, yellow, and green.",
    )

    request = captured["request"]
    body = json.loads(request.data.decode("utf-8"))

    assert captured["timeout"] == 60
    assert request.full_url == "http://example.test:4000/v1/chat/completions"
    assert any(
        header.lower() == "authorization" and value == "Bearer secret-key"
        for header, value in request.header_items()
    )
    assert body["model"] == "test-model"
    assert body["temperature"] == 0
    assert "Current draft JSON:" in body["messages"][-1]["content"]
    assert turn.reply == "I added the initial state."
    assert turn.patch.operations[0].op == "set_module_name"


def test_openai_structured_client_rejects_non_json_content(monkeypatch) -> None:
    def fake_urlopen(request, timeout):
        return FakeHTTPResponse(
            {
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "not json",
                        }
                    }
                ]
            }
        )

    monkeypatch.setattr("tlaforge.llm.urllib.request.urlopen", fake_urlopen)

    client = OpenAICompatibleStructuredClient(
        model="test-model",
        api_key="secret-key",
        base_url="http://example.test:4000",
    )

    with pytest.raises(StructuredOutputError, match="valid JSON"):
        client.complete_turn(draft=MachineDraft(), transcript=[], user_message="hi")
