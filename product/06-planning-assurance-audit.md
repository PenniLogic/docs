# PenniLogic - Planning Assurance Audit

> **Historical assurance iteration 1.** Superseded by
> [`07-planning-assurance-iteration-2.md`](07-planning-assurance-iteration-2.md), which rebuilt the
> effective graph, execution schedule and second-pass security/product controls.

> **Verdict: REVISE completed; HOLD remains for gated feature implementation.**
>
> **Date:** 2026-09-02.
> **Scope:** the live GitHub Project, durable backlog, architecture and security seams, product and
> UX coverage, contract compatibility, ticket cold-start quality, parallel delivery, review and
> verification.
>
> This audit does not promise that unanswered architecture decisions have somehow been answered.
> It makes the opposite guarantee: a developer cannot start dependent work until the decision and
> machine-readable contract that answer it are merged.

## 1. Result

The plan is comprehensive enough to execute in parallel after its gates close. The source validates
with:

| Measure | Current target |
|---|---:|
| Epics | 32 |
| Implementation tickets | 220 |
| Project items after sync | 252 |
| Planning inventory | 1791 points |
| Numbered-sprint tranche | 819 points |
| `Future` work | 113 tickets / 966 points |
| Undated `Backlog` work | 2 tickets / 6 points |
| Startable work | 12 implementation tickets plus E31 |

These are dated audit measurements. The validator and rendered Project README derive current totals;
this document is not the source for future counts.

The live Project and source matched exactly before remediation: 239 items, 0 planned sync
operations. The remediated dry run plans the 13 new tickets, ticket patches, field changes,
dependency edges, rollups and Project metadata as one deterministic projection.

## 2. Method

The audit read the live Project through GraphQL and the complete durable source, including all 169
native tickets then present, all 61 strict legacy patches, the rendered bodies of all 207 live
implementation issues, the architecture and security documents, product and risk records, every
quality and governance ticket, JSON schemas, validator and sync tooling.

Four independent passes covered:

1. Live board and source reconciliation.
2. Architecture, security, privacy and cross-language schema seams.
3. Product, feature and end-to-end UX coverage.
4. Delivery protocol, ticket quality, review and verification.

Claims were checked against ticket ids and dependencies rather than accepted from prose.

## 3. Findings closed by this change

### Delivery-system enforcement

| Finding | Resolution |
|---|---|
| `manifest.json` violated its own schema | `ticket_size` and `roadmap_partial_span` are now declared and required |
| Schema `$id` values forced offline validation toward a fake network host | Local schemas no longer override their file base URI |
| Schemas existed but were not evaluated | `validate-backlog-v2.ps1` executes `Test-Json -SchemaFile` for the manifest and every declared data file |
| Native tickets could evade length and unknown-property rules | The evaluated schema is now authoritative; semantic graph checks remain in PowerShell |
| `parallel_boundary` had two minimums | Native and legacy values require at least 40 characters |
| Four legacy API tickets had no Context section | `set_context` is a strict patch operation and api#6, api#7, api#9 and api#19 receive concrete context |
| A patch stamp could hide a later incomplete body | Sync verifies all required headings on the effective legacy body before any write |
| A replacement could re-append its own superseded bullet | Validation rejects any `replace_text.old` value that also appears in the patch's `add_*` lists |
| Named release gates had no enforceable release path | `T-PRS-02` gates `T-REL-02`; `T-ADM-12` gates `T-QA-13`; source-level gate metadata fails unless every release gate reaches a terminal gate through dependencies |
| Mutable Project README totals went stale | Ticket, point and schedule totals are rendered from the source at sync time |
| Review and test handoffs were hidden inside one board | Review, Test and Blocked queues are durable views with reviewers and linked pull requests |

### Architecture and security

| Finding | Resolution |
|---|---|
| Raw-message hash, transaction dedupe key and fuzzy matching were contradictory | ADR-018 must define three separate artifacts. Raw-derived HMAC stays device-local; the API carries a random source event id; the server computes a keyed structured fingerprint and uses reversible fuzzy candidate links |
| The admin audit ADR followed the append-only event schema it governs | `T-ADR-ADMIN-06` moves to Sprint 02 and `T-SEC-03` depends on it, including correlation id and chosen write-topology tests |
| Persisted transaction embeddings appeared in research with no owner or erasure | They are prohibited until `T-ADR-EMBED-12` decides storage, tenancy, inversion risk, retention and hard-delete erasure; infrastructure rejects vector extensions while it is open |
| Data residency was documented but not enforced | `T-PLT-01` owns one committed region policy covering databases, object and backup stores, KMS and secrets, enforced at plan time and during drift detection; `T-CMP-04` consumes it |
| Conversation history was an unclassified financial-text store | `T-CON-14` and `T-AIP-06` define history-off default, opt-in encryption, retention, export and erasure in the core API while ai-service stays stateless |
| Administrative streams lacked implementation ordering | The foundational schema now consumes ADR-020's correlation and single-write or dual-write failure decision before it can merge |

The existing controls were also re-verified: integer money across Kotlin, TypeScript, Python and SQL;
per-currency ledger invariants; forced RLS and ReBAC; envelope encryption and blind-index rotation;
shared-data erasure; passkeys and recovery; SSRF and DNS-rebinding controls; prompt-injection and
tool-scope defenses; admin isolation; supply-chain controls; offline conflict and idempotency rules.

## 4. Product and UX coverage added

Thirteen implementation-ready Future tickets record work that was absent without pretending it fits
inside the saturated MVP schedule:

| Ticket | Coverage |
|---|---|
| `T-ADR-EMBED-12` | Persisted embedding decision or explicit prohibition |
| `T-AND-06` | Constrained-device runtime and large-screen adaptation |
| `T-ING-04` | Android cash-withdrawal reconciliation |
| `T-CON-13` | Refund, cash and recurring lifecycle contract |
| `T-TXN-01` | Linked consumer refunds with correct ledger treatment |
| `T-TXN-02` | Android refund review and correction |
| `T-GOL-04` | Sourced salary-market options for a measured goal gap |
| `T-CON-14` | Assistant conversation lifecycle contract |
| `T-AIP-06` | Opt-in encrypted assistant history, export and erasure |
| `T-NOT-03` | Cross-channel preference centre |
| `T-DEBT-03` | Credit-card cycles and advanced payoff strategies |
| `T-RCR-01` | Recurring-charge confirmation, price alerts and safe cancel assist |
| `T-BUD-01` | Sinking funds for known irregular expenses |

Existing client and quality tickets now also cover:

- Web account, category and manual transaction parity.
- Web cash and refund states.
- Low-memory Android release evidence using the matrix owned by `T-QA-12`.
- Mobile split-group export.
- Adult-only launch enforcement for onboarding, invitations and grants.
- Salary-market provenance and advice-boundary states on Android and web.
- History-off, retention, export and deletion states on both assistant clients.
- Android cross-channel preference visibility.
- Android and web recurring-charge and sinking-fund journeys.

No scheduled estimate was increased. The additions to scheduled tickets are contract, security or
verification constraints inside their existing outcome; separable product work is represented by a
new Future ticket. Every 13-point Future ticket still must be split before entering a numbered
sprint.

## 5. Original requirement disposition

| Requirement | Planning disposition |
|---|---|
| Native Android | Kotlin and Compose, deep OS integration, offline queue and device matrix |
| Calls | Dropped: Play policy does not permit the finance use case |
| SMS | Permitted money-management exception, on-device deterministic parser, Play declaration gate |
| Other UPI apps | No direct API; captured indirectly through bank SMS and payment notifications |
| Email | Future on-device parsing and import; raw content does not cross the device boundary |
| Ambiguous payments | Clarification inbox, reversible rules and conflict states |
| Salary and additional income | Income model, payroll expectation, variable income and UI parity |
| Debt and expenses | Append-only double-entry ledger, debt engine, budgets, safe-to-spend and reporting |
| Goals | Deterministic competition and scenarios, sourced salary-market information, sinking funds |
| Family | Per-person, per-category, revocable grants with abuse-safety and access transparency |
| Split groups | Deterministic shares, itemized bills, settlement links, disputes, simplification and export |
| AI subscription and BYOK | Server-routed gateway, encrypted keys, quotas, provenance and refusal |
| Custom AI base URL | Register once, validate, pin, audit and enforce network egress policy |
| Web | Customer parity for entry, analysis, debt, income, goals, groups, billing and AI |
| Admin | Separate service and identity boundary, redacted by default, JIT elevation and red-team gate |
| Plans and quotas | Server-authoritative plans, monthly and annual billing, model and request/token quotas |

## 6. Ticket cold-start quality and schema compatibility

Every ticket is required to carry Outcome, Context, Scope, Acceptance criteria, Contracts and
schema, Security and privacy, Observability, Tests, Rollout and rollback, Non-goals, Dependencies,
Parallel boundary and Definition of Done. Legacy headings are checked after patching, not assumed.

The contract is deliberately the implementation detail source:

1. E26 decides irreversible shapes and emits machine-readable artifacts.
2. E02 publishes OpenAPI 3.1, JSON schemas, error catalogues and generated Kotlin, TypeScript and
   Python clients.
3. Provider and consumer contract tests fail incompatible implementations.
4. Android local entities are bound to the published contract.
5. Breaking changes use expand-migrate-contract with a compatibility window.

The schemas are not claimed to be compatible before they exist. Dependent tickets remain Backlog
until the accepted ADR and generated contract make compatibility testable.

## 7. Parallel branches, pull requests and review

The plan supports parallel execution through:

- One ticket, one primary repository, one branch, one worktree and one pull request.
- Early draft pull requests with stable-id branch and title metadata.
- Explicit parallel boundaries and native `blockedBy` edges.
- Contract-first stacks with ordered links, bottom-up merge order and a named restack owner.
- Expand-migrate-contract for schema changes.
- One in-flight migration registry and lock.
- Numeric implementation and independent-review WIP caps.
- Merge-queue or documented serialized merge policy per repository.
- Required checks for issue linkage, open blockers, branch/title format, stack metadata, migration
  reversal evidence and current STRIDE record.

The current repositories do not yet have the product branch-protection rules wired. That is not a
hidden gap: `T-GOV-03`, the repository scaffolds and `T-SCA-INF-01` own it, and feature work remains
on HOLD until those controls exist. Money-path and security-path changes cannot use the temporary
single-collaborator exception.

## 8. Verification coverage

| Verification class | Owning work |
|---|---|
| Unit and integration | Per-feature tickets and repository scaffolds |
| Property and independent-model | `T-QA-01` |
| Mutation and idempotency | `T-QA-01` |
| Provider and consumer contract | `T-QA-02` |
| White-box tenancy and policy | `T-QA-03` |
| Black-box API and authorization attacks | `T-QA-03` |
| SAST, DAST, dependency and secret scanning | `T-QA-04` |
| Supply chain, IaC, container and mobile provenance | `T-QA-11` |
| Web E2E, accessibility, browser matrix and performance | `T-QA-06` |
| Android instrumented, device, accessibility and performance | `T-QA-08`, `T-QA-12` |
| Admin operator E2E and planted control defects | `T-QA-13`, `T-ADM-12` |
| Privacy traffic inspection | `T-QA-09` |
| Load, stress, soak, chaos and DR | `T-QA-05` |
| Independent penetration and red-team | `T-QA-10` |
| Parser positive, negative and coverage gates | `T-QA-12`, `T-PRS-01`, `T-PRS-02` |
| Private beta and public launch evidence | `T-REL-02`, `T-REL-03` |

Release gates consume their evidence through dependencies and machine-readable manifests. A named
release gate with no dependency path to a terminal gate now fails validation.

## 9. Explicit limits and remaining blockers

The planning source cannot remove these external constraints:

1. A distinct qualified reviewer is still required before money-path or security-path code can
   merge.
2. A physical Indian-SIM device must be procured for real parser validation.
3. Counsel must approve jurisdiction profiles, processor agreements and statutory values.
4. Google must approve the SMS permission declaration.
5. Vendor availability, model retention terms and prices must be revalidated before contracting.

The following remain deliberate non-goals or gated decisions, not forgotten features:

- Direct call-log ingestion.
- Direct access to another UPI application's private history.
- Lending, loan brokering, ads or sale of data.
- Account Aggregator integration in MVP.
- Tax filing features before holdings and advice-boundary evidence exist.
- Persisted user-derived embeddings before `T-ADR-EMBED-12`.
- Any model performing financial arithmetic or initiating a payment.

## 10. Direct answer

The plan is now internally coherent, live-board-reconcilable, security-led and detailed enough for
parallel agents to execute **once each ticket reaches Ready**. No developer should interpret
`Backlog` as permission to invent an unresolved schema. The remaining second-reviewer, device,
legal, store and vendor constraints are visible hard gates rather than undocumented assumptions.
