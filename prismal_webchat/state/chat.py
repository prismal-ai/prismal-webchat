"""Per-tab chat state: the whole turn lifecycle (ARCHITECTURE §4.1/§4.2).

``send`` is a regular event: it shows the visitor's message and clears the
input before any network call (SPEC-WCB-CHT-001), then chains
``stream_turn``, a *background* event so that ``stop_streaming`` can run
while a turn is in flight (Reflex serializes regular events per tab).

``stream_turn`` applies each SDK event inside its own ``async with self``
block, so every event is pushed to the browser as it arrives
(SPEC-WCB-CHT-003). Stop cancels the task; the cancellation unwinds the SDK
iterator, which closes the HTTP stream so the host cancels the run
(SPEC-WCB-CHT-005) — no cancel RPC exists or is invented.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import uuid
from collections.abc import AsyncGenerator, Callable
from typing import Any

import reflex as rx
from prismal_sdk import PrismalSDKError, ProtocolNotEnabledError
from prismal_sdk.agui import StreamProtocol

from prismal_webchat.client import agui_available, disable_agui, get_client
from prismal_webchat.errors import error_code, friendly_error
from prismal_webchat.settings import get_settings
from prismal_webchat.state.agui_mapper import apply_agui
from prismal_webchat.state.mapping import apply_classic, end_turn, update_last
from prismal_webchat.state.models import ChatMessage, ToolActivity

log = logging.getLogger(__name__)

Mapper = Callable[..., bool]

#: In-flight turn per tab (client token) so Stop can cancel it promptly,
#: even while the host is silent (heartbeats never reach the iterator).
_inflight: dict[str, asyncio.Task[Any]] = {}


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class ChatState(rx.State):
    messages: list[ChatMessage] = []
    input_text: str = ""
    thread_id: str = ""
    streaming: bool = False
    tools: list[ToolActivity] = []
    subagent: str = ""
    subagent_run_id: str = ""

    # Backend-only (underscore): never serialized to the browser.
    _pending_content: str = ""
    _stop_requested: bool = False

    @rx.event
    def set_input_text(self, value: str) -> None:
        self.input_text = value

    @rx.event
    def send(self) -> Any:
        content = self.input_text
        if self.streaming or not content.strip():
            return
        # Content is kept verbatim: no trimming, templating or prefixing
        # anywhere in this repo (SPEC-WCB-CHT-006).
        self.messages = [
            *self.messages,
            ChatMessage(id=_new_id(), role="user", text=content),
            ChatMessage(id=_new_id(), role="assistant"),
        ]
        self.input_text = ""
        self.streaming = True
        self._stop_requested = False
        self._pending_content = content
        yield
        yield ChatState.stream_turn

    @rx.event
    def stop_streaming(self) -> None:
        self._stop_requested = True
        task = _inflight.get(self._tab_key())
        if task is not None:
            task.cancel()

    @rx.event(background=True)
    async def stream_turn(self) -> None:
        key = self._tab_key()
        task = asyncio.current_task()
        if task is not None:
            _inflight[key] = task
        request_id = _new_id()
        try:
            async with self:
                content = self._pending_content
                thread_id = self.thread_id
            settings = get_settings()
            client = get_client()
            log.info("turn %s started thread=%s", request_id, thread_id or "<new>")

            if not thread_id:
                thread_id = (await client.create_thread()).thread_id
                async with self:
                    self.thread_id = thread_id

            use_agui = settings.agui_enabled and agui_available()
            try:
                count = await self._consume(
                    client,
                    thread_id,
                    content,
                    "ag-ui" if use_agui else "prismal",
                    settings.show_usage,
                )
            except ProtocolNotEnabledError:
                # SPEC-WCB-AGU-008: refused before any event — resend once,
                # classically, and stay classic for the rest of the process.
                if not use_agui:
                    raise
                disable_agui()
                count = await self._consume(
                    client, thread_id, content, "prismal", settings.show_usage
                )
            log.info("turn %s finished thread=%s events=%d", request_id, thread_id, count)
        except PrismalSDKError as exc:
            # The only place SDK exceptions are caught (SPEC-WCB-ERR-001).
            log.warning("turn %s failed code=%s", request_id, error_code(exc))
            friendly = friendly_error(exc)
            async with self:
                update_last(
                    self,
                    kind="error",
                    error_text=friendly.text,
                    retryable=friendly.retryable,
                )
        except asyncio.CancelledError:
            async with self:
                stopped_by_visitor = self._stop_requested
            log.info("turn %s cancelled (stop=%s)", request_id, stopped_by_visitor)
            if not stopped_by_visitor:
                await self._finish(key)
                raise  # tab teardown: let the runtime see the cancellation
        await self._finish(key)

    async def _consume(
        self,
        client: Any,
        thread_id: str,
        content: str,
        protocol: StreamProtocol,
        show_usage: bool,
    ) -> int:
        mapper: Mapper = apply_agui if protocol == "ag-ui" else apply_classic
        stream: AsyncGenerator[Any, None] = client.send_message(
            thread_id, content, protocol=protocol
        )
        count = 0
        async with contextlib.aclosing(stream):
            async for event in stream:
                count += 1
                async with self:
                    if mapper(self, event, show_usage=show_usage):
                        break
        return count

    async def _finish(self, key: str) -> None:
        _inflight.pop(key, None)
        async with self:
            end_turn(self)
            self.streaming = False
            self._pending_content = ""
            self._stop_requested = False

    def _tab_key(self) -> str:
        return self.router.session.client_token or "default"
