"""WCB-01-01: process-wide AsyncPrismalClient (SPEC-WCB-APP-003, AUT-001/003)."""

from __future__ import annotations

from typing import Any, ClassVar

import pytest
from pydantic import SecretStr

from prismal_webchat import client as client_mod
from prismal_webchat.settings import WebchatSettings


class _Recorder:
    instances: ClassVar[list[_Recorder]] = []

    def __init__(self, base_url: str, **kwargs: Any) -> None:
        self.base_url = base_url
        self.kwargs = kwargs
        self.closed = False
        _Recorder.instances.append(self)

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture(autouse=True)
def _isolate(monkeypatch: pytest.MonkeyPatch) -> None:
    _Recorder.instances = []
    monkeypatch.setattr(client_mod, "AsyncPrismalClient", _Recorder)
    monkeypatch.setattr(
        client_mod,
        "get_settings",
        lambda: WebchatSettings(
            server_url="https://host.example.com", token=SecretStr("tok"), org_id="acme"
        ),
    )
    client_mod.reset_client_for_tests()


def test_client_is_built_lazily_once() -> None:
    assert _Recorder.instances == []
    first, second = client_mod.get_client(), client_mod.get_client()
    assert first is second
    assert len(_Recorder.instances) == 1


def test_client_receives_settings_only_through_constructor() -> None:
    built = client_mod.get_client()
    assert built.base_url == "https://host.example.com"  # type: ignore[attr-defined]
    assert built.kwargs == {"token": "tok", "org_id": "acme"}  # type: ignore[attr-defined]


async def test_close_client_closes_and_resets() -> None:
    built = client_mod.get_client()
    await client_mod.close_client()
    assert built.closed is True  # type: ignore[attr-defined]
    assert client_mod.get_client() is not built


async def test_close_client_without_client_is_noop() -> None:
    await client_mod.close_client()
    assert _Recorder.instances == []


def test_agui_fallback_is_sticky_for_the_process() -> None:
    assert client_mod.agui_available() is True
    client_mod.disable_agui()
    assert client_mod.agui_available() is False


def test_get_settings_is_cached() -> None:
    from prismal_webchat.settings import get_settings

    get_settings.cache_clear()
    assert get_settings() is get_settings()


async def test_lifespan_closes_client_on_shutdown() -> None:
    async with client_mod.client_lifespan():
        built = client_mod.get_client()
        assert built.closed is False  # type: ignore[attr-defined]
    assert built.closed is True  # type: ignore[attr-defined]


def test_app_registers_client_lifespan() -> None:
    from prismal_webchat.webchat import app

    assert client_mod.client_lifespan in app.get_lifespan_tasks()
