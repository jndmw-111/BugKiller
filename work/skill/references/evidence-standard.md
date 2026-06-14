# Evidence Standard

Mark a Bug confirmed only when all conditions hold:

1. The trigger input is explicit.
2. The concrete test was generated during the current run.
3. The test was actually executed.
4. Actual behavior violates source, interface, documentation, or a business
   invariant.
5. Environment, dependency, build, and test-code errors were excluded.
6. At least three independent reruns produced the same relevant result.
7. A minimal reproduction is available.
8. Raw output, exit status, response, exception, or state change is preserved.
9. The strategy family and execution fallback level are recorded.
10. Source integrity verification shows `code/` was not modified.
11. The target project's real implementation was executed; a rewritten model
    of the logic is not product evidence.
12. Candidate provenance proves whether the trigger was independently formed
    or came from a project-provided lead.
13. The candidate maps to a declared bug direction, system archetype, and
    coverage-plan entry.
14. Runtime coverage or equivalent execution evidence identifies the real
    product source path and symbol reached by the generated test.

Store raw evidence in `result/artifacts/evidence/`. Evidence records should
identify the exact command, start/end timestamps, exit status, runtime or test
runner version, bounded relevant output, state delta, generated test, fallback
level, and matching trace sequence. Store the initial execution, normal
control, and every rerun separately. Do not edit raw output to make it more
convincing.

Use these evidence classes:

- `independent-confirmed`: all criteria hold and the candidate predates access
  to answer-bearing material;
- `lead-confirmed`: all confirmation criteria hold, but the trigger or location
  came from a project-provided tutorial, CVE, answer, advisory, or fix note;
- `candidate`: a real invariant and test idea exist but confirmation is
  incomplete;
- `inconclusive`: execution occurred but observations cannot distinguish
  product behavior from another cause;
- `rejected`: controls or investigation disproved the hypothesis;
- `environment-blocked`: no safe executable path was available.

Both `independent-confirmed` and `lead-confirmed` are real confirmed Bugs and
contribute to the total confirmed count. Keep separate provenance counts so a
lead-derived result is not misrepresented as independent discovery.

Runtime test-quality evidence is reported separately from Bug confirmation.
Preserve native coverage reports, key-path hit records, mutation diffs,
baseline output, mutant output, normalized mutation results, and the calculated
score. Coverage and mutation scores strengthen confidence in the tests but
cannot independently confirm or reject a vulnerability.
