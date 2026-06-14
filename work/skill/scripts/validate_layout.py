#!/usr/bin/env python3
"""Validate the static competition submission layout."""

from __future__ import annotations

import argparse
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
REQUIRED_FILES = (
    "INSTRUCTION.md",
    "work/skill/SKILL.md",
    "work/skill/agents/openai.yaml",
    "result/output.md",
    "logs/interaction.md",
    "work/skill/references/strategy-portfolio.md",
    "work/skill/references/system-profiles.md",
    "work/skill/references/execution-fallback.md",
    "work/skill/references/runtime-quality.md",
    "work/skill/scripts/prepare_run.py",
    "work/skill/scripts/quality_tools.py",
    "work/skill/scripts/source_snapshot.py",
)
REQUIRED_DIRS = (
    "code",
    "work",
    "work/skill/references",
    "work/skill/scripts",
    "work/templates",
    "work/tests",
    "work/docs",
    "result",
    "result/artifacts",
    "logs",
    "logs/trace",
)


def validate(root: Path) -> list[str]:
    root = root.resolve()
    errors = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"missing file: {relative}")
    for relative in REQUIRED_DIRS:
        if not (root / relative).is_dir():
            errors.append(f"missing directory: {relative}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    errors = validate(args.root)
    if errors:
        print("Layout validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Layout validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
