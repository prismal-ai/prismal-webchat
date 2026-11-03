"""Backend-only configuration (SPEC.md §6, ARCHITECTURE §4.4).

``WebchatSettings`` is never an ``rx.State`` field and never crosses into
components: only derived, non-secret presentation values do
(SPEC-WCB-CFG-003). The token is a ``SecretStr`` handed only to the SDK
client constructor (SPEC-WCB-AUT-001/002).
"""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

Theme = Literal["light", "dark", "auto"]

_HTTP_SCHEMES = ("http", "https")
_HEX_COLOR = re.compile(r"#[0-9A-Fa-f]{6}")


def _is_origin(value: str) -> bool:
    """``scheme://host[:port]`` with nothing after it (SPEC-WCB-CFG-002)."""
    parts = urlsplit(value)
    try:
        parts.port  # noqa: B018 - raises ValueError on a malformed port
    except ValueError:
        return False
    return (
        parts.scheme in _HTTP_SCHEMES
        and bool(parts.hostname)
        and "*" not in parts.netloc
        and "@" not in parts.netloc
        and value == f"{parts.scheme}://{parts.netloc}"
    )


class WebchatSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="PRISMAL_WEBCHAT_",
        extra="ignore",
        frozen=True,
    )

    # Upstream (prismal-server via prismal-sdk)
    server_url: str = "http://localhost:8000"
    token: SecretStr | None = None
    org_id: str | None = None

    # Presentation (non-secret)
    title: str = "prismal"
    welcome_message: str = "Hi! How can I help?"
    # #5D4BE5 (not the original #6C5CE7, 3.94:1) passes silverpoint's 4.5:1
    # ink contrast on the cream ground (DELTA-2026-11, SPEC-WCB-UI-002).
    accent_color: str = "#5D4BE5"
    theme: Theme = "light"

    # Embedding (frame-ancestors allowlist; empty => 'self')
    embed_origins: list[str] = []

    # DELTA-2026-10 (SPEC-WCB-CFG-004)
    agui_enabled: bool = False
    show_usage: bool = False

    @field_validator("server_url")
    @classmethod
    def _absolute_http_url(cls, value: str) -> str:
        parts = urlsplit(value)
        if parts.scheme not in _HTTP_SCHEMES or not parts.hostname:
            raise ValueError("server_url must be an absolute http(s):// URL")
        return value.rstrip("/")

    @field_validator("accent_color")
    @classmethod
    def _hex_color(cls, value: str) -> str:
        if not _HEX_COLOR.fullmatch(value):
            raise ValueError("accent_color must be a #RRGGBB hex colour")
        return value.upper()

    @field_validator("embed_origins")
    @classmethod
    def _origins_only(cls, value: list[str]) -> list[str]:
        bad = [origin for origin in value if not _is_origin(origin)]
        if bad:
            raise ValueError(f"embed_origins entries must be scheme://host[:port]; got {bad}")
        return value


@lru_cache(maxsize=1)
def get_settings() -> WebchatSettings:
    """Process-wide settings, read once (fail-fast at first use)."""
    return WebchatSettings()
