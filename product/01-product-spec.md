# PenniLogic — Product Specification

> **Status:** Draft for review, 2026-09-01. Research phase.
> This document turns the initial brief into a coherent product, and — importantly — surfaces the
> places where the brief contains **genuine contradictions that must be resolved by a human
> decision**, not papered over in code.

---

## 1. Positioning

**PenniLogic is a debt-first personal finance operating system.**

That framing is deliberate. The brief lists debt management first, and it is the right wedge:

- Budgeting apps are a crowded, largely commoditised market with a well-known retention problem —
  people stop logging expenses.
- **Debt is different.** It has a fixed, knowable end state ("₹0 owed"), it generates genuine
  anxiety, and progress toward payoff is intrinsically motivating in a way that "you spent ₹4,200 on
  food this month" is not. A debt payoff date is a *destination*; a budget is a *chore*.
- Debt payoff has **provable, deterministic value**. "Reorder these five debts and you become debt
  free 14 months sooner and save ₹1.87 lakh in interest" is a calculable, verifiable claim. It
  justifies a subscription in a way that a spending pie chart does not.

Everything else in the brief — expense tracking, goals, family, splitting, AI — is in service of
that spine. Expense tracking exists to find money to throw at debt. Goals extend the same engine
past the payoff date. Family groups exist because household debt is a household problem.

**One-line positioning:** *Know exactly when you'll be debt free — and what to change to get there
sooner.*

---

## 2. The three contradictions in the brief

These need explicit decisions before build. Each is recorded as an open ADR.

### 2.1 "Family can access others' data" vs. "Security is one of the main keys"

The brief asks for family groups where "partners/family can access others' data as well." Taken
literally, this is the highest-risk feature in the product. Shared financial visibility is a known
vector for **financial abuse in intimate-partner relationships**, and it is not a hypothetical
edge case — it is common.

A naive implementation ("join group → see everything, forever") is dangerous and would be
indefensible after an incident.

**Recommended resolution — consent-based, granular, revocable, and symmetric:**

- Sharing is **opt-in per data category** (net worth / debts / income / transactions / goals), not
  all-or-nothing.
- Sharing is **per-member**, not per-group — you choose what each person sees.
- **Unilateral revocation, always.** Any member can revoke at any time, instantly, without needing
  the other party's approval and **without notifying them of the reason**.
- **No silent surveillance.** If someone views your detailed transactions, that is visible to you in
  an access log. Asymmetric invisible monitoring is the abuse pattern; make it impossible.
- **A discreet exit.** Leaving a family group must be quick, must not send a dramatic notification,
  and must immediately cut historical access — the other party keeps no cached copy of your data.
- Default to **aggregates, not line items**. Most legitimate family use cases ("are we on track for
  the house deposit?") are satisfied by totals. Transaction-level sharing should be a deliberate,
  separate grant.

> This is not over-engineering. It is the difference between a feature that helps couples and one
> that gets the product written about for the wrong reasons.

### 2.2 "Admin can control the full application" vs. financial privacy

The brief asks for admin pages where "admin can control the full application." Read literally, that
means staff can read every user's salary, debts, and spending. That is an enormous insider-risk and
breach blast-radius, and in several jurisdictions it is a compliance problem on its own.

**Recommended resolution — a powerful admin console that is powerful over the _system_, not over
_user financial data_:**

| Admin CAN (unrestricted) | Admin CANNOT (by default) |
|---|---|
| Manage plans, pricing, feature flags, AI quotas | Read a user's transaction descriptions or balances |
| Configure AI providers, models, routing, spend caps | Read raw SMS/email content (never leaves device) |
| View aggregate/anonymised analytics | Browse individual financial records casually |
| Manage support tickets, suspend/refund accounts | Export bulk user financial data |
| View audit logs, system health, job queues | Act without leaving an immutable audit trail |

For genuine support cases, use **just-in-time, scoped, justified, time-boxed access**: the admin
states a reason, it is tied to a support ticket, the user is notified, access auto-expires, and the
whole thing is written to an append-only audit log. High-sensitivity actions require **two-person
approval**.

This gives the operator everything they actually need while making a compromised admin account a
containable incident rather than a company-ending one.

### 2.3 "Suggest to find a job which has X salary" vs. financial-advice regulation

The brief's goal engine is asked to make recommendations. There is a real regulatory line between
**financial education//calculation** and **regulated financial advice** (SEBI in India; equivalents
elsewhere). Telling someone to buy a specific investment product is regulated. Telling them the
arithmetic of their own situation generally is not.

**Recommended resolution — be a calculator and a mirror, not an adviser:**

- ✅ *"At your current savings rate of ₹18,000/month, this goal completes in Feb 2031 — 3 years later
  than your target. Closing the gap requires ₹31,000/month."* (arithmetic on the user's own data)
- ✅ *"Roles in your field at the next level typically pay 25–40% more."* (labelled market
  information, sourced)
- ❌ *"You should invest in X fund."* (regulated advice)
- ❌ Projected investment returns presented as expectations rather than clearly-labelled scenarios.

Frame outputs as **scenarios and trade-offs the user selects between**, never as instructions. This
is also better product design: it preserves user agency instead of issuing orders.

**✅ Verified against SEBI (Investment Advisers) Regulations 2013 (amended July 2023):**

| Feature | Triggers SEBI IA registration? |
|---|---|
| "At your savings rate, this goal completes Feb 2031" | **No** — mathematical projection |
| "Closing the gap needs ₹31,000/month" | **No** — factual gap analysis |
| "Roles at the next level typically pay 25–40% more" | **No** — general market information |
| **Debt payoff ordering (avalanche/snowball)** | **No** — debt management is outside SEBI IA scope entirely |
| "Consider an index fund" | **Borderline** — generic category; needs strong disclaimer |
| "Invest in XYZ Mutual Fund" / "sell Fund A, buy Fund B" | **Yes** — specific product/portfolio advice |

**Our entire core wedge — debt payoff strategy — sits outside SEBI IA scope.** That is a
significant and fortunate finding: the most valuable feature carries the least regulatory risk.

Required practice: frame output as informational/illustrative/educational; never name specific
securities; display *"This is not investment advice. Please consult a SEBI-registered investment
adviser."*

> **Strategic note:** SEBI IA registration would *also* make us eligible for Account Aggregator FIU
> status (see the feasibility doc §5.2). If we ever want richer advice features **or** direct AA
> access, one registration unlocks both. Worth evaluating deliberately rather than by default.

---

## 3. Feature specification

### 3.1 Ingestion & transaction intelligence

| Feature | Priority | Notes |
|---|---|---|
| Manual entry (fast, ≤3 taps) | **P0** | The app must work for a user who denies every permission |
| On-device SMS parsing | **P0** | The wedge; requires Play declaration (see feasibility doc) |
| Notification-listener capture | **P1** | Catches UPI/wallet spend SMS misses |
| Transaction dedupe across channels | **P0** | Same payment seen via SMS *and* notification must merge |
| Confidence scoring | **P0** | Drives the "ask the user" flow |
| **"What was this?" clarification inbox** | **P0** | Explicitly requested in the brief; batched, never nagging |
| Auto-categorisation + learned merchant rules | **P0** | Must learn from corrections and never re-ask |
| Recurring/subscription management | **P1** | Confirmed series, renewal forecast, price-change alerts and safe cancel assist; never claims to cancel automatically |
| Receipt OCR / photo capture | **P2** | |
| CSV / bank statement import | **P1** | Essential for onboarding history + non-SMS markets |
| Account Aggregator (India) | **P2** | Strategic; see feasibility + compliance docs |
| Email receipt parsing | **P3** | Gated on Gmail CASA cost/benefit |
| Multi-currency | **P2** | Needed for global expansion |
| Cash transaction handling | **P1** | ATM withdrawal → "where did this cash go?" is an under-served gap |
| Consumer refund lifecycle | **P1** | Linked reversing transactions, including pending and partial refunds; never misclassified as income |

### 3.2 Debt management — the differentiator

| Feature | Priority | Notes |
|---|---|---|
| Debt inventory (balance, APR, min payment, term, fees) | **P0** | |
| **Payoff date projection** | **P0** | The headline number the product is built around |
| Avalanche / snowball / hybrid strategy comparison | **P0** | Show interest saved *and* time saved for each |
| "What if I pay ₹X more?" simulator | **P0** | Instant, deterministic, no LLM |
| Refinance / consolidation modelling | **P1** | Model it; do **not** recommend specific lenders (see §2.3) |
| Extra-payment allocation guidance | **P0** | |
| Amortisation schedule + interest-paid-to-date | **P1** | |
| Debt-free countdown + milestone celebration | **P1** | Retention driver |
| Credit-card minimum-payment trap visualisation | **P1** | Emotionally powerful, genuinely educational |
| Credit-card billing-cycle intelligence | **P1** | Statement/due dates, grace period, revolving balance and EMI conversion |
| Advanced payoff strategies | **P2** | Utilization-first, highest-payment and highest-interest-cost, all deterministic |
| Loan/EMI reminders | **P1** | Missed-payment prevention has direct monetary value |

### 3.3 Income & budgeting

Salary awareness (explicitly requested), variable/irregular income support (critical for
freelancers and a common competitor gap), additional/side income, expected-vs-received payroll
detection, category budgets with rollover, safe-to-spend, cash-flow forecasting, and
bill/subscription calendar. Sinking funds reserve contributions for known irregular expenses
without creating a ledger transaction. Personal net worth and its trend are derived from the ledger per
currency; currencies are never silently collapsed into one total before the multi-currency engine
exists.

### 3.4 Goals

Multi-goal support with priority ordering and **competition modelling** — the honest, differentiating
feature is showing that funding the car goal *delays* the house goal, and by exactly how long.
Includes required-savings-rate calculation, income-gap analysis ("this goal needs ₹X more per
month"), scenario comparison, and shared household goals. An optional salary-market view may show
sourced ranges by role and location with geography, methodology and as-of date; it never recommends
an employer, guarantees an outcome or asks a model to invent a benchmark.

### 3.5 Family groups

Per-category, per-member, revocable sharing (see §2.1). Combined household net worth, income, and
spending; shared goals with per-member contribution tracking; household debt view.

### 3.6 Split groups (Splitwise-equivalent)

Groups and one-off splits; equal/exact/percentage/share/adjustment splits; itemised bill splitting;
multi-currency; **debt simplification** (minimise the number of transfers to settle a group);
settlement recording; UPI deep-link to actually pay; balance history; export.

> **Strategic note:** Splitwise's 2024+ monetisation changes (limits on the free tier, ads)
> generated significant user frustration. A *genuinely* generous free split tier is a cheap,
> high-leverage acquisition channel for us: splitting is inherently viral — every group invites
> non-users — and it feeds transaction data into the core product. **Recommendation: never
> paywall core splitting.** Let it be the top of the funnel.

### 3.7 AI

Covered in depth in the AI architecture doc. Product-level requirements: conversational Q&A over the
user's own data; the clarification flow; categorisation; proactive insights and anomaly detection;
natural-language entry; goal/debt narrative explanation; weekly/monthly review generation.
Natural-language entry produces a structured draft that the user reviews and confirms through the
ordinary transaction API; a model never writes a transaction or initiates a payment.
Conversation history is off by default. If a user opts in, the core API owns encrypted,
retention-bounded history with export and deletion; the AI service remains stateless and the content
is never used for training.

Three access modes, per the brief: **managed subscription** (we pay, we meter), **BYOK**, and
**custom provider with custom base URL** (self-hosted/OpenAI-compatible).

> **Differentiator check:** BYOK and custom base URL are, as far as the competitive research shows,
> essentially unheard of in consumer finance apps. This is a real wedge with privacy-conscious and
> technical users — and it structurally lowers our COGS. It should be marketed loudly, not buried
> in settings.

**Hard rule: all money math is deterministic.** The LLM explains, narrates, and routes — it never
computes a payoff date, an interest total, or a balance. Numbers come from the engine and are passed
*to* the model. This is non-negotiable for correctness and for liability.

### 3.8 Web app & admin console

Full-featured web app (data entry and analysis are simply better on a large screen), plus the admin
console scoped per §2.2: plan/feature/quota management, AI provider configuration and spend caps,
support tooling, aggregate analytics, audit log review.

Feature parity is explicit work rather than an aspiration: web tickets cover income and budgeting,
goals, net worth, family, splitting, AI/BYOK and billing. Capture that depends on Android-only
permissions stays mobile-only. Account, category and manual transaction management, refund and cash
reconciliation, and a cross-channel notification preference centre are explicit web work.

### 3.9 Trust, security & control (user-facing)

App lock (biometric), privacy/"hide balances" mode, full data export, **real account deletion**,
per-category consent management, access logs, a privacy-safe help/support entry, and a transparent
"what leaves your device" screen.
Launch is adult-only. Under-age or unknown eligibility fails closed before profile creation and
cannot be bypassed through a family invitation or placeholder membership.

> Given that we ask for SMS access, radical transparency about data handling is not optional
> garnish — it is the price of the permission and the core of the trust proposition.

---

## 4. Monetisation shape

Per the brief: Free, Pro, monthly and yearly, with admin-configurable features and AI quotas.

Guiding principles:

1. **Never paywall the safety net.** Manual entry, core tracking, and debt payoff basics stay free.
   An app that hides your debt payoff date behind a paywall is adversarial to a user in financial
   distress — and that user is precisely who we are for.
2. **Paywall depth and automation, not existence.** Free = you can do it. Pro = it does it for you.
3. **Splitting stays free** (§3.6) — it is acquisition, not revenue.
4. **AI is the natural metered axis.** It has real marginal cost, so quota-based tiering is honest
   and easy to explain.
5. **BYOK users should get a discount, not a penalty** — they are absorbing our COGS.

### 4.1 Confirmed pricing (from unit-economics analysis, 2026-09)

**India (INR)**

| Tier | Monthly | Annual (per mo) | AI quota | Gross margin |
|---|---|---|---|---|
| Free | ₹0 | — | 5 Q&A/mo | — (acquisition) |
| **Pro** | **₹299** | **₹199** (₹2,388/yr) | 150 Q&A + 30 summaries | **~85%** |
| Pro+ | ₹499 | ₹349 | 500 Q&A | ~85% |
| **BYOK Pro** | **₹149** | ₹99 | Unlimited (their key) | **~95%** |

**US / Global (USD)**

| Tier | Monthly | Annual (per mo) | AI quota |
|---|---|---|---|
| Free | $0 | — | 5 Q&A/mo |
| **Pro** | **$6.99** | **$4.99** | 150 Q&A + 30 summaries |
| Pro+ | $12.99 | $8.99 | 500 Q&A |
| BYOK Pro | $3.99 | $2.99 | Unlimited (their key) |

### 4.2 The margin insight that shapes the design

Initial modelling suggested AI would destroy our margins (15–17% at ₹249). **That was wrong — and
the error is instructive.** It assumed AI COGS applied to *free* users too.

> **The fix is quota enforcement, not price.** With a hard 5 Q&A/month free cap and a 150 Q&A Pro
> cap, ₹299 delivers **~85% gross margin**. Ungated AI on a free tier is what makes finance-AI
> businesses fail, not the price point.

This makes server-side quota enforcement a **revenue-critical system**, not a nicety — reinforcing
the domain-model decision to own entitlements in-house rather than delegating to a flag vendor.

**BYOK is our highest-margin tier (~95%)**, since inference cost falls to zero and only
infrastructure remains. It is simultaneously a privacy differentiator, a COGS eliminator, and a
margin winner — a genuinely rare alignment. Market it prominently.

### 4.3 BYOK loophole guards

BYOK at half the Pro price risks becoming a cheap route to the full feature set. Four guards:

1. **Scope it.** BYOK gets core features + AI-via-their-key. It does *not* get priority support,
   family sharing, or premium integrations — those stay Pro.
2. **Validate the key at signup** with a live test call; a 7-day grace period on breakage, then
   downgrade.
3. **Enforce routing server-side.** All AI calls traverse our proxy; a BYOK user with an empty key
   is rejected by the server, never the client.
4. **Soft-cap orchestration** (~500 Q&A/mo) since our infrastructure still bears per-call cost.

---

## 4A. Strategic constraints from competitor failures

Competitive research surfaced four independent post-mortems that converge on the same conclusions.
These are business-model commitments, not feature decisions.

### 4A.1 Never offer credit products. Never sell to a lender.

| Case | What happened |
|---|---|
| **Walnut** (India) | Beloved SMS expense tracker → acquired by Capital Float (2018) → rebranded Axio → PFM deprioritised for BNPL/lending → sunset. Acquired by Amazon 2025. |
| **Tally** (US) | Debt payoff app that *offered credit* → shut down Aug 2024 on credit unit economics. |
| **MoneyView** (India) | Lending + PFM → aggressive loan recovery → Trustpilot ~1.8/5 |
| **CRED** (India) | Lending monetisation → support rating ~1.9/5 |

**Lesson:** lending economics and PFM trust are structurally incompatible. The moment recovery goes
wrong, the trust that made users share their financial life with you is destroyed — and PFM trust is
the entire asset.

> **Commitment: PenniLogic is pure software, monetised by subscription. We do not lend, we do not
> broker loans, and we do not take referral fees for credit products.** This also keeps us clear of
> RBI Digital Lending Guidelines and preserves the "aligned incentives" positioning that competitors
> have forfeited.

Notably, this is also a *differentiator*: it lets us honestly say we make money only when the user
finds us useful, not when they borrow.

### 4A.2 Subscription, never ads

Mint had 22M+ users and was shut down in March 2024 because ad/referral revenue could not cover
rising data-aggregation costs. The "user is the product" model fails in PFM as costs scale with
users.

> **Commitment: no ads, no data sale.** (Play policy independently forbids selling SMS-derived
> data — see the feasibility doc.)

### 4A.3 Never retroactively degrade the free tier

Splitwise added free-tier expense limits and ads, generating sustained backlash and active user
flight — which is precisely the opening our free splitting tier targets (§3.6).

> **Commitment:** if limits are ever introduced, **grandfather existing free users** and announce
> at least 90 days ahead.

### 4A.4 Data export is a trust feature, not a nice-to-have

Monarch became the primary beneficiary of Mint's shutdown largely by making import easy. Most Indian
apps offer no export at all, and users fear lock-in.

> **Commitment: full data export from day one**, prominently offered. The willingness to let users
> leave is what convinces them to stay.

---

## 5. Sequencing

| Phase | Contents | Rationale |
|---|---|---|
| **0 — Foundations** | Ledger, auth, accounts, manual entry, categories | Correctness before cleverness |
| **1 — The wedge** | Debt engine, payoff projection, strategy comparison, simulator | The reason to install |
| **2 — Automation** | SMS parsing + declaration, **notification listener**, dedupe, clarification inbox | The reason to keep it |
| **3 — Reach** | Web app, admin console, subscriptions | Monetisation |
| **4 — Network** | Split groups, family groups | Virality + retention |
| **5 — Intelligence** | Full AI harness, BYOK, insights | Differentiation + pricing power |
| **6 — Moat** | Account Aggregator, multi-currency, expansion | Durability |

> **Deliberate ordering note:** ship the **debt engine before the AI**. The debt engine is
> deterministic, provable, and defensible; it works offline and costs nothing per user. The AI is a
> multiplier on a product that must already be valuable without it. Building the AI first would
> produce an expensive chatbot with nothing true to say.

---

## 6. Open decisions for the founder

- [ ] **Confirm the §2.1 family-sharing model** (granular/revocable) over the brief's literal
      "family can access others' data"
- [ ] **Confirm the §2.2 admin model** (system-powerful, data-restricted) over literal "full control"
- [ ] **Confirm the §2.3 advice boundary** (calculator, not adviser)
- [ ] **Accept dropping call-log access** — not permitted by Play policy for this use case
- [ ] Confirm India-first launch with global architecture
- [ ] Confirm debt-first positioning over generic "expense manager"
