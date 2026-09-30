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
finding left without an owner; and the ticket itself is listed in that refresh's `tickets_in_scope`,
which `python scripts/check_threat_model.py --ticket PenniLogic/<repo>#N` checks. A ticket added to
an epic after its refresh, or one that introduces a new data class, trust boundary, external party,
AI capability, sharing path or money flow, needs a `scope_changed` refresh that lists it. A stale
refresh or an invalid record blocks Ready for every ticket in the epic.

The gate runs against the runner's clock. `--today` exists for tests and what-if runs only; a
workflow that implements the gate must never forward a value a pull request controls into `--today`,
because a caller-supplied clock can un-stale any record and moves the one-day future tolerance with
it.

## Epic status

The checker classifies every epic, in this order of precedence:

| Status | Meaning | Gate result |
| --- | --- | --- |
| `invalid` | The record or its latest refresh breaks a rule: schema, fewer categories than the model requires, a finding without the fields its status needs, a `closed` finding whose resolution names nothing checkable, evidence that names nothing checkable, an analysis, scope, attack path or control under 40 characters, a blank string, a `definition_of_ready` refresh with no ticket in scope, personal data in scope with no `data_flows`, a date after the clock, a handed-off finding pointing at an epic, a URL, endpoint or key shape anywhere in the record. Invalid is never partially credited. | fails, and the repository check fails |
| `not_refreshed` | No refresh recorded. | fails, naming the epic and the owner who must record one |
| `stale` | Latest refresh older than the cadence, or performed against an older `model_version`. Treated as missing. | fails |
| `blocked` | Latest refresh is current but at least one finding is `open` (no owning ticket). | fails, naming the unowned findings |
| `current` | Valid, within cadence, current model version, every finding closed or handed off. | passes |

`controlled` means a control exists today and the evidence names where; a control that a ticket will
build is recorded as a `finding` handed to that ticket, so the disposition field never says
"controlled" about something that does not yet exist. `accepted` means the risk is knowingly carried
and the evidence names the decision that accepts it.

## Findings and hand-off

A finding is either `handed_off` to an existing public ticket by identifier (`PenniLogic/<repo>#N`),
`closed` with a resolution that names a public ticket, a decision record, a repository path or a test
(so a closure is something a reader can go and check, never a bare sentence), or `open`. An open
finding is honest: it says the work has no owner yet.
The refresh that raises it fails the gate for that epic until a ticket exists and the record is
updated, which is the intended pressure. A finding may not be handed to an epic issue, to a historical
`PenniLogic-old` number, or to a ticket whose scope does not cover it; the second and third are
review matters, the first is enforced. When a new refresh is recorded, restate any earlier finding that
is still relevant; only the latest refresh is evaluated.

## Data subjects and flows

Every refresh whose `information_disclosure` review is anything but `not_applicable` inventories the
personal data the epic touches in `data_flows`: the data class, its subjects (users, household
members, counterparties, research participants, operators, contributors), the purpose-registry
entry, consent record or decision that permits it or the ticket that will create one (compliance
O-1), retention and its source (O-4), the erasure path including derived and multi-subject copies
(O-2, O-4, O-13), age-gate conditioning (O-6) and every processor or cross-border destination (O-7).
The checker enforces presence, not adequacy: the privacy review role reads the entries.

## Record schema (for the T-GOV-04 check)

`schema.json` is authoritative. The check should read `records/<epic>.json`, take the last element of
`refreshes`, and apply the status rules above with `cadence_weeks` and `model_version` from
`categories.json`; or simply run `python scripts/check_threat_model.py --epic <epic>` and
`python scripts/check_threat_model.py --ticket PenniLogic/<repo>#N [--epic <epic>]` against the
runner clock and use the exit codes (`--json` for the full inventory). Field summary:

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
| `refreshes[].scope` | string | What was in scope, including trust boundaries; at least 40 characters. |
| `refreshes[].tickets_in_scope[]` | `PenniLogic/<repo>#N` | Child tickets considered; non-empty for a `definition_of_ready` refresh. The `--ticket` gate reads this list. |
| `refreshes[].sources[]` | string | Documents, decision records and issues read. |
| `refreshes[].data_flows[]` | object | Personal-data inventory: `data_class`, `subjects[]` (enumerated), `purpose_ref`, `retention`, `erasure_path`, `children`, `processors[]`. Non-empty unless `information_disclosure` is `not_applicable`. |
| `refreshes[].categories[]` | object | Exactly the required categories, each with `id`, `disposition` (`controlled`, `accepted`, `finding`, `not_applicable`), `analysis` (at least 40 characters), `evidence[]` (required for `controlled` and `accepted`; every item names a public ticket, `ADR-nnn`, a repository path or a `test_` name) and `findings[]` (required for `finding`; may cross-reference a finding whose primary category differs). |
| `refreshes[].findings[]` | object | `id` (`Exx-Fnn`, prefix equals the epic), `category` (a reviewed category that lists it), `severity` (`critical`, `high`, `medium`, `low`), `title`, `attack_path` and `recommended_control` (at least 40 characters each), `status` (`handed_off` with `owner_ticket`; `closed` with a `resolution` of at least 40 characters naming a checkable reference; `open` with neither). |

## Running the check

```text
python scripts/check_threat_model.py                       validate the model, every record and these documents; print the summary
python scripts/check_threat_model.py --epic E01            exit 0 only if E01 is current (the epic gate)
python scripts/check_threat_model.py --ticket PenniLogic/api#82
                                                           exit 0 only if a current refresh lists that ticket (the ticket gate)
python scripts/check_threat_model.py --today 2027-01-15 --json
                                                           what-if run against another clock; never a gate
```

The summary line counts epics that are current, stale, blocked, not refreshed and invalid, then lists
every non-trivial epic with its reason and every unowned finding with the owner who must find it a
ticket. That is the observability the ticket asks for: the state of the model without opening the
board. Exit code 1 in the default mode means invalid data; a blocked or stale epic is reported, not a
data error, because the record is telling the truth. `python -m unittest discover -s scripts/tests`
runs the tests in CI; the check itself is run by the developer and, once `T-GOV-04` exists, by the
pull-request gate.

What the content rules do not catch, stated so nobody relies on them for more: a hand-off ticket's
existence, state and scope are not checked offline (a closed ticket or a pull-request number passes
the pattern; review verifies them); the endpoint and key patterns are shapes, so an unusual token
format or a hostname without a dot passes them and `check_repository.py` catches only GitHub token
shapes in committed files; and the reference rule proves an evidence item points somewhere, not that
the place says what the item claims.

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
