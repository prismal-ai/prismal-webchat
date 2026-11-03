"""Embedding policy: ``frame-ancestors`` CSP (WCB-03-03, SPEC-WCB-EMB-002).

The allowlist is enforced by the browser from a response header, never by
in-page JS. ``frame-ancestors`` is ignored in ``<meta>``, so it must be a
header: installed as a Reflex ``api_transformer`` it covers every response
the backend serves, including the compiled frontend in prod/single-port.
(The dev server's Vite frontend on :3000 does not pass through it.)
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from prismal_webchat.settings import WebchatSettings


def frame_ancestors(origins: Sequence[str]) -> str:
    """Empty allowlist => same-origin only (embedding disabled by default)."""
    return " ".join(["frame-ancestors", "'self'", *origins])


class FrameAncestorsMiddleware:
    """Adds the policy as its own CSP header; existing CSP headers are kept
    (browsers enforce every CSP header, so nothing is loosened)."""

    def __init__(self, app: ASGIApp, *, origins: Sequence[str]) -> None:
        self.app = app
        self.policy = frame_ancestors(origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_policy(message: Message) -> None:
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message).append("Content-Security-Policy", self.policy)
            await send(message)

        await self.app(scope, receive, send_with_policy)


def csp_transformer(settings: WebchatSettings) -> Callable[[ASGIApp], ASGIApp]:
    origins = list(settings.embed_origins)

    def apply_frame_ancestors(app: ASGIApp) -> ASGIApp:
        return FrameAncestorsMiddleware(app, origins=origins)

    return apply_frame_ancestors
