"""Command line entry point for pruning and exact receipt recovery."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from jevsweep.filtering import OutputPruner, PruneConfig, PruneRequest
from jevsweep.jev import JevGateway
from jevsweep.receipts import ReceiptStore

DEFAULT_RECEIPTS = Path(".jevsweep/receipts")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="jevsweep",
        description="Jev-based tool-output pruning for coding agents",
    )
    commands = parser.add_subparsers(dest="subcommand", required=True)

    prune = commands.add_parser(
        "prune", help="prune one large tool result before the coding model reads it"
    )
    prune.add_argument("--task", required=True)
    prune.add_argument("--focus", default="")
    prune.add_argument("--tool", default="tool")
    prune.add_argument("--path")
    prune.add_argument("--command")
    prune.add_argument(
        "--input", type=Path, help="tool output to read; stdin when omitted"
    )
    prune.add_argument("--receipts", type=Path, default=DEFAULT_RECEIPTS)
    prune.add_argument("--json", action="store_true")

    recover = commands.add_parser(
        "recover", help="recover exact omitted content by receipt handle"
    )
    recover.add_argument("receipt_id")
    recover.add_argument("--start-line", type=int)
    recover.add_argument("--end-line", type=int)
    recover.add_argument("--receipts", type=Path, default=DEFAULT_RECEIPTS)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        if arguments.subcommand == "prune":
            return _prune(arguments)
        if arguments.subcommand == "recover":
            sys.stdout.write(
                ReceiptStore(arguments.receipts).read(
                    arguments.receipt_id,
                    start_line=arguments.start_line,
                    end_line=arguments.end_line,
                )
            )
            return 0
        return 2
    except (KeyError, OSError, RuntimeError, ValueError) as error:
        print(f"jevsweep: {error}", file=sys.stderr)
        return 2


def _prune(arguments: argparse.Namespace) -> int:
    output = _read(arguments.input)
    tool_arguments: dict[str, Any] = {}
    if arguments.path:
        tool_arguments["path"] = arguments.path
    if arguments.command:
        tool_arguments["command"] = arguments.command
    outcome = OutputPruner(
        ReceiptStore(arguments.receipts),
        judge=JevGateway(),
        config=PruneConfig.from_env(),
    ).prune(
        PruneRequest(
            task=arguments.task,
            output=output,
            tool=arguments.tool,
            arguments=tool_arguments,
            focus=arguments.focus,
        )
    )
    if arguments.json:
        print(json.dumps({"text": outcome.text, **outcome.to_dict()}, indent=2))
    else:
        print(outcome.text)
    return 0


def _read(path: Path | None) -> str:
    return path.read_text(encoding="utf-8") if path is not None else sys.stdin.read()


if __name__ == "__main__":
    raise SystemExit(main())
