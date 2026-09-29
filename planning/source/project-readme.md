# PenniLogic Delivery

This board is generated. Nothing here is edited by hand and expected to survive: the durable source
is `planning-automation/backlog-v2` in the `PenniLogic/docs` repository, and `sync-backlog-v2.ps1`
projects it onto this project. If the board and the source disagree, the source wins and the next
sync says so.

## What is on the board

- **{epics} epics.** 23 already existed (E01 to E23, in `PenniLogic/docs`); 15 were added by the v2 source
  (E24 platform and reliability, E25 quality and release assurance, E26 architecture decision gates,
  E27 launch-blocking compliance floor, E28 advanced ingestion, E29 account aggregator readiness,
  E30 globalization, E31 program governance, E32 server sync, E33 experience strategy/research,
  E34 design system/content, E35 Android design, E36 web design, E37 admin design and E38 Design QA).
- **{tickets} implementation tickets.** {existing_tickets} predate the v2 source and are patched in place; {new_tickets} are new.
  Every ticket names one primary repository, one component and one owning epic.
- **Eight repositories.** admin, ai-service, android, api, contracts, docs, infra, web.

Estimates live on tickets. Epics carry `Rollup`, the sum of their children, so an epic with a zero
rollup owns no work and is a planning error rather than a small epic.

**{points} points is a visible planning inventory and a lower bound, not a measured final size.** It is
the sum of the estimates now written down - {new_points} on the {new_tickets} new tickets plus
{existing_points} on the {existing_tickets} that
predate them - and work that has not been decomposed yet contributes nothing to it. It is not a
commitment, not a release date and not a velocity forecast.

## Capacity and what the dates mean

Sprint assignments use three independent pools on the same two-week clock: **Engineering** has three
20-point lanes, **Product Design and UX** has six, and **Quality Assurance** has four. Each pool has
its own review cap and the validator rejects pool overload, lane overlap, dependency inversion and
review overload.

Capacity is a staffing assumption, not velocity evidence. Fewer people or missing qualified
reviewers lengthen the schedule; design or QA capacity never disguises an engineering bottleneck.

{scheduled_points} points across {scheduled_tickets} tickets sit in the numbered plan. Sprint 16 is
the private-beta gate; Sprints 17-18 remain explicit contingency before indicative forecast work.
{future_points} points across {future_tickets} `Future` tickets remain deliberately outside numbered
sprint commitments. The remaining {backlog_points} points across {backlog_tickets} `Backlog` tickets
are unscheduled prerequisites or completed external work retained for traceability.

`Start` and `Due` remain execution-tranche dates. `Forecast Start`, `Forecast Due` and `Forecast
Confidence` are a separate complete outlook: numbered work is `Planned`, startable work is `Ready`,
closed work is `Completed`, and post-MVP work is dependency-aware but explicitly `Indicative`.
Forecast dates do not move a ticket out of `Future` and do not create a sprint commitment.

## Pre-v2 field authority

All 61 items that predate this source carry a strict patch, and every one of those patches restates
`Sprint` and `Status` explicitly. Anything left unstated would keep the value the superseded delivery
plan assigned, which is exactly the drift this source exists to remove.

## The HOLD gate

An item is on HOLD - `Status` stays `Backlog` - while anything it declares a dependency on is still
open. This is enforced, not aspirational: the sync reads native GitHub `blockedBy` edges and forces
`Ready` back down to `Backlog` when a blocker is open. Four program-level holds sit above the
per-item rule:

1. **Architecture holds contracts.** No schema or generated type lands before the decision record
   that fixes its shape is accepted (E26). Money wire format, category model, ledger currency,
   encryption scope and grant-mediated cross-user reads, authentication and relying-party identifier,
   the administrative boundary and its audit streams, shared-data erasure, AI egress, and the
   entitlement and quota model are all decisions, not implementation details.
2. **Security holds real data.** No environment holds real user data before the data protection
   floor is live in it: envelope encryption, blind index, row-level security and the audit event
   service (E19), on infrastructure that has a proven restore and an alert that reaches a human
   (E24).
3. **Compliance holds beta.** The launch-blocking compliance floor (E27) - consent ledger, purpose
   registry, data-principal rights, retention jobs, pre-onboarding consent, the age gate, the
   third-party component inventory and the data safety declaration - must be closed before beta.
   E20 keeps only the post-beta work: counsel review, role and transfer registers, payment
   self-assessment and global readiness.
4. **Design holds frontend.** Every Android, customer-web and admin frontend ticket derives its exact
   flow-design dependencies plus `T-DQA-12` from the experience coverage registry. Repository
   scaffolds and backend work may proceed after agent governance closes, but no mapped frontend
   becomes Ready before the CDO D6 gate and its platform handoff close.

## What Ready means

`Ready` is a claim that nothing is in the way: no open blocker, no unresolved dependency, no
decision still pending. It is not a priority signal and not an intention to start soon. Anything
else is `Backlog`. During agent-governance adoption exactly **one implementation item** is
independently `Ready`; no epic is currently `Ready`:

`T-QA-07`.

`T-GOV-03` and `infra#4` are `In Progress` outside the numbered sprint while the agent profiles,
generated repository policy and rulesets are adopted. `T-GOV-01`, `T-GOV-02`, all six repository
scaffolds and `infra#2` depend on that gate and remain `Backlog`. `T-QA-07` is the independent
physical-device procurement item; corpus governance and the wider compatibility matrix remain in
`T-QA-12`.

**E31 is `In Progress`.** `T-EXT-01` is `Done`: the organisation was upgraded to
GitHub Team on 2026-09-02, a temporary private-repository pull request proved active rulesets,
required review and a required status check, and every fixture was removed. `T-GOV-03` is therefore
dependency-free and `In Progress`.

The remaining statuses behave normally: `In Progress`, `In Review`, `In Test`, `Blocked`, `Done` are
moved by people, and the sync does not overwrite a human's forward progress. The only status the
sync forces is `Ready` down to `Backlog`.

## Parallel lanes

The dependency graph is a DAG with no schedule inversions, so several lanes run concurrently:

| Lane | Owns | Gated by |
|---|---|---|
| Governance | E31 | nothing; the GitHub Team capability prerequisite is complete |
| Foundations | E01, E24 | governance |
| Architecture gates | E26 | governance |
| Contracts and domain | E02, E04, E32 | architecture gates |
| Debt product | E05, E06 | contracts |
| Ingestion | E08, E09, E10, E11, E28 | contracts, platform |
| Security and compliance | E19, E27 | architecture gates, platform |
| Identity and recovery | E03 | the auth decision record |
| Quality and release | E25 | test strategy; its tickets span the whole numbered schedule and beyond |
| Experience strategy and research | E33 | governance, product truth and research operations |
| Design system and content | E34 | experience direction, state taxonomy and research |
| Android, web and admin design | E35, E36, E37 | IA, shared system and platform prototypes |
| Independent Design QA | E38 | platform designs, accessibility, usability and coverage evidence |
| Money and AI | E14, E17, E18 | quota contract, entitlement record, crypto and AI egress records |
| Sharing | E15, E16 | shared-data erasure record, grant-mediated read predicate |
| Trust controls | E23 | compliance floor, privacy contract and design readiness; Sprint 16 for Android beta surfaces |
| Web, goals, retention, support | E12, E21, E22, E07, E13, E20 | `Future`; no numbered sprint is claimed for them |

Cross-lane work is expressed as ticket-level dependencies, never as an epic-level block, so one
unscheduled epic cannot stall a lane that does not actually need it.

## Views

| View | Filter | What it answers |
|---|---|---|
| Current Sprint | `-kind:Epic start:<=@today+14d due:>=@today` | Ticket windows overlapping the next fourteen days. Self-updating and includes the next sprint before it starts |
| Ready Queue | `status:Ready -kind:Epic` | What may be started right now. Self-updating: the sync maintains `Status` |
| Review Queue | `status:"In Review" -kind:Epic` | The independent-review bottleneck, including reviewers and linked pull requests |
| Test Queue | `status:"In Test" -kind:Epic` | Work handed from implementation review into environment or independent verification |
| Design Pipeline | `label:design -kind:Epic` | Product design work across research, systems and platform squads |
| UX Research | `label:ux-research -kind:Epic` | Research plans, evidence and finding disposition |
| Screen Flow Coverage | `label:experience-coverage -kind:Epic` | Registry and independent coverage checks |
| Design QA | `label:design-qa -kind:Epic` | Usability, accessibility, abuse, conformance and UAT gates |
| Design Handoffs | `label:handoff -kind:Epic` | D6 artifacts that unblock frontend work |
| Blocked Queue | `status:Blocked -kind:Epic` | Work that became blocked after starting and needs intervention |
| Epic Rollups | `kind:Epic` | Epic sizing, progress, execution dates, full forecast dates and confidence |
| Delivery Roadmap | `-kind:Epic` | Every implementation ticket on its complete forecast timeline |
| Feature Outlook | `kind:Epic` | Owner and investor view: when each feature is forecast ready, with indicative dates clearly marked |
| Sprint Board | `-kind:Epic` | All non-epic work by status |
| Risk Coverage | `-risk:None` | Every item that claims a risk |
| Quality Gates | `perspective:Test,QA,Security,Compliance` | The verification surface |

The view definitions are durable data in `planning-automation/board-views.json`, not hand-made board
settings.

## Risks

`Risk` is a single-select on every item. R1 SMS permission, R2 User retention, R3 Breach, R4 Insider
risk, R5 Scope, R6 Parser rot, R7 AI cost, R8 Sharing abuse, R9 Advice boundary, R10 Wrong numbers,
R11 Prompt injection, R12 Billing economics, R13 Split conversion, R14 Key-person, R15 Data
lifecycle. Every risk has at least one owning item; a risk with no owner is a gap, and closing those
gaps is why R12 to R15 exist.

`R2 Retention` was renamed to `R2 User retention` because it read ambiguously against *data*
retention and was being applied to erasure and retention-period work, which is a different failure
class. That work now carries `R15 Data lifecycle`; `R2 User retention` stays with the activation and
retention programme.

## Source of truth

- Durable source: `planning-automation/backlog-v2` in the `PenniLogic/docs` repository -
  https://github.com/PenniLogic/docs/tree/main/planning-automation/backlog-v2
- Tooling and runbook: `planning-automation/README.md` and
  `planning-automation/backlog-v2/README.md`, both inside `PenniLogic/docs`
- Validate offline: `pwsh -NoProfile -File .\validate-backlog-v2.ps1`
- Preview: `pwsh -NoProfile -File .\sync-backlog-v2.ps1 -DryRun` (reads only, writes nothing)
- Apply: `pwsh -NoProfile -File .\sync-backlog-v2.ps1 -Apply`
- Forecast preview: `pwsh -NoProfile -File .\setup-forecast-roadmap.ps1`
- Forecast apply: `pwsh -NoProfile -File .\setup-forecast-roadmap.ps1 -Apply`

Every managed item carries `<!-- plan-id: ID -->` in its body. That marker, not the title, is what
the sync matches on. Do not edit or remove it by hand.
