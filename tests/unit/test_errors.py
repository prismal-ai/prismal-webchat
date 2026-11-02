"""Error UX mapping (SPEC-WCB-ERR-001/002, DELTA-2026-10 ERR-002)."""

from __future__ import annotations

import pytest
from prismal_sdk import PrismalConnectionError, PrismalSDKError, PrismalTimeoutError

from prismal_webchat.errors import BUDGET_TEXT, friendly_error
from tests.scripts import api_error

UNREACHABLE = "Can't reach the assistant right now — try again."
GENERIC = "Something went wrong. Please try again."


@pytest.mark.parametrize(
    ("exc", "text", "retryable"),
    [
        (PrismalConnectionError("refused 10.0.0.3:8000"), UNREACHABLE, True),
        (PrismalTimeoutError("read timeout"), UNREACHABLE, True),
        (api_error(402, "budget_exceeded", "tenant acme over $5"), BUDGET_TEXT, False),
        (api_error(429, "budget_exceeded", "v0.1 host"), BUDGET_TEXT, False),
        (api_error(503, "runtime_composition_error"), GENERIC, True),
        (api_error(403, "policy_denied", "rule 7"), "That request can't be processed.", True),
        (api_error(403, "permission_denied"), "That request can't be processed.", True),
        (api_error(500, "internal_error", "Traceback ..."), GENERIC, True),
        (PrismalSDKError("weird"), GENERIC, True),
    ],
)
def test_maps_to_friendly_text(exc: Exception, text: str, retryable: bool) -> None:
    friendly = friendly_error(exc)
    assert (friendly.text, friendly.retryable) == (text, retryable)


def test_budget_copy_matches_delta() -> None:
    assert BUDGET_TEXT == (
        "This assistant has reached its usage limit for now. Please try again later."
    )


@pytest.mark.parametrize(
    "exc",
    [
        api_error(402, "budget_exceeded", "tenant acme exceeded $5.00", limit=5.0),
        api_error(500, "internal_error", "Traceback (most recent call last)"),
        PrismalConnectionError("refused 10.0.0.3:8000"),
    ],
)
def test_never_leaks_codes_or_server_messages(exc: Exception) -> None:
    text = friendly_error(exc).text
    for leak in (
        "budget_exceeded",
        "internal_error",
        "acme",
        "5.0",
        "Traceback",
        "10.0.0.3",
        "402",
    ):
        assert leak not in text
