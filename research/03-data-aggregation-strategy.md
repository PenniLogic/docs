# PenniLogic — Bank Data Aggregation Strategy

> **Status:** Consolidated 2026-09-01 from the compliance and feasibility research.
> **Purpose:** one place to answer "how do we get bank data in market X, and what does it cost us in
> money, time and regulatory burden?" Detail and sources live in
> [`../compliance/01-regulatory-landscape.md`](../compliance/01-regulatory-landscape.md).

---

## 1. The short answer

| Market | Mechanism | Can we use it *now*? |
|---|---|---|
| **India (launch)** | On-device SMS + notification parsing | ✅ **Yes** — no third party, no licence |
| **India (later)** | RBI Account Aggregator | ❌ **Not directly** — requires regulated FIU status |
| **EU** | Ride a licensed AISP (Tink, TrueLayer) | ✅ Yes — they hold the licence |
| **UK** | Agent of an FCA-authorised AISP (TrueLayer, Yapily) | ✅ Yes — agent model |
| **US** | Screen-scraping aggregators (Plaid, MX, Finicity) | ✅ Yes — no federal mandate in force |

**MVP conclusion: we need no aggregation vendor at all.** India launch runs entirely on on-device
parsing plus manual entry and statement import. Every aggregator relationship is a later-phase,
market-entry decision — which is a genuine advantage, since it means zero per-user data cost and
zero vendor dependency at launch.

---

## 2. India — the important nuance

The Account Aggregator framework is the best data source in the country: consented, structured,
authoritative, no parser rot, 284.6M linked accounts and 179+ FIPs as of March 2026, with PFM an
explicitly recognised consent purpose.

**But we cannot use it.** An FIU must be regulated by RBI, SEBI, IRDAI or PFRDA
(<https://sahamati.org.in/fiu/>), and a Technology Service Provider — Setu, Perfios, Finarkein,
FinBox, Digitap, Cygnet — **cannot confer that status**. They build the plumbing *for* a regulated
entity.

| Route | Lead time | Notes |
|---|---|---|
| Partner with a regulated FIU | Months | Viable; adds dependency + likely revenue share |
| TSP alone | — | **Does not solve eligibility** |
| **SEBI IA registration** | Months–years | **Also unlocks richer advice features** — dual payoff |
| NBFC registration | Years | ~₹10 Cr capital; disproportionate for a PFM app |

> **Strategic read:** AA is a *destination*, not a fallback. Treating it as an emergency escape
> hatch from a Play policy change would be a planning error — see risk R1 in the risk register.

**Available FI types** (once eligible): deposits (up to 6 months of transactions with date, amount,
credit/debit, narration, mode, counterparty), term/recurring deposits, mutual funds, equities, NPS,
insurance, EPF/PPF, GSTN. Rich enough for everything we want to do.

**Cost:** negotiated per-consent or per-fetch, not publicly standardised. `UNVERIFIED` — confirm
commercially when the time comes.

---

## 3. Global expansion

**EU — PSD2.** We do **not** need our own AISP licence to start. Integrate a licensed aggregator
(Tink, Visa-owned; or TrueLayer) which holds the licence and manages bank connections; we build UX
on top. Own registration becomes worthwhile only at scale. Watch PSD3/PSR and FiDA.

**UK.** Either FCA AISP authorisation or — the practical MVP path — operate as an **agent** of an
authorised AISP such as TrueLayer UK or Yapily.

**US.** CFPB Section 1033 exists on paper but is **enjoined and being rewritten**; as of September
2026 there are no operative compliance deadlines and no binding federal open-banking requirement.
Data access therefore still runs through aggregators (Plaid, MX, Finicity/Mastercard) or direct bank
partnerships.

> ⚠️ **Cost warning learned from Mint.** Mint was shut down partly because aggregation costs scale
> with users while ad revenue does not. Any aggregator we adopt introduces a **per-user variable
> cost** that must be priced into the tier that uses it. This is a further argument for
> subscription-only monetisation, and for keeping on-device parsing — which costs nothing per user —
> as the primary channel wherever it works.

---

## 4. Sequencing

1. **Now (MVP, India):** on-device parsing + manual + import. No vendor, no licence, no per-user cost.
2. **Year 1:** open the regulated-partner / SEBI-IA conversation. Long lead time, so start early.
3. **On EU/UK entry:** integrate Tink or TrueLayer; ride their licence.
4. **On US entry:** Plaid or MX; price the per-user cost into the plan.
5. **At scale:** revisit owning the licence in each region.

---

## 5. Open items

- [ ] Confirm FIU eligibility directly against the RBI Master Direction with counsel
- [ ] Commercial AA pricing from at least two AAs/TSPs (`UNVERIFIED` today)
- [ ] Plaid / Tink / TrueLayer current per-user pricing before committing to a market
