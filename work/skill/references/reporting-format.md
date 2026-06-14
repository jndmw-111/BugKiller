# Reporting Format

## Project profile

`result/project_profile.md` should contain scope, languages, frameworks, build
and test commands, entry points, interfaces, constraints, and setup limits.

## Final report

`result/output.md` should contain:

- run ID, independent-run statement, and tested scope;
- blind-analysis status, reviewed answer-bearing paths, lead coverage, and
  candidate provenance summary;
- project profile link;
- selected strategy families and per-strategy results;
- attack-surface coverage matrix and techniques used;
- primary/secondary system archetypes and classification evidence;
- all 15 direction priorities, execution status, specialty obligations, and
  risk-weighted coverage before and after rebalancing;
- full-start status and fallback levels attempted;
- commands and test counts;
- independently confirmed Bugs;
- project-lead confirmed Bugs;
- independent count, project-lead count, and combined confirmed Bug count;
- every project lead with confirmed, rejected, inconclusive, not-applicable, or
  environment-blocked disposition;
- candidates, rejected hypotheses, inconclusive results, and setup failures;
- for every confirmed Bug: invariant, trigger, generated test, actual result,
  expected result, three-rerun table, minimal reproduction, impact, evidence
  paths, and trace references;
- limitations and untested areas;
- final success, no-Bug, or incomplete conclusion;
- statement of whether human intervention occurred.
- source-integrity verification result.
- runtime coverage tool, commands, measured scope, line/branch/function
  metrics, raw reports, and high-risk key-path hits;
- mutation tool or manual method, isolated-copy confirmation, baseline result,
  killed/survived/invalid/timeout/not-covered/blocked counts, score, critical
  mutant disposition, diffs, and evidence.

Never claim more than the evidence supports. If no Bug is confirmed, report the
attack surfaces inspected and tests executed.

Never describe the risk-weighted coverage percentage as Bug recall, detection
rate, or proof that the remaining system is vulnerability-free.

Do not confuse risk-direction coverage, runtime code coverage, and mutation
score. Report all three with their exact scope and limitations.
