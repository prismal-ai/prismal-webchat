"""WCB-02-01/03/04/06, D-06, D-08 (UI): chat panel and input bar trees.

Offline: inspects the rendered component tree, no frontend compile.
"""

from __future__ import annotations

import reflex as rx
from pydantic import SecretStr

from prismal_webchat.components.chat_panel import chat_panel, markdown_link, message_markdown
from prismal_webchat.components.input_bar import input_bar
from prismal_webchat.settings import WebchatSettings


def _panel(**kw: object) -> str:
    return str(chat_panel(WebchatSettings(**kw)))  # type: ignore[arg-type]


def test_panel_uses_silverpoint_building_blocks() -> None:
    rendered = _panel()
    for name in ("SpSurface", "SpAvatar", "SpTag", "SpAlert", "SpSkeleton", "SpProgress"):
        assert name in rendered, name


def test_welcome_message_is_presentational() -> None:
    rendered = _panel(welcome_message="Hola, soy Prismal")
    assert "Hola, soy Prismal" in rendered


def test_markdown_does_not_interpret_raw_html() -> None:
    rendered = str(message_markdown(rx.Var.create("x")))
    assert "rehypeRaw" not in rendered
    assert "ReactMarkdown" in rendered


def test_markdown_links_open_safely() -> None:
    rendered = str(markdown_link("site", href="https://example.com"))
    assert 'rel:"noopener noreferrer"' in rendered
    assert 'target:"_blank"' in rendered


def test_transcript_is_an_aria_live_region() -> None:
    rendered = _panel()
    assert '"aria-live":"polite"' in rendered
    assert 'role:"log"' in rendered


def test_retry_button_only_for_retryable_errors() -> None:
    rendered = _panel()
    assert "retryable" in rendered
    assert "Retry" in rendered


def test_usage_footer_absent_unless_enabled() -> None:
    assert "tokens" not in _panel(show_usage=False)
    assert "tokens" in _panel(show_usage=True)


def test_panel_never_embeds_settings_secrets() -> None:
    secret = "wcb-test-token-DO-NOT-LEAK"
    rendered = str(
        chat_panel(WebchatSettings(token=SecretStr(secret), server_url="https://h.example"))
    )
    assert secret not in rendered and "h.example" not in rendered


def test_input_bar_submits_with_enter_through_a_form() -> None:
    rendered = str(input_bar())
    assert rendered.startswith('jsx("form"')
    assert "onSubmit" in rendered
    assert "SpInput" in rendered
    assert 'type:"submit"' in rendered


def test_input_bar_disables_send_and_shows_stop_while_streaming() -> None:
    rendered = str(input_bar())
    assert "streaming" in rendered
    assert "stop_streaming" in rendered
    assert "Stop" in rendered
