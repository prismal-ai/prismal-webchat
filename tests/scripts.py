"""Scripted turns for ``FakeAsyncPrismalClient`` (WCB-00-05, WCB-D-02).

AG-UI events are built from wire-shaped (camelCase) dicts through the SDK's
own ``parse_agui_event``; errors through the SDK's ``error_for_code`` — so the
fake exercises the same models and the same code→class mapping as the real
client.
"""

from __future__ import annotations

from typing import Any

from prismal_sdk import DoneEvent, PrismalConnectionError, TokenEvent, ToolCallEvent, Usage
from prismal_sdk.agui import AgUiEvent, parse_agui_event
from prismal_sdk.exceptions import PrismalAPIError, error_for_code

THREAD = "thread-1"
RUN = "run-1"
MSG = "msg-1"

# A full 12-key usage with values that must never reach a visitor (USG-001).
USAGE = Usage(
    prompt_tokens=120,
    completion_tokens=30,
    cache_read_tokens=40,
    total_tokens=150,
    calls=1,
    cost_usd=0.0123,
    cost_source="gateway",
    estimated=False,
    served_model="secret-model-x",
    gateway="secret-gateway-y",
)


# ── Classic (protocol="prismal") ───────────────────────────────────────────


def done(usage: Usage | None = None) -> DoneEvent:
    return DoneEvent(thread_id=THREAD, finish_reason="stop", usage=usage)


def classic_text(*deltas: str, usage: Usage | None = None) -> list[Any]:
    return [*(TokenEvent(delta=d) for d in deltas), done(usage)]


def classic_tool(name: str, *deltas: str) -> list[Any]:
    return [
        ToolCallEvent(name=name, args={"q": "x"}),
        *(TokenEvent(delta=d) for d in deltas),
        done(),
    ]


def classic_midstream_error(*deltas: str, error: BaseException | None = None) -> list[Any]:
    return [
        *(TokenEvent(delta=d) for d in deltas),
        error or PrismalConnectionError("connection reset by peer"),
    ]


# ── Errors (pinned per WCB-D-01: RH2 §11 / CS2 §7) ───────────────────────────


def api_error(
    status: int, code: str, message: str = "server detail", **details: Any
) -> PrismalAPIError:
    return error_for_code(status, code, message, details)


def budget_exceeded(*deltas: str) -> list[Any]:
    """402 before the turn (no deltas) or a terminal stream error mid-turn."""
    err = api_error(
        402,
        "budget_exceeded",
        "tenant acme exceeded cost budget",
        scope="tenant",
        limit=5.0,
        consumed=5.2,
    )
    return [*(TokenEvent(delta=d) for d in deltas), err]


def protocol_not_enabled() -> list[Any]:
    return [api_error(406, "protocol_not_enabled", "AG-UI disabled for tenant")]


# ── AG-UI (protocol="ag-ui") ──────────────────────────────────────────────────


def ag(type_: str, **fields: Any) -> AgUiEvent:
    return parse_agui_event({"type": type_, "threadId": THREAD, "runId": RUN, **fields})


def run_started() -> AgUiEvent:
    return ag("RUN_STARTED")


def run_finished() -> AgUiEvent:
    return ag("RUN_FINISHED")


def usage_event(usage: Usage = USAGE) -> AgUiEvent:
    return ag("CUSTOM", name="prismal.usage", value=usage.model_dump())


def text(*deltas: str, message_id: str = MSG) -> list[AgUiEvent]:
    return [
        ag("TEXT_MESSAGE_START", messageId=message_id, role="assistant"),
        *(ag("TEXT_MESSAGE_CONTENT", messageId=message_id, delta=d) for d in deltas),
        ag("TEXT_MESSAGE_END", messageId=message_id),
    ]


def tool_call(call_id: str, name: str, *, end: str = "TOOL_CALL_END") -> list[AgUiEvent]:
    closing = (
        ag("TOOL_CALL_RESULT", toolCallId=call_id, content={"secret": "tool output"})
        if end == "TOOL_CALL_RESULT"
        else ag("TOOL_CALL_END", toolCallId=call_id)
    )
    return [
        ag("TOOL_CALL_START", toolCallId=call_id, toolCallName=name),
        ag("TOOL_CALL_ARGS", toolCallId=call_id, delta='{"q": "secret args"}'),
        closing,
    ]


def subagent(run_id: str, name: str, *inner: AgUiEvent) -> list[AgUiEvent]:
    return [
        ag("SUBAGENT_STARTED", subagentRunId=run_id, name=name),
        *inner,
        ag("SUBAGENT_FINISHED", subagentRunId=run_id),
    ]


def agui_text(*deltas: str, usage: Usage | None = USAGE) -> list[Any]:
    tail = [usage_event(usage)] if usage is not None else []
    return [run_started(), *text(*deltas), *tail, run_finished()]


def agui_run_error(*deltas: str, code: str = "budget_exceeded") -> list[Any]:
    """RUN_ERROR is raised by the SDK as the mapped exception (SPEC-CS2-AGU-003)."""
    return [run_started(), *text(*deltas)[:-1], api_error(200, code, "run failed")]
