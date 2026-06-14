# Runtime Test Quality

Runtime coverage answers whether generated tests executed the intended product
code. Mutation testing answers whether those tests detect important decision
errors. Neither metric proves that the target is vulnerability-free.

## Tool discovery

Run:

```bash
python3 work/skill/scripts/quality_tools.py detect
```

Prefer an already available target-language tool and do not download tooling:

- Python: `coverage` or `pytest-cov`; use standard-library `trace` only as
  line-execution fallback.
- JavaScript/TypeScript: project Jest/Vitest coverage, `c8`, `nyc`, Node test
  coverage, or `NODE_V8_COVERAGE`.
- Go: `go test -coverprofile`.
- Java/Kotlin: project-configured JaCoCo.
- Rust: `cargo llvm-cov` or Tarpaulin.
- .NET: project-configured Coverlet or `dotnet test` collection.
- Ruby/PHP: project-configured SimpleCov, Xdebug, or PCOV.
- C/C++/Swift: compiler coverage such as `gcov` or `llvm-cov`.

If no native tool is available, keep testing and record `unsupported` with the
specific detection evidence. A complete run requires measured coverage; an
unsupported or blocked measurement makes the run incomplete.

## Coverage protocol

1. Establish a passing normal-control baseline.
2. Execute current-run generated tests under the coverage tool.
3. Restrict metrics to product files under `code/`; exclude generated tests,
   dependencies, fixtures, and temporary fakes.
4. Preserve the raw report and exact command under
   `result/artifacts/evidence/`.
5. Record line, branch, and function coverage when the tool supports them.
   Branch coverage is especially important for authorization, business rules,
   state transitions, and boundary comparisons.
6. Record a `key_path_hit` for every tested high-risk direction. It must name
   the product source file, symbol, direction, and evidence path.
7. Every confirmed Bug must have a key-path hit linked by candidate ID. A test
   file merely running successfully is not execution evidence for its target.
8. When full-system coverage is unavailable, measure the deepest executable
   module, handler, service, parser, or pure-logic layer reached by the
   fallback workflow.

Coverage percentages are diagnostic, not universal pass thresholds. Low
coverage triggers focused test generation; high coverage does not replace
invariant-based assertions or vulnerability evidence.

## Targeted mutation protocol

Mutation is allowed only in a disposable isolated copy outside `code/`.
Capture the original source hash, run one mutant at a time, and delete the copy
afterward. Never patch the authoritative input.

Before mutation:

1. select source paths proven reachable by runtime coverage;
2. run the generated tests against the unmodified isolated baseline;
3. require the baseline to pass;
4. cap the default campaign at 20 targeted mutants and use the run command
   timeout.

Prioritize semantic decision mutations:

- negate a condition;
- change `<`, `<=`, `>`, `>=`, `==`, or `!=` at a boundary;
- remove or force an authorization/ownership guard;
- replace a decision boolean;
- alter a return value or state transition;
- remove exception, rollback, or failure handling;
- perturb arithmetic or comparison logic tied to a business invariant.

Avoid mass textual replacement. Mutate one syntactically valid location at a
time and preserve a bounded diff. Use a native mutation tool when already
available; otherwise the Agent may create a small, targeted manual mutation in
the disposable copy.

Classify each mutant:

- `killed`: current-run tests fail for the intended assertion;
- `survived`: tests pass, revealing a test-quality gap;
- `invalid`: mutant cannot represent executable target behavior;
- `timeout`: bounded execution exceeded its limit;
- `not-covered`: the mutated path did not execute;
- `blocked`: the environment prevented a valid comparison.

Only killed and survived mutants enter the score:

`mutation score = killed / (killed + survived) * 100`

Invalid mutants must include a reason and are excluded. A surviving, timed-out,
not-covered, or blocked critical mutant is unresolved. Strengthen tests and
rerun it. A complete run requires:

- assessment of every tested high-risk direction;
- at least one valid targeted mutant for each direction marked tested;
- a critical decision mutant for applicable input-boundary,
  authorization/ownership, and business-logic directions;
- no unresolved critical mutant;
- at least 80% targeted mutation score.

A surviving mutant is not automatically a product Bug. It is evidence that
the generated tests may not detect a relevant implementation error.

## Required evidence

Normalize mutation results as JSON with a top-level `mutants` list. Every item
must include:

- `id`, `direction`, `operator`, `source_path`, and `critical`;
- `status`;
- `diff_path`;
- raw `evidence_path`;
- current-run generated `test_path`.

Use:

```bash
python3 work/skill/scripts/quality_tools.py score \
  --input result/artifacts/evidence/mutation-results.json \
  --output result/artifacts/evidence/mutation-summary.json
```

Record coverage and mutation commands, outcomes, evidence paths, and concise
decisions in Trace. Re-run source integrity verification after the campaign.
