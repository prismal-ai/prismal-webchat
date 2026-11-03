"""Message input + Send/Stop (WCB-02-01, CHT-004, NFR-004).

``sp_input`` inside a native form: Enter submits, no key-handler tricks
(``sp_textarea`` exposes no key events, so it cannot send on Enter).
"""

from __future__ import annotations

import reflex as rx
from reflex_silverpoint_react import sp_button, sp_input

from prismal_webchat.state.chat import INPUT_ID, ChatState


def input_bar() -> rx.Component:
    return rx.el.form(
        rx.el.div(
            sp_input(
                id=INPUT_ID,
                name="message",
                value=ChatState.input_text,
                on_change=ChatState.set_input_text,
                label="Message",
                placeholder="Type a message…",
                width="100%",
            ),
            flex="1",
        ),
        rx.cond(
            ChatState.streaming,
            sp_button("Stop", variant="danger", type="button", on_click=ChatState.stop_streaming),
            sp_button("Send", variant="primary", type="submit", disabled=ChatState.streaming),
        ),
        on_submit=lambda _form: ChatState.send,
        display="flex",
        gap="8px",
        align_items="flex-end",
        padding="12px 16px",
    )
