#!/usr/bin/env python3
"""Create a bounded, read-only inventory of an unknown local codebase."""

from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MAX_FILES = 20_000
DEFAULT_MAX_READ_BYTES = 20_000_000
DEFAULT_MAX_ANSWER_HINTS = 1000
MAX_FILE_SAMPLE = 64_000
IGNORED_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "venv",
    "node_modules",
    "vendor",
    "dist",
    "build",
    "target",
    "__pycache__",
}
LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".c": "C",
    ".h": "C/C++",
    ".cpp": "C++",
    ".cc": "C++",
    ".swift": "Swift",
    ".scala": "Scala",
    ".sh": "Shell",
}
MANIFEST_HINTS = {
    "pyproject.toml": ("Python", "Python packaging/build"),
    "requirements.txt": ("Python", "pip dependencies"),
    "package.json": ("JavaScript/TypeScript", "Node package/build"),
    "pom.xml": ("Java", "Maven"),
    "build.gradle": ("Java/Kotlin", "Gradle"),
    "build.gradle.kts": ("Kotlin", "Gradle"),
    "go.mod": ("Go", "Go modules"),
    "Cargo.toml": ("Rust", "Cargo"),
    "Gemfile": ("Ruby", "Bundler"),
    "composer.json": ("PHP", "Composer"),
    "Dockerfile": ("Container", "Docker"),
    "Makefile": ("Build", "Make"),
}
COMMAND_HINTS = {
    "pyproject.toml": {
        "test": ["python3 -m unittest discover", "python3 -m pytest"],
        "build": ["python3 -m build"],
    },
    "requirements.txt": {
        "setup": ["python3 -m pip install -r requirements.txt"],
    },
    "package.json": {
        "setup": ["npm install"],
        "test": ["npm test"],
        "run": ["npm start"],
    },
    "pom.xml": {"test": ["mvn test"], "build": ["mvn package"]},
    "build.gradle": {"test": ["./gradlew test"], "build": ["./gradlew build"]},
    "build.gradle.kts": {
        "test": ["./gradlew test"],
        "build": ["./gradlew build"],
    },
    "go.mod": {"test": ["go test ./..."], "build": ["go build ./..."]},
    "Cargo.toml": {"test": ["cargo test"], "build": ["cargo build"]},
    "Gemfile": {"test": ["bundle exec rake test"]},
    "composer.json": {"test": ["composer test"]},
    "Makefile": {"build": ["make"], "test": ["make test"]},
}
TEST_MARKERS = (
    "test",
    "tests",
    "spec",
    "specs",
)
ANSWER_PATH_MARKERS = {
    "answer",
    "answers",
    "solution",
    "solutions",
    "tutorial",
    "tutorials",
    "walkthrough",
    "walkthroughs",
    "writeup",
    "writeups",
    "advisory",
    "advisories",
    "cve",
    "vulnerability",
    "vulnerabilities",
}
ANSWER_CONTENT_PATTERNS = {
    "cve-id": re.compile(r"\bCVE-\d{4}-\d{4,}\b", re.IGNORECASE),
    "known-vulnerability": re.compile(
        r"\bknown\s+vulnerabilit(?:y|ies)\b",
        re.IGNORECASE,
    ),
    "solution-heading": re.compile(
        r"(?im)^\s{0,3}#{1,6}\s+(?:solution|answer|writeup)\b"
    ),
    "tutorial-heading": re.compile(
        r"(?im)^\s{0,3}#{1,6}\s+(?:tutorial|walkthrough)\b"
    ),
    "reproduction-heading": re.compile(
        r"(?im)^\s{0,3}#{1,6}\s+(?:exploit|reproduction|proof\s+of\s+concept)\b"
    ),
}
ATTACK_SURFACE_MARKERS = {
    "ingress": {
        "api",
        "cli",
        "command",
        "commands",
        "controller",
        "controllers",
        "endpoint",
        "endpoints",
        "graphql",
        "handler",
        "handlers",
        "route",
        "routes",
    },
    "identity-and-authorization": {
        "account",
        "accounts",
        "auth",
        "authentication",
        "authorization",
        "login",
        "permission",
        "permissions",
        "role",
        "roles",
        "session",
        "sessions",
        "tenant",
        "tenants",
    },
    "state-and-persistence": {
        "cache",
        "dao",
        "database",
        "db",
        "job",
        "jobs",
        "migration",
        "migrations",
        "model",
        "models",
        "queue",
        "repository",
        "repositories",
        "store",
        "worker",
        "workers",
    },
    "parsing-files-and-output": {
        "decoder",
        "download",
        "downloads",
        "file",
        "files",
        "parser",
        "parsers",
        "serializer",
        "serializers",
        "template",
        "templates",
        "upload",
        "uploads",
        "view",
        "views",
    },
    "configuration-and-integration": {
        "adapter",
        "adapters",
        "client",
        "clients",
        "config",
        "configuration",
        "deploy",
        "deployment",
        "docker",
        "integration",
        "integrations",
        "plugin",
        "plugins",
    },
}
ARCHETYPE_PATH_MARKERS = {
    "web-api": {
        "api",
        "controller",
        "controllers",
        "endpoint",
        "graphql",
        "handler",
        "routes",
        "server",
    },
    "commerce-financial": {
        "billing",
        "cart",
        "checkout",
        "discount",
        "invoice",
        "order",
        "payment",
        "price",
    },
    "multi-tenant-saas": {
        "membership",
        "organization",
        "tenant",
        "workspace",
    },
    "identity-access": {
        "auth",
        "login",
        "mfa",
        "oauth",
        "oidc",
        "password",
        "saml",
        "session",
    },
    "file-content": {
        "archive",
        "document",
        "download",
        "file",
        "media",
        "storage",
        "upload",
    },
    "microservices": {
        "gateway",
        "grpc",
        "kubernetes",
        "proto",
        "protobuf",
        "service",
        "services",
    },
    "async-messaging": {
        "consumer",
        "event",
        "events",
        "kafka",
        "message",
        "producer",
        "queue",
        "worker",
    },
    "data-pipeline": {
        "airflow",
        "batch",
        "etl",
        "ingest",
        "pipeline",
        "spark",
        "transform",
    },
    "cli-desktop": {
        "cli",
        "command",
        "desktop",
        "electron",
        "gui",
    },
    "sdk-library": {
        "client",
        "library",
        "sdk",
    },
    "infrastructure-automation": {
        "ansible",
        "deploy",
        "deployment",
        "helm",
        "terraform",
    },
    "mobile-client": {
        "android",
        "ios",
        "mobile",
        "webview",
    },
    "ai-agent": {
        "agent",
        "embedding",
        "llm",
        "model",
        "prompt",
        "rag",
        "retrieval",
        "tool",
        "vector",
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect filenames and bounded text samples without modifying source."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("code"),
        help="source path relative to root; defaults to code",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("result/artifacts/evidence/project-discovery.json"),
        help="JSON output path relative to root",
    )
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument(
        "--max-answer-hints",
        type=int,
        default=DEFAULT_MAX_ANSWER_HINTS,
    )
    parser.add_argument(
        "--max-read-bytes",
        type=int,
        default=DEFAULT_MAX_READ_BYTES,
    )
    return parser


def _within(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _resolve_inside(root: Path, relative: Path, label: str) -> Path:
    if relative.is_absolute():
        raise ValueError(f"{label} must be relative to project root")
    path = (root / relative).resolve()
    if not _within(path, root):
        raise ValueError(f"{label} escapes project root")
    return path


def _iter_files(source: Path, max_files: int):
    count = 0
    for current, directories, filenames in os.walk(source):
        directories[:] = sorted(
            name for name in directories if name not in IGNORED_DIRS
        )
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.is_symlink():
                continue
            yield path
            count += 1
            if count >= max_files:
                return


def _path_tokens(path: Path) -> set[str]:
    return {
        token
        for token in re.split(r"[^a-z0-9]+", path.as_posix().lower())
        if token
    }


def discover(
    root: Path,
    source_relative: Path,
    *,
    max_files: int = DEFAULT_MAX_FILES,
    max_read_bytes: int = DEFAULT_MAX_READ_BYTES,
    max_answer_hints: int = DEFAULT_MAX_ANSWER_HINTS,
) -> dict[str, Any]:
    root = root.resolve()
    source = _resolve_inside(root, source_relative, "source")
    if not source.is_dir():
        raise FileNotFoundError(f"source directory does not exist: {source_relative}")
    if not any(source.iterdir()):
        raise FileNotFoundError(f"source directory is empty: {source_relative}")
    if not 1 <= max_files <= 100_000:
        raise ValueError("max-files must be between 1 and 100000")
    if not 0 <= max_read_bytes <= 100_000_000:
        raise ValueError("max-read-bytes must be between 0 and 100000000")
    if not 1 <= max_answer_hints <= 5000:
        raise ValueError("max-answer-hints must be between 1 and 5000")

    extension_counts: Counter[str] = Counter()
    language_counts: Counter[str] = Counter()
    manifests = []
    test_paths = []
    likely_entry_points = []
    answer_bearing_path_hints = []
    attack_surface_path_hints: dict[str, list[str]] = {
        category: [] for category in ATTACK_SURFACE_MARKERS
    }
    archetype_signal_paths: dict[str, list[str]] = {
        archetype: [] for archetype in ARCHETYPE_PATH_MARKERS
    }
    subprojects = set()
    command_hints: dict[str, list[dict[str, str]]] = {}
    top_level_counts: Counter[str] = Counter()
    sampled_bytes = 0
    file_count = 0
    truncated = False
    answer_hint_match_count = 0
    answer_hint_limit_reached = False

    for path in _iter_files(source, max_files + 1):
        file_count += 1
        if file_count > max_files:
            truncated = True
            file_count = max_files
            break
        relative = path.relative_to(root).as_posix()
        source_relative_path = path.relative_to(source)
        path_tokens = _path_tokens(source_relative_path)
        top_level = source_relative_path.parts[0]
        top_level_counts[top_level] += 1
        extension = path.suffix.lower() or "[none]"
        extension_counts[extension] += 1
        if extension in LANGUAGES:
            language_counts[LANGUAGES[extension]] += 1
        if path.name in MANIFEST_HINTS:
            language, build = MANIFEST_HINTS[path.name]
            manifests.append(
                {"path": relative, "language_hint": language, "build_hint": build}
            )
            parent = path.parent.relative_to(source).as_posix()
            subprojects.add("." if parent == "." else parent)
            for category, commands in COMMAND_HINTS.get(path.name, {}).items():
                command_hints.setdefault(category, [])
                for command in commands:
                    command_hints[category].append(
                        {
                            "working_directory": parent,
                            "command": command,
                            "status": "hint-only",
                        }
                    )
        lower_parts = [part.lower() for part in path.parts]
        if any(
            part in TEST_MARKERS
            or part.startswith("test_")
            or part.endswith("_test.py")
            for part in lower_parts
        ):
            if len(test_paths) < 100:
                test_paths.append(relative)
        if path.name.lower() in {
            "main.py",
            "app.py",
            "server.py",
            "manage.py",
            "index.js",
            "index.ts",
            "main.go",
            "main.rs",
        }:
            if len(likely_entry_points) < 100:
                likely_entry_points.append(relative)

        answer_matches = sorted(path_tokens & ANSWER_PATH_MARKERS)
        content_matches: list[str] = []
        for category, markers in ATTACK_SURFACE_MARKERS.items():
            if (
                path_tokens & markers
                and len(attack_surface_path_hints[category]) < 100
            ):
                attack_surface_path_hints[category].append(relative)
        for archetype, markers in ARCHETYPE_PATH_MARKERS.items():
            if (
                path_tokens & markers
                and len(archetype_signal_paths[archetype]) < 100
            ):
                archetype_signal_paths[archetype].append(relative)

        if sampled_bytes < max_read_bytes and path.stat().st_size <= MAX_FILE_SAMPLE:
            remaining = max_read_bytes - sampled_bytes
            try:
                sample = path.read_bytes()[: min(MAX_FILE_SAMPLE, remaining)]
            except OSError:
                continue
            sampled_bytes += len(sample)
            text_sample = sample.decode("utf-8", errors="ignore")
            content_matches = sorted(
                name
                for name, pattern in ANSWER_CONTENT_PATTERNS.items()
                if pattern.search(text_sample)
            )

        if (
            (answer_matches or content_matches)
        ):
            answer_hint_match_count += 1
            if len(answer_bearing_path_hints) < max_answer_hints:
                answer_bearing_path_hints.append(
                    {
                        "path": relative,
                        "matched_path_markers": answer_matches,
                        "matched_content_markers": content_matches,
                        "status": "review-required",
                    }
                )
            else:
                answer_hint_limit_reached = True

    complexity_reasons = []
    if len(subprojects) > 1:
        complexity_reasons.append("multiple-subprojects")
    if len(likely_entry_points) > 1:
        complexity_reasons.append("multiple-entry-points")
    if len(language_counts) > 1:
        complexity_reasons.append("multiple-languages")
    if file_count >= 500:
        complexity_reasons.append("large-file-count")
    populated_surface_categories = sum(
        1 for paths in attack_surface_path_hints.values() if paths
    )
    if populated_surface_categories >= 4:
        complexity_reasons.append("broad-attack-surface")
    if any(language in language_counts for language in ("C", "C++")):
        archetype_signal_paths["native-systems"] = [
            item
            for item in (
                manifest["path"] for manifest in manifests
                if manifest["language_hint"] in {"Build", "Container"}
            )
        ][:100]
        if not archetype_signal_paths["native-systems"]:
            archetype_signal_paths["native-systems"] = likely_entry_points[:100]
    archetype_hints = [
        {
            "archetype": archetype,
            "signal_count": len(paths),
            "evidence_paths": paths[:20],
            "status": "hint-only",
        }
        for archetype, paths in archetype_signal_paths.items()
        if paths
    ]
    archetype_hints.sort(
        key=lambda item: (-item["signal_count"], item["archetype"])
    )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source_relative.as_posix(),
        "file_count": file_count,
        "file_limit_reached": truncated,
        "sampled_bytes": sampled_bytes,
        "languages": dict(language_counts.most_common()),
        "extensions": dict(extension_counts.most_common(30)),
        "manifests": manifests[:100],
        "subprojects": sorted(subprojects)[:100],
        "top_level_file_counts": dict(top_level_counts.most_common(50)),
        "command_hints": command_hints,
        "likely_entry_points": likely_entry_points,
        "test_paths": test_paths,
        "answer_bearing_path_hints": answer_bearing_path_hints,
        "answer_hint_match_count": answer_hint_match_count,
        "answer_hint_limit_reached": answer_hint_limit_reached,
        "attack_surface_path_hints": attack_surface_path_hints,
        "system_archetype_hints": archetype_hints,
        "complexity": {
            "reasons": complexity_reasons,
            "suggested_strategy_target": 4 if complexity_reasons else 3,
            "populated_attack_surface_categories": populated_surface_categories,
        },
        "notes": [
            "Hints are an inventory, not a vulnerability conclusion.",
            "Answer-bearing path and content hints must be temporarily quarantined, then reviewed after the independent first pass.",
            "Attack-surface path hints are starting points, not proof that an interface is reachable.",
            "System archetype hints require Agent verification from behavior and trust boundaries.",
            "The platform Agent must verify command hints, frameworks, entry points, and constraints.",
            "Command hints are not authorization to install remote dependencies.",
        ],
    }


def main() -> int:
    args = build_parser().parse_args()
    root = args.root.resolve()
    try:
        output = _resolve_inside(root, args.output, "output")
        code = (root / "code").resolve()
        if _within(output, code):
            raise ValueError("output must not be written inside code/")
        profile = discover(
            root,
            args.source,
            max_files=args.max_files,
            max_read_bytes=args.max_read_bytes,
            max_answer_hints=args.max_answer_hints,
        )
        encoded = json.dumps(profile, ensure_ascii=False, indent=2) + "\n"
        if len(encoded.encode("utf-8")) > 1_000_000:
            raise ValueError("discovery output exceeds 1000000 bytes")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(encoded, encoding="utf-8")
    except (OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    print(output.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
