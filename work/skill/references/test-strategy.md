# Test Strategy

## Candidate format

For each candidate record:

1. identifier, provenance, lead source when applicable, formation time,
   bug direction, strategy family, system archetype, and target module;
2. source observations; for independent candidates, exclude temporarily
   quarantined answer material, and for lead-derived candidates, record the
   exact project lead source;
3. expected invariant and its evidence strength;
4. proposed trigger class and normal control;
5. expected safe behavior and observable Bug signal;
6. input controllability, path reachability, and result observability;
7. independence from other candidates;
8. risk, side effects, fallback level, and false-positive checks;
9. evidence needed to accept or reject it.

## Dynamic test generation

Generate concrete test code and inputs only after inspecting the current
`code/`. Save them beneath `result/artifacts/generated_tests/`; never add them
to `code/`.

Prefer the project's existing test runner and public interfaces. Use temporary
copies or isolated processes when execution could create state. Set explicit
timeouts. Change one relevant variable at a time and keep a normal control case.
When the complete service is unavailable, generate module-level or callable
surface tests according to `execution-fallback.md`.

Select techniques from the observed surface rather than applying a fixed
payload list:

- partition valid, invalid, empty, absent, extreme, and cross-type inputs;
- compare sibling endpoints, roles, layers, serializers, or implementations;
- define metamorphic relations such as order independence, round-trip
  preservation, monotonicity, idempotency, or equivalent encodings;
- enumerate a bounded role x action x owner/non-owner matrix;
- exercise valid and invalid state transitions, replays, duplicates, retries,
  and safe bounded interleavings;
- inject local, reversible failures at dependency boundaries to inspect
  rollback and partial state;
- vary encoding, normalization, path form, serialization, and output context;
- test configuration defaults, missing settings, feature combinations, and
  adapter contract mismatches.
- use grammar-aware or property-based generation for parsers and structured
  protocols; preserve seeds and minimize failures;
- test layer disagreement across proxy/backend, gateway/service,
  serializer/parser, client/server, and single/bulk behavior;
- for native targets, use available compiler/runtime sanitizers and real target
  binaries when safe; static warnings alone remain candidates;
- for AI Agent targets, treat prompts, retrieved content, tool results, memory,
  and model output as mutually untrusted boundaries.

Generated tests must execute the target project's real code or a locally
started instance. Fakes may replace unavailable dependencies but not the target
decision or transformation under test. A reimplementation in another language
can help form a hypothesis but cannot confirm target behavior.

After tests execute, apply `runtime-quality.md`. Runtime coverage must identify
the product source paths and decision symbols actually reached. Targeted
mutation then checks whether assertions detect meaningful changes to covered
authorization guards, business conditions, state transitions, failure paths,
and boundary comparisons. A surviving mutant is a test-quality gap, not by
itself a product Bug.

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
- capture the exact command, timestamps, exit status, runner/runtime version,
  bounded raw output, and state delta for every execution;
- write a separate trace event for the initial test, normal control, and each
  independent rerun;
- verify that an answer-bearing file did not supply an allegedly independent
  trigger.
- verify every actionable project-provided lead with a newly generated
  current-run test; preserve failed, rejected, and blocked outcomes as well as
  confirmations.
- verify that runtime coverage reaches the intended product path rather than
  only test setup or a fake dependency;
- kill applicable critical targeted mutants, or mark the run incomplete with
  evidence rather than overstating test strength.

Static warnings, unreachable code, build failures, and test harness mistakes are
not confirmed Bugs.
