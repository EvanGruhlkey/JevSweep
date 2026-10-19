from __future__ import annotations

import io
import json
import sys
from pathlib import Path

from contextlens import integrations
from contextlens.filtering import PruneConfig
from contextlens.install import install_claude, install_codex
from contextlens.models import estimate_tokens
from contextlens.receipts import ReceiptStore
from tests.test_filtering import FakeJudge, noise


def test_claude_hook_replaces_only_stdout_before_delivery(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        integrations,
        "_filter",
        lambda task, output, tool, arguments: "filtered receipt=cl_" + "a" * 24,
    )
    response = {"stdout": noise(), "stderr": "", "interrupted": False}
    payload = {
        "tool_name": "Bash",
        "tool_input": {"command": "rg needle ."},
        "tool_response": response,
    }
    replacement = integrations.claude_hook(payload, task="find needle")
    assert replacement is not None
    delivered = replacement["hookSpecificOutput"]["updatedToolOutput"]
    assert delivered["stdout"] != response["stdout"]
    assert delivered["stderr"] == response["stderr"]
    assert (
        integrations.claude_hook(
            {**payload, "tool_response": {**response, "stderr": "ERROR"}}, task="t"
        )
        is None
    )
    assert integrations.claude_hook({**payload, "tool_name": "Write"}, task="t") is None


def test_claude_hook_uses_current_session_task_without_env(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("JEVSWEEP_TASK", raising=False)
    transcript = tmp_path / "session.jsonl"
    entries = [
        {"type": "user", "message": {"content": "Fix the parser bug"}},
        {
            "type": "user",
            "message": {"content": [{"type": "tool_result", "content": "noise"}]},
        },
        {
            "type": "user",
            "message": {"content": [{"type": "text", "text": "Check tests too"}]},
        },
    ]
    transcript.write_text(
        "\n".join(json.dumps(entry) for entry in entries), encoding="utf-8"
    )
    seen: list[str] = []

    def filter_result(task, output, tool, arguments):
        seen.append(task)
        return "filtered"

    monkeypatch.setattr(integrations, "_filter", filter_result)
    payload = {
        "transcript_path": str(transcript),
        "tool_name": "Bash",
        "tool_input": {"command": "rg parser ."},
        "tool_response": {"stdout": "raw", "stderr": ""},
    }
    assert integrations.claude_hook(payload, task=integrations.claude_task(payload))
    assert seen == ["Fix the parser bug\nCheck tests too"]
    stdin = io.StringIO(json.dumps(payload))
    stdout = io.StringIO()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)
    assert integrations.claude_main() == 0
    assert (
        json.loads(stdout.getvalue())["hookSpecificOutput"]["updatedToolOutput"][
            "stdout"
        ]
        == "filtered"
    )
    assert (
        integrations.claude_task({"transcript_path": str(tmp_path / "missing")}) == ""
    )


def test_codex_wrapper_prints_only_filtered_output(tmp_path: Path, monkeypatch) -> None:
    stream = io.BytesIO()
    monkeypatch.setattr(sys, "stdout", type("Output", (), {"buffer": stream})())
    monkeypatch.setattr(sys, "stderr", type("Output", (), {"buffer": io.BytesIO()})())
    monkeypatch.setattr(integrations, "_filter", lambda *args: "filtered")
    assert (
        integrations.codex_main(
            ["--task", "fix bug", "--", sys.executable, "-c", "print('raw')"]
        )
        == 0
    )
    assert stream.getvalue() == b"filtered"


def test_exact_recovery_and_metrics_for_bypass_and_prune(tmp_path: Path) -> None:
    from contextlens.filtering import PruneSession
    from contextlens.middleware import ToolResultMiddleware

    store = ReceiptStore(tmp_path)
    raw = noise()
    session = PruneSession(
        store,
        task="fix bug",
        judge=FakeJudge(0.0),
        config=PruneConfig(minimum_tokens=0, minimum_savings_tokens=100),
    )
    middleware = ToolResultMiddleware(session)
    assert middleware.process("shell", {}, "short") == "short"
    filtered = middleware.process("shell", {"command": "echo"}, raw)
    assert filtered != raw
    assert store.read(session.outcomes[1].receipt_id) == raw
    metrics = session.metrics()
    assert metrics["raw_tool_output_tokens"] == estimate_tokens(
        "short"
    ) + estimate_tokens(raw)
    assert metrics["injected_tool_output_tokens"] == estimate_tokens(
        "short"
    ) + estimate_tokens(filtered)


def test_minimum_savings_bypass_reports_zero_savings(tmp_path: Path) -> None:
    from contextlens.filtering import PruneSession
    from contextlens.middleware import ToolResultMiddleware

    lines = noise().splitlines()
    for index in range(20, len(lines), 40):
        lines[index] = "WARNING: important diagnostic"
    raw = "\n".join(lines)
    session = PruneSession(
        ReceiptStore(tmp_path),
        task="fix bug",
        judge=FakeJudge(0.0),
        config=PruneConfig(minimum_tokens=0, minimum_savings_tokens=3000),
    )
    delivered = ToolResultMiddleware(session).process("shell", {}, raw)
    assert delivered == raw
    assert session.outcomes[0].reason == "below_minimum_savings"
    assert session.metrics()["tool_output_tokens_removed"] == 0
    assert session.outcomes[0].retained_tokens == session.outcomes[0].original_tokens


def test_installers_preserve_existing_claude_hooks(tmp_path: Path) -> None:
    path = tmp_path / ".claude" / "settings.local.json"
    path.parent.mkdir()
    path.write_text(
        json.dumps({"hooks": {"PostToolUse": [{"matcher": "Read", "hooks": []}]}}),
        encoding="utf-8",
    )
    install_claude(tmp_path)
    install_claude(tmp_path)
    entries = json.loads(path.read_text(encoding="utf-8"))["hooks"]["PostToolUse"]
    assert len(entries) == 2
    assert entries[0]["matcher"] == "Read"
    assert "jevsweep-run" in install_codex(tmp_path).read_text(encoding="utf-8")
