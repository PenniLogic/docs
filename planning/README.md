# planning

The preserved PenniLogic delivery backlog, and the rules for any script that reads
or writes the GitHub Project that tracks it. Everything here is product/design
source and historical planning evidence; nothing in it is a release approval, an
implementation claim or a current-readiness statement (see [MIGRATION.md](../MIGRATION.md)).

## Layout

| Path | What it holds | Checked by |
|---|---|---|
| `backlog.json` | The 2026-09-29 snapshot of the retired `PenniLogic-old` delivery board: 427 preserved cards, each with its legacy identity (`legacy_id`, `source_repository`, `source_number`, `source_url`), title, kind, `legacy_status`, sprint, priority, estimate and component. Issue discussions were not copied. | `scripts/check_docs.py` validates `schema_version`, a unique non-empty `legacy_id` per card, a title, a `PenniLogic-old` `source_url` (provenance), a known `legacy_status`, and `item_count` equal to the number of cards. `scripts/tests/test_docs.py` exercises the duplicate-identity, count, provenance and status rejections. |
| `source/` | The accepted backlog-v2 product specification imported from the private organization: `manifest.json`, `epics.json`, one `tickets-*.json` file per epic or area, `patches-existing-tickets.json`, `existing-items.json`, `evidence/execution-lanes.json`, `evidence/experience-coverage.json`, and the JSON Schemas in `source/schema/`. `source/README.md` and `source/project-readme.md` are the preserved runbook and board README of that era. | `scripts/check_docs.py` parses every `*.json` under `source/`. Schema conformance is not re-validated in this repository; the validator that did so was private-era tooling. |

Historical `Done` statuses in `backlog.json` are original evidence, not new public
acceptance.

### Tooling named inside `source/` is not part of this repository

`source/README.md` and `source/project-readme.md` refer to a `planning-automation/`
directory and its PowerShell scripts (`sync-backlog-v2.ps1`, `validate-backlog-v2.ps1`,
`setup-views.ps1`, `setup-forecast-roadmap.ps1`, the first-pass `tickets-0N.ps1` scripts, the
retired `setup-roadmap-and-points.ps1` stub) plus `board-views.json` and
`project-schema.json`. None of those files were imported. The two documents are kept
verbatim as history: do not follow their run instructions here and do not recreate
the scripts from them. The scripts that actually operated on the public board are
described under [Current example](#current-example-the-2026-09-29-publication) and
are not committed either; checking them in is a separate decision.

## The trap: GraphQL connections truncate silently

A GitHub GraphQL connection returns at most the `first:` you asked for. When the
population is larger, there is no error and no warning, just a shorter list. A read
that stops at one page therefore yields a confident wrong answer, and a writer that
acts on such a read destroys data. Two real incidents in the old organization:

1. **A false "not on the board" report.** While verifying a cross-session governance
   handoff, a single non-paginated `items(first:100)` read was run against the delivery
   board, which then held 404 items. Only page 1 came back, which produced the confident
   conclusion that a specific issue was not on the board. That conclusion was reported
   to another session and had to be formally retracted: the issue was on page 2 with
   `Status = Blocked`.
2. **Truncated reads feeding writes.** The retired `setup-roadmap-and-points.ps1`
   paired `items(first:100)` with `issues(first:60)` and then wrote epic `Rollup`
   values computed from that read. Once the private-era docs repository grew past 60
   issues (141 when the original ticket was written), every epic beyond the first page
   would have resolved to zero children and had `Rollup = 0` written over a correct
   value. The script was retired to a throwing stub by a later pass, so the live risk
   was gone, but the pattern is cheap to reintroduce; that is why these rules are
   written down.

The original private-era ticket
([PenniLogic-old/docs#176](https://github.com/PenniLogic-old/docs/issues/176), carried
here as [docs#72](https://github.com/PenniLogic/docs/issues/72)) also recorded an
audit of the `.ps1` scripts of that time. The audit is historical evidence about
tooling that no longer exists here and is not repeated.

## Rules for planning readers and writers

### Rule 1: drain before you decide, and drain before you write

Any GraphQL connection whose result feeds a decision, a report or a mutation is
paginated until exhausted, and the number of nodes fetched is compared with the
connection's `totalCount`:

```graphql
query($id: ID!, $after: String) {
  node(id: $id) { ... on ProjectV2 {
    items(first: 100, after: $after) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { id type isArchived }
    }
  } }
}
```

Loop while `pageInfo.hasNextPage` is true, passing `pageInfo.endCursor` as `after`.
When the loop ends, record `totalCount` next to the fetched count in the run's
output or receipt, and prefer a hard assertion that they are equal. A script that
cannot show both numbers has not proven that it read the whole population.

### Rule 2: nested connections get a `totalCount` guard

A connection nested inside another one (`fieldValues` inside `items`, `subIssues`
inside `issues`) cannot be paged cheaply from the parent query: the parent cursor
advances items, not the inner list. Request the nested `totalCount` alongside the
nodes and fail loudly when it exceeds the requested `first:`:

```graphql
fieldValues(first: 50) {
  totalCount
  nodes { __typename }
}
```

```python
if values["totalCount"] > len(values["nodes"]):
    raise RuntimeError(f"item {item_id}: {values['totalCount']} field values, "
                       f"only {len(values['nodes'])} fetched")
```

Re-measure the headroom whenever a Project field is added or an epic gains
children: a `first:` that was generous last month is not a permanent fact.

### Rule 3: guard the population before mutating

Before the first write, assert that the population is exactly what the run was
planned against: the expected count, the expected identities, and the expected
target repository or Project. A count that differs means the plan or the board has
moved, and the correct response is to stop and re-plan, not to proceed with whatever
came back. The 2026-09-29 publication refused to start any phase unless exactly 349
active drafts were present (see below).

### Rule 4: verify by simulation and read-back, never by re-running a writer

A writer is proven before it runs by exercising its transformation offline against
the real inputs with no network calls, and after it runs by reading the result back
and diffing it against a snapshot taken before the run. Re-running the writer "to
see if it works" is not verification: it either repeats the mutation or, if the
writer is idempotent, proves only idempotence. Keep the before snapshot, the after
snapshot and the diff receipt with the run.

### REST rule: `per_page=100` until a short page

REST list endpoints page too. Request `per_page=100` and keep incrementing `page`
until a response comes back empty or shorter than 100. On `repos/{owner}/{repo}/issues`
also skip entries that carry a `pull_request` key, because that endpoint lists pull
requests as issues.

## Current example: the 2026-09-29 publication

The scripts that published the preserved backlog as public repository issues,
`snapshot_project.py` and `publish_issues.py`, are retained in the coordinator's
session artifacts (`issue-publication-20260929`), not in this repository. Read
against the rules above:

| Rule | What the scripts do | Evidence |
|---|---|---|
| 1 | `snapshot_project.py` pages `items(first: 100, after: $after)` with `totalCount` and `pageInfo { hasNextPage endCursor }` until `hasNextPage` is false, then writes `total_count` and `fetched` side by side. `publish_issues.py` reuses the same query to re-drain the Project in its `verify` phase. | Pre-publication snapshot: `total_count` 349, `fetched` 349 (all 349 unarchived drafts). Post-publication read-back: 352 items, all issues. The equality is recorded, not yet asserted. |
| 2 | Not implemented. Neither the `fieldValues(first: 50)` read inside `items` nor the `fields(first: 60)` read requests `totalCount`; both rely on measured headroom (next section). | See [Known headroom](#known-headroom-rule-2-not-yet-enforced). |
| 3 | `publish_issues.py` builds its draft map from the before snapshot in its constructor, requires a source-identity line in every draft, rejects two drafts for one source identity, and raises `Expected 349 active drafts, found N` otherwise, so no phase (preflight, convert, create, update, project, link or verify) starts against a different population. Every phase first verifies the operating login, user id and organization id; before each conversion it re-reads the live item, checks it still belongs to the expected Project with the same content id, title and complete original body, and after conversion checks the created issue landed in the expected repository by numeric id with identical title and body. | Receipt methods: 349 `converted_draft`, 51 `created_direct`; 400 included records, 400 live issues with source identity. |
| 4 | Offline tests (`test_publish_issues.py`) run the body transformation for every draft against a synthetic mapping with no GitHub calls, including the idempotence check that transforming an already-transformed body changes nothing. `verify` re-lists every issue with REST paging, checks each included record has exactly one live issue whose body still contains the complete original specification, re-reads every expected parent and blocked-by edge, checks the migrated graph is acyclic, re-drains the Project and diffs the field values of every converted item against the before snapshot, then writes `publication-receipt.json` and `project-items-after.json`. | 306/306 parent edges and 1497/1497 blocked-by edges verified, no cycles, 0 problems. Field diff: 343 of 349 converted items identical; the 6 differences were the six Sprint 01 items whose `Status` had been deliberately moved from `Backlog` to `In Progress` between the snapshots, each reported with its before and after values rather than hidden. |
| REST | `list_live_issues` pages `repos/{repo}/issues?state=all&per_page=100&page=N` until a batch is empty or shorter than 100 and skips pull requests; a `paged()` helper does the same for `sub_issues` and `dependencies/blocked_by`. | Used for the 400-issue inventory and the edge read-back above. |

### Known headroom (Rule 2 not yet enforced)

Neither script requests a nested `totalCount`, so the two nested reads below rely on
measured headroom rather than a guard. Both measurements come from the retained
snapshots, not from a live query:

| Read | Requested | Defined / observed | Margin |
|---|---|---|---|
| `fieldValues(first: 50)` inside `items` | 50 | 29 fields defined on the Project; at most 17 value nodes on any item in the pre-publication snapshot (349 drafts), at most 20 in the post-publication read-back (352 issues, which carry built-in values such as `Labels` and `Repository` that drafts do not). | 30 spare at the post-publication read-back. The rise from 17 to 20 after conversion is exactly why the number is re-measured, not remembered. |
| `fields(first: 60)` on the Project | 60 | 29 fields defined. | 31 spare; a single unpaged read with no `totalCount`. |

`subIssues` inside `issues` is not read by these scripts; parent and blocked-by
edges are read through the paged REST endpoints. Adding the `totalCount` guard to
both nested reads is the outstanding change if the scripts are ever committed to
this repository (a separate decision; see docs#72).

## Before running any planning writer

- Verify the operating account, organization id and repository or Project id in the
  same process, before the first read.
- Drain every top-level connection; record `totalCount` against fetched (Rule 1).
- Request `totalCount` on every nested connection and fail when it exceeds `first:`
  (Rule 2).
- Assert the expected population count and identities before the first mutation
  (Rule 3).
- Take a before snapshot; prove the transformation offline; after the run, re-drain,
  diff against the snapshot and keep the receipt (Rule 4). Never re-run the writer as
  a test.
- Page REST with `per_page=100` until a short page.

A green run of these checks proves that the board matches the plan. It does not
review the plan, and it is not product or release acceptance.
