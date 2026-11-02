"""``FakeAsyncPrismalClient``: the offline unit-test seam (ADR-005).

Replays scripted turns. A script is a list whose items are either SDK event
models (yielded) or exception instances (raised in place, exactly where the
real client raises: before the first event for an HTTP/protocol refusal, or
mid-stream for a terminal ``error`` / ``RUN_ERROR`` / transport failure).
"""

from __future__ import annotations

import itertools
from collections import deque
from collections.abc import AsyncIterator, Sequence
from typing import Any

from prismal_sdk import ThreadCreated
from prismal_sdk.agui import StreamProtocol

ScriptItem = Any  # an SDK event model or a BaseException instance


class FakeAsyncPrismalClient:
    def __init__(self) -> None:
        self._turns: dict[str, deque[list[ScriptItem]]] = {
            "prismal": deque(),
            "ag-ui": deque(),
        }
        self._ids = itertools.count(1)
        self.threads_created = 0
        #: (thread_id, content, protocol) per send_message call, verbatim.
        self.sent: list[tuple[str, str, StreamProtocol]] = []
        self.streams_completed = 0
        self.streams_closed_early = 0
        self.closed = False

    # -- scripting -----------------------------------------------------------
    def queue_turn(
        self, script: Sequence[ScriptItem], protocol: StreamProtocol = "prismal"
    ) -> None:
        self._turns[protocol].append(list(script))

    # -- AsyncPrismalClient surface used by the webchat ------------------------
    async def create_thread(self) -> ThreadCreated:
        self.threads_created += 1
        return ThreadCreated(thread_id=f"thread-{next(self._ids)}")

    async def send_message(
        self,
        thread_id: str,
        content: str,
        *,
        protocol: StreamProtocol = "prismal",
        **_: Any,
    ) -> AsyncIterator[Any]:
        self.sent.append((thread_id, content, protocol))
        assert self._turns[protocol], f"no scripted {protocol} turn queued"
        script = self._turns[protocol].popleft()
        finished = False
        try:
            for item in script:
                if isinstance(item, BaseException):
                    finished = True  # an error ends the stream; not an early close
                    raise item
                yield item
            finished = True
            self.streams_completed += 1
        finally:
            if not finished:
                # GeneratorExit/CancelledError: the consumer stopped iterating,
                # which is the webchat's cancellation contract (SPEC-WCB-CHT-005).
                self.streams_closed_early += 1

    async def aclose(self) -> None:
        self.closed = True
