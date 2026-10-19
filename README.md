# JevSweep

JevSweep saves each eligible tool result locally, splits large text into chunks, and asks Jev which chunks matter to the current coding task. The existing Python `OutputPruner` keeps diagnostics, results, uncertain chunks, and anything Jev cannot score. It replaces low-value chunks with receipt markers; `contextlens recover RECEIPT_ID` restores the exact original. Small, structured, binary, and failing command output passes through. A minimum estimated saving gate avoids most unproductive Jev calls. Jev scores relevance only; it never chooses coding-agent actions.

## Install

```bash
python -m pip install -e .
export AI_GATEWAY_API_KEY="..."  # Vercel AI Gateway access to Jev
```

### Claude Code

```bash
jevsweep-install claude --path /path/to/your/project
export JEVSWEEP_TASK="fix the parser's failing test"
cd /path/to/your/project && claude
```

On PowerShell, set the task with `$env:JEVSWEEP_TASK = "fix the parser's failing test"`. The installer merges a `PostToolUse` Bash hook into `.claude/settings.local.json`. For successful Bash calls, the hook replaces `stdout` in the tool result **before Claude reads it**. It preserves stderr and failures, and returns the original on any filter error. Claude's [hook contract](https://code.claude.com/docs/en/hooks) supports `updatedToolOutput` for this replacement. The task variable must describe the current task; if absent, the hook passes output through. This adapter currently covers Bash stdout only.

### Codex

```bash
jevsweep-install codex --path /path/to/your/project
cd /path/to/your/project && codex
```

Invoke the installed `$jevsweep` skill, or run verbose commands through the wrapper:

```bash
jevsweep-run --task "fix the parser's failing test" -- rg parser src tests
```

The wrapper captures command output, filters it, then prints only the delivered result to Codex. Stderr and nonzero exit status remain intact. **Codex commands run directly are not intercepted.** A skill can guide wrapper use but cannot guarantee transparent interception of every tool call; see [Codex skills](https://learn.chatgpt.com/docs/build-skills). Use `contextlens recover RECEIPT_ID` to inspect omitted content. Receipts default to `.contextlens/receipts`; set `JEVSWEEP_RECEIPTS` to change the path.

Hosts with their own tool dispatcher can use `ToolResultMiddleware(PruneSession(...)).wrap(...)` around text tools before appending returned results to the coding model's request. `benchmarks/agent.py` demonstrates this boundary.

## Measure

The default paired benchmark compares baseline and JevSweep on the same ten pinned GitHub issues, prompts, model, tools, and hidden fix checks:

```bash
python -m pip install -e ".[dev]"
export OPENAI_API_KEY="..."
export AI_GATEWAY_API_KEY="..."
python -m benchmarks.run --output benchmarks/artifacts/new-run --trials 1 --timeout 300
```

The report separates **estimated** raw and injected tool-output tokens (fast local estimator), **actual provider-reported** coding-model input and uncached input tokens, Jev's own reported tokens and cost, verified fixes, and latency. Missing provider usage remains missing; it is never inferred. `python -m benchmarks.offline --output benchmarks/artifacts/offline.json` checks local plumbing without model credentials and does not measure coding-task success.

The [historical September 2026 report](benchmarks/results/four-condition-2026-09-21-tuned.md) found 5/10 verified fixes in both conditions, 36.2% fewer injected tool-output tokens, and 24.8% fewer uncached coding-model input tokens in an earlier implementation. **Those numbers are historical and have not been reproduced by this version.** Transcript compaction and rule filtering remain experimental code outside the default workflow.
