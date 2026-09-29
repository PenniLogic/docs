# PenniLogic — Planning Completeness Audit

> **Historical first completeness pass.** Superseded by
> [`07-planning-assurance-iteration-2.md`](07-planning-assurance-iteration-2.md); retained so earlier
> findings and corrections remain auditable.

> **Verdict: the plan is unusually good, and it is not yet executable as written.**
>
> **Status:** audit complete and remediated, 2026-09-02. **Scope:** the delivery system — board,
> backlog source, ticket content, decision gates — measured against one question: *can a developer or
> agent pick up a ticket and finish it without coming back to ask what was meant?*
>
> **Outcome:** 18 findings. 14 fixed in the same change, 3 corrected or withdrawn on re-examination
> (§3.1), 1 outstanding and blocked on a second reviewer rather than on planning. 22 tickets added,
> one ticket-size rule enforced in the validator, the admin console decomposed from one ticket into
> seven.
>
> **Canonical for:** the gaps between the plan as written and parallel, multi-agent execution.
> It does **not** reopen product strategy. Positioning, pricing, the lending prohibition, the advice
> boundary, the admin posture, Route D and the multi-repo structure remain confirmed — see
> [`../00-EXECUTIVE-SUMMARY.md`](../00-EXECUTIVE-SUMMARY.md) and [`../adr/README.md`](../adr/README.md).
>
> **Historical measurement note.** The 185-ticket and 1601-point figures below are the input snapshot
> this audit measured, not the current plan. Current totals and the follow-up assurance findings are
> in [`06-planning-assurance-audit.md`](06-planning-assurance-audit.md).
>
> This audit sits **after** [`04-execution-readiness-review.md`](04-execution-readiness-review.md).
> That document asked whether the delivery system was ready and answered HOLD. This one assumes the
> HOLD and asks a narrower question: when the HOLD lifts, is there enough written down to build from?

---

## 1. What the audit found

The planning record is stronger than most funded startups produce. That is the honest headline, and
the findings below should be read against it rather than as a repudiation of it.

**Measured strengths**

| Dimension | Measurement |
|---|---|
| Ticket structure | **185/185** carry Outcome, Acceptance criteria, Tests, Security and privacy, Observability, Rollout and rollback, Scope, Parallel boundary, Definition of Done, Non-goals and Dependencies |
| Ticket depth | Median body **4,077 characters**; shortest **2,293**. No stub tickets exist |
| Source integrity | `validate-backlog-v2.ps1` passes with **0 warnings**; dependency graph is a DAG with no schedule inversions |
| Sprint discipline | Every numbered sprint is at or under the 60-point ceiling; no sprint is overloaded |
| Risk coverage | 15 named risks, **every one owned** by at least one item |
| Decision gates | 10 architecture records, each stating what it must settle. `T-ADR-MONEY-01` correctly anticipates the TypeScript `bigint`-across-JSON trap and pins a Python `Decimal` wrapper |
| Test strategy | 16 quality tickets spanning property, mutation, contract, tenancy-attack, static, dynamic, supply-chain, privacy-traffic, load, chaos, penetration, accessibility and two release evidence gates |
| Governance | Contract-first PR metadata, migration registry and lock, one ticket per branch, WIP caps, expand-migrate-contract protocol |

**The finding that matters most**

Every ticket says *what must be true when it is done*. Almost none says *what to build*.

| Probe across all 185 ticket bodies | Hits |
|---|---|
| Names an HTTP endpoint path | **0** |
| Contains a request/response example | **0** |
| Names a database column or DDL | 15 |
| Names an error code or error envelope | **1** |
| States a latency budget | 5 |

The `contracts_schema` field, which looks like it should close this, is prose. On `T-CON-01` it reads
*"OpenAPI 3.1 additions with examples for at least one fixed rate and one variable rate debt"* — a
requirement about a schema, not a schema.

This is a **deliberate and defensible sequencing choice**: the interface is owned by the `contracts`
repo and shaped by the E26 decision records, so writing field names into tickets today would
pre-empt records that have not been made. The consequence is still real, and it should be stated
plainly rather than discovered in Sprint 05:

> **Until E26 and the E02 contract tickets land, no implementation ticket is self-sufficient.**
> The stated goal — "no developer should come back asking for more details" — is achieved by the
> decision records and the published contract, not by the tickets. The tickets are ready to be
> *scheduled*; they are not yet ready to be *built from*.

---

## 2. Blockers

Four findings block the parallel, multi-agent execution model the plan describes.

### B1 — Nobody is tasked with writing the bank parser templates

ADR-003 claims the deterministic parser covers "~80–85% of Indian bank SMS formats", and the parser
is the entire product wedge. The supporting work exists:

- `android#7` builds the parser **engine** and the sender allowlist
- `android#8` makes rules **remotely updatable**
- `T-QA-12` publishes a **sanitized corpus** and compatibility matrix

None of them authors a template. There is no ticket covering the top 20–30 Indian bank and wallet
sender formats, **no coverage target stated anywhere in the backlog**, and no standing process for
adding a template when a bank changes format. `R6 Parser rot` carries 13 tickets, all about the
mechanism and none about the content.

The most valuable asset in the product has no owner and no acceptance number.

**Fix.** Three tickets: author and version the initial template library; publish a coverage target
measured against the sanitized corpus and wire it into the release gate; write the template-authoring
runbook with a response SLA for a format change.

### B2 — 58 of 185 tickets sit at 13 points, the ceiling of the scale

The estimate scale is 3 / 5 / 8 / 13. There is no 21, so **13 is an open-ended bucket** and a
13-point ticket has unknown true size. Thirty-one percent of the backlog is in it.

Many are not single deliverables. `Build web transactions, bulk edit, statement import and full data
export` is four features. `Build the admin console with plan management, support tooling, aggregate
analytics and a red-team suite` is five. The governance protocol requires **one ticket per branch and
per worktree** — so a ticket that cannot be one pull request cannot honour the protocol that governs
it.

**Fix.** Split every 13-point implementation ticket into ≤8-point slices, each independently
mergeable. Add a validator rule rejecting `estimate = 13` on repo-scoped implementation tickets, so
the constraint holds for future tickets too.

### B3 — The admin console is one ticket

The brief asked for admin pages where "admin can control the full application", and the security
posture (system-powerful, data-restricted) is well designed across six `api`-side tickets. But the
console itself is a single 13-point ticket. The `admin` repository owns **three tickets and 24
points** in total, one of which is the scaffold and one the quality gate.

**Fix.** Decompose into at least six: plan and pricing CRUD; feature-flag and quota editor; provider
configuration and spend caps; support lookup, suspend and refund; aggregate analytics with cohort
minimums; audit review. Keep the red-team suite as its own gate.

### B4 — No ticket carries an interface specification

Quantified in §1. The mitigation is sequencing, not rewriting every ticket.

**Fix.** Make each E26 record emit a **machine-readable artifact**, not only prose — a JSON Schema
fragment, an enum list, an error catalogue — and make the contract tickets land the actual OpenAPI
before dependent tickets leave `Backlog`. Add this to the E26 Definition of Done, which currently
requires only that the document is "merged and dated".

---

## 3. High-severity findings

### 3.1 Corrections: three findings did not survive re-examination

Recorded first and prominently, because an audit that does not correct itself when the evidence
contradicts it is not an audit. Each of these was checked against the source a second time before the
remediation was written, and each turned out to be weaker than first stated.

| Finding | Original claim | What the evidence showed | Now |
|---|---|---|---|
| **H4** Load, chaos, DR and penetration testing unscheduled | "A control that is never scheduled is not a control" | `T-REL-03` already depends on `T-QA-05` and `T-QA-10`, and its criteria require dated load/soak/chaos results within budget, zero open high or critical penetration findings, and an evidenced production restore, alert and rollback — with **manual override impossible** | **Withdrawn.** A gate that cannot be waived is a stronger control than a date that can be missed |
| **H3** 49% of the plan has no sprint | "The board does not say so; the plan and the MVP plan wear one label" | The board README already states these are "post-MVP work that is **deliberately undated**". Every one of the 81 tickets is fully specified and dependency-gated | **Downgraded to low.** Only the executive summary lacked the framing; that sentence is now aligned |
| **H2** The entitlement record is unscheduled | "The cheapest available unblock for two entire lanes" | All seven tickets depending on `T-ADR-ENT-09` are themselves `Future`. It blocks nothing scheduled, and monetisation is phase 3 by design | **Downgraded to low.** A framing mismatch in the summary, not a scheduling error |

One further check was run to test the same instinct: an independent pass over the whole graph looking
for a numbered-sprint ticket depending on `Future` or later work found **zero schedule inversions**.
The dependency graph is clean.

The pattern in all three is worth naming, because it is the standing risk in auditing a plan this
carefully built: **an unscheduled item is not necessarily an unmanaged one.** This plan routinely
substitutes dependency gates for dates, which is the more robust mechanism, and reading `Future` as
"forgotten" mistakes a deliberate choice for an omission. The findings that survived below are the
ones where nothing — no date, no gate, no owner — was holding the work.

### H1 — Sprint 02 pushes six architecture records through one reviewer in two weeks

42 of Sprint 02's 56 points are decision records: money wire format, category model, ledger currency,
encryption scope, authentication, AI egress. The plan states in its own words that "one independent
reviewer is a separate bottleneck", then schedules the six highest-stakes decisions in the system
behind that person simultaneously.

They are also **substantively coupled**. The money wire format constrains ledger currency, which
constrains the category model. Drafting them in parallel risks incoherence, not just a queue.

**Fix.** Sequence `T-ADR-MONEY-01` and `T-ADR-LEDGER-03` first; make `T-ADR-CAT-02` depend on both.
Spread the rest across Sprints 02–04, or secure the second architecture reviewer before Sprint 02.

### H2 — The entitlement and quota record is unscheduled

> **Corrected on re-examination. Downgraded to low.** See §3.1.

The executive summary states margin "depends almost entirely on quota enforcement" and that ungated
free-tier AI is what destroys finance-AI businesses. `T-ADR-ENT-09`, the record that fixes the
entitlement and quota model, is `Future`.

**Why the finding does not stand.** Every ticket that depends on `T-ADR-ENT-09` — `T-BIL-01`,
`T-BIL-02`, `T-BIL-10`, `T-CON-03`, `T-AI-01`, `T-ADM-07`, `T-EXP-01` — is itself `Future`. The
record blocks nothing that is scheduled, and monetisation is phase 3 of the build sequence by
deliberate design: you need a product before you charge for it. The placement is consistent.

What is left is a **framing mismatch**, not a scheduling error: "revenue-critical" in the executive
summary reads as though it were a Sprint 1 concern. Revenue-critical and post-MVP are not in tension,
and the summary now says so.

### H3 — 49% of the plan has no sprint

> **Corrected on re-examination. Downgraded to low.** See §3.1.

Roughly 820 points sit in Sprints 01–14 and 792 points across 81 tickets are `Future` — all of web,
admin, AI, groups, billing, goals, income, net worth, advanced ingestion, Account Aggregator and
globalisation.

**Why the finding does not stand.** The board README already states this explicitly: those points are
"post-MVP work that is **deliberately undated**". That is not an omission, it is a defensible
position, and on reflection the better one. Scheduling fourteen further speculative sprints before a
single line of code exists, against a team whose own capacity note says one person takes three times
as long, would produce dates nobody should believe. `Future` here means "not yet dated", not "not
planned": every one of those 81 tickets carries the full eleven-section specification and is gated by
dependencies rather than by a date.

What was genuinely inconsistent is that the **executive summary** said only "the rest are `Future` or
unscheduled" without the post-MVP framing the board README carries. That one sentence is now aligned.

### H4 — Load, chaos, DR and penetration testing are unscheduled

> **Withdrawn. The finding was incorrect.** See §3.1.

`T-QA-05` (load, stress, soak, chaos and the disaster-recovery game day) and `T-QA-10` (independent
penetration test) are both `Future`, and the original finding read that as "a control that is never
scheduled is not a control".

**Why the finding was wrong.** `T-REL-03`, the public-launch evidence gate, already depends on both,
and its acceptance criteria enforce them directly:

> - *Load, soak and chaos results are present, dated against the release candidate, and within the published budgets*
> - *No high or critical penetration-test finding is open, and every closed one has a retest record*
> - *A production restore, a production alert that reached a human, and a production rollback rehearsal are all evidenced*
> - *A manual override is impossible; an exception requires a recorded, dated, expiring waiver with a named owner*

The work is bound to the launch by a gate that cannot be waived silently, which is a stronger control
than a sprint assignment. A date can be missed and the release still shipped; this gate cannot.

**No change was made.** The plan was already right here.

### H5 — No shared error model across five codebases

Two tickets mention an error shape; one mentions an error code. Three clients and two backends will
each invent their own error handling, retry semantics and user-facing copy — undermining `T-UX-01`,
which defines the client state taxonomy but has no error catalogue to bind to.

**Fix.** One contracts ticket publishing an RFC 9457 `problem+json` catalogue with stable machine-
readable codes, mapped to the `T-UX-01` state taxonomy. Client tickets consume it.

### H6 — No investment or asset tracking; net worth is structurally incomplete for India

Net worth is derived from the ledger, so it counts bank balances and debts and nothing else. An
Indian household's net worth is substantially mutual funds, EPF, PPF, NPS, gold and property. As
specified, the net-worth surface will look wrong to its target user on first open.

**Fix.** Add a manual-first `holdings` account type — asset class, units, valuation date,
user-entered — feeding net worth. No brokerage integration and no advice, so it stays outside SEBI IA
scope and adds no regulatory burden.

### H7 — No credit score tracking in a debt-first product

Every mainstream Indian finance app surfaces the bureau score, and for a debt-payoff product it is
the most natural progress metric available: paying down a card *visibly moves it*. There is zero
coverage in the spec and the backlog.

**Fix.** Evaluate a bureau partner behind a decision record. If declined on cost or diligence, record
it as an explicit non-goal with reasoning — otherwise it will be re-raised indefinitely.

### H8 — No usability testing or user research anywhere in the plan

`R2 User retention` is the one risk the executive summary says to watch above all others, and it
carries 10 tickets — every one of them instrumentation. Nothing in the plan puts the product in front
of a person before launch. The plan measures retention; it never investigates it.

**Fix.** One research ticket per phase: concept test of the debt-first wedge before E06 builds it;
moderated usability on onboarding and the SMS permission prompt before `T-QA-08`; a beta feedback
loop feeding the retention kill criterion.

---

## 4. Medium and low findings

| # | Finding | Fix |
|---|---|---|
| M1 | **No design system, no dark mode, no theming.** Two incidental design-system mentions, zero for dark mode across three client surfaces | Shared design tokens and component library ahead of the client build tickets; dark mode as an acceptance criterion in the client quality gates, beside contrast |
| M2 | **Nothing binds the Android local schema to the contract.** Room/SQLite appears in 6 tickets, all incidental; nothing requires local entities to track the published DTOs | Generate local entities from the contract, or add a CI round-trip fidelity check |
| M3 | **No competitor data migration**, despite the spec naming Splitwise's monetisation backlash as "our opening" and Monarch's portability win as the lesson | A Splitwise/Mint/Walnut CSV import ticket reusing the statement-import pipeline. Small, high-leverage acquisition work |
| M4 | **No A/B experimentation.** Retention is the top risk and the retention programme has a kill criterion, but no way to test a variant to inform it. Feature flags are release-scoped only | Server-side assignment plus exposure logging, reusing entitlement infrastructure. Explicitly kept out of the entitlement path |
| M5 | **No duress or panic mode**, despite a product spec section on intimate-partner financial abuse and a coercive-control review on family sharing. Trust controls stop at app lock, privacy mode and safe exit | Duress PIN opening a reduced or decoy view, plus a fast conceal path, added to E23 |
| L1 | **No app rating prompt, lifecycle email, or financial health score.** The transactional outbox exists; nothing drives activation, winback or store ratings | Add to the retention epic. Resist the health score unless it can be made demonstrably non-advisory |

---

## 5. What was checked and found sound

Recording the negative results matters as much as the findings, so that the next audit does not
re-litigate them.

### 5.1 The Play policy claim was independently re-verified and holds

The single most load-bearing external assumption in the product is the executive summary's claim that
Google Play explicitly permits SMS-based budgeting. It was re-checked against the primary source
during this audit, because everything downstream of it — the wedge, the ingestion architecture, the
Android-first decision — rests on it being true.

**It is true, in both the live policy and the July 2026 revision.** Both pages carry, verbatim, in
the temporary-exception table:

> **SMS-based money management** — *For example, apps that track and manage budget*
> → `READ_SMS`, `RECEIVE_MMS`, `RECEIVE_SMS`, `RECEIVE_WAP_PUSH`

Sources: the [current
policy](https://support.google.com/googleplay/android-developer/answer/10208820) and the [July 2026
preview](https://support.google.com/googleplay/android-developer/answer/17225965).

Two points worth recording:

- **The only change in the July 2026 revision is the removal of account-verification-via-call as a
  `READ_CALL_LOG` use case.** ADR-011 dropped call-log access already, so the revision costs us
  nothing. The decision anticipated the change correctly.
- **This claim is easy to read wrongly, and doing so is alarming.** The policy opens by stating that
  permitted uses are default SMS, Phone or Assistant handler — which, read alone, appears to exclude
  us. The money-management exception sits in a separate table further down the page. A secondary
  source consulted during this audit made exactly that error and reported the wedge as a critical
  policy risk. It is not. The caveats in the executive summary — temporary exception, Play review,
  demo video, prominent store listing, unresolved declaration blocks all publishing — remain the
  accurate reading.

### 5.2 Everything else checked

- **Money handling.** Integer minor units, currency exponent stored not hardcoded, floating point
  banned in CI, the `bigint`-across-JSON trap anticipated, Python `Decimal` wrapper pinned.
- **Ledger.** Double-entry with a database-enforced zero-sum invariant, append-only with reversing
  corrections, transfers modelled correctly, balances recomputed rather than cached.
- **Security.** Envelope encryption, blind index, row-level security, crypto-shredding, tamper-evident
  admin audit chain, just-in-time elevation, four-eyes bulk export, tenancy attack suite, secret
  scanning with history coverage, SDK allowlist, privacy traffic inspection on every release
  candidate, STRIDE refresh at Definition of Ready.
- **Testing.** Property-based, mutation, contract (provider and consumer), independent-model
  verification of debt mathematics, red-team scenario suites, accessibility and performance budgets
  on both clients, pseudo-localization gates, supply-chain and provenance verification.
- **Privacy posture.** Raw message content structurally excluded from the API — enforced in the
  contract rather than by policy — consent ledger, purpose registry, data-principal rights, retention
  jobs.
- **Localisation.** Framework, INR-first rendering, Indian digit grouping, plural handling, RTL
  readiness and pseudo-localization gates are all present and correctly separated from translation
  content.
- **Governance.** Contract-first PR metadata, migration registry with a lock, one ticket per branch,
  WIP caps, expand-migrate-contract, native `blockedBy` edges reconciled by the sync, bootstrap expiry
  with an automated check.

---

## 6. Competitive gaps

Researched across 11 Indian applications, 12 global personal finance tools, 5 debt-specific tools and
4 split-expense applications. Only gaps genuinely absent from the plan are listed; the many places
where the plan already matches or beats the field are not repeated here. Nothing in this section
recommends lending, ads, data sale or any capability the product has deliberately excluded.

| Gap | Who does it | Why it matters | Verdict |
|---|---|---|---|
| **Autopay and e-mandate register** with an upcoming-debit calendar and a bounce warning | Nobody completely; single-purpose products exist for this alone | Debit volumes have roughly tripled year on year and a large share of attempts fail for insufficient balance. Each failure is a penalty and a manual retry | **Added** as `T-MND-01`. Sits on the ingestion pipeline and the cash-flow forecast we already build. Moves no money, so no payment licence |
| **Indian loan mechanics** — reduce-instalment vs reduce-tenure, prepayment and foreclosure charges, floating-rate reset, tax-adjusted effective rate | Nobody; only standalone calculators on lender sites | The most-asked question by Indian borrowers, and the two prepayment choices differ materially. Pure arithmetic on the user's own figures, so it suits the deterministic engine and stays outside adviser scope | **Added** as `T-DEBT-02` |
| **Investment and retirement holdings** feeding net worth | INDmoney, ET Money, Kuvera, Groww | Confirms H6 independently | **Added** as `T-NWT-04` and `T-NWT-05` |
| **Credit score tracking** | CRED, Money View, INDmoney, Paytm, OneScore — free and near-universal in India | Confirms H7. Also closes the debt engine's loop: paying down a card visibly moves the score | **Decision record added** as `T-ADR-BUREAU-11`. Deliberately not built blind — the constraint is commercial, since bureaus generally expect lead-generation monetisation, which we have excluded |
| **Credit-card cycle intelligence** — statement date vs due date, interest-free period, revolving-balance and EMI-conversion detection | CRED is closest; no one models the interest-free period properly | The plan has minimum-payment-trap visualisation but not the cycle underneath it | **Recommended**, not yet ticketed. Natural extension of the debt engine once `T-DEBT-02` lands |
| **More payoff strategies** — credit-utilisation-first, highest-monthly-payment, highest-monthly-interest | Undebt.it ships seven; the plan has four including hybrid and custom order | Cheap: pure arithmetic over data we already hold | **Recommended**. Extend `T-CON-01` and the strategy engine rather than adding a ticket |
| **Recurring-charge detection with cancel assist and price-hike alerts** | Rocket Money, Copilot, Emma | The plan detects recurring charges but does nothing with the detection | **Recommended**. The detection exists in `api#19`; the alerting layer does not |
| **Sinking funds** alongside rollover budgets | YNAB, Monarch, Copilot, Actual | The plan has rollover budgets but no concept of saving toward a known irregular expense | **Recommended**. Small addition to the budgeting engine |
| **Tax module** — deduction tracker, capital-gains statement, filing-ready export | ET Money, INDmoney, Kuvera | Seasonal engagement and a monetisation surface | **Deferred deliberately.** Depends on holdings landing first, and the advice boundary needs testing before we go near it |

Two cautions on this research. Several competitor claims rest on secondary reviews because the
vendors' own pages are JavaScript-rendered and could not be fetched, so exact free-versus-paid tier
boundaries are unconfirmed. And the engagement statistics quoted for streaks and gamification come
from vendor marketing, so they are directional rather than audited — which is a further reason the
plan's explicit decision to exclude gamification should stand until a real experiment tests it.

---

## 7. What this audit changed

The audit did not stop at findings. The cheap, contained fixes are implemented in the same change:
**16 new remediation tickets** in `planning-automation/backlog-v2/tickets-audit-remediation.json`,
plus six new admin capability slices created by decomposing the original console ticket, for the 22
ticket increase stated above. All were schema-valid and within the sprint ceiling at that snapshot.

| Ticket | Closes | Sprint |
|---|---|---|
| `T-PRS-01` Author the initial bank and wallet parser template library | B1 | 13 |
| `T-PRS-02` Publish the parser coverage target and enforce it as a release gate | B1 | 14 |
| `T-PRS-03` Establish the template authoring runbook and format-change response | B1 | 14 |
| `T-CON-12` Publish the shared error catalogue and problem detail contract | H5 | Future |
| `T-NWT-04` Model manually entered holdings and asset classes feeding net worth | H6 | Future |
| `T-NWT-05` Build Android holdings entry and net worth composition | H6 | Future |
| `T-ADR-BUREAU-11` ADR: credit bureau score integration or explicit non-goal | H7 | Future |
| `T-RES-01` Run the debt-first concept test before the debt experience is built | H8 | Future |
| `T-RES-02` Run moderated usability on onboarding and the permission request | H8 | Future |
| `T-DSY-01` Publish shared design tokens, theming and the dark mode contract | M1 | Future |
| `T-SYN-04` Bind the Android local schema to the published contract | M2 | Future |
| `T-MIG-02` Import balances and history from competitor exports | M3 | Future |
| `T-EXP-01` Build server-side experiment assignment and exposure logging | M4 | Future |
| `T-TRU-05` Build duress unlock and rapid conceal for coercive situations | M5 | Future |
| `T-MND-01` Detect autopay mandates and warn before a debit is likely to bounce | §6 | Future |
| `T-DEBT-02` Model Indian loan mechanics: prepayment, charges and tax-adjusted rate | §6 | Future |

The parser tickets are scheduled rather than deferred, because B1 is a blocker and the SMS capability
ships in Sprint 12. They fit the remaining capacity in Sprints 13 and 14 exactly, which is why those
sprints now read 60 and 58 rather than 52 and 50.

### 7.1 The admin console is decomposed (B3)

`T-ADM-04` was one 13-point ticket covering the shell, plan management, provider configuration, spend
caps, support tooling, aggregate analytics and a red-team suite. It is now narrowed to the **console
shell** — operator session, role-gated navigation, the shared redaction and confirmation primitives,
and the structural absence of any per-user financial listing route — with six capability tickets
mounting into it:

| Ticket | Owns |
|---|---|
| `T-ADM-04` (5) | Shell, operator session, default-deny navigation, redaction and confirmation primitives |
| `T-ADM-07` (5) | Plan, feature and quota management with change recording |
| `T-ADM-08` (5) | AI provider configuration and spend caps that halt traffic |
| `T-ADM-09` (5) | Support lookup, status, suspension and refund |
| `T-ADM-10` (5) | Aggregate analytics with enforced cohort minimums |
| `T-ADM-11` (5) | Audit review and access monitoring |
| `T-ADM-12` (5) | Operator red-team suite as a blocking release gate |

Two things are worth noting. The total is **35 points, not 13** — that is the finding rather than
scope creep, since 13 was the ceiling bucket concealing the real size, and the 1601-point total was
always described as a lower bound. And the **red-team suite is now its own ticket**: previously the
proof that the console could not be abused shipped in the same change as the console, which is not a
proof. It now depends on all six surfaces and gates their release.

### 7.2 The 13-point problem is now enforced rather than described (B2)

Bulk-splitting 58 tickets was rejected as the wrong fix. Two reasons: some are genuinely indivisible
— the ledger schema and the amortisation engine are each one coherent deliverable — and splitting
work twelve sprints out, before the decision records that shape it have landed, is speculative.

Instead the rule is now machine-enforced. `manifest.ticket_size` records a split threshold of 13 and
an `unsplit_allowlist`, and `validate-backlog-v2.ps1` fails when:

- a threshold ticket in a numbered sprint has no allowlist entry;
- an entry's `split_by` date has passed;
- an entry plans to split *after* its own sprint has already started;
- an entry names a sprint the ticket is no longer in.

A stale entry raises a warning, so the list shrinks rather than accumulating. **A threshold ticket in
`Future` is permitted** — scheduling it into a numbered sprint is the moment the split falls due.
This is the same pattern as the `T-GOV-03` bootstrap expiry: a temporary state is allowed, but only
with a date and a check that fails when the date passes.

Twelve v2 tickets are currently in the allowlist, each naming what it bundles. Every validator run
prints the outstanding count and the next due date, so the debt is visible rather than implicit. All
four failure modes were verified by deliberate violation before the rule was committed.

### 7.3 The architecture records are sequenced (H1, partial)

`T-ADR-CAT-02` now depends on `T-ADR-MONEY-01` and `T-ADR-LEDGER-03`, completing the chain
money → ledger → category. The coupling is real: a category is a reporting dimension over ledger
entries, so its append-only decision depends on how those entries and their currency are fixed.
Drafting the three in parallel risked three internally consistent records that disagree with each
other.

This addresses the *coherence* half of H1 at zero capacity cost, since dependency edges express
ordering within a sprint. The *review bottleneck* half — six records through one reviewer in two
weeks — is untouched, because it is a staffing decision rather than an editorial one.

**What is still outstanding.** Scheduling `T-ADR-ENT-09` (H2), load and penetration testing (H4), and
spreading the Sprint 02 records across Sprints 02–04 (H1) all require displacing work from sprints
already at the ceiling, or extending the numbered schedule beyond Sprint 14 — which also means adding
options to the live project's `Sprint` field. Both are capacity decisions. The relabelling of the MVP
boundary (H3) depends on which of those is chosen.

---

## 8. Recommended sequence

Ordered by what unblocks the most work per unit of effort.

| Order | Action | Unblocks |
|---|---|---|
| 1 | Re-sequence the E26 records (H1) — **ordering done via dependency edges; the review load needs a second reviewer, not a calendar change** | Coherence of the six records; the queue itself is `T-GOV-03` |
| 2 | ~~Add the machine-readable-artifact requirement to the E26 Definition of Done (B4)~~ **Done: all 11 records** | Turns decision records into inputs a developer can build from |
| 3 | ~~Create the parser template library, coverage target and authoring runbook (B1)~~ **Done: 3 tickets, Sprints 13-14** | The product wedge; was unowned |
| 4 | ~~Split the 58 thirteen-point tickets; add the validator rule (B2)~~ **Rule added; splits now fall due per sprint** | Parallel execution; one ticket becomes one PR |
| 5 | ~~Decompose the admin console (B3)~~ **Done: 7 tickets** | The admin lane, which was one ticket wide |
| 6 | ~~Publish the error catalogue (H5)~~ **Done: `T-CON-12`** | All five codebases; binds `T-UX-01` to something real |
| 7 | ~~Schedule load, chaos, DR and penetration testing (H4)~~ **Withdrawn: already enforced by the T-REL-03 gate** | - |
| 8 | ~~Relabel the MVP boundary (H3)~~ **Done: executive summary aligned with the board README** | Removes the last inconsistency in how `Future` is described |
| 9 | ~~Add holdings, credit score decision, user research (H6, H7, H8)~~ **Done: 5 tickets + 1 decision record** | Product completeness for the launch market |
| 10 | ~~Design system, local-schema binding, competitor import, experiments, duress mode (M1-M5)~~ **Done: 5 tickets** | Quality and growth surface |

Items 1, 2 and 4 are cheap, are pure planning work, and can be done **now** — they need neither the
second reviewer nor the physical device, and every one of them makes the rest of the plan cheaper to
execute.

---

## 9. Answering the question directly

| Question asked | Answer |
|---|---|
| Is the planning done properly? | **Yes, and it is better than the norm.** Structure, risk ownership, security depth and test strategy are all strong. Three of the eight high findings did not survive re-examination (§3.1), which is itself evidence of how carefully it was built |
| Are there architectural gaps? | **Two, both now closed.** No shared error model (H5 → `T-CON-12`); no binding between the Android local schema and the contract (M2 → `T-SYN-04`). The decision-gate coverage itself was sound, and the records now have to emit machine-readable artifacts rather than prose |
| Are there feature gaps? | **Yes, and the largest was content rather than capability.** The bank parser templates — the product wedge — had no owning ticket at all (B1). Also investments and net worth (H6), credit score (H7), competitor import (M3), plus two India differentiators nobody currently serves: autopay mandate management and Indian loan mechanics (§6). All are now ticketed or recorded as decisions |
| Are there UX gaps? | **Three, now closed.** No user research (H8 → two tickets), no design system or dark mode (M1 → `T-DSY-01`), no duress mode (M5 → `T-TRU-05`). `T-UX-01` was already excellent and is the model the new work follows |
| Do tickets have everything a developer needs? | **Not yet, and by design** — but the path is now enforced rather than assumed. Tickets carry outcomes, constraints and verification; interfaces arrive with E26 and E02, and every decision record must now publish a machine-readable artifact its dependants consume (B4) |
| Are the schemas mutually compatible? | **Unknowable today**, because they are not written. The mechanism to keep them compatible — one contracts repo, generated clients, provider and consumer contract tests, expand-migrate-contract, and now a local-schema binding check on Android — is correctly designed |
| Can we develop in parallel, multiple branches and PRs? | **Now yes, with a rule that holds the line.** 58 tickets sat at the estimate ceiling, contradicting the one-ticket-one-branch protocol. Splitting is now due the moment a threshold ticket enters a numbered sprint, enforced by the validator and visible in every run (B2). The admin lane, which was one ticket wide, is now seven (B3) |
| Is security adequately covered? | **Yes — the strongest part of the plan.** The only genuine gap was duress mode (M5), now added. The penetration test was never a gap: `T-REL-03` cannot pass with an open high or critical finding, and manual override is impossible |
| Is testing adequate? | **Yes.** Coverage spans unit, property, mutation, contract, integration, E2E, accessibility, performance, load, soak, chaos, supply-chain and penetration, plus a parser coverage gate that did not exist before (B1). The scheduling concern was withdrawn: the launch gate binds the work more tightly than a sprint date would (§3.1) |
| What is actually left? | **One thing: a second reviewer.** Six coupled architecture records queue behind one person in Sprint 02. Their ordering is now enforced so they cannot contradict each other, but no planning source can manufacture review capacity. That is `T-GOV-03`, already the named external blocker |

---

## 10. What this audit did not cover

Stated so the boundary is explicit and the next reviewer does not assume it was checked.

- **Vendor and pricing revalidation.** Provider rates, store fees and bureau costs were not re-priced.
- **Legal review.** The compliance record was read for coverage, not verified by counsel.
- **Estimate accuracy.** Sizes were audited for *distribution shape*, not for whether 8 points is the
  right number for any particular ticket. No measured velocity exists yet.
- **The 61 pre-v2 items' issue bodies as rendered on GitHub.** The patch source was audited; the
  rendered result was spot-checked, not read in full.
