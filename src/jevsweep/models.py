"""Fast token estimates and value types used by the pruning engine."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from enum import StrEnum

_TOKEN_PIECES = re.compile(r"[A-Za-z]+|\d+|[^\sA-Za-z\d]")
_DIGIT = re.compile(r"\d")


def estimate_tokens(text: str) -> int:
    """Estimate tokens without a tokenizer.

    A word costs one token per six letters, a digit half a token, and any
    other symbol nine tenths. Calibrated by `fast-jev-compaction` against the
    usage Jev reports for real transcripts, where it lands a little above the
    true count. A flat characters-per-token ratio undercounts JSON-heavy
    states badly, which would push requests over the provider limit.
    """

    total = 0.0
    for piece in _TOKEN_PIECES.findall(text):
        first = piece[0]
        if first.isdigit():
            total += len(piece) / 2
        elif first.isascii() and first.isalpha():
            total += 1 + (len(piece) - 1) // 6
        else:
            total += 0.9
    return math.ceil(total)


def estimate_state_tokens(text: str) -> int:
    """Estimate tokens for a JSON state, where digits are tokenized densely."""

    return estimate_tokens(text) + len(_DIGIT.findall(text)) // 2


class OutputCategory(StrEnum):
    """What a tool result looks like, which changes the guidance Jev gets."""

    BUILD = "build"
    SEARCH = "search"
    SOURCE = "source"
    STRUCTURED = "structured"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LineRange:
    """A contiguous 1-based line range removed from a rendered observation."""

    start_line: int
    end_line: int

    def __post_init__(self) -> None:
        if self.start_line < 1 or self.end_line < self.start_line:
            raise ValueError("invalid line range")

    @property
    def line_count(self) -> int:
        return self.end_line - self.start_line + 1

    def to_dict(self) -> dict[str, int]:
        return {
            "start_line": self.start_line,
            "end_line": self.end_line,
            "line_count": self.line_count,
        }
