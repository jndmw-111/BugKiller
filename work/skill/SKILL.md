---
name: legacy-system-vulnerability-hunter
description: Use when an AI agent must inspect an authorized unknown codebase in code/, apply multiple vulnerability strategies in one independent run, generate and execute tests, degrade gracefully when the full system cannot start, and produce reproducible evidence and audit records.
---

# Legacy System Vulnerability Hunter

Treat `code/` as authorized, unknown, and read-only. Work with the file,
terminal, and local test capabilities actually available; do not depend on
brand-specific Agent features. Source analysis may create candidates, but only
executed evidence can confirm a Bug.

## Workflow

1. Start a self-contained run with a unique ID. Do not inherit findings or
   generated tests from earlier runs.
2. Read [project-discovery.md](references/project-discovery.md). Perform a blind
   discovery phase, temporarily quarantine answer-bearing tutorials, solutions,
   advisories, and fix notes, then inventory the project by subproject and entry
   point.
3. Read [system-profiles.md](references/system-profiles.md). Classify the target,
   assess all universal bug directions, and elevate archetype-specific risks.
4. Build an attack-surface matrix from ingress through identity, parsing,
   authorization, state, data sinks, output contexts, and external boundaries.
   Write the verified profile to `result/project_profile.md`.
5. Read [strategy-portfolio.md](references/strategy-portfolio.md). Apply at
   least three independent strategy families, targeting four for complex
   projects. Record applicability and coverage gaps.
6. Record each candidate as: provenance, direction, strategy, target, observation,
   invariant, trigger class, expected safe behavior, failure signal,
   controllability, reachability, observability, confidence, and
   false-positive checks.
7. Complete a breadth pass before a depth pass. Prefer hypotheses across
   different interfaces, roles, states, and data flows over minor variants of
   an answer-bearing example.
8. After fixing the independent first pass, review every quarantined source.
   Register every actionable lead, dynamically test it, and report confirmed,
   rejected, inconclusive, not-applicable, or environment-blocked outcomes.
   Do not omit lead-derived bugs; include confirmed ones in the total Bug count.
9. Read [test-strategy.md](references/test-strategy.md). Use applicable
   boundary, differential, metamorphic, authorization-matrix, state-machine,
   failure-path, encoding, and configuration techniques.
10. Generate concrete tests during this run under
   `result/artifacts/generated_tests/`; never present old, preset, or
   answer-derived tests as independent current-run discovery.
11. Run `runtime_runner.py inspect`, verify declared commands, and establish the
    smallest executable baseline. Use `runtime_runner.py exec` for writing
    builds/tests and `runtime_runner.py service` for a localhost service plus a
    current-run generated probe. Preserve every report in the runtime execution
    registry.
12. Attempt the normal build and test path. If the complete system cannot run,
    follow [execution-fallback.md](references/execution-fallback.md) and continue
    through independently testable layers rather than ending the run.
13. Execute bounded tests against real target code, validate normal controls,
    and separate product
   behavior from build, dependency, environment, state, and test-code failures.
14. Read [runtime-quality.md](references/runtime-quality.md). Use an available
    target-language coverage tool to prove key product paths executed. Then run
    bounded targeted mutation tests only in a disposable isolated copy. Improve
    tests that let critical authorization, business-rule, state, or boundary
    mutants survive.
15. Recalculate risk-weighted coverage after the breadth pass, then rebalance
    remaining budget toward uncovered high-risk directions and specialty
    obligations. A complete run targets at least 95% weighted dynamic-test
    coverage; this is not a claim of 95% Bug recall.
16. A complete run also requires measured runtime coverage, key-path evidence
    for high-risk directions and confirmed candidates, no unresolved critical
    mutant, and at least 80% targeted mutation score. Unsupported instrumentation
    makes the run incomplete but must not stop other executable strategies.
17. Minimize credible triggers under `result/artifacts/reproduction/` and
    independently repeat each from comparable state at least three times.
    Log every execution and rerun as a separate trace event.
18. Apply [evidence-standard.md](references/evidence-standard.md). Label results
    independent-confirmed, lead-confirmed, candidate,
    inconclusive, rejected, or environment-blocked.
19. Follow [reporting-format.md](references/reporting-format.md), write
    `result/output.md`, and log concise decisions, commands, results, strategy,
    fallback level, and evidence paths in `logs/trace/`.

## Safety And Stop Rules

Follow [safety-policy.md](references/safety-policy.md). Never modify `code/`,
contact non-local systems, destroy data, elevate privileges, establish
persistence, execute untrusted remote scripts, or expose secrets.

Stop only the unsafe or exhausted test line. Continue other strategies and
testable modules when one build, service, dependency, candidate, or subsystem is
blocked. End the full run after the bounded strategy portfolio is exhausted or
no safe executable surface remains.

Never preload versions, CVEs, known vulnerabilities, answer keys, Bug
locations, or trigger methods. If the repository contains them, register and
temporarily quarantine them until independent candidates and first-pass tests
are fixed, then review and validate every actionable lead. Continue independent
hunting after lead validation. Finding no confirmed Bug is valid only when both
tracks, fallback attempts, evidence, and limitations are reported.
