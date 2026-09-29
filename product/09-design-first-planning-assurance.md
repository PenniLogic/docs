# PenniLogic design-first planning assurance

> **Verdict: SHIP THE PLAN; HOLD MAPPED FRONTEND IMPLEMENTATION.**
>
> Governance, repositories, contracts, backend, security, infrastructure, research operations and
> design work may start when their ticket dependencies allow. Android, customer-web and admin
> frontend work remains blocked until its exact platform design dependencies and `T-DQA-12` close.
> This verdict authorizes the SDLC plan, not an uncreated visual design or a private-beta release.

## 1. Assurance scope

This third planning pass re-audited the complete architecture, product, security, compliance,
experience, delivery and verification graph after the UI/UX omission in the earlier plan was found.
It covers all eight repositories and GitHub Project 2, not only the six new design epics.

The durable sources are:

- `PRODUCT.md` for product truth and non-negotiable invariants;
- `product/08-experience-design-and-sdlc-plan.md` for the CDO-led operating model;
- `planning-automation/backlog-v2/evidence/experience-coverage.json` for exact traceability;
- `planning-automation/backlog-v2/` for executable epics, tickets, dependencies and capacity; and
- `planning-automation/validate-backlog-v2.ps1` for offline enforcement.

Earlier assurance documents remain useful history. Where they disagree on counts, dates, capacity or
frontend authorization, this document and the current backlog source win.

## 2. Final planning inventory

| Inventory | Current plan |
|---|---:|
| Epics | 38 |
| Implementation tickets | 312 |
| Source-native tickets | 274 |
| Strictly patched legacy tickets | 38 |
| Source-native points | 2,143 |
| Numbered-sprint assignments | 187 |
| Numbered-sprint points | 1,405 |
| Personas | 12 |
| End-to-end journeys | 12 |
| User stories | 38 |
| Platform flows | 38 |
| Registered screens/surfaces | 141 |
| Reusable component families | 57 |
| Required diagrams/specification sets | 21 |
| Mapped frontend tickets | 74 |
| Reasoned non-frontend client-repository exclusions | 20 |

The design-first pass added E33-E38, 68 research/design/Design-QA tickets and seven missing frontend
implementation tickets. The target Project contains 350 issue-backed items after synchronization.

## 3. No-clarification ticket contract

Every source-native ticket states:

1. outcome and context;
2. bounded scope and explicit non-goals;
3. acceptance criteria;
4. contracts and schema consequences;
5. security and privacy requirements;
6. observability without sensitive payloads;
7. required tests;
8. rollout and rollback;
9. dependencies and one parallel ownership boundary; and
10. Definition of Done.

All 61 pre-v2 issues have strict patches; all 38 legacy implementation tickets receive equivalent
cold-start sections. The sync derives an `Experience coverage` section into every affected design,
frontend and QA issue. It names exact persona, journey, user-story, flow, screen, state, component and
diagram IDs, so a team does not have to reverse-engineer its assignment from a Figma page or ask
which states and tests it owns.

One ticket remains one primary repository, one branch and one independently reviewable pull request.
A threshold-size ticket cannot enter its sprint without a dated split record.

## 4. Experience completeness

The planning registry is a bidirectional graph:

`Persona -> Journey -> User story -> Flow -> Screen -> Component -> Design/Implementation/QA`

Validation rejects duplicate or dangling IDs, orphan routes, one-way journey/flow or flow/screen
references, unused components, undeclared screen/component states, cross-platform component use,
wrong-repository implementation owners, non-independent QA owners and missing design ownership.

Every non-epic ticket in `android`, `web` or `admin` must be either:

- one of the 74 mapped frontend tickets; or
- one of 20 reviewed exclusions with a concrete nonvisual rationale.

This exhaustive partition prevents a new UI ticket from bypassing design merely by being omitted
from `frontend_tickets`.

Coverage includes authenticated and unauthenticated entry, consent and age eligibility, deny-all
manual use, account recovery and session revocation, debt and transaction management, clarification,
imports/exports, categories and rules, income/budgets/goals/net worth, split and household invite
acceptance, grants/revocation/safe exit, AI and BYOK/custom endpoints, subscriptions and quotas,
notifications, localization/accessibility preferences, trust/rights/support, operator recovery,
redaction/elevation/four-eyes access, lifecycle, billing, provider operations, audits, production
access, restore review, incidents and release evidence.

`surface_type` distinguishes pages, dialogs, sheets, overlays, system handoffs, widgets and
notification landings. Shared overlay/menu/snackbar/undo/stepper/FAB behavior is component-owned;
safety-critical uses remain attached to their controlling screen.

## 5. Design organization and gates

The CDO-led programme has named accountability for DesignOps, UX Research, Service Design,
Information Architecture, Android, web, admin, Design Systems, Content, Localization, Accessibility,
UX Engineering and independent Design QA.

D0-D9 gates separate:

- problem/evidence and journey/IA approval;
- visual direction and system design;
- prototype and research validation;
- immutable D6 design handoff;
- D7 built conformance;
- D8 release design QA; and
- D9 measured post-launch learning.

CDO approval is limited to material direction, D6/D8, major shared-system releases and exceptions.
Operational review is delegated with WIP limits and SLAs so the CDO is not a serial production
bottleneck.

`handoff-manifest.schema.json` fixes the D6 contract: immutable Figma version/frame IDs, exact
coverage IDs, contract versions and errors, designed/inherited/exempt states, synthetic fixtures,
content ranges, assets, accessibility, localization, privacy, telemetry, approvals, expiry and
checksum. `design-readiness.schema.json` fixes the cross-platform evidence aggregated by
`T-DQA-12`. No current record falsely claims that those future artifacts are already approved.

## 6. Security and financial correctness

The prior architecture/security decisions remain mandatory:

- integer minor-unit money plus currency/exponent;
- append-only balanced ledger with reversal-based correction;
- raw SMS, notification and email content remains on device;
- default-deny, per-person/per-category sharing with separate aggregate/detail grants;
- backend-routed AI that neither computes money nor initiates payment;
- server-authoritative entitlements and quotas;
- envelope encryption, blind indexes, row-level authorization and immutable audit;
- step-up, cooling-off and key suspension around recovery and provider credentials;
- redacted admin by default with provenance, qualification, four-eyes and time-boxed access; and
- restore-safe erasure, retention, rights and incident evidence.

The design registry gives privacy, revocation, denial, stale, destructive, quota and recovery states
explicit owners. Interface copy or client logic may not invent legal values, authorization, money
results or advice.

## 7. Verification and release assurance

The plan includes independent tasks and executable gates for:

- unit, property-based and deterministic money-model tests;
- API, event and generated-client contract tests;
- repository integration and cross-client compatibility;
- Android unit, instrumentation, device/API matrix and privacy traffic inspection;
- web/admin E2E, semantic, keyboard, screen-reader, zoom and performance checks;
- parser golden corpus, false-positive and compatibility regression;
- AI evaluation, refusal, provenance, prompt-injection and provider-failure cases;
- object authorization, tenancy, recovery and malicious-operator black-box attacks;
- SAST, SCA, secret, IaC, container, mobile and supply-chain analysis;
- load, stress, soak, chaos, backup and disaster-recovery exercises;
- heuristic, cognitive, moderated, unmoderated and longitudinal UX research;
- financial comprehension, localization, accessibility and coercion/dark-pattern review;
- design-system, screenshot, semantic and interaction conformance; and
- private-beta and public-launch evidence gates with expiring, attributable exceptions.

Design authors do not approve their own artifacts. Feature QA, security review, money-path review and
release evidence remain separate concerns even when they run in the same sprint.

## 8. Feasible parallel schedule

The numbered plan uses one two-week, 20-point lane clock with independent pools:

| Pool | Planned lanes | Review ceiling |
|---|---:|---:|
| Engineering | 3 | 20 |
| Product Design and UX | 6 | 40 |
| Quality Assurance | 4 | 40 |

The machine-checked lane proof contains 187 assignments with no overlap, capacity breach, cycle,
cross-sprint inversion or same-sprint dependency inversion. Review peaks are 18/20 Engineering,
30/40 Product Design and UX and 10/40 Quality Assurance.

Sprint 01 execution is preconditioned on the unscheduled `T-GOV-03`/`infra#4` agent-governance
adoption closing; their estimates are intentionally outside the numbered lane proof.

- `T-DQA-12` closes in Sprint 07.
- The first mapped frontend work starts in Sprint 08.
- The private-beta evidence gate closes in Sprint 16.
- Sprints 17-18 are explicit contingency, not hidden feature capacity.
- Future work is dependency-aware and indicative, not a sprint commitment.

## 9. Adversarial findings closed in this pass

The pass found and corrected:

- the missing CDO organization, design lifecycle and platform design backlogs;
- absent personas, user stories, journeys, sitemaps, screen/component/state registries and diagrams;
- invitation, consent, recovery, profile/session, preferences, notification and rule-management gaps;
- missing overlay/menu/snackbar/undo/FAB/stepper component contracts;
- missing QA-to-design dependencies and an infeasible QA sequencing assumption;
- a source-native derived-dependency schedule-validation blind spot;
- Android screens mapped to a web/admin-only table component;
- one-way journey/flow references and a prototype incorrectly modeled as a production route;
- client tickets able to avoid frontend classification;
- missing immutable D6 handoff/readiness schema shapes;
- missing ticket-visible coverage IDs; and
- a dry-run failure when legacy frontend issues depended on new, not-yet-created design tickets.

Deliberate fixtures confirm failure on a missing screen, dangling component, missing frontend mapping,
wrong design/QA pool, lane overlap, missing readiness-gate marker and disconnected release gate.
Valid and planted-invalid D6 evidence fixtures exercise both new evidence schemas.

## 10. Residual assumptions and execution holds

This is a complete development plan, not completed discovery or design evidence. The following are
intentional execution gates rather than unspecified work:

- visual identity, final navigation, production UI and language rollout remain open until their
  named CDO/research tickets close;
- quantitative usability thresholds are pre-registered by the research tickets before recruitment;
- legal/counsel and Google Play decisions remain external evidence, not assumptions;
- story-point capacity is a planning ceiling until measured velocity replaces it; and
- production access, beta and launch stay closed until their executable evidence gates pass.

Any new feature, route, client ticket, component or state changes the registry and reopens only the
affected design, implementation, QA and release evidence. The validator is the enforcement boundary;
a slide deck, Figma comment or manually edited Project card cannot waive it.
