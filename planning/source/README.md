# backlog-v2 - the durable planning source

This directory is the written source of the PenniLogic backlog: new epics and tickets, strict
patches against issues that already exist, and the durable template for the board's own README.
`sync-backlog-v2.ps1` projects it onto
[PenniLogic Delivery](https://github.com/orgs/PenniLogic-old/projects/2). Nothing here is generated from
the board; the board is generated from here. Run `validate-backlog-v2.ps1` for current counts,
points, sprint load and Ready state across the eight repositories.

## Why a v2 source exists

The first planning pass lived inside `tickets-0N.ps1` scripts. That worked exactly once. Ticket text
was embedded in PowerShell here-strings, so it could not be diffed as data, validated before a run,
or re-applied without creating duplicates; and a script that has already been executed cannot tell
you what the board is *supposed* to look like. Three consequences followed: encoding corruption that
needed one-off repair scripts, epics created twice under slightly different titles, and dependencies
that existed as prose in a body but as nothing the board could act on.

v2 separates the two concerns:

* **The source is data.** ASCII-only JSON, one file per epic or area, every field schema-checked. A
  change to a ticket is a reviewable diff, not a re-run of an imperative script.
* **The tooling is idempotent.** Every item this source owns carries a stable marker, so a rerun
  updates in place. Running the sync twice produces the same board as running it once.

## Layout

| File | What it holds |
|---|---|
| `manifest.json` | File index with counts, Project vocabularies, execution calendar, forecast phase floors, planning capacity, Roadmap partial-span allowlist, and metadata contract |
| `epics.json` | The 15 new epics, E24 to E38, including experience strategy, design system, platform design and Design QA |
| `tickets-*.json` | New tickets, grouped by the epic or area that owns them |
| `patches-existing-tickets.json` | Strict edits to all 61 issues that already exist: 23 epics and 38 tickets. Ticket patches also enforce cold-start parity for Outcome, Scope, contracts, security, observability, tests, rollback, non-goals, parallel boundary and Definition of Done |
| `project-readme.md` | The durable copy of the board's README. The sync compares it with the live value and updates it only when it differs |
| `existing-items.json` | Offline snapshot of the 61 items already on the board as they were *before* this source. Reference data only - the sync never writes an item from this file, and the patches, not this snapshot, are what the board ends up with |
| `evidence/experience-coverage.json` | Schema-validated personas, journeys, flows, screens, component families, diagrams and design/implementation/QA ownership |
| `schema/*.schema.json` | JSON Schema for the manifest, epics, tickets, patches, lane proof, planning registry, immutable D6 handoff, D6 readiness evidence and snapshot |

The board's views live one directory up, in `../board-views.json`. That file is the durable view
specification - filters, layouts and visible fields - and `setup-views.ps1` is its sole writer.
`sync-backlog-v2.ps1` owns execution dates and rollups; `setup-forecast-roadmap.ps1` owns forecast
dates and confidence. The retired `setup-roadmap-and-points.ps1` performs no writes.

## Planning capacity

`manifest.capacity.pools` records three independent two-week pools on one 20-point clock:
Engineering has three lanes, Product Design and UX has six, and Quality Assurance has four.
Validation fails on pool overload, lane overlap, dependency timing or pool-specific review overload.

Capacity is a staffing assumption, not measured velocity. A smaller team or unavailable qualified
reviewer lengthens the plan; spare design capacity cannot hide an engineering or QA bottleneck.

The validator prints the exact scheduled, `Future` and `Backlog` totals on every run. The total is a
planning inventory and a lower bound, not a measured final size: work that has not been decomposed
contributes nothing to it. Mutable totals belong in validator output and the rendered Project README,
not in this prose.

## Ticket size

`manifest.ticket_size` records a **split threshold of 13 points**. Thirteen is the largest value the
estimate vocabulary allows, so it is an open-ended bucket rather than a measurement: a 13 means
thirteen *or more*. A ticket that size usually bundles several independently mergeable deliverables,
which contradicts the one-ticket-one-branch rule in the delivery protocol - a ticket that cannot be
one pull request cannot honour the protocol that governs it.

The rule is **not** that 13 is forbidden. It is that a ticket may not still be at the threshold when
its sprint starts:

- A threshold ticket in `Future` is fine. Splitting undated work is speculative, and the shape of the
  split is usually clearer once the decision records it depends on have landed.
- **Scheduling it into a numbered sprint is the moment the split falls due.** Every threshold ticket
  in a numbered sprint, whether native or legacy, needs an `unsplit_allowlist` entry naming the
  sprint, the date it must be split by, and which deliverables it currently bundles.

`validate-backlog-v2.ps1` fails when a threshold ticket in a numbered sprint has no entry, when an
entry's `split_by` has passed, when an entry plans to split *after* its own sprint has already begun,
or when the entry names a sprint the ticket is no longer in. A split is incomplete until dependencies,
estimates, reviewer load and `evidence/execution-lanes.json` are regenerated and valid. A stale entry -
one naming a ticket that has since been split or moved - is a warning, so the list shrinks rather than
accumulating.

Every run prints the outstanding count and the next date, so the debt is visible rather than
implicit:

```
unsplit    22 threshold ticket(s) still whole in numbered sprints; next split due 2026-09-25 (api#2)
```

The original api#2 deadline of 2026-09-21 was missed because setup delayed delivery and no sprint
had started. The coordinator proposed this finite reschedule to 2026-09-25 under the owner's
standing delivery direction; no fresh specific-date owner approval is recorded. It remains before
ledger implementation and well before Sprint 04 begins on 2026-10-19, and is not an automatic
renewal or a claim that decomposition is complete.

This is the same pattern as the `T-GOV-03` adoption exception: a temporary state is permitted only
for exact bootstrap paths and automatically stops when the active ruleset exists.

## Roadmap spans

An epic's `Start` and `Due` are derived from its children - the minimum child `Start` to the maximum
child `Due` - and never from the epic's own `Sprint`, which is a label for where the epic begins
rather than how long it lasts. An epic with no dated child has both dates cleared, so no bar is
drawn at all.

An epic that owns both dated and `Future` children shows only its **currently scheduled tranche**.
That is legitimate and easy to misread as the whole epic, so every such epic is listed in
`manifest.roadmap_partial_span.allowed` and the validator fails on one that is partial and unlisted,
or listed and no longer partial. A partial bar is therefore a decision on the record rather than an
accident nobody noticed.

## Complete forecast

Execution dates and forecast dates are deliberately different fields. `Start` and `Due` describe
only numbered sprints. `Forecast Start` and `Forecast Due` cover every ticket, while `Forecast
Confidence` distinguishes `Completed`, `Ready`, `Planned` and `Indicative`.

The forecast starts Future work after Sprint 18, waits for every declared dependency, applies the
phase floors in `manifest.forecast.phase_floor`, and packs work independently into the Engineering,
Product Design and UX, and Quality Assurance pools. Epic forecasts span all their child tickets. This gives owners and
investors a complete feature outlook without pretending post-MVP dates are committed sprints.

The numbered tranche also has a machine-checked capacity-pool packing proof at
`evidence/execution-lanes.json`. Validation fails on a missing assignment, estimate or sprint drift,
pool mismatch, lane overlap, out-of-capacity interval, same-sprint dependency inversion or reviewer overload.

## Experience coverage and frontend readiness

`manifest.experience` points to the canonical coverage registry and `T-DQA-12` readiness gate.
Every mapped Android, web and admin ticket derives the global gate plus its exact flow/screen design
dependencies from that registry. The validator rejects dangling IDs, one-way mappings, unused
components, platform mismatches, non-QA verifiers, unmapped frontend tickets and missing design
ownership. Every implementation ticket in the Android, web or admin repositories must be mapped as
frontend work or carry a reviewed non-frontend exclusion rationale, so omission from the registry
cannot silently bypass design. The sync writes derived dependencies into issue bodies and native
GitHub `blockedBy` edges, so the registry is an enforced plan rather than a reporting spreadsheet.

## Pre-v2 field authority

Every one of the 61 items that predate this source carries a patch, and every patch states
`set_fields.sprint` and `set_fields.status`. The schema and the validator both require it. An item
that restates neither keeps whatever the superseded delivery plan assigned, which is drift that
looks like a decision. Only the two genuinely dependency-free pre-v2 tickets - `infra#2` and
`infra#4` is the in-progress governance adoption; `infra#2` is blocked by `T-GOV-03`; every other
pre-v2 ticket and all 23 pre-v2 epics are `Backlog`.
`T-QA-07` is also `Ready`: physical-device procurement has no technical dependency, while its
sanitized corpus and compatibility-matrix work is separately blocked in `T-QA-12`.

## Field-option changes

Project 2 now matches the risk vocabulary in this source: `R2 Retention` was renamed to
**`R2 User retention`**, **`R15 Data lifecycle`** was added, and `None` was moved to the end. The
refreshed `../project-schema.json` contains the live option IDs. This tooling still deliberately
does not create, rename or delete fields or options during a backlog sync; any future vocabulary
change must be applied to the board first and followed by a schema-cache refresh.

## Board metadata

The board's short description and README are part of this source. The README is `project-readme.md`
verbatim. The short description is rendered at run time from
`manifest.project_metadata.short_description_template`, whose `{epics}` and `{tickets}` placeholders
are filled from the manifest counts plus the offline snapshot - validation rejects a template
containing a standalone number, because a hardcoded count is stale the moment an epic is added. Both
values are read before they are written, so a rerun that changes nothing performs no write, and both
go to the API as a JSON payload rather than a command-line argument.

## Epic patches

All 23 epics that already exist carry a patch. Every one of them restates the title in ASCII
(`[EPIC] E## - ...`). That is not cosmetic: the Project caches the title it saw when an item was
added, and the first planning pass wrote em dashes through a Windows CLI argument, so the cached
copies are both stale and mojibake. Rewriting all 23 repairs them and prevents a recurrence.
Epic patches use three lists the ticket patches do not - `add_scope`, `add_out_of_scope` and
`add_exit_criteria` - which append to the sections an epic body actually has. These three are the
only optional keys in the patch contract; every other key must be present even when empty.

## How to use it

```powershell
# Paths are relative to the root of this repository, PenniLogic/docs. There is no
# docs/ prefix from in here: this repository IS docs, and a path written as
# docs/planning-automation only resolves from a sibling checkout, not from a
# worktree of this repository.
cd planning-automation

# 1. Validate. Offline, no network, no third-party module. Do this after every edit.
pwsh -NoProfile -File .\validate-backlog-v2.ps1

# 2. Dry run. Reads GitHub, writes nothing, prints the full execution plan.
pwsh -NoProfile -File .\sync-backlog-v2.ps1 -DryRun

# 3. Apply. Only after the dry run reads correctly.
pwsh -NoProfile -File .\sync-backlog-v2.ps1 -Apply
```

Use `pwsh` (PowerShell 7), never `powershell` (5.1). The sync clears `GH_TOKEN`, `GITHUB_TOKEN` and
`GIT_CONFIG_PARAMETERS` for its own process and then asks the API which account the remaining
credentials belong to. If that is not `basiltt` it stops; it will not switch accounts for you:

```powershell
gh auth switch --user basiltt
gh auth refresh -h github.com -s project
```

Useful extras: `-KeepPayloads` keeps the JSON request bodies in `.sync-work` so a failed call can be
replayed by hand, and `-RefreshExisting` refreshes the pre-v2 baseline in `existing-items.json`.
Marker-owned v2 items are excluded so they are not counted twice after the first apply.

## Stable IDs

Every epic and ticket has a `stable_id` (`E24`, `T-GOV-03`, `T-SCA-API-01`). It is written into the
issue body as an HTML comment:

```
<!-- plan-id: T-GOV-03 -->
```

That marker, not the title, is what the sync matches on. It is why a rerun updates rather than
duplicates, why a ticket can be retitled without losing its identity, and why dependencies can be
written against ids that do not have issue numbers yet. **Never edit or remove a marker by hand, and
never reuse a stable id for different work.** Patched issues additionally carry
`<!-- plan-patch: ref hash -->`, which records that a specific patch has already been applied.

## Source-of-truth precedence

1. **This directory** is authoritative for everything it declares: titles, bodies, field values,
   dependencies, epic parentage and estimates. If the board disagrees, the board is wrong and the
   next sync corrects it.
2. **The board** is authoritative for what it alone knows: issue numbers, node ids, assignees,
   comments, and any status past `Ready` that a human has moved. The sync only forces a status down
   to `Backlog` when an item claims `Ready` while a declared blocker is still open.
3. **Native `blockedBy` edges** are authoritative for dependencies, and this source is authoritative
   for the items it owns. On a marked item, an edge that the source does not declare is stale and is
   deleted. On a patched or pre-existing item, only the edges a patch names in `remove_dependencies`
   are deleted; anything else undeclared is reported as drift, because a person may have recorded a
   dependency this source has never heard of.
4. **`project-schema.json`** is authoritative for field and option ids. It is a cache; refresh it if
   the project's fields change. This tooling sets field *values* and never creates, renames or
   deletes a field.
5. **`existing-items.json`** is a snapshot, not a target. It exists so validation can check schedule
   ordering with no network access. When it disagrees with the board, refresh it.

`Backlog` and `Future` are undated. Moving an item into either clears any `Start` and `Due` left
behind by an earlier sprint, so a stale date cannot read as a commitment nobody made.

Estimates live on tickets; epics carry `Rollup`, the sum of their children. Both totals are compared
on every sync, because inequality means a ticket is orphaned or parented twice.

## What this tooling does not do

It does not review anything. Validation checks that the plan is internally coherent - unique ids,
resolvable references, no cycles, no dependency scheduled after its dependent *using the post-patch
sprint of every existing item*, `Ready` only when nothing blocks it, no numbered sprint over the
planning capacity ceiling, every epic with a mixed dated and undated child set listed in the Roadmap
partial-span allowlist, every pre-v2 item restating its own `Sprint` and `Status`, and values the
board will actually accept. It cannot tell you whether a ticket is a good idea, whether the
acceptance criteria are the right ones, or whether the code that eventually closes it is correct. A
green validator and a clean apply mean the board matches the plan, nothing more. Code review, threat
modelling and the code-owner reviewer gate in `T-GOV-03` are separate controls and none of them are
replaced here.
