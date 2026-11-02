"""Reflex app assembly (ARCHITECTURE §3).

``/`` is the full chat page. The bare, iframe-safe ``/chat`` route arrives
with WCB-03-01.
"""

from __future__ import annotations

import reflex as rx

from prismal_webchat.client import client_lifespan
from prismal_webchat.components.chat_panel import chat_panel
from prismal_webchat.components.input_bar import input_bar
from prismal_webchat.components.theme import themed, validate_theme
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


app = rx.App()
app.register_lifespan_task(client_lifespan)
app.add_page(index, route="/", title=settings.title)
