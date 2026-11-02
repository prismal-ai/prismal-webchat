"""Reflex app assembly (ARCHITECTURE §3).

Scaffold only (WCB-00-02): an empty chat shell themed with silverpoint.
The chat panel, settings-driven theme and the bare ``/chat`` route arrive in
WCB-02-01, WCB-02-05 and WCB-03-01.
"""

from __future__ import annotations

import reflex as rx
from reflex_silverpoint_react import silverpoint_provider, sp_surface

from prismal_webchat.client import client_lifespan


def index() -> rx.Component:
    return silverpoint_provider(
        rx.center(
            sp_surface(
                rx.heading("prismal", size="5"),
                rx.text("Chat coming soon."),
                frame="card",
                id="chat-shell",
                width="min(480px, 100%)",
                padding="24px",
            ),
            min_height="100vh",
            padding="16px",
        ),
        ground="silverpoint",
        substrate="cream",
    )


app = rx.App()
app.register_lifespan_task(client_lifespan)
app.add_page(index, route="/", title="prismal")
