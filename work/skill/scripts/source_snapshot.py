#!/usr/bin/env python3
"""Create or verify a bounded content snapshot of the read-only source tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MAX_FILES = 20_000
DEFAULT_MAX_BYTES = 512_000_000


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _resolve(root: Path, relative: Path, label: str) -> Path:
    if relative.is_absolute():
        raise ValueError(f"{label} must be relative to project root")
    path = (root / relative).resolve()
    if not _inside(path, root):
        raise ValueError(f"{label} escapes project root")
    return path


def snapshot(
    root: Path,
    source_relative: Path,
    *,
    max_files: int,
    max_bytes: int,
) -> dict[str, Any]:
    root = root.resolve()
    source = _resolve(root, source_relative, "source")
    if not source.is_dir():
        raise FileNotFoundError(f"source directory does not exist: {source_relative}")
    if not any(source.iterdir()):
        raise FileNotFoundError(f"source directory is empty: {source_relative}")
    if not 1 <= max_files <= 100_000:
        raise ValueError("max-files must be between 1 and 100000")
    if not 1 <= max_bytes <= 2_000_000_000:
        raise ValueError("max-bytes must be between 1 and 2000000000")

    files: dict[str, dict[str, Any]] = {}
    total_bytes = 0
    for current, directories, filenames in os.walk(source, followlinks=False):
        directories.sort()
        filenames.sort()
        for filename in filenames:
            path = Path(current) / filename
            relative = path.relative_to(source).as_posix()
            if len(files) >= max_files:
                raise ValueError("source exceeds max-files; integrity snapshot incomplete")
            if path.is_symlink():
                files[relative] = {
                    "type": "symlink",
                    "target": os.readlink(path),
                }
                continue
            size = path.stat().st_size
            total_bytes += size
            if total_bytes > max_bytes:
                raise ValueError("source exceeds max-bytes; integrity snapshot incomplete")
            digest = hashlib.sha256()
            with path.open("rb") as handle:
                while True:
                    chunk = handle.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
            files[relative] = {
                "type": "file",
                "size": size,
                "sha256": digest.hexdigest(),
            }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source_relative.as_posix(),
        "file_count": len(files),
        "total_bytes": total_bytes,
        "files": files,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for name in ("create", "verify"):
        command = subparsers.add_parser(name)
        command.add_argument("--root", type=Path, default=DEFAULT_ROOT)
        command.add_argument("--source", type=Path, default=Path("code"))
        command.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
        command.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
        command.add_argument(
            "--output" if name == "create" else "--snapshot",
            type=Path,
            required=True,
        )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    try:
        current = snapshot(
            root,
            args.source,
            max_files=args.max_files,
            max_bytes=args.max_bytes,
        )
        relative = args.output if args.command == "create" else args.snapshot
        saved_path = _resolve(root, relative, "snapshot")
        code = (root / "code").resolve()
        if _inside(saved_path, code):
            raise ValueError("snapshot must not be written inside code/")
        if args.command == "create":
            encoded = json.dumps(current, ensure_ascii=False, indent=2) + "\n"
            if len(encoded.encode("utf-8")) > 20_000_000:
                raise ValueError("snapshot output exceeds 20000000 bytes")
            saved_path.parent.mkdir(parents=True, exist_ok=True)
            saved_path.write_text(encoded, encoding="utf-8")
            print(relative.as_posix())
            return 0

        expected = json.loads(saved_path.read_text(encoding="utf-8"))
        expected_comparable = dict(expected)
        current_comparable = dict(current)
        expected_comparable.pop("generated_at", None)
        current_comparable.pop("generated_at", None)
        if expected_comparable != current_comparable:
            before = expected.get("files", {})
            after = current.get("files", {})
            added = sorted(set(after) - set(before))[:20]
            removed = sorted(set(before) - set(after))[:20]
            changed = sorted(
                key for key in set(before) & set(after) if before[key] != after[key]
            )[:20]
            print(
                "FAIL: source changed "
                f"added={added} removed={removed} changed={changed}"
            )
            return 1
        print(
            f"PASS: source unchanged files={current['file_count']} "
            f"bytes={current['total_bytes']}"
        )
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
