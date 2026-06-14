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
2. Read [project-discovery.md](references/project-discovery.md), inventory the
   project by subproject and entry point, and write `result/project_profile.md`.
3. Read [strategy-portfolio.md](references/strategy-portfolio.md). Apply at
   least three relevant strategy families in this run; record why any family is
   not applicable.
4. Identify interfaces, trust boundaries, state changes, parsers,
   authorization decisions, error paths, and documented or code-enforced
   invariants.
5. Record each candidate as: strategy, observation, violated invariant, trigger
   idea, safe expected result, observable failure signal, confidence, and
   false-positive checks.
6. Prioritize a bounded portfolio by impact, executability, evidence clarity,
   environment cost, and destructive risk.
7. Read [test-strategy.md](references/test-strategy.md). Generate concrete tests
   during this run under `result/artifacts/generated_tests/`; never present old
   or preset tests as current-run Agent generation.
8. Attempt the normal build and test path. If the complete system cannot run,
   follow [execution-fallback.md](references/execution-fallback.md) and continue
   through independently testable layers rather than ending the run.
9. Execute bounded tests, validate normal controls, and separate product
   behavior from build, dependency, environment, state, and test-code failures.
10. Minimize credible triggers under `result/artifacts/reproduction/` and
    independently repeat each from comparable state at least three times.
11. Apply [evidence-standard.md](references/evidence-standard.md). Label results
    confirmed, candidate, inconclusive, rejected, or environment-blocked.
12. Follow [reporting-format.md](references/reporting-format.md), write
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
locations, or trigger methods. Finding no confirmed Bug is valid when the
tested strategies, fallback attempts, evidence, and limitations are reported.
