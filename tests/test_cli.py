from __future__ import annotations

import json
from pathlib import Path

import pytest

from jevsweep.cli import main
from jevsweep.receipts import ReceiptStore


def test_recover_writes_the_exact_original(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    store = ReceiptStore(tmp_path)
    receipt = store.save("alpha\nbeta\ngamma\n")
    assert main(["recover", receipt.receipt_id, "--receipts", str(tmp_path)]) == 0
    assert capsys.readouterr().out == "alpha\nbeta\ngamma\n"


def test_recover_supports_a_line_range(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    receipt = ReceiptStore(tmp_path).save("alpha\nbeta\ngamma\n")
    assert (
        main(
            [
                "recover",
                receipt.receipt_id,
                "--start-line",
                "2",
                "--end-line",
                "2",
                "--receipts",
                str(tmp_path),
            ]
        )
        == 0
    )
    assert capsys.readouterr().out == "beta\n"


def test_unknown_receipt_reports_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["recover", "js_" + "0" * 24, "--receipts", str(tmp_path)]) == 2
    assert "jevsweep:" in capsys.readouterr().err


def test_prune_fails_open_without_credentials(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("AI_GATEWAY_API_KEY", raising=False)
    monkeypatch.setenv("JEVSWEEP_MIN_TOKENS", "10")
    source = tmp_path / "output.txt"
    output = "\n".join(f"progress line {index}" for index in range(400))
    source.write_text(output, encoding="utf-8")
    assert (
        main(
            [
                "prune",
                "--task",
                "fix the parser",
                "--input",
                str(source),
                "--receipts",
                str(tmp_path / "receipts"),
                "--json",
            ]
        )
        == 0
    )
    payload = json.loads(capsys.readouterr().out)
    assert payload["text"] == output
    assert payload["reason"] == "jev_unavailable"
    assert payload["receipt_id"]


def test_help_lists_only_supported_commands(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        main(["--help"])
    assert error.value.code == 0
    output = capsys.readouterr().out
    assert "prune" in output and "recover" in output
    assert "compact" not in output and "mcp" not in output
