# PenniLogic - Execution Readiness Review

> **Historical first gate.** Superseded by
> [`07-planning-assurance-iteration-2.md`](07-planning-assurance-iteration-2.md); retained as the
> evidence trail for the original HOLD and its remediation.
>
> Its one-collaborator review bootstrap is also superseded by
> [`../governance/AI-DEVELOPMENT-GOVERNANCE.md`](../governance/AI-DEVELOPMENT-GOVERNANCE.md):
> separate qualified agent sessions now provide logical implementation/review separation under the
> single GitHub user, and a required policy check validates their current-head attestations.

> **Verdict: HOLD for feature implementation.**
> Only governance, repository scaffolding, the two dependency-free infra items, and physical-device
> procurement are `Ready`. **E31 is the only `Ready` epic.** No money-path,
> ingestion, security, billing, sharing, or AI feature ticket may start until the architecture
> decision records that fix its shape are accepted.
>
> **Status:** audit complete, remediation projected into the durable planning source.
> **Scope:** the delivery system - board, backlog, gates, protocol - not the product strategy.
> **Canonical for:** what is safe to start, what is blocked, and what must be true before beta.
>
> **Historical measurement note.** Counts and point totals in this document describe the source at
> the time of this readiness review. Current totals are derived by
> `../planning-automation/validate-backlog-v2.ps1` and summarized in
> [`06-planning-assurance-audit.md`](06-planning-assurance-audit.md).

This document is the audit and hand-off record. It states the live state that was audited, the
remediated target, the gates that hold implementation, and the external blockers no plan can remove.
It does **not** reopen product decisions. Positioning, pricing, the lending prohibition, the advice
boundary, the admin posture, Route D for Account Aggregator, and the multi-repo structure remain
confirmed - see [`../00-EXECUTIVE-SUMMARY.md`](../00-EXECUTIVE-SUMMARY.md) and
[`../adr/README.md`](../adr/README.md).

---

## 1. Verdict

| Question | Answer |
|---|---|
| Is the product strategy sound? | Yes. Unchanged by this audit. |
| Is the research record sound? | Yes. Preserved in full; nothing here deletes it. |
| Can feature implementation start? | **No.** HOLD. |
| What can start? | Program governance (`T-GOV-01`, `T-GOV-02`, `T-GOV-03`), repository scaffolding (the `T-SCA-*` tickets in E01), the two dependency-free `infra` tickets, and undated physical-device procurement (`T-QA-07`) - **12 items in the Ready Queue**, plus E31. After `T-GOV-03`, `T-ADR-INDEX-10` establishes the per-record ADR layout; each architecture record then unlocks only its dependent lane, while the AI-egress and entitlement records remain scheduled with their consumers. |
| What lifts the HOLD? | Acceptance of the nine architecture decision records, per lane, one lane at a time. The HOLD is released incrementally, not globally. |
| What blocks the governance lane itself? | Nothing external. `T-EXT-01` is `Done`: GitHub Team was verified with an active private-repository ruleset and a temporary pull request blocked by both a required review and a pending required status check. |

The 12 startable implementation items are `T-GOV-01`, `T-GOV-02`, `T-GOV-03`, `T-QA-07`, one scaffolding ticket per
customer-facing repository (`T-SCA-API-01`, `T-SCA-CON-01`, `T-SCA-WEB-01`, `T-SCA-ADM-01`,
`T-SCA-AIS-01`, `T-SCA-AND-01`), and the two pre-v2 tickets that depend on nothing: `infra#2` (the
local development environment) and `infra#4` (CODEOWNERS, pull request template and contribution
conventions). **E31 is the only `Ready` epic.** `T-EXT-01` remains on the board as a completed,
unscheduled evidence item. No feature ticket is among the startable items.

`Ready` on this board is a claim that **nothing is in the way** - no open blocker, no unresolved
dependency, no pending decision. It is not a priority signal. Everything else is `Backlog`.

---

## 2. Audited live state, before remediation

The board was audited as it actually existed, not as it was described.

| Finding | Detail |
|---|---|
| Coverage | **23 epics and 38 tickets.** The plan document described a smaller, earlier shape. |
| Empty epics | **11 epics owned zero tickets.** An epic with a zero rollup owns no work; it is a planning error, not a small epic. |
| Dependencies | **No native `blockedBy` edges existed.** Dependencies were prose in issue bodies - unreadable by the board, unenforceable by tooling, and invisible in any view. |
| `Ready` violations | Items sat at `Ready` while work they depended on was still open, including items whose blockers had not been created yet. |
| Project metadata | Board title, short description and README were stale; several epic titles were cached mojibake from non-ASCII passed as a Windows CLI argument. |
| Schedule shape | Sprint assignments formed **serial chains**: work that could run in parallel was queued behind unrelated work, and some dependencies were scheduled *after* their dependents. |
| Team reality | **One collaborator, no teams.** Every "independent reviewer" and "second approver" control in the plan had no one to perform it. |
| Repositories | **All eight repositories were effectively empty.** No build, no test, no lint, no CI - so no ticket could be verified even if it were started. |
| Risk coverage | Billing unit economics, split-to-paid conversion, and reviewer/key-person concentration had no owning item on the board. |

The single most consequential finding is the combination of the last three: a plan whose quality
gates assume a reviewer that does not exist, running against repositories that cannot build, with
dependencies the board cannot enforce. That is why the verdict is HOLD rather than "start carefully".

---

## 3. Remediated target

The remediation is written as data in
[`../planning-automation/backlog-v2/README.md`](../planning-automation/backlog-v2/README.md) and
projected onto the board by `sync-backlog-v2.ps1`. The board is generated from that source; the
source is never generated from the board.

| Dimension | Before | After |
|---|---|---|
| Epics | 23 | **32** (9 new: E24 to E32) |
| Implementation tickets | 38 | **185** (147 new) |
| Strict patches to existing issues | - | **61** (23 epics, 38 tickets) |
| Named risks | R1 to R11 | **R1 to R15, plus `None`** (16 values) |
| Planning inventory | 306 points | **1601 points** |

**Reconciliation of the point total:** 306 (the 38 pre-existing tickets, and the number quoted in
the original delivery plan) + 1295 (the 147 new tickets) = **1601**.

> **1601 points is a visible planning inventory and a lower bound, not a measured final size.** It
> is the sum of the estimates that have actually been written down. Unknown implementation work,
> vendor integration details and findings discovered by the decision gates contribute nothing until
> decomposed, so the number can still grow. It is not a commitment, not a
> release date and not a velocity forecast. No date can be read off it before three sprints of
> measured velocity exist.

New epics: E24 platform and reliability, E25 quality and release assurance, E26 architecture decision
gates, E27 launch-blocking compliance floor, E28 advanced ingestion, E29 Account Aggregator
readiness, E30 globalization, E31 program governance, E32 server sync.

New risks: **R12 Billing economics**, **R13 Split conversion**, **R14 Key-person**, and
**R15 Data lifecycle**. `R2 Retention` is renamed **`R2 User retention`**, because it was reading
ambiguously against *data* retention and was being applied to erasure and retention-period work that
is a different failure class entirely. Every risk value now has at least one owning item, and the
[risk-to-ticket ownership matrix](02-risk-register.md#risk-to-ticket-ownership-matrix) is the
reconciliation target `T-CMP-04` checks automatically.

### What the hardening passes changed

| Gap | Correction |
|---|---|
| Sprint 01 Definition of Done was circular | The six scaffolds and `T-GOV-01`, `T-GOV-02`, `T-GOV-03` now record their check names and local reproduction commands *for* `T-SCA-INF-01` instead of requiring branch protection that does not exist yet. `T-SCA-INF-01` gains `T-GOV-03` as a dependency and **solely owns branch-protection wiring**; `infra#1` is a CI conformance gate only. |
| `T-GOV-03` was mechanically impossible with one collaborator | The general rule is now pull request plus passing checks with **no blanket approval requirement** during a time-boxed bootstrap. Money-path and security-path files are blocked by CODEOWNERS until a distinct qualified reviewer exists. The protected and exempt path set is machine-readable, carries one expiry date, and an automated check fails after it. Administrator bypass is disabled or alerted. |
| Pre-v2 field values were inherited, not chosen | All **61** pre-v2 items now carry a patch that states `Sprint` and `Status` explicitly. Only `infra#2` and `infra#4` stay `Ready`. |
| The AI quota dependency was a cycle | `T-AI-01` depends on the published quota contract `T-CON-03`, not on the billing implementation `T-BIL-02`. Gateway development runs against the contract and its mock; only production enablement stays gated. |
| Five cross-lane tickets were oversized | `T-CON-04` split into sharing / AI tools / admin API (5+5+3); `T-ADM-03` into redaction-and-unmask / elevation-and-monitoring (5+8); `T-AI-05` into dispatcher-and-defences / evaluation-and-spend (8+5); `T-SPL-01` into split ledger / authorization-and-settlement (8+5); `T-BIL-05` into webhook verification / lifecycle-and-reconciliation (5+8). Totals preserved. |
| The i18n gate was asserted, not backed | `T-QA-06` and `T-QA-08` now carry locale-aware INR formatting, pseudo-localization, long-string and right-to-left layout-safety criteria as MVP quality gates. Multi-currency remains E30 and is not claimed. |
| Protocol rules 4 to 6 were prose | `T-GOV-04` enforces them: contract-first pull request metadata, one in-flight migration through a registry and lock, reversible or compensating migration evidence, linked issue and native dependency validation, and early draft pull request visibility. |
| Legacy tickets were not cold-start equivalent to v2 tickets | All 38 legacy implementation tickets now gain Outcome, Scope, contracts, security, observability, tests, rollback, non-goals, Parallel boundary and ticket-specific Definition of Done content through strict, idempotent patches. The validator rejects a future legacy patch that omits that parity. |
| Web and product parity had unowned surfaces | Tickets now own web income and budgeting, goals, net worth, family, splitting, AI/BYOK and billing; personal net worth, refinance modelling, natural-language draft entry, provider failover, key rotation and complete billing unwind/convergence are also explicit work. |
| Physical-device procurement was blocked behind corpus governance | `T-QA-07` now owns only dependency-free procurement and is `Ready`; `T-QA-12` owns the sanitized corpus and the wider Android/OEM compatibility matrix after the test strategy lands. |
| Quality coverage stopped at source scanning | `T-QA-11` owns IaC, container, Android-binary, SBOM and signed-provenance gates; browser coverage names Chromium, Firefox and WebKit, and the Android gate names TalkBack, touch, contrast, motion, font and OEM constraints. |
| Parallel-PR mechanics were incomplete | `T-GOV-02` and `T-GOV-04` now require one ticket per branch/worktree, stable-ID naming, early draft and stack metadata, explicit merge/restack rules, merge-queue policy and numeric implementation/review WIP caps. |

### What the second hardening pass changed

| Gap | Correction |
|---|---|
| Branch protection was assumed to be configurable | It is not. The organisation is on **GitHub Free with eight private repositories**, so the branch-protection and ruleset endpoints return **HTTP 403**. `T-EXT-01` records the constraint with API evidence, prices the plan change, and proves the capability on a private fixture repository. `T-GOV-03` and `E31` now depend on it, which is why **no epic is `Ready`** and the Ready set is 11 rather than 12. The repositories stay private; that is not the lever. |
| Nine ADR tickets would have edited one file | `T-ADR-INDEX-10` splits `adr/README.md` into one file per decision and generates the index and pending table. ADR-015 to ADR-023 are reserved per ticket, and each gate ticket owns exactly one file, so nine worktrees never converge on the same lines. |
| Two entitlement schemas contradicted each other | `T-ADR-ENT-09` (ADR-023) is the ninth gate. It fixes plan and feature identity, request and token quota as separate dimensions, the per-plan model allowlist and unlisted-model refusal, BYOK quota treatment, event-sourced usage versus a materialized counter, and the reset boundary. It supersedes `architecture/01-domain-model.md` §5 and `architecture/03-stack-and-monetization.md` §8, both of which are now marked superseded in place. |
| Python was not a generated client target | The `ai-service` is Python and was consuming a contract it had no generated client for. `T-SCA-CON-01`, `contracts#1`, `T-QA-02` and `T-ADR-MONEY-01` now name Kotlin, TypeScript **and** Python, with a Decimal-backed money wrapper and a named serialisation seam. |
| Cross-user reads had no enforcement mechanism | `T-ADR-CRYPTO-04` now decides the grant-mediated read predicate under forced RLS - the exact predicate, the session context, the trusted setter - and forbids every bypass by name. `T-SEC-01` denies a cross-tenant read with no satisfied grant, `T-FAM-01` depends on both, and `T-CON-04` binds its grant reference to the database policy identifier. |
| Revocation was described two ways | It has **two bounds, not one**: an online bound for server-served reads and an offline lease bound for a disconnected client. `T-CON-04` publishes both as numeric contract metadata, `T-FAM-02` has an airplane-mode lease-expiry test, and the domain and security documents are reconciled - neither may be called "immediate". |
| The migration runner was four sprints behind the first migration | `T-MIG-01` (Sprint 03) owns the runner, the `T-GOV-04` registry integration and reversal evidence, ahead of the ledger schema in `api#2`. `T-ENV-01` keeps seed data only. `api#2` owns `FORCE ROW LEVEL SECURITY` and default deny; `T-SEC-01` owns the low-privilege role, write checks and invoker functions. |
| Import and privacy shapes were invented per endpoint | `T-CON-10` publishes the shared statement-import components and `T-CON-09` the export, consent, rights-request and transparency contract. `api#10`, `api#18`, `T-CON-02`, the compliance floor and the client trust surfaces all consume them. |
| Cold-start product surfaces had no owner | Account recovery (`T-AUTH-01`, `T-AUTH-02`), the transaction timeline (`T-AND-04`), Android budgeting parity (`T-AND-05`), notifications (`T-NOT-01`, `T-NOT-02`, `T-CON-11`), user support (`T-SUP-01` to `T-SUP-03`), the Android release pipeline (`T-REL-01`), retention (`T-RET-01`), plan versioning (`T-BIL-10`), admin quality (`T-QA-13`), admin access lifecycle (`T-ADM-06`), the web trust centre (`T-TRU-03`) and the shared client state taxonomy (`T-UX-01`) are all now owned. |
| The MVP and launch gates were checklists | `T-REL-02` (Sprint 14) is an executable private-beta evidence gate and `T-REL-03` is the public-launch gate. Both read artifacts, fail with the missing item named, and accept only a dated, expiring, attributable waiver. |
| Threat-model refresh was bundled with the penetration test | `T-QA-14` (Sprint 02, 3 points) owns the per-epic STRIDE refresh at Definition of Ready, enforced by `T-GOV-04` on an epic's first pull request. `T-QA-10` drops to 5 points and keeps only the external test and the red-team scenarios. Total points unchanged. |
| Quality thresholds were "agreed" rather than numeric | `docs#21` must publish per-package line, branch and mutation floors plus a flake quarantine ceiling and retry limit, as machine-readable data; a named package with no number fails the reconciliation check. `T-QA-01` reads those numbers instead of an unwritten agreement. |
| Accessibility had no stated target | `T-QA-06` and `T-QA-13` both state **WCAG 2.2 AA** with a named, pinned ruleset, and route what the scanner cannot decide to a manual walkthrough. |
| AI evaluation had no floor | `T-AI-06` now requires >=95% task accuracy, >=1000 governed synthetic cases with provenance, >=50 adversarial cases, a named corpus owner, pinned provider model versions, a rerun forced by any version change, and a harmful-answer report-contain-correct path tied to the kill switch and on-call. |
| Obligations and risks had no ownership map | `compliance/01-regulatory-landscape.md` gains an obligation-to-ticket matrix and `02-risk-register.md` a risk-to-ticket matrix. `T-CMP-04` owns the automated reconciliation that fails on an unowned obligation, an unowned risk or a dangling reference, and statutory values are read from versioned counsel-reviewed jurisdiction profiles that **fail closed** when absent or expired. |

---

## 3a. Capacity and what the sprint numbers mean

Sprints 01 to 14 are planned against a **maximum of 60 points per two-week sprint**: three engineers
or agents at 20 points each. It is a ceiling on what may be *planned*, enforced by
`validate-backlog-v2.ps1`, and not a claim about what will be *delivered*.

Two limits it deliberately does not model:

- **One independent reviewer is a separate bottleneck.** Review capacity does not scale with the
  three implementation lanes. Money-path and security-path work queues behind it, and `T-GOV-03`
  blocks those paths outright until a distinct qualified reviewer exists.
- **A one-person implementation takes proportionally longer.** With one engineer rather than three,
  the same content takes roughly three times the elapsed time. **These dates are not reliable for a
  single developer.** They are an ordering and a load profile.

806 of the 1601 points sit in Sprints 01 to 14. The remaining 795 are unscheduled - 792 `Future` and
3 in `Backlog` (`T-EXT-01`, which is a billing decision rather than sprint work). The accepted
sequence is governance and scaffolding, then the architecture decision records, then contracts,
ledger, auth and manual entry, then the deterministic debt engine, then security and the pre-beta
compliance floor, then ingestion automation, then the clarification inbox, the trust surfaces and the
MVP evidence gate. AI, groups, web, goals, notifications, support and the remaining post-MVP work
stay `Future` and carry no numbered sprint.

No numbered sprint exceeds the ceiling. The current source moves dependency-free physical-device
procurement (`T-QA-07`) out of engineering sprint load and brings `T-ADR-ADMIN-06` into Sprint 02,
before `T-SEC-03` freezes the append-only audit event schema it governs. `T-ADR-ERASE-07` remains in
Sprint 07 and `T-ENV-01` remains in Sprint 13.

---

## 4. Blocking architecture gates

Nine decisions are gates, not implementation details. Each is a ticket in **E26**, each depends on
`T-GOV-03`, and each is `Backlog` until the branch protection and code-owner policy it produces is in
place. The Team capability prerequisite is complete, so `T-GOV-03` is now `Ready`; no schema,
generated client, or money-path implementation lands before the record that fixes its shape is
accepted.

Each record is published as its own file under a **reserved number**, and the index and pending table
in `adr/README.md` are generated. `T-ADR-INDEX-10` owns that split and the generator. It is the
tenth ticket in E26 and it is not a decision: it exists so the nine that are can land in parallel
without nine worktrees editing the same lines.

| Gate | Ticket | File | Fixes |
|---|---|---|---|
| Money wire format, time, idempotency | `T-ADR-MONEY-01` | ADR-015 | Canonical decimal string plus currency at every JSON boundary; no raw float, no raw 64-bit integer; UTC instants with an explicit user time zone; idempotency key scope, lifetime and conflict behaviour on every financial write; the Kotlin, TypeScript **and Python** wrapper types and their serialisation seams |
| Category model | `T-ADR-CAT-02` | ADR-016 | Categories as an append-only reporting dimension rather than mutable rows that silently rewrite history |
| Ledger currency, FX, debt balance | `T-ADR-LEDGER-03` | ADR-017 | Ledger currency policy, foreign-exchange reservation, and how a debt balance is derived rather than cached |
| Encryption, search, RLS, grant-mediated reads | `T-ADR-CRYPTO-04` | ADR-018 | Encryption scope, which fields stay searchable (blind index), row-level security, and the exact predicate, session context and trusted setter that admit a grant-mediated cross-user read without any RLS bypass |
| Auth, passkeys, RP-ID, recovery | `T-ADR-AUTH-05` | ADR-019 | Provider choice, relying-party identifier - which is expensive to change after first enrolment - and account recovery |
| Administrative boundary and audit streams | `T-ADR-ADMIN-06` | ADR-020 | Admin deployment separation, database role, and the relationship between the foundational audit trail, the chained administrative log and the subject-visible transparency stream, including their stores and single-or-dual write semantics |
| Shared-data erasure | `T-ADR-ERASE-07` | ADR-021 | Crypto-shredding across shared data, and cross-user key access when one member's erasure affects another's balances |
| AI egress and Mode C | `T-ADR-AIEGRESS-08` | ADR-022 | AI egress path, runtime platform (including the ECS question), and Mode C custom endpoints |
| Entitlement and quota model | `T-ADR-ENT-09` | ADR-023 | Plan and feature identity, request and token quota dimensions, per-plan model allowlist and unlisted-model refusal, BYOK quota treatment, event-sourced usage versus materialized counters, and the reset boundary and its time zone. Supersedes the two conflicting entitlement sketches in the research documents |

These are implementation blockers. **They are not reopened product strategy.** ADR-001, ADR-002,
ADR-005, ADR-006 and ADR-007 remain accepted; these nine records specify the parts those decisions
deliberately left unspecified.

---

## 5. MVP and UX corrections

The audit found MVP scope that was named but not decomposed, and user-visible behaviour that had no
owning ticket.

- **Android auth, onboarding, manual entry, categories and statement import** are MVP, not
  post-MVP. Manual entry and import are the only ingestion mitigation entirely within our control
  (ADR-013), so "token fallback" quality is not acceptable.
- **Permission revocation** is a first-class flow. The app must remain fully usable with every
  permission denied, and revocation must not strand or corrupt already-captured data.
- **Conflict and rollback behaviour** must be defined and visible: what happens on a failed sync, a
  duplicate capture, a reversed correction, or a rolled-back release.
- **Trust and privacy surfaces** - permission dashboard, access log, discreet exit from a shared
  group, and full data export - are product features, not settings-screen filler.
- **Accessibility and internationalization** are gates, not polish. Budgets are enforced in CI
  (`T-QA-06`, `T-QA-08`), and the internationalization half is now backed rather than asserted:
  locale-aware INR formatting, a pseudo-localization run over every core journey, and long-string
  and right-to-left layout-safety checks. That is an MVP quality bar for a single-currency product;
  **multi-currency does not ship before E30 and is not claimed here.**
- **Physical device and golden corpus.** Real Indian bank SMS formats cannot be emulated. The device
  procurement ticket (`T-QA-07`) is dependency-free and `Ready`; the sanitized corpus and wider
  compatibility matrix are separately owned by `T-QA-12`.
- **The states between the happy paths are a shared vocabulary, not per-screen taste.** `T-UX-01`
  publishes one taxonomy - empty, loading, error, offline, stale, permission-denied, quota-exceeded,
  degraded - with machine-readable identifiers, and the client quality gates assert coverage against
  it. Before this, the same condition was called three different things in three tickets, which made
  the gates unenforceable.
- **Cold-start surfaces that had no owner now have one.** Account recovery and the lost-device path
  (`T-AUTH-01`, `T-AUTH-02`, and web registration and recovery folded into `T-WEB-01`); the
  transaction timeline a user actually lives in (`T-AND-04`); Android category, budget and reporting
  parity (`T-AND-05`); notifications end to end (`T-CON-11`, `T-NOT-01`, `T-NOT-02`) with the
  income, goals, admin, family, split and retention consumers wired to the outbox rather than to a
  provider; user support (`T-SUP-01`, `T-SUP-02`, `T-SUP-03`), which every existing help link now
  resolves to; the Android release pipeline (`T-REL-01`); retention with a written kill criterion
  (`T-RET-01`); plan versioning and grandfathering (`T-BIL-10`); administrator joiner, mover and
  leaver lifecycle (`T-ADM-06`); admin console quality gates (`T-QA-13`); and the web trust centre
  (`T-TRU-03`).
- **Retention is built with a stop condition.** `T-RET-01` carries an explicit kill and reconsider
  threshold - a named metric, a window, a value and the owner who decides - and a holdout group, so
  the programme is measured rather than assumed. No streaks, points, badges or leaderboards: that is
  a stated non-goal, not an omission.

---

## 6. Security and compliance corrections, before beta

Two hard program-level holds:

**Security holds real data.** No environment holds real user data before the data protection floor
is live in it: envelope encryption, blind index, row-level security, and the audit event service
(E19), on infrastructure with a **proven restore** and an alert that reaches a human (E24). A backup
that has never been restored is not a backup.

**Compliance holds beta.** The launch-blocking compliance floor (E27) must close before beta:

- Consent ledger, purpose registry, data-principal rights, and retention jobs (`T-CMP-01`).
- Pre-onboarding consent, the age gate, and the permission dashboard (`T-CMP-02`).
- Third-party component/SDK inventory, payload scrubbing, and the Play **Data Safety** declaration
  (`T-CMP-03`). The SDK inventory is not paperwork: Play policy bans transfer of SMS-derived data,
  and the inventory is how we prove no SDK is near it. Automated **traffic capture** on every release
  candidate (`T-QA-09`) is the evidence.
- Compliance floor pack and a rehearsed **CERT-In breach reporting drill** - 6-hour reporting,
  180-day log retention (`T-CMP-04`). Those figures, like every statutory value in this plan, are
  read at runtime from a **versioned counsel-reviewed jurisdiction profile** with a reviewer, a
  review date and an expiry. `T-CMP-04` owns the profiles and the automated reconciliation; when no
  current profile exists the dependent behaviour **fails closed** rather than asserting an
  unreviewed position.
- A **grievance channel with a named officer and a published response clock** (`T-CMP-01`), because
  a rights request with nobody counting the clock is not a rights process.
- The shared **export, consent, rights-request and transparency contract** (`T-CON-09`), so the
  compliance floor, the Android trust surfaces and the web trust centre implement one set of shapes.

Every launch-relevant obligation is mapped to its owning ticket in the
[obligation-to-ticket matrix](../compliance/01-regulatory-landscape.md#0-obligation-to-ticket-ownership-matrix),
and `T-CMP-04` fails when an obligation there has no owner or names a ticket that does not exist.

E20 keeps only post-beta work: counsel review, role and transfer registers, payment self-assessment,
and global readiness. Detail in
[`../compliance/01-regulatory-landscape.md`](../compliance/01-regulatory-landscape.md) and
[`../architecture/02-security-architecture.md`](../architecture/02-security-architecture.md).

---

## 7. Quality matrix

The full verification surface, owned by **E25**. Each row has an owning ticket; none is aspirational.

| Layer | Technique | Where |
|---|---|---|
| Unit | Deterministic unit tests | every repo, CI gate |
| Property | Invariant and generative tests on money math | `T-QA-01` |
| Mutation | Mutation score against the numeric per-package floor published by `docs#21` | `T-QA-01` |
| Coverage floors | Numeric line and branch floors per named package, machine-readable | `docs#21`, consumed by `T-QA-01` and `T-QA-04` |
| Flake control | Numeric quarantine-rate ceiling and retry limit, gated | `docs#21`, `T-QA-04` |
| Integration | Service plus real database | api, ai-service |
| Contract | Provider and consumer verification against the published spec, Kotlin, TypeScript and Python | `T-QA-02` |
| End-to-end | Journey tests, web, instrumented Android and admin operator journeys | `T-QA-06`, `T-QA-08`, `T-QA-13` |
| Black-box | Behavioural tests from the specification only | `T-QA-02`, `T-QA-06` |
| White-box | Coverage-directed and internal-invariant tests | `T-QA-01`, `T-QA-03` |
| SAST | Static analysis, dependency and secret scanning as a hard gate | `T-QA-04` |
| DAST | Dynamic scanning of running services | `T-QA-04` |
| Supply chain | IaC, container, Android binary, SBOM and signed provenance | `T-QA-11` |
| Authorization attack | Tenancy, object-authorization and authentication abuse suite | `T-QA-03` |
| Threat model | Per-epic STRIDE refresh at Definition of Ready, enforced on an epic's first pull request | `T-QA-14`, enforced by `T-GOV-04` |
| Load / stress / soak | Sustained and breaking-point profiles | `T-QA-05` |
| Chaos | Dependency failure and partition injection | `T-QA-05` |
| Restore / DR | Performed restore drill and a disaster-recovery game day | `T-PLT-02`, `T-QA-05` |
| Accessibility | WCAG 2.2 AA with a named pinned ruleset, automated plus manual audit, budgeted in CI | `T-QA-06`, `T-QA-08`, `T-QA-13` |
| Client state coverage | Every surface handles every applicable state identifier | `T-UX-01`, asserted by `T-QA-06`, `T-QA-08`, `T-QA-13` |
| Internationalization | Locale-aware INR formatting, pseudo-localization, long-string and RTL layout safety | `T-QA-06`, `T-QA-08` (framework: `T-GLO-02`) |
| Performance | Enforced budgets, web, Android and admin | `T-QA-06`, `T-QA-08`, `T-QA-13` |
| Privacy inspection | Traffic capture proving no raw message content egresses | `T-QA-09` |
| Insider-risk controls | Planted-defect gate on redaction, unmask and four-eyes operator journeys | `T-QA-13` |
| AI evaluation | Grounding, refusal, advice-boundary and prompt-injection evals against a governed corpus with a >=95% accuracy floor | `T-AI-05`, `T-AI-06` |
| Billing replay | Purchase, renewal, refund and entitlement replay | `T-BIL-05`, `T-BIL-06` |
| Penetration test | Independent external test plus red-team scenarios | `T-QA-10` |
| Release rollback | Rehearsed deploy rollback and staged release control | `T-PLT-01`, `T-REL-01` |
| Android release gate | Play App Signing custody, track promotion, staged rollout halt on Vitals budgets | `T-REL-01` |
| Delivery protocol | Contract-first metadata, migration lock, dependency and draft-visibility checks | `T-GOV-04`, `T-MIG-01` |
| Compliance reconciliation | Obligation and risk matrices reconciled against the board, jurisdiction profiles fail closed | `T-CMP-04` |
| Release evidence | Executable private-beta and public-launch gates reading artifacts, not checklists | `T-REL-02`, `T-REL-03` |

Flaky tests are quarantined, not ignored, and the quarantine is itself gated (`T-QA-04`) against the
numeric ceiling `docs#21` publishes.

---

## 8. Parallel development protocol and hard gates

Published by `T-GOV-02`, made authoritative by `T-GOV-01`, and **enforced as required checks by
`T-GOV-04`**. Rules 4, 5 and 6 were previously asserted and are now failed by a check.

1. **One ticket, one primary repository, one branch, one pull request.** A ticket that spans
   repositories is split, and each part names its own primary repository.
2. **Native `blockedBy` edges are the dependency authority.** Prose in a body is documentation, not a
   dependency. On a source-owned item, an edge the source does not declare is stale and is deleted.
   `T-GOV-04` fails a pull request that names no plan item, or names one whose blockers are open.
3. **Only dependency-free work may be `Ready`.** The sync forces `Ready` down to `Backlog` whenever a
   declared blocker is open. This is enforced, not aspirational.
4. **Contract-first, expand-migrate-contract.** The contract changes first and additively; consumers
   migrate; only then is the old shape removed. `T-GOV-04` requires pull request metadata naming the
   change class and, for a breaking consumer change, the contract pull request that precedes it.
5. **Migrations are serialized.** One schema migration in flight at a time, reversible, with the
   rollback rehearsed. `T-GOV-04` owns a migration registry and a lock: a second in-flight migration
   fails the pull request and the message names the lock holder, and a migration without reversal or
   compensating evidence fails.
6. **Draft pull requests early.** `T-GOV-04` reports a branch pushed beyond the published window
   with no open pull request, so two lanes cannot silently converge on the same file.
7. **Money-path and security-path changes require a distinct qualified reviewer.** Not a preference,
   and not a blanket rule over every pull request: `T-GOV-03` configures CODEOWNERS so those paths
   are *blocked* until such a reviewer exists, while general work merges on pull request plus
   passing checks during a time-boxed, machine-readable, expiring bootstrap.
8. **Automated review is supplemental.** Copilot review, linters and scanners do not satisfy the
   code-owner reviewer gate. They reduce the reviewer's load; they do not replace the reviewer.

### Reading the Definition of Done line about independent review

Every ticket carries a Definition of Done line that begins *"merged behind an approved review from a
reviewer who is not the author"*. Read literally with one collaborator, that line blocks the entire
board, which is exactly how a control gets quietly switched off. It is therefore **explicitly subject
to the time-boxed bootstrap `T-GOV-03` records**, and the line itself says so.

What that does and does not mean:

- **General work.** During the bootstrap window, a ticket that touches no money-path and no
  security-path file merges on pull request plus passing required checks, with no blanket second
  approval. The bootstrap carries **one machine-readable expiry date**, and an automated check fails
  after it. It is an interim with an end, not a permanent relaxation.
- **Protected paths.** Money-path and security-path files are **not** softened by that wording.
  CODEOWNERS blocks them outright until a distinct qualified reviewer exists. There is no bootstrap
  exception, no self-approval and no administrator bypass; where the platform cannot disable bypass,
  it is alerted on.
- **The precondition.** None of this is enforceable today. On GitHub Free with private repositories
  the branch-protection and ruleset APIs return HTTP 403, so `T-EXT-01` is the precondition for
  `T-GOV-03` being anything other than a document. Until it closes, the reviewer gate is a written
  intention, and the plan says so rather than implying otherwise.

---

## 9. Known external blockers and assumptions

These remaining items are outside the plan's control. **No amount of planning removes them**, and the schedule should
be read as conditional on all of them.

| Blocker | Why it is external | Consequence if unresolved |
|---|---|---|
| **Second independent reviewer** | Requires a second person. One collaborator exists today. | Money-path and security-path files stay blocked by CODEOWNERS; the rest of the work still merges on pull request plus passing checks. `T-GOV-03` records a time-boxed, machine-readable expiry; it is an interim, not a solution. (R14 Key-person.) |
| **Physical Android device with an Indian SIM** | Real bank SMS formats cannot be emulated or bought. | Parser coverage stays unvalidated on real traffic. (R6 Parser rot.) |
| **Legal counsel and DPAs** | Third-party professional and vendor availability. | The versioned jurisdiction profiles `T-CMP-04` owns cannot be produced, so every statutory value - reporting windows, response clocks, retention periods, tax thresholds - **fails closed** rather than being guessed. `T-CMP-01`, `T-BIL-03` and `T-BIL-04` cannot ship a claim without a current profile. |
| **Store permission review** | Google decides, on its timetable, after we file. | An unresolved declaration blocks *all* publishing, including pricing and listing changes - so it is filed during beta, not launch week. `T-REL-03` fails without the approval evidence. (R1 SMS permission.) |
| **Vendor and pricing revalidation** | Every price and version in the research is date-stamped September 2026 and volatile. | Unit economics and stack claims must be re-verified before any purchase or contract. (R7 AI cost, R12 Billing economics.) |

Each is tracked on the board against its named risk. None can be closed by writing a better plan.
The resolved GitHub plan prerequisite remains recorded as `T-EXT-01`, with the capability matrix in
PenniLogic/infra and the temporary enforcement proof removed after verification.

---

## 10. Source-of-truth precedence

1. **[`../planning-automation/backlog-v2/`](../planning-automation/backlog-v2/README.md)** - the
   durable planning source. Authoritative for titles, bodies, field values, dependencies, epic
   parentage and estimates. If the board disagrees, the board is wrong.
2. **The board** - [PenniLogic Delivery](https://github.com/orgs/PenniLogic-old/projects/2).
   Authoritative for what only it knows: issue numbers, node ids, assignees, comments, and human
   forward progress past `Ready`.
3. **Native `blockedBy` edges** - authoritative for dependencies.
4. **[`../adr/README.md`](../adr/README.md)** - authoritative for architecture decisions. Its
   accepted index and its pending gate table are **generated** from one file per decision under
   `adr/`, owned by `T-ADR-INDEX-10`; the nine E26 records land as ADR-015 to ADR-023 in their own
   reserved files. A generated region is never hand-edited.
5. **This document** - authoritative for the execution verdict and the gate list.
6. **[`03-delivery-plan.md`](03-delivery-plan.md)** - the original research-phase schedule. Retained
   as the reasoning record; its point totals, its sprint assignments and its dates are
   **superseded** for execution by items 1 and 5. In particular its Sprint 11 to Sprint 14 column -
   web, income and budgeting, billing, admin console, trust controls - no longer describes where
   that work sits: those epics are `Future` and carry no numbered sprint, except the Android trust
   surfaces (`T-TRU-01`, `T-TRU-02`) which are Sprint 14.

Where a research document and an accepted record disagree, the record wins. Two research sections are
already marked superseded in place: `architecture/01-domain-model.md` §5 and
`architecture/03-stack-and-monetization.md` §8, both by ADR-023 (`T-ADR-ENT-09`).
`architecture/02-security-architecture.md` carries an ownership pointer table at the top for the same
reason: a research-era deferral in that document is not implementation authority, and the table names
the item that actually decides each topic.

Related: [`02-risk-register.md`](02-risk-register.md) for R1 to R15 in narrative form plus the
risk-to-ticket ownership matrix, [`../compliance/01-regulatory-landscape.md`](../compliance/01-regulatory-landscape.md)
for the obligation-to-ticket matrix, and [`../planning-automation/README.md`](../planning-automation/README.md)
for tooling.

---

## 11. What this review does not claim

A green validator and a clean sync mean the board matches the plan. Nothing more. This review does
not assert that any acceptance criterion is the right one, that any estimate is accurate, or that the
code which eventually closes a ticket is correct. It does not claim the point total is the final
size of the work: it is the inventory that is currently visible and a lower bound on what will be.
It does not claim the sprint dates are achievable by one person; they are planned against three
implementation lanes and one reviewer, and a single developer should read them as an ordering rather
than a calendar. Code review, threat modelling and the code-owner reviewer gate are separate
controls, and none of them are replaced here.
