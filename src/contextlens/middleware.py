"""Host-side tool boundary that filters results before model delivery."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import wraps
from typing import Any

from contextlens.filtering import PruneSession, protected_line
from contextlens.models import estimate_tokens


class ToolResultMiddleware:
    """Install around a synchronous tool dispatcher, once per coding task."""

    def __init__(
        self, session: PruneSession, *, minimum_expected_savings: int = 512
    ) -> None:
        if minimum_expected_savings < 0:
            raise ValueError("minimum_expected_savings cannot be negative")
        self.session = session
        self.minimum_expected_savings = minimum_expected_savings

    def wrap(
        self, tool: str, call: Callable[[Mapping[str, Any]], Any]
    ) -> Callable[[Mapping[str, Any]], Any]:
        """Return a callable with the same argument and result shape."""

        @wraps(call)
        def intercepted(arguments: Mapping[str, Any]) -> Any:
            result = call(arguments)
            return self.process(tool, arguments, result)

        return intercepted

    def process(self, tool: str, arguments: Mapping[str, Any], result: Any) -> Any:
        """Process a raw result at any host tool-result boundary."""
        if not isinstance(result, str):
            return result
        if any(protected_line(line) for line in result.splitlines()):
            return result
        minimum = max(
            self.session.config.minimum_tokens,
            self.minimum_expected_savings * 2,
        )
        if estimate_tokens(result) < minimum:
            return result
        try:
            outcome = self.session.observe(result, tool=tool, arguments=arguments)
        except Exception:
            return result
        if (
            outcome.original_tokens - outcome.retained_tokens
            < self.minimum_expected_savings
        ):
            return result
        return outcome.text
