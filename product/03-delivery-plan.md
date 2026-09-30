# PenniLogic — Delivery Plan

> ## Superseded for execution — read this first
>
> **This is the original research-phase schedule, dated 2026-09-01.** It is retained as the reasoning
> record: why the epics exist, how the five perspectives were applied, and what the Definition of
> Ready/Done and quality gates were derived from. All of that still stands.
>
> **Its numbers and dates do not.** The **306 points across Sprints 01-10**, the sprint assignments,
> and the "MVP by end of Sprint 10" target were computed against a 20-epic/38-ticket board that no
> longer describes the work. Current board counts, points and sprint load are derived by
> `../planning-automation/validate-backlog-v2.ps1`; this historical plan does not hardcode them.
>
> **The §4 sprint table is superseded in full.** The current design-first plan has 38 epics and 312
> implementation tickets, scheduled in independent Engineering (3 x 20-point), Product Design and UX
> (6 x 20-point), and Quality Assurance (4 x 20-point) pools. `T-DQA-12` closes the CDO design
> readiness gate in Sprint 07; mapped frontend work begins no earlier than Sprint 08; `T-REL-02`
> closes private beta in Sprint 16; Sprints 17-18 are contingency. Capacity is an assumption, not
> measured velocity. Every assignment comes only from the durable backlog source and its executable
> pooled-lane proof.
>
> For execution, the authoritative sources are:
> * [`../planning-automation/backlog-v2/README.md`](../planning-automation/backlog-v2/README.md) — the durable board source
> * [`08-experience-design-and-sdlc-plan.md`](08-experience-design-and-sdlc-plan.md) — the current CDO-led design and SDLC operating contract
> * [`09-design-first-planning-assurance.md`](09-design-first-planning-assurance.md) — the current calibrated planning verdict
>
> Where this document and those sources disagree, the current sources win. The historical body below is deliberately
> left unedited.

> **Status:** 2026-09-01. Drives the GitHub Project at
> <https://github.com/orgs/PenniLogic-old/projects/2>
> **Basis:** the research phase in this repo. Every epic traces to a documented decision or risk.

---

## 1. Planning assumptions — state them, because everything depends on them

| Assumption | Value | If wrong |
|---|---|---|
| Team size | 1–3 engineers | Sprint capacity scales linearly; sequence does not change |
| Sprint length | 2 weeks | — |
| Capacity | 20 points/sprint/engineer | Estimates are relative, so velocity self-corrects after ~3 sprints |
| Start | Sprint 01, Sept 2026 | — |
| MVP target | End of Sprint 10 (~5 months) | Phases 0–2 are the MVP; 3+ are post-MVP |

> **Estimates are story points, not days.** Anyone reading a date off these numbers before three
> sprints of measured velocity exist is guessing.

---

## 2. Perspective summary

The plan was built by asking five different questions of the same product. Each surfaced work the
others missed.

| Perspective | Central question | What it added |
|---|---|---|
| **Product / PM** | Will anyone use and pay for this? | Debt-first sequencing; retention instrumentation from day one; kill-criteria for the wedge |
| **Solution Architect** | What is expensive to change later? | Ledger correctness before features; contracts-first; spikes before commitments; ADR gates |
| **Developer** | Can I actually build this ticket? | Acceptance criteria, interface definitions, explicit non-goals, technical notes per ticket |
| **Test** | How do I know it works? | Test strategy per layer; the golden-corpus regression suite for parsers; device matrix |
| **QA** | Should this ship? | Definition of Ready/Done; non-functional gates; release checklist; policy-compliance gates |

### 2.1 Product / PM lens

The dominant risk is **retention (R2)**, not technology. Mint had 22M users and died. Therefore:
- **Ship the debt engine first.** It is the reason to install and return.
- **Instrument activation and week-4 retention from the very first release.** If W4 retention is
  bad, no feature fixes it — the positioning is wrong, and we need to know in weeks, not quarters.
- **Kill criteria:** if, after the Phase 1 beta, users do not return to check their payoff date,
  stop and re-examine positioning before building Phases 3–5.

### 2.2 Solution Architect lens

Order work by **cost-of-change**, not by visibility:
1. **Ledger correctness first.** Money representation and double-entry are effectively irreversible.
2. **Contracts before clients.** Three clients consume one API; drift is the main multi-repo failure.
3. **Spikes before commitments.** Parser coverage, Play declaration, and sync are each unknown enough
   to warrant a timeboxed spike before an epic depends on them.
4. **ADR gates.** Any decision that changes an ADR stops for review rather than being absorbed
   silently into a PR.

### 2.3 Developer lens

Every ticket must answer: what am I building, how do I know it's right, and what is explicitly out of
scope? Tickets therefore carry context, acceptance criteria, technical notes, non-goals, and
dependencies. A ticket that cannot be picked up cold is not ready.

### 2.4 Test lens

| Layer | Approach |
|---|---|
| Ledger/domain | Property-based tests. The zero-sum invariant is machine-checkable — exploit that. |
| Parsers | **Golden corpus** regression suite. Every real SMS format ever seen becomes a permanent case. |
| API | Contract tests against the OpenAPI spec |
| Android | Unit + instrumented; device matrix incl. **API 31 vs current** for restricted settings |
| E2E | Playwright for web/admin; critical journeys only |
| AI | Eval suite for correctness and refusal; adversarial prompt-injection cases |

### 2.5 QA lens

Quality gates that must hold before anything ships — see §6.

---

## 3. Epics

Each epic maps to a phase and carries an exit criterion. An epic is not "done" when its tickets
close; it is done when its exit criterion is demonstrably met.

| # | Epic | Phase | Exit criterion |
|---|---|---|---|
| E01 | Engineering foundations | P0 | CI green on all repos; one command brings up a dev environment |
| E02 | Contracts & domain model | P0 | OpenAPI published; ledger schema migrated; zero-sum invariant enforced in DB |
| E03 | Identity & accounts | P0 | A user can register, sign in, and create accounts, with sessions surviving restart |
| E04 | Ledger & transactions | P0 | Manual transactions post correct double entries; balances always recompute from entries |
| E05 | **Debt engine** | P1 | Payoff date, strategy comparison, and simulator produce results verified against an independent amortisation model |
| E06 | Debt UX (Android) | P1 | A user can add debts and see their payoff date offline |
| E07 | Retention instrumentation | P1 | Activation and W1/W4 retention visible in a dashboard |
| E08 | Ingestion pipeline | P2 | Events from any source normalise, dedupe, and score confidence |
| E09 | SMS capture + Play declaration | P2 | Declaration **submitted**; on-device parsing live behind a flag |
| E10 | Notification capture | P2 | Payment-app notifications produce transactions on API 31 and current |
| E11 | Clarification inbox | P2 | Low-confidence transactions are resolved by the user in a batched flow |
| E12 | Web application | P3 | Feature parity with Android for analysis and entry |
| E13 | Admin console | P3 | Admin can manage plans/quotas; financial data redacted by default with JIT access |
| E14 | Subscriptions & entitlements | P3 | Play + web purchase grants entitlement; quotas enforced server-side |
| E15 | Split groups | P4 | Group expenses split, simplified, and settled without money being created or destroyed |
| E16 | Family groups | P4 | Per-category revocable sharing with access transparency |
| E17 | AI harness | P5 | All three modes (managed/BYOK/custom) work with quota enforcement and SSRF defence |
| E18 | AI product features | P5 | Categorisation, insights, and Q&A grounded in deterministic tool output |
| E19 | Security hardening | Cross | Independent pen test passed |
| E20 | Compliance readiness | Cross | DPDP checklist complete; policies published; breach runbook tested |
| **E21** | **Income & budgeting** | P3 | Salary detected; budgets work for irregular income; safe-to-spend reconciles to the ledger |
| **E22** | **Goal planning** | P4 | Goals projected deterministically; multi-goal competition modelled; advice boundary respected |
| **E23** | **User-facing trust & privacy** | P3 | App lock, privacy mode, accurate "what leaves your device" screen, working export and deletion |

> **E21–E23 were added during review.** The first planning pass covered 7 of the 9 product-spec
> feature sections. Income/salary awareness (§3.3) and goal planning (§3.4) had no epic despite both
> being headline requirements in the original brief, and the user-facing trust controls (§3.9) were
> only partially covered by the backend security and compliance epics.
>
> Worth noting as a process lesson: the gap was invisible when reading the epic list on its own. It
> only surfaced from mechanically diffing the product spec's feature sections against the epics.

---

## 4. Sprint plan

Actual committed load, as configured in the project board (2026-09-01):

| Sprint | Dates | Focus | Epics | Tickets | Points | Milestone |
|---|---|---|---|---|---|---|
| 01 | 09-07 → 09-18 | Repo scaffolding, CI, dev env | E01 | 4 | 21 | Walking skeleton |
| 02 | 09-21 → 10-02 | Contracts, money primitive, ledger schema | E02 | 5 | 36 | **Ledger correct** |
| 03 | 10-05 → 10-16 | Auth, accounts, transactions, import | E03, E04 | 7 | 44 | First usable slice |
| 04 | 10-19 → 10-30 | Debt model + amortisation engine | E05 | 2 | 21 | — |
| 05 | 11-02 → 11-13 | Strategies, simulator, verification suite | E05 | 4 | 29 | **Debt engine verified** |
| 06 | 11-16 → 11-27 | Android debt UX, offline, analytics | E06, E07 | 6 | 48 | **Phase 1 beta** ← validate the wedge |
| 07 | 11-30 → 12-11 | Ingestion pipeline, dedupe, enrichment | E08 | 3 | 34 | — |
| 08 | 12-14 → 12-25 | On-device parser + Play declaration filed | E09 | 3 | 34 | **Declaration submitted** (long lead) |
| 09 | 12-28 → 01-08 | Notification capture, device matrix | E10 | 2 | 21 | — |
| 10 | 01-11 → 01-22 | Clarification inbox, release gates | E11 | 2 | 18 | **MVP feature-complete** |
| 11 | 01-25 → 02-05 | Web app core, income & budgeting | E12, E21 | *not decomposed* | — | — |
| 12 | 02-08 → 02-19 | Entitlements + Play/Razorpay billing | E14 | *not decomposed* | — | **Monetisation live** |
| 13 | 02-22 → 03-05 | Admin console + JIT access controls | E13 | *not decomposed* | — | — |
| 14 | 03-08 → 03-19 | Security, compliance, trust controls, pen test | E19, E20, E23 | *not decomposed* | — | **Public launch ready** |
| Future | — | Split groups, family groups, goals, AI | E15–E18, E22 | *not decomposed* | — | Post-launch |

**Total committed: 306 points across Sprints 01–10** — roughly 30 points per sprint, consistent with
1–2 engineers at the assumed 20 points each. Full dates in §7.4.

### Two deliberate choices in this plan

**Epics carry no story points.** Points live on deliverable tickets only, in the `Estimate` field. If
epics were also sized there, every sprint total would double-count the epics that have been broken
down, and anyone summing the board would get roughly twice the real number. Epic-level sizing lives
in a separate `Rollup` field (the sum of that epic's children), surfaced in the **Epic Rollups**
table because GitHub's Roadmap layout does not expose custom number fields.
Ticket `Estimate` total and epic `Rollup` total both equal **306** — that equality is the check that
no work is double-counted or orphaned.

**Sprints 11+ are intentionally not decomposed yet.** Detailed tickets exist through Sprint 10, which
covers the MVP. Writing detailed acceptance criteria for work six months out would be speculative,
and the Sprint 06 beta may well change what Sprints 11+ should contain. Decompose each phase as it
approaches.

> **Why the Play declaration lands in Sprint 08 rather than later:** review takes 7–14 days, appeals
> 2–4 weeks, and an unresolved declaration **blocks all publishing** — including store listing and
> pricing changes. Filing it during beta rather than at launch keeps that risk off the critical path.

### The decision point that matters most

**Sprint 06 is a genuine go/no-go.** It ships the debt-first wedge to real users with retention
instrumentation already in place. If week-4 retention is poor, the positioning is wrong — and no
amount of Phase 2–5 work fixes a positioning problem. Agree the kill criteria *before* the beta, not
after seeing the numbers.

> **Why the Play declaration lands in Sprint 08 rather than later:** review takes 7–14 days, appeals
> 2–4 weeks, and an unresolved declaration **blocks all publishing** — including store listing and
> pricing changes. Filing it during beta rather than at launch keeps that risk off the critical path.

---

## 5. Definition of Ready / Done

### Definition of Ready (a ticket may be started)
- [ ] Outcome stated in user-observable terms
- [ ] Acceptance criteria are testable
- [ ] Dependencies identified and unblocked
- [ ] Estimated
- [ ] Component and phase assigned
- [ ] Design/ADR settled where the ticket touches an architectural decision
- [ ] The ticket's epic has a dated STRIDE threat-model refresh that is `current` for
      `python scripts/check_threat_model.py --epic <epic>`: recorded in
      `governance/threat-model/records/<epic>.json` before the epic's first ticket starts, within the
      published 12-week cadence and against the current category list, with every finding closed or
      handed to a named ticket; and the ticket is listed in that refresh's `tickets_in_scope`
      (`python scripts/check_threat_model.py --ticket PenniLogic/<repo>#N`), or, where it introduces
      a new data class, trust boundary, external party, AI capability, sharing path or money flow, a
      `scope_changed` refresh dated after the ticket's scope was fixed lists it (`T-QA-14`; see
      `governance/threat-model/README.md`). A stale refresh or an invalid record blocks Ready for
      every ticket in the epic, as does a finding without an owner; the test-evidence items in
      `governance/test-strategy.md` section 14 apply in addition to this list.

### Definition of Done (a ticket may be closed)
- [ ] Acceptance criteria demonstrably met
- [ ] Tests written and passing; **no reduction in coverage of money-handling code**
- [ ] Code reviewed
- [ ] No secrets introduced; dependency additions reviewed against the SDK policy
- [ ] Money paths use integer minor units — verified, not assumed
- [ ] Docs/ADR updated if behaviour or a decision changed
- [ ] Observability in place for anything user-facing or failure-prone

---

## 6. Non-functional gates

These are release-blocking. They exist because this is finance software.

| Gate | Requirement |
|---|---|
| **Correctness** | Ledger zero-sum invariant enforced in DB. Debt maths validated against an independent model. No float in any money path. |
| **Privacy** | Raw SMS/notification text never transmitted — verified by inspecting traffic, not by reading code. |
| **Security** | No secrets in repos; authz default-deny; admin financial views redacted by default; pen test passed before public launch. |
| **Performance** | App cold start < 2s on a mid-range device; transaction list smooth at 10k rows. |
| **Reliability** | Offline capture never loses a transaction. Idempotent writes — a retry never duplicates. |
| **Compliance** | Play declaration approved before SMS ships to production. DPDP consent + export + deletion working. |
| **Accessibility** | Core flows navigable by screen reader; text scales without truncation. |

---

## 7. The project board

**<https://github.com/orgs/PenniLogic-old/projects/2>**

### 7.1 Field schema

Every item carries these attributes. Consistency here is what makes the board queryable rather than
merely decorative.

| Field | Type | Values | Purpose |
|---|---|---|---|
| **Status** | select | Backlog · Ready · In Progress · In Review · In Test · Blocked · Done | Workflow state |
| **Kind** | select | Epic · Story · Task · Spike · Bug · Chore | Item taxonomy |
| **Phase** | select | P0 Foundations → P6 Moat | Roadmap phase |
| **Sprint** | select | Backlog · Sprint 01–18 · Future | Iteration |
| **Component** | select | android · api · ai-service · web · admin · contracts · infra · docs · cross-cutting | Owning repo |
| **Priority** | select | P0 Critical · P1 High · P2 Medium · P3 Low | Urgency |
| **Perspective** | select | Product · Architecture · Development · Test · QA · Security · Compliance · Ops | Which lens owns it |
| **Risk** | select | R1–R15 · None | **Traceability to the risk register** |
| **Estimate** | number | Fibonacci points | Sizing — **deliverable tickets only** |
| **Rollup** | number | Sum of child estimates | Epic-level sizing in the Epic Rollups view |
| **Start** | date | Ticket sprint start / earliest dated epic child | Roadmap timeline bar |
| **Due** | date | Ticket sprint end / latest dated epic child | Roadmap timeline bar |

> **Field names are deliberately single words.** GitHub's project filter syntax is `field:value`,
> and multi-word field names do not filter reliably — `-"Work Type":Epic` is stored literally and
> matches nothing, silently emptying the view. `Kind`, `Risk` and `Due` filter cleanly as
> `-kind:Epic`, `-risk:None`, `due:...`.

### Estimate vs Rollup — why both exist

Epics and their child tickets both appear on the board. If both carried `Estimate`, every sprint
total would count the work twice.

- **`Estimate`** lives on deliverable tickets only. This is the number sprint capacity and velocity
  are measured against.
- **`Rollup`** lives on epics and holds the sum of its children's estimates. This is what makes the
  Roadmap useful for planning.

**Reconciliation check:** total ticket `Estimate` = total epic `Rollup` = **306**. Equality proves
every ticket is attributed to exactly one epic — no double-count, no orphaned points. Re-run this
check after adding tickets.

**Risk is the field most likely to be skipped and most worth keeping.** It answers "what are we
actually doing about R1?" directly from the board, rather than by reading three documents.

### 7.2 Structure

- **Epics** live in `PenniLogic/docs` — they are cross-cutting by nature.
- **Tickets** live in their component repo (`api`, `android`, `infra`, …) — work happens where the
  code is.
- Tickets are linked to their epic as **cross-repo sub-issues**, so epic progress rolls up
  automatically.

### 7.3 Board views

Six views, fully configured. **Verified item counts** against the board data:

| View | Layout | Grouped by | Filter | Items |
|---|---|---|---|---|
| **Roadmap** | **Roadmap (timeline)** | — | `kind:Epic` | 23 |
| **Sprint Board** | Board | Status | `-kind:Epic` | 38 |
| **By Component** | Table | Component | `-kind:Epic` | 38 |
| **Risk Coverage** | Table | Risk | `-risk:None` | 51 |
| **Quality Gates** | Table | Perspective | `perspective:Test,QA,Security,Compliance` | 17 |
| **All Items** | Table | — | — | 61 |

Narrow the Sprint Board to the active sprint by adding `sprint:"Sprint 01"` to its filter.

**Roadmap** uses GitHub's dedicated timeline layout, with **Start date → `Start`** and
**Target date → `Due`**, zoomed to Year so the full Sep 2026 → Mar 2027 plan is visible in one
screen. Epic bars are staggered by sprint; `Future` epics have no bar because they are deliberately
undated.

> **Roadmap date fields cannot be set through the API.** `updateProjectV2View` accepts `layout` but
> not the date-field mapping, and roadmap views reject `visibleFieldIds` outright
> (*"Roadmap views do not support visible fields"*). The mapping was set through the UI.
> Same for grouping — `ProjectV2ViewConfigurationInput` exposes only `visibleFieldIds`.
>
> If a view ever shows an **"Unsaved changes"** marker after a UI edit, press **Ctrl+S**. The view
> options menu only offers *"Save changes to new view"*, which is not what you want.

Views are reproducible via [`setup-views.ps1`](../planning-automation/setup-views.ps1). Execution
dates and rollups come from `sync-backlog-v2.ps1`; forecast dates come from
`setup-forecast-roadmap.ps1`. The old `setup-roadmap-and-points.ps1` entry point is retired.

### 7.4 Sprint calendar

Sprint 01 begins **Monday 2026-09-07**; sprints are two weeks, Monday to Friday of week 2. Every
scheduled item carries `Start` and `Due` derived from its sprint, which is what makes the Roadmap
timeline render.

| Sprint | Start | End | | Sprint | Start | End |
|---|---|---|---|---|---|---|
| 01 | 2026-09-07 | 2026-09-18 | | 08 | 2026-12-14 | 2026-12-25 |
| 02 | 2026-09-21 | 2026-10-02 | | 09 | 2026-12-28 | 2027-01-08 |
| 03 | 2026-10-05 | 2026-10-16 | | 10 | 2027-01-11 | 2027-01-22 |
| 04 | 2026-10-19 | 2026-10-30 | | 11 | 2027-01-25 | 2027-02-05 |
| 05 | 2026-11-02 | 2026-11-13 | | 12 | 2027-02-08 | 2027-02-19 |
| 06 | 2026-11-16 | 2026-11-27 | | 13 | 2027-02-22 | 2027-03-05 |
| 07 | 2026-11-30 | 2026-12-11 | | 14 | 2027-03-08 | 2027-03-19 |
| 15 | 2027-03-22 | 2027-04-02 | | 17 | 2027-04-19 | 2027-04-30 |
| 16 | 2027-04-05 | 2027-04-16 | | 18 | 2027-05-03 | 2027-05-14 |

**`Future` items are intentionally absent from execution `Start` and `Due`.** Their separate forecast
fields provide an indicative outlook without presenting undecomposed post-beta work as a sprint commitment.

> These dates assume no holidays and no slippage. They are a planning scaffold, not a commitment —
> treat them as such until three sprints of measured velocity exist.

### 7.5 Labels

Each repo carries a consistent label set: work types (`epic`, `story`, `task`, `spike`, `bug`,
`chore`), priorities (`P0-critical`…`P3-low`), and four that trigger extra scrutiny —
**`money-path`**, **`security`**, **`compliance`**, **`needs-adr`**.

`money-path` exists so review rigour does not depend on whether the reviewer happened to notice the
code handled money.

---

## 8. Review findings (2026-09-01)

A full review of the board found and fixed the following. Recorded because several are traps that
will recur.

### Defects found and fixed

| # | Defect | Cause | Fix |
|---|---|---|---|
| 1 | **All 20 epic titles showed `â€"`** | Passing a UTF-8 em dash as a **CLI argument** to `gh.exe` on Windows corrupts it (ANSI code page) | Set titles via `gh api --input <utf8-json>` |
| 2 | **18 of 20 epic bodies corrupted; all 20 had a BOM** | Epic scripts were run under **PowerShell 5.1**, which reads UTF-8 `.ps1` files as ANSI and writes a BOM with `Set-Content -Encoding UTF8` | Strip BOM, reverse CP1252→UTF-8, PATCH via JSON |
| 3 | **Sprint Board / Roadmap / By Component were empty** | Filters used quoted **field names** (`-"Work Type":Epic`). GitHub's syntax is `field:value`; multi-word field names do not filter | Renamed fields to single words (`Kind`, `Risk`, `Due`); filters now `-kind:Epic` |
| 4 | **Sprint totals double-counted** | Epics *and* their child tickets both carried Estimates | Cleared all epic estimates |
| 5 | **3 epics missing** | Product spec §3.3, §3.4, §3.9 had no epic | Added E21, E22, E23 |
| 6 | **Field rename silently broke automation** | Ticket scripts referenced `'Work Type'`/`'Risk Link'` as hashtable keys | Updated all scripts |
| 7 | **Scripts had hardcoded paths** to a deleted directory | Absolute paths to `.planning` | Switched to `$PSScriptRoot` |

### Verified clean

- 61 project items, **every one fully populated** across all 8 required fields
- 58 cross-references between issues — **zero dangling**
- Dependency chains semantically correct (spot-checked end to end)
- Zero orphan tickets; every ticket linked to an epic
- Zero issues without labels
- All 38 ticket bodies free of encoding defects
- No epic carries an Estimate

### Encoding rules for anyone extending this

These caused four of the seven defects above:

1. **Always run the planning scripts with `pwsh`, never `powershell`.** PowerShell 5.1 misreads
   UTF-8 script files as ANSI.
2. **Never pass non-ASCII text as a command-line argument.** Route it through a UTF-8 file
   (`--body-file`, or `gh api --input`).
3. **Prefer `gh api --input <json>` over `gh issue create`** when the content contains any
   non-ASCII. It sets title, body and labels in one encoding-safe call.
4. **In PowerShell, `$obj.prop` in an unquoted argument expands as `$obj` + literal `.prop`.**
   Assign to a local scalar first. This one fails *silently* — the mutation succeeds with a wrong
   value, which is how field names briefly became `@{From=Work Type; To=Kind}.To`.

---

## 9. Traceability

Every epic links to the research that justifies it:

| Epic | Justified by |
|---|---|
| E04, E05 | `architecture/01-domain-model.md`, ADR-001, ADR-002 |
| E09 | `research/01-data-ingestion-feasibility.md`, ADR-003, ADR-004 |
| E10 | Feasibility §3 — notifications are co-primary, not supplementary |
| E13 | `architecture/02-security-architecture.md` §2, product spec §2.2 |
| E14 | `architecture/03-stack-and-monetization.md`, ADR-007 |
| E16 | Product spec §2.1 — sharing-abuse mitigations |
| E17 | `ai/01-ai-harness-research.md`, ADR-013 |
| E20 | `compliance/01-regulatory-landscape.md` |
| E21 | Product spec §3.3 — salary awareness was an explicit brief requirement |
| E22 | Product spec §3.4, §2.3; compliance §3.1 — advice boundary |
| E23 | Product spec §3.9; ADR-004, ADR-006 |

### Product spec coverage

Every feature section now maps to at least one epic:

| Spec section | Epic(s) |
|---|---|
| 3.1 Ingestion & transaction intelligence | E04, E08, E09, E10, E11 |
| 3.2 Debt management | E05, E06 |
| 3.3 Income & budgeting | **E21** |
| 3.4 Goals | **E22** |
| 3.5 Family groups | E16 |
| 3.6 Split groups | E15 |
| 3.7 AI | E17, E18 |
| 3.8 Web app & admin console | E12, E13 |
| 3.9 Trust, security & control | **E23**, E19, E20 |
