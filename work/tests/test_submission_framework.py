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
from prepare_run import (
    BUG_DIRECTIONS,
    COVERAGE_TARGET_PERCENT,
    MUTATION_TARGET_PERCENT,
    SYSTEM_ARCHETYPES,
    TARGETED_MUTANT_BUDGET,
    TECHNIQUES,
    prepare,
)
from quality_tools import detect_tools, score_mutants
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
    direction_matrix = [
        {
            "id": direction,
            "priority": "high",
            "rationale": "The minimal validation target exercises every direction.",
            "evidence_paths": ["code/source.txt"],
            "planned_techniques": ["normal-control", "boundary-equivalence"],
            "executed_techniques": ["normal-control", "boundary-equivalence"],
            "candidate_ids": [],
            "test_paths": ["result/artifacts/generated_tests/test_dynamic.py"],
            "blocker_evidence_paths": [],
            "status": "tested",
        }
        for direction in BUG_DIRECTIONS
    ]
    coverage_hits = [
        {
            "id": f"HIT-{index:03d}",
            "direction": direction,
            "candidate_id": "",
            "source_path": "code/source.txt",
            "symbol": f"decision_{index}",
            "evidence_path": "result/artifacts/evidence/coverage-report.json",
        }
        for index, direction in enumerate(BUG_DIRECTIONS, start=1)
    ]
    critical_directions = {
        "input-boundary": "boundary-change",
        "authorization-ownership": "authorization-guard-removal",
        "business-logic": "condition-negation",
    }
    mutants = [
        {
            "id": f"MUT-{index:03d}",
            "direction": direction,
            "operator": critical_directions.get(direction, "boolean-replacement"),
            "source_path": "code/source.txt",
            "critical": direction in critical_directions,
            "status": "killed",
            "diff_path": "result/artifacts/evidence/mutation.diff",
            "evidence_path": "result/artifacts/evidence/mutation-run.txt",
            "test_path": "result/artifacts/generated_tests/test_dynamic.py",
        }
        for index, direction in enumerate(BUG_DIRECTIONS, start=1)
    ]
    mutation_results = {"mutants": mutants}
    manifest = {
        "schema_version": 5,
        "run_id": "test-run",
        "independent_run": True,
        "run_status": "complete",
        "system_classification": {
            "primary_archetypes": ["generic-application"],
            "secondary_archetypes": [],
            "confidence": "high",
            "evidence_paths": ["code/source.txt"],
            "rationale": "Minimal deterministic validation target.",
        },
        "minimum_strategy_families": 3,
        "complex_project_strategy_target": 4,
        "project_complexity": {
            "is_complex": False,
            "reasons": [],
            "strategy_target_exception": "",
        },
        "strategy_portfolio": [
            "input-and-parsing",
            "authorization-and-ownership",
            "state-and-workflow",
        ],
        "selected_strategies": [
            "input-and-parsing",
            "authorization-and-ownership",
            "state-and-workflow",
        ],
        "blind_analysis": {
            "phase": "complete",
            "answer_bearing_paths": [],
            "candidate_provenance_required": True,
            "first_pass_fixed_before_answer_review": True,
        },
        "lead_validation": {
            "required": True,
            "source_registry": [],
            "lead_registry": [],
            "all_discovered_sources_reviewed": True,
            "all_actionable_leads_dispositioned": True,
        },
        "track_metrics": {
            "independent_candidates": 0,
            "lead_candidates": 0,
            "independent_confirmed": 0,
            "lead_confirmed": 0,
            "total_confirmed": 0,
        },
        "coverage_dimensions": [
            "ingress",
            "parsing",
            "authorization",
            "state",
            "sinks",
            "external",
        ],
        "bug_direction_catalog": list(BUG_DIRECTIONS),
        "system_archetype_catalog": list(SYSTEM_ARCHETYPES),
        "technique_catalog": list(TECHNIQUES),
        "coverage_plan": {
            "target_percent": COVERAGE_TARGET_PERCENT,
            "claim_scope": (
                "risk-weighted dynamic-test coverage; not Bug recall or proof "
                "that the target is vulnerability-free"
            ),
            "direction_matrix": direction_matrix,
            "specialty_obligations": [],
            "calculated_percent": 100.0,
            "coverage_gap_reason": "",
            "rebalance": {
                "performed": True,
                "before_percent": 60.0,
                "after_percent": 100.0,
                "changes": ["Completed remaining high-priority directions."],
                "decision_summary": "Reallocated the remaining test budget.",
            },
        },
        "runtime_quality": {
            "tool_detection_path": (
                "result/artifacts/evidence/quality-tools.json"
            ),
            "coverage": {
                "status": "measured",
                "tool": "fixture-native-coverage",
                "native": True,
                "commands": ["fixture-test --coverage"],
                "scope_files": ["code/source.txt"],
                "report_paths": [
                    "result/artifacts/evidence/coverage-report.json"
                ],
                "metrics": {
                    "line_percent": 100.0,
                    "branch_percent": 100.0,
                    "function_percent": 100.0,
                },
                "metric_limitations": "",
                "key_path_hits": coverage_hits,
                "unavailable_reason": "",
            },
            "mutation": {
                "status": "measured",
                "tool": "fixture-isolated-mutation",
                "isolated_copy_confirmed": True,
                "baseline_passed": True,
                "original_code_unchanged": True,
                "commands": ["fixture-mutate --isolated"],
                "baseline_evidence_path": (
                    "result/artifacts/evidence/mutation-run.txt"
                ),
                "isolation_evidence_path": (
                    "result/artifacts/evidence/mutation-run.txt"
                ),
                "targeted_mutant_budget": TARGETED_MUTANT_BUDGET,
                "target_score_percent": MUTATION_TARGET_PERCENT,
                "results_path": (
                    "result/artifacts/evidence/mutation-results.json"
                ),
                "summary": score_mutants(mutation_results),
                "direction_assessments": [
                    {
                        "direction": direction,
                        "status": "tested",
                        "rationale": "A covered decision was mutated in isolation.",
                        "mutant_ids": [f"MUT-{index:03d}"],
                        "evidence_paths": [],
                        "blocker_evidence_paths": [],
                    }
                    for index, direction in enumerate(BUG_DIRECTIONS, start=1)
                ],
                "unavailable_reason": "",
            },
        },
        "required_test_techniques": [
            "normal-control",
            "boundary",
            "differential",
            "negative-space",
        ],
        "budget_allocation_percent": {
            "discovery-controls-and-breadth": 30,
            "candidate-execution-and-minimization": 40,
            "confirmation-evidence-and-reporting": 30,
        },
        "candidate_registry": [],
    }
    files = {
        "INSTRUCTION.md": "instruction",
        "work/skill/SKILL.md": "skill",
        "work/skill/agents/openai.yaml": "interface: {}",
        "work/skill/references/strategy-portfolio.md": "strategies",
        "work/skill/references/system-profiles.md": "profiles",
        "work/skill/references/execution-fallback.md": "fallback",
        "work/skill/references/runtime-quality.md": "runtime quality",
        "work/skill/scripts/prepare_run.py": "script",
        "work/skill/scripts/quality_tools.py": "script",
        "work/skill/scripts/source_snapshot.py": "script",
        "result/output.md": "output",
        "result/project_profile.md": "profile",
        "result/run_manifest.json": json.dumps(manifest),
        "result/artifacts/generated_tests/test_dynamic.py": "assert True\n",
        "result/artifacts/evidence/project-discovery.json": json.dumps(
            {
                "file_limit_reached": False,
                "answer_hint_limit_reached": False,
                "answer_bearing_path_hints": [],
            }
        ),
        "result/artifacts/evidence/quality-tools.json": json.dumps(
            {
                "schema_version": 1,
                "file_limit_reached": False,
                "coverage_tools": [{"id": "fixture", "available": True}],
                "mutation_tools": [{"id": "fixture", "available": True}],
            }
        ),
        "result/artifacts/evidence/coverage-report.json": json.dumps(
            {"fixture": "product source executed"}
        ),
        "result/artifacts/evidence/mutation-results.json": json.dumps(
            mutation_results
        ),
        "result/artifacts/evidence/mutation.diff": "- false\n+ true\n",
        "result/artifacts/evidence/mutation-run.txt": "mutant killed\n",
        "logs/interaction.md": "",
        "code/source.txt": "immutable",
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
    source_before = snapshot(
        root,
        Path("code"),
        max_files=1000,
        max_bytes=10_000_000,
    )
    (root / "result/artifacts/evidence/source-before.json").write_text(
        json.dumps(source_before),
        encoding="utf-8",
    )


def link_candidate(manifest: dict, direction: str, candidate_id: str) -> None:
    for entry in manifest["coverage_plan"]["direction_matrix"]:
        if entry["id"] == direction:
            entry["candidate_ids"].append(candidate_id)
            for hit in manifest["runtime_quality"]["coverage"]["key_path_hits"]:
                if hit["direction"] == direction and not hit["candidate_id"]:
                    hit["candidate_id"] = candidate_id
                    break
            return
    raise AssertionError(f"missing direction: {direction}")


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
            "system-profiles.md",
            "runtime-quality.md",
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
            "盲分析与线索验证",
            "双轨全面探索",
            "系统分类与风险覆盖计划",
            "15 个通用漏洞方向",
            "风险加权动态测试覆盖率",
            "运行时代码覆盖与变异测试质量门",
            "key_path_hit",
            "定向变异分数至少 80%",
            "攻击面矩阵",
            "项目线索确认",
            "已确认 Bug 总数",
            "差分测试",
            "变形测试",
            "角色 × 操作 × 资源归属",
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
        self.assertIn("at least three independent strategy families", normalized)
        self.assertIn("targeting four for complex projects", normalized)
        self.assertIn("answer-bearing", normalized)
        self.assertIn("review every quarantined source", normalized)
        self.assertIn("include confirmed ones in the total Bug count", normalized)
        self.assertIn("metamorphic", normalized)
        self.assertIn("authorization-matrix", normalized)
        self.assertIn("system-profiles.md", text)
        self.assertIn("95% weighted dynamic-test coverage", normalized)
        self.assertIn("runtime-quality.md", text)
        self.assertIn("at least 80% targeted mutation score", normalized)
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
        self.assertIn("attack_surface_path_hints", profile)
        self.assertIn("system_archetype_hints", profile)
        self.assertIn("complexity", profile)
        self.assertFalse(profile["file_limit_reached"])
        self.assertFalse(profile["answer_hint_limit_reached"])

    def test_discovery_marks_answer_paths_and_attack_surface_hints(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            paths = {
                "code/docs/tutorial/solution.md": "example",
                "code/docs/release-notes.md": "# Solution\nCVE-2026-12345\n",
                "code/app/routes/accounts.js": "module.exports = {};",
                "code/app/auth/session.py": "def check(): pass\n",
                "code/app/models/user.py": "class User: pass\n",
            }
            for relative, content in paths.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            profile = discover(root, Path("code"))
            answer_paths = {
                item["path"] for item in profile["answer_bearing_path_hints"]
            }
            self.assertIn("code/docs/tutorial/solution.md", answer_paths)
            self.assertIn("code/docs/release-notes.md", answer_paths)
            self.assertTrue(profile["attack_surface_path_hints"]["ingress"])
            self.assertTrue(
                profile["attack_surface_path_hints"]["identity-and-authorization"]
            )
            self.assertTrue(
                profile["attack_surface_path_hints"]["state-and-persistence"]
            )
            archetypes = {
                item["archetype"] for item in profile["system_archetype_hints"]
            }
            self.assertIn("web-api", archetypes)
            self.assertIn("identity-access", archetypes)

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

    def test_quality_tool_detection_is_bounded_and_read_only(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(FIXTURE, root / "code")
            before = tree_hash(root / "code")
            detected = detect_tools(root, Path("code"), max_files=1000)
            self.assertIn("Python", detected["languages"])
            self.assertFalse(detected["file_limit_reached"])
            self.assertTrue(
                any(
                    item["id"] == "python-stdlib-trace" and item["available"]
                    for item in detected["coverage_tools"]
                )
            )
            self.assertTrue(
                any(
                    item["id"] == "manual-isolated-targeted-mutation"
                    and item["available"]
                    for item in detected["mutation_tools"]
                )
            )
            self.assertEqual(before, tree_hash(root / "code"))

    def test_quality_tool_detection_reads_nested_project_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            service = root / "code/services/api"
            service.mkdir(parents=True)
            (service / "index.js").write_text("module.exports = 1;\n", encoding="utf-8")
            (service / "package.json").write_text(
                json.dumps({"devDependencies": {"c8": "1.0.0"}}),
                encoding="utf-8",
            )
            detected = detect_tools(root, Path("code"), max_files=100)
            self.assertTrue(
                any(
                    item["id"] == "c8-or-nyc" and item["available"]
                    for item in detected["coverage_tools"]
                )
            )

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
            (root / "result/project_discovery.json").write_text(
                "stale", encoding="utf-8"
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
            self.assertFalse((root / "result/project_discovery.json").exists())
            self.assertFalse((root / "logs/trace/old.jsonl").exists())
            self.assertEqual(manifest["run_id"], "run-test")
            self.assertEqual(manifest["schema_version"], 5)
            self.assertTrue(manifest["independent_run"])
            self.assertEqual(manifest["minimum_strategy_families"], 3)
            self.assertEqual(manifest["complex_project_strategy_target"], 4)
            self.assertIsNone(manifest["project_complexity"]["is_complex"])
            self.assertEqual(manifest["blind_analysis"]["phase"], "phase-a-pending")
            self.assertTrue(manifest["lead_validation"]["required"])
            self.assertFalse(
                manifest["lead_validation"]["all_discovered_sources_reviewed"]
            )
            self.assertEqual(manifest["track_metrics"]["total_confirmed"], 0)
            self.assertEqual(
                manifest["bug_direction_catalog"],
                list(BUG_DIRECTIONS),
            )
            self.assertEqual(
                manifest["coverage_plan"]["target_percent"],
                COVERAGE_TARGET_PERCENT,
            )
            self.assertEqual(manifest["coverage_plan"]["direction_matrix"], [])
            self.assertEqual(
                manifest["runtime_quality"]["mutation"]["target_score_percent"],
                MUTATION_TARGET_PERCENT,
            )
            self.assertEqual(
                manifest["runtime_quality"]["mutation"]["targeted_mutant_budget"],
                TARGETED_MUTANT_BUDGET,
            )
            self.assertIn("web-api", manifest["system_archetype_catalog"])
            self.assertTrue(
                manifest["blind_analysis"]["candidate_provenance_required"]
            )
            self.assertEqual(
                sum(manifest["budget_allocation_percent"].values()),
                100,
            )
            self.assertGreaterEqual(len(manifest["coverage_dimensions"]), 6)
            self.assertGreaterEqual(len(manifest["required_test_techniques"]), 4)

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

    def test_mutation_score_excludes_invalid_and_flags_critical_survivors(
        self,
    ) -> None:
        summary = score_mutants(
            {
                "mutants": [
                    {"id": "M1", "status": "killed", "critical": True},
                    {"id": "M2", "status": "survived", "critical": True},
                    {"id": "M3", "status": "invalid", "critical": False},
                ]
            }
        )
        self.assertEqual(summary["valid_mutants"], 2)
        self.assertEqual(summary["score_percent"], 50.0)
        self.assertEqual(summary["critical_survivors"], ["M2"])

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

    def test_final_submission_rejects_underdiverse_strategy_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["selected_strategies"] = ["input-and-parsing"]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="final",
                operation="validate",
                command="",
                tool="",
                input_summary="",
                output_summary="failed",
                status="error",
                evidence_path="result/run_manifest.json",
                decision_summary="Strategy portfolio is incomplete.",
            )
            errors = validate_submission(root)
            self.assertTrue(any("at least 3 required" in error for error in errors))

    def test_final_submission_rejects_missing_bug_direction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["coverage_plan"]["direction_matrix"].pop()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="final",
                operation="validate",
                command="",
                tool="",
                input_summary="",
                output_summary="failed",
                status="error",
                evidence_path="result/run_manifest.json",
                decision_summary="A universal bug direction is missing.",
            )
            errors = validate_submission(root)
            self.assertTrue(
                any("must contain every bug direction exactly once" in error for error in errors)
            )

    def test_final_submission_enforces_archetype_high_priorities(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["system_classification"]["primary_archetypes"] = ["web-api"]
            for entry in manifest["coverage_plan"]["direction_matrix"]:
                if entry["id"] == "web-protocol-client":
                    entry["priority"] = "low"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="final",
                operation="validate",
                command="",
                tool="",
                input_summary="",
                output_summary="failed",
                status="error",
                evidence_path="result/run_manifest.json",
                decision_summary="Web API risks were under-prioritized.",
            )
            errors = validate_submission(root)
            self.assertTrue(
                any("must be high for the selected primary archetype" in error for error in errors)
            )

    def test_final_submission_accepts_completed_web_profile(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["system_classification"]["primary_archetypes"] = ["web-api"]
            manifest["coverage_plan"]["specialty_obligations"] = [
                {
                    "id": "http-browser-security",
                    "status": "tested",
                    "rationale": "The target exposes an HTTP interface.",
                    "executed_techniques": [
                        "differential",
                        "negative-space-sibling",
                    ],
                    "test_paths": [
                        "result/artifacts/generated_tests/test_dynamic.py"
                    ],
                    "blocker_evidence_paths": [],
                    "evidence_paths": ["code/source.txt"],
                }
            ]
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
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
                decision_summary="Web profile obligations are complete.",
            )
            self.assertEqual(validate_submission(root), [])

    def test_final_submission_rejects_complete_run_below_coverage_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            blocker = root / "result/artifacts/evidence/blocked.txt"
            blocker.write_text("environment blocked\n", encoding="utf-8")
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry = manifest["coverage_plan"]["direction_matrix"][0]
            entry["status"] = "blocked"
            entry["executed_techniques"] = []
            entry["blocker_evidence_paths"] = [
                "result/artifacts/evidence/blocked.txt"
            ]
            manifest["coverage_plan"]["calculated_percent"] = 93.33
            manifest["coverage_plan"]["rebalance"]["after_percent"] = 93.33
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="final",
                operation="validate",
                command="",
                tool="",
                input_summary="",
                output_summary="failed",
                status="error",
                evidence_path="result/run_manifest.json",
                decision_summary="Coverage is below the complete-run target.",
            )
            errors = validate_submission(root)
            self.assertTrue(any("below 95.0" in error for error in errors))
            self.assertTrue(any("untested high-priority" in error for error in errors))

    def test_final_submission_rejects_missing_runtime_key_path_hit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["runtime_quality"]["coverage"]["key_path_hits"].pop()
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="quality",
                operation="validate-runtime-coverage",
                command="fixture-test --coverage",
                tool="fixture",
                input_summary="high-risk paths",
                output_summary="one path missing",
                status="error",
                evidence_path="result/artifacts/evidence/coverage-report.json",
                decision_summary="Reject incomplete key-path evidence.",
            )
            errors = validate_submission(root)
            self.assertTrue(
                any(
                    "missing key-path evidence for high-risk directions" in error
                    for error in errors
                )
            )

    def test_final_submission_rejects_surviving_critical_mutant(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            results_path = root / "result/artifacts/evidence/mutation-results.json"
            results = json.loads(results_path.read_text(encoding="utf-8"))
            results["mutants"][0]["status"] = "survived"
            results_path.write_text(json.dumps(results), encoding="utf-8")
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["runtime_quality"]["mutation"]["summary"] = score_mutants(results)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="quality",
                operation="mutation",
                command="fixture-mutate",
                tool="fixture",
                input_summary="critical boundary mutant",
                output_summary="survived",
                status="error",
                evidence_path="result/artifacts/evidence/mutation-run.txt",
                decision_summary="Critical assertion strength is insufficient.",
            )
            errors = validate_submission(root)
            self.assertTrue(
                any("unresolved critical mutants" in error for error in errors)
            )

    def test_final_submission_rejects_low_mutation_score(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            results_path = root / "result/artifacts/evidence/mutation-results.json"
            results = json.loads(results_path.read_text(encoding="utf-8"))
            for mutant in results["mutants"][3:7]:
                mutant["status"] = "survived"
            results_path.write_text(json.dumps(results), encoding="utf-8")
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["runtime_quality"]["mutation"]["summary"] = score_mutants(results)
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="quality",
                operation="mutation-score",
                command="fixture-mutate",
                tool="fixture",
                input_summary="targeted mutants",
                output_summary="score below target",
                status="error",
                evidence_path="result/artifacts/evidence/mutation-results.json",
                decision_summary="Reject weak mutation score.",
            )
            errors = validate_submission(root)
            self.assertTrue(any("mutation score" in error for error in errors))
            self.assertTrue(any("below 80.0" in error for error in errors))

    def test_final_submission_accepts_incomplete_run_with_coverage_blocker(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            blocker = root / "result/artifacts/evidence/blocked.txt"
            blocker.write_text("environment blocked\n", encoding="utf-8")
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entry = manifest["coverage_plan"]["direction_matrix"][0]
            entry["status"] = "blocked"
            entry["executed_techniques"] = []
            entry["blocker_evidence_paths"] = [
                "result/artifacts/evidence/blocked.txt"
            ]
            manifest["run_status"] = "incomplete"
            manifest["coverage_plan"]["calculated_percent"] = 93.33
            manifest["coverage_plan"]["coverage_gap_reason"] = (
                "One high-risk direction was blocked by the recorded environment."
            )
            manifest["coverage_plan"]["rebalance"]["after_percent"] = 93.33
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="final",
                operation="validate",
                command="",
                tool="",
                input_summary="",
                output_summary="incomplete",
                status="blocked",
                evidence_path="result/artifacts/evidence/blocked.txt",
                decision_summary="Report an evidence-backed incomplete run.",
            )
            self.assertEqual(validate_submission(root), [])

    def test_final_submission_rejects_incomplete_blind_phase(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["blind_analysis"]["phase"] = "phase-a-pending"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="final",
                operation="validate",
                command="",
                tool="",
                input_summary="",
                output_summary="failed",
                status="error",
                evidence_path="result/run_manifest.json",
                decision_summary="Blind analysis is incomplete.",
            )
            errors = validate_submission(root)
            self.assertIn("run manifest blind analysis is not complete", errors)

    def test_final_submission_rejects_modified_code(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            (root / "code/source.txt").write_text("changed", encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="final",
                operation="validate",
                command="",
                tool="",
                input_summary="",
                output_summary="failed",
                status="error",
                evidence_path="result/artifacts/evidence/source-before.json",
                decision_summary="Source integrity failed.",
            )
            errors = validate_submission(root)
            self.assertTrue(any("source integrity check failed" in error for error in errors))

    def test_final_submission_rejects_unproven_confirmed_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["candidate_registry"] = [
                {
                    "id": "BUG-001",
                    "formed_at": "2026-06-14T00:00:00Z",
                    "provenance": "lead-derived",
                    "lead_source": "code/docs/tutorial.md",
                    "direction": "input-boundary",
                    "system_archetypes": ["generic-application"],
                    "strategy": "input-and-parsing",
                    "status": "independent-confirmed",
                    "generated_test": "result/artifacts/generated_tests/test_dynamic.py",
                    "reproduction": "result/artifacts/reproduction/reproduce.py",
                    "rerun_trace_sequences": [2],
                    "evidence_paths": [],
                }
            ]
            link_candidate(manifest, "input-boundary", "BUG-001")
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="final",
                operation="validate",
                command="",
                tool="",
                input_summary="",
                output_summary="failed",
                status="error",
                evidence_path="result/run_manifest.json",
                decision_summary="Confirmation evidence is incomplete.",
            )
            errors = validate_submission(root)
            self.assertTrue(
                any("independent confirmation has wrong provenance" in error for error in errors)
            )
            self.assertTrue(
                any("at least three rerun trace sequences" in error for error in errors)
            )

    def test_final_submission_accepts_confirmed_candidate_with_trace_evidence(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            reproduction = root / "result/artifacts/reproduction/reproduce.py"
            reproduction.write_text("print('reproduce')\n", encoding="utf-8")
            evidence_paths = []
            for number in range(1, 4):
                relative = f"result/artifacts/evidence/retest-{number}.txt"
                (root / relative).write_text("confirmed\n", encoding="utf-8")
                evidence_paths.append(relative)
            trace = Path("logs/trace/test.jsonl")
            for operation in ("initial", "control", "rerun-1", "rerun-2", "rerun-3"):
                append_event(
                    root,
                    trace,
                    stage="test",
                    operation=operation,
                    command="python test_dynamic.py",
                    tool="unittest",
                    input_summary=operation,
                    output_summary="observed",
                    status="confirmed",
                    evidence_path=evidence_paths[-1],
                    decision_summary="Execute bounded verification.",
                    strategy="input-and-parsing",
                    fallback_level="pure-logic-verification",
                )
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["candidate_registry"] = [
                {
                    "id": "BUG-001",
                    "formed_at": "2026-06-14T00:00:00Z",
                    "provenance": "independent",
                    "direction": "input-boundary",
                    "system_archetypes": ["generic-application"],
                    "strategy": "input-and-parsing",
                    "status": "independent-confirmed",
                    "generated_test": "result/artifacts/generated_tests/test_dynamic.py",
                    "reproduction": "result/artifacts/reproduction/reproduce.py",
                    "trace_file": "logs/trace/test.jsonl",
                    "initial_trace_sequence": 1,
                    "control_trace_sequence": 2,
                    "rerun_trace_sequences": [3, 4, 5],
                    "evidence_paths": evidence_paths,
                }
            ]
            link_candidate(manifest, "input-boundary", "BUG-001")
            manifest["track_metrics"] = {
                "independent_candidates": 1,
                "lead_candidates": 0,
                "independent_confirmed": 1,
                "lead_confirmed": 0,
                "total_confirmed": 1,
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(validate_submission(root), [])

    def test_final_submission_rejects_unreviewed_discovered_lead_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            discovery = root / "result/artifacts/evidence/project-discovery.json"
            discovery.write_text(
                json.dumps(
                    {
                        "file_limit_reached": False,
                        "answer_hint_limit_reached": False,
                        "answer_bearing_path_hints": [
                            {"path": "code/docs/tutorial.md"}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            append_event(
                root,
                Path("logs/trace/test.jsonl"),
                stage="final",
                operation="validate",
                command="",
                tool="",
                input_summary="",
                output_summary="failed",
                status="error",
                evidence_path="result/run_manifest.json",
                decision_summary="A discovered project lead was not reviewed.",
            )
            errors = validate_submission(root)
            self.assertTrue(
                any(
                    "discovered answer-bearing sources missing review entries" in error
                    for error in errors
                )
            )

    def test_final_submission_accepts_confirmed_project_lead(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            lead_source = root / "code/docs/tutorial.md"
            lead_source.parent.mkdir(parents=True, exist_ok=True)
            lead_source.write_text("# Tutorial\n", encoding="utf-8")
            source_before = snapshot(
                root,
                Path("code"),
                max_files=1000,
                max_bytes=10_000_000,
            )
            (root / "result/artifacts/evidence/source-before.json").write_text(
                json.dumps(source_before),
                encoding="utf-8",
            )
            discovery = root / "result/artifacts/evidence/project-discovery.json"
            discovery.write_text(
                json.dumps(
                    {
                        "file_limit_reached": False,
                        "answer_hint_limit_reached": False,
                        "answer_bearing_path_hints": [
                            {"path": "code/docs/tutorial.md"}
                        ]
                    }
                ),
                encoding="utf-8",
            )
            reproduction = root / "result/artifacts/reproduction/lead.py"
            reproduction.write_text("print('lead')\n", encoding="utf-8")
            evidence_paths = []
            for number in range(1, 4):
                relative = f"result/artifacts/evidence/lead-retest-{number}.txt"
                (root / relative).write_text("confirmed\n", encoding="utf-8")
                evidence_paths.append(relative)
            trace = Path("logs/trace/test.jsonl")
            for operation in ("initial", "control", "rerun-1", "rerun-2", "rerun-3"):
                append_event(
                    root,
                    trace,
                    stage="lead-validation",
                    operation=operation,
                    command="python test_dynamic.py",
                    tool="unittest",
                    input_summary=operation,
                    output_summary="observed",
                    status="confirmed",
                    evidence_path=evidence_paths[-1],
                    decision_summary="Verify a project-provided lead.",
                    strategy="input-and-parsing",
                    fallback_level="pure-logic-verification",
                )
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["blind_analysis"]["answer_bearing_paths"] = [
                "code/docs/tutorial.md"
            ]
            manifest["candidate_registry"] = [
                {
                    "id": "LEAD-BUG-001",
                    "formed_at": "2026-06-14T00:00:00Z",
                    "provenance": "lead-derived",
                    "lead_source": "code/docs/tutorial.md",
                    "direction": "input-boundary",
                    "system_archetypes": ["generic-application"],
                    "strategy": "input-and-parsing",
                    "status": "lead-confirmed",
                    "generated_test": "result/artifacts/generated_tests/test_dynamic.py",
                    "reproduction": "result/artifacts/reproduction/lead.py",
                    "trace_file": "logs/trace/test.jsonl",
                    "initial_trace_sequence": 1,
                    "control_trace_sequence": 2,
                    "rerun_trace_sequences": [3, 4, 5],
                    "evidence_paths": evidence_paths,
                }
            ]
            link_candidate(manifest, "input-boundary", "LEAD-BUG-001")
            manifest["lead_validation"] = {
                "required": True,
                "source_registry": [
                    {
                        "path": "code/docs/tutorial.md",
                        "classification": "actionable",
                        "reason": "Contains a concrete vulnerability claim.",
                        "reviewed": True,
                    }
                ],
                "lead_registry": [
                    {
                        "id": "LEAD-001",
                        "source_path": "code/docs/tutorial.md",
                        "claim_summary": "A concrete behavior requires verification.",
                        "status": "confirmed",
                        "candidate_id": "LEAD-BUG-001",
                    }
                ],
                "all_discovered_sources_reviewed": True,
                "all_actionable_leads_dispositioned": True,
            }
            manifest["track_metrics"] = {
                "independent_candidates": 0,
                "lead_candidates": 1,
                "independent_confirmed": 0,
                "lead_confirmed": 1,
                "total_confirmed": 1,
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(validate_submission(root), [])

    def test_final_submission_accepts_rejected_project_lead(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            create_minimal_root(root)
            lead_source = root / "code/docs/advisory.md"
            lead_source.parent.mkdir(parents=True, exist_ok=True)
            lead_source.write_text("# Advisory\n", encoding="utf-8")
            source_before = snapshot(
                root,
                Path("code"),
                max_files=1000,
                max_bytes=10_000_000,
            )
            (root / "result/artifacts/evidence/source-before.json").write_text(
                json.dumps(source_before),
                encoding="utf-8",
            )
            discovery = root / "result/artifacts/evidence/project-discovery.json"
            discovery.write_text(
                json.dumps(
                    {
                        "file_limit_reached": False,
                        "answer_hint_limit_reached": False,
                        "answer_bearing_path_hints": [
                            {"path": "code/docs/advisory.md"}
                        ],
                    }
                ),
                encoding="utf-8",
            )
            evidence = root / "result/artifacts/evidence/lead-rejected.txt"
            evidence.write_text("control and trigger behaved identically\n", encoding="utf-8")
            trace = Path("logs/trace/test.jsonl")
            append_event(
                root,
                trace,
                stage="lead-validation",
                operation="execute-and-reject",
                command="python test_dynamic.py",
                tool="unittest",
                input_summary="bounded lead check",
                output_summary="hypothesis rejected",
                status="rejected",
                evidence_path="result/artifacts/evidence/lead-rejected.txt",
                decision_summary="The project lead does not apply.",
                strategy="input-and-parsing",
                fallback_level="pure-logic-verification",
            )
            manifest_path = root / "result/run_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["blind_analysis"]["answer_bearing_paths"] = [
                "code/docs/advisory.md"
            ]
            manifest["candidate_registry"] = [
                {
                    "id": "LEAD-CANDIDATE-001",
                    "formed_at": "2026-06-14T00:00:00Z",
                    "provenance": "lead-derived",
                    "lead_source": "code/docs/advisory.md",
                    "direction": "input-boundary",
                    "system_archetypes": ["generic-application"],
                    "strategy": "input-and-parsing",
                    "status": "rejected",
                    "generated_test": "result/artifacts/generated_tests/test_dynamic.py",
                    "trace_file": "logs/trace/test.jsonl",
                    "execution_trace_sequences": [1],
                    "evidence_paths": [
                        "result/artifacts/evidence/lead-rejected.txt"
                    ],
                }
            ]
            link_candidate(manifest, "input-boundary", "LEAD-CANDIDATE-001")
            manifest["lead_validation"] = {
                "required": True,
                "source_registry": [
                    {
                        "path": "code/docs/advisory.md",
                        "classification": "actionable",
                        "reason": "Contains a concrete claim that can be tested.",
                        "reviewed": True,
                    }
                ],
                "lead_registry": [
                    {
                        "id": "LEAD-001",
                        "source_path": "code/docs/advisory.md",
                        "claim_summary": "The advisory claim requires verification.",
                        "status": "rejected",
                        "candidate_id": "LEAD-CANDIDATE-001",
                    }
                ],
                "all_discovered_sources_reviewed": True,
                "all_actionable_leads_dispositioned": True,
            }
            manifest["track_metrics"] = {
                "independent_candidates": 0,
                "lead_candidates": 1,
                "independent_confirmed": 0,
                "lead_confirmed": 0,
                "total_confirmed": 0,
            }
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            self.assertEqual(validate_submission(root), [])


class ScriptInterfaceTest(unittest.TestCase):
    def test_all_cli_scripts_support_help(self) -> None:
        scripts = [
            "discover_project.py",
            "init_artifacts.py",
            "redact.py",
            "prepare_run.py",
            "quality_tools.py",
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
