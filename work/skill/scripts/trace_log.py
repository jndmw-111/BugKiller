#!/usr/bin/env python3
"""Append redacted events to a JSONL SHA-256 hash chain."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from redact import redact_value


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
ZERO_HASH = "0" * 64
MAX_FIELD_CHARS = 8000


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _bounded(value: str) -> str:
    return value[:MAX_FIELD_CHARS]


def _trace_path(root: Path, relative: Path) -> Path:
    if relative.is_absolute():
        raise ValueError("trace path must be relative to project root")
    path = (root / relative).resolve()
    trace_root = (root / "logs/trace").resolve()
    if path.parent != trace_root or path.suffix != ".jsonl":
        raise ValueError("trace must be logs/trace/<name>.jsonl")
    return path


def _last_event(path: Path) -> tuple[int, str]:
    if not path.exists() or path.stat().st_size == 0:
        return 0, ZERO_HASH
    if path.stat().st_size > 10_000_000:
        raise ValueError("trace exceeds 10000000 bytes")
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return 0, ZERO_HASH
    last = json.loads(lines[-1])
    sequence = last.get("sequence")
    current_hash = last.get("current_hash")
    if not isinstance(sequence, int) or not isinstance(current_hash, str):
        raise ValueError("existing trace has an invalid final event")
    return sequence, current_hash


def append_event(
    root: Path,
    trace_relative: Path,
    *,
    stage: str,
    operation: str,
    command: str,
    tool: str,
    input_summary: str,
    output_summary: str,
    status: str,
    evidence_path: str,
    decision_summary: str,
    strategy: str = "",
    fallback_level: str = "",
) -> dict[str, Any]:
    root = root.resolve()
    path = _trace_path(root, trace_relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    sequence, previous_hash = _last_event(path)
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "sequence": sequence + 1,
        "stage": _bounded(stage),
        "operation": _bounded(operation),
        "command": _bounded(command),
        "tool": _bounded(tool),
        "input_summary": _bounded(input_summary),
        "output_summary": _bounded(output_summary),
        "status": _bounded(status),
        "evidence_path": _bounded(evidence_path),
        "decision_summary": _bounded(decision_summary),
        "strategy": _bounded(strategy),
        "fallback_level": _bounded(fallback_level),
        "previous_hash": previous_hash,
    }
    event = redact_value(event)
    event["current_hash"] = hashlib.sha256(canonical(event)).hexdigest()
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return event


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)
    append = subparsers.add_parser("append", help="append one trace event")
    append.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    append.add_argument("--trace", type=Path, required=True)
    append.add_argument("--stage", required=True)
    append.add_argument("--operation", required=True)
    append.add_argument("--command", default="")
    append.add_argument("--tool", default="")
    append.add_argument("--input-summary", default="")
    append.add_argument("--output-summary", default="")
    append.add_argument("--status", required=True)
    append.add_argument("--evidence-path", default="")
    append.add_argument("--decision-summary", default="")
    append.add_argument("--strategy", default="")
    append.add_argument("--fallback-level", default="")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        event = append_event(
            args.root,
            args.trace,
            stage=args.stage,
            operation=args.operation,
            command=args.command,
            tool=args.tool,
            input_summary=args.input_summary,
            output_summary=args.output_summary,
            status=args.status,
            evidence_path=args.evidence_path,
            decision_summary=args.decision_summary,
            strategy=args.strategy,
            fallback_level=args.fallback_level,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 1
    print(f"sequence={event['sequence']} hash={event['current_hash']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
