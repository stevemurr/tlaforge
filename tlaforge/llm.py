"""Structured-output LLM clients for TLAForge sessions."""

from __future__ import annotations

import json
import os
from typing import Any, Protocol
import urllib.request

from .draft import AssistantTurn, ConversationMessage, MachineDraft
from .errors import StructuredOutputError

LIVE_BASE_URL_ENV = "TLAFORGE_LIVE_BASE_URL"
LIVE_MODEL_ENV = "TLAFORGE_LIVE_MODEL"
LIVE_API_KEY_ENV = "TLAFORGE_LIVE_API_KEY"
_LOCAL_PROVIDER_EXTRA_BODY = {"chat_template_kwargs": {"thinking": False}}


class StructuredTurnClient(Protocol):
    def complete_turn(
        self,
        *,
        draft: MachineDraft,
        transcript: list[ConversationMessage],
        user_message: str,
    ) -> AssistantTurn:
        """Return a validated assistant turn for the next session step."""


def _post_json(
    *,
    url: str,
    payload: dict[str, Any],
    headers: dict[str, str],
    timeout: int,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read())


def _normalize_openai_endpoint(url: str) -> str:
    normalized = url.rstrip("/")
    if normalized.endswith("/chat/completions"):
        return normalized
    if normalized.endswith("/v1"):
        return f"{normalized}/chat/completions"
    return f"{normalized}/v1/chat/completions"


def _extract_openai_text_content(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    text_parts.append(text)
        if text_parts:
            return "".join(text_parts)
    raise StructuredOutputError("response did not include assistant text content")


def _system_prompt() -> str:
    schema = json.dumps(AssistantTurn.model_json_schema(), indent=2, sort_keys=True)
    return (
        "You are TLAForge's structured state-machine assistant.\n"
        "Respond with JSON only that validates against the AssistantTurn schema below.\n"
        "Never emit Python or raw TLA+.\n"
        "Use patch.operations to update the draft deterministically.\n"
        "If information is missing, ask a direct follow-up question in reply and add a "
        "required open question operation instead of guessing.\n"
        "Supported expression kinds are ref, string, int, bool, binary, and, or, and not.\n"
        "Do not invent unsupported expression kinds or patch operations.\n\n"
        "AssistantTurn JSON Schema:\n"
        f"{schema}"
    )


class OpenAICompatibleStructuredClient:
    """Structured-output client for OpenAI-compatible chat completion APIs."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str = "https://api.openai.com",
        endpoint: str | None = None,
        extra_body: dict[str, Any] | None = None,
        timeout: int = 60,
        max_tokens: int = 1024,
        use_response_format: bool = False,
    ) -> None:
        self.model = model
        self.api_key = (
            api_key
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("TLAFORGE_OPENAI_API_KEY")
        )
        self.endpoint = _normalize_openai_endpoint(endpoint or base_url)
        self.extra_body = {"temperature": 0, **(extra_body or {})}
        self.timeout = timeout
        self.max_tokens = max_tokens
        self.use_response_format = use_response_format

    @classmethod
    def local(
        cls,
        *,
        model: str,
        api_key: str,
        base_url: str,
        timeout: int = 60,
        max_tokens: int = 1024,
    ) -> OpenAICompatibleStructuredClient:
        """Construct a strict local-provider client with known-good defaults."""
        return cls(
            model=model,
            api_key=api_key,
            base_url=base_url,
            extra_body=_LOCAL_PROVIDER_EXTRA_BODY,
            timeout=timeout,
            max_tokens=max_tokens,
            use_response_format=True,
        )

    @classmethod
    def from_live_env(
        cls,
        *,
        timeout: int = 60,
        max_tokens: int = 1024,
    ) -> OpenAICompatibleStructuredClient:
        """Construct a strict local-provider client from TLAFORGE_LIVE_* env vars."""
        missing = [
            name
            for name in (LIVE_BASE_URL_ENV, LIVE_MODEL_ENV, LIVE_API_KEY_ENV)
            if not os.environ.get(name)
        ]
        if missing:
            missing_list = ", ".join(missing)
            raise RuntimeError(
                f"Set {missing_list} before using the local TLAForge live client."
            )
        return cls.local(
            model=os.environ[LIVE_MODEL_ENV],
            api_key=os.environ[LIVE_API_KEY_ENV],
            base_url=os.environ[LIVE_BASE_URL_ENV],
            timeout=timeout,
            max_tokens=max_tokens,
        )

    def complete_turn(
        self,
        *,
        draft: MachineDraft,
        transcript: list[ConversationMessage],
        user_message: str,
    ) -> AssistantTurn:
        if not self.api_key:
            raise RuntimeError(
                "Set OPENAI_API_KEY or TLAFORGE_OPENAI_API_KEY before using the "
                "OpenAI-compatible TLAForge client."
            )

        messages = [
            {"role": "system", "content": _system_prompt()},
            *[
                {"role": message.role, "content": message.content}
                for message in transcript
            ],
            {
                "role": "user",
                "content": (
                    "Current draft JSON:\n"
                    f"{draft.model_dump_json(indent=2)}\n\n"
                    "Latest user request:\n"
                    f"{user_message}"
                ),
            },
        ]
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            **self.extra_body,
        }
        if self.use_response_format:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "assistant_turn",
                    "strict": True,
                    "schema": AssistantTurn.model_json_schema(),
                },
            }

        response = _post_json(
            url=self.endpoint,
            payload=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            timeout=self.timeout,
        )

        try:
            message = response["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise StructuredOutputError("response did not include a usable choice") from exc

        content = _extract_openai_text_content(message)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise StructuredOutputError("response was not valid JSON") from exc
        try:
            return AssistantTurn.model_validate(parsed)
        except Exception as exc:  # pragma: no cover - exact message depends on pydantic internals
            raise StructuredOutputError("response JSON did not match AssistantTurn schema") from exc
