from pathlib import Path

from jevsweep.receipts import ReceiptStore
from jevsweep.rules import RuleBasedPruner


def test_rules_remove_only_repeated_progress_and_recover_exactly(
    tmp_path: Path,
) -> None:
    store = ReceiptStore(tmp_path)
    output = (
        "start\r\n"
        + "".join(f"progress step {i}\r\n" for i in range(50))
        + "Tests: 8 passed\r\n"
    )
    result = RuleBasedPruner(store, minimum_savings=10).prune(output)
    assert "Tests: 8 passed" in result
    assert "progress step 9" not in result
    receipt = result.split("receipt=", 1)[1].split("]", 1)[0]
    assert store.read(receipt) == output


def test_rules_preserve_small_and_diagnostic_output(tmp_path: Path) -> None:
    pruner = RuleBasedPruner(ReceiptStore(tmp_path))
    output = "Traceback (most recent call last):\n" + "progress step 1\n" * 50
    assert pruner.prune(output) == output
