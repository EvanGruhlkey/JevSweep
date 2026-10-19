"""Small adapters for Claude Code hooks and explicitly wrapped Codex commands."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from contextlens.filtering import PruneSession
from contextlens.middleware import ToolResultMiddleware
from contextlens.receipts import ReceiptStore

TRANSCRIPT_TAIL_BYTES = 512_000


def _filter(task: str, output: str, tool: str, arguments: Mapping[str, Any]) -> str:
    session = PruneSession(
        ReceiptStore(
            Path(os.environ.get("JEVSWEEP_RECEIPTS", ".contextlens/receipts"))
        ),
        task=task,
    )
    result = ToolResultMiddleware(session).process(tool, arguments, output)
    return result if isinstance(result, str) else output


def claude_hook(payload: Mapping[str, Any], *, task: str) -> dict[str, Any] | None:
    """Return Claude's replacement payload for a successful Bash stdout."""

    response = payload.get("tool_response")
    if payload.get("tool_name") != "Bash" or not isinstance(response, dict):
        return None
    if response.get("stderr") or response.get("interrupted"):
        return None
    if response.get("exitCode", response.get("exit_code", 0)) != 0:
        return None
    stdout = response.get("stdout")
    arguments = payload.get("tool_input")
    if not isinstance(stdout, str) or not isinstance(arguments, dict):
        return None
    filtered = _filter(task, stdout, "shell", arguments)
    if filtered == stdout:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "updatedToolOutput": {**response, "stdout": filtered},
        }
    }


def claude_task(payload: Mapping[str, Any]) -> str:
    """Read recent user text from Claude's session transcript, or fail open."""

    override = os.environ.get("JEVSWEEP_TASK", "").strip()
    if override:
        return override[:2000]
    name = payload.get("transcript_path")
    if not isinstance(name, str) or not name:
        return ""
    try:
        with Path(name).expanduser().open("rb") as transcript:
            transcript.seek(0, 2)
            transcript.seek(max(0, transcript.tell() - TRANSCRIPT_TAIL_BYTES))
            tail = transcript.read().decode("utf-8", errors="ignore")
    except OSError:
        return ""
    prompts: list[str] = []
    for line in reversed(tail.splitlines()):
        try:
            entry = json.loads(line)
        except (ValueError, TypeError):
            continue
        if not isinstance(entry, dict) or entry.get("type") != "user":
            continue
        if entry.get("isMeta") or entry.get("isSidechain"):
            continue
        message = entry.get("message")
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            prompt = content
        elif isinstance(content, list):
            prompt = "\n".join(
                block["text"]
                for block in content
                if isinstance(block, dict)
                and block.get("type") == "text"
                and isinstance(block.get("text"), str)
            )
        else:
            continue
        if prompt.strip():
            prompts.append(prompt.strip())
        if len(prompts) == 3:
            break
    return "\n".join(reversed(prompts))[-2000:]


def claude_main() -> int:
    """Claude Code calls this after Bash; empty stdout means keep its original."""

    try:
        payload = json.load(sys.stdin)
        if isinstance(payload, dict):
            task = claude_task(payload)
            if task:
                replacement = claude_hook(payload, task=task)
                if replacement is not None:
                    sys.stdout.write(json.dumps(replacement))
    except Exception:
        # A broken adapter cannot block the coding agent or hide a result.
        return 0
    return 0


def codex_main(argv: Sequence[str] | None = None) -> int:
    """Run a command, then print only the filtered stdout to the agent."""

    parser = argparse.ArgumentParser(prog="jevsweep-run")
    parser.add_argument("--task", required=True)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command:
        parser.error("a command is required after --")
    try:
        completed = subprocess.run(command, capture_output=True)
    except OSError as error:
        print(f"jevsweep-run: {error}", file=sys.stderr)
        return 127
    output = completed.stdout
    if completed.returncode == 0 and not completed.stderr:
        try:
            decoded = output.decode("utf-8")
            filtered = _filter(
                args.task, decoded, "shell", {"command": " ".join(command)}
            )
            output = filtered.encode("utf-8")
        except Exception:
            pass
    sys.stdout.buffer.write(output)
    sys.stderr.buffer.write(completed.stderr)
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(codex_main())
