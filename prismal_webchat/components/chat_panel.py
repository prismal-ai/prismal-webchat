"""Transcript: bubbles, live activity, error + retry (WCB-02-01/02/03/04, D-06, D-08).

Silverpoint ships no chat component, so the panel is composed from its
primitives (SPEC-WCB-UI-001): ``sp_surface`` bubbles seeded by message id
(UI-003), ``sp_avatar``, ``sp_skeleton`` while the first token is pending,
``sp_tag`` tool chips, ``sp_progress`` for the sub-agent line and
``sp_alert`` for errors. Markdown stays with ``rx.markdown``.
"""

from __future__ import annotations

from typing import Any

import reflex as rx
from reflex_silverpoint_react import (
    sp_alert,
    sp_avatar,
    sp_button,
    sp_glyph,
    sp_progress,
    sp_skeleton,
    sp_surface,
    sp_tag,
)

from prismal_webchat.settings import WebchatSettings
from prismal_webchat.state.agui_mapper import SUBAGENT_FALLBACK
from prismal_webchat.state.chat import ChatState
from prismal_webchat.state.models import ChatMessage

TRANSCRIPT_ID = "prismal-chat-transcript"


def markdown_link(*children: Any, **props: Any) -> rx.Component:
    """Model output links open in a new tab without opener access (CHT-008)."""
    return rx.el.a(*children, **props, rel="noopener noreferrer", target="_blank")


def message_markdown(text: Any) -> rx.Component:
    # use_raw=False: raw HTML in model output is rendered inert (CHT-008).
    return rx.markdown(text, use_raw=False, component_map={"a": markdown_link})


def _row(*children: rx.Component, mine: bool) -> rx.Component:
    return rx.el.div(
        *children,
        display="flex",
        gap="10px",
        align_items="flex-start",
        flex_direction="row-reverse" if mine else "row",
    )


def _bubble(*children: rx.Component, seed: Any) -> rx.Component:
    # No tone: silverpoint tone is hatching, which would sit behind the text.
    return sp_surface(
        *children,
        frame="card",
        seed=seed,
        padding="10px 14px",
        max_width="85%",
        overflow_wrap="anywhere",
    )


def welcome_bubble(text: str) -> rx.Component:
    """Presentational first bubble; never sent to the engine (CHT-007)."""
    return _row(
        sp_avatar(initials="AI", name="Assistant", pixel_size=32),
        _bubble(message_markdown(text), seed="welcome"),
        mine=False,
    )


def _usage_footer(m: Any) -> rx.Component:
    # Rendered only when show_usage is on; total_tokens only (USG-002).
    return rx.cond(
        m.total_tokens,
        rx.el.p(m.total_tokens.to_string(), " tokens", font_size="12px", opacity="0.7"),
    )


def _error_block(m: Any) -> rx.Component:
    return rx.cond(
        m.kind == "error",
        rx.el.div(
            sp_alert(m.error_text, kind="error"),
            rx.cond(
                m.retryable,
                sp_button(
                    "Retry",
                    on_click=ChatState.retry(m.id),  # type: ignore[operator]  # reflex typing
                    size="sm",
                ),
            ),
            display="flex",
            flex_direction="column",
            gap="8px",
            margin_top="8px",
        ),
    )


def message_bubble(m: Any, *, show_usage: bool) -> rx.Component:
    assistant = _row(
        sp_avatar(initials="AI", name="Assistant", pixel_size=32),
        _bubble(
            rx.cond(
                (m.id == ChatState.live_id) & (m.text == ""),
                sp_skeleton(lines=2, label="Assistant is thinking"),
                message_markdown(m.text),
            ),
            _error_block(m),
            *([_usage_footer(m)] if show_usage else []),
            seed=m.id,
        ),
        mine=False,
    )
    # A finished turn with no text and no error (e.g. tool-only) shows nothing.
    has_content = (m.text != "") | (m.kind == "error") | (m.id == ChatState.live_id)
    user = _row(
        sp_avatar(initials="You", name="You", pixel_size=32),
        _bubble(rx.el.p(m.text, white_space="pre-wrap", margin="0"), seed=m.id),
        mine=True,
    )
    return rx.cond(m.role == "user", user, rx.cond(has_content, assistant))


def activity_row() -> rx.Component:
    """Tool chips (CHT-003, AGU-003) and the sub-agent line (AGU-004)."""
    chips = rx.foreach(
        ChatState.tools,
        lambda t: sp_tag(
            rx.cond(t.done, sp_glyph(glyph="tick", size="sm")),
            "using ",
            t.name,
            rx.cond(t.done, "", "…"),
            tone=rx.cond(t.done, 1, 2),
        ),
    )
    subagent = rx.cond(
        ChatState.subagent != "",
        rx.el.div(
            sp_progress(shape="line", label="Working"),
            rx.el.span(
                rx.cond(
                    ChatState.subagent == SUBAGENT_FALLBACK,
                    "working…",
                    "working on: " + ChatState.subagent,
                ),
                font_size="13px",
            ),
            display="flex",
            flex_direction="column",
            gap="4px",
        ),
    )
    return rx.el.div(chips, subagent, display="flex", flex_wrap="wrap", gap="6px")


def chat_panel(settings: WebchatSettings) -> rx.Component:
    return rx.el.div(
        welcome_bubble(settings.welcome_message),
        rx.foreach(
            ChatState.messages,
            lambda m: message_bubble(m.to(ChatMessage), show_usage=settings.show_usage),
        ),
        activity_row(),
        id=TRANSCRIPT_ID,
        role="log",
        custom_attrs={"aria-live": "polite", "aria-label": "Conversation"},
        display="flex",
        flex_direction="column",
        gap="12px",
        overflow_y="auto",
        flex="1",
        padding="16px",
    )
