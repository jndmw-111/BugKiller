#!/usr/bin/env python3
"""Detect local test-quality tools and score normalized mutation results."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
MAX_JSON_BYTES = 1_000_000
MUTANT_STATUSES = {
    "killed",
    "survived",
    "invalid",
    "timeout",
    "not-covered",
    "blocked",
}


def _relative_path(root: Path, value: Path, *, output: bool = False) -> Path:
    if value.is_absolute():
        raise ValueError("paths must be relative to the project root")
    resolved = (root / value).resolve()
    if root != resolved and root not in resolved.parents:
        raise ValueError("path escapes the project root")
    if output and (root / "code").resolve() in (resolved, *resolved.parents):
        raise ValueError("refusing to write inside code/")
    return resolved


def _read_bounded(path: Path, limit: int = 262_144) -> str:
    if not path.is_file() or path.stat().st_size > limit:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _available(
    root: Path,
    executable: str,
    project_paths: tuple[str | Path, ...] = (),
) -> bool:
    if shutil.which(executable):
        return True
    return any((root / path).is_file() for path in project_paths)


def detect_tools(root: Path, source: Path, max_files: int) -> dict:
    root = root.resolve()
    source_root = _relative_path(root, source)
    if not source_root.is_dir():
        raise FileNotFoundError(f"source directory not found: {source}")
    if not 1 <= max_files <= 100_000:
        raise ValueError("max-files must be between 1 and 100000")

    suffix_languages = {
        ".py": "Python",
        ".js": "JavaScript",
        ".mjs": "JavaScript",
        ".cjs": "JavaScript",
        ".ts": "TypeScript",
        ".tsx": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".java": "Java",
        ".kt": "Kotlin",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".c": "C",
        ".cc": "C++",
        ".cpp": "C++",
        ".swift": "Swift",
    }
    languages: set[str] = set()
    files_scanned = 0
    truncated = False
    manifest_names = {
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "Cargo.toml",
        "composer.json",
        "Gemfile",
        "Directory.Build.props",
    }
    manifest_chunks = []
    manifest_bytes = 0
    gradle_wrapper_found = False
    for path in sorted(source_root.rglob("*")):
        if not path.is_file():
            continue
        files_scanned += 1
        if files_scanned > max_files:
            truncated = True
            break
        language = suffix_languages.get(path.suffix.lower())
        if language:
            languages.add(language)
        if path.name == "gradlew":
            gradle_wrapper_found = True
        if path.name in manifest_names and manifest_bytes < 524_288:
            text = _read_bounded(path, min(262_144, 524_288 - manifest_bytes))
            manifest_chunks.append(text)
            manifest_bytes += len(text.encode("utf-8"))

    manifest_text = "\n".join(manifest_chunks).lower()

    coverage_tools = [
        {
            "id": "python-coverage",
            "available": "Python" in languages and _available(root, "coverage"),
            "native": True,
            "detection": "coverage executable",
        },
        {
            "id": "python-stdlib-trace",
            "available": "Python" in languages,
            "native": True,
            "detection": "Python standard library fallback",
        },
        {
            "id": "node-v8-coverage",
            "available": bool(
                {"JavaScript", "TypeScript"} & languages
                and _available(root, "node")
            ),
            "native": True,
            "detection": "node executable",
        },
        {
            "id": "c8-or-nyc",
            "available": bool(
                {"JavaScript", "TypeScript"} & languages
                and (
                    _available(
                        root,
                        "c8",
                        (source_root / "node_modules/.bin/c8",),
                    )
                    or _available(
                        root,
                        "nyc",
                        (source_root / "node_modules/.bin/nyc",),
                    )
                    or '"c8"' in manifest_text
                    or '"nyc"' in manifest_text
                )
            ),
            "native": True,
            "detection": "executable, local node_modules, or package manifest",
        },
        {
            "id": "go-cover",
            "available": "Go" in languages and _available(root, "go"),
            "native": True,
            "detection": "go executable",
        },
        {
            "id": "cargo-llvm-cov-or-tarpaulin",
            "available": bool(
                "Rust" in languages
                and (
                    _available(root, "cargo-llvm-cov")
                    or _available(root, "cargo-tarpaulin")
                )
            ),
            "native": True,
            "detection": "Rust coverage executable",
        },
        {
            "id": "jacoco",
            "available": bool(
                {"Java", "Kotlin"} & languages
                and "jacoco" in manifest_text
                and (
                    _available(root, "mvn")
                    or _available(root, "gradle")
                    or gradle_wrapper_found
                )
            ),
            "native": True,
            "detection": "build configuration and runner",
        },
        {
            "id": "dotnet-coverlet",
            "available": bool(
                "C#" in languages
                and _available(root, "dotnet")
                and ("coverlet" in manifest_text or "collectcoverage" in manifest_text)
            ),
            "native": True,
            "detection": "dotnet executable and project configuration",
        },
        {
            "id": "gcov-or-llvm-cov",
            "available": bool(
                {"C", "C++", "Swift"} & languages
                and (_available(root, "gcov") or _available(root, "llvm-cov"))
            ),
            "native": True,
            "detection": "compiler coverage executable",
        },
        {
            "id": "ruby-simplecov",
            "available": bool(
                "Ruby" in languages
                and ("simplecov" in manifest_text or _available(root, "simplecov"))
            ),
            "native": True,
            "detection": "Gemfile or executable",
        },
        {
            "id": "php-xdebug-or-pcov",
            "available": bool(
                "PHP" in languages
                and _available(root, "php")
                and ("xdebug" in manifest_text or "pcov" in manifest_text)
            ),
            "native": True,
            "detection": "PHP executable and project configuration",
        },
    ]

    mutation_tools = [
        {
            "id": "mutmut-or-cosmic-ray",
            "available": bool(
                "Python" in languages
                and (
                    _available(root, "mutmut")
                    or _available(root, "cosmic-ray")
                    or "mutmut" in manifest_text
                    or "cosmic-ray" in manifest_text
                )
            ),
            "detection": "executable or Python manifest",
        },
        {
            "id": "stryker-js",
            "available": bool(
                {"JavaScript", "TypeScript"} & languages
                and (
                    _available(
                        root,
                        "stryker",
                        (source_root / "node_modules/.bin/stryker",),
                    )
                    or "@stryker-mutator" in manifest_text
                )
            ),
            "detection": "executable, local node_modules, or package manifest",
        },
        {
            "id": "pitest",
            "available": bool(
                {"Java", "Kotlin"} & languages and "pitest" in manifest_text
            ),
            "detection": "build configuration",
        },
        {
            "id": "cargo-mutants",
            "available": "Rust" in languages and _available(root, "cargo-mutants"),
            "detection": "cargo-mutants executable",
        },
        {
            "id": "infection",
            "available": bool(
                "PHP" in languages
                and (_available(root, "infection") or "infection" in manifest_text)
            ),
            "detection": "executable or composer manifest",
        },
        {
            "id": "stryker-dotnet",
            "available": bool(
                "C#" in languages
                and (_available(root, "dotnet-stryker") or "stryker" in manifest_text)
            ),
            "detection": "executable or project configuration",
        },
        {
            "id": "manual-isolated-targeted-mutation",
            "available": bool(languages),
            "detection": "language source exists; Agent must mutate only a disposable copy",
        },
    ]
    return {
        "schema_version": 1,
        "source": source.as_posix(),
        "files_scanned": min(files_scanned, max_files),
        "file_limit_reached": truncated,
        "languages": sorted(languages),
        "coverage_tools": coverage_tools,
        "mutation_tools": mutation_tools,
    }


def score_mutants(value: object) -> dict:
    if not isinstance(value, dict) or not isinstance(value.get("mutants"), list):
        raise ValueError("mutation input must be an object with a mutants list")
    counts = {status: 0 for status in sorted(MUTANT_STATUSES)}
    critical_survivors = []
    seen: set[str] = set()
    for index, mutant in enumerate(value["mutants"], start=1):
        if not isinstance(mutant, dict):
            raise ValueError(f"mutant {index} must be an object")
        mutant_id = mutant.get("id")
        status = mutant.get("status")
        if not isinstance(mutant_id, str) or not mutant_id.strip():
            raise ValueError(f"mutant {index} has no valid id")
        if mutant_id in seen:
            raise ValueError(f"duplicate mutant id: {mutant_id}")
        seen.add(mutant_id)
        if status not in MUTANT_STATUSES:
            raise ValueError(f"mutant {mutant_id} has invalid status: {status}")
        counts[status] += 1
        if mutant.get("critical") is True and status in {
            "survived",
            "timeout",
            "not-covered",
            "blocked",
        }:
            critical_survivors.append(mutant_id)
    denominator = counts["killed"] + counts["survived"]
    score = round(100.0 * counts["killed"] / denominator, 2) if denominator else 0.0
    return {
        **counts,
        "valid_mutants": denominator,
        "score_percent": score,
        "critical_survivors": critical_survivors,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    detect = subparsers.add_parser("detect", help="detect local coverage and mutation tools")
    detect.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    detect.add_argument("--source", type=Path, default=Path("code"))
    detect.add_argument(
        "--output",
        type=Path,
        default=Path("result/artifacts/evidence/quality-tools.json"),
    )
    detect.add_argument("--max-files", type=int, default=20_000)

    score = subparsers.add_parser("score", help="score normalized mutation results")
    score.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    score.add_argument("--input", type=Path, required=True)
    score.add_argument("--output", type=Path)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        root = args.root.resolve()
        if args.command == "detect":
            result = detect_tools(root, args.source, args.max_files)
            output = _relative_path(root, args.output, output=True)
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
        else:
            input_path = _relative_path(root, args.input)
            artifact_root = (root / "result/artifacts").resolve()
            if artifact_root not in input_path.parents:
                raise ValueError("mutation input must be under result/artifacts/")
            if not input_path.is_file() or input_path.stat().st_size > MAX_JSON_BYTES:
                raise ValueError("mutation input is missing or exceeds 1000000 bytes")
            value = json.loads(input_path.read_text(encoding="utf-8"))
            result = score_mutants(value)
            if args.output:
                output = _relative_path(root, args.output, output=True)
                evidence_root = (root / "result/artifacts/evidence").resolve()
                if evidence_root not in output.parents:
                    raise ValueError("score output must be under result/artifacts/evidence/")
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
