#!/usr/bin/env python3
"""Inspect and execute an unknown local project in a bounded isolated copy."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from redact import redact_text
from source_snapshot import snapshot


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MAX_FILES = 100_000
DEFAULT_MAX_BYTES = 2_000_000_000
DEFAULT_MAX_OUTPUT_BYTES = 1_000_000
DEFAULT_TIMEOUT_SECONDS = 120
COPY_EXCLUDES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
}
DEPENDENCY_DIRS = {"node_modules", ".venv", "venv", "vendor"}
SAFE_ENV_KEYS = {
    "PATH",
    "LANG",
    "LC_ALL",
    "JAVA_HOME",
    "GOROOT",
    "GOPATH",
    "CARGO_HOME",
    "RUSTUP_HOME",
    "DOTNET_ROOT",
    "NVM_BIN",
    "VOLTA_HOME",
    "SYSTEMROOT",
}
BLOCKED_EXECUTABLES = {
    "curl",
    "dd",
    "launchctl",
    "nc",
    "ncat",
    "nmap",
    "reboot",
    "rm",
    "scp",
    "sftp",
    "shutdown",
    "ssh",
    "su",
    "sudo",
    "systemctl",
    "wget",
}
INLINE_EVAL_FLAGS = {
    "bash": {"-c", "-lc"},
    "sh": {"-c", "-lc"},
    "zsh": {"-c", "-lc"},
    "python": {"-c"},
    "python3": {"-c"},
    "node": {"-e", "--eval"},
    "ruby": {"-e"},
    "perl": {"-e"},
    "php": {"-r"},
}
RUNTIME_COMMANDS = {
    "python3": ["python3", "--version"],
    "python": ["python", "--version"],
    "node": ["node", "--version"],
    "npm": ["npm", "--version"],
    "pnpm": ["pnpm", "--version"],
    "yarn": ["yarn", "--version"],
    "java": ["java", "-version"],
    "mvn": ["mvn", "--version"],
    "gradle": ["gradle", "--version"],
    "go": ["go", "version"],
    "cargo": ["cargo", "--version"],
    "rustc": ["rustc", "--version"],
    "dotnet": ["dotnet", "--version"],
    "ruby": ["ruby", "--version"],
    "php": ["php", "--version"],
    "make": ["make", "--version"],
    "cmake": ["cmake", "--version"],
}
MANIFEST_NAMES = {
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "Pipfile",
    "poetry.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "go.mod",
    "Cargo.toml",
    "Gemfile",
    "composer.json",
    "Makefile",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    "compose.yml",
    "compose.yaml",
    "CMakeLists.txt",
    "tox.ini",
    "pytest.ini",
    "noxfile.py",
}
ENV_TEMPLATE_NAMES = {
    ".env.example",
    ".env.sample",
    ".env.template",
    "example.env",
    "sample.env",
}
BLOCKED_ENV_KEYS = {
    "PATH",
    "HOME",
    "TMPDIR",
    "PYTHONPATH",
    "PYTHONHOME",
    "NODE_OPTIONS",
    "RUBYOPT",
    "PERL5OPT",
    "BASH_ENV",
    "ENV",
    "LD_PRELOAD",
    "LD_LIBRARY_PATH",
    "DYLD_INSERT_LIBRARIES",
    "DYLD_LIBRARY_PATH",
}


def _inside(path: Path, parent: Path) -> bool:
    return path == parent or parent in path.parents


def _resolve(root: Path, relative: Path, label: str) -> Path:
    if relative.is_absolute():
        raise ValueError(f"{label} must be relative to project root")
    path = (root / relative).resolve()
    if not _inside(path, root):
        raise ValueError(f"{label} escapes project root")
    return path


def _resolve_source(root: Path, relative: Path) -> Path:
    source = _resolve(root, relative, "source")
    code = (root / "code").resolve()
    if not _inside(source, code):
        raise ValueError("source must be code/ or a subdirectory of code/")
    if not source.is_dir() or not any(source.iterdir()):
        raise FileNotFoundError(f"source directory is missing or empty: {relative}")
    return source


def _resolve_evidence(root: Path, relative: Path) -> Path:
    output = _resolve(root, relative, "output")
    evidence = (root / "result/artifacts/evidence").resolve()
    if not _inside(output, evidence):
        raise ValueError("output must be under result/artifacts/evidence/")
    return output


def _bounded_json(value: str, label: str) -> list[str]:
    if len(value.encode("utf-8")) > 64_000:
        raise ValueError(f"{label} exceeds 64000 bytes")
    parsed = json.loads(value)
    if (
        not isinstance(parsed, list)
        or not parsed
        or not all(isinstance(item, str) and item for item in parsed)
        or len(parsed) > 100
    ):
        raise ValueError(f"{label} must be a non-empty JSON string array")
    return parsed


def _validate_command(command: list[str]) -> None:
    if not command or len(command) > 100:
        raise ValueError("command must contain between 1 and 100 arguments")
    if any("\x00" in item or len(item) > 8192 for item in command):
        raise ValueError("command contains an invalid or oversized argument")
    executable = Path(command[0]).name.lower()
    if executable in BLOCKED_EXECUTABLES:
        raise ValueError(f"blocked executable: {executable}")
    blocked_flags = INLINE_EVAL_FLAGS.get(executable, set())
    if any(item in blocked_flags for item in command[1:]):
        raise ValueError(f"inline code execution is blocked for {executable}")


def _safe_environment(home: Path) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if key in SAFE_ENV_KEYS and isinstance(value, str)
    }
    environment.update(
        {
            "HOME": str(home),
            "TMPDIR": str(home / "tmp"),
            "CI": "1",
            "NO_COLOR": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "PIP_NO_INPUT": "1",
            "NPM_CONFIG_UPDATE_NOTIFIER": "false",
            "NPM_CONFIG_FUND": "false",
            "NPM_CONFIG_AUDIT": "false",
            "NO_PROXY": "127.0.0.1,localhost,::1",
            "no_proxy": "127.0.0.1,localhost,::1",
        }
    )
    (home / "tmp").mkdir(parents=True, exist_ok=True)
    return environment


def _load_environment_file(root: Path, relative: Path | None) -> dict[str, str]:
    if relative is None:
        return {}
    path = _resolve(root, relative, "env-file")
    allowed = (root / "result/artifacts/generated_tests").resolve()
    if not _inside(path, allowed):
        raise ValueError("env-file must be under result/artifacts/generated_tests/")
    if not path.is_file() or path.stat().st_size > 64_000:
        raise ValueError("env-file is missing or exceeds 64000 bytes")
    result: dict[str, str] = {}
    for number, raw_line in enumerate(
        path.read_text(encoding="utf-8", errors="strict").splitlines(),
        start=1,
    ):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError(f"env-file line {number} must use KEY=VALUE")
        key, value = line.split("=", 1)
        key = key.strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"env-file line {number} has an invalid key")
        if key.upper() in BLOCKED_ENV_KEYS or key.upper().startswith("DYLD_"):
            raise ValueError(f"env-file key is blocked: {key}")
        if "\x00" in value or len(value) > 4096:
            raise ValueError(f"env-file value for {key} is invalid or oversized")
        result[key] = value
        if len(result) > 200:
            raise ValueError("env-file contains more than 200 variables")
    return result


def _validate_environment_overrides(
    value: dict[str, str] | None,
) -> dict[str, str]:
    result = dict(value or {})
    if len(result) > 200:
        raise ValueError("environment contains more than 200 variables")
    for key, item in result.items():
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"environment has an invalid key: {key}")
        if key.upper() in BLOCKED_ENV_KEYS or key.upper().startswith("DYLD_"):
            raise ValueError(f"environment key is blocked: {key}")
        if not isinstance(item, str) or "\x00" in item or len(item) > 4096:
            raise ValueError(f"environment value for {key} is invalid or oversized")
    return result


def _snapshot_comparable(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop("generated_at", None)
    return result


def _redact_explicit_values(value: Any, secrets: list[str]) -> Any:
    if isinstance(value, dict):
        return {
            key: _redact_explicit_values(item, secrets)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_redact_explicit_values(item, secrets) for item in value]
    if isinstance(value, str):
        result = value
        for secret in sorted((item for item in secrets if item), key=len, reverse=True):
            result = result.replace(secret, "[REDACTED]")
        return result
    return value


def _copy_ignore(dependency_mode: str):
    excluded = set(COPY_EXCLUDES)
    if dependency_mode == "exclude":
        excluded.update(DEPENDENCY_DIRS)

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in excluded}

    return ignore


def _scan_copy_scope(
    source: Path,
    *,
    dependency_mode: str,
    max_files: int,
    max_bytes: int,
) -> tuple[int, int]:
    excluded = set(COPY_EXCLUDES)
    if dependency_mode == "exclude":
        excluded.update(DEPENDENCY_DIRS)
    count = 0
    total = 0
    for current, directories, filenames in os.walk(source, followlinks=False):
        directories[:] = sorted(name for name in directories if name not in excluded)
        for dirname in directories:
            path = Path(current) / dirname
            if not path.is_symlink():
                continue
            if Path(os.readlink(path)).is_absolute() or not _inside(
                path.resolve(),
                source,
            ):
                raise ValueError(
                    f"source symlink is absolute or escapes source: "
                    f"{path.relative_to(source)}"
                )
        for filename in sorted(filenames):
            path = Path(current) / filename
            if path.is_symlink():
                if Path(os.readlink(path)).is_absolute() or not _inside(
                    path.resolve(),
                    source,
                ):
                    raise ValueError(
                        f"source symlink is absolute or escapes source: "
                        f"{path.relative_to(source)}"
                    )
                count += 1
                if count > max_files:
                    raise ValueError(
                        "isolated copy exceeds max-files; select a smaller subproject"
                    )
                continue
            count += 1
            total += path.stat().st_size
            if count > max_files:
                raise ValueError(
                    "isolated copy exceeds max-files; select a smaller subproject"
                )
            if total > max_bytes:
                raise ValueError(
                    "isolated copy exceeds max-bytes; select a smaller subproject"
                )
    return count, total


class _Capture:
    def __init__(self, stream, limit: int) -> None:
        self.stream = stream
        self.limit = limit
        self.buffer = bytearray()
        self.truncated = False
        self.thread = threading.Thread(target=self._read, daemon=True)

    def _read(self) -> None:
        while True:
            chunk = self.stream.read(65536)
            if not chunk:
                return
            remaining = self.limit - len(self.buffer)
            if remaining > 0:
                self.buffer.extend(chunk[:remaining])
            if len(chunk) > max(remaining, 0):
                self.truncated = True

    def start(self) -> None:
        self.thread.start()

    def finish(self) -> tuple[str, bool]:
        self.thread.join(timeout=5)
        self.stream.close()
        return (
            redact_text(self.buffer.decode("utf-8", errors="replace")),
            self.truncated,
        )


def _start_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    max_output_bytes: int,
) -> tuple[subprocess.Popen[bytes], _Capture, _Capture]:
    _validate_command(command)
    process = subprocess.Popen(
        command,
        cwd=cwd,
        env=environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    assert process.stdout is not None
    assert process.stderr is not None
    stdout = _Capture(process.stdout, max_output_bytes)
    stderr = _Capture(process.stderr, max_output_bytes)
    stdout.start()
    stderr.start()
    return process, stdout, stderr


def _terminate(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=3)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait(timeout=3)


def _finish_process(
    process: subprocess.Popen[bytes],
    stdout_capture: _Capture,
    stderr_capture: _Capture,
    *,
    timeout_seconds: int,
) -> dict[str, Any]:
    timed_out = False
    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate(process)
        return_code = process.returncode
    stdout, stdout_truncated = stdout_capture.finish()
    stderr, stderr_truncated = stderr_capture.finish()
    return {
        "return_code": return_code,
        "timed_out": timed_out,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_truncated": stdout_truncated,
        "stderr_truncated": stderr_truncated,
    }


def _run_process(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str],
    timeout_seconds: int,
    max_output_bytes: int,
) -> dict[str, Any]:
    started = time.monotonic()
    process, stdout, stderr = _start_process(
        command,
        cwd=cwd,
        environment=environment,
        max_output_bytes=max_output_bytes,
    )
    result = _finish_process(
        process,
        stdout,
        stderr,
        timeout_seconds=timeout_seconds,
    )
    result["duration_seconds"] = round(time.monotonic() - started, 3)
    result["status"] = (
        "timeout"
        if result["timed_out"]
        else "passed"
        if result["return_code"] == 0
        else "failed"
    )
    return result


def _write_report(output: Path, report: dict[str, Any]) -> None:
    encoded = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if len(encoded.encode("utf-8")) > 5_000_000:
        raise ValueError("runtime report exceeds 5000000 bytes")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(encoded, encoding="utf-8")


def _runtime_version(command: list[str]) -> str:
    try:
        completed = subprocess.run(
            command,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=3,
            check=False,
            env={key: value for key, value in os.environ.items() if key in SAFE_ENV_KEYS},
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return redact_text(completed.stdout.strip())[:500]


def inspect_runtime(root: Path, source_relative: Path, max_files: int) -> dict[str, Any]:
    root = root.resolve()
    source = _resolve_source(root, source_relative)
    if not 1 <= max_files <= 100_000:
        raise ValueError("max-files must be between 1 and 100000")

    manifests = []
    env_templates = []
    environment_variables: set[str] = set()
    entry_points = []
    local_dependency_dirs = []
    service_manifests = []
    command_candidates = []
    scanned = 0
    truncated = False
    for current, directories, filenames in os.walk(source, followlinks=False):
        for name in directories:
            if name in DEPENDENCY_DIRS and len(local_dependency_dirs) < 100:
                local_dependency_dirs.append(
                    (Path(current) / name).relative_to(root).as_posix()
                )
        directories[:] = sorted(
            name
            for name in directories
            if name not in COPY_EXCLUDES and name not in DEPENDENCY_DIRS
        )
        for filename in sorted(filenames):
            scanned += 1
            if scanned > max_files:
                truncated = True
                break
            path = Path(current) / filename
            relative_source = path.relative_to(source).as_posix()
            relative_root = path.relative_to(root).as_posix()
            is_dotnet_manifest = path.suffix.lower() in {".sln", ".csproj", ".fsproj"}
            if filename in MANIFEST_NAMES or is_dotnet_manifest:
                manifests.append(relative_root)
                workdir = path.parent.relative_to(source).as_posix()
                workdir = "." if workdir == "." else workdir
                if filename == "package.json" and path.stat().st_size <= 1_000_000:
                    try:
                        package = json.loads(path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError):
                        package = {}
                    scripts = package.get("scripts") if isinstance(package, dict) else {}
                    if isinstance(scripts, dict):
                        if (path.parent / "pnpm-lock.yaml").is_file():
                            package_runner = "pnpm"
                        elif (path.parent / "yarn.lock").is_file():
                            package_runner = "yarn"
                        else:
                            package_runner = "npm"
                        for name in ("test", "build", "start", "dev"):
                            if isinstance(scripts.get(name), str):
                                argv = (
                                    [package_runner, name]
                                    if package_runner == "yarn"
                                    else [package_runner, "run", name]
                                )
                                command_candidates.append(
                                    {
                                        "phase": (
                                            "start" if name in {"start", "dev"} else name
                                        ),
                                        "working_directory": workdir,
                                        "argv": argv,
                                        "source": relative_root,
                                        "confidence": "manifest-declared",
                                        "automatic_execution": False,
                                    }
                                )
                elif filename == "pyproject.toml":
                    command_candidates.extend(
                        [
                            {
                                "phase": "test",
                                "working_directory": workdir,
                                "argv": ["python3", "-m", "pytest"],
                                "source": relative_root,
                                "confidence": "manifest-inferred",
                                "automatic_execution": False,
                            },
                            {
                                "phase": "test",
                                "working_directory": workdir,
                                "argv": [
                                    "python3",
                                    "-m",
                                    "unittest",
                                    "discover",
                                ],
                                "source": relative_root,
                                "confidence": "manifest-inferred",
                                "automatic_execution": False,
                            },
                        ]
                    )
                elif filename == "go.mod":
                    command_candidates.append(
                        {
                            "phase": "test",
                            "working_directory": workdir,
                            "argv": ["go", "test", "./..."],
                            "source": relative_root,
                            "confidence": "manifest-inferred",
                            "automatic_execution": False,
                        }
                    )
                elif filename == "Cargo.toml":
                    command_candidates.append(
                        {
                            "phase": "test",
                            "working_directory": workdir,
                            "argv": ["cargo", "test"],
                            "source": relative_root,
                            "confidence": "manifest-inferred",
                            "automatic_execution": False,
                        }
                    )
                elif filename == "pom.xml":
                    for phase, argv in (
                        ("test", ["mvn", "test"]),
                        ("build", ["mvn", "package", "-DskipTests"]),
                    ):
                        command_candidates.append(
                            {
                                "phase": phase,
                                "working_directory": workdir,
                                "argv": argv,
                                "source": relative_root,
                                "confidence": "manifest-inferred",
                                "automatic_execution": False,
                            }
                        )
                elif filename in {"build.gradle", "build.gradle.kts"}:
                    gradle = (
                        "./gradlew"
                        if (path.parent / "gradlew").is_file()
                        else "gradle"
                    )
                    for phase in ("test", "build"):
                        command_candidates.append(
                            {
                                "phase": phase,
                                "working_directory": workdir,
                                "argv": [gradle, phase],
                                "source": relative_root,
                                "confidence": "manifest-inferred",
                                "automatic_execution": False,
                            }
                        )
                elif is_dotnet_manifest:
                    for phase in ("test", "build"):
                        command_candidates.append(
                            {
                                "phase": phase,
                                "working_directory": workdir,
                                "argv": ["dotnet", phase, filename],
                                "source": relative_root,
                                "confidence": "manifest-inferred",
                                "automatic_execution": False,
                            }
                        )
                elif filename == "Gemfile":
                    command_candidates.append(
                        {
                            "phase": "test",
                            "working_directory": workdir,
                            "argv": ["bundle", "exec", "rake", "test"],
                            "source": relative_root,
                            "confidence": "manifest-inferred",
                            "automatic_execution": False,
                        }
                    )
                elif filename == "composer.json":
                    command_candidates.append(
                        {
                            "phase": "test",
                            "working_directory": workdir,
                            "argv": ["composer", "test"],
                            "source": relative_root,
                            "confidence": "manifest-inferred",
                            "automatic_execution": False,
                        }
                    )
                elif filename == "Makefile":
                    for phase, argv in (
                        ("test", ["make", "test"]),
                        ("build", ["make"]),
                    ):
                        command_candidates.append(
                            {
                                "phase": phase,
                                "working_directory": workdir,
                                "argv": argv,
                                "source": relative_root,
                                "confidence": "manifest-inferred",
                                "automatic_execution": False,
                            }
                        )
                elif filename == "CMakeLists.txt":
                    command_candidates.append(
                        {
                            "phase": "build",
                            "working_directory": workdir,
                            "argv": ["cmake", "--build", "build"],
                            "source": relative_root,
                            "confidence": "manifest-inferred",
                            "automatic_execution": False,
                        }
                    )
                if filename in {
                    "Dockerfile",
                    "docker-compose.yml",
                    "docker-compose.yaml",
                    "compose.yml",
                    "compose.yaml",
                }:
                    service_manifests.append(relative_root)
            if filename in ENV_TEMPLATE_NAMES:
                env_templates.append(relative_root)
                if path.stat().st_size <= 64_000:
                    try:
                        template = path.read_text(encoding="utf-8", errors="replace")
                    except OSError:
                        template = ""
                    environment_variables.update(
                        match.group(1)
                        for match in re.finditer(
                            r"(?m)^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=",
                            template,
                        )
                    )
            if filename.lower() in {
                "main.py",
                "app.py",
                "server.py",
                "manage.py",
                "index.js",
                "index.ts",
                "main.go",
                "main.rs",
            }:
                entry_points.append(relative_root)
        if truncated:
            break

    runtimes = []
    for name, version_command in RUNTIME_COMMANDS.items():
        executable = shutil.which(name)
        runtimes.append(
            {
                "name": name,
                "available": executable is not None,
                "path": executable or "",
                "version": _runtime_version(version_command) if executable else "",
            }
        )
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": source_relative.as_posix(),
        "files_scanned": min(scanned, max_files),
        "file_limit_reached": truncated,
        "runtimes": runtimes,
        "manifests": manifests[:200],
        "entry_points": entry_points[:200],
        "environment_templates": env_templates[:100],
        "environment_variable_names": sorted(environment_variables)[:500],
        "service_manifests": service_manifests[:100],
        "local_dependency_directories": sorted(set(local_dependency_dirs)),
        "command_candidates": command_candidates[:200],
        "execution_policy": {
            "commands_are_candidates_only": True,
            "remote_dependency_installation_allowed": False,
            "isolated_copy_required_for_writing_builds": True,
            "localhost_health_checks_only": True,
        },
    }


def _isolated_context(
    root: Path,
    source_relative: Path,
    *,
    dependency_mode: str,
    max_files: int,
    max_bytes: int,
):
    source = _resolve_source(root, source_relative)
    before = snapshot(
        root,
        source_relative,
        max_files=max_files,
        max_bytes=max_bytes,
    )
    copied_files, copied_bytes = _scan_copy_scope(
        source,
        dependency_mode=dependency_mode,
        max_files=max_files,
        max_bytes=max_bytes,
    )
    temporary = tempfile.TemporaryDirectory(prefix="legacy-runtime-")
    temporary_root = Path(temporary.name).resolve()
    isolated_source = temporary_root / "source"
    shutil.copytree(
        source,
        isolated_source,
        symlinks=True,
        ignore=_copy_ignore(dependency_mode),
    )
    home = temporary_root / "home"
    home.mkdir()
    return temporary, source, isolated_source, home, before, copied_files, copied_bytes


def execute_isolated(
    root: Path,
    source_relative: Path,
    workdir_relative: Path,
    command: list[str],
    *,
    dependency_mode: str,
    timeout_seconds: int,
    max_output_bytes: int,
    max_files: int,
    max_bytes: int,
    environment_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    _validate_limits(timeout_seconds, max_output_bytes, max_files, max_bytes)
    environment_overrides = _validate_environment_overrides(environment_overrides)
    (
        temporary,
        _source,
        isolated_source,
        home,
        before,
        copied_files,
        copied_bytes,
    ) = _isolated_context(
        root,
        source_relative,
        dependency_mode=dependency_mode,
        max_files=max_files,
        max_bytes=max_bytes,
    )
    try:
        workdir = (isolated_source / workdir_relative).resolve()
        if not _inside(workdir, isolated_source) or not workdir.is_dir():
            raise ValueError("workdir must be an existing directory inside source")
        started_at = datetime.now(timezone.utc).isoformat()
        environment = _safe_environment(home)
        environment.update(environment_overrides or {})
        result = _run_process(
            command,
            cwd=workdir,
            environment=environment,
            timeout_seconds=timeout_seconds,
            max_output_bytes=max_output_bytes,
        )
        result = _redact_explicit_values(
            result,
            list((environment_overrides or {}).values()),
        )
        after = snapshot(
            root,
            source_relative,
            max_files=max_files,
            max_bytes=max_bytes,
        )
        source_unchanged = _snapshot_comparable(before) == _snapshot_comparable(after)
        return {
            "schema_version": 1,
            "kind": "command",
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "source": source_relative.as_posix(),
            "workdir": workdir_relative.as_posix(),
            "mode": "isolated-copy",
            "dependency_mode": dependency_mode,
            "copied_files": copied_files,
            "copied_bytes": copied_bytes,
            "command": [redact_text(item) for item in command],
            "timeout_seconds": timeout_seconds,
            "max_output_bytes": max_output_bytes,
            "environment_keys": sorted((environment_overrides or {}).keys()),
            "source_unchanged": source_unchanged,
            "result": result,
        }
    finally:
        temporary.cleanup()


def _validate_health_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("health-url must use http or https")
    if parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("health-url must target localhost")
    if parsed.username or parsed.password:
        raise ValueError("health-url must not contain credentials")
    return value


def _health_ready(url: str, timeout: float) -> tuple[bool, str]:
    request = urllib.request.Request(url, method="GET")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(request, timeout=timeout) as response:
            return 100 <= response.status < 500, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        return 100 <= exc.code < 500, f"HTTP {exc.code}"
    except (OSError, urllib.error.URLError) as exc:
        return False, type(exc).__name__


def _validate_health_tcp(value: str) -> tuple[str, int]:
    if value.startswith("[::1]:"):
        host = "::1"
        port_text = value[len("[::1]:") :]
    else:
        try:
            host, port_text = value.rsplit(":", 1)
        except ValueError as exc:
            raise ValueError("health-tcp must use host:port") from exc
    if host not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("health-tcp must target localhost")
    try:
        port = int(port_text)
    except ValueError as exc:
        raise ValueError("health-tcp port must be an integer") from exc
    if not 1 <= port <= 65535:
        raise ValueError("health-tcp port must be between 1 and 65535")
    return host, port


def _tcp_ready(target: tuple[str, int], timeout: float) -> tuple[bool, str]:
    try:
        with socket.create_connection(target, timeout=timeout):
            return True, "TCP connected"
    except OSError as exc:
        return False, type(exc).__name__


def execute_service(
    root: Path,
    source_relative: Path,
    workdir_relative: Path,
    start_command: list[str],
    probe_command: list[str],
    health_url: str | None,
    *,
    health_tcp: str | None = None,
    dependency_mode: str,
    startup_timeout_seconds: int,
    probe_timeout_seconds: int,
    max_output_bytes: int,
    max_files: int,
    max_bytes: int,
    environment_overrides: dict[str, str] | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    _validate_limits(
        max(startup_timeout_seconds, probe_timeout_seconds),
        max_output_bytes,
        max_files,
        max_bytes,
    )
    environment_overrides = _validate_environment_overrides(environment_overrides)
    if bool(health_url) == bool(health_tcp):
        raise ValueError("provide exactly one of health_url or health_tcp")
    validated_url = _validate_health_url(health_url) if health_url else None
    validated_tcp = _validate_health_tcp(health_tcp) if health_tcp else None
    _validate_command(start_command)
    _validate_command(probe_command)
    (
        temporary,
        _source,
        isolated_source,
        home,
        before,
        copied_files,
        copied_bytes,
    ) = _isolated_context(
        root,
        source_relative,
        dependency_mode=dependency_mode,
        max_files=max_files,
        max_bytes=max_bytes,
    )
    service = None
    service_stdout = None
    service_stderr = None
    started_at = datetime.now(timezone.utc).isoformat()
    health_attempts = []
    try:
        workdir = (isolated_source / workdir_relative).resolve()
        if not _inside(workdir, isolated_source) or not workdir.is_dir():
            raise ValueError("workdir must be an existing directory inside source")
        environment = _safe_environment(home)
        environment.update(environment_overrides or {})
        service, service_stdout, service_stderr = _start_process(
            start_command,
            cwd=workdir,
            environment=environment,
            max_output_bytes=max_output_bytes,
        )
        deadline = time.monotonic() + startup_timeout_seconds
        ready = False
        while time.monotonic() < deadline:
            if service.poll() is not None:
                break
            if validated_url:
                ready, observation = _health_ready(validated_url, timeout=1.0)
            else:
                assert validated_tcp is not None
                ready, observation = _tcp_ready(validated_tcp, timeout=1.0)
            health_attempts.append(
                {
                    "elapsed_seconds": round(
                        startup_timeout_seconds - max(deadline - time.monotonic(), 0),
                        3,
                    ),
                    "observation": observation,
                    "ready": ready,
                }
            )
            if ready:
                break
            time.sleep(0.25)

        probe_result = None
        if ready:
            probe_result = _run_process(
                probe_command,
                cwd=(root / "result/artifacts/generated_tests").resolve(),
                environment=environment,
                timeout_seconds=probe_timeout_seconds,
                max_output_bytes=max_output_bytes,
            )
        _terminate(service)
        service_result = {
            "return_code": service.returncode,
            "stdout": service_stdout.finish()[0],
            "stderr": service_stderr.finish()[0],
            "stdout_truncated": service_stdout.truncated,
            "stderr_truncated": service_stderr.truncated,
        }
        explicit_values = list((environment_overrides or {}).values())
        service_result = _redact_explicit_values(service_result, explicit_values)
        probe_result = _redact_explicit_values(probe_result, explicit_values)
        after = snapshot(
            root,
            source_relative,
            max_files=max_files,
            max_bytes=max_bytes,
        )
        source_unchanged = _snapshot_comparable(before) == _snapshot_comparable(after)
        passed = ready and probe_result is not None and probe_result["status"] == "passed"
        return {
            "schema_version": 1,
            "kind": "service",
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "source": source_relative.as_posix(),
            "workdir": workdir_relative.as_posix(),
            "mode": "isolated-copy",
            "dependency_mode": dependency_mode,
            "copied_files": copied_files,
            "copied_bytes": copied_bytes,
            "start_command": [redact_text(item) for item in start_command],
            "probe_command": [redact_text(item) for item in probe_command],
            "health_url": validated_url or "",
            "health_tcp": health_tcp or "",
            "health_ready": ready,
            "health_attempts": health_attempts[-200:],
            "environment_keys": sorted((environment_overrides or {}).keys()),
            "service_result": service_result,
            "probe_result": probe_result,
            "source_unchanged": source_unchanged,
            "status": "passed" if passed else "failed",
        }
    finally:
        if service is not None:
            _terminate(service)
        temporary.cleanup()


def _validate_limits(
    timeout_seconds: int,
    max_output_bytes: int,
    max_files: int,
    max_bytes: int,
) -> None:
    if not 1 <= timeout_seconds <= 1800:
        raise ValueError("timeout must be between 1 and 1800 seconds")
    if not 1024 <= max_output_bytes <= 5_000_000:
        raise ValueError("max-output-bytes must be between 1024 and 5000000")
    if not 1 <= max_files <= 100_000:
        raise ValueError("max-files must be between 1 and 100000")
    if not 1 <= max_bytes <= 2_000_000_000:
        raise ValueError("max-bytes must be between 1 and 2000000000")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    inspect = subparsers.add_parser("inspect", help="inventory runtimes and commands")
    inspect.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    inspect.add_argument("--source", type=Path, default=Path("code"))
    inspect.add_argument(
        "--output",
        type=Path,
        default=Path("result/artifacts/evidence/runtime-capabilities.json"),
    )
    inspect.add_argument("--max-files", type=int, default=20_000)

    execute = subparsers.add_parser("exec", help="run one command in an isolated copy")
    _add_execution_arguments(execute, include_timeout=True)
    execute.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="command after --, for example -- python3 -m unittest",
    )

    service = subparsers.add_parser(
        "service",
        help="start an isolated service, check localhost health, and run a probe",
    )
    _add_execution_arguments(service, include_timeout=False)
    service.add_argument("--start-command-json", required=True)
    service.add_argument("--probe-command-json", required=True)
    health = service.add_mutually_exclusive_group(required=True)
    health.add_argument("--health-url")
    health.add_argument("--health-tcp")
    service.add_argument("--startup-timeout-seconds", type=int, default=60)
    service.add_argument("--probe-timeout-seconds", type=int, default=120)
    return parser


def _add_execution_arguments(
    parser: argparse.ArgumentParser,
    *,
    include_timeout: bool,
) -> None:
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--source", type=Path, default=Path("code"))
    parser.add_argument("--workdir", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--dependency-mode",
        choices=("exclude", "copy"),
        default="exclude",
    )
    if include_timeout:
        parser.add_argument(
            "--timeout-seconds",
            type=int,
            default=DEFAULT_TIMEOUT_SECONDS,
        )
    parser.add_argument("--max-output-bytes", type=int, default=DEFAULT_MAX_OUTPUT_BYTES)
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument(
        "--env-file",
        type=Path,
        help=(
            "synthetic KEY=VALUE file under result/artifacts/generated_tests; "
            "values are never written to the runtime report"
        ),
    )


def main() -> int:
    args = build_parser().parse_args()
    try:
        root = args.root.resolve()
        output = _resolve_evidence(root, args.output)
        if args.subcommand == "inspect":
            report = inspect_runtime(root, args.source, args.max_files)
        elif args.subcommand == "exec":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            environment = _load_environment_file(root, args.env_file)
            report = execute_isolated(
                root,
                args.source,
                args.workdir,
                command,
                dependency_mode=args.dependency_mode,
                timeout_seconds=args.timeout_seconds,
                max_output_bytes=args.max_output_bytes,
                max_files=args.max_files,
                max_bytes=args.max_bytes,
                environment_overrides=environment,
            )
        else:
            environment = _load_environment_file(root, args.env_file)
            report = execute_service(
                root,
                args.source,
                args.workdir,
                _bounded_json(args.start_command_json, "start-command-json"),
                _bounded_json(args.probe_command_json, "probe-command-json"),
                args.health_url,
                health_tcp=args.health_tcp,
                dependency_mode=args.dependency_mode,
                startup_timeout_seconds=args.startup_timeout_seconds,
                probe_timeout_seconds=args.probe_timeout_seconds,
                max_output_bytes=args.max_output_bytes,
                max_files=args.max_files,
                max_bytes=args.max_bytes,
                environment_overrides=environment,
            )
        _write_report(output, report)
        print(output.relative_to(root))
        return 0
    except (
        FileNotFoundError,
        OSError,
        ValueError,
        json.JSONDecodeError,
        subprocess.SubprocessError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
