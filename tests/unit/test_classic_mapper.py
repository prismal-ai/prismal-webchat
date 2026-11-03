"""Classic SSE events -> chat view (SPEC-WCB-CHT-003, USG-001..003)."""

from __future__ import annotations

from prismal_sdk import StateEvent, TokenEvent, ToolCallEvent

from prismal_webchat.state.mapping import apply_classic
from tests import scripts
from tests.unit.view import View


def test_tokens_append_to_live_assistant_message() -> None:
    view = View()
    for event in scripts.classic_text("Hel", "lo")[:-1]:
        assert apply_classic(view, event, show_usage=False) is False
    assert view.last.text == "Hello"


def test_tool_call_sets_single_indicator() -> None:
    view = View()
    apply_classic(view, ToolCallEvent(name="web_search"), show_usage=False)
    apply_classic(view, ToolCallEvent(name="calculator"), show_usage=False)
    assert [(t.name, t.done) for t in view.tools] == [("calculator", False)]


def test_done_is_terminal_and_clears_indicator() -> None:
    view = View()
    apply_classic(view, ToolCallEvent(name="web_search"), show_usage=False)
    assert apply_classic(view, scripts.done(), show_usage=False) is True
    assert view.tools == []


def test_state_event_changes_nothing() -> None:
    view = View()
    before = repr(view)
    assert apply_classic(view, StateEvent(data={"node": "x"}), show_usage=False) is False
    assert repr(view) == before


def test_usage_hidden_by_default() -> None:
    view = View()
    apply_classic(view, scripts.done(scripts.USAGE), show_usage=False)
    assert view.last.total_tokens is None


def test_usage_footer_shows_total_tokens_only_when_enabled() -> None:
    view = View()
    apply_classic(view, scripts.done(scripts.USAGE), show_usage=True)
    assert view.last.total_tokens == 150


def test_missing_usage_is_fail_open() -> None:
    view = View()
    assert apply_classic(view, scripts.done(None), show_usage=True) is True
    assert view.last.total_tokens is None


def test_token_after_tool_keeps_text_order() -> None:
    view = View()
    for event in [TokenEvent(delta="A"), ToolCallEvent(name="t"), TokenEvent(delta="B")]:
        apply_classic(view, event, show_usage=False)
    assert view.last.text == "AB"
