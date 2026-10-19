---
name: jevsweep
description: Use when running verbose read-only shell commands during coding tasks;
  wrap the command so low-value stdout is filtered before Codex receives it.
---

# JevSweep command wrapper

For verbose read-only commands such as searches, file reads, and test discovery, run:

```text
jevsweep-run --task "the current coding task" -- rg pattern src
```

The wrapper captures the command output, saves a receipt, and sends only its filtered stdout to Codex. It preserves stderr and exit status. Use ordinary commands for edits, interactive tools, and short output. If a receipt marker appears, recover its complete original with `contextlens recover RECEIPT_ID`. This skill guides explicit wrapper use; it cannot intercept Codex commands run without the wrapper.
