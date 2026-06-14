# Execution Fallback

Failure to start the complete system is a scope reduction, not an automatic end
to the run. Record each attempted level, its command, result, and evidence.

## Runtime orchestration

Run `runtime_runner.py inspect` before executing guessed commands. Verify
manifest-declared scripts, required runtime availability, local dependency
directories, environment templates, entry points, and external-service needs.
The inventory never authorizes remote installation.

Use:

- `runtime_runner.py exec` for builds, tests, CLIs, migrations against
  disposable data, and other commands that may write beside source;
- `runtime_runner.py service` for an isolated background service, a localhost
  HTTP or TCP health check, and a current-run generated probe;
- `--dependency-mode copy` only when a bounded repository-local dependency
  directory is required;
- `--env-file` only for synthetic local test configuration stored under
  `result/artifacts/generated_tests/`; reports retain keys but redact values
  and reject execution-path or loader injection variables;
- a narrower `--source code/<subproject>` when the whole repository exceeds
  copy limits.

Every attempt must produce a JSON report and a `runtime_execution.attempts`
entry. Classify failures as runtime missing, dependency missing, configuration
missing, external service missing, build error, startup error, timeout, or
test error before moving down the ladder.

## Levels

0. **Full system**: documented build, existing test suite, and normal service
   startup.
1. **Existing tests without full service**: unit, package, component, or offline
   tests already present.
2. **Subproject or module**: build and test one package, library, plugin,
   service, or workspace member.
3. **Public callable surface**: invoke a CLI, exported function, parser,
   handler, service class, or library API.
4. **Isolated local harness**: use a temporary copy and local fakes for
   unavailable databases, queues, clocks, filesystems, or downstream services.
5. **Pure-logic verification**: directly test validation, authorization,
   state-machine, transformation, arithmetic, or error-handling logic.
6. **Static-only candidate**: when no safe execution path exists, preserve the
   observation and blocking evidence but do not confirm a Bug.

## Rules

- Never add stubs, tests, or build files to `code/`.
- Use `result/artifacts/` or a temporary isolated copy.
- Prefer the target project's bundled runtime and installed dependencies before
  replacing infrastructure.
- Do not run package installation merely because a manifest exists. Prefer
  existing lock-resolved local dependencies and platform-provided caches.
- For databases, queues, caches, and object stores, use disposable local state
  and a unique temporary namespace. Never connect to production or unrelated
  services.
- Start only the minimum dependency chain needed for the selected interface.
  In a multi-service target, test downstream services or modules separately
  when the gateway or orchestrator is blocked.
- A fake may stand in for a dependency only when the target module, validation,
  authorization, state transition, parser, or transformation itself still
  executes.
- A cross-language reimplementation or manually predicted output is a
  hypothesis aid, not confirmation evidence.
- Do not download unknown remote scripts or silently install unapproved
  dependencies.
- A failure at one level should not block unrelated modules or strategies.
- Explore independent modules in parallel or breadth-first when practical; the
  levels are a capability ladder, not a reason to follow one blocked path only.
- State clearly which level produced each piece of evidence.
- Confirmation still requires actual execution and three consistent reruns;
  level 6 can never produce a confirmed Bug.
- Measure runtime coverage at the deepest executable fallback level. Module
  coverage is valid evidence for that module even when full-system coverage is
  unavailable.
- Run mutation testing only where a passing baseline and disposable isolated
  source copy are available. A blocked mutation campaign does not block other
  modules, but it prevents a `complete` run.
- A complete run must reference at least one successful runtime report. If the
  full system failed, preserve its report and attempt at least one lower level.
