#!/usr/bin/env python3
"""Prepare one independent run and write its strategy manifest."""

from __future__ import annotations

import argparse
import json
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from init_artifacts import initialize


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
STRATEGIES = (
    "input-and-parsing",
    "authorization-and-ownership",
    "state-and-workflow",
    "data-integrity-and-failure-paths",
    "file-and-injection-surfaces",
    "configuration-and-integration",
)
RESET_DIRS = (
    "result/artifacts/generated_tests",
    "result/artifacts/reproduction",
    "result/artifacts/evidence",
)
RESET_FILES = (
    "result/project_profile.md",
    "result/output.md",
    "result/run_manifest.json",
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--run-id", help="optional stable run identifier")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="remove only prior generated result artifacts and trace JSONL files",
    )
    parser.add_argument("--candidate-budget", type=int, default=8)
    parser.add_argument("--test-budget", type=int, default=30)
    parser.add_argument("--command-timeout-seconds", type=int, default=120)
    return parser


def _validate_budget(name: str, value: int, minimum: int, maximum: int) -> None:
    if not minimum <= value <= maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")


def prepare(
    root: Path,
    *,
    run_id: Optional[str],
    reset: bool,
    candidate_budget: int,
    test_budget: int,
    command_timeout_seconds: int,
) -> dict:
    root = root.resolve()
    _validate_budget("candidate-budget", candidate_budget, 1, 50)
    _validate_budget("test-budget", test_budget, 1, 200)
    _validate_budget("command-timeout-seconds", command_timeout_seconds, 1, 1800)

    if reset:
        for relative in RESET_DIRS:
            path = (root / relative).resolve()
            if root / "code" in path.parents or path == root / "code":
                raise ValueError("refusing to reset code/")
            if path.exists():
                shutil.rmtree(path)
        for relative in RESET_FILES:
            path = root / relative
            if path.exists():
                path.unlink()
        trace_dir = root / "logs/trace"
        if trace_dir.is_dir():
            for trace in trace_dir.glob("*.jsonl"):
                trace.unlink()
        interaction = root / "logs/interaction.md"
        interaction.parent.mkdir(parents=True, exist_ok=True)
        interaction.write_bytes(b"")

    initialize(root, with_templates=True)
    manifest = {
        "run_id": run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "independent_run": True,
        "minimum_strategy_families": 3,
        "strategy_portfolio": list(STRATEGIES),
        "selected_strategies": [],
        "candidate_budget": candidate_budget,
        "test_budget": test_budget,
        "command_timeout_seconds": command_timeout_seconds,
        "fallback_levels": [
            "full-system",
            "existing-tests",
            "subproject-or-module",
            "public-callable-surface",
            "isolated-local-harness",
            "pure-logic-verification",
            "static-only-candidate",
        ],
        "notes": [
            "The Agent must select at least three relevant strategies.",
            "This run must not inherit findings or generated tests from another run.",
        ],
    }
    output = root / "result/run_manifest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    args = build_parser().parse_args()
    try:
        manifest = prepare(
            args.root,
            run_id=args.run_id,
            reset=args.reset,
            candidate_budget=args.candidate_budget,
            test_budget=args.test_budget,
            command_timeout_seconds=args.command_timeout_seconds,
        )
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 1
    print(f"run_id={manifest['run_id']}")
    print("result/run_manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
