"""WCB-04-02 + WCB-D-09: ChatState against a live prismal-server (opt-in).

    PRISMAL_SERVER_HOST_FAKE_LLM_MODE=true PRISMAL_AGUI_EVENTS_ENABLED=true \\
        uvicorn prismal_server.app:app            # in prismal-server
    uv run pytest -m contract                     # here

Targets ``PRISMAL_WEBCHAT_CONTRACT_URL`` (default http://localhost:8000).
Uses the real ``AsyncPrismalClient``; the server's fake-LLM script echoes
content in <=16-char token chunks, ``/tool <q>`` emits one tool call and
``/error`` ends with a terminal ``internal_error``. The budget refusal stays
fake-client only (DELTA-2026-10 WCB-D-09).
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Iterator
from typing import Any

import pytest
from prismal_sdk import AsyncPrismalClient, TokenEvent, ToolCallEvent
from prismal_sdk.agui import PrismalUsageEvent, TextMessageContent, ToolCallStart

from prismal_webchat import client as client_mod
from prismal_webchat.errors import GENERIC_TEXT
from prismal_webchat.settings import WebchatSettings
from prismal_webchat.state import chat as chat_mod
from prismal_webchat.state.chat import ChatState

pytestmark = pytest.mark.contract

BASE_URL = os.environ.get("PRISMAL_WEBCHAT_CONTRACT_URL", "http://localhost:8000")


class RecordingClient:
    """Real client; remembers every event and the tool chips seen mid-turn."""

    def __init__(self, inner: AsyncPrismalClient, state: ChatState) -> None:
        self.inner, self.state = inner, state
        self.events: list[Any] = []
        self.protocols: list[str] = []
        self.chips_seen: list[tuple[str, bool]] = []

    async def create_thread(self) -> Any:
        return await self.inner.create_thread()

    async def send_message(self, thread_id: str, content: str, **kw: Any) -> AsyncIterator[Any]:
        self.protocols.append(kw.get("protocol", "prismal"))
        async for event in self.inner.send_message(thread_id, content, **kw):
            self.events.append(event)
            yield event
            # Runs after ChatState applied the previous event.
            self.chips_seen += [(t.name, t.done) for t in self.state.tools]


@pytest.fixture
async def live() -> AsyncIterator[AsyncPrismalClient]:
    client = AsyncPrismalClient(BASE_URL)
    try:
        await client.healthz()
    except Exception as exc:  # pragma: no cover - environment guard
        pytest.fail(f"no prismal-server at {BASE_URL}: {exc!r}")
    yield client
    await client.aclose()


@pytest.fixture
def make(monkeypatch: pytest.MonkeyPatch, live: AsyncPrismalClient) -> Iterator[Any]:
    client_mod.reset_client_for_tests()

    def build(**settings: Any) -> tuple[ChatState, RecordingClient]:
        state = ChatState()
        rec = RecordingClient(live, state)
        monkeypatch.setattr(chat_mod, "get_client", lambda: rec)
        monkeypatch.setattr(chat_mod, "get_settings", lambda: WebchatSettings(**settings))
        return state, rec

    yield build
    client_mod.reset_client_for_tests()


async def turn(state: ChatState, text: str) -> None:
    state.set_input_text(text)
    for _ in ChatState.send.fn(state):
        pass
    await ChatState.stream_turn.fn(state)


# ── classic ─────────────────────────────────────────────────────────────────


async def test_classic_turn_streams_in_chunks(make: Any) -> None:
    state, rec = make()
    text = "hello from the webchat contract suite"

    await turn(state, text)

    assert state.messages[-1].text == f"echo: {text}"
    assert sum(isinstance(e, TokenEvent) for e in rec.events) >= 2
    assert state.streaming is False and state.thread_id


async def test_thread_is_reused_across_turns(make: Any) -> None:
    state, _ = make()
    await turn(state, "first")
    thread = state.thread_id
    await turn(state, "second")
    assert state.thread_id == thread
    assert [m.text for m in state.messages if m.role == "assistant"] == [
        "echo: first",
        "echo: second",
    ]


async def test_tool_call_shows_chip_then_clears(make: Any) -> None:
    state, rec = make()
    await turn(state, "/tool weather caracas")
    assert any(isinstance(e, ToolCallEvent) for e in rec.events)
    assert ("fake_tool", False) in rec.chips_seen
    assert state.tools == []


async def test_terminal_error_renders_friendly_retryable_bubble(make: Any) -> None:
    state, _ = make()
    await turn(state, "/error")
    last = state.messages[-1]
    assert (last.kind, last.error_text, last.retryable) == ("error", GENERIC_TEXT, True)
    assert "fake error" not in repr(state.messages)
    assert state.streaming is False


# ── AG-UI (needs PRISMAL_AGUI_EVENTS_ENABLED=true on the server) ─────────────


async def test_agui_turn_streams_text_and_usage_without_showing_it(make: Any) -> None:
    state, rec = make(agui_enabled=True)
    await turn(state, "hello agui")

    assert rec.protocols == ["ag-ui"], "server fell back: is AG-UI enabled there?"
    assert any(isinstance(e, TextMessageContent) for e in rec.events)
    assert any(isinstance(e, PrismalUsageEvent) for e in rec.events)
    assert state.messages[-1].text == "echo: hello agui"
    assert state.messages[-1].total_tokens is None  # show_usage off


async def test_agui_tool_chip_keyed_by_call_id(make: Any) -> None:
    state, rec = make(agui_enabled=True)
    await turn(state, "/tool docs")
    starts = [e for e in rec.events if isinstance(e, ToolCallStart)]
    assert starts and starts[0].tool_call_name == "fake_tool"
    assert ("fake_tool", False) in rec.chips_seen
    assert state.tools == []


async def test_agui_opt_in_usage_footer(make: Any) -> None:
    state, _ = make(agui_enabled=True, show_usage=True)
    await turn(state, "count me")
    assert state.messages[-1].total_tokens == 15
