"""Classic SSE events -> chat view (SPEC-WCB-CHT-003).

Pure functions: one SDK event in, one view mutation out. Each returns
``True`` when the event closes the turn.
"""

from __future__ import annotations

import dataclasses
import logging
from typing import Any

from prismal_sdk import DoneEvent, TokenEvent, ToolCallEvent, Usage

from prismal_webchat.state.models import ChatView, ToolActivity

log = logging.getLogger(__name__)


def update_last(view: ChatView, **changes: Any) -> None:
    """Replace (not mutate) the live assistant message so Reflex sees the change."""
    view.messages[-1] = dataclasses.replace(view.messages[-1], **changes)


def append_text(view: ChatView, delta: str) -> None:
    update_last(view, text=view.messages[-1].text + delta)


def record_usage(view: ChatView, usage: Usage | None, *, show_usage: bool) -> None:
    # Default policy: nothing usage-related reaches state (SPEC-WCB-USG-001).
    if show_usage and usage is not None:
        update_last(view, total_tokens=usage.total_tokens)


def end_turn(view: ChatView) -> None:
    view.tools = []
    view.subagent = ""
    view.subagent_run_id = ""


def apply_classic(view: ChatView, event: Any, *, show_usage: bool) -> bool:
    if isinstance(event, TokenEvent):
        append_text(view, event.delta)
    elif isinstance(event, ToolCallEvent):
        view.tools = [ToolActivity(id="classic", name=event.name)]
    elif isinstance(event, DoneEvent):
        record_usage(view, event.usage, show_usage=show_usage)
        end_turn(view)
        return True
    else:  # StateEvent and anything newer: no visible change
        log.debug("ignored classic event %s", type(event).__name__)
    return False
