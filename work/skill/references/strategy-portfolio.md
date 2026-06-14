# Strategy Portfolio

Use multiple complementary strategy families in every independent run. Select
at least three that match the observed project and record the selection in
`result/run_manifest.json`.

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
- Prefer different trust boundaries or modules rather than many variants of one
  sink.
- Include a normal control for each executable candidate.
- Limit initial candidates to a manageable set; expand only when evidence
  justifies it.
- Do not use random variation without recording the input and purpose.
- A family may be marked not applicable only with project-specific evidence.

Score candidates qualitatively using:

- execution feasibility;
- security or business impact;
- evidence clarity;
- environment cost;
- destructive risk.

Prioritize high-feasibility, high-impact, low-risk candidates while reserving
time for three reruns and reporting.
