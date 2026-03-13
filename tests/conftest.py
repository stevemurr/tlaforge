import os

import pytest

from tlaforge.llm import (
    LIVE_API_KEY_ENV,
    LIVE_BASE_URL_ENV,
    LIVE_MODEL_ENV,
    OpenAICompatibleStructuredClient,
)


LIVE_TRAFFIC_LIGHT_MESSAGES = (
    "Create a module named TrafficLight with states red, green, and yellow. Set the initial state to red.",
    "Add transitions red to green, green to yellow, and yellow to red.",
    "Add an invariant named ValidState using a binary in expression with left ref state and right ref States.",
)


def _live_env_missing() -> list[str]:
    return [
        name
        for name in (LIVE_BASE_URL_ENV, LIVE_MODEL_ENV, LIVE_API_KEY_ENV)
        if not os.environ.get(name)
    ]


@pytest.fixture
def live_client() -> OpenAICompatibleStructuredClient:
    missing = _live_env_missing()
    if missing:
        pytest.skip(f"live network test requires env vars: {', '.join(missing)}")
    return OpenAICompatibleStructuredClient.from_live_env(max_tokens=4096)


@pytest.fixture
def live_traffic_light_messages() -> tuple[str, str, str]:
    return LIVE_TRAFFIC_LIGHT_MESSAGES
