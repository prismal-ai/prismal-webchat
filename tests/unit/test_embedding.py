"""WCB-03-01..04: iframe route, frame-ancestors CSP, embed.js loader.

SPEC-WCB-APP-001, EMB-001..004.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

import pytest
from starlette.responses import PlainTextResponse
from starlette.types import ASGIApp, Message

from prismal_webchat.embedding import FrameAncestorsMiddleware, csp_transformer, frame_ancestors
from prismal_webchat.settings import WebchatSettings

ROOT = Path(__file__).resolve().parents[2]
EMBED_JS = ROOT / "assets" / "embed.js"


# ── CSP (EMB-002) ────────────────────────────────────────────────────────────


def test_empty_allowlist_means_self_only() -> None:
    assert frame_ancestors([]) == "frame-ancestors 'self'"


def test_allowlist_is_appended_to_self() -> None:
    assert frame_ancestors(["https://a.example", "http://localhost:5500"]) == (
        "frame-ancestors 'self' https://a.example http://localhost:5500"
    )


def _page(headers: dict[str, str] | None = None) -> ASGIApp:
    return PlainTextResponse("ok", headers=headers)


async def _csp_headers(app: ASGIApp, path: str = "/") -> list[str]:
    """Call ``app`` as ASGI and return its Content-Security-Policy values."""
    sent: list[Message] = []

    async def receive() -> Message:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: Message) -> None:
        sent.append(message)

    scope = {"type": "http", "method": "GET", "path": path, "headers": [], "query_string": b""}
    await app(scope, receive, send)
    start = next(m for m in sent if m["type"] == "http.response.start")
    return [
        v.decode() for k, v in start["headers"] if k.decode().lower() == "content-security-policy"
    ]


@pytest.mark.parametrize("path", ["/", "/chat", "/chat/", "/embed.js", "/_next/x.js"])
async def test_every_http_response_carries_the_policy(path: str) -> None:
    app = FrameAncestorsMiddleware(_page(), origins=["https://www.example.com"])
    assert await _csp_headers(app, path) == ["frame-ancestors 'self' https://www.example.com"]


async def test_existing_csp_is_kept_and_policy_added_alongside() -> None:
    app = FrameAncestorsMiddleware(
        _page({"Content-Security-Policy": "default-src 'self'"}), origins=[]
    )
    assert await _csp_headers(app) == ["default-src 'self'", "frame-ancestors 'self'"]


async def test_non_http_scopes_pass_through_untouched() -> None:
    seen: list[str] = []

    async def inner(scope: dict[str, object], receive: object, send: object) -> None:
        seen.append(str(scope["type"]))

    await FrameAncestorsMiddleware(inner, origins=[])({"type": "websocket"}, None, None)  # type: ignore[arg-type]
    assert seen == ["websocket"]


async def test_transformer_reads_allowlist_from_settings() -> None:
    wrapped = csp_transformer(WebchatSettings(embed_origins=["https://x.example"]))(_page())
    assert await _csp_headers(wrapped) == ["frame-ancestors 'self' https://x.example"]


def test_app_installs_the_transformer() -> None:
    from prismal_webchat.webchat import app

    transformers = app.api_transformer
    assert transformers is not None
    assert getattr(transformers, "__name__", "") == "apply_frame_ancestors"


# ── /chat route (APP-001, WCB-03-01) ─────────────────────────────────────────


def test_bare_chat_route_is_registered() -> None:
    from prismal_webchat.webchat import app

    assert "chat" in app._unevaluated_pages


def test_bare_route_has_no_page_chrome_but_same_state() -> None:
    from prismal_webchat.webchat import chat_bare, index

    bare, full = str(chat_bare()), str(index())
    assert 'jsx("h1"' in full and 'jsx("h1"' not in bare
    for shared in ("SilverpointProvider", "SpInput", 'role:"log"'):
        assert shared in bare


def test_bare_route_can_ask_the_loader_to_close() -> None:
    from prismal_webchat.webchat import chat_bare

    rendered = str(chat_bare())
    assert "prismal-chat:close" in rendered
    assert "window.parent.postMessage" in rendered


# ── embed.js (EMB-001/003/004) ───────────────────────────────────────────────


@pytest.fixture(scope="module")
def loader() -> str:
    return EMBED_JS.read_text()


def test_loader_derives_its_origin_from_its_own_script_tag(loader: str) -> None:
    assert "document.currentScript" in loader
    assert '"/chat"' in loader


@pytest.mark.parametrize(
    "forbidden",
    [
        "localhost:8000",
        "PRISMAL_WEBCHAT",
        "token",
        "Bearer",
        "org_id",
        "X-Org-Id",
        "http://",
        "https://",
    ],
)
def test_loader_knows_no_secret_tenant_or_server_url(loader: str, forbidden: str) -> None:
    assert forbidden.lower() not in loader.lower()


def test_loader_validates_message_origin_before_acting(loader: str) -> None:
    listener = loader[loader.index('addEventListener("message"') :]
    assert listener.index("event.origin !== chatOrigin") < listener.index("setOpen(")


def test_loader_exposes_open_close_and_is_idempotent(loader: str) -> None:
    for token in ("prismal-chat:open", "prismal-chat:close", "window.PrismalChat", "aria-expanded"):
        assert token in loader
    assert re.search(r"if \(window\.PrismalChat\)\s*\{?\s*return", loader)


@pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")
def test_loader_is_valid_javascript() -> None:
    result = subprocess.run(["node", "--check", str(EMBED_JS)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
