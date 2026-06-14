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

Store raw evidence in `result/artifacts/evidence/`. Evidence records should
identify the command, timestamps, relevant output, generated test, and matching
trace sequence. Do not edit raw output to make it more convincing.
