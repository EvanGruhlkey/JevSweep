"""Transcript types used only by the paired coding-agent benchmark."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

from jevsweep.models import estimate_tokens


@dataclass(frozen=True, slots=True)
class ToolUse:
    tool_use_id: str
    tool: str
    arguments: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.tool_use_id.strip() or not self.tool.strip():
            raise ValueError("tool use needs an identifier and name")
        object.__setattr__(self, "arguments", MappingProxyType(dict(self.arguments)))


@dataclass(frozen=True, slots=True)
class ToolResult:
    tool_use_id: str
    text: str
    is_error: bool = False

    def __post_init__(self) -> None:
        if not self.tool_use_id.strip():
            raise ValueError("tool result needs an identifier")


@dataclass(frozen=True, slots=True)
class Message:
    role: str
    text: str = ""
    tool_uses: tuple[ToolUse, ...] = ()
    tool_results: tuple[ToolResult, ...] = ()

    def __post_init__(self) -> None:
        if self.role not in {"system", "user", "assistant"}:
            raise ValueError(f"unsupported role: {self.role!r}")
        object.__setattr__(self, "tool_uses", tuple(self.tool_uses))
        object.__setattr__(self, "tool_results", tuple(self.tool_results))


def transcript_tokens(messages: tuple[Message, ...]) -> int:
    total = 0
    for message in messages:
        total += estimate_tokens(message.text)
        for use in message.tool_uses:
            total += estimate_tokens(repr(dict(use.arguments)))
        for result in message.tool_results:
            total += estimate_tokens(result.text)
    return total
