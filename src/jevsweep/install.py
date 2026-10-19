"""Install the supported agent entry points without replacing other settings."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SKILL = """---
name: jevsweep
description: Use when running verbose read-only shell commands during coding tasks;
  wrap the command so low-value stdout is filtered before Codex receives it.
---

# JevSweep command wrapper

For verbose read-only commands such as searches, file reads, and test discovery, run:

```text
jevsweep-run --task "the current coding task" -- rg pattern src
```

The wrapper captures command output, saves a receipt, and sends only filtered
stdout to Codex. It preserves stderr and exit status. Use ordinary commands
for edits, interactive tools, and short output. Recover a receipt with
`jevsweep recover RECEIPT_ID`. This skill guides explicit wrapper use;
it cannot intercept Codex commands run without the wrapper.
"""


def install_claude(project: Path) -> Path:
    path = project / ".claude" / "settings.local.json"
    settings: dict[str, Any] = (
        json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    )
    hooks = settings.setdefault("hooks", {})
    post = hooks.setdefault("PostToolUse", [])
    entry = {
        "matcher": "Bash",
        "hooks": [{"type": "command", "command": "jevsweep-claude-hook"}],
    }
    if entry not in post:
        post.append(entry)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    return path


def install_codex(home: Path) -> Path:
    path = home / ".agents" / "skills" / "jevsweep" / "SKILL.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SKILL, encoding="utf-8")
    return path


def main() -> int:
    parser = argparse.ArgumentParser(prog="jevsweep-install")
    parser.add_argument("platform", choices=("claude", "codex"))
    parser.add_argument("--path", type=Path, default=Path.cwd())
    args = parser.parse_args()
    path = (
        install_claude(args.path)
        if args.platform == "claude"
        else install_codex(args.path)
    )
    print(path)
    return 0
