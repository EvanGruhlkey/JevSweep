"""Installable tool-call boundary for conservative observation pruning."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from contextlens.pruning.model import ObservationKind, estimate_tokens
from contextlens.pruning.runtime import (
    PruningSession,
    ToolObservation,
    classify_observation,
)


class ToolResultMiddleware:
    """Wrap an agent's tool dispatcher so results are processed before delivery.

    Only plain Python source reads are eligible. All other shapes pass through.
    The agent host must install this at its tool-result boundary.
    """

    def __init__(
        self, session: PruningSession, *, minimum_expected_savings: int = 512
    ) -> None:
        self.session = session
        self.minimum_expected_savings = minimum_expected_savings

    def wrap(self, call: Callable[..., Any], tool: str) -> Callable[..., Any]:
        @wraps(call)
        def intercepted(**arguments: Any) -> Any:
            result = call(**arguments)
            if not isinstance(result, str):
                return result
            try:
                observation = ToolObservation(result, tool, arguments)
                kind, language = classify_observation(observation)
                if kind is not ObservationKind.CODE or language != "python":
                    return result
                if estimate_tokens(result) < max(
                    self.session.minimum_tokens, self.minimum_expected_savings * 2
                ):
                    return result
                if _unsafe(result):
                    return result
                pruned = self.session.observe(observation)
                if pruned.result.saved_tokens < self.minimum_expected_savings:
                    return result
                return pruned.text
            except Exception:
                return result

        return intercepted


def _unsafe(content: str) -> bool:
    lowered = content.lower()
    return any(
        marker in lowered
        for marker in (
            "traceback (most recent call last)",
            "error:",
            "failed",
            "assertionerror",
            "git diff",
            "diff --git",
            "test result",
            "tests passed",
            "tests failed",
        )
    )
