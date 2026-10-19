"""Lossless, conservative compaction of older tool observations."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from contextlens.pruning.model import ObservationKind, PruneRequest, estimate_tokens
from contextlens.pruning.receipts import ReceiptStore


def compact_transcript(
    messages: Sequence[Mapping[str, Any]],
    receipts: ReceiptStore,
    *,
    keep_recent: int = 8,
    minimum_tokens: int = 256,
) -> list[dict[str, Any]]:
    """Replace only old, ordinary tool reads with exact recovery markers."""
    if keep_recent < 0:
        raise ValueError("keep_recent cannot be negative")
    cutoff = max(0, len(messages) - keep_recent)
    output: list[dict[str, Any]] = []
    for index, message in enumerate(messages):
        item = dict(message)
        content = item.get("content")
        if (
            index >= cutoff
            or item.get("role") != "tool"
            or not isinstance(content, str)
            or estimate_tokens(content) < minimum_tokens
            or any(
                word in content.lower()
                for word in (
                    "error",
                    "fail",
                    "traceback",
                    "git diff",
                    "diff --git",
                    "modified",
                    "created",
                    "deleted",
                    "test",
                    "patch",
                    "commit",
                )
            )
        ):
            output.append(item)
            continue
        original = json.dumps(item, ensure_ascii=False, separators=(",", ":"))
        receipt = receipts.save(
            PruneRequest(
                task="transcript recovery", content=original, kind=ObservationKind.TEXT
            )
        )
        marker = f"[ContextLens omitted tool message; recover {receipt.receipt_id}]"
        if estimate_tokens(marker) >= estimate_tokens(content):
            output.append(item)
            continue
        item["content"] = marker
        output.append(item)
    return output


def recover_message(
    message: Mapping[str, Any], receipts: ReceiptStore
) -> dict[str, Any]:
    content = message.get("content")
    if not isinstance(content, str) or not content.startswith(
        "[ContextLens omitted tool message; recover cl_"
    ):
        return dict(message)
    receipt_id = content.removeprefix(
        "[ContextLens omitted tool message; recover "
    ).removesuffix("]")
    return json.loads(receipts.read(receipt_id))
