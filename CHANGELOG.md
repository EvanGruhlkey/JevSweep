# Changelog

## Unreleased

- Renamed the Python distribution, import package, CLI, configuration variables, and current documentation to JevSweep.
- Added automatic Claude Code Bash result filtering and an explicit Codex command wrapper.
- Kept old `cl_` receipt handles readable; new receipts use `js_` handles.
- Removed transcript compaction, rule filtering, and MCP code from the supported package and default benchmark. Historical results remain under `benchmarks/results/` and `docs/history/`.
- Aligned pruning decisions and metrics with the output actually delivered to the coding model.

Earlier implementation history is available in Git history and [`docs/history/`](docs/history/).
