"""AG-UI events -> chat view (WCB-D-04, SPEC-WCB-AGU-002..007).

Dispatches on the SDK's classes only, so wire-name changes stay in the SDK.
Tool arguments/results and agent state are never rendered.
"""

from __future__ import annotations

import logging
from typing import Any

from prismal_sdk.agui import (
    PrismalUsageEvent,
    RunFinished,
    SubagentFinished,
    SubagentStarted,
    TextMessageContent,
    ToolCallEnd,
    ToolCallResult,
    ToolCallStart,
)

from prismal_webchat.state.mapping import append_text, end_turn, record_usage
from prismal_webchat.state.models import ChatView, ToolActivity

log = logging.getLogger(__name__)

SUBAGENT_FALLBACK = "…"


def _mark_tool_done(view: ChatView, call_id: str) -> None:
    view.tools = [
        ToolActivity(id=t.id, name=t.name, done=True) if t.id == call_id else t for t in view.tools
    ]


def apply_agui(view: ChatView, event: Any, *, show_usage: bool) -> bool:
    if isinstance(event, TextMessageContent):
        append_text(view, event.delta)
    elif isinstance(event, ToolCallStart):
        view.tools = [*view.tools, ToolActivity(id=event.tool_call_id, name=event.tool_call_name)]
    elif isinstance(event, ToolCallEnd | ToolCallResult):
        _mark_tool_done(view, event.tool_call_id)
    elif isinstance(event, SubagentStarted):
        view.subagent = event.name or SUBAGENT_FALLBACK
        view.subagent_run_id = event.subagent_run_id
    elif isinstance(event, SubagentFinished):
        if event.subagent_run_id == view.subagent_run_id:
            view.subagent = ""
            view.subagent_run_id = ""
    elif isinstance(event, PrismalUsageEvent):
        record_usage(view, event.usage, show_usage=show_usage)
    elif isinstance(event, RunFinished):
        end_turn(view)
        return True
    else:  # SPEC-WCB-AGU-005/007: no visible change, type only at debug
        log.debug("ignored AG-UI event %s", getattr(event, "type", type(event).__name__))
    return False
