#!/usr/bin/env python3
"""Redact sensitive values from bounded text or JSON input."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


MAX_INPUT_BYTES = 1_000_000
REDACTED = "[REDACTED]"
SENSITIVE_KEY = re.compile(
    r"(api[-_]?key|authorization|cookie|password|passwd|secret|token)",
    re.IGNORECASE,
)
TEXT_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._~+/=-]+"),
    re.compile(
        r"(?i)\b(api[-_]?key|password|passwd|secret|token)\b"
        r"(\s*[:=]\s*)"
        r"([^\s,;\"']+)"
    ),
)


def redact_value(value: Any, key: str = "") -> Any:
    if SENSITIVE_KEY.search(key):
        return REDACTED
    if isinstance(value, dict):
        return {str(k): redact_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(item, key) for item in value]
    if isinstance(value, tuple):
        return [redact_value(item, key) for item in value]
    if isinstance(value, str):
        return redact_text(value)
    return value


def redact_text(text: str) -> str:
    result = TEXT_PATTERNS[0].sub(r"\1" + REDACTED, text)
    result = TEXT_PATTERNS[1].sub(r"\1\2" + REDACTED, result)
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Redact likely credentials without reading environment variables."
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="parse stdin as JSON and redact recursively",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
    if len(raw) > MAX_INPUT_BYTES:
        print("error: input exceeds 1000000 bytes", file=sys.stderr)
        return 2
    text = raw.decode("utf-8", errors="replace")
    if args.json:
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            print(f"error: invalid JSON: {exc}", file=sys.stderr)
            return 2
        print(json.dumps(redact_value(value), ensure_ascii=False, sort_keys=True))
    else:
        sys.stdout.write(redact_text(text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
