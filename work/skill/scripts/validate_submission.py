#!/usr/bin/env python3
"""Validate final output directories, reports, and trace chains."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from validate_layout import validate
from verify_trace import verify


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
FINAL_FILES = (
    "result/run_manifest.json",
    "result/project_profile.md",
    "result/output.md",
)
FINAL_DIRS = (
    "result/artifacts/generated_tests",
    "result/artifacts/reproduction",
    "result/artifacts/evidence",
)


def validate_submission(root: Path) -> list[str]:
    root = root.resolve()
    errors = validate(root)
    for relative in FINAL_FILES:
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty final file: {relative}")
    for relative in FINAL_DIRS:
        if not (root / relative).is_dir():
            errors.append(f"missing final directory: {relative}")
    traces = sorted((root / "logs/trace").glob("*.jsonl"))
    if not traces:
        errors.append("no JSONL trace found in logs/trace")
    for trace in traces:
        valid, message = verify(trace)
        if not valid:
            errors.append(f"invalid trace {trace.name}: {message}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    errors = validate_submission(args.root)
    if errors:
        print("Submission validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Submission validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
