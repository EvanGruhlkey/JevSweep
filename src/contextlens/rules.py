"""Simple, receipt-backed pruning baseline for repeated progress output."""

from __future__ import annotations

import re

from contextlens.models import estimate_tokens
from contextlens.receipts import ReceiptStore

_PROGRESS = re.compile(r"^\s*(?:progress step \d+|\[\s*\d+%\])\s*$", re.I)


class RuleBasedPruner:
    """Drop repeated progress lines; leave other output untouched."""

    def __init__(self, receipts: ReceiptStore, *, minimum_savings: int = 128) -> None:
        self.receipts = receipts
        self.minimum_savings = minimum_savings

    def prune(self, output: str) -> str:
        if any(word in output.lower() for word in ("traceback", "error", "failed")):
            return output
        lines = output.splitlines(keepends=True)
        remove = [
            index
            for index, line in enumerate(lines)
            if _PROGRESS.fullmatch(line.strip())
        ]
        if len(remove) < 10:
            return output
        receipt = self.receipts.save(output, category="rules")
        removed = set(remove)
        retained = "".join(
            line for index, line in enumerate(lines) if index not in removed
        )
        marker = (
            f"[contextlens omitted {len(remove)} progress lines; "
            f"receipt={receipt.receipt_id}]\n"
        )
        rendered = retained + marker
        return (
            rendered
            if estimate_tokens(output) - estimate_tokens(rendered)
            >= self.minimum_savings
            else output
        )
