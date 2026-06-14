# Reporting Format

## Project profile

`result/project_profile.md` should contain scope, languages, frameworks, build
and test commands, entry points, interfaces, constraints, and setup limits.

## Final report

`result/output.md` should contain:

- run ID, independent-run statement, and tested scope;
- project profile link;
- selected strategy families and per-strategy results;
- full-start status and fallback levels attempted;
- commands and test counts;
- confirmed Bugs, candidates, rejected hypotheses, and setup failures;
- for every confirmed Bug: invariant, trigger, generated test, actual result,
  expected result, three-rerun table, minimal reproduction, impact, evidence
  paths, and trace references;
- limitations and untested areas;
- final success, no-Bug, or incomplete conclusion;
- statement of whether human intervention occurred.
- source-integrity verification result.

Never claim more than the evidence supports. If no Bug is confirmed, report the
attack surfaces inspected and tests executed.
