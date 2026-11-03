"""WCB-D-04: AG-UI events -> chat view (SPEC-WCB-AGU-002..007, USG-*).

Table-driven over scripted sequences (DELTA-2026-10 §6).
"""

from __future__ import annotations

from typing import Any

import pytest

from prismal_webchat.state.agui_mapper import apply_agui
from tests import scripts
from tests.scripts import ag
from tests.unit.view import View


def run(events: list[Any], *, show_usage: bool = False) -> tuple[View, list[bool]]:
    view = View()
    terminal = [apply_agui(view, e, show_usage=show_usage) for e in events]
    return view, terminal


def test_text_content_appends_like_tokens() -> None:
    view, terminal = run(scripts.agui_text("Hel", "lo", usage=None))
    assert view.last.text == "Hello"
    assert terminal[-1] is True and not any(terminal[:-1])


@pytest.mark.parametrize("end", ["TOOL_CALL_END", "TOOL_CALL_RESULT"])
def test_tool_chip_running_then_done_keyed_by_call_id(end: str) -> None:
    start, args, closing = scripts.tool_call("c1", "web_search", end=end)
    view, _ = run([start, args])
    assert [(t.id, t.name, t.done) for t in view.tools] == [("c1", "web_search", False)]
    apply_agui(view, closing, show_usage=False)
    assert [(t.id, t.done) for t in view.tools] == [("c1", True)]


def test_tool_args_and_results_never_rendered() -> None:
    view, _ = run(scripts.tool_call("c1", "web_search", end="TOOL_CALL_RESULT"))
    assert "secret" not in repr(view)


def test_parallel_tool_calls_tracked_independently() -> None:
    a = scripts.tool_call("c1", "web_search")
    b = scripts.tool_call("c2", "calculator")
    view, _ = run([a[0], b[0], b[2]])
    assert [(t.id, t.done) for t in view.tools] == [("c1", False), ("c2", True)]


def test_tool_chip_mid_text_keeps_text_order() -> None:
    text = scripts.text("Let me ", "check. ", "Done.")
    start, _, end = scripts.tool_call("c1", "web_search")
    events = [text[0], text[1], text[2], start, end, text[3], text[4]]
    view, _ = run(events)
    assert view.last.text == "Let me check. Done."


def test_subagent_line_shown_then_cleared_by_same_run_id() -> None:
    started, finished = scripts.subagent("s1", "researcher")
    view, _ = run([started])
    assert view.subagent == "researcher"
    apply_agui(view, finished, show_usage=False)
    assert view.subagent == ""


def test_nested_subagent_shows_one_line_and_ignores_foreign_finish() -> None:
    outer_start, outer_end = scripts.subagent("s1", "planner")
    inner_start, inner_end = scripts.subagent("s2", "researcher")
    view, _ = run([outer_start, inner_start])
    assert view.subagent == "researcher"  # at most one line: the latest
    apply_agui(view, outer_end, show_usage=False)  # not the visible one
    assert view.subagent == "researcher"
    apply_agui(view, inner_end, show_usage=False)
    assert view.subagent == ""


def test_subagent_without_name_falls_back() -> None:
    view, _ = run([ag("SUBAGENT_STARTED", subagentRunId="s1", name="")])
    assert view.subagent == "…"


@pytest.mark.parametrize(
    "event",
    [
        ag("SOMETHING_NEW", foo=1),
        ag("CUSTOM", name="vendor.thing", value={"x": 1}),
        ag("RUN_STARTED"),
        ag("TEXT_MESSAGE_START", messageId="m", role="assistant"),
        ag("TEXT_MESSAGE_END", messageId="m"),
        ag("TOOL_CALL_ARGS", toolCallId="c", delta="{}"),
        ag("STATE_SNAPSHOT", snapshot={"secret": 1}),
        ag("STATE_DELTA", delta=[{"op": "add", "path": "/x", "value": "secret"}]),
        ag("STEP_STARTED", stepName="s"),
    ],
)
def test_ignored_events_change_nothing(event: Any) -> None:
    view = View()
    before = repr(view)
    assert apply_agui(view, event, show_usage=False) is False
    assert repr(view) == before


def test_run_finished_clears_tools_and_subagent() -> None:
    start, *_ = scripts.tool_call("c1", "web_search")
    sub, _ = scripts.subagent("s1", "researcher")
    view, terminal = run([start, sub, scripts.run_finished()])
    assert terminal[-1] is True
    assert (view.tools, view.subagent) == ([], "")


def test_usage_event_hidden_by_default() -> None:
    view, _ = run(scripts.agui_text("x"))
    assert view.last.total_tokens is None
    assert "secret-model" not in repr(view)


def test_usage_event_shows_total_tokens_when_enabled() -> None:
    view, _ = run(scripts.agui_text("x"), show_usage=True)
    assert view.last.total_tokens == 150


def test_run_finished_without_usage_is_fail_open() -> None:
    view, terminal = run(scripts.agui_text("x", usage=None), show_usage=True)
    assert terminal[-1] is True
    assert view.last.total_tokens is None


def test_interrupted_run_finished_ends_turn_and_hides_interrupt_payload() -> None:
    """SDK 0.3 / host 0.3: an interrupted run is still terminal for the widget.

    The webchat has no resume UI (DELTA-2026-11-pypi §4): the turn ends with
    the text streamed so far, and interrupt ids/payloads never reach the view.
    """
    finished = scripts.ag(
        "RUN_FINISHED",
        outcome={
            "type": "interrupt",
            "interrupts": [{"id": "int-SENTINEL-1", "value": {"question": "approve?"}}],
        },
    )
    assert finished.is_interrupted  # type: ignore[attr-defined]
    view, terminal = run([*scripts.text("Partial."), finished])
    assert terminal[-1] is True
    assert view.last.text == "Partial."
    assert "int-SENTINEL-1" not in repr(view)
    assert "approve?" not in repr(view)
