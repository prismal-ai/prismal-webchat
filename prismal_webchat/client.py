"""The one path to prismal-server (SPEC-WCB-APP-003, ADR-002).

A lazily built, process-wide ``AsyncPrismalClient``. Settings reach the SDK
only through its constructor; the token never leaves this module's call.
"""

from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator

from prismal_sdk import AsyncPrismalClient

from prismal_webchat.settings import get_settings

log = logging.getLogger(__name__)

_client: AsyncPrismalClient | None = None
_agui_available = True


def get_client() -> AsyncPrismalClient:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncPrismalClient(
            settings.server_url,
            token=settings.token.get_secret_value() if settings.token else None,
            org_id=settings.org_id,
        )
    return _client


async def close_client() -> None:
    """Close the pool on app shutdown (registered as a Reflex lifespan task)."""
    global _client
    if _client is not None:
        client, _client = _client, None
        await client.aclose()


@contextlib.asynccontextmanager
async def client_lifespan() -> AsyncIterator[None]:
    """Reflex lifespan task: nothing at startup (lazy), close at shutdown."""
    try:
        yield
    finally:
        await close_client()


def agui_available() -> bool:
    return _agui_available


def disable_agui() -> None:
    """Sticky classic fallback after ProtocolNotEnabledError (SPEC-WCB-AGU-008)."""
    global _agui_available
    if _agui_available:
        _agui_available = False
        log.warning("AG-UI not enabled on prismal-server; using classic stream for this process")


def reset_client_for_tests() -> None:
    global _client, _agui_available
    _client = None
    _agui_available = True
