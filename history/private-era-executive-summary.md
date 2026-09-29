# PenniLogic — Executive Summary

> **Research phase complete.** 2026-09-01.
> This is the decision brief. It states what we verified, what changed as a result, and what needs
> your sign-off before implementation starts. Everything here is backed by primary sources in the
> detailed documents.
>
> **Execution status: DESIGN-FIRST CONTROLLED START.** The product decisions below are confirmed and
> are not reopened. Dependency-free governance, scaffolding, research operations and design
> foundations may start; every mapped Android, web and admin frontend remains blocked until its D6
> artifact and the `T-DQA-12` CDO readiness gate are accepted. `T-GOV-03` and `infra#4` are
> **In Progress** to install agent-review governance. Their dependent scaffolds and automation remain
> `Backlog`; only physical-device procurement (`T-QA-07`) is independently `Ready`.
> **E31 is `In Progress`; no epic is currently `Ready`.** The plan prerequisite is complete:
> PenniLogic was upgraded
> to GitHub Team on 2026-09-02, required checks and reviews were proven on a temporary private
> fixture, the fixture was removed, and `T-EXT-01` is `Done`. See
> [`product/09-design-first-planning-assurance.md`](product/09-design-first-planning-assurance.md).
>
> **On the numbers.** Current epic, ticket and point totals are derived from the durable backlog and
> printed by `planning-automation/validate-backlog-v2.ps1`; they are not hardcoded here. The work in
> Sprints 01-16 are **the active private-beta tranche**; Sprints 17-18 are explicit contingency and
> the rest is `Future` — post-beta work that is
> **deliberately undated**, because scheduling it before any velocity has been measured would be
> planning theatre. `Future` therefore means "not yet dated", never "not planned": every such ticket
> is fully specified and gated by dependencies, and the launch evidence gate cannot pass without the
> ones that matter. Sprints use independent Engineering (3 x 20-point), Product Design and UX
> (6 x 20-point), and Quality Assurance (4 x 20-point) pools with separate review ceilings.
> Capacity is a staffing assumption until measured velocity replaces it.

---

## 1. Is this buildable? Yes — with three requirements removed or reshaped.

The brief described a product that is largely achievable, but three parts of it cannot be built as
literally written. None of these are fatal; each has a better version.

| Brief said | Reality | What we do instead |
|---|---|---|
| "Access my Calls" | Google Play grants `CALL_LOG` only to default dialers, caller-ID apps, and a bank's own app. **No exception exists for finance apps**, and account-verification-by-call is being removed 2027-01-27. | **Drop it.** Call logs record who you called, not what you spent. Requesting it would also endanger the SMS approval in the same review. |
| "Access other UPI apps" | **No public API exists.** No third-party app can read Google Pay / PhonePe / Paytm history. | Capture UPI spending **indirectly** via bank SMS and payment-app notifications — which achieves the actual goal. |
| "Family can access others' data" | Literal implementation is an intimate-partner-abuse vector. | **Granular, per-member, revocable consent** with access logging and discreet exit. Preserves the real use case. |

**And one requirement to reshape rather than remove:**

"Admin can control the full application" → an admin console that is **powerful over the system, restricted over user financial data**. Full control of plans, pricing, features, AI quotas, and support; no casual browsing of anyone's salary or transactions. Access to individual financial records is just-in-time, ticket-justified, time-boxed, two-person-approved, and written to an immutable audit log. This keeps every capability you actually need while ensuring a phished admin account is a contained incident rather than a company-ending breach.

---

## 2. The finding that de-risks the product

**Google Play explicitly permits our core feature.** The policy lists, verbatim:

> **"SMS-based money management"** — *"For example, apps that track and manage budget"*
> → grants `READ_SMS`, `RECEIVE_SMS`, `RECEIVE_MMS`, `RECEIVE_WAP_PUSH`

I verified this in the current policy **and** in the July 2026 revision (effective 2027-01-27), where it appears **unchanged**. This is not on a deprecation path. Competitive research confirms SMS parsing is the *dominant* approach in India — Walnut, MoneyView and ET Money all used it. We are not doing anything unusual.

**Caveats that shape the plan:** it is a *temporary* exception requiring Play review, a demo video, and a store listing that prominently features the capability. An unresolved declaration **blocks all publishing** — including pricing and store listing changes — so it must be filed during beta, not launch week.

---

## 3. The finding that adds risk

**Account Aggregator is not the safety net I assumed.** Per RBI's Master Direction, an FIU must be regulated by RBI, SEBI, IRDAI or PFRDA. **A non-regulated startup cannot access AA data**, and a Technology Service Provider *cannot* confer that status.

So "if Google withdraws SMS access, we move to Account Aggregator" **is not an available fallback** — it needs a regulated partner or our own registration, which is months-to-years of lead time.

**Consequences, already reflected in the plan:**
- Manual entry and statement import must be genuinely excellent, not token fallbacks. This is the only mitigation entirely within our control.
- The **notification listener ships alongside SMS**, not after it. It is governed by different policy, so one decision cannot remove both channels.
- Regulated-partner or SEBI-IA conversations start early, as long-lead-time work.

**A strategic option worth weighing:** SEBI Investment Adviser registration would make us AA-eligible *and* legitimise richer advice features. One registration unlocks both.

---

## 4. Positioning: lead with debt

Retention — not technology — is what kills personal finance apps. Mint had 22M+ users and still shut down.

A debt payoff countdown is a **destination**; a spending pie chart is a **chore**. Debt payoff produces provable, deterministic value ("14 months sooner, ₹1.87 lakh saved") that justifies a subscription, works offline, and costs nothing per user to compute.

The reviewed competitor set did not identify an India-native product combining deterministic debt payoff with the planned ingestion and privacy model. Tally (US) shut down, Bright Money is US-only, and Undebt.it demonstrates interest in a manual web debt tool; its public user count does not establish how many users pay.

**Build the deterministic debt engine before the AI harness.** The AI is a multiplier on a product that must already be valuable; built first, it produces an expensive chatbot with nothing true to say.

---

## 5. Business model: the margin trap and the way out

Initial modelling suggested AI would destroy margins — 15–17% at ₹249/month. **That diagnosis was wrong, and the error is the most useful lesson in the research.** It assumed AI costs applied to free users too.

> **The fix is quota enforcement, not price.** With a hard 5 Q&A/month free cap and a 150 Q&A Pro cap, **₹299/month yields ~85% gross margin.** Ungated free-tier AI is what kills finance-AI businesses.

This makes **server-side quota enforcement revenue-critical infrastructure**, which is why entitlements are owned in-house rather than delegated to a feature-flag vendor.

| Tier | India | US | AI quota | Margin |
|---|---|---|---|---|
| Free | ₹0 | $0 | 5 Q&A/mo | acquisition |
| **Pro** | **₹299** (₹199 annual) | **$6.99** ($4.99 annual) | 150 Q&A | **~85%** |
| Pro+ | ₹499 | $12.99 | 500 Q&A | ~85% |
| **BYOK Pro** | **₹149** | **$3.99** | unlimited (their key) | **~95%** |

**BYOK is both our differentiator and our best margin.** Research confirmed **zero** consumer finance apps offer bring-your-own-key or custom base URL — verified across YNAB, Monarch, Copilot, Cleo, Rocket Money, Fi, Jupiter, CRED and INDmoney. It eliminates our largest variable cost, appeals to privacy-conscious and technical users, and earns ~95% margin. Rare alignment; market it loudly.

---

## 6. Hard business-model commitments

Four independent post-mortems converge on the same lesson:

| Company | Outcome |
|---|---|
| Walnut | Beloved tracker → acquired by a lender → deprioritised → dead |
| Tally | Debt app that offered credit → shut down on credit economics |
| MoneyView | Lending + PFM → recovery harassment → Trustpilot ~1.8/5 |
| CRED | Lending monetisation → support rating ~1.9/5 |

> **We do not lend, broker loans, or take credit referral fees.** Lending economics and PFM trust are structurally incompatible. This also keeps us clear of RBI Digital Lending Guidelines — confirmed as not applicable to a pure advisory app.

Also committed: **no ads, no data sale** (Mint's ad model failed at 22M users; Play policy independently bans selling SMS-derived data); **never retroactively degrade the free tier** (Splitwise's backlash is our opening); **full data export from day one** (Monarch won Mint's users on portability).

---

## 7. Regulatory position

Good news on the core wedge: **debt payoff strategy sits entirely outside SEBI Investment Adviser scope.** Our most valuable feature carries the least regulatory risk.

The line we stay behind: projections, gap analysis and market information are educational. Naming specific securities or recommending portfolio actions triggers registration. The AI must therefore be a **calculator and a mirror, never an adviser** — with all money math deterministic and every output carrying the standard disclaimer.

Compliance work required before launch is documented in `compliance/01-regulatory-landscape.md`: DPDP obligations, CERT-In 6-hour breach reporting and 180-day log retention, and consent design. On-device SMS parsing materially reduces this exposure.

---

## 8. Recommended architecture

| Layer | Decision |
|---|---|
| Mobile | Native Android, Kotlin + Compose (deep OS integration rules out cross-platform) |
| Core API | Kotlin/Ktor — shares models with the client, strong typing for money |
| AI service | Python/FastAPI + LiteLLM proxy — separate service, independently scalable/replaceable |
| Data | Postgres; **integer minor units**, never floats; double-entry, append-only ledger |
| Authorization | ReBAC (OpenFGA) — sharing is a relationship problem, not a roles problem |
| Erasure | Crypto-shredding — resolves append-only ledger vs. right-to-erasure |
| Offline | Local SQLite + mutation queue for MVP; PowerSync evaluated for v1.1 |
| Ingestion | Deterministic parser primary (all devices), on-device LLM for the long tail |

**One override worth flagging:** the AI research recommended an on-device LLM as the *primary* SMS parser. That model needs ~8GB RAM flagship hardware. **India is predominantly mid-range devices**, so that design would have failed most of our target market. Inverted: deterministic parser primary, LLM for the long tail. (ADR-003.)

> **Nine decisions inside this architecture are still open, and they block implementation.** Money
> wire format/time/idempotency, the category model, ledger currency/FX/debt-balance derivation,
> encryption scope/searchable fields/RLS and the grant-mediated cross-user read predicate, auth +
> passkey relying-party identifier + recovery, the administrative boundary and its three audit
> streams, shared-data erasure and cross-user key access, AI egress/Mode C, and the entitlement and
> quota model — the last of which resolves two research documents that describe entitlements
> differently. These specify what the accepted ADRs deliberately left unspecified. They are
> **implementation blockers, not reopened product strategy** - nothing in sections 1 to 7 changes
> because of them. Each is a ticket in epic E26 and lands as ADR-015 to ADR-023 in its own file; see
> [`product/04-execution-readiness-review.md`](product/04-execution-readiness-review.md) section 4.

---

## 9. Build sequence

| Phase | Contents | Why here |
|---|---|---|
| 0 | Ledger, auth, accounts, manual entry | Correctness before cleverness |
| 1 | **Debt engine, payoff projection, simulator** | The reason to install |
| 2 | SMS + notification capture, dedupe, clarification inbox | The reason to stay |
| 3 | Web app, admin console, subscriptions | Monetisation |
| 4 | Split groups, family groups | Virality + retention |
| 5 | Full AI harness, BYOK | Differentiation |
| 6 | Account Aggregator, multi-currency | Durability |

---

## 10. Decisions — confirmed 2026-09-01

All blocking **product** decisions are **approved** and remain settled. What follows is the record of
that sign-off; none of it is reopened below.

> **Product decisions are unblocked. Execution is not.** The execution-readiness audit found the
> delivery system unready: dependencies the board could not enforce, empty repositories, review gates
> with no reviewer, and nine architecture questions still open. The verdict is **HOLD for feature
> implementation** — 11 items are `Ready` and no epic is: governance, scaffolding, physical-device
> procurement, and the two dependency-free `infra` tickets. See
> [`product/04-execution-readiness-review.md`](product/04-execution-readiness-review.md).

| Decision | Outcome |
|---|---|
| Call-log access | ✅ **Dropped** — not permitted by Play policy |
| Positioning | ✅ **Debt-first** confirmed |
| Family sharing | ✅ **Granular, per-member, revocable** consent |
| Admin console | ✅ **System-powerful, data-restricted** |
| Advice boundary | ✅ **Calculator, not adviser** |
| Lending | ✅ **Never** — no loans, no brokering, no credit referral fees |
| Pricing | ✅ ₹299 Pro / ₹149 BYOK (US $6.99 / $3.99) |
| **Account Aggregator** | ✅ **Route D — defer AA entirely for MVP.** On-device parsing only; no FIU partner, no TSP, no registration. See ADR-013 |
| Repository structure | ✅ **Multi-repo** under the `PenniLogic` org. See ADR-014 |

### Still open (non-blocking for product; some are blocking for execution)

- [x] **Upgrade the GitHub organisation plan.** Completed 2026-09-02. PenniLogic is on GitHub Team;
      a temporary private-repository pull request was blocked by one required review and a pending
      required check under an active ruleset. The pull request, ruleset, protection rule and
      branches were removed, all product repositories remained private, and `T-EXT-01` is `Done`.
- [ ] **Source a physical Android device with an Indian SIM** — real bank SMS formats cannot be
      emulated, and the parser is the core of the product. Highest-value outstanding item, and an
      execution blocker for parser validation. Procurement is now dependency-free and `Ready`
      (`T-QA-07`); the sanitized corpus and compatibility matrix follow in `T-QA-12`.
- [ ] **Activate independent reviewer-agent gates.** One GitHub user operates the project, so
      `T-GOV-03` uses separate qualified agent profiles and sessions with current-head attestations
      rather than pretending a second account exists. Money/security paths remain blocked until
      their specialist-agent evidence is configured.
- [ ] **Engage counsel for the jurisdiction profiles.** Every statutory value in the plan — reporting
      windows, rights-request response clocks, retention periods, GST thresholds — is read from a
      versioned counsel-reviewed profile and **fails closed** when none exists. Nothing in this
      research is a legal conclusion (`T-CMP-04`).
- [ ] Evaluate **SEBI IA registration** later — it would unlock AA access *and* richer advice
      features in one step. Revisit near product-market fit.
- [ ] Install Android Studio; approve remaining dev connectors when credentials exist.

The remaining external blockers and assumptions — agent-review enforcement, device, counsel and DPAs, store
permission review, and vendor/pricing revalidation — are in
[`product/04-execution-readiness-review.md`](product/04-execution-readiness-review.md) §9.

---

## 11. The one thing to watch

If only one risk gets sustained attention, make it **user retention** (`R2 User retention` on the
board). The Play permission, security, and admin risks are all solvable with engineering discipline
and are largely addressed by decisions already recorded here. Retention is what quietly kills finance
apps that do everything else right — and it is decided by positioning long before it shows up in a
metric.

**Validate the debt-first wedge with real users before building the expensive phases.** `T-RET-01`
owns the programme that tests it, and it carries an explicit kill and reconsider threshold so the
answer can be "stop" rather than "tune it again".
