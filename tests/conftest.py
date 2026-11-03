"""Shared fixtures: offline SDK double + settings (WCB-00-05, SPEC-WCB-NFR-001)."""

from __future__ import annotations

import pytest
from pydantic import SecretStr

from prismal_webchat.settings import WebchatSettings
from tests.fakes import FakeAsyncPrismalClient

#: Sentinel secret; leak tests (WCB-04-01) grep for it.
TEST_TOKEN = "wcb-test-token-DO-NOT-LEAK"


@pytest.fixture
def fake_client() -> FakeAsyncPrismalClient:
    return FakeAsyncPrismalClient()


@pytest.fixture
def settings() -> WebchatSettings:
    return WebchatSettings(token=SecretStr(TEST_TOKEN), org_id="acme")


@pytest.fixture
def agui_settings() -> WebchatSettings:
    return WebchatSettings(token=SecretStr(TEST_TOKEN), agui_enabled=True)
