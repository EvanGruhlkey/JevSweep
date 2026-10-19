"""Paired coding-task comparison contract; no synthetic benchmark outcomes."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

STRATEGIES = ("baseline", "rules", "jev")


def compare_strategies(
    tasks: Sequence[str],
    run: Callable[[str, str], Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Run each strategy on each task with a fresh agent environment.

    ``run`` owns isolation, installs the selected middleware, and reports
    measured provider usage. Missing measurements remain absent, not zero.
    """
    rows: list[dict[str, Any]] = []
    for task in tasks:
        task_rows = []
        for strategy in STRATEGIES:
            measured = dict(run(task, strategy))
            if "success" not in measured:
                raise ValueError("runner must report task success")
            row = {"task": task, "strategy": strategy, **measured}
            task_rows.append(row)
        baseline_tokens = task_rows[0].get("input_tokens")
        for row in task_rows:
            tokens = row.get("input_tokens")
            row["input_tokens_saved_vs_baseline"] = (
                baseline_tokens - tokens
                if isinstance(tokens, int) and isinstance(baseline_tokens, int)
                else None
            )
        rows.extend(task_rows)
    return rows
