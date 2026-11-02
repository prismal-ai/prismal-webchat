"""A plain ChatView for mapper tests (no Reflex)."""

from __future__ import annotations

from dataclasses import dataclass, field

from prismal_webchat.state.models import ChatMessage, ToolActivity


@dataclass
class View:
    messages: list[ChatMessage] = field(
        default_factory=lambda: [ChatMessage(id="a1", role="assistant")]
    )
    tools: list[ToolActivity] = field(default_factory=list)
    subagent: str = ""
    subagent_run_id: str = ""

    @property
    def last(self) -> ChatMessage:
        return self.messages[-1]
