# Architecture

JevSweep runs at the tool-result boundary, before a coding model receives the result. The Claude Code `PostToolUse` hook can replace successful Bash stdout automatically. In Codex, the agent must choose the installed command wrapper; direct tool calls are not intercepted. Both call the same Python `OutputPruner`.

```text
tool result -> save exact receipt -> eligibility gate -> protected chunks
            -> Jev relevance scores -> filtered result -> coding model
```

The pruner skips small, binary, structured, and long-line outputs. It protects diagnostics and final results, keeps chunks Jev cannot score, and returns the original on any scoring failure. A minimum-savings threshold is enforced inside `OutputPruner`, so session metrics reflect the text actually delivered. The local estimator gates pruning and measures injected tool output; the paired benchmark uses provider-reported usage for coding-model tokens and Jev usage separately.

| Module | Purpose |
| --- | --- |
| [`filtering.py`](../src/jevsweep/filtering.py) | Chunking, safety rules, Jev decisions, session metrics |
| [`jev.py`](../src/jevsweep/jev.py) | Bounded Jev requests and usage |
| [`receipts.py`](../src/jevsweep/receipts.py) | Exact original storage and recovery |
| [`middleware.py`](../src/jevsweep/middleware.py) | Host tool-result boundary |
| [`integrations.py`](../src/jevsweep/integrations.py) | Claude hook and Codex command wrapper |
| [`cli.py`](../src/jevsweep/cli.py) | Manual prune and recovery commands |

The default benchmark compares only baseline and live pruning on the same ten issues. Historical benchmark data remains under [`benchmarks/results`](../benchmarks/results/); retired research notes remain under [`docs/history`](history/).
