# Paired coding-agent benchmark

The default runner compares `baseline` and `live_pruning` on the same ten
pinned GitHub issues. Each attempt gets a fresh checkout, the same coding
model, task prompt, tools, time limit, turn limit, and hidden grader. The
agent never sees the context-layer setting. A preflight verifies each grader
fails before the gold fix and passes with it.

```bash
export OPENAI_API_KEY="..."
export AI_GATEWAY_API_KEY="..."
python -m pip install uv
python -m benchmarks.run --output benchmarks/artifacts/new-run --trials 1 --timeout 300
```

Each attempt stores its prompt, patch, verification, and usage record. The
report includes verified fixes, actual provider input and uncached input
tokens, raw and injected tool-output tokens, Jev requests and token usage,
Jev cost, and wall time. Missing provider usage is reported as unavailable.
Use `--case ID` to select a task or `--model` to change the coding model.

`python -m benchmarks.offline --output benchmarks/artifacts/offline.json`
checks the integration with a scripted solver and local relevance judge. It
does not measure coding-model task success.

[Historical benchmark reports](results/) are preserved. They used a different
set of conditions, including experimental transcript compaction; their
percentages are not new results for this simplified runner.
