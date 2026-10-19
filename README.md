# JevSweep

JevSweep reduces coding-agent input tokens by filtering verbose tool output before the model reads it. It saves the original locally, keeps important chunks, and uses Jev to identify low-value chunks. Omitted text is recoverable by receipt ID. Jev only scores relevance; it does not choose agent actions.

## Install

```bash
python -m pip install -e .
export AI_GATEWAY_API_KEY="..."
```

## Use

### Claude Code

```bash
jevsweep-install claude --path /path/to/project
export JEVSWEEP_TASK="fix the failing parser test"
cd /path/to/project && claude
```

The `PostToolUse` hook filters successful Bash stdout before Claude reads it. It passes through errors and unhandled results. Set `JEVSWEEP_TASK` for each task. On PowerShell, use `$env:JEVSWEEP_TASK = "fix the failing parser test"`.

### Codex

```bash
jevsweep-install codex --path /path/to/project
jevsweep-run --task "fix the failing parser test" -- rg parser src tests
```

The installed `$jevsweep` skill guides Codex to use the wrapper. **Only wrapped commands are filtered**; direct Codex tool calls are not intercepted.

Recover any omitted output with `contextlens recover RECEIPT_ID`. Receipts are stored in `.contextlens/receipts` by default.

## How it works

The Python `OutputPruner` saves the full result, skips small or unsuitable output, and protects diagnostics and final results. Jev scores the remaining chunks against the current task. Low-value chunks become receipt markers; uncertain chunks and Jev failures pass through. Claude's hook and the Codex wrapper both call this same engine. A coding-agent host can also wrap its tool dispatcher with `ToolResultMiddleware`.

## Evaluation

The paired benchmark compares baseline and JevSweep on ten pinned GitHub issues. It measures verified fixes, estimated injected tool-output tokens, provider-reported coding-model input tokens, Jev usage, and latency. Run it with coding-model and Jev credentials:

```bash
export OPENAI_API_KEY="..."
python -m benchmarks.run --output benchmarks/artifacts/new-run --trials 1 --timeout 300
```

`OPENAI_API_KEY` is for the benchmark's separate coding agent, **not** for Claude Code or Codex integration. The [historical September 2026 results](benchmarks/results/four-condition-2026-09-21-tuned.md) used an earlier implementation and are not claimed for this version. The offline harness (`python -m benchmarks.offline --output benchmarks/artifacts/offline.json`) tests filtering without measuring coding-task success.
