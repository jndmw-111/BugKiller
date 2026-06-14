#!/usr/bin/env python3
"""Initialize result artifact directories without touching code/."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
ARTIFACT_DIRS = (
    "result/artifacts/generated_tests",
    "result/artifacts/reproduction",
    "result/artifacts/evidence",
    "logs/trace",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create bounded result and trace directories."
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=DEFAULT_ROOT,
        help="project root, defaults to the repository containing this script",
    )
    parser.add_argument(
        "--with-templates",
        action="store_true",
        help="copy missing report templates into result/",
    )
    return parser


def initialize(root: Path, with_templates: bool = False) -> list[Path]:
    root = root.resolve()
    created: list[Path] = []
    code = root / "code"
    for relative in ARTIFACT_DIRS:
        path = (root / relative).resolve()
        if path == code or code in path.parents:
            raise ValueError("refusing to write inside code/")
        path.mkdir(parents=True, exist_ok=True)
        created.append(path)
    interaction = root / "logs/interaction.md"
    interaction.parent.mkdir(parents=True, exist_ok=True)
    if not interaction.exists():
        interaction.write_bytes(b"")
        created.append(interaction)
    if with_templates:
        mappings = (
            ("work/templates/project_profile.md", "result/project_profile.md"),
            ("work/templates/output.md", "result/output.md"),
        )
        for source_relative, target_relative in mappings:
            source = root / source_relative
            target = root / target_relative
            if source.is_file() and not target.exists():
                shutil.copyfile(source, target)
                created.append(target)
    return created


def main() -> int:
    args = build_parser().parse_args()
    try:
        created = initialize(args.root, args.with_templates)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 1
    for path in created:
        print(path.relative_to(args.root.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
