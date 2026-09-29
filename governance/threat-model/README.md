# Per-epic STRIDE threat-model refresh

Plan item `T-QA-14`, public issue [PenniLogic/docs#48](https://github.com/PenniLogic/docs/issues/48).

Every epic carries a dated threat-model refresh, with a named owner and the categories it reviewed,
before its first ticket starts, and again on a published cadence or when a named trigger fires. The
refresh is machine-readable so the pull-request check that `T-GOV-04` owns can gate an epic without
reading prose. This directory is the whole mechanism; nothing here implements a mitigation. A finding
is handed to the ticket that owns the work, or it stays open and blocks the epic.

The baseline model is `architecture/02-security-architecture.md` section 1. It had no entries for
billing forgery, entitlement tampering, AI service compromise, request forgery, prompt injection,
split manipulation or administrative identity compromise; `categories.json` adds those seven with
owners, so the model now has thirteen categories. The baseline document stays as research input and
is superseded, for the list of categories and their owners, by `categories.json`.

## Files

| Path | Contents |
| --- | --- |
| `categories.json` | The model: thirteen categories with owner, definition and baseline threat references; the accountable owners and review roles; the cadence; the refresh triggers. Bump `model_version` when a category is added. |
| `schema.json` | Draft-07 schema (strict subset) for `categories.json` (definition `model`) and every record (definition `record`). |
| `records/<epic>.json` | One record per epic, `E01` to `E38`, whether or not it has been refreshed. An epic with no refresh has an empty `refreshes` list; a missing file is an error, so an epic cannot be lost. |
| `STRIDE-refresh-template.md` | How to perform a refresh: rules, per-category prompts and the evidence each disposition must cite. |
| `../../scripts/check_threat_model.py` | The checker: schema, model rules, inventory completeness, record rules, staleness against an injectable clock, blocked epics, the observability summary. |
| `../../scripts/tests/test_threat_model.py` | The tests the ticket names, each proven to bite with a planted defect. |

## Owners in a single-owner organisation

PenniLogic has one GitHub owner (`basiltt`) and several independent AI sessions. The named owner of a
category is that accountable owner plus the independent review role that must review every finding
in the category: `review_role` in `categories.json` is a key of `review_roles` in
`.github/agent-policy.json`, which maps it to an agent profile in `PenniLogic/.github/agents`
(for example `security` to `pennilogic-security-reviewer`). The owner of a refresh is the same
account plus the session that performed it, recorded in `performed_by`. No human role is invented, and
a refresh record is not review approval: the pull request that adds it still needs the independent
reviews the repository policy requires.

## Cadence and triggers

The cadence is **12 weeks**. An epic that is still open 12 weeks after its latest refresh is
`stale`, and a stale record is treated as missing by any gate. The following named triggers force an
early refresh; each is recorded as the `trigger` of the refresh it caused:

| Trigger | When |
| --- | --- |
| `definition_of_ready` | The first refresh, before the epic's first ticket starts. |
| `cadence` | The latest refresh is 12 weeks old and the epic is still open. |
| `model_changed` | `categories.json` gained a category (`model_version` increased); every open epic whose latest refresh predates it is stale until the new category is reviewed. |
| `scope_changed` | A ticket added to or re-scoped inside the epic introduces a new trust boundary, data class, external party, AI capability, sharing path or money flow. |
| `decision_changed` | An architecture decision record the epic depends on is accepted, amended or superseded. |
| `security_event` | An incident, a penetration-test or red-team finding (`PenniLogic/docs#43`) or a disclosed dependency vulnerability touches a component the epic owns. |

## Definition of Ready

`product/03-delivery-plan.md` section 5 carries the item. In short: a ticket may start only when its
epic's record is `current` for `python scripts/check_threat_model.py --epic <epic>`, which means a
refresh exists, is within the cadence, was performed against the current model version, and has no
finding left without an owner.

## Epic status

The checker classifies every epic, in this order of precedence:

| Status | Meaning | Gate result |
| --- | --- | --- |
| `invalid` | The record or its latest refresh breaks a rule: schema, fewer categories than the model requires, a finding without the fields its status needs, a date after the clock, a handed-off finding pointing at an epic, a URL anywhere in the record. Invalid is never partially credited. | fails, and the repository check fails |
| `not_refreshed` | No refresh recorded. | fails, naming the epic and the owner who must record one |
| `stale` | Latest refresh older than the cadence, or performed against an older `model_version`. Treated as missing. | fails |
| `blocked` | Latest refresh is current but at least one finding is `open` (no owning ticket). | fails, naming the unowned findings |
| `current` | Valid, within cadence, current model version, every finding closed or handed off. | passes |

## Findings and hand-off

A finding is either `handed_off` to an existing public ticket by identifier (`PenniLogic/<repo>#N`),
`closed` with a resolution, or `open`. An open finding is honest: it says the work has no owner yet.
The refresh that raises it fails the gate for that epic until a ticket exists and the record is
updated, which is the intended pressure. A finding may not be handed to an epic issue, to a historical
`PenniLogic-old` number, or to a ticket whose scope does not cover it; the second and third are
review matters, the first is enforced. When a new refresh is recorded, restate any earlier finding that
is still relevant; only the latest refresh is evaluated.

## Record schema (for the T-GOV-04 check)

`schema.json` is authoritative. The check should read `records/<epic>.json`, take the last element of
`refreshes`, and apply the status rules above with `cadence_weeks` and `model_version` from
`categories.json`; or simply run `python scripts/check_threat_model.py --epic <epic> [--today DATE]
[--json]` and use the exit code. Field summary:

| Field | Type | Meaning |
| --- | --- | --- |
| `schema_version` | `1` | Record schema version. |
| `epic` | `E[0-9]{2}` | Epic identifier; equals the file name. |
| `title` | string | Epic title without the `[EPIC] Exx -` prefix. |
| `issue` | `PenniLogic/docs#N` or `null` | Public epic issue. `null` requires `note` (currently only `E31`, which has no public epic issue). |
| `owner.accountable` | GitHub login | Who must record a refresh; one of `accountable_owners` in the model. |
| `refreshes[]` | array | Chronological. Empty means not refreshed. |
| `refreshes[].date` | `YYYY-MM-DD` | Calendar date of the refresh; may be at most one day after the checking clock. |
| `refreshes[].trigger` | trigger id | One of `refresh_triggers` in the model. |
| `refreshes[].model_version` | integer | The `categories.json` version reviewed; determines the required category set. |
| `refreshes[].performed_by` | object | `accountable` (login), `session` (`copilot-session:<uuid>` or `github:<login>`), `role` (`pennilogic-*`). |
| `refreshes[].scope` | string | What was in scope, including trust boundaries. |
| `refreshes[].tickets_in_scope[]` | `PenniLogic/<repo>#N` | Child tickets considered. |
| `refreshes[].sources[]` | string | Documents, decision records and issues read. |
| `refreshes[].categories[]` | object | Exactly the required categories, each with `id`, `disposition` (`controlled`, `accepted`, `finding`, `not_applicable`), `analysis`, `evidence[]` (required for `controlled` and `accepted`) and `findings[]` (required for `finding`; may cross-reference a finding whose primary category differs). |
| `refreshes[].findings[]` | object | `id` (`Exx-Fnn`, prefix equals the epic), `category` (a reviewed category that lists it), `severity` (`critical`, `high`, `medium`, `low`), `title`, `attack_path`, `recommended_control`, `status` (`handed_off` with `owner_ticket`; `closed` with `resolution`; `open` with neither). |

## Running the check

```text
python scripts/check_threat_model.py                  validate the model, every record and these documents; print the summary
python scripts/check_threat_model.py --epic E01       exit 0 only if E01 is current (the Definition of Ready gate)
python scripts/check_threat_model.py --today 2027-01-15 --json
```

The summary line counts epics that are current, stale, blocked, not refreshed and invalid, then lists
every non-trivial epic with its reason and every unowned finding with the owner who must find it a
ticket. That is the observability the ticket asks for: the state of the model without opening the
board. Exit code 1 in the default mode means invalid data; a blocked or stale epic is reported, not a
data error, because the record is telling the truth. `python -m unittest discover -s scripts/tests`
runs the tests in CI; the check itself is run by the developer and, once `T-GOV-04` exists, by the
pull-request gate.

## Rollout and rollback

The template, the thirteen categories and the records land first, then the Definition of Ready item,
then the automated pull-request check in `T-GOV-04` (infra), which has no public issue yet. Rolling
back removes the automated check; the records already written remain valid evidence. Adding a
category is a `model_version` bump and makes every earlier refresh stale, which is the intended
effect; it never makes a record invalid.

## What this is not

Not the penetration test or red-team scenarios (`PenniLogic/docs#43` owns those), not a mitigation
of anything, not a claim that a handed-off finding is fixed, and not a substitute for the independent
security, privacy, money and QA reviews the repository policy requires on the pull request that
changes any file here.
