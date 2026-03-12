import json

import pytest

from tlaforge.agent import AnthropicTextGenerationClient, TLAForgeAgent


VALID_SPEC_CODE = """spec = StateMachineSpec(
    module_name="Example",
    states=["idle"],
    initial_state="idle",
)"""


class RecordingClient:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def complete(self, *, system_prompt, history, user_message, model, max_tokens):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "history": list(history),
                "user_message": user_message,
                "model": model,
                "max_tokens": max_tokens,
            }
        )
        if not self.responses:
            raise AssertionError("No mock response configured")
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


class FakeHTTPResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_anthropic_client_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = AnthropicTextGenerationClient(api_key=None)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        client.complete(
            system_prompt="system",
            history=[],
            user_message="describe a system",
            model="claude-test",
            max_tokens=128,
        )


def test_anthropic_client_builds_request_and_parses_response(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return FakeHTTPResponse({"content": [{"text": "```python\nspec = 1\n```"}]})

    monkeypatch.setattr("tlaforge.agent.urllib.request.urlopen", fake_urlopen)

    client = AnthropicTextGenerationClient(api_key="secret-key")
    response = client.complete(
        system_prompt="system prompt",
        history=[{"role": "assistant", "content": "previous"}],
        user_message="describe a workflow",
        model="claude-test",
        max_tokens=256,
    )

    request = captured["request"]
    body = json.loads(request.data.decode("utf-8"))

    assert response == "```python\nspec = 1\n```"
    assert captured["timeout"] == 60
    assert request.full_url == "https://api.anthropic.com/v1/messages"
    assert any(
        header.lower() == "x-api-key" and value == "secret-key"
        for header, value in request.header_items()
    )
    assert body["system"] == "system prompt"
    assert body["messages"][-1]["content"] == "describe a workflow"
    assert body["model"] == "claude-test"
    assert body["max_tokens"] == 256


def test_extract_code_handles_fenced_and_unfenced_responses() -> None:
    agent = TLAForgeAgent(client=RecordingClient())

    assert agent._extract_code("```python\nspec = 1\n```") == "spec = 1\n"
    assert agent._extract_code("spec = 2") == "spec = 2"


def test_exec_code_returns_spec_and_requires_spec_assignment() -> None:
    agent = TLAForgeAgent(client=RecordingClient())

    spec = agent._exec_code(VALID_SPEC_CODE)

    assert spec.module_name == "Example"

    with pytest.raises(ValueError, match="spec"):
        agent._exec_code("x = 1")


def test_generate_succeeds_on_first_try() -> None:
    client = RecordingClient(VALID_SPEC_CODE)
    agent = TLAForgeAgent(client=client, model="mock-model", max_tokens=123)

    tla, code = agent.generate("A simple idle system")

    assert "MODULE Example" in tla
    assert code == VALID_SPEC_CODE
    assert len(agent.history) == 2
    assert client.calls[0]["user_message"].startswith("Generate a TLA+ spec")
    assert client.calls[0]["model"] == "mock-model"
    assert client.calls[0]["max_tokens"] == 123


def test_generate_retries_after_execution_error() -> None:
    client = RecordingClient("x = 1", VALID_SPEC_CODE)
    agent = TLAForgeAgent(client=client)

    tla, _ = agent.generate("Retry until the code is valid")

    assert "MODULE Example" in tla
    assert len(client.calls) == 2
    assert "LLM code did not assign a `spec` variable" in client.calls[1]["user_message"]


def test_generate_raises_after_exhausting_retries() -> None:
    client = RecordingClient("x = 1", "y = 2")
    agent = TLAForgeAgent(client=client)

    with pytest.raises(RuntimeError, match="Failed after 2 attempts"):
        agent.generate("This never succeeds", max_retries=2)

    assert len(client.calls) == 2


def test_refine_reuses_prior_history() -> None:
    client = RecordingClient(VALID_SPEC_CODE, VALID_SPEC_CODE.replace("Example", "Refined"))
    agent = TLAForgeAgent(client=client)

    first_tla, _ = agent.generate("Initial description")
    refined_tla, refined_code = agent.refine("Rename the module")

    assert "MODULE Example" in first_tla
    assert "MODULE Refined" in refined_tla
    assert "Refined" in refined_code
    assert client.calls[0]["history"] == []
    assert len(client.calls[1]["history"]) == 2
    assert client.calls[1]["history"][0]["role"] == "user"
    assert "Initial description" in client.calls[1]["history"][0]["content"]


def test_default_agent_fails_without_api_key(monkeypatch) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = TLAForgeAgent()

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        agent.generate("A system with no key available", max_retries=1)
