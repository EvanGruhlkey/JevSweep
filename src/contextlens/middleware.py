"""Host-side tool boundary that filters results before model delivery."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from functools import wraps
from typing import Any

from contextlens.filtering import PruneSession


class ToolResultMiddleware:
    """Install around a synchronous tool dispatcher, once per coding task."""

    def __init__(self, session: PruneSession) -> None:
        self.session = session

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
        try:
            outcome = self.session.observe(result, tool=tool, arguments=arguments)
        except Exception:
            return result
        return outcome.text
