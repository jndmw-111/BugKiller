# Project Discovery

## Read-only inventory

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
verify its hints by reading the relevant files.

## Project profile

Write `result/project_profile.md` with:

- languages and frameworks, with evidence paths;
- build and run commands, distinguishing observed from inferred;
- entry points and exposed interfaces;
- existing tests and fixtures;
- state stores and external dependencies;
- trust boundaries and authorization surfaces;
- documented or code-enforced business constraints;
- unresolved setup questions.
- subprojects that can be built or tested independently;
- full-start blockers and the next usable fallback level.

Do not infer a version, vulnerability, or CVE from a dependency name alone.
Do not require complete repository comprehension before beginning safe tests on
a well-understood module.
