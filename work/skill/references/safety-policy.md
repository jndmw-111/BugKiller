# Safety Policy

## Allowed scope

- Read the authorized repository under `code/`.
- Write only to `result/`, `logs/`, or a bounded temporary directory.
- Create an isolated temporary copy when a build necessarily writes into its
  source tree.
- Apply targeted mutations only to a disposable isolated copy after recording
  the original source snapshot.
- Execute local build and test commands needed to verify candidates.
- Use local services started from the authorized project when required.

## Prohibited actions

- Modifying, formatting, deleting, or generating files inside `code/`.
- Scanning public networks or unrelated local hosts.
- Destructive data changes, privilege escalation, persistence, credential
  extraction, or denial-of-service testing.
- Executing downloaded or unknown remote scripts.
- Printing environment variables or secrets into reports and traces.
- Treating a preset test or static suspicion as a current-run confirmed Bug.

## Resource limits

Use explicit command timeouts, bounded output capture, a small candidate set,
and a finite test budget. Prefer disposable local state. If one execution path
is blocked, move to another module or fallback level. Stop the full run only
when no safe executable surface remains.

Fuzzing, concurrency, replay, and fault injection must be bounded,
deterministic enough to reproduce, and restricted to local disposable state.
Cap input size, case count, worker count, retry count, and elapsed time. Do not
perform load, exhaustion, or denial-of-service testing. Record any seed and
every minimized input used as evidence.

Mutation campaigns use one mutant at a time, a default maximum of 20 targeted
mutants, and the normal command timeout. Never apply broad textual mutations,
never mutate dependencies, and never run a mutant against production or
non-disposable data. Verify `code/` integrity again after the campaign.
