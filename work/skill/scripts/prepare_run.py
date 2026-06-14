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
BUG_DIRECTIONS = (
    "input-boundary",
    "authorization-ownership",
    "business-logic",
    "data-consistency",
    "injection",
    "web-protocol-client",
    "file-path",
    "parsing-serialization",
    "authentication-session",
    "secrets-cryptography",
    "errors-observability",
    "configuration-deployment",
    "dependencies-integration",
    "api-abuse",
    "concurrency-resource",
)
TECHNIQUES = (
    "normal-control",
    "boundary-equivalence",
    "grammar-property-fuzzing",
    "differential",
    "metamorphic",
    "authorization-matrix",
    "state-machine",
    "fault-injection",
    "concurrency-interleaving",
    "encoding-canonicalization",
    "configuration-combinatorial",
    "dependency-reachability",
    "data-flow-sink",
    "negative-space-sibling",
    "sanitizer-runtime-instrumentation",
)
SYSTEM_ARCHETYPES = {
    "generic-application": {
        "high_priority": (
            "input-boundary",
            "authorization-ownership",
            "business-logic",
            "data-consistency",
            "errors-observability",
            "configuration-deployment",
        ),
        "specialty_checks": (),
    },
    "web-api": {
        "high_priority": (
            "input-boundary",
            "authorization-ownership",
            "injection",
            "web-protocol-client",
            "parsing-serialization",
            "authentication-session",
            "api-abuse",
        ),
        "specialty_checks": ("http-browser-security",),
    },
    "commerce-financial": {
        "high_priority": (
            "authorization-ownership",
            "business-logic",
            "data-consistency",
            "authentication-session",
            "api-abuse",
            "concurrency-resource",
        ),
        "specialty_checks": ("money-ledger-invariants",),
    },
    "multi-tenant-saas": {
        "high_priority": (
            "authorization-ownership",
            "data-consistency",
            "authentication-session",
            "configuration-deployment",
            "api-abuse",
        ),
        "specialty_checks": ("cross-tenant-isolation",),
    },
    "identity-access": {
        "high_priority": (
            "input-boundary",
            "authorization-ownership",
            "authentication-session",
            "secrets-cryptography",
            "errors-observability",
            "concurrency-resource",
        ),
        "specialty_checks": ("identity-lifecycle",),
    },
    "file-content": {
        "high_priority": (
            "input-boundary",
            "injection",
            "file-path",
            "parsing-serialization",
            "concurrency-resource",
        ),
        "specialty_checks": ("archive-content-boundaries",),
    },
    "microservices": {
        "high_priority": (
            "authorization-ownership",
            "data-consistency",
            "parsing-serialization",
            "configuration-deployment",
            "dependencies-integration",
            "api-abuse",
            "concurrency-resource",
        ),
        "specialty_checks": ("service-to-service-trust",),
    },
    "async-messaging": {
        "high_priority": (
            "business-logic",
            "data-consistency",
            "parsing-serialization",
            "configuration-deployment",
            "concurrency-resource",
        ),
        "specialty_checks": ("delivery-ordering-idempotency",),
    },
    "data-pipeline": {
        "high_priority": (
            "input-boundary",
            "business-logic",
            "data-consistency",
            "file-path",
            "parsing-serialization",
            "concurrency-resource",
        ),
        "specialty_checks": ("schema-lineage-checkpointing",),
    },
    "cli-desktop": {
        "high_priority": (
            "input-boundary",
            "injection",
            "file-path",
            "secrets-cryptography",
            "configuration-deployment",
            "dependencies-integration",
        ),
        "specialty_checks": ("local-ipc-update-integrity",),
    },
    "sdk-library": {
        "high_priority": (
            "input-boundary",
            "business-logic",
            "parsing-serialization",
            "errors-observability",
            "dependencies-integration",
            "concurrency-resource",
        ),
        "specialty_checks": ("api-compatibility-contract",),
    },
    "native-systems": {
        "high_priority": (
            "input-boundary",
            "parsing-serialization",
            "errors-observability",
            "dependencies-integration",
            "concurrency-resource",
        ),
        "specialty_checks": ("native-memory-size-safety",),
    },
    "infrastructure-automation": {
        "high_priority": (
            "authorization-ownership",
            "injection",
            "file-path",
            "secrets-cryptography",
            "configuration-deployment",
            "dependencies-integration",
        ),
        "specialty_checks": ("supply-chain-artifact-integrity",),
    },
    "mobile-client": {
        "high_priority": (
            "authorization-ownership",
            "web-protocol-client",
            "file-path",
            "authentication-session",
            "secrets-cryptography",
            "configuration-deployment",
            "api-abuse",
        ),
        "specialty_checks": ("mobile-ipc-storage-transport",),
    },
    "ai-agent": {
        "high_priority": (
            "authorization-ownership",
            "business-logic",
            "injection",
            "parsing-serialization",
            "secrets-cryptography",
            "configuration-deployment",
            "api-abuse",
        ),
        "specialty_checks": ("prompt-tool-memory-trust",),
    },
}
COVERAGE_TARGET_PERCENT = 95.0
MUTATION_TARGET_PERCENT = 80.0
TARGETED_MUTANT_BUDGET = 20
RESET_DIRS = (
    "result/artifacts/generated_tests",
    "result/artifacts/reproduction",
    "result/artifacts/evidence",
)
RESET_FILES = (
    "result/project_profile.md",
    "result/output.md",
    "result/run_manifest.json",
    "result/project_discovery.json",
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
    parser.add_argument("--candidate-budget", type=int, default=12)
    parser.add_argument("--test-budget", type=int, default=48)
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
        "schema_version": 5,
        "run_id": run_id or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8],
        "started_at": datetime.now(timezone.utc).isoformat(),
        "independent_run": True,
        "run_status": "initialized",
        "system_classification": {
            "primary_archetypes": [],
            "secondary_archetypes": [],
            "confidence": "",
            "evidence_paths": [],
            "rationale": "",
        },
        "minimum_strategy_families": 3,
        "complex_project_strategy_target": 4,
        "project_complexity": {
            "is_complex": None,
            "reasons": [],
            "strategy_target_exception": "",
        },
        "strategy_portfolio": list(STRATEGIES),
        "selected_strategies": [],
        "blind_analysis": {
            "phase": "phase-a-pending",
            "answer_bearing_paths": [],
            "candidate_provenance_required": True,
            "first_pass_fixed_before_answer_review": False,
        },
        "lead_validation": {
            "required": True,
            "source_registry": [],
            "lead_registry": [],
            "all_discovered_sources_reviewed": False,
            "all_actionable_leads_dispositioned": False,
        },
        "track_metrics": {
            "independent_candidates": 0,
            "lead_candidates": 0,
            "independent_confirmed": 0,
            "lead_confirmed": 0,
            "total_confirmed": 0,
        },
        "coverage_dimensions": [
            "ingress-and-identity",
            "parsing-types-and-normalization",
            "authorization-and-ownership",
            "state-transitions-and-persistence",
            "sinks-serialization-and-output",
            "external-boundaries-and-configuration",
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
            "direction_matrix": [],
            "specialty_obligations": [],
            "calculated_percent": 0.0,
            "coverage_gap_reason": "",
            "rebalance": {
                "performed": False,
                "before_percent": 0.0,
                "after_percent": 0.0,
                "changes": [],
                "decision_summary": "",
            },
        },
        "runtime_quality": {
            "tool_detection_path": (
                "result/artifacts/evidence/quality-tools.json"
            ),
            "coverage": {
                "status": "pending",
                "tool": "",
                "native": None,
                "commands": [],
                "scope_files": [],
                "report_paths": [],
                "metrics": {
                    "line_percent": None,
                    "branch_percent": None,
                    "function_percent": None,
                },
                "metric_limitations": "",
                "key_path_hits": [],
                "unavailable_reason": "",
            },
            "mutation": {
                "status": "pending",
                "tool": "",
                "isolated_copy_confirmed": False,
                "baseline_passed": False,
                "original_code_unchanged": False,
                "commands": [],
                "baseline_evidence_path": "",
                "isolation_evidence_path": "",
                "targeted_mutant_budget": TARGETED_MUTANT_BUDGET,
                "target_score_percent": MUTATION_TARGET_PERCENT,
                "results_path": "",
                "summary": {
                    "killed": 0,
                    "survived": 0,
                    "invalid": 0,
                    "timeout": 0,
                    "not-covered": 0,
                    "blocked": 0,
                    "valid_mutants": 0,
                    "score_percent": 0.0,
                    "critical_survivors": [],
                },
                "direction_assessments": [],
                "unavailable_reason": "",
            },
        },
        "required_test_techniques": [
            "normal-control",
            "boundary-or-equivalence-partition",
            "differential-or-metamorphic",
            "negative-space-or-sibling-comparison",
        ],
        "budget_allocation_percent": {
            "discovery-controls-and-breadth": 30,
            "candidate-execution-and-minimization": 40,
            "confirmation-evidence-and-reporting": 30,
        },
        "candidate_registry": [],
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
            "Complex projects should target at least four relevant strategies.",
            "This run must not inherit findings or generated tests from another run.",
            "Temporarily quarantine answer-bearing material until independent first-pass candidates are fixed.",
            "Then review every discovered source and validate every actionable lead.",
            "Confirmed project leads count as confirmed Bugs while retaining provenance.",
            "Assess all 15 bug directions and prioritize them by system archetype.",
            "A complete run targets 95 percent risk-weighted dynamic-test coverage, not 95 percent Bug recall.",
            "Measure native runtime code coverage when available and prove key target paths executed.",
            "Run bounded targeted mutation testing only in an isolated copy; complete runs require no unresolved critical mutant and at least 80 percent mutation score.",
            "Log the initial execution, normal control, and every rerun separately.",
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
