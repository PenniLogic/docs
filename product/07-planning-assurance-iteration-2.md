# PenniLogic planning assurance — adversarial iteration 2

> **Historical pre-design assurance.** The architecture, security and feature-gap findings remain
> valid, but its capacity counts and frontend authorization are superseded by
> [`08-experience-design-and-sdlc-plan.md`](08-experience-design-and-sdlc-plan.md) and the design-first
> assurance report. No mapped frontend work may start before `T-DQA-12`.
> Its twelve-item Ready conclusion is also superseded by the agent-review rollout: `T-GOV-03` and
> `infra#4` are in progress, and their dependent repository work remains Backlog.

**Review date:** 2026-09-03
**Verdict:** **READY TO START THE DEPENDENCY-FREE FOUNDATION WAVE; NOT AUTHORIZED TO SKIP GATES**

This review supersedes the readiness conclusions in `04-execution-readiness-review.md`,
`05-planning-completeness-audit.md` and `06-planning-assurance-audit.md`. Those documents remain the
history of earlier findings. The durable implementation source is
`../planning-automation/backlog-v2/`.

The second pass did not accept “all tickets have sections” as evidence of readiness. It rebuilt the
effective dependency graph, challenged authorization and erasure boundaries, traced feature inputs
to outputs on Android and web, checked current external assumptions, and proved that the numbered
tranche can actually fit its stated implementation and review capacity.

## 1. Decision

Development may start on the twelve dependency-free implementation items currently marked `Ready`.
No dependent item becomes Ready merely because its sprint has arrived. Native `blockedBy` edges,
required checks, contract versions, migration locks and evidence gates remain authoritative.

“Ready” does **not** mean defect-free. No planning process can guarantee that. It means:

1. no material planning gap found in this review is left without an owner;
2. every implementation ticket has outcome, context, scope, acceptance criteria, contract impact,
   security/privacy, observability, tests, rollout/rollback, non-goals, dependencies, parallel
   boundary and Definition of Done;
3. the complete effective graph and the live GitHub graph agree;
4. invalid schedule, dependency, schema, lane, review-capacity and roadmap states fail validation;
5. release remains impossible until executable evidence gates pass.

## 2. Audited state

| Measure | Result |
|---|---:|
| Epics | 32 |
| Implementation tickets | 237 |
| Live Project items | 269 |
| Tickets in numbered private-beta tranche | 118 |
| Numbered-tranche estimate | 908 points |
| Execution horizon | Sprint 01–18 |
| Implementation capacity | 3 lanes × 20 points per sprint |
| Independent review capacity | 20 review points per sprint |
| Peak planned review load | 19 points |
| Post-beta forecast | F19–F41, through 2028-03-31 |

`../planning-automation/backlog-v2/evidence/execution-lanes.json` assigns every numbered ticket to a
lane and point interval. It is a machine-checked feasibility envelope for the current pre-split
inventory, not permission to execute a 13-point ticket whole. Validation rejects a missing or
duplicate assignment, estimate or sprint drift, lane overlap, over-capacity interval,
same-sprint dependency inversion and reviewer overload. Every required split must regenerate and
revalidate this proof before the split is complete.

## 3. Structural findings and disposition

| Finding | Disposition |
|---|---|
| The clarification release dependency was reversed: the journey depended on its gate | Reversed. `T-QA-08` now depends on `android#11`; private beta depends on both |
| Legacy issue dependencies were absent from offline validation | All 61 legacy snapshot entries now carry canonical dependencies; the validator builds one graph across legacy, native and patch additions |
| Legacy epics used plain `E##` dependency lines that bullet-only readers ignored | Legacy IDs are resolved from unique epic titles, dependency sections are migrated to canonical bullets, native edges are reconciled and unresolved tokens fail |
| The 14-sprint plan was impossible under its own three-lane model | Replanned to 18 sprints and persisted as an executable lane proof; implementation and review capacity are both enforced |
| Source synchronization could overwrite human workflow state | `In Progress`, `In Review`, `In Test`, `Blocked` and `Done` are preserved; source `Ready` still downgrades when blockers remain |
| Dependency reversal could create a transient GitHub cycle | Explicit removals now execute before additions; the interrupted live synchronization resumed idempotently |
| A malformed same-sprint cycle could hang critical-path validation | Cycle detection now suppresses recursive critical-path evaluation and returns the structural cycle as a finite validation failure |
| Forecasting trusted dependency prose rather than the GitHub graph | Forecasting now requires the rendered body dependencies and native `blockedBy` edges to match exactly |
| Room-to-contract fidelity was orphaned | `T-SYN-04` is a pre-queue gate and `android#5`, `T-SYN-03`, Android QA and beta depend on it |
| Provenance arrived after ingestion, sync and export | `T-CON-15` owns `source_event_id`, source event, candidate, dedup decision and persisted provenance before consumers |
| Error semantics could be reinvented by feature contracts | Error-bearing contract tickets depend on `T-CON-12`; generated Kotlin, TypeScript and Python clients consume one taxonomy |
| Natural-language transaction entry had no contract and no web confirmation journey | `T-CON-16`, `T-AIP-05`, Android and web now share expiring draft, correction, cancel and idempotent-confirm semantics |
| Web bulk transaction UX had no server query contract | `T-CON-17` and `T-TXN-03` own bounded, authorized, cursor-based query/search/export behavior |
| Billing recovery paths could mutate quota or interpret mutable plans privately | Webhooks normalize only; lifecycle and unwind resolve immutable plan versions through `T-BIL-10` and quota through `T-BIL-02` |
| Admin UI controls did not govern direct database, backup, object-store or KMS access | `T-PLT-05` removes standing human access and brokers, approves, audits and exposes every unredacted read |
| An operator-created support ticket could authorize the same operator’s unmask request | Access-basis provenance is immutable; operator-originated, self-approved, reclassified or unverifiable bases deny |
| A backup restore could resurrect an erased user | `T-SEC-02` writes an independently protected erasure barrier; `T-SEC-07` proves restore, failover and replay cannot re-enable the subject |
| Household aggregate polling enabled differencing attacks | Contracts and implementation use fixed closed periods, stable snapshots, no exclusion/range probing, query budgets and typed suppression |
| The family epic delivered grants but no household product | `T-FAM-05`–`T-FAM-07` own aggregates, joint goals and Android/web experiences |
| Advanced debt engines lacked complete Android/web inputs and output presentation | `T-DEBT-04` and `T-DEBT-05` own advanced debt creation, validation, comparison and derivation UX |
| Rights requests started clocks without an operator fulfilment path | `T-ADM-13` owns the bounded, audited, accessible rights and grievance queue before beta |
| Holdings, clarification and notification preferences had parity gaps | `T-NWT-06`, `T-WEB-04` and `T-NOT-04` close the web and Android gaps |
| Android and Play assumptions were stale or unowned | `T-AND-07` targets API 36; `T-CMP-05` owns the Financial features declaration, manifest permission bans, `<queries>` and Contact Picker |
| External claims overstated Consent Manager, provider ZDR and competitor adoption | Documents now distinguish optional Consent Manager interoperability, counsel-owned retention, model/feature-specific ZDR evidence and unverified Undebt.it paying share |

## 4. Security and privacy invariants

These are release constraints, not preferences:

- Raw SMS, notification and email content never crosses the device boundary. A digest derived from
  raw content is also prohibited at network, sync and export boundaries.
- Money uses integer minor units with currency and exponent. Financial arithmetic is deterministic;
  AI explains results but does not calculate money or initiate payment.
- Ledger history is append-only and balanced per currency. Corrections use reversals.
- Tenant isolation is enforced at policy and row levels, including `FORCE ROW LEVEL SECURITY`.
- Sharing is default-deny, per member and category; aggregate and detail grants are distinct.
- Provider keys and custom destinations are backend-only, step-up protected, notified, revocable and
  suspended after account recovery. Client-direct AI traffic is prohibited.
- No human has standing production-data access. Unredacted reads require independent provenance,
  approval from a current roster with at least two independently eligible approvers, bounded
  elevation, immutable audit and subject-visible transparency.
- Erasure cannot report complete until key destruction, propagation and the restore barrier succeed.
- A no-training provider term is not ZDR. Provider/model/endpoint/feature eligibility is
  default-deny when contractual or technical evidence is missing or expired.

## 5. Verification ownership

| Verification class | Primary owners | Release position |
|---|---|---|
| Unit and component tests | Every implementation ticket | Required on every pull request |
| Property, independent-model and mutation tests for money | `T-QA-01`, `api#16` | Before deterministic debt work can complete |
| Provider/consumer contract and generated-client tests | `T-QA-02`, contract tickets | Contract-first; required before consumer merge |
| Sync, migration and prior-release compatibility | `T-SYN-01`–`T-SYN-04`, `T-MIG-01` | Required before offline queue and beta |
| Android instrumentation, accessibility and performance | `T-QA-08`, `T-QA-12` | Private-beta gate |
| Web end-to-end, accessibility and browser performance | `T-QA-06` | Before web release |
| Admin operator journeys and accessibility | `T-QA-13` plus `T-ADM-13` ticket tests | Rights queue before beta; full console before public launch |
| Privacy black-box traffic inspection | `T-QA-09` | Every release candidate |
| Tenancy, object-authorization and authentication attacks | `T-QA-03` | Private-beta gate |
| Static, dynamic, dependency, secret and flaky-test controls | `T-QA-04` | Required pipeline gate |
| IaC, container, mobile and supply-chain verification | `T-QA-11` | Private-beta gate |
| Load, stress, soak, chaos and disaster recovery | `T-QA-05` | Private-beta gate |
| Independent penetration and named red-team scenarios | `T-QA-10` | Public-launch gate |

`T-REL-02` is the executable private-beta gate. It now depends on the clarification journey, full
Android gate, attack suite, load/chaos suite, supply-chain checks, security controls, restore-safe
erasure, production-access governance, rights queue, API 36/Play declaration work, privacy controls
and Play permission journey. `T-REL-03` adds the independent penetration test, full admin/web/support,
billing and legal readiness required for public launch.

## 6. Parallel-delivery contract

- One ticket owns one branch-sized outcome. Native and legacy 13-point scheduled tickets must be
  split by their recorded deadlines before their sprint begins; each split updates dependencies,
  estimates, reviewer load and the lane proof.
- Contract changes merge and publish before consumers. Consumers pin versions and use generated
  clients; no repository invents a private wire shape.
- Native GitHub dependencies are authoritative and must match the ticket body.
- Database migrations use the registry and one in-flight migration lock. Expand/migrate/contract and
  compensating rollback evidence are mandatory.
- Draft pull requests expose integration risk early. Money and security paths require a distinct
  qualified reviewer; no reviewer exception weakens those paths.
- Three implementation lanes may proceed concurrently only within the persisted lane proof. The one
  independent reviewer has separate capacity and can become the pacing constraint. Capacity
  arithmetic assumes that reviewer is qualified for the assigned change; `T-GOV-03` verifies scope,
  evidence, expiry and author conflict and blocks work when the assumption is false.

## 7. External decisions that still block protected capabilities

These are intentionally owned gates, not missing requirements:

1. `T-CMP-04`: counsel must publish current India commencement, DPDP Rule 6/CERT-In retention,
   erasure and statutory-clock profiles before onboarding.
2. `T-QA-07` is now a numbered Sprint 05 prerequisite; `T-QA-12` consumes the physical-device and
   compatibility evidence before Android permission and release claims are accepted.
3. `T-REL-01`, `T-CMP-05`, `android#9`: Play declarations and restricted-permission approval must
   succeed before the corresponding test or production track is enabled.
4. `T-AI-06`: every managed AI provider/model/feature needs DPA, residency, retention and cost
   evidence before routing is enabled.
5. `T-GOV-03`: money/security changes remain blocked without a distinct qualified reviewer, even if
   implementation capacity is otherwise available.

## 8. Remaining planning risks

- Future dates are forecasts, not commitments. F19–F41 must be recalculated after every dependency
  or estimate change and replaced with measured velocity after three sprints.
- The current plan assumes three implementation lanes and one dedicated independent reviewer. A
  smaller team lengthens elapsed time; adding implementers without review capacity does not.
- Scheduled 13-point items are decomposition debt, not permission to merge oversized changes.
- Sprint 01–15 capacity is intentionally dense. The 18-sprint horizon is a zero-contingency
  feasibility floor; rework, staffing below three implementation lanes or qualification gaps can
  move the private-beta date.
- Policy, pricing, platform and provider claims expire. The owning ticket must revalidate primary
  sources before implementation or procurement.
- A green validator proves internal consistency and capacity, not product-market fit or legal
  correctness. User research, counsel decisions and release evidence remain independent gates.

## 9. Authorization

Start Sprint 01 foundation and governance work. Do not load production personal data before
`T-SEC-01` and `T-PLT-05` are effective. Do not enable SMS, notification capture, sharing, AI,
billing or administrative unmasking before their native blockers close. Do not invite private-beta
users until `T-REL-02` passes without an expired waiver.
