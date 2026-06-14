# Project Discovery

## Blind, read-only inventory

Inspect `code/` without modifying it. For a large repository, identify
subprojects first and work breadth-first across manifests and entry points
before reading implementation depth. Start with filenames and small,
high-signal files:

- project manifests and lockfiles;
- README and architecture documents;
- build, container, CI, and deployment files;
- source roots and executable entry points;
- routes, handlers, controllers, commands, jobs, parsers, and migrations;
- existing tests and test configuration.
- workspace, monorepo, module, and package boundaries;
- local service, database, queue, container, and environment requirements.

Use `work/skill/scripts/discover_project.py` for a bounded first inventory, then
verify its hints by reading the relevant files. Use
`work/skill/scripts/runtime_runner.py inspect` to separately inventory installed
runtimes, nested declared commands, environment templates, local dependency
directories, service manifests, and executable entry points.

## Two-phase lead handling

Before forming candidates, identify files likely to disclose intended answers:
solutions, answer keys, walkthroughs, tutorials, writeups, CVE or advisory
material, vulnerability catalogs, challenge descriptions, fix notes, and
comments that explicitly reveal a vulnerable location or trigger.

During blind phase A:

- record the path and reason for quarantine without using its answer content;
- use manifests, interfaces, architecture, business documentation, entry
  points, and existing tests to establish constraints;
- register hypotheses and their source observations before opening quarantined
  answer material;
- mark each hypothesis `independent`, `lead-derived`, or `static-only`.

Phase B must consult every quarantined source after the first independent
hypothesis and test plan are fixed. Classify each source as actionable or
non-actionable and record why. Extract every actionable claim into the lead
registry, then dynamically test it against the current target.

A confirmed lead-derived result counts as a confirmed Bug and must appear in
the main report and total count. Preserve provenance as `lead-derived` so it is
not misrepresented as blind independent discovery. Rejected, inconclusive,
not-applicable, and environment-blocked leads must also be reported.

For CVE or dependency claims, verify component identity, applicable version,
configuration, reachability, and trigger behavior. A name or version match
alone is not confirmation.

## Attack-surface map

Trace relevant paths from input to observable effect:

1. ingress: route, command, file, message, job, callback, or public function;
2. identity: authentication source, role, tenant, resource owner, and trust
   transition;
3. interpretation: parser, decoder, type conversion, normalization, and
   validation;
4. decision: authorization, business rule, feature flag, and state guard;
5. state: database, cache, filesystem, queue, transaction, and retry;
6. sink: query, template, command, path, serializer, log, response, or external
   adapter;
7. observation: response, exception, state delta, emitted event, or audit trail.

Compare sibling operations and negative space: create/read/update/delete,
single/bulk, normal/privileged, sync/async, and success/failure paths. Missing
or inconsistent checks often appear in the unmatched branch.

## System classification

Use `system-profiles.md` to select primary and secondary archetypes. Cite
evidence paths and confidence. Mixed systems may select multiple profiles; for
example, a multi-tenant commerce API should inherit high priorities from
`web-api`, `commerce-financial`, and `multi-tenant-saas`.

Do not choose a profile only from a framework name. Verify actual interfaces,
roles, state, data sensitivity, deployment boundaries, and business behavior.

## Project profile

Write `result/project_profile.md` with:

- languages and frameworks, with evidence paths;
- build and run commands, distinguishing observed from inferred;
- installed runtime/build-tool availability and exact version evidence;
- repository-local dependency directories and whether they can be copied
  within isolation limits;
- entry points and exposed interfaces;
- existing tests and fixtures;
- state stores and external dependencies;
- trust boundaries and authorization surfaces;
- documented or code-enforced business constraints;
- unresolved setup questions.
- subprojects that can be built or tested independently;
- full-start blockers and the next usable fallback level.
- each isolated build/test/start attempt and its report path;
- the attack-surface matrix and interfaces selected for testing;
- reviewed answer-bearing paths, source classification, and lead coverage;
- coverage gaps and confidence level for inferred constraints.
- primary/secondary system archetypes and classification evidence;
- all 15 bug-direction priorities and profile-specific specialty obligations.

Do not infer a version, vulnerability, or CVE from a dependency name alone.
Do not require complete repository comprehension before beginning safe tests on
a well-understood module.
