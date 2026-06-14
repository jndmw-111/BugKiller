# System Profiles And Risk Coverage

Classify the target before allocating tests. Select one or more primary
archetypes using code, manifests, interfaces, data flows, and deployment
evidence. Use `generic-application` only when no specific archetype is
supported.

## Archetype priorities

- **generic-application**: input boundaries, authorization, business rules,
  data consistency, error paths, and configuration.
- **web-api**: authentication/session, authorization, injection, browser and
  HTTP behavior, API abuse, parsing, and output encoding.
- **commerce-financial**: business invariants, money precision, authorization,
  transaction consistency, replay/idempotency, concurrency, and auditability.
- **multi-tenant-saas**: tenant isolation, ownership, cache/data partitioning,
  bulk APIs, background jobs, exports, and cross-tenant integration.
- **identity-access**: authentication, session/token lifecycle, recovery, MFA,
  authorization, cryptography, enumeration, and rate controls.
- **file-content**: path handling, upload/download, archive extraction,
  parser differentials, content type, metadata, storage, and resource bounds.
- **microservices**: service identity, gateway/backend disagreement, retries,
  distributed state, message trust, configuration, and dependency contracts.
- **async-messaging**: ordering, duplicate delivery, replay, poison messages,
  partial failure, dead-letter handling, idempotency, and eventual consistency.
- **data-pipeline**: schema drift, type conversion, truncation, encoding,
  duplicate/lost records, checkpointing, lineage, and partial batch failure.
- **cli-desktop**: argument/command injection, local paths and permissions,
  IPC, configuration, secret storage, update integrity, and unsafe file opens.
- **sdk-library**: API contracts, type/boundary behavior, parser/serializer
  symmetry, thread safety, error contracts, compatibility, and dependencies.
- **native-systems**: memory safety, integer/size arithmetic, lifetime,
  concurrency, unsafe boundaries, binary parsing, ABI, and resource handling.
- **infrastructure-automation**: command/template injection, privilege
  boundaries, secrets, unsafe defaults, artifact integrity, and deployment
  drift.
- **mobile-client**: local storage, IPC/deep links, authentication tokens,
  transport trust, platform permissions, WebViews, and update integrity.
- **ai-agent**: direct and indirect prompt injection, tool authorization,
  data exfiltration, retrieval poisoning, memory isolation, output trust, and
  untrusted model/tool content.

## Universal bug directions

Assess every direction exactly once as `high`, `medium`, `low`, or
`not-applicable`:

1. `input-boundary`
2. `authorization-ownership`
3. `business-logic`
4. `data-consistency`
5. `injection`
6. `web-protocol-client`
7. `file-path`
8. `parsing-serialization`
9. `authentication-session`
10. `secrets-cryptography`
11. `errors-observability`
12. `configuration-deployment`
13. `dependencies-integration`
14. `api-abuse`
15. `concurrency-resource`

Profile-specific requirements may add specialty obligations such as native
memory safety, AI tool trust, mobile IPC/storage, or supply-chain integrity.

## Coverage rules

- Provide project evidence for every priority decision.
- Treat all priorities required by a primary archetype as `high`.
- Execute at least two complementary techniques for each high direction and at
  least one for each tested medium or low direction.
- High directions must be dynamically tested in a complete run. A blocked high
  direction makes the run incomplete and requires blocker evidence.
- After the first pass, calculate risk-weighted coverage, inspect uncovered
  high-risk paths, and rebalance remaining tests.
- Use weights high=5, medium=3, low=1; exclude evidence-backed
  `not-applicable` directions. Count tested=1, partial=0.5, blocked/planned=0.
- Target at least 95% risk-weighted dynamic-test coverage for a complete run.
  This measures execution coverage of the declared plan, not the percentage of
  all real Bugs found. Never claim 95% Bug recall without benchmark ground
  truth and an independently known denominator.

Use OWASP ASVS/WSTG or MASTG where applicable, current MITRE CWE categories for
weakness breadth, and risk-tailored verification consistent with NIST SSDF.
