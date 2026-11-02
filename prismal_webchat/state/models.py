"""UI-side records rendered by the chat panel (WCB-01-02).

They hold presentation data only: never the token, settings, tool
arguments/results, or usage beyond an opt-in ``total_tokens`` (USG-001/002).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

Role = Literal["user", "assistant"]
Kind = Literal["text", "error"]


@dataclass
class ChatMessage:
    id: str
    role: Role
    text: str = ""
    kind: Kind = "text"
    #: Friendly error copy shown under partial text (ERR-001/003).
    error_text: str = ""
    retryable: bool = False
    #: Only set when ``show_usage`` is on (SPEC-WCB-USG-002).
    total_tokens: int | None = None


@dataclass
class ToolActivity:
    id: str
    name: str
    done: bool = False


class ChatView(Protocol):
    """What the mappers touch; satisfied by ``ChatState`` and by test views."""

    messages: list[ChatMessage]
    tools: list[ToolActivity]
    subagent: str
    subagent_run_id: str
