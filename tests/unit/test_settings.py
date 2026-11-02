"""WCB-00-03 + WCB-D-03: WebchatSettings.

SPEC-WCB-CFG-001/002/004, SPEC-WCB-AUT-001, SPEC-WCB-APP-004.
"""

from __future__ import annotations

import pytest
from pydantic import SecretStr, ValidationError

from prismal_webchat.settings import WebchatSettings

ENV_KEYS = (
    "SERVER_URL",
    "TOKEN",
    "ORG_ID",
    "TITLE",
    "WELCOME_MESSAGE",
    "ACCENT_COLOR",
    "THEME",
    "EMBED_ORIGINS",
    "AGUI_ENABLED",
    "SHOW_USAGE",
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in ENV_KEYS:
        monkeypatch.delenv(f"PRISMAL_WEBCHAT_{key}", raising=False)


def test_defaults_boot_against_local_host() -> None:
    s = WebchatSettings()
    assert s.server_url == "http://localhost:8000"
    assert s.token is None
    assert s.org_id is None
    assert s.title == "prismal"
    assert s.welcome_message == "Hi! How can I help?"
    assert s.accent_color == "#5D4BE5"
    assert s.theme == "light"
    assert s.embed_origins == []
    assert s.agui_enabled is False
    assert s.show_usage is False


def test_reads_prefixed_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRISMAL_WEBCHAT_SERVER_URL", "https://host.example.com")
    monkeypatch.setenv("PRISMAL_WEBCHAT_TOKEN", "s3cret-token")
    monkeypatch.setenv("PRISMAL_WEBCHAT_ORG_ID", "acme")
    monkeypatch.setenv("PRISMAL_WEBCHAT_THEME", "dark")
    monkeypatch.setenv("PRISMAL_WEBCHAT_EMBED_ORIGINS", '["https://www.example.com"]')
    monkeypatch.setenv("PRISMAL_WEBCHAT_AGUI_ENABLED", "true")
    monkeypatch.setenv("PRISMAL_WEBCHAT_SHOW_USAGE", "1")

    s = WebchatSettings()

    assert s.server_url == "https://host.example.com"
    assert isinstance(s.token, SecretStr)
    assert s.token.get_secret_value() == "s3cret-token"
    assert s.org_id == "acme"
    assert s.theme == "dark"
    assert s.embed_origins == ["https://www.example.com"]
    assert s.agui_enabled is True
    assert s.show_usage is True


def test_token_never_appears_in_repr_or_dump(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PRISMAL_WEBCHAT_TOKEN", "s3cret-token")
    s = WebchatSettings()
    assert "s3cret-token" not in repr(s)
    assert "s3cret-token" not in str(s.model_dump())
    assert "s3cret-token" not in s.model_dump_json()


@pytest.mark.parametrize(
    "url",
    ["localhost:8000", "ftp://host.example.com", "/relative", "http://", ""],
)
def test_server_url_must_be_absolute_http(url: str) -> None:
    with pytest.raises(ValidationError):
        WebchatSettings(server_url=url)


def test_server_url_trailing_slash_is_normalized() -> None:
    assert WebchatSettings(server_url="http://h:8000/").server_url == "http://h:8000"


@pytest.mark.parametrize("theme", ["light", "dark", "auto"])
def test_theme_accepts_known_values(theme: str) -> None:
    assert WebchatSettings(theme=theme).theme == theme


def test_theme_rejects_unknown_value() -> None:
    with pytest.raises(ValidationError):
        WebchatSettings(theme="sepia")


@pytest.mark.parametrize(
    "origin",
    ["https://www.example.com", "http://localhost:5173", "https://a.b.example.co.uk:8443"],
)
def test_embed_origins_accepts_origins(origin: str) -> None:
    assert WebchatSettings(embed_origins=[origin]).embed_origins == [origin]


@pytest.mark.parametrize(
    "origin",
    [
        "https://www.example.com/",  # path
        "https://www.example.com/page",
        "www.example.com",  # no scheme
        "ftp://example.com",
        "https://example.com?x=1",
        "https://*.example.com",  # wildcard: not supported in v0.1
        "'self'",
        "*",
    ],
)
def test_embed_origins_rejects_non_origins(origin: str) -> None:
    with pytest.raises(ValidationError):
        WebchatSettings(embed_origins=[origin])
