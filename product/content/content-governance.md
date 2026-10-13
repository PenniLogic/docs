# Content system: ownership, regulated-copy workflow and signals

> **Status: proposed.** This page and every value in `product/content/` are proposed by the implementing session
> of PenniLogic/docs#84 (T-CNT-01) and await confirmation by their owners. Nothing here is legal text, legal
> interpretation, an approval or comprehension evidence.

## Files

| File | Role |
|---|---|
| `glossary.json` | One definition and preferred label per term (`term.<slug>`), forbidden aliases, surfaces, comprehension flag. |
| `voice.json` | Reading-level target (provisional), sentence limit, principles, banned shame/guarantee/hype/advice phrases, number/date/currency conventions and the eight content patterns. |
| `message-keys.json` | Source-of-copy catalogue: key, category, copy, minimum/typical/maximum range, term references, owner, platforms, neutral safe exit. |
| `regulated-copy.json` | Versioned regulated and security copy (`RC-NNN`) with approval, history and rollback fields. |
| `*.schema.json` | Shape only, shared draft-07 subset; every rule beyond shape is in `scripts/check_content.py`. |
| `glossary.md`, `voice.md`, `message-keys.md`, `regulated-copy.md` | Generated views (`python scripts/check_content.py --write-views`); a unittest fails when they drift. |

The client-state taxonomy (`product/client-state-taxonomy.json`, PenniLogic/docs#1) stays the only source of state
copy, forbidden terms and copy rules. This catalogue imports them by reference: `state.` keys are derived from its
state identifiers and carry no copy, and a forbidden term restated here is refused as a fork.

## Key namespaces

| Root | Meaning |
|---|---|
| `state.` | Derived from taxonomy states: `state.<id>.headline/body/action`, `state.<id>.<variant>.headline/body`, `state.<id>.<variant or cause>.action`. No copy. |
| `nav.` | Navigation labels owned by PenniLogic/docs#74. Held: every `nav.` key is refused until docs#74 publishes them, and the default check counts the hold as a readiness gap. |
| `reg.` | Bound one-to-one to a regulated-copy record; the copy lives only in the record. |
| `common.` | Shared by Android, web and admin, including the neutral safe-exit keys. |
| other | Product copy such as `pattern.` slot keys; may not use the `term`, `voice`, `banned` or `convention` roots. |

Removing or renaming a term or key needs a major version bump; additions are minor.

## Regulated-copy workflow

1. Content Design drafts a record (`status: draft`, `approval: null`) bound to its `reg.` key and a neutral
   fail-closed key.
2. The record moves to `in_review` when the qualified legal/compliance owner (design-gates role `legal`) receives
   it. That role is unassigned today, so no record can leave draft with an approval.
3. Only that owner records approval: role, decision reference, `effective_at` and `expires_at` (at most 366 days
   apart). The checker refuses an approval from any other role, without a decision reference, or without a
   coordinator-verified assignment of the role; the published data supplies none.
4. Approved copy is usable only while `effective_at <= now < expires_at`; at `expires_at` it is expired. The clock
   is injected (`--now`), never inferred.
5. Changing approved copy means a new version; the record keeps its prior versions in `history`.
6. Withdrawal sets `withdrawn`; records are never deleted.

**Fail closed.** A consumer that finds a record missing, draft, in review, not yet effective, expired or withdrawn
shows the record's fail-closed key (a neutral safe-exit key without placeholders) or blocks the flow. It never
substitutes local or cached text.

**Rollback** pins `rollback_version` to a prior version in `history` whose status is `approved` and whose window
still contains `now`; any other target is refused.

## Proposed observability signals (metadata only)

Names proposed for the observability owners; they carry identifiers and counts only, never copy, user content,
amounts or identity.

| Signal | Emitted when | Fields |
|---|---|---|
| `content.unknown_term` | A client or support tool meets a term reference that is not in the glossary. | term identifier, glossary version, platform |
| `content.copy_version_mismatch` | A client renders a key or record version other than the published one, or a regulated record fails closed. | key or `RC-NNN`, expected and found versions, platform |
| `content.comprehension_failure` | A comprehension study (PenniLogic/docs#66) records a failed explanation of a term. | term identifier, study reference |
| `content.wording_support_contact` | Support tags a contact as caused by wording. | key or term identifier, support category |

## Held gates (never filled in here)

- Comprehension evidence for payoff, projected, available, pending, reversed, aggregate and revoked
  (PenniLogic/docs#66); the reading-level target stays provisional until then.
- Qualified legal/compliance approval of every regulated record; the approver role is unassigned.
- Content, Compliance, Accessibility and CDO approvals; independent Core, QA, Compliance and Accessibility review.
- `nav.` labels from PenniLogic/docs#74; infra#22 conformance; current-head CI on the pull request.

`python scripts/check_content.py` reports `NOT GREEN: readiness incomplete` with exact gap counts until these
exist; `--structure` checks structure only.
