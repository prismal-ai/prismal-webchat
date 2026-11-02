"""SDK exception -> visitor copy (ARCHITECTURE §6, SPEC-WCB-ERR-001/002).

Codes, server messages and tracebacks never reach the visitor; callers log
the code only.
"""

from __future__ import annotations

from dataclasses import dataclass

from prismal_sdk import (
    PermissionDeniedError,
    PolicyDeniedError,
    PrismalAPIError,
    PrismalTransportError,
)

UNREACHABLE_TEXT = "Can't reach the assistant right now — try again."
BUDGET_TEXT = "This assistant has reached its usage limit for now. Please try again later."
DENIED_TEXT = "That request can't be processed."
GENERIC_TEXT = "Something went wrong. Please try again."


@dataclass(frozen=True)
class FriendlyError:
    text: str
    retryable: bool


def friendly_error(exc: BaseException) -> FriendlyError:
    # Budget is mapped by code (DELTA-2026-10 ERR-002): covers 402, the v0.1
    # host's 429 and the mid-stream terminal error alike. No retry offered.
    if isinstance(exc, PrismalAPIError) and exc.code == "budget_exceeded":
        return FriendlyError(BUDGET_TEXT, retryable=False)
    if isinstance(exc, PrismalTransportError):
        return FriendlyError(UNREACHABLE_TEXT, retryable=True)
    if isinstance(exc, PolicyDeniedError | PermissionDeniedError):
        return FriendlyError(DENIED_TEXT, retryable=True)
    return FriendlyError(GENERIC_TEXT, retryable=True)


def error_code(exc: BaseException) -> str:
    """Loggable identifier: the wire code or the exception class, never a message."""
    return exc.code if isinstance(exc, PrismalAPIError) else type(exc).__name__
