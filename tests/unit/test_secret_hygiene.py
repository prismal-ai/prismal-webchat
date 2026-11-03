"""WCB-04-01 (offline part): nothing secret or usage-related leaves the backend.

SPEC-WCB-AUT-002 (token never in state/logs), SPEC-WCB-USG-001 (no usage in
state by default), SPEC-WCB-NFR-003 (logs carry no message content).
The compiled-frontend scan is the opt-in ``compile`` suite.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import pytest
from pydantic import SecretStr
from reflex_base.utils.format import json_dumps

from prismal_webchat import client as client_mod
from prismal_webchat.settings import WebchatSettings
from prismal_webchat.state import chat as chat_mod
from prismal_webchat.state.chat import ChatState
from tests import scripts
from tests.conftest import TEST_TOKEN
from tests.fakes import FakeAsyncPrismalClient

QUESTION = "my private question about salary 98765"
USAGE_LEAKS = (
    "cost_usd",
    "cost_source",
    "served_model",
    "gateway",
    "prompt_tokens",
    "completion_tokens",
    "cache_read_tokens",
    "secret-model-x",
    "secret-gateway-y",
    "0.0123",
)


@pytest.fixture
def wire(
    monkeypatch: pytest.MonkeyPatch, fake_client: FakeAsyncPrismalClient
) -> Iterator[dict[str, Any]]:
    cfg: dict[str, Any] = {
        "settings": WebchatSettings(token=SecretStr(TEST_TOKEN), org_id="acme-org")
    }
    monkeypatch.setattr(chat_mod, "get_client", lambda: fake_client)
    monkeypatch.setattr(chat_mod, "get_settings", lambda: cfg["settings"])
    client_mod.reset_client_for_tests()
    yield cfg
    client_mod.reset_client_for_tests()


async def _turn(state: ChatState, text: str) -> None:
    state.set_input_text(text)
    for _ in ChatState.send.fn(state):
        pass
    await ChatState.stream_turn.fn(state)


def _serialized(state: ChatState) -> str:
    """What Reflex would ship to the browser for this state (its own serializer)."""
    return json_dumps(state.dict(), separators=(",", ":"))


async def _run_usage_turns(
    wire: dict[str, Any], fake_client: FakeAsyncPrismalClient, *, show_usage: bool
) -> tuple[ChatState, ChatState]:
    """One classic and one AG-UI turn, both carrying the full usage payload."""
    base = wire["settings"]
    wire["settings"] = base.model_copy(update={"show_usage": show_usage})
    classic = ChatState()
    fake_client.queue_turn(scripts.classic_text("hi", usage=scripts.USAGE))
    await _turn(classic, "q")

    wire["settings"] = base.model_copy(update={"show_usage": show_usage, "agui_enabled": True})
    agui = ChatState()
    fake_client.queue_turn(scripts.agui_text("hi"), protocol="ag-ui")
    await _turn(agui, "q")
    return classic, agui


async def test_no_usage_in_state_by_default(
    wire: dict[str, Any], fake_client: FakeAsyncPrismalClient
) -> None:
    states = await _run_usage_turns(wire, fake_client, show_usage=False)
    for state in states:
        payload = _serialized(state)
        for leak in (*USAGE_LEAKS, '"total_tokens":150'):
            assert leak not in payload, leak


async def test_opt_in_usage_exposes_total_tokens_only(
    wire: dict[str, Any], fake_client: FakeAsyncPrismalClient
) -> None:
    states = await _run_usage_turns(wire, fake_client, show_usage=True)
    for state in states:
        payload = _serialized(state)
        assert '"total_tokens":150' in payload
        for leak in USAGE_LEAKS:
            assert leak not in payload, leak


async def test_state_never_carries_token_settings_or_backend_vars(
    wire: dict[str, Any], fake_client: FakeAsyncPrismalClient
) -> None:
    state = ChatState()
    fake_client.queue_turn(scripts.classic_midstream_error("x"))
    await _turn(state, QUESTION)
    payload = _serialized(state)
    for leak in (TEST_TOKEN, "acme-org", "localhost:8000", "_pending_content", "_stop_requested"):
        assert leak not in payload, leak


async def test_logs_carry_no_content_token_or_server_message(
    wire: dict[str, Any], fake_client: FakeAsyncPrismalClient, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    state = ChatState()
    fake_client.queue_turn(scripts.classic_text("the answer text", usage=scripts.USAGE))
    fake_client.queue_turn(scripts.budget_exceeded("partial answer"))
    await _turn(state, QUESTION)
    await _turn(state, QUESTION)

    logged = "\n".join(r.getMessage() for r in caplog.records)
    assert "budget_exceeded" in logged  # mapped codes are fine (NFR-003)
    assert "thread-1" in logged
    for leak in (QUESTION, "the answer text", "partial answer", TEST_TOKEN, "tenant acme exceeded"):
        assert leak not in logged, leak
