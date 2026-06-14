#!/usr/bin/env python3
"""Validate final output directories, reports, and trace chains."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from prepare_run import (
    BUG_DIRECTIONS,
    COVERAGE_TARGET_PERCENT,
    MUTATION_TARGET_PERCENT,
    SYSTEM_ARCHETYPES,
    TARGETED_MUTANT_BUDGET,
    TECHNIQUES,
)
from quality_tools import MUTANT_STATUSES, score_mutants
from source_snapshot import snapshot
from validate_layout import validate
from verify_trace import verify


DEFAULT_ROOT = Path(__file__).resolve().parents[3]
FINAL_FILES = (
    "result/run_manifest.json",
    "result/project_profile.md",
    "result/output.md",
)
FINAL_DIRS = (
    "result/artifacts/generated_tests",
    "result/artifacts/reproduction",
    "result/artifacts/evidence",
)
FINAL_BLIND_PHASES = {
    "phase-a-complete",
    "phase-b-complete",
    "complete",
}
ALLOWED_PROVENANCE = {
    "independent",
    "lead-derived",
    "static-only",
}
ALLOWED_CANDIDATE_STATUS = {
    "independent-confirmed",
    "lead-confirmed",
    "candidate",
    "inconclusive",
    "rejected",
    "not-applicable",
    "environment-blocked",
}
ALLOWED_LEAD_STATUS = {
    "confirmed",
    "rejected",
    "inconclusive",
    "not-applicable",
    "environment-blocked",
}
ALLOWED_SOURCE_CLASSIFICATION = {
    "actionable",
    "non-actionable",
}
ALLOWED_PRIORITIES = {"high", "medium", "low", "not-applicable"}
ALLOWED_COVERAGE_STATUS = {
    "tested",
    "partial",
    "blocked",
    "planned",
    "not-applicable",
}
PRIORITY_WEIGHTS = {"high": 5.0, "medium": 3.0, "low": 1.0}
COMPLETION_WEIGHTS = {
    "tested": 1.0,
    "partial": 0.5,
    "blocked": 0.0,
    "planned": 0.0,
}
ALLOWED_RUNTIME_STATUS = {"measured", "blocked", "unsupported"}
MUTATION_OPERATORS = {
    "condition-negation",
    "boundary-change",
    "authorization-guard-removal",
    "boolean-replacement",
    "return-value-change",
    "state-transition-change",
    "exception-or-rollback-removal",
    "arithmetic-change",
}
CRITICAL_MUTATION_DIRECTIONS = {
    "input-boundary",
    "authorization-ownership",
    "business-logic",
}


def _read_manifest(path: Path, errors: list[str]) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        return {}
    if path.stat().st_size > 1_000_000:
        errors.append("run manifest exceeds 1000000 bytes")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid run manifest: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append("run manifest must be a JSON object")
        return {}
    return value


def _is_artifact_file(root: Path, relative: object, directory: str) -> bool:
    if not isinstance(relative, str) or not relative:
        return False
    candidate = Path(relative)
    if candidate.is_absolute():
        return False
    resolved = (root / candidate).resolve()
    allowed = (root / directory).resolve()
    return (
        allowed in resolved.parents
        and resolved.is_file()
        and resolved.stat().st_size > 0
    )


def _is_code_file(root: Path, relative: object) -> bool:
    if not isinstance(relative, str) or not relative:
        return False
    candidate = Path(relative)
    if candidate.is_absolute():
        return False
    resolved = (root / candidate).resolve()
    code_root = (root / "code").resolve()
    return (
        code_root in resolved.parents
        and resolved.is_file()
    )


def _trace_sequences(root: Path, relative: object) -> set[int] | None:
    if not isinstance(relative, str) or not relative:
        return None
    candidate = Path(relative)
    if candidate.is_absolute():
        return None
    resolved = (root / candidate).resolve()
    trace_root = (root / "logs/trace").resolve()
    if resolved.parent != trace_root or resolved.suffix != ".jsonl":
        return None
    try:
        events = [
            json.loads(line)
            for line in resolved.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    except (OSError, json.JSONDecodeError):
        return None
    sequences = {
        event.get("sequence")
        for event in events
        if isinstance(event, dict) and isinstance(event.get("sequence"), int)
    }
    return sequences


def _load_discovered_answer_paths(root: Path, errors: list[str]) -> set[str]:
    path = root / "result/artifacts/evidence/project-discovery.json"
    if not path.is_file() or path.stat().st_size == 0:
        errors.append(
            "missing project discovery evidence: "
            "result/artifacts/evidence/project-discovery.json"
        )
        return set()
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"invalid project discovery evidence: {exc}")
        return set()
    if not isinstance(value, dict):
        errors.append("project discovery evidence must be a JSON object")
        return set()
    if value.get("file_limit_reached") is not False:
        errors.append("project discovery file scan was truncated")
    if value.get("answer_hint_limit_reached") is not False:
        errors.append("project discovery answer-bearing hint scan was truncated")
    hints = value.get("answer_bearing_path_hints")
    if not isinstance(hints, list):
        errors.append("project discovery answer_bearing_path_hints must be a list")
        return set()
    discovered = set()
    for index, hint in enumerate(hints, start=1):
        if not isinstance(hint, dict) or not isinstance(hint.get("path"), str):
            errors.append(f"project discovery answer hint {index} is invalid")
            continue
        discovered.add(hint["path"])
    return discovered


def _read_json_artifact(
    root: Path,
    relative: object,
    directory: str,
    prefix: str,
    errors: list[str],
) -> dict:
    if not _is_artifact_file(root, relative, directory):
        errors.append(f"{prefix} must reference an existing artifact")
        return {}
    path = root / str(relative)
    if path.stat().st_size > 1_000_000:
        errors.append(f"{prefix} exceeds 1000000 bytes")
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"{prefix} is invalid JSON: {exc}")
        return {}
    if not isinstance(value, dict):
        errors.append(f"{prefix} must contain a JSON object")
        return {}
    return value


def _validate_code_evidence_paths(
    root: Path,
    value: object,
    prefix: str,
    errors: list[str],
) -> list[str]:
    if not isinstance(value, list) or not value:
        errors.append(f"{prefix} must contain project evidence paths")
        return []
    valid = []
    for item in value:
        if not _is_code_file(root, item):
            errors.append(f"{prefix} contains a missing or non-code path: {item}")
        elif isinstance(item, str):
            valid.append(item)
    return valid


def _validate_coverage_plan(
    root: Path,
    manifest: dict,
    candidates_by_id: dict[str, dict],
    errors: list[str],
) -> None:
    classification = manifest.get("system_classification")
    if not isinstance(classification, dict):
        errors.append("run manifest system_classification must be an object")
        primary = []
        secondary = []
    else:
        raw_primary = classification.get("primary_archetypes")
        raw_secondary = classification.get("secondary_archetypes")
        if not isinstance(raw_primary, list) or not raw_primary:
            errors.append("system_classification.primary_archetypes must be non-empty")
            raw_primary = []
        if not isinstance(raw_secondary, list):
            errors.append("system_classification.secondary_archetypes must be a list")
            raw_secondary = []
        primary = [
            item
            for item in raw_primary
            if isinstance(item, str) and item in SYSTEM_ARCHETYPES
        ]
        secondary = [
            item
            for item in raw_secondary
            if isinstance(item, str) and item in SYSTEM_ARCHETYPES
        ]
        if len(primary) != len(raw_primary) or len(secondary) != len(raw_secondary):
            errors.append("system classification contains an unknown archetype")
        selected_profiles = [*primary, *secondary]
        if len(set(selected_profiles)) != len(selected_profiles):
            errors.append("system classification contains duplicate archetypes")
        if "generic-application" in selected_profiles and len(selected_profiles) > 1:
            errors.append("generic-application cannot be combined with specific archetypes")
        if classification.get("confidence") not in {"high", "medium", "low"}:
            errors.append("system classification confidence must be high, medium, or low")
        if not isinstance(classification.get("rationale"), str) or not classification[
            "rationale"
        ].strip():
            errors.append("system classification rationale must be non-empty")
        _validate_code_evidence_paths(
            root,
            classification.get("evidence_paths"),
            "system classification evidence_paths",
            errors,
        )

    catalog = manifest.get("bug_direction_catalog")
    if catalog != list(BUG_DIRECTIONS):
        errors.append("run manifest bug_direction_catalog does not match schema")
    archetype_catalog = manifest.get("system_archetype_catalog")
    if archetype_catalog != list(SYSTEM_ARCHETYPES):
        errors.append("run manifest system_archetype_catalog does not match schema")
    technique_catalog = manifest.get("technique_catalog")
    if technique_catalog != list(TECHNIQUES):
        errors.append("run manifest technique_catalog does not match schema")

    plan = manifest.get("coverage_plan")
    if not isinstance(plan, dict):
        errors.append("run manifest coverage_plan must be an object")
        return
    if plan.get("target_percent") != COVERAGE_TARGET_PERCENT:
        errors.append(f"coverage target must be {COVERAGE_TARGET_PERCENT}")
    claim_scope = plan.get("claim_scope")
    if (
        not isinstance(claim_scope, str)
        or "not Bug recall" not in claim_scope
        or "vulnerability-free" not in claim_scope
    ):
        errors.append("coverage claim_scope must reject Bug-recall guarantees")

    matrix = plan.get("direction_matrix")
    if not isinstance(matrix, list):
        errors.append("coverage_plan.direction_matrix must be a list")
        matrix = []
    direction_ids = [item.get("id") for item in matrix if isinstance(item, dict)]
    valid_direction_ids = [
        item for item in direction_ids if isinstance(item, str)
    ]
    if (
        len(matrix) != len(BUG_DIRECTIONS)
        or len(valid_direction_ids) != len(direction_ids)
        or set(valid_direction_ids) != set(BUG_DIRECTIONS)
    ):
        errors.append("coverage direction matrix must contain every bug direction exactly once")
    if len(valid_direction_ids) != len(set(valid_direction_ids)):
        errors.append("coverage direction matrix contains duplicate directions")

    required_high = set()
    required_specialties = set()
    for profile in primary:
        if profile in SYSTEM_ARCHETYPES:
            required_high.update(SYSTEM_ARCHETYPES[profile]["high_priority"])
            required_specialties.update(
                SYSTEM_ARCHETYPES[profile]["specialty_checks"]
            )

    weighted_numerator = 0.0
    weighted_denominator = 0.0
    uncovered_high = []
    matrix_candidate_ids: set[str] = set()
    for index, entry in enumerate(matrix, start=1):
        prefix = f"coverage_plan.direction_matrix[{index}]"
        if not isinstance(entry, dict):
            errors.append(f"{prefix} must be an object")
            continue
        direction = entry.get("id")
        priority = entry.get("priority")
        status = entry.get("status")
        if direction not in BUG_DIRECTIONS:
            errors.append(f"{prefix}.id is invalid")
        if priority not in ALLOWED_PRIORITIES:
            errors.append(f"{prefix}.priority is invalid")
        if status not in ALLOWED_COVERAGE_STATUS:
            errors.append(f"{prefix}.status is invalid")
        if direction in required_high and priority != "high":
            errors.append(f"{prefix} must be high for the selected primary archetype")
        if not isinstance(entry.get("rationale"), str) or not entry[
            "rationale"
        ].strip():
            errors.append(f"{prefix}.rationale must be non-empty")
        _validate_code_evidence_paths(
            root,
            entry.get("evidence_paths"),
            f"{prefix}.evidence_paths",
            errors,
        )

        planned = entry.get("planned_techniques")
        executed = entry.get("executed_techniques")
        if not isinstance(planned, list) or not all(
            isinstance(item, str) and item in TECHNIQUES for item in planned
        ):
            errors.append(f"{prefix}.planned_techniques is invalid")
            planned = []
        if not isinstance(executed, list) or not all(
            isinstance(item, str) and item in TECHNIQUES for item in executed
        ):
            errors.append(f"{prefix}.executed_techniques is invalid")
            executed = []
        if len(planned) != len(set(planned)) or len(executed) != len(set(executed)):
            errors.append(f"{prefix} contains duplicate techniques")
        if not set(executed).issubset(set(planned)):
            errors.append(f"{prefix} executed techniques were not planned")

        candidate_ids = entry.get("candidate_ids")
        if not isinstance(candidate_ids, list) or not all(
            isinstance(item, str) and item in candidates_by_id
            for item in candidate_ids
        ):
            errors.append(f"{prefix}.candidate_ids is invalid")
            candidate_ids = []
        for candidate_id in candidate_ids:
            matrix_candidate_ids.add(candidate_id)
            if candidates_by_id[candidate_id].get("direction") != direction:
                errors.append(
                    f"{prefix} candidate {candidate_id} has a different direction"
                )

        test_paths = entry.get("test_paths")
        if not isinstance(test_paths, list):
            errors.append(f"{prefix}.test_paths must be a list")
            test_paths = []
        valid_tests = all(
            _is_artifact_file(root, item, "result/artifacts/generated_tests")
            for item in test_paths
        )
        if not valid_tests:
            errors.append(f"{prefix}.test_paths contains a missing generated test")

        blocker_paths = entry.get("blocker_evidence_paths")
        if not isinstance(blocker_paths, list):
            errors.append(f"{prefix}.blocker_evidence_paths must be a list")
            blocker_paths = []

        if priority == "not-applicable":
            if status != "not-applicable":
                errors.append(f"{prefix} not-applicable priority has wrong status")
            if planned or executed or test_paths:
                errors.append(f"{prefix} not-applicable direction must not claim tests")
            continue
        if status == "not-applicable":
            errors.append(f"{prefix} applicable direction cannot be not-applicable")
            continue
        if priority in PRIORITY_WEIGHTS:
            weighted_denominator += PRIORITY_WEIGHTS[priority]
            weighted_numerator += (
                PRIORITY_WEIGHTS[priority] * COMPLETION_WEIGHTS.get(status, 0.0)
            )
        if status == "tested":
            minimum_techniques = 2 if priority == "high" else 1
            if len(executed) < minimum_techniques:
                errors.append(
                    f"{prefix} tested {priority} direction needs "
                    f"{minimum_techniques} executed techniques"
                )
            if not test_paths:
                errors.append(f"{prefix} tested direction must reference generated tests")
        elif status == "partial":
            if not executed or not test_paths:
                errors.append(f"{prefix} partial direction needs an executed test")
        elif status == "blocked":
            if not blocker_paths or not all(
                _is_artifact_file(root, item, "result/artifacts/evidence")
                for item in blocker_paths
            ):
                errors.append(f"{prefix} blocked direction needs blocker evidence")
        if priority == "high" and status != "tested":
            uncovered_high.append(direction)

    missing_candidate_links = sorted(set(candidates_by_id) - matrix_candidate_ids)
    if missing_candidate_links:
        errors.append(
            "candidates missing coverage direction links: "
            + ", ".join(missing_candidate_links[:20])
        )

    calculated = (
        round(100.0 * weighted_numerator / weighted_denominator, 2)
        if weighted_denominator
        else 0.0
    )
    recorded = plan.get("calculated_percent")
    if not isinstance(recorded, (int, float)) or abs(float(recorded) - calculated) > 0.01:
        errors.append(f"coverage calculated_percent must equal {calculated}")

    obligations = plan.get("specialty_obligations")
    if not isinstance(obligations, list):
        errors.append("coverage_plan.specialty_obligations must be a list")
        obligations = []
    obligation_ids = {
        item.get("id")
        for item in obligations
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    if len(obligation_ids) != len(
        [item for item in obligations if isinstance(item, dict)]
    ):
        errors.append("coverage specialty obligations contain duplicate or invalid IDs")
    if not required_specialties.issubset(obligation_ids):
        errors.append("coverage plan is missing required specialty obligations")
    for index, obligation in enumerate(obligations, start=1):
        prefix = f"coverage_plan.specialty_obligations[{index}]"
        if not isinstance(obligation, dict):
            errors.append(f"{prefix} must be an object")
            continue
        if not isinstance(obligation.get("id"), str) or not obligation["id"].strip():
            errors.append(f"{prefix}.id must be non-empty")
        status = obligation.get("status")
        if status not in {"tested", "blocked", "not-applicable"}:
            errors.append(f"{prefix}.status is invalid")
        if not isinstance(obligation.get("rationale"), str) or not obligation[
            "rationale"
        ].strip():
            errors.append(f"{prefix}.rationale must be non-empty")
        if status == "tested":
            tests = obligation.get("test_paths")
            if not isinstance(tests, list) or not tests or not all(
                _is_artifact_file(root, item, "result/artifacts/generated_tests")
                for item in tests
            ):
                errors.append(f"{prefix} tested obligation needs generated tests")
            techniques = obligation.get("executed_techniques")
            if (
                not isinstance(techniques, list)
                or len(set(techniques)) < 2
                or not all(
                    isinstance(item, str) and item in TECHNIQUES
                    for item in techniques
                )
            ):
                errors.append(
                    f"{prefix} tested obligation needs two complementary techniques"
                )
        if status == "blocked":
            blockers = obligation.get("blocker_evidence_paths")
            if not isinstance(blockers, list) or not blockers or not all(
                _is_artifact_file(root, item, "result/artifacts/evidence")
                for item in blockers
            ):
                errors.append(f"{prefix} blocked obligation needs evidence")
        if status == "not-applicable":
            _validate_code_evidence_paths(
                root,
                obligation.get("evidence_paths"),
                f"{prefix}.evidence_paths",
                errors,
            )

    rebalance = plan.get("rebalance")
    if not isinstance(rebalance, dict):
        errors.append("coverage_plan.rebalance must be an object")
    else:
        if rebalance.get("performed") is not True:
            errors.append("coverage rebalance must be performed")
        before = rebalance.get("before_percent")
        after = rebalance.get("after_percent")
        if not isinstance(before, (int, float)) or not 0 <= float(before) <= 100:
            errors.append("coverage rebalance before_percent is invalid")
        if not isinstance(after, (int, float)) or abs(float(after) - calculated) > 0.01:
            errors.append("coverage rebalance after_percent must match final coverage")
        if not isinstance(rebalance.get("changes"), list):
            errors.append("coverage rebalance changes must be a list")
        if not isinstance(rebalance.get("decision_summary"), str) or not rebalance[
            "decision_summary"
        ].strip():
            errors.append("coverage rebalance decision_summary must be non-empty")

    run_status = manifest.get("run_status")
    if run_status not in {"complete", "incomplete"}:
        errors.append("final run_status must be complete or incomplete")
    if run_status == "complete":
        if uncovered_high:
            errors.append(
                "complete run has untested high-priority directions: "
                + ", ".join(sorted(item for item in uncovered_high if item))
            )
        if calculated < COVERAGE_TARGET_PERCENT:
            errors.append(
                f"complete run coverage {calculated} is below {COVERAGE_TARGET_PERCENT}"
            )
        unfinished_obligations = [
            item.get("id")
            for item in obligations
            if isinstance(item, dict)
            and item.get("id") in required_specialties
            and item.get("status") != "tested"
        ]
        if unfinished_obligations:
            errors.append("complete run has unfinished required specialty obligations")
    elif run_status == "incomplete":
        gap_reason = plan.get("coverage_gap_reason")
        if not isinstance(gap_reason, str) or not gap_reason.strip():
            errors.append("incomplete run must explain coverage_gap_reason")


def _validate_runtime_quality(
    root: Path,
    manifest: dict,
    candidates_by_id: dict[str, dict],
    errors: list[str],
) -> None:
    quality = manifest.get("runtime_quality")
    if not isinstance(quality, dict):
        errors.append("run manifest runtime_quality must be an object")
        return

    tool_detection = _read_json_artifact(
        root,
        quality.get("tool_detection_path"),
        "result/artifacts/evidence",
        "runtime_quality.tool_detection_path",
        errors,
    )
    if tool_detection:
        if tool_detection.get("schema_version") != 1:
            errors.append("quality tool detection schema_version must be 1")
        if tool_detection.get("file_limit_reached") is not False:
            errors.append("quality tool detection scan was truncated")
        for field in ("coverage_tools", "mutation_tools"):
            tools = tool_detection.get(field)
            if not isinstance(tools, list) or not tools:
                errors.append(f"quality tool detection {field} must be non-empty")

    run_status = manifest.get("run_status")
    plan = manifest.get("coverage_plan")
    matrix = plan.get("direction_matrix", []) if isinstance(plan, dict) else []
    high_tested = {
        entry.get("id")
        for entry in matrix
        if isinstance(entry, dict)
        and entry.get("priority") == "high"
        and entry.get("status") == "tested"
        and entry.get("id") in BUG_DIRECTIONS
    }
    high_priority = {
        entry.get("id")
        for entry in matrix
        if isinstance(entry, dict)
        and entry.get("priority") == "high"
        and entry.get("id") in BUG_DIRECTIONS
    }

    coverage = quality.get("coverage")
    if not isinstance(coverage, dict):
        errors.append("runtime_quality.coverage must be an object")
        coverage = {}
    coverage_status = coverage.get("status")
    if coverage_status not in ALLOWED_RUNTIME_STATUS:
        errors.append("runtime coverage status must be measured, blocked, or unsupported")
    if run_status == "complete" and coverage_status != "measured":
        errors.append("complete run requires measured runtime code coverage")
    coverage_hits: list[dict] = []
    if coverage_status == "measured":
        if not isinstance(coverage.get("tool"), str) or not coverage["tool"].strip():
            errors.append("measured runtime coverage must identify its tool")
        if not isinstance(coverage.get("native"), bool):
            errors.append("measured runtime coverage must declare native true or false")
        commands = coverage.get("commands")
        if not isinstance(commands, list) or not commands or not all(
            isinstance(item, str) and item.strip() for item in commands
        ):
            errors.append("measured runtime coverage must record executed commands")
        scope_files = coverage.get("scope_files")
        if not isinstance(scope_files, list) or not scope_files:
            errors.append("measured runtime coverage must identify product source files")
        elif not all(_is_code_file(root, item) for item in scope_files):
            errors.append("runtime coverage scope_files must exist under code/")
        report_paths = coverage.get("report_paths")
        if not isinstance(report_paths, list) or not report_paths or not all(
            _is_artifact_file(root, item, "result/artifacts/evidence")
            for item in report_paths
        ):
            errors.append("measured runtime coverage must reference raw coverage reports")
        metrics = coverage.get("metrics")
        if not isinstance(metrics, dict):
            errors.append("runtime coverage metrics must be an object")
        else:
            numeric_metrics = 0
            for name in ("line_percent", "branch_percent", "function_percent"):
                value = metrics.get(name)
                if value is None:
                    continue
                if not isinstance(value, (int, float)) or not 0 <= float(value) <= 100:
                    errors.append(f"runtime coverage metric {name} is invalid")
                else:
                    numeric_metrics += 1
            if numeric_metrics == 0:
                errors.append("runtime coverage must contain at least one measured metric")
            if metrics.get("branch_percent") is None:
                limitations = coverage.get("metric_limitations")
                if not isinstance(limitations, str) or not limitations.strip():
                    errors.append(
                        "missing branch coverage requires metric_limitations"
                    )
        hits = coverage.get("key_path_hits")
        if not isinstance(hits, list) or not hits:
            errors.append("runtime coverage must record key_path_hits")
            hits = []
        seen_hit_ids: set[str] = set()
        for index, hit in enumerate(hits, start=1):
            prefix = f"runtime_quality.coverage.key_path_hits[{index}]"
            if not isinstance(hit, dict):
                errors.append(f"{prefix} must be an object")
                continue
            hit_id = hit.get("id")
            direction = hit.get("direction")
            candidate_id = hit.get("candidate_id")
            if not isinstance(hit_id, str) or not hit_id.strip():
                errors.append(f"{prefix}.id must be non-empty")
            elif hit_id in seen_hit_ids:
                errors.append(f"{prefix}.id duplicates another hit")
            else:
                seen_hit_ids.add(hit_id)
            if direction not in BUG_DIRECTIONS:
                errors.append(f"{prefix}.direction is invalid")
            if candidate_id not in (None, "") and candidate_id not in candidates_by_id:
                errors.append(f"{prefix}.candidate_id is invalid")
            if not _is_code_file(root, hit.get("source_path")):
                errors.append(f"{prefix}.source_path must exist under code/")
            if not isinstance(hit.get("symbol"), str) or not hit["symbol"].strip():
                errors.append(f"{prefix}.symbol must be non-empty")
            if not _is_artifact_file(
                root,
                hit.get("evidence_path"),
                "result/artifacts/evidence",
            ):
                errors.append(f"{prefix}.evidence_path must exist")
            coverage_hits.append(hit)
        hit_directions = {
            hit.get("direction")
            for hit in coverage_hits
            if isinstance(hit, dict)
        }
        missing_high_hits = sorted(high_tested - hit_directions)
        if missing_high_hits:
            errors.append(
                "runtime coverage is missing key-path evidence for high-risk directions: "
                + ", ".join(missing_high_hits)
            )
        confirmed_ids = {
            candidate_id
            for candidate_id, candidate in candidates_by_id.items()
            if candidate.get("status") in {"independent-confirmed", "lead-confirmed"}
        }
        covered_candidate_ids = {
            hit.get("candidate_id")
            for hit in coverage_hits
            if isinstance(hit, dict)
        }
        missing_candidate_hits = sorted(confirmed_ids - covered_candidate_ids)
        if missing_candidate_hits:
            errors.append(
                "confirmed candidates lack runtime target-code coverage evidence: "
                + ", ".join(missing_candidate_hits)
            )
    elif coverage_status in {"blocked", "unsupported"}:
        reason = coverage.get("unavailable_reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append("unmeasured runtime coverage requires unavailable_reason")

    mutation = quality.get("mutation")
    if not isinstance(mutation, dict):
        errors.append("runtime_quality.mutation must be an object")
        return
    mutation_status = mutation.get("status")
    if mutation_status not in ALLOWED_RUNTIME_STATUS:
        errors.append("mutation status must be measured, blocked, or unsupported")
    if run_status == "complete" and mutation_status != "measured":
        errors.append("complete run requires measured targeted mutation testing")
    if mutation.get("targeted_mutant_budget") != TARGETED_MUTANT_BUDGET:
        errors.append(
            f"targeted_mutant_budget must be {TARGETED_MUTANT_BUDGET}"
        )
    if mutation.get("target_score_percent") != MUTATION_TARGET_PERCENT:
        errors.append(
            f"mutation target_score_percent must be {MUTATION_TARGET_PERCENT}"
        )
    if mutation_status in {"blocked", "unsupported"}:
        reason = mutation.get("unavailable_reason")
        if not isinstance(reason, str) or not reason.strip():
            errors.append("unmeasured mutation testing requires unavailable_reason")
        return
    if mutation_status != "measured":
        return

    if not isinstance(mutation.get("tool"), str) or not mutation["tool"].strip():
        errors.append("measured mutation testing must identify its tool or method")
    if mutation.get("isolated_copy_confirmed") is not True:
        errors.append("mutation testing must confirm use of an isolated source copy")
    if mutation.get("baseline_passed") is not True:
        errors.append("mutation testing requires a passing baseline")
    if mutation.get("original_code_unchanged") is not True:
        errors.append("mutation testing must confirm original code remained unchanged")
    mutation_commands = mutation.get("commands")
    if not isinstance(mutation_commands, list) or not mutation_commands or not all(
        isinstance(item, str) and item.strip() for item in mutation_commands
    ):
        errors.append("measured mutation testing must record executed commands")
    for field in ("baseline_evidence_path", "isolation_evidence_path"):
        if not _is_artifact_file(
            root,
            mutation.get(field),
            "result/artifacts/evidence",
        ):
            errors.append(f"runtime_quality.mutation.{field} must exist")

    mutation_results = _read_json_artifact(
        root,
        mutation.get("results_path"),
        "result/artifacts/evidence",
        "runtime_quality.mutation.results_path",
        errors,
    )
    mutants = mutation_results.get("mutants", []) if mutation_results else []
    calculated_summary: dict = {}
    if mutation_results:
        try:
            calculated_summary = score_mutants(mutation_results)
        except ValueError as exc:
            errors.append(f"invalid mutation results: {exc}")
    summary = mutation.get("summary")
    if not isinstance(summary, dict):
        errors.append("runtime_quality.mutation.summary must be an object")
    elif calculated_summary and summary != calculated_summary:
        errors.append("runtime mutation summary does not match mutation results")

    mutant_ids: set[str] = set()
    mutants_by_id: dict[str, dict] = {}
    if not isinstance(mutants, list) or not mutants:
        errors.append("measured mutation testing must contain mutants")
        mutants = []
    for index, mutant in enumerate(mutants, start=1):
        prefix = f"mutation results mutant[{index}]"
        if not isinstance(mutant, dict):
            errors.append(f"{prefix} must be an object")
            continue
        mutant_id = mutant.get("id")
        direction = mutant.get("direction")
        if not isinstance(mutant_id, str) or not mutant_id.strip():
            errors.append(f"{prefix}.id must be non-empty")
        elif mutant_id in mutant_ids:
            errors.append(f"{prefix}.id duplicates another mutant")
        else:
            mutant_ids.add(mutant_id)
            mutants_by_id[mutant_id] = mutant
        if direction not in BUG_DIRECTIONS:
            errors.append(f"{prefix}.direction is invalid")
        if mutant.get("operator") not in MUTATION_OPERATORS:
            errors.append(f"{prefix}.operator is invalid")
        if not _is_code_file(root, mutant.get("source_path")):
            errors.append(f"{prefix}.source_path must reference original code")
        if not isinstance(mutant.get("critical"), bool):
            errors.append(f"{prefix}.critical must be boolean")
        mutant_status = mutant.get("status")
        if mutant_status not in MUTANT_STATUSES:
            errors.append(f"{prefix}.status is invalid")
        elif mutant_status in {"invalid", "timeout", "not-covered", "blocked"}:
            if not isinstance(mutant.get("reason"), str) or not mutant[
                "reason"
            ].strip():
                errors.append(f"{prefix}.reason is required for {mutant_status}")
        if not _is_artifact_file(
            root,
            mutant.get("diff_path"),
            "result/artifacts/evidence",
        ):
            errors.append(f"{prefix}.diff_path must exist")
        if not _is_artifact_file(
            root,
            mutant.get("evidence_path"),
            "result/artifacts/evidence",
        ):
            errors.append(f"{prefix}.evidence_path must exist")
        if not _is_artifact_file(
            root,
            mutant.get("test_path"),
            "result/artifacts/generated_tests",
        ):
            errors.append(f"{prefix}.test_path must reference a generated test")

    assessments = mutation.get("direction_assessments")
    if not isinstance(assessments, list):
        errors.append("mutation direction_assessments must be a list")
        assessments = []
    assessed_directions: set[str] = set()
    for index, assessment in enumerate(assessments, start=1):
        prefix = f"runtime_quality.mutation.direction_assessments[{index}]"
        if not isinstance(assessment, dict):
            errors.append(f"{prefix} must be an object")
            continue
        direction = assessment.get("direction")
        status = assessment.get("status")
        ids = assessment.get("mutant_ids")
        if direction not in high_priority:
            errors.append(f"{prefix}.direction must be a high-risk direction")
        elif direction in assessed_directions:
            errors.append(f"{prefix}.direction duplicates another assessment")
        else:
            assessed_directions.add(direction)
        if status not in {"tested", "not-applicable", "blocked"}:
            errors.append(f"{prefix}.status is invalid")
        if not isinstance(assessment.get("rationale"), str) or not assessment[
            "rationale"
        ].strip():
            errors.append(f"{prefix}.rationale must be non-empty")
        if status == "tested":
            if not isinstance(ids, list) or not ids or not all(
                isinstance(item, str)
                and item in mutants_by_id
                and mutants_by_id[item].get("direction") == direction
                for item in ids
            ):
                errors.append(f"{prefix}.mutant_ids must reference matching mutants")
                ids = []
            valid_ids = [
                item
                for item in ids
                if mutants_by_id[item].get("status") in {"killed", "survived"}
            ]
            if not valid_ids:
                errors.append(f"{prefix} needs at least one valid killed or survived mutant")
            if direction in CRITICAL_MUTATION_DIRECTIONS and not any(
                mutants_by_id[item].get("critical") is True
                for item in valid_ids
            ):
                errors.append(f"{prefix} needs a critical decision mutant")
        elif status == "not-applicable":
            evidence_paths = assessment.get("evidence_paths")
            _validate_code_evidence_paths(
                root,
                evidence_paths,
                f"{prefix}.evidence_paths",
                errors,
            )
            if ids:
                errors.append(f"{prefix} not-applicable assessment cannot list mutants")
        elif status == "blocked":
            blocker_paths = assessment.get("blocker_evidence_paths")
            if not isinstance(blocker_paths, list) or not blocker_paths or not all(
                _is_artifact_file(root, item, "result/artifacts/evidence")
                for item in blocker_paths
            ):
                errors.append(f"{prefix} blocked assessment needs evidence")

    missing_assessments = sorted(high_tested - assessed_directions)
    if missing_assessments:
        errors.append(
            "mutation testing is missing high-risk direction assessments: "
            + ", ".join(missing_assessments)
        )
    if run_status == "complete":
        blocked_assessments = [
            item.get("direction")
            for item in assessments
            if isinstance(item, dict) and item.get("status") == "blocked"
        ]
        if blocked_assessments:
            errors.append("complete run has blocked high-risk mutation assessments")
        if calculated_summary:
            if calculated_summary["score_percent"] < MUTATION_TARGET_PERCENT:
                errors.append(
                    "complete run mutation score "
                    f"{calculated_summary['score_percent']} is below "
                    f"{MUTATION_TARGET_PERCENT}"
                )
            if calculated_summary["critical_survivors"]:
                errors.append(
                    "complete run has unresolved critical mutants: "
                    + ", ".join(calculated_summary["critical_survivors"])
                )


def _validate_lead_registry(
    root: Path,
    manifest: dict,
    candidates_by_id: dict[str, dict],
    errors: list[str],
) -> None:
    lead_validation = manifest.get("lead_validation")
    if not isinstance(lead_validation, dict):
        errors.append("run manifest lead_validation must be an object")
        return
    if lead_validation.get("required") is not True:
        errors.append("run manifest must require project lead validation")
    if lead_validation.get("all_discovered_sources_reviewed") is not True:
        errors.append("not all discovered lead sources were reviewed")
    if lead_validation.get("all_actionable_leads_dispositioned") is not True:
        errors.append("not all actionable project leads were dispositioned")

    sources = lead_validation.get("source_registry")
    if not isinstance(sources, list):
        errors.append("lead_validation.source_registry must be a list")
        sources = []
    source_paths: set[str] = set()
    actionable_paths: set[str] = set()
    for index, source in enumerate(sources, start=1):
        prefix = f"lead_validation.source_registry[{index}]"
        if not isinstance(source, dict):
            errors.append(f"{prefix} must be an object")
            continue
        path = source.get("path")
        classification = source.get("classification")
        reason = source.get("reason")
        if not isinstance(path, str) or not path.strip():
            errors.append(f"{prefix}.path must be a non-empty string")
            continue
        if path in source_paths:
            errors.append(f"{prefix}.path duplicates another source")
        source_paths.add(path)
        if not _is_code_file(root, path):
            errors.append(f"{prefix}.path must reference an existing file in code/")
        if classification not in ALLOWED_SOURCE_CLASSIFICATION:
            errors.append(f"{prefix}.classification is invalid")
        if not isinstance(reason, str) or not reason.strip():
            errors.append(f"{prefix}.reason must be a non-empty string")
        if source.get("reviewed") is not True:
            errors.append(f"{prefix} must be marked reviewed")
        if classification == "actionable":
            actionable_paths.add(path)

    discovered_paths = _load_discovered_answer_paths(root, errors)
    missing_sources = sorted(discovered_paths - source_paths)
    if missing_sources:
        errors.append(
            "discovered answer-bearing sources missing review entries: "
            + ", ".join(missing_sources[:20])
        )
    blind = manifest.get("blind_analysis")
    blind_paths = blind.get("answer_bearing_paths", []) if isinstance(blind, dict) else []
    if isinstance(blind_paths, list) and set(blind_paths) != source_paths:
        errors.append(
            "blind_analysis.answer_bearing_paths must match reviewed lead sources"
        )

    leads = lead_validation.get("lead_registry")
    if not isinstance(leads, list):
        errors.append("lead_validation.lead_registry must be a list")
        leads = []
    lead_ids: set[str] = set()
    lead_source_paths: set[str] = set()
    referenced_candidate_ids: set[str] = set()
    for index, lead in enumerate(leads, start=1):
        prefix = f"lead_validation.lead_registry[{index}]"
        if not isinstance(lead, dict):
            errors.append(f"{prefix} must be an object")
            continue
        lead_id = lead.get("id")
        source_path = lead.get("source_path")
        status = lead.get("status")
        candidate_id = lead.get("candidate_id")
        if not isinstance(lead_id, str) or not lead_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string")
        elif lead_id in lead_ids:
            errors.append(f"{prefix}.id duplicates another lead")
        else:
            lead_ids.add(lead_id)
        if source_path not in source_paths:
            errors.append(f"{prefix}.source_path is not in source_registry")
        elif isinstance(source_path, str):
            lead_source_paths.add(source_path)
        if not isinstance(lead.get("claim_summary"), str) or not lead[
            "claim_summary"
        ].strip():
            errors.append(f"{prefix}.claim_summary must be a non-empty string")
        if status not in ALLOWED_LEAD_STATUS:
            errors.append(f"{prefix}.status is invalid")
        if not isinstance(candidate_id, str) or candidate_id not in candidates_by_id:
            errors.append(f"{prefix}.candidate_id must reference candidate_registry")
            continue
        candidate = candidates_by_id[candidate_id]
        referenced_candidate_ids.add(candidate_id)
        if candidate.get("provenance") != "lead-derived":
            errors.append(f"{prefix} candidate must have lead-derived provenance")
        if candidate.get("lead_source") != source_path:
            errors.append(f"{prefix} candidate lead_source does not match source_path")
        expected_candidate_status = {
            "confirmed": "lead-confirmed",
            "rejected": "rejected",
            "inconclusive": "inconclusive",
            "not-applicable": "not-applicable",
            "environment-blocked": "environment-blocked",
        }.get(status)
        if candidate.get("status") != expected_candidate_status:
            errors.append(
                f"{prefix} status does not match referenced candidate status"
            )

        if status in {"rejected", "inconclusive"}:
            if not _is_artifact_file(
                root,
                candidate.get("generated_test"),
                "result/artifacts/generated_tests",
            ):
                errors.append(
                    f"{prefix} must reference an executed current-run generated test"
                )
        if status != "confirmed":
            evidence = candidate.get("evidence_paths")
            if (
                not isinstance(evidence, list)
                or not evidence
                or not all(
                    _is_artifact_file(root, item, "result/artifacts/evidence")
                    for item in evidence
                )
            ):
                errors.append(f"{prefix} must reference disposition evidence")
            sequences = _trace_sequences(root, candidate.get("trace_file"))
            decision_sequences = candidate.get("execution_trace_sequences")
            if (
                sequences is None
                or not isinstance(decision_sequences, list)
                or not decision_sequences
                or not all(
                    isinstance(item, int) and item > 0
                    for item in decision_sequences
                )
                or not set(decision_sequences).issubset(sequences)
            ):
                errors.append(f"{prefix} must reference valid disposition trace events")

    missing_actionable = sorted(actionable_paths - lead_source_paths)
    if missing_actionable:
        errors.append(
            "actionable lead sources have no registered leads: "
            + ", ".join(missing_actionable[:20])
        )
    unregistered_candidates = sorted(
        candidate_id
        for candidate_id, candidate in candidates_by_id.items()
        if candidate.get("provenance") == "lead-derived"
        and candidate_id not in referenced_candidate_ids
    )
    if unregistered_candidates:
        errors.append(
            "lead-derived candidates missing lead registry entries: "
            + ", ".join(unregistered_candidates[:20])
        )


def _validate_manifest(root: Path, manifest: dict, errors: list[str]) -> None:
    if not manifest:
        return
    if manifest.get("schema_version") != 5:
        errors.append("run manifest schema_version must be 5")
    if manifest.get("independent_run") is not True:
        errors.append("run manifest must declare independent_run=true")

    portfolio = manifest.get("strategy_portfolio")
    selected = manifest.get("selected_strategies")
    minimum = manifest.get("minimum_strategy_families")
    if not isinstance(portfolio, list) or not all(
        isinstance(item, str) and item for item in portfolio
    ):
        errors.append("run manifest strategy_portfolio must be a string list")
        portfolio = []
    if not isinstance(minimum, int) or minimum < 3:
        errors.append("run manifest minimum_strategy_families must be at least 3")
        minimum = 3
    if not isinstance(selected, list) or not all(
        isinstance(item, str) and item for item in selected
    ):
        errors.append("run manifest selected_strategies must be a string list")
        selected = []
    if len(set(selected)) != len(selected):
        errors.append("run manifest selected_strategies contains duplicates")
    if len(selected) < minimum:
        errors.append(
            f"run manifest selects {len(selected)} strategies; at least {minimum} required"
        )
    unknown = sorted(set(selected) - set(portfolio))
    if unknown:
        errors.append(f"run manifest selects unknown strategies: {unknown}")

    target = manifest.get("complex_project_strategy_target")
    if not isinstance(target, int) or target < 4:
        errors.append("run manifest complex_project_strategy_target must be at least 4")
        target = 4
    complexity = manifest.get("project_complexity")
    if not isinstance(complexity, dict):
        errors.append("run manifest project_complexity must be an object")
    else:
        is_complex = complexity.get("is_complex")
        reasons = complexity.get("reasons")
        exception = complexity.get("strategy_target_exception")
        if not isinstance(is_complex, bool):
            errors.append("run manifest project_complexity.is_complex must be boolean")
        if not isinstance(reasons, list) or not all(
            isinstance(item, str) and item for item in reasons
        ):
            errors.append("run manifest project complexity reasons must be a string list")
        if (
            is_complex is True
            and len(selected) < target
            and (not isinstance(exception, str) or not exception.strip())
        ):
            errors.append(
                "complex project selected fewer than target strategies without an exception"
            )

    blind = manifest.get("blind_analysis")
    if not isinstance(blind, dict):
        errors.append("run manifest blind_analysis must be an object")
    else:
        if blind.get("phase") not in FINAL_BLIND_PHASES:
            errors.append("run manifest blind analysis is not complete")
        if blind.get("candidate_provenance_required") is not True:
            errors.append("run manifest must require candidate provenance")
        if blind.get("first_pass_fixed_before_answer_review") is not True:
            errors.append(
                "run manifest must confirm first pass was fixed before answer review"
            )
        paths = blind.get("answer_bearing_paths")
        if not isinstance(paths, list) or not all(isinstance(item, str) for item in paths):
            errors.append("run manifest answer_bearing_paths must be a string list")

    coverage = manifest.get("coverage_dimensions")
    if (
        not isinstance(coverage, list)
        or not all(isinstance(item, str) and item for item in coverage)
        or len(set(coverage)) < 6
    ):
        errors.append("run manifest must retain at least six coverage dimensions")
    techniques = manifest.get("required_test_techniques")
    if (
        not isinstance(techniques, list)
        or not all(isinstance(item, str) and item for item in techniques)
        or len(set(techniques)) < 4
    ):
        errors.append("run manifest must retain required test techniques")
    candidates = manifest.get("candidate_registry")
    if not isinstance(candidates, list):
        errors.append("run manifest candidate_registry must be a list")
        candidates = []
    candidate_ids: set[str] = set()
    candidates_by_id: dict[str, dict] = {}
    classification = manifest.get("system_classification")
    selected_archetypes = set()
    if isinstance(classification, dict):
        for field in ("primary_archetypes", "secondary_archetypes"):
            values = classification.get(field)
            if isinstance(values, list):
                selected_archetypes.update(
                    item
                    for item in values
                    if isinstance(item, str) and item in SYSTEM_ARCHETYPES
                )
    for index, candidate in enumerate(candidates, start=1):
        prefix = f"candidate_registry[{index}]"
        if not isinstance(candidate, dict):
            errors.append(f"{prefix} must be an object")
            continue
        candidate_id = candidate.get("id")
        provenance = candidate.get("provenance")
        direction = candidate.get("direction")
        archetypes = candidate.get("system_archetypes")
        strategy = candidate.get("strategy")
        status = candidate.get("status")
        if not isinstance(candidate_id, str) or not candidate_id.strip():
            errors.append(f"{prefix}.id must be a non-empty string")
        elif candidate_id in candidate_ids:
            errors.append(f"{prefix}.id duplicates another candidate")
        else:
            candidate_ids.add(candidate_id)
            candidates_by_id[candidate_id] = candidate
        if not isinstance(candidate.get("formed_at"), str) or not candidate[
            "formed_at"
        ].strip():
            errors.append(f"{prefix}.formed_at must be a non-empty string")
        if provenance not in ALLOWED_PROVENANCE:
            errors.append(f"{prefix}.provenance is invalid")
        if direction not in BUG_DIRECTIONS:
            errors.append(f"{prefix}.direction is invalid")
        if not isinstance(archetypes, list) or not archetypes or not all(
            isinstance(item, str) and item in SYSTEM_ARCHETYPES
            for item in archetypes
        ):
            errors.append(f"{prefix}.system_archetypes is invalid")
        elif not set(archetypes).issubset(selected_archetypes):
            errors.append(f"{prefix}.system_archetypes were not selected for this run")
        if provenance == "lead-derived":
            if not isinstance(candidate.get("lead_source"), str) or not candidate[
                "lead_source"
            ].strip():
                errors.append(f"{prefix}.lead_source must be a non-empty string")
        if strategy not in portfolio:
            errors.append(f"{prefix}.strategy is not in strategy_portfolio")
        if status not in ALLOWED_CANDIDATE_STATUS:
            errors.append(f"{prefix}.status is invalid")
        if status in {"independent-confirmed", "lead-confirmed"}:
            if status == "independent-confirmed" and provenance != "independent":
                errors.append(f"{prefix} independent confirmation has wrong provenance")
            if status == "lead-confirmed" and provenance != "lead-derived":
                errors.append(f"{prefix} lead confirmation has wrong provenance")
            test_path = candidate.get("generated_test")
            reproduction = candidate.get("reproduction")
            reruns = candidate.get("rerun_trace_sequences")
            evidence = candidate.get("evidence_paths")
            trace_file = candidate.get("trace_file")
            initial_sequence = candidate.get("initial_trace_sequence")
            control_sequence = candidate.get("control_trace_sequence")
            if not _is_artifact_file(
                root,
                test_path,
                "result/artifacts/generated_tests",
            ):
                errors.append(f"{prefix}.generated_test must reference an existing test")
            if not _is_artifact_file(
                root,
                reproduction,
                "result/artifacts/reproduction",
            ):
                errors.append(
                    f"{prefix}.reproduction must reference an existing reproduction"
                )
            if (
                not isinstance(reruns, list)
                or not all(isinstance(item, int) and item > 0 for item in reruns)
                or len(set(reruns)) < 3
            ):
                errors.append(f"{prefix} must reference at least three rerun trace sequences")
                reruns = []
            sequences = _trace_sequences(root, trace_file)
            if sequences is None:
                errors.append(f"{prefix}.trace_file must reference an existing JSONL trace")
            else:
                required_sequences = [initial_sequence, control_sequence, *reruns]
                if not all(
                    isinstance(item, int) and item > 0 for item in required_sequences
                ):
                    errors.append(
                        f"{prefix} must reference initial, control, and rerun trace sequences"
                    )
                elif not set(required_sequences).issubset(sequences):
                    errors.append(f"{prefix} references trace sequences that do not exist")
            if (
                not isinstance(evidence, list)
                or len(evidence) < 3
                or not all(
                    _is_artifact_file(root, item, "result/artifacts/evidence")
                    for item in evidence
                )
                or len(set(evidence)) < 3
            ):
                errors.append(
                    f"{prefix} must reference at least three existing evidence files"
                )

    _validate_coverage_plan(root, manifest, candidates_by_id, errors)
    _validate_runtime_quality(root, manifest, candidates_by_id, errors)
    _validate_lead_registry(root, manifest, candidates_by_id, errors)

    metrics = manifest.get("track_metrics")
    if not isinstance(metrics, dict):
        errors.append("run manifest track_metrics must be an object")
    else:
        expected_metrics = {
            "independent_candidates": sum(
                1
                for candidate in candidates
                if isinstance(candidate, dict)
                and candidate.get("provenance") == "independent"
            ),
            "lead_candidates": sum(
                1
                for candidate in candidates
                if isinstance(candidate, dict)
                and candidate.get("provenance") == "lead-derived"
            ),
            "independent_confirmed": sum(
                1
                for candidate in candidates
                if isinstance(candidate, dict)
                and candidate.get("status") == "independent-confirmed"
            ),
            "lead_confirmed": sum(
                1
                for candidate in candidates
                if isinstance(candidate, dict)
                and candidate.get("status") == "lead-confirmed"
            ),
        }
        expected_metrics["total_confirmed"] = (
            expected_metrics["independent_confirmed"]
            + expected_metrics["lead_confirmed"]
        )
        for name, expected in expected_metrics.items():
            if metrics.get(name) != expected:
                errors.append(
                    f"run manifest track_metrics.{name} must equal {expected}"
                )

    allocation = manifest.get("budget_allocation_percent")
    if (
        not isinstance(allocation, dict)
        or not allocation
        or not all(isinstance(value, int) for value in allocation.values())
        or sum(allocation.values()) != 100
    ):
        errors.append("run manifest budget allocation must contain integer values totaling 100")


def _validate_source_integrity(root: Path, errors: list[str]) -> None:
    saved_path = root / "result/artifacts/evidence/source-before.json"
    if not saved_path.is_file() or saved_path.stat().st_size == 0:
        errors.append("missing source snapshot: result/artifacts/evidence/source-before.json")
        return
    try:
        expected = json.loads(saved_path.read_text(encoding="utf-8"))
        file_count = int(expected.get("file_count", 0))
        total_bytes = int(expected.get("total_bytes", 0))
        current = snapshot(
            root,
            Path("code"),
            max_files=min(100_000, max(20_000, file_count + 1)),
            max_bytes=min(2_000_000_000, max(512_000_000, total_bytes + 1)),
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        errors.append(f"unable to verify source snapshot: {exc}")
        return
    expected_comparable = dict(expected)
    current_comparable = dict(current)
    expected_comparable.pop("generated_at", None)
    current_comparable.pop("generated_at", None)
    if expected_comparable != current_comparable:
        errors.append("source integrity check failed: code/ differs from source-before.json")


def validate_submission(root: Path) -> list[str]:
    root = root.resolve()
    errors = validate(root)
    for relative in FINAL_FILES:
        path = root / relative
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty final file: {relative}")
    for relative in FINAL_DIRS:
        if not (root / relative).is_dir():
            errors.append(f"missing final directory: {relative}")
    manifest = _read_manifest(root / "result/run_manifest.json", errors)
    _validate_manifest(root, manifest, errors)
    generated_tests = root / "result/artifacts/generated_tests"
    if generated_tests.is_dir() and not any(
        path.is_file() for path in generated_tests.rglob("*")
    ):
        errors.append("no generated test file found")
    _validate_source_integrity(root, errors)
    traces = sorted((root / "logs/trace").glob("*.jsonl"))
    if not traces:
        errors.append("no JSONL trace found in logs/trace")
    for trace in traces:
        valid, message = verify(trace)
        if not valid:
            errors.append(f"invalid trace {trace.name}: {message}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    errors = validate_submission(args.root)
    if errors:
        print("Submission validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Submission validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
