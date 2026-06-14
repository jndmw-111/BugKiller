# Safety Policy

## Allowed scope

- Read the authorized repository under `code/`.
- Write only to `result/`, `logs/`, or a bounded temporary directory.
- Create an isolated temporary copy when a build necessarily writes into its
  source tree.
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
