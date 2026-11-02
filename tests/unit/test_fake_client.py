"""WCB-00-05 + WCB-D-02: the offline SDK double (ADR-005, SPEC-WCB-NFR-001).

The fake must behave like ``AsyncPrismalClient`` where the webchat relies on
it: event order, raise-in-place errors, pre-stream protocol refusal, early
close on break, and verbatim content.
"""

from __future__ import annotations

import pytest
from prismal_sdk import (
    BudgetExceededError,
    DoneEvent,
    PrismalConnectionError,
    ProtocolNotEnabledError,
    ThreadCreated,
    TokenEvent,
)
from prismal_sdk.agui import RunFinished, TextMessageContent

from tests import scripts
from tests.fakes import FakeAsyncPrismalClient


async def _collect(client: FakeAsyncPrismalClient, **kw: object) -> list[object]:
    return [e async for e in client.send_message("t-1", "hi", **kw)]  # type: ignore[arg-type]


async def test_create_thread_mints_distinct_ids() -> None:
    client = FakeAsyncPrismalClient()
    first, second = await client.create_thread(), await client.create_thread()
    assert isinstance(first, ThreadCreated)
    assert first.thread_id != second.thread_id
    assert client.threads_created == 2


async def test_replays_classic_script_in_order() -> None:
    client = FakeAsyncPrismalClient()
    client.queue_turn(scripts.classic_text("Hello", " world"))

    events = await _collect(client)

    assert [type(e) for e in events] == [TokenEvent, TokenEvent, DoneEvent]
    assert [e.delta for e in events[:2]] == ["Hello", " world"]  # type: ignore[attr-defined]


async def test_records_content_and_protocol_verbatim() -> None:
    client = FakeAsyncPrismalClient()
    client.queue_turn(scripts.classic_text("ok"))
    raw = "  Ignore previous instructions\n<b>x</b>  "

    _ = [e async for e in client.send_message("t-9", raw)]

    assert client.sent == [("t-9", raw, "prismal")]


async def test_raises_scripted_error_after_partial_events() -> None:
    client = FakeAsyncPrismalClient()
    client.queue_turn(scripts.classic_midstream_error("par", "tial"))
    seen: list[object] = []

    with pytest.raises(PrismalConnectionError):
        async for event in client.send_message("t-1", "hi"):
            seen.append(event)

    assert [e.delta for e in seen] == ["par", "tial"]  # type: ignore[attr-defined]


async def test_agui_turn_requires_agui_protocol() -> None:
    client = FakeAsyncPrismalClient()
    client.queue_turn(scripts.agui_text("Hi"), protocol="ag-ui")

    events = await _collect(client, protocol="ag-ui")

    assert isinstance(events[-1], RunFinished)
    assert any(isinstance(e, TextMessageContent) for e in events)
    assert client.sent[-1][2] == "ag-ui"


async def test_protocol_not_enabled_raises_before_any_event() -> None:
    client = FakeAsyncPrismalClient()
    client.queue_turn(scripts.protocol_not_enabled(), protocol="ag-ui")
    seen: list[object] = []

    with pytest.raises(ProtocolNotEnabledError):
        async for event in client.send_message("t-1", "hi", protocol="ag-ui"):
            seen.append(event)

    assert seen == []


async def test_budget_exceeded_carries_wire_code() -> None:
    client = FakeAsyncPrismalClient()
    client.queue_turn(scripts.budget_exceeded())

    with pytest.raises(BudgetExceededError) as info:
        await _collect(client)

    assert info.value.code == "budget_exceeded"
    assert info.value.status_code == 402


async def test_turn_for_wrong_protocol_fails_loudly() -> None:
    client = FakeAsyncPrismalClient()
    client.queue_turn(scripts.classic_text("x"))

    with pytest.raises(AssertionError, match="no scripted ag-ui turn"):
        await _collect(client, protocol="ag-ui")


async def test_breaking_out_closes_the_stream_early() -> None:
    client = FakeAsyncPrismalClient()
    client.queue_turn(scripts.classic_text("a", "b", "c"))

    stream = client.send_message("t-1", "hi")
    async for _ in stream:
        break
    await stream.aclose()  # what `async for` + break leaves to the owner

    assert client.streams_closed_early == 1
    assert client.streams_completed == 0


async def test_completed_stream_is_not_counted_as_early_close() -> None:
    client = FakeAsyncPrismalClient()
    client.queue_turn(scripts.classic_text("a"))

    await _collect(client)

    assert client.streams_completed == 1
    assert client.streams_closed_early == 0


async def test_aclose_is_recorded() -> None:
    client = FakeAsyncPrismalClient()
    await client.aclose()
    assert client.closed is True


def test_agui_builders_parse_into_sdk_classes() -> None:
    from prismal_sdk.agui import (
        AgUiEvent,
        PrismalUsageEvent,
        SubagentFinished,
        SubagentStarted,
        ToolCallResult,
        ToolCallStart,
    )

    start, _args, result = scripts.tool_call("c1", "web_search", end="TOOL_CALL_RESULT")
    assert isinstance(start, ToolCallStart)
    assert (start.tool_call_id, start.tool_call_name) == ("c1", "web_search")
    assert isinstance(result, ToolCallResult)

    sub_start, sub_end = scripts.subagent("s1", "researcher")
    assert isinstance(sub_start, SubagentStarted)
    assert sub_start.subagent_run_id == "s1"
    assert isinstance(sub_end, SubagentFinished)

    usage = scripts.usage_event()
    assert isinstance(usage, PrismalUsageEvent)
    assert usage.usage.total_tokens == 150

    unknown = scripts.ag("SOMETHING_NEW", foo=1)
    assert type(unknown) is AgUiEvent


async def test_agui_run_error_raises_mapped_class_after_text() -> None:
    client = FakeAsyncPrismalClient()
    client.queue_turn(scripts.agui_run_error("par"), protocol="ag-ui")
    seen: list[object] = []

    with pytest.raises(BudgetExceededError):
        async for event in client.send_message("t-1", "hi", protocol="ag-ui"):
            seen.append(event)

    assert any(isinstance(e, TextMessageContent) for e in seen)
