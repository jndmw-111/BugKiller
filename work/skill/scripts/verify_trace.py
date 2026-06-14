#!/usr/bin/env python3
"""Verify sequence ordering and SHA-256 links in one trace."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
ZERO_HASH = "0" * 64


def canonical(value: dict[str, Any]) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def verify(path: Path) -> tuple[bool, str]:
    if not path.is_file():
        return False, "trace file does not exist"
    if path.stat().st_size > 10_000_000:
        return False, "trace exceeds 10000000 bytes"
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return False, "trace is empty"
    previous = ZERO_HASH
    for expected_sequence, line in enumerate(lines, start=1):
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            return False, f"line {expected_sequence}: invalid JSON: {exc}"
        current_hash = event.pop("current_hash", None)
        if event.get("sequence") != expected_sequence:
            return False, f"line {expected_sequence}: non-contiguous sequence"
        if event.get("previous_hash") != previous:
            return False, f"line {expected_sequence}: previous_hash mismatch"
        calculated = hashlib.sha256(canonical(event)).hexdigest()
        if current_hash != calculated:
            return False, f"line {expected_sequence}: current_hash mismatch"
        previous = current_hash
    return True, f"{len(lines)} events verified"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trace", type=Path, help="trace path relative to root")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    if args.trace.is_absolute():
        print("FAIL: trace path must be relative to project root")
        return 2
    path = (root / args.trace).resolve()
    trace_root = (root / "logs/trace").resolve()
    if path.parent != trace_root:
        print("FAIL: trace must be inside logs/trace/")
        return 2
    valid, message = verify(path)
    print(("PASS: " if valid else "FAIL: ") + message)
    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
