# JevSweep

JevSweep is a Python context layer for coding agents. The agent host installs
`ToolResultMiddleware` around tool results, before those results enter the
coding model's next request. Large text results are saved locally, split into
chunks, and scored by Jev against the current coding task. Diagnostic chunks,
relevant chunks, and chunks Jev could not score stay visible. Omitted chunks
carry a receipt handle that restores the exact original output. Small,
structured, or unsafe results pass through; Jev failure also returns the
original. Jev scores relevance only and never chooses agent actions.

## Install and integrate

```bash
python -m pip install -e .
export AI_GATEWAY_API_KEY="..."  # Vercel AI Gateway access to Jev
```

Register wrapped tools in a coding agent's host dispatcher. The wrapper takes
the tool's argument mapping and returns the text the model should receive:

```python
from pathlib import Path
from contextlens import PruneSession, ReceiptStore, ToolResultMiddleware

receipts = ReceiptStore(Path(".contextlens/receipts"))
session = PruneSession(receipts, task="fix the failing parser test")
middleware = ToolResultMiddleware(session)
tools["read_file"] = middleware.wrap("read_file", tools["read_file"])
tools["shell"] = middleware.wrap("shell", tools["shell"])
```

The host must call the wrapped functions and append **their returned text** to
model context. `benchmarks/agent.py` is a working host integration: it runs
the middleware after tool execution and before constructing the next model
request. The default gate skips short output and requires a minimum estimated
reduction before returning a pruned result, avoiding many unproductive Jev
calls. Tune that gate against measured Jev cost and latency for your setup.

To recover an omission, call `ReceiptStore.read(receipt_id)` or:

```bash
contextlens recover cl_RECEIPT_ID --receipts .contextlens/receipts
```

## Evaluate on coding tasks

The default benchmark runs **baseline** and **JevSweep live pruning** on the
same ten pinned GitHub issues, model, prompts, tools, turn limit, and hidden
graders. It records verified fixes, raw and injected tool-output tokens,
uncached coding-model input tokens, Jev requests and usage, Jev cost, and wall
time. Coding-model token counts come from provider usage; no missing usage is
inferred from prompt length. A new run needs coding-model and Jev credentials:

```bash
python -m pip install -e ".[dev]"
export OPENAI_API_KEY="..."
export AI_GATEWAY_API_KEY="..."
python -m benchmarks.run --output benchmarks/artifacts/new-run --trials 1 --timeout 300
```

The [historical September 2026 run](benchmarks/results/four-condition-2026-09-21-tuned.md)
reported 5/10 verified fixes in both baseline and JevSweep, 36.2% fewer
injected tool-output tokens, and 24.8% fewer uncached coding-model input
tokens. It measured the earlier four-condition implementation. **Those
percentages have not been reproduced by this simplified default workflow.**
Historical reports remain under [benchmarks/results](benchmarks/results).
The offline fixture check runs without credentials, but does not measure
coding-model task success.

Transcript compaction and the simple rules filter remain in the repository as
optional experiments. Neither runs in the default coding-agent workflow or
the default paired benchmark.
