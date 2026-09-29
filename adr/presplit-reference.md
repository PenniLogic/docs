# Architecture Decision Records

Short, durable records of decisions that are expensive to reverse. Each states the decision, the
reasoning, and what would make us revisit it.

**Status key:** `ACCEPTED` = decided · `PROPOSED` = recommended, awaiting founder sign-off ·
`SUPERSEDED` = replaced by a later ADR

ADR-001 to ADR-014 below are **accepted** and unchanged. Nine further decisions are open and gate
implementation — see [Pending execution-gate ADRs](#pending-execution-gate-adrs) at the end. They are
reserved as ADR-015 to ADR-023, one file each.

---

## ADR-001 — Money is stored as integer minor units
**Status:** ACCEPTED · 2026-09-01

**Decision.** All monetary values are `BIGINT` minor units paired with an ISO-4217 currency code.
Floating-point types are forbidden for money anywhere in the system.

**Why.** Binary floating point cannot represent decimal fractions exactly (`0.1 + 0.2 != 0.3`),
and rounding drift in a financial ledger is unacceptable and hard to detect. Integer minor units are
exact, fast, and unambiguous across Kotlin, Python, TypeScript and SQL — avoiding the real risk of a
driver silently coercing `NUMERIC` to `double`.

**Notes.** Currency exponent is stored with the currency — never hardcode `/100` (JPY = 0, KWD = 3).
FX: store original amount, currency, rate, and converted value *as of the transaction date*.

**Revisit if:** never, realistically.

---

## ADR-002 — Double-entry, append-only ledger
**Status:** ACCEPTED · 2026-09-01

**Decision.** Transactions comprise balanced entries; `SUM(entries.amount) = 0` per transaction,
enforced in the database. Records are append-only; corrections are reversing entries.

**Why.** Single-entry models systematically mis-handle transfers between a user's own accounts
(double-counting them as income and expense) and provide no structural invariant to detect
corruption. The zero-sum rule catches a whole class of bugs at the storage layer. Append-only gives
a real audit trail and reconstructible history.

**Cost.** Conflicts with the right to erasure — resolved by ADR-006.

---

## ADR-003 — Deterministic parser primary, on-device LLM as fallback
**Status:** ACCEPTED · 2026-09-01 · *overrides the AI research recommendation*

**Decision.** SMS/notification parsing uses a deterministic regex/template parser as the **primary**
path, with a small on-device LLM (Gemma-3 1B via LiteRT-LM) as a **fallback** for unrecognised
formats on capable hardware.

**Why.** The AI research proposed the inverse. But the on-device model requires roughly
Snapdragon 8 Gen 2+ and 8 GB+ RAM — flagship devices. **India is our launch market and is
predominantly mid-range hardware.** An architecture whose core ingestion works only on premium
phones would fail most of the target market. The deterministic parser covers ~80–85% of Indian bank
SMS formats, runs on any device, and is fast, battery-cheap and debuggable.

**Consequence.** Parser templates ship as **remotely updatable config**, so a bank changing format
is a config push rather than an app release.

**Validated 2026-09-01.** A spike on an Android 12 emulator parsed realistic HDFC/ICICI/SBI messages
**5/5**, including correctly ignoring a loan promo sent from a genuine bank sender ID and a rupee
amount from a non-bank sender. See `docs/research/spikes/sms_parser_spike.py`. The negative cases
are the important ones — a parser that invents transactions from marketing SMS would corrupt the
ledger.

**Revisit if:** small-model hardware requirements fall far enough to cover mid-range devices.

---

## ADR-004 — Raw message content never leaves the device
**Status:** ACCEPTED · 2026-09-01

**Decision.** Raw SMS and notification text is parsed on-device. Only structured transactions
(`amount, merchant, direction, occurred_at, account_ref`) are transmitted. A hash of the raw message
is stored for deduplication; the text itself never is. The server API has **no field** capable of
accepting raw message content.

**Pending execution clarification.** The accepted privacy boundary remains unchanged, but the
sentence above does not distinguish local exact deduplication from server cross-channel matching.
ADR-018 must define those as separate artefacts before implementation: any raw-derived digest stays
device-local, while the server may receive only structured fields and a non-content-derived source
identifier. Until ADR-018 is accepted, no capture or sync contract may add a raw-derived digest.

**Why.** Four benefits at once: (1) removes a concentrated store of raw financial text as a breach
target, (2) materially reduces DPDP/GDPR exposure through data minimisation, (3) reduces Play policy
risk, (4) genuine competitive differentiation. Enforcing it in the API contract makes it structural
rather than a policy someone can forget.

---

## ADR-005 — Relationship-based access control (ReBAC) for sharing
**Status:** ACCEPTED · 2026-09-01 *(approved by founder)*

**Decision.** Use a Zanzibar-style ReBAC model (OpenFGA or SpiceDB) for authorization, rather than
roles.

**Why.** Our sharing model — personal data, family groups with per-category grants, split groups,
and admin — is a *relationship* question, not a role question. RBAC collapses under requirements
like "A may see B's aggregate income but not transaction descriptions, only while a grant is active."
Aggregate access and detail access must be independently grantable.

**Rules.** Default deny. Grants are per-(member × category × detail-level). Revocation is immediate
and unilateral. Detail-level access to another person's data is logged and visible to them.

**Revisit if:** the final sharing model turns out much simpler than specified.

---

## ADR-006 — Crypto-shredding for the right to erasure
**Status:** ACCEPTED · 2026-09-01 *(approved by founder)*

**Decision.** Encrypt per-user sensitive data with a per-user data encryption key (DEK) under
envelope encryption. To erase a user, destroy the DEK.

**Why.** Resolves the direct conflict between an append-only ledger (ADR-002) plus immutable backups
and the DPDP/GDPR right to erasure. Ciphertext remains but is permanently unreadable —
cryptographically equivalent to deletion — without rewriting history or corrupting backups.

**Open.** Split groups complicate this: a deleted member's expenses still affect others' balances.
Resolution is to anonymise to a placeholder, preserve the financial facts others depend on, and
destroy personal identifiers.

---

## ADR-007 — Entitlements owned in-house, enforced server-side
**Status:** ACCEPTED · 2026-09-01

**Decision.** Plans, features and AI quotas are first-class tables we own. Enforcement is
server-side. No third-party feature-flag vendor sits in the entitlement path.

**Why.** Entitlements are **billing-critical and revenue-critical**. The unit-economics analysis
showed margin depends almost entirely on quota enforcement — ungated free-tier AI, not price, is
what destroys margin. That makes quota enforcement a core business system that must be
transactionally consistent with subscription state and must not depend on a vendor's uptime to
decide whether a paying user gets what they paid for.

**Note.** A flag vendor may still be used for *release* flags (staged rollouts) — just never for
entitlements.

---

## ADR-008 — Native Android (not cross-platform)
**Status:** ACCEPTED · 2026-09-01

**Decision.** Kotlin + Jetpack Compose, native.

**Why.** The product depends on deep OS integration: `NotificationListenerService`, SMS receivers,
background work under modern Android restrictions, on-device ML, Android Keystore/StrongBox, and
Play Integrity. These are exactly the areas where cross-platform frameworks require native modules
anyway, forfeiting the benefit. Kotlin also aligns with the backend choice (ADR-009), enabling
shared models.

**Later.** Kotlin Multiplatform can share business logic with a future iOS app; the domain/ledger
logic should be written with that in mind.

---

## ADR-009 — Polyglot backend: Kotlin/Ktor core + Python/FastAPI AI service
**Status:** ACCEPTED · 2026-09-01 *(approved by founder)*

**Decision.** Core API (auth, ledger, entitlements, sync) in Kotlin/Ktor. A separate Python/FastAPI
service hosts the AI harness and LiteLLM proxy.

**Why.** Kotlin shares language and models with the Android client and is strongly typed for
financial correctness. Python is where the AI ecosystem lives (LiteLLM is Python-first). Splitting
them lets the AI service scale, fail, and be replaced independently of the money-handling core —
which is desirable, since the AI service is the component most likely to change.

**Risk.** Two runtimes to operate. Acceptable given the clean boundary.

---

## ADR-010 — Offline: start simple, adopt a sync engine later
**Status:** ACCEPTED · 2026-09-01

**Decision.** MVP uses local SQLite plus an offline mutation queue (WorkManager) with idempotency
keys. Evaluate PowerSync for v1.1.

**Why.** Financial records are append-only by nature, which makes conflict resolution largely
unnecessary — you never edit a past debit, you post a correction. Most consumer finance apps use
simple last-write-wins on reconnect rather than CRDTs. A full sync engine is ~2–3 weeks of setup and
ongoing complexity that is not justified before we have users.

**Rule.** Never sync a cached balance — always recompute from entries. Stale balances are the main
real conflict hazard.

**Revisit when:** multi-device usage or real-time family sharing makes manual sync painful.

---

## ADR-011 — Drop call log access
**Status:** ACCEPTED · 2026-09-01

**Decision.** Remove the brief's "access my Calls" requirement.

**Why.** Google Play grants `CALL_LOG` only for default-dialer, caller-ID/spam, companion-device,
cross-device sync, automation, enterprise, in-vehicle, proxy-call, and a bank's own authentication
use cases. There is **no money-management exception**, and account-verification-by-call is being
removed effective 2027-01-27. Requesting it would likely jeopardise the SMS declaration in the same
review. There is also little product value — call logs record who you called, not what you spent.

---

## ADR-012 — Positioning: debt-first
**Status:** ACCEPTED · 2026-09-01 *(approved by founder)*

**Decision.** Lead with debt payoff, not general expense tracking.

**Why.** Retention is the primary killer of personal finance apps (Mint had scale and still shut
down). A debt payoff countdown is a destination and a reason to return; a spending pie chart is a
chore. Debt payoff also produces provable, deterministic value ("14 months sooner, ₹1.87 lakh saved")
that justifies a subscription, and it works offline with zero marginal cost.

**Consequence.** Build the deterministic debt engine **before** the AI harness. The AI is a
multiplier on a product that must already be valuable.

---

## ADR-013 — Account Aggregator: Route D (defer AA, on-device parsing for MVP)
**Status:** ACCEPTED · 2026-09-01 *(founder decision)*

**Decision.** For MVP we do **not** pursue Account Aggregator access. Ingestion is on-device SMS and
notification parsing, plus manual entry and statement import. We do not partner with a regulated
FIU, do not engage a TSP, and do not seek NBFC or SEBI IA registration at this stage.

**Why.** A non-regulated entity cannot be an FIU (ADR context: <https://sahamati.org.in/fiu/>), and
the alternatives all carry material cost:

| Route | Why not now |
|---|---|
| A — partner with a regulated FIU | Adds a dependency, revenue share, and partner negotiation before we have users |
| B — TSP | Cannot confer FIU status; solves nothing on its own |
| C — become regulated | NBFC ≈ ₹10 Cr capital; SEBI IA needs counsel + runway. Disproportionate pre-product-market-fit |
| **D — on-device parsing** | **Chosen.** No third party, no licence, no per-user data cost |

The decisive argument: the AA Master Direction governs entities accessing data **through the AA
network**. On-device SMS parsing with user consent is a different category entirely, so Route D
**removes the FIU question from the MVP critical path** rather than deferring it.

It also has a real economic benefit — zero per-user data-acquisition cost, which is precisely the
cost structure that killed Mint.

**What this obliges us to do.** Because AA is *not* an available fallback (see risk R1), the
mitigations must be things we control:
1. Manual entry and statement import must be **genuinely excellent**, not token fallbacks.
2. The **notification listener ships alongside SMS** — different policy surface, so a single Google
   decision cannot remove both channels.
3. All ingestion sits behind one `TransactionSource` abstraction so a future AA integration is an
   additive change, not a rewrite.

**Revisit when:** we approach product-market fit, SMS coverage measurably degrades, or SEBI IA
registration becomes attractive for advice features (at which point it unlocks AA as a side effect —
see feasibility doc §5.2).

---

## ADR-014 — Multi-repository structure under the PenniLogic GitHub org
**Status:** ACCEPTED · 2026-09-01 *(founder decision)*

**Decision.** One repository per deployable unit, in the `PenniLogic` org, rather than a monorepo.

| Repo | Contains | Stack |
|---|---|---|
| `docs` | Product, architecture, compliance, ADRs — the source of truth | Markdown |
| `contracts` | OpenAPI specs, shared schemas, generated clients | YAML/JSON |
| `api` | Core API: auth, ledger, entitlements, sync | Kotlin/Ktor |
| `ai-service` | AI harness, LiteLLM proxy, BYOK routing, quotas | Python/FastAPI |
| `android` | Native mobile app, on-device parsing | Kotlin/Compose |
| `web` | Customer-facing web app | Next.js |
| `admin` | Admin console — **separate service, separate auth domain** | Next.js |
| `infra` | IaC, deployment, observability config | Terraform/Docker |

**Why separate `admin`.** This is a security decision, not an organisational one. The security
architecture requires the admin console to be a separate service on a separate auth domain, so that
a compromise of the customer-facing web app cannot reach admin capability. Sharing a repo would make
it easy to accidentally share code, config, or session handling across that boundary.

**Why a `contracts` repo.** The main cost of multi-repo is interface drift between the API and its
three clients. A dedicated contracts repo, versioned and consumed by the others, makes the interface
an explicit artefact rather than an accident. Without it, multi-repo reliably produces
"the app broke because the API changed" bugs.

**Accepted cost.** Cross-cutting changes now span multiple pull requests, and CI must handle
cross-repo dependencies. This is the deliberate trade for independent deployability and a hard
security boundary around admin.

---

## Pending execution-gate ADRs

Nine decisions are still open. Each is a ticket in epic **E26 - Architecture decision gates**, each
depends on `T-GOV-03` (branch protection, agent-review routing and current-head attestation gates),
and each is `Backlog` until that dependency closes. The GitHub Team capability prerequisite
is complete (`T-EXT-01`), so `T-GOV-03` is now `In Progress`.
**Dependent implementation work stays in `Backlog` until the record is accepted**
and merged here as a numbered ADR - no schema, generated client, or money-path code lands before the
record that fixes its shape.

**Each record has a reserved number and its own file.** `T-ADR-INDEX-10` splits this document into
one file per decision and generates both the accepted index and the table below, so nine tickets can
land in parallel without any two of them editing the same lines. The reservation is checked in: a
record claiming a number reserved for a different ticket fails the check, and a generated region that
has been hand-edited fails it too.

No outcome is recorded below, because none has been decided. The "Question" column states what the
record must settle, not what it will say.

| File | Ticket | Question the record must settle | Blocks |
|---|---|---|---|
| ADR-015 | `T-ADR-MONEY-01` | Money wire format, time representation and idempotency: the exact JSON form of an amount, UTC instants plus an explicit user time zone, idempotency key scope, lifetime and conflict behaviour, and the Kotlin, TypeScript and Python wrapper types with their serialisation seams | Contracts, generated clients, every financial write path |
| ADR-016 | `T-ADR-CAT-02` | Category model: append-only reporting dimension versus mutable rows that silently rewrite historical reports | Ledger schema, budgets, reporting |
| ADR-017 | `T-ADR-LEDGER-03` | Ledger currency, foreign-exchange reservation, and how a debt balance is derived rather than cached | Ledger schema, debt engine, multi-currency (E30) |
| ADR-018 | `T-ADR-CRYPTO-04` | Encryption scope, searchable fields, row-level security and grant-mediated reads; also the distinct device-local raw-message HMAC, server structured dedupe key and reversible fuzzy-match semantics that supersede ADR-004's ambiguous hash sentence | Data protection floor (E19), capture contract (E02), sharing (E15, E16), any environment holding real data |
| ADR-019 | `T-ADR-AUTH-05` | Authentication provider, passkeys, the relying-party identifier, and account recovery | Auth, onboarding, recovery, all clients |
| ADR-020 | `T-ADR-ADMIN-06` | Administrative boundary: deployment separation, database role, and how the foundational audit trail, the chained administrative log and the subject-visible transparency stream relate - stores, and single or dual write | Admin console (E13), audit and insider-risk controls, transparency surfaces |
| ADR-021 | `T-ADR-ERASE-07` | Shared-data erasure and cross-user key access - the open question ADR-006 named | Sharing and split groups (E15, E16), erasure and data-principal rights |
| ADR-022 | `T-ADR-AIEGRESS-08` | AI egress path, runtime platform, and Mode C custom endpoints - including which destinations are code-managed and which are runtime registered, validated and pinned | AI harness (E17), AI product surfaces (E18), BYOK, platform (E24) |
| ADR-023 | `T-ADR-ENT-09` | Entitlement and quota model: plan and feature identity, request and token quota dimensions, per-plan model allowlist and unlisted-model refusal, BYOK quota treatment, event-sourced usage versus materialized counters, and the reset boundary and its time zone. **Supersedes** the conflicting sketches in `architecture/01-domain-model.md` §5 and `architecture/03-stack-and-monetization.md` §8 | Quota contract (`T-CON-03`), billing (`T-BIL-01`, `T-BIL-02`), AI gateway (`T-AI-01`) |

A tenth E26 ticket, `T-ADR-INDEX-10`, is not a decision: it owns the per-file layout, the reservation
file and the generator for the two tables in this document.

Two additional decisions are deliberately `Future` and do not block the MVP tranche:
`T-ADR-BUREAU-11` decides whether credit-bureau integration is viable without violating the
no-lending business model, and `T-ADR-EMBED-12` decides whether any user-derived embedding may be
persisted. Until the latter is accepted, vector database extensions and durable user-derived
embeddings are prohibited.

Context and the full gate list: [`../product/04-execution-readiness-review.md`](../product/04-execution-readiness-review.md).
Ticket source: [`../planning-automation/backlog-v2/README.md`](../planning-automation/backlog-v2/README.md).
