# Test Strategy

## Candidate format

For each candidate record:

1. strategy family and target module;
2. source observation;
3. expected invariant;
4. proposed trigger class;
5. expected safe behavior;
6. observable Bug signal;
7. risk and side effects;
8. fallback level and evidence needed to accept or reject it.

## Dynamic test generation

Generate concrete test code and inputs only after inspecting the current
`code/`. Save them beneath `result/artifacts/generated_tests/`; never add them
to `code/`.

Prefer the project's existing test runner and public interfaces. Use temporary
copies or isolated processes when execution could create state. Set explicit
timeouts. Change one relevant variable at a time and keep a normal control case.
When the complete service is unavailable, generate module-level or callable
surface tests according to `execution-fallback.md`.

## False-positive elimination

Before blaming the product:

- confirm the build and baseline tests can run;
- inspect dependency and environment errors separately;
- validate the generated test itself;
- rerun a normal control;
- verify the observed result contradicts a real invariant;
- minimize unrelated setup;
- repeat the final trigger at least three times.
- restore or recreate comparable initial state before each rerun.

Static warnings, unreachable code, build failures, and test harness mistakes are
not confirmed Bugs.
