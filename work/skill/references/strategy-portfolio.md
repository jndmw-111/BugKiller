# Strategy Portfolio

Use multiple complementary strategy families in every independent run. Select
at least three that match the observed project and record the selection in
`result/run_manifest.json`.

Read `system-profiles.md` first. Strategy selection must follow the classified
system archetype and its high-priority bug directions rather than giving every
project the same checklist.

## Strategy families

1. **Input and parsing**: types, empty values, numeric and length boundaries,
   encoding, parser disagreement, normalization, and error handling.
2. **Authorization and ownership**: identity propagation, role checks, resource
   ownership, tenant boundaries, default access, and trust transitions.
3. **State and workflow**: invalid transitions, ordering, replay, idempotency,
   duplicate operations, race-prone updates, and stale state.
4. **Data integrity and failure paths**: transactions, partial failure,
   rollback, arithmetic relations, consistency, exception paths, and retries.
5. **File and injection surfaces**: path handling, templates, serialization,
   query/command construction, upload/download boundaries, and output encoding.
6. **Configuration and integration**: unsafe defaults, environment-dependent
   behavior, component contracts, adapters, feature flags, and cross-module
   assumptions.

## Portfolio rules

- Cover at least three applicable families in one run.
- Target at least four families when the project has multiple subprojects,
  public interfaces, roles, state stores, or external components.
- Prefer different trust boundaries or modules rather than many variants of one
  sink.
- Complete a breadth pass over the attack-surface map before deep testing.
- Include at least one independently derived candidate that is not seeded by an
  answer-bearing file whenever any executable surface exists.
- After the independent breadth pass, validate every actionable project lead.
  Lead validation supplements the strategy portfolio and never replaces
  independent exploration.
- Include a normal control for each executable candidate.
- Limit initial candidates to a manageable set; expand only when evidence
  justifies it.
- Do not use random variation without recording the input and purpose.
- A family may be marked not applicable only with project-specific evidence.

Use complementary test lenses across selected families:

- equivalence partitions, boundaries, missing values, type confusion, and
  parser disagreement;
- differential checks across sibling endpoints, roles, layers, or
  implementations;
- metamorphic relations that should preserve or predictably transform an
  invariant;
- role x action x ownership authorization matrices;
- invalid transitions, replay, idempotency, stale state, and bounded
  interleavings;
- partial failure, rollback, retry, timeout, and error-translation paths;
- encoding, normalization, serialization, path, template, and output-context
  differences;
- default/configuration/feature-flag combinations and cross-module contracts.
- browser and HTTP controls: XSS, CSRF, SSRF, redirects, CORS, host/proxy
  semantics, response headers, and request parsing differentials;
- authentication lifecycle: session fixation, token refresh/revocation,
  recovery, MFA, enumeration, and bounded rate controls;
- API abuse: duplicate parameters, field-level authorization, mass assignment,
  overexposure, and single/bulk asymmetry;
- native and specialized surfaces when applicable: memory/size safety, IPC,
  supply-chain integrity, prompt/tool trust, retrieval poisoning, and
  untrusted-output handling.

Allocate the run budget deliberately: approximately 30 percent for discovery,
controls, and breadth; 40 percent for candidate execution and minimization; and
30 percent for independent reruns, evidence, integrity checks, and reporting.
Adjust when setup cost is high, but never consume the confirmation reserve on
unbounded exploration.

Score candidates qualitatively using:

- execution feasibility;
- security or business impact;
- evidence clarity;
- user-input controllability;
- code-path reachability;
- output or state observability;
- independence from known examples and other candidates;
- environment cost;
- destructive risk.

Prioritize high-feasibility, high-impact, low-risk candidates while reserving
time for three reruns and reporting. After confirming a defect pattern, inspect
bounded siblings sharing the same decision, sink, adapter, or state transition,
but do not count trivial variants as strategy diversity.
