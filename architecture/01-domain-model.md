# PenniLogic — Domain & Data Model

> **Status:** Draft, 2026-09-01. Research phase.
> Covers the modelling decisions that are **expensive to change later**: money representation, the
> ledger, multi-party ownership, entitlements, and deletion. These are the choices that quietly
> determine whether the product is correct at scale.

---

## 1. Money representation

**Rule: money is never a floating-point number. Anywhere. Ever.**

```kotlin
// Correct
data class Money(val minorUnits: Long, val currency: CurrencyCode)  // 1234 = ₹12.34

// Forbidden
val amount: Double   // 0.1 + 0.2 != 0.3
val amount: Float
```

- **Storage:** `BIGINT` minor units + a `CHAR(3)` ISO-4217 currency code. Two columns, always
  together. Never a bare number.
- **Why not `NUMERIC`?** Postgres `NUMERIC` is exact and acceptable, but integer minor units are
  faster, unambiguous across every language binding in a polyglot stack, and immune to a driver
  silently coercing to `double` — a very real failure mode in JS and Python clients.
- **Careful with minor-unit assumptions.** Not every currency has 2 decimal places (JPY has 0, KWD
  has 3). Store the exponent with the currency; do not hardcode `/100`.
- **Rounding must be explicit and consistent** — especially in split groups, where naive rounding
  loses or creates money. See §4.3.
- **Multi-currency:** store the original amount *and* currency, plus the FX rate and the converted
  amount **as of the transaction date**. Never convert on read using today's rate — historical
  reports would silently change over time.

---

## 2. The ledger

### 2.1 Why double-entry

A personal finance app is a bookkeeping system, and single-entry models fail predictably: transfers
between your own accounts get double-counted as income and expense, balances drift from reality, and
there is no structural invariant to catch corruption.

**Double-entry gives one invariant that catches almost every class of bug:**

> For every transaction, the sum of all entry amounts equals zero.

That single check, asserted in the database and in tests, is worth more than any amount of
defensive code.

```
Transaction: "Groceries ₹1,200 on HDFC card"
  Entry 1:  Expense:Groceries      +1200
  Entry 2:  Liability:HDFC Card    -1200
                                   -----
                                       0  ✅

Transaction: "Transfer ₹10,000 savings → current"   (single-entry gets this wrong)
  Entry 1:  Asset:Current         +10000
  Entry 2:  Asset:Savings         -10000
                                   -----
                                       0  ✅  Correctly NOT income or expense
```

### 2.2 Core shape

```
accounts        id, owner_id, type(ASSET|LIABILITY|INCOME|EXPENSE|EQUITY),
                currency, name, institution, mask, is_archived

transactions    id, owner_id, occurred_at, booked_at, description,
                source(MANUAL|SMS|NOTIFICATION|AA|IMPORT|EMAIL),
                source_confidence, dedupe_key, needs_review, external_ref

entries         id, transaction_id, account_id, amount_minor, currency
                -- SUM(amount_minor) per transaction MUST = 0
```

**Append-only.** Corrections are new reversing transactions, never `UPDATE`s or `DELETE`s on
historical entries. This gives a real audit trail and makes the ledger reconstructible — which is
what "financial correctness" actually means in practice.

### 2.3 Ingestion pipeline and dedupe

The same real-world payment can arrive via SMS *and* a notification *and* later via Account
Aggregator. Deduplication is therefore a first-class concern, not a cleanup step.

```
RawFinancialEvent  →  Parse  →  Candidate  →  Dedupe  →  Enrich  →  Transaction
                                                 ↓
                                      needs_review → "What was this?"
```

- **`transactions.dedupe_key`** is a server-computed, keyed fingerprint over canonical structured
  fields. It is not derived from raw message text. Duplicate candidates are found by a fuzzy match
  on `(amount, account, timestamp ± window, merchant-ish)` because sources disagree on those values.
  A fuzzy merge creates a reversible link and audit record; it never deletes either candidate.
- **Exact raw-message dedupe is device-local.** The Android raw-event store keeps an HMAC under a
  per-install Keystore key. Neither that digest nor the raw text crosses the API, sync or export
  boundary. ADR-018 must publish the precise construction and supersede ADR-004's ambiguous hash
  sentence before capture contracts can leave `Backlog`.
- **Source precedence:** `AA > IMPORT > SMS > NOTIFICATION > MANUAL-guess`. A higher-authority
  source *enriches* an existing record; it must never silently contradict a **user-confirmed** value.
  User confirmation always wins.
- Keep the raw event (on-device) linked to the transaction for debugging parser regressions.

---

## 3. Ownership, sharing, and authorization

This is the hardest part of the model. A single transaction may be visible to: its owner, a family
member with a category-level grant, and members of a split group it was shared into — each with a
*different* level of detail.

**Do not model this with roles.** Role-based access control collapses under "user A can see user B's
*aggregate income* but not their *transaction descriptions*, only while a grant is active, and only
for accounts B has opted in." That is a **relationship** question, not a role question.

**Recommendation: relationship-based access control (ReBAC, Zanzibar-style).**

```
transaction:tx_123#owner            @user:alice
account:acc_9#viewer_aggregate      @family_group:fam_5#member
family_group:fam_5#member           @user:bob
split_group:trip_goa#member         @user:carol
```

Then every access is one question: *does `user:bob` have `viewer_aggregate` on `account:acc_9`?*

**Design rules:**

1. **Default deny.** Absence of a grant is a denial.
2. **Grants are per-(member × category × detail-level)**, not per-group. Granularity lives in the
   grant, not in code branches.
3. **Revocation is unilateral** — no counterparty approval — and takes effect against two *different,
   published, numeric* bounds, not one. Server-served reads stop within the **online revocation
   bound** measured from the successful revoke call. A client that is offline serves previously
   granted data only until its **offline lease bound** elapses, then denies. `T-CON-04` publishes
   both numbers as contract metadata, `T-FAM-02` tests both, and neither may be described to a user
   as "immediate". The security architecture's 24-hour local cache TTL and remote-wipe signal are the
   *offline* bound; they are not a contradiction of this rule, they are the second half of it.
   Earlier wording in the product spec §2.1 that says "immediate, no cached copies" describes the
   online bound only and is superseded by the two-bound statement here.
4. **Aggregate vs. detail are genuinely different permissions**, not a UI toggle. "Total spent last
   month" and "the list of what you bought" must be separately grantable.
5. **Every detail-level access on another person's data is logged and visible to that person.**
6. **Sharing a transaction into a split group shares only the split-relevant projection** —
   amount, date, description — never the funding account or balances.

---

## 4. Split groups

### 4.1 Model

```
split_groups            id, name, currency, simplify_debts(bool)
split_group_members     group_id, user_id | placeholder_name   -- non-users must work
split_expenses          id, group_id, payer_id, amount, currency, occurred_at, description
split_shares            expense_id, member_id, share_minor     -- SUM = expense amount, exactly
settlements             id, group_id, from_member, to_member, amount, settled_at, method
```

**Placeholder members matter.** Requiring everyone to install the app before you can split a trip
kills the viral loop — which is the entire strategic point of this feature. Support named
placeholders that can be claimed later.

### 4.2 Debt simplification

Minimise the number of transfers needed to settle. Compute each member's net balance, then greedily
match largest creditor to largest debtor.

```
Raw:        A→B ₹500, B→C ₹500, C→A ₹200     (3 transfers)
Simplified: A→C ₹300, ...                    (fewer transfers, identical net position)
```

**Make it optional and always show the derivation.** Users get suspicious when an app silently
rewrites who owes whom — Splitwise has this complaint. Transparency here is a trust feature.

### 4.3 The rounding invariant

```
₹100 split 3 ways = 33.33 + 33.33 + 33.33 = ₹99.99   ← ₹0.01 has vanished
```

**Rule: `SUM(split_shares.share_minor) == split_expenses.amount_minor`, enforced as a database
constraint.** Distribute remainder minor units deterministically (e.g. to the earliest members by
a stable ordering) and make it visible. Money must never be created or destroyed by rounding.

---

## 5. Plans, entitlements, and AI quota

> **Superseded by [ADR-023](../adr/ADR-023.md) (`T-ADR-ENT-09`, accepted 2026-09-30).** This section
> is research history, not implementation authority. ADR-023 §1 names this section and
> [`03-stack-and-monetization.md` §8](03-stack-and-monetization.md#8-entitlements--feature-flags) as
> the two sketches it supersedes in full, and states which rules below remain binding (server-side
> checks, own-key usage metered but not charged against the token allowance, a defined and displayed
> reset semantic, reserve-then-reconcile for streamed consumption, no data loss on a plan change) and
> which are discarded (the mutable `plans` row, plan-scoped `max_requests`/`max_tokens`/
> `allowed_models[]`, `cost_micros` and `byok(bool)` on usage events). Read ADR-023 for plan
> versions, feature keys, the `requests` and `tokens` dimensions, the model allowlist and
> `model_not_in_plan`, BYOK treatment, the event-sourced ledger and the reset boundary. `T-CON-03`,
> `T-BIL-01`, `T-BIL-02` and `T-AI-01` consume that record, not this section. What follows is the
> argument that produced the question, not the schema to build.

The brief requires admin-configurable per-plan features and AI quotas. This should be **first-class
data we own**, not an external feature-flag vendor — entitlements are billing-critical, must be
enforced server-side, must be queryable transactionally alongside the subscription, and must not
depend on a third-party's availability to decide whether a paying user gets what they paid for.

```
plans                 id, code, name, is_active
plan_features         plan_id, feature_key, enabled, limit_value   -- e.g. max_accounts
plan_ai_quotas        plan_id, window(DAY|MONTH), max_requests, max_tokens, allowed_models[]
subscriptions         id, user_id, plan_id, status, period_start, period_end,
                      provider(PLAY|STRIPE|RAZORPAY), provider_ref
ai_usage_events       id, user_id, occurred_at, feature, model, provider,
                      input_tokens, output_tokens, cost_micros, byok(bool)
```

**Design rules:**

- **Entitlement checks are server-side.** The client may *hint* the UI, but the server is
  authoritative. Never trust a client claim of "Pro".
- **BYOK usage is metered but not charged against paid quota.** The user is paying the provider
  directly; charging them our quota too would be indefensible. Still record usage — for abuse
  detection and product analytics.
- **Quota windows need a defined reset semantic** (calendar day in the user's timezone vs. rolling
  24h). Pick one, document it, show it in the UI. Ambiguity here generates support tickets.
- **Metering streaming responses:** output token count is unknown until the stream completes.
  Reserve an estimate on start, reconcile on completion, and fail *open* on a reconciliation error
  (never charge a user for a response they did not receive).
- **Plan changes must not retroactively invalidate data.** If a user downgrades below their account
  limit, existing accounts go read-only — they are never deleted. Deleting a paying-then-free user's
  financial history would be catastrophic and unforgivable.

---

## 6. Deletion, retention, and the append-only conflict

There is a **real architectural conflict** here that must be designed for deliberately:

> Financial correctness wants an **immutable, append-only** ledger.
> DPDP/GDPR give users a **right to erasure**.

These are in direct tension. The standard resolution is **crypto-shredding**:

1. Encrypt each user's sensitive field data with a **per-user data encryption key (DEK)**.
2. The DEK is itself encrypted by a master key in a KMS (envelope encryption).
3. **To erase a user, destroy their DEK.** The ciphertext remains in backups and append-only
   structures but is permanently unreadable — cryptographically equivalent to deletion.

This satisfies erasure without violating ledger immutability or corrupting backups, and it is
robust to the practical reality that you cannot selectively rewrite historical backups.

Also required:
- **Retention schedules per data class** (raw events vs. ledger vs. audit logs), since regulators
  mandate *minimum* log retention that can conflict with *maximum* data retention.
- **Deletion must propagate to derived data**: embeddings, caches, search indexes, analytics,
  and any third-party processor.
- **Split groups complicate erasure**: a deleted user's expenses still affect *other* members'
  balances. Resolution: anonymise the member to a placeholder, preserve the financial facts needed
  for others' correctness, destroy the personal identifiers.

---

## 7. Offline-first and sync

Mobile finance apps must work on a train with no signal, and SMS-triggered capture happens whether
or not the network is up.

- **Local Room/SQLite is the source of truth for the client**; the server is the source of truth for
  the account.
- **Queue mutations locally** with idempotency keys; replay on reconnect.
- **Conflicts are rare but must be defined.** Financial records are mostly append-only, which makes
  this tractable: last-writer-wins on *user-editable metadata* (category, notes) and
  never-overwrite on *ledger amounts*.
- **Idempotency keys on every mutating API call** — a retried "add transaction" must not create
  duplicates. This is the single most common source of phantom-duplicate bugs in finance apps.

---

## 8. Decisions to confirm

**Confirmed 2026-09-01** — all five are accepted and recorded as ADRs:

- [x] Double-entry ledger — **accepted**, ADR-002
- [x] Integer minor units — **accepted**, ADR-001
- [x] ReBAC/Zanzibar for sharing — **accepted**, ADR-005
- [x] Crypto-shredding as the erasure mechanism — **accepted**, ADR-006
- [x] Entitlements owned in-house — **accepted**, ADR-007

### 8.1 Still unresolved — schema gates that block implementation

Accepting the five above fixed the *shape* of the model, not its details. These remain open, each is
a decision record in epic E26, and dependent schema, migration and generated-client work stays in
`Backlog` until the corresponding record is accepted. See
[`../product/04-execution-readiness-review.md`](../product/04-execution-readiness-review.md).

| Gate | Ticket | What is undecided |
|---|---|---|
| Money wire format, time, idempotency | `T-ADR-MONEY-01` | JSON representation of an amount across languages, UTC instants plus user time zone, idempotency key scope/lifetime/conflict behaviour |
| Category model | `T-ADR-CAT-02` | Categories as an append-only reporting dimension versus mutable rows that rewrite history |
| Ledger currency, FX, debt balance | `T-ADR-LEDGER-03` | Ledger currency policy, FX reservation, and how a debt balance is derived rather than cached |
| Encryption, search, RLS, dedupe artifacts | `T-ADR-CRYPTO-04` | Which columns are encrypted, which stay searchable, where row-level security applies, and how device-local raw-message HMAC, server structured fingerprint and fuzzy candidate matching remain distinct |
| Auth, passkeys, RP-ID, recovery | `T-ADR-AUTH-05` | Provider, relying-party identifier, and account recovery — the RP-ID is expensive to change after first enrolment |
| Administrative boundary | `T-ADR-ADMIN-06` | Admin deployment separation, database role, and the audit event stream |
| Shared-data erasure | `T-ADR-ERASE-07` | Crypto-shredding across shared data and cross-user key access — the open question ADR-006 named |
| AI egress, Mode C | `T-ADR-AIEGRESS-08` | Egress path, runtime platform, and custom-endpoint handling |
