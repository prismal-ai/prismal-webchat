"""Reflex app assembly (ARCHITECTURE §3).

``/`` is the full chat page; ``/chat`` is the same ``ChatState``-driven panel
without page chrome, for the ``embed.js`` iframe (SPEC-WCB-APP-001).
"""

from __future__ import annotations

import reflex as rx
from reflex_silverpoint_react import sp_button

from prismal_webchat.client import client_lifespan
from prismal_webchat.components.chat_panel import chat_panel
from prismal_webchat.components.input_bar import input_bar
from prismal_webchat.components.theme import themed, validate_theme
from prismal_webchat.embedding import csp_transformer
from prismal_webchat.settings import get_settings

settings = get_settings()
validate_theme(settings)  # fail fast on an unreadable accent (SPEC-WCB-UI-002)


def chat_window() -> rx.Component:
    return rx.el.main(
        rx.el.header(
            rx.el.h1(settings.title, font_size="18px", margin="0"),
            padding="12px 16px",
            border_bottom="1px solid currentColor",
        ),
        chat_panel(settings),
        input_bar(),
        display="flex",
        flex_direction="column",
        height="100dvh",
        max_width="760px",
        margin="0 auto",
    )


def index() -> rx.Component:
    return themed(chat_window(), settings=settings)


#: Asks the embedding loader to close the widget (SPEC-WCB-EMB-003). The
#: message carries no data, so any targetOrigin is safe; the loader checks
#: that it comes from the chat's origin.
CLOSE_WIDGET = rx.call_script('window.parent.postMessage({type: "prismal-chat:close"}, "*")')


def chat_bare() -> rx.Component:
    return themed(
        rx.el.div(
            rx.el.div(
                sp_button("Close", size="sm", on_click=CLOSE_WIDGET),
                display="flex",
                justify_content="flex-end",
                padding="8px 12px 0",
            ),
            chat_panel(settings),
            input_bar(),
            display="flex",
            flex_direction="column",
            height="100dvh",
        ),
        settings=settings,
    )


app = rx.App(api_transformer=csp_transformer(settings))
app.register_lifespan_task(client_lifespan)
app.add_page(index, route="/", title=settings.title)
app.add_page(chat_bare, route="/chat", title=settings.title)
