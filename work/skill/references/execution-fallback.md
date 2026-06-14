# Execution Fallback

Failure to start the complete system is a scope reduction, not an automatic end
to the run. Record each attempted level, its command, result, and evidence.

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
