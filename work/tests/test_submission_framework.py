from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = PROJECT_ROOT / "work/skill/scripts"
FIXTURE = PROJECT_ROOT / "work/tests/fixtures/sample_legacy_app"
sys.path.insert(0, str(SCRIPTS))

from discover_project import discover
from init_artifacts import initialize
from prepare_run import prepare
from redact import REDACTED, redact_text, redact_value
from source_snapshot import snapshot
from trace_log import append_event
from validate_layout import validate
from validate_submission import validate_submission
from verify_trace import verify


def tree_hash(path: Path) -> str:
    digest = hashlib.sha256()
    for item in sorted(path.rglob("*")):
        digest.update(item.relative_to(path).as_posix().encode())
        if item.is_file():
            digest.update(item.read_bytes())
    return digest.hexdigest()


def create_minimal_root(root: Path) -> None:
    files = {
        "INSTRUCTION.md": "instruction",
        "work/skill/SKILL.md": "skill",
        "work/skill/agents/openai.yaml": "interface: {}",
        "work/skill/references/strategy-portfolio.md": "strategies",
        "work/skill/references/execution-fallback.md": "fallback",
        "work/skill/scripts/prepare_run.py": "script",
        "work/skill/scripts/source_snapshot.py": "script",
        "result/output.md": "output",
        "result/project_profile.md": "profile",
        "result/run_manifest.json": "{}",
        "logs/interaction.md": "",
    }
    directories = [
        "code",
        "work/skill/references",
        "work/skill/scripts",
        "work/templates",
        "work/tests",
        "work/docs",
        "result/artifacts/generated_tests",
        "result/artifacts/reproduction",
        "result/artifacts/evidence",
        "logs/trace",
    ]
    for directory in directories:
        (root / directory).mkdir(parents=True, exist_ok=True)
    for relative, content in files.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


class StructureAndSkillTest(unittest.TestCase):
    def test_required_layout_is_complete(self) -> None:
        self.assertEqual(validate(PROJECT_ROOT), [])

    def test_skill_frontmatter_is_exact(self) -> None:
        text = (PROJECT_ROOT / "work/skill/SKILL.md").read_text(encoding="utf-8")
        expected = (
            "---\n"
            "name: legacy-system-vulnerability-hunter\n"
            "description: Use when an AI agent must inspect an authorized unknown "
            "codebase in code/, apply multiple vulnerability strategies in one "
            "independent run, generate and execute tests, degrade gracefully when "
            "the full system cannot start, and produce reproducible evidence and "
            "audit records.\n"
            "---\n"
        )
        self.assertTrue(text.startswith(expected))
        self.assertNotIn("TODO", text)

    def test_skill_references_exist(self) -> None:
        names = [
            "project-discovery.md",
            "test-strategy.md",
            "evidence-standard.md",
            "safety-policy.md",
            "reporting-format.md",
            "strategy-portfolio.md",
            "execution-fallback.md",
        ]
        for name in names:
            self.assertTrue(
                (PROJECT_ROOT / "work/skill/references" / name).is_file(),
                name,
            )

    def test_instruction_contains_required_workflow(self) -> None:
        text = (PROJECT_ROOT / "INSTRUCTION.md").read_text(encoding="utf-8")
        markers = [
            "code/",
            "work/skill/SKILL.md",
            "动态生成具体测试",
            "generated_tests",
            "实际执行测试",
            "至少独立复测三次",
            "至少覆盖三类适用策略",
            "完整构建或系统启动失败时",
            "某一层失败不等于整次运行失败",
            "source_snapshot.py verify",
            "result/output.md",
            "logs/trace/",
            "不得删除、格式化或直接修改",
        ]
        for marker in markers:
            self.assertIn(marker, text)
        self.assertNotIn("LLM_API_KEY", text)
        self.assertNotIn("Codex", text)
        self.assertNotIn("codex", text)

    def test_prompts_do_not_contain_fixture_answers(self) -> None:
        combined = (
            (PROJECT_ROOT / "INSTRUCTION.md").read_text(encoding="utf-8")
            + (PROJECT_ROOT / "work/skill/SKILL.md").read_text(encoding="utf-8")
        )
        for fixture_specific in ("checkout_total", "discount_percent", "pricing.py"):
            self.assertNotIn(fixture_specific, combined)

    def test_core_instructions_are_agent_brand_neutral(self) -> None:
        combined = (
            (PROJECT_ROOT / "INSTRUCTION.md").read_text(encoding="utf-8")
            + (PROJECT_ROOT / "work/skill/SKILL.md").read_text(encoding="utf-8")
            + (PROJECT_ROOT / "work/docs/ARCHITECTURE.md").read_text(
                encoding="utf-8"
            )
        ).lower()
        self.assertNotIn("codex", combined)
        self.assertIn("通用 ai agent", combined)

    def test_skill_requires_multi_strategy_and_fallback(self) -> None:
        text = (PROJECT_ROOT / "work/skill/SKILL.md").read_text(encoding="utf-8")
        normalized = " ".join(text.split())
        self.assertIn("at least three relevant strategy families", normalized)
        self.assertIn("execution-fallback.md", text)
        self.assertIn("Continue other strategies", normalized)


class DiscoveryTest(unittest.TestCase):
    def test_project_discovery_identifies_fixture(self) -> None:
        profile = discover(
            PROJECT_ROOT,
            Path("work/tests/fixtures/sample_legacy_app"),
        )
        self.assertGreaterEqual(profile["file_count"], 4)
        self.assertIn("Python", profile["languages"])
        self.assertTrue(
            any(item["path"].endswith("pyproject.toml") for item in profile["manifests"])
        )
        self.assertTrue(any("test_pricing.py" in path for path in profile["test_paths"]))
        self.assertIn(".", profile["subprojects"])
        self.assertIn("test", profile["command_hints"])

    def test_missing_code_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaises(FileNotFoundError):
                discover(root, Path("code"))

    def test_discovery_does_not_modify_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(FIXTURE, root / "code")
            before = tree_hash(root / "code")
            discover(root, Path("code"))
            self.assertEqual(before, tree_hash(root / "code"))

    def test_source_snapshot_detects_changes_without_writing_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(FIXTURE, root / "code")
            before_tree = tree_hash(root / "code")
            baseline = snapshot(
                root,
                Path("code"),
                max_files=1000,
                max_bytes=10_000_000,
            )
            self.assertEqual(before_tree, tree_hash(root / "code"))
            target = root / "code/README.md"
            target.write_text(
                target.read_text(encoding="utf-8") + "\nchanged\n",
                encoding="utf-8",
            )
            changed = snapshot(
                root,
                Path("code"),
                max_files=1000,
                max_bytes=10_000_000,
            )
            self.assertNotEqual(baseline["files"], changed["files"])


class ArtifactAndTraceTest(unittest.TestCase):
    def test_result_directories_are_initialized(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "code").mkdir()
            initialize(root)
            for relative in (
                "result/artifacts/generated_tests",
                "result/artifacts/reproduction",
                "result/artifacts/evidence",
                "logs/trace",
            ):
                self.assertTrue((root / relative).is_dir())
            self.assertTrue((root / "logs/interaction.md").is_file())
            self.assertEqual(list((root / "code").iterdir()), [])

    def test_prepare_run_resets_outputs_but_not_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "code").mkdir()
            source = root / "code/source.txt"
            source.write_text("immutable", encoding="utf-8")
            (root / "result/artifacts/evidence").mkdir(parents=True)
            (root / "result/artifacts/evidence/old.txt").write_text(
                "old", encoding="utf-8"
            )
            (root / "logs/trace").mkdir(parents=True)
            (root / "logs/trace/old.jsonl").write_text("old", encoding="utf-8")
            templates = root / "work/templates"
            templates.mkdir(parents=True)
            (templates / "project_profile.md").write_text("profile", encoding="utf-8")
            (templates / "output.md").write_text("output", encoding="utf-8")

            manifest = prepare(
                root,
                run_id="run-test",
                reset=True,
                candidate_budget=8,
                test_budget=30,
                command_timeout_seconds=120,
            )

            self.assertEqual(source.read_text(encoding="utf-8"), "immutable")
            self.assertFalse((root / "result/artifacts/evidence/old.txt").exists())
            self.assertFalse((root / "logs/trace/old.jsonl").exists())
            self.assertEqual(manifest["run_id"], "run-test")
            self.assertTrue(manifest["independent_run"])
            self.assertEqual(manifest["minimum_strategy_families"], 3)

    def test_trace_sequence_redaction_and_hash_chain(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "logs/trace").mkdir(parents=True)
            trace = Path("logs/trace/test.jsonl")
            append_event(
                root,
                trace,
                stage="discover",
                operation="inventory",
                command="token=very-secret",
                tool="test",
                input_summary="Authorization: Bearer abc123",
                output_summary="done",
                status="ok",
                evidence_path="",
                decision_summary="Inspect manifests.",
            )
            append_event(
                root,
                trace,
                stage="test",
                operation="execute",
                command="python generated_test.py",
                tool="unittest",
                input_summary="one bounded case",
                output_summary="failed as expected",
                status="candidate",
                evidence_path="result/artifacts/evidence/run-1.txt",
                decision_summary="Repeat the minimized trigger.",
            )
            path = root / trace
            events = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual([event["sequence"] for event in events], [1, 2])
            self.assertIn("strategy", events[0])
            self.assertIn("fallback_level", events[0])
            self.assertNotIn("very-secret", path.read_text(encoding="utf-8"))
            self.assertNotIn("abc123", path.read_text(encoding="utf-8"))
            self.assertEqual(events[0]["command"], "token=" + REDACTED)
            valid, message = verify(path)
            self.assertTrue(valid, message)

    def test_hash_chain_detects_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "logs/trace").mkdir(parents=True)
            trace = Path("logs/trace/test.jsonl")
            append_event(
                root,
                trace,
                stage="one",
                operation="one",
                command="",
                tool="",
                input_summary="",
                output_summary="",
                status="ok",
                evidence_path="",
                decision_summary="",
            )
            path = root / trace
            event = json.loads(path.read_text(encoding="utf-8"))
            event["status"] = "tampered"
            path.write_text(json.dumps(event) + "\n", encoding="utf-8")
            valid, _ = verify(path)
            self.assertFalse(valid)

    def test_sensitive_information_redaction(self) -> None:
        self.assertNotIn(
            "secret-value",
            redact_text("api_key=secret-value Authorization: Bearer abc"),
        )
        value = redact_value({"password": "secret", "nested": {"token": "abc"}})
        self.assertEqual(value["password"], REDACTED)
        self.assertEqual(value["nested"]["token"], REDACTED)

    def test_final_submission_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="final",
                operation="validate",
                command="",
                tool="",
                input_summary="",
                output_summary="passed",
                status="ok",
                evidence_path="result/output.md",
                decision_summary="Finish.",
            )
            self.assertEqual(validate_submission(root), [])


class ScriptInterfaceTest(unittest.TestCase):
    def test_all_cli_scripts_support_help(self) -> None:
        scripts = [
            "discover_project.py",
            "init_artifacts.py",
            "redact.py",
            "prepare_run.py",
            "source_snapshot.py",
            "trace_log.py",
            "validate_layout.py",
            "validate_submission.py",
            "verify_trace.py",
        ]
        for script in scripts:
            completed = subprocess.run(
                [sys.executable, str(SCRIPTS / script), "--help"],
                cwd=PROJECT_ROOT,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=5,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, script + completed.stderr)


if __name__ == "__main__":
    unittest.main()
