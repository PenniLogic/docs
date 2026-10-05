# Design operations and decision rights

**Source:** [T-UXR-01 / docs#64](https://github.com/PenniLogic/docs/issues/64).
**Contract:** [design-gates.json](design-gates.json), version `1.0.0`, with
[design-gates.schema.json](design-gates.schema.json).
**Status:** source implementation proposed for independent review, not current rights approval,
research permission, live Figma provisioning or full issue acceptance.

## 1. Authority and current operating boundary

`basiltt` is the actual accountable product owner. The owner's 2026-10-05 delegation permits
technical/design decisions and implementation while the owner is unavailable; Root context
`5a1e7d78-6f81-4abb-9ab5-d8b1648df012` is the delegated decision coordinator. It is not a human
Chief Design Officer, legal officer, second account or extra vote. Discipline names below describe
responsibilities, not staffed human posts. The author of this source cannot approve these rights.

Controlled Git source is the **current artifact and decision workspace**. Work is isolated by
checkout and issue-sized ownership; candidate versions remain unapproved until the accepted
[delivery policy](DELIVERY.md) is met. No current design approval or appointment is seeded in the
data. Root must record each actual independent context, runtime, role, exact artifact scope,
assignment evidence and expiry before a candidate can rely on its review.

Figma ownership, account access, feature availability and recovery have **not** been verified.
Shared-file creation, editing and publishing remain disabled. The topology below is a complete
specification, not a claim that its project, files, branches, libraries or grants exist. No paid
feature, external share, permission change or automatic remote control is authorized by this record.
Live enablement needs separately reviewed evidence and an explicit source-policy revision; changing
a local flag or passing the tabletop is insufficient.

Participant contact is also disabled. Technical/design delegation is neither consent nor qualified
legal advice. In particular, the research operations consumer must keep no-contact/start gates
closed until its actual UX Research, Privacy, Legal, Accessibility and controlled-store owner and
verifier assignments, lawful protocol, consent and store controls are evidenced. A hypothetical
agent named Legal does not satisfy qualified legal review. Missing operational prerequisites do
not prevent drafting and validating safe source contracts.

## 2. RACI and accountable artifact ownership

Each class has one scalar accountable role, one or more responsible roles and at least one verifier
outside both accountable and responsible roles. The JSON is the full RACI, including consulted and
informed roles. Unknown classes, duplicate identifiers, missing accountables, unknown approvers or
self-verifiers fail lint. An artifact instance also names all producing contexts, including authors
of consumed evidence; aliases or the same account with different role labels do not make its author
independent. Scope-specific assignments may share an account but not verification context.

| Role identifier | Responsibility and limit |
| --- | --- |
| `product_owner` | Actual owner basiltt; D0/D9 product decisions can be attributed to an evidenced delegate without transferring human accountability. |
| `decision_coordinator` | Root's CDO-equivalent decisions only at D2/D6/D8, shared-system major releases and material exceptions. |
| `design_ops` | D18, ownership, topology, WIP, SLA, decision log, evidence integrity and archives. |
| `research` | UX Research Lead responsibility: methods, ethical protocol, synthesis limitations and research dispositions; not permission to contact participants. |
| `service_design` | Personas/JTBD, journeys, blueprints, platform allocation and canonical IA. |
| `android_design` | Android flows, states, screens and prototypes. |
| `web_design` | Customer-web flows, states, screens and prototypes. |
| `admin_design` | Operator flows, states, screens, role fidelity and prototypes. |
| `systems` | Foundations, tokens, assets, component APIs, variants and library changes. |
| `content` | Glossary, copy, disclosures, localization and regulated-copy routing. |
| `accessibility` | Inclusive-design and assistive-technology evidence; independent acceptance, not waivers of invariants. |
| `ux_engineering` | Handoff assets, component/state/API/test/telemetry mapping and implementation drift. |
| `design_qa` | Independent critique, prototype validation and build/design conformance. |
| `engineering` | Feasibility and implementation consequences; no replacement engineering governance. |
| `privacy` | Independent minimization, research access, sharing, retention and offboarding review. |
| `security` | Independent abuse, authorization and security review; not implied by design approval. |
| `legal` | Qualified legal review where required; explicitly unassigned, not fabricated counsel or an AI license. |
| `research_store_owner` | Accountable controlled-store ownership, inventory, grants, retention and deletion; explicitly unassigned pending a verified store. |
| `release` | Independent release-evidence verification; no deployment or publishing permission. |

**All discipline rights acceptance and independent appointments remain pending.** The following
compact view does not appoint its roles; consult the JSON for R/C/I detail.

| Artifact class (including all its sub-artifacts) | One accountable role | Independent verifier |
| --- | --- | --- |
| `product_truth` | product_owner | design_qa |
| `design_governance` (D18, topology, decisions, queues) | design_ops | design_qa |
| `research_plan` | research | privacy |
| `research_synthesis` (including research dispositions) | research | privacy |
| `research_access` (store, grants, retention, offboarding) | research_store_owner | privacy |
| `personas_jobs` | service_design | design_qa |
| `journeys_blueprints` | service_design | research |
| `sitemaps` | service_design | design_qa |
| `visual_direction` | decision_coordinator | accessibility |
| `foundations_tokens` | systems | accessibility |
| `components` | systems | design_qa |
| `android_experience` | android_design | design_qa |
| `web_experience` | web_design | design_qa |
| `admin_experience` | admin_design | design_qa |
| `content_localization` | content | accessibility |
| `accessibility_evidence` | accessibility | design_qa |
| `prototype_validation` | research | accessibility |
| `handoff` | ux_engineering | design_qa |
| `readiness` | decision_coordinator | design_qa |
| `build_conformance` | engineering | design_qa |
| `release_design_qa` | decision_coordinator | release |
| `outcome_review` | product_owner | design_qa |
| `traceability_registry` | design_ops | design_qa |
| `archive` | design_ops | privacy |

Every artifact, file, shared region, review, decision and escalation inherits its single accountable
role; splitting an artifact requires new explicit instances and owners, not two accountables.
DesignOps owns shared Cover/Changelog/Handoff/Archive indexes while the discipline owns its content.
Platform squads may propose library or IA changes in isolated copies but never edit the canonical
shared region. A review produces evidence; only the accountable role disposes of it, and it cannot
dispose of a blocking independent finding as a substitute for the finder's resolution.

## 3. Gate contract and freshness

`D0` through `D9` are gate identifiers, not diagram IDs such as `D18`. The JSON names the exact
evidence keys and allowed artifact classes. Each gate requires the previous gate, recursively;
cross-platform snapshots can reference more than one prerequisite instance. Every referenced
instance is re-evaluated, not trusted because its stored status says approved.

| Gate | Evidence (all named JSON keys required) | Approver | Maximum age |
| --- | --- | --- | --- |
| `D0` Product truth | Product truth, constraints, known evidence, open decisions, research ethics | product_owner | 720 hours |
| `D1` Experience architecture | Personas/jobs, journeys, blueprints, platform allocation, sitemaps, registry | service_design | 720 hours |
| `D2` Direction | Tested alternatives, direction decision, accessibility pre-check | decision_coordinator | 720 hours |
| `D3` Flow definition | Task flows, wireflows, content hierarchy, edge cases, contract assumptions, telemetry | Artifact's platform accountable | 336 hours |
| `D4` System design | High fidelity, adaptive variants, components, tokens, content, motion | systems | 336 hours |
| `D5` Prototype validation | Interactive paths, heuristics, accessibility, usability, comprehension | design_qa | 168 hours |
| `D6` Implementation readiness | Handoff, assets, component mapping, state table, API fields, test IDs, limitations | decision_coordinator | 168 hours |
| `D7` Build conformance | Design/code comparison, visual regression, interaction/accessibility parity, deviations | engineering | 72 hours |
| `D8` Release design QA | Device/browser/operator walkthroughs, localization, destructive flows, privacy, final UAT | decision_coordinator | 24 hours |
| `D9` Outcome review | Aggregate metrics, redacted support synthesis, longitudinal research, design debt | product_owner | 720 hours |

The artifact's independent verifier is required **in addition** to the approver, even when their
disciplines otherwise overlap. Each review context must be non-author across the consumed dependency
closure. One context cannot satisfy two required approval roles or both approval and verification.
Actual affected Privacy, Security, Accessibility and other independent requirements under DELIVERY
still apply; a D-gate is not their replacement.

Approval is a bound record, not a boolean:

- Bind the artifact ID/class/squad, semantic version, Git commit/path/SHA-256, all producer contexts,
  change kind, versioned consumed inputs, evidence, dependency scopes and comment identities to
  `scope_sha256`. The stable canonicalization is implemented by `scope_digest`.
- Bind role and actual context/runtime through a **separately coordinator-verified assignment**
  with exact artifact IDs, start/expiry and immutable evidence. Bind the review's evidence bytes,
  decision, scope and timestamp. Self-written UUIDs, hashes or runtime strings prove no identity.
- Require every evidence object to exist at its pinned local Git commit/path with matching bytes.
  A URL, title, missing blob, mutable branch, digest-only claim or missing evidence key is insufficient.
  No remote evidence is fetched by the checker. Review/assignment provenance and completeness must
  be established by Root under DELIVERY before supplying this trusted input.
- Compare to a trusted current UTC clock. `now == expires_at` is expired, with no grace. Future,
  reversed, overlong or timezone-free timestamps fail. Reviews cannot predate their evidence,
  prerequisite decisions, comment resolution or assignment, or outlive the assignment.
- Reopen affected artifacts on contract, user-visible policy, IA, component major, critical
  acceptance, artifact bytes/version, evidence or blocking-comment change, approval expiry or role
  revocation. Unaffected squads are not frozen. Every applicable consumed input must be listed by
  the producer/registry consumer; the checker cannot discover deliberately omitted dependencies.
- An unresolved blocking comment, rejected review, stale scope or reopened/blocked prerequisite
  prevents closure. Blocking comments persist across versions. Resolution requires the original
  independent finder's actual scoped review assignment, current scope, evidence and time; an author
  cannot merely toggle a resolved flag. This includes assigned specialist finders (for example
  Security) without relabeling them as Design QA or counting them as the artifact's RACI verifier.
  Root must supply the complete current comment inventory.

`draft` is unreviewed work; `in_review` is a closure candidate; `blocked` cannot proceed;
`approved` is only a recorded result that must still be re-evaluated; `reopened` needs fresh evidence;
`superseded` points to a replacement; `archived` is read-only. Neither archived nor superseded
versions satisfy a dependency. Fresh reviews are new immutable records, never edits of history.

Shared-system major releases add a `shared_system_major` evidence key and a separate
decision_coordinator approval to D4. Material changes add `material_exception` evidence and the
coordinator wherever they occur. Both have a maximum 24-hour decision window and retain all
ordinary gate/verifier checks. An exception **never** bypasses expiry, evidence, blocking comments,
independence, privacy, consent, legal qualification, access denial or financial invariants.

## 4. T-UXR-06 and research disposition interface

Use schema definitions `snapshot`, `gate_record`, `assignment`, `decision`, `source_state`, `grant`
and `work`; consumers must not infer active approvals from the policy data. `close_gate` returns the
target scope, earliest effective `expires_at` and number of recursively checked artifacts, or raises
a static `Refused` rule. This is an offline evidence check, not a side-effecting gate closer.

Source references use portable Git tree paths (`governance/example.json`), a full commit ID and
`sha256:` plus 64 lowercase hex digits. They are not host paths. Evidence bodies, research content
and comments stay out of the snapshot; only safe references enter it. Referenced documents must
also be sanitized **before** entering this public repository. Hashing a sensitive file does not
authorize committing it.

The existing planning `experience-coverage.schema.json`, `handoff-manifest.schema.json` and
`design-readiness.schema.json` remain unchanged historical/planning contracts. T-UXR-06 adds these
gate records to its coverage references; it must not reinterpret the historical `T-DQA-12` ticket
identifier as gate `D6`, overwrite the planning schemas, or treat their old CDO label as a staffed
human appointment. This source supplies vocabulary/evaluation, not a second engineering pipeline.

An immutable `decision` has accept/revise/decline/defer disposition; all producing contexts
(including proposal/evidence authors); distinct non-author actor and independent verifier
contexts/roles; artifact/class/base digest; target version; proposal references and their
ticket/squad branches; result if applicable; reason/evidence reference; related decisions; UTC
decision/expiry; previous hash and content hash. The referenced reason contains the alternatives,
bounded scope, rationale, affected gates/consumers, residual risk, owner, follow-up and rollback.
It contains no participant narrative or financial data.

The research consumer uses `research_disposition` for research_plan/research_synthesis decisions:
research is accountable and Privacy independently verifies; Legal, Accessibility and the actual
store owner remain consulted/operational start requirements. An accepted methodological source
disposition is **not** permission to recruit, contact, record, collect or share. Unassigned legal or
store responsibilities remain a real start blocker. Revisions and deferred decisions preserve the
original evidence and never manufacture consent, legal approval or a staffed lead.

## 5. WIP, SLA, exceptions and escalation

DesignOps records each active item, squad, actual review context, role, submitted time and
acknowledgement. `queue_metrics` also takes separately verified assignments and verifies their local
evidence; each work ID must be in its current reviewer's artifact scope. Limits include blocked work:
**2 active items per squad**, **3 review items per
independent verifier context**, **2 for the coordinator context** across all its role aliases.
Coordinator identity comes from those assignments, even when every queued item uses another one
of that context's roles. Do not invent capacity by counting discipline labels as people. When full, stop intake or
reprioritize within the limit; another bounded context needs an actual appointment first.

Acknowledge within **24 elapsed UTC hours**, dispose as accept/revise/decline/defer within **48**,
and escalate unresolved work by **72**. At 24 hours DesignOps alerts the assigned reviewer; at
48 it marks the overdue review blocked and escalates to the artifact accountable; at 72 Root
decides reprioritization/reassignment. The original clock is retained across handoffs; weekends,
owner absence, retries and a new comment do not reset it. No timeout auto-approves work.

Exceptions are version-bound decision records, maximum **24 hours**, with rationale, considered
alternatives, affected artifacts/gates, independent verification, expiry, return plan and linked
follow-up. Nonmaterial scheduling dispositions remain with DesignOps and stay within WIP/SLA
ceilings; material exceptions require decision_coordinator. Expiry reopens rather than extending
automatically. Missing qualified operational authority escalates as a blocker, not to a fabricated
substitute. Root's technical delegation does not waive required specialist or human/legal authority.

Assignments are scoped for at most **72 hours** and grants for at most **24 hours**. Reappointment
requires a new actual record; missing or removed assignments fail closed. These short leases bound
delegation during owner absence without manufacturing approval.

## 6. Figma topology, publishing and restoration (disabled)

Reserved project name: **PenniLogic - Experience**. The JSON enumerates exact file/page names:

| Reserved file | Content owner | Content pages beyond Cover/Changelog/Handoff/Archive |
| --- | --- | --- |
| 00 - Product truth and research | research | Product truth, Research plans, Findings |
| 01 - Service and IA | service_design | Personas and JTBD, Journeys, Blueprints, Sitemaps |
| 02 - Foundations library | systems | Foundations, Assets |
| 03 - Components library | systems | Components, Android variants, Web variants, Admin variants |
| 10 - Android product | android_design | Flows, Screens, Prototype |
| 20 - Customer web product | web_design | Flows, Screens, Prototype |
| 30 - Admin product | admin_design | Flows, Screens, Prototype |
| 40 - Content and localization | content | Glossary, Source copy, Regulated copy, Pseudo localization |
| 50 - Design QA | design_qa | Test plans, Findings, Conformance, Release snapshots |
| 90 - Archive | design_ops | Cover, Changelog, Archive, Restoration (no Handoff page) |

After actual access is verified, DesignOps is the sole writer for controlled index pages; the
file's assigned discipline is sole writer for its content region. Platform files subdivide Flows
and Screens by stable flow/screen ID and Prototype by critical journey ID. Each region reservation
records artifact ID, file/page/frame references, context, squad, base version, start and expiry.
Concurrent writes to one canonical region are refused. Expired reservations stop new writes and
require explicit reassignment, never automatic takeover.

Branches/proposal copies use `T-UXA-04__android__debt-details`:
`<plan-ticket>__<squad>__<change-slug>`. Squad and branch identity must agree and branch names must be
unique in a decision. Pages/frames use `<stable-ID> - <short-purpose>`, never participant names,
balances or support text. If native Figma branching is unavailable on the existing plan, use
separate proposal files with these names and pinned exported/source references; do not purchase
features or grant canonical-file edit access as a workaround.

Only the assigned Systems context may prepare library promotion. Require component descriptions,
property names, variants, accessibility notes, content limits, code targets, a versioned manifest,
consumer compatibility evidence, independent verification and fresh applicable gates. Use SemVer:
patch fixes without contract change, minor additive components/tokens, major breaking changes.
Coordinator approval is required only for a shared-system **major** release, not every patch.
Expand, migrate consumers, then retire; no silent replacement. D6 pins platform/library/frame
versions and D8 pins release evidence. Comments link to the issue and exact source/Figma version.

DesignOps serializes promotion from the last recorded canonical revision. A changed base, reused
branch, unresolved conflict or failed gate stops it. `source_change` is only an offline tabletop
transition: it preserves old versions and returns `reopened`, never approved or published.
Actual callers must serialize one writer and compare the freshly read trusted revision immediately
before persistence; this pure function is not a cross-process lock or a SaaS permission control.

Archive accepted superseded snapshots by `<artifact-ID>@<version>` with source digest, replacement,
decision and owner pointers. Migration imports existing sanitized evidence **read-only** with
provenance and limitations; an import does not renew its approval. Never overwrite an archive.
Restoration copies a known old snapshot into a **new higher version**, appends a restore decision
and reopens affected gates. It does not erase later versions or inherit the old approval.

Rollback appends a publishing-freeze decision, preserves every proposal, decision and version,
keeps the last verified library available read-only and stops promotion. Draft analysis may continue.
Restoration does not clear the freeze. Unfreezing requires independently verified current evidence,
actual workspace recovery/access proof and a separate authorized policy decision; this source has
no enable-publishing action.

## 7. Privacy-safe access and audit

Only `synthetic` and `redacted_nonparticipant` metadata is admissible. No real financial records,
raw SMS/email, credentials, participant identifiers, recordings or unredacted support evidence
belongs in design files, public Git evidence, snapshots, fixtures, decision reasons or logs.
No permission to store research raw material is implied; controlled research-store operations
belong to the separately gated research protocol and its actual owner.

Default deny. Grants name one actual context/role, artifact, exact file IDs, allowed view/comment/edit
actions, safe classification, issue/start/expiry and immutable audit reference. Grants cannot
outlive their scoped assignments. A view grant does
not imply edit; file access does not imply ownership of controlled/shared pages. Archive edits,
unknown pages, cross-squad library edits, revoked/expired grants and missing assignments fail.
No publish action is granted by this source model. All Figma access requests fail until real access
has been verified, even when the source-model grant otherwise looks valid.

External sharing and public links are disabled. Future exceptions require an actual recipient and
purpose, minimum read/comment scope, redaction verification, explicit accountable owner and Privacy
review, expiry, export/link controls and auditable revocation; they never allow raw research or
public financial content. Record the audit in the authorized controlled store, not participant
details in a public log. No public-link setting or invite is changed here.

On offboarding, revoke grants/sessions immediately, remove memberships and export/link access,
transfer ownership through a decision, and have the independent Privacy verifier confirm the
inventory. Removing an assignment is revocation for this checker. Missing live SaaS evidence stays
unverified; source tests cannot establish that a remote member or link was really removed.

## 8. Collision tabletop, evidence and observability

Two synthetic squads propose incompatible component changes from the same pinned base, in separate
ticket/squad branches. Both proposals remain immutable. The canonical writer records a conflict
and defers; attempts to adopt either stale revision or skip the unresolved decision fail without
mutating state. Systems then records a reasoned, independently verified combined/additive proposal
referencing the conflict and both originals. One serialized source transition advances the version;
the other squad must rebase its proposal, never overwrite shared work. Prior content, proposals,
conflict and resolution remain readable. These are fixture contexts, not actual role approvals.

The executable tests exercise duplicate/missing RACI, expiry at equality, stale version/input/blob,
reopened/expired prerequisites, blocking comments, wrong/same/expired reviewer contexts, denied
access, branch/revision collision, immutable log tampering and freeze/restore. They run offline
with synthetic blobs; a separate test reads an actual pinned local Git blob.

Run the focused checker and tests:

```text
python scripts/check_design_gates.py
python -m unittest discover -s scripts/tests -p test_design_gates.py
```

The existing native unittest discovery includes these tests and validates the committed policy,
schema and prose; generated CI/checker consumers are not hand-edited. For an actual candidate:

```text
python scripts/check_design_gates.py --snapshot candidate.json --assignments verified-assignments.json
```

Root must first establish the assignments' origin, actual context separation, exact reviewed
version, complete current dependency/comment inventory and supporting evidence under DELIVERY.
The command uses current UTC and local Git objects only, prints static refusal codes rather than
candidate contents, and never writes a gate, issue, PR, research record or Figma object.

DesignOps observes review age, blocked artifact count, effective approval expiry, WIP by squad and
reopened-gate count. `queue_metrics` reports age/WIP/blocked and SLA breaches; `artifact_metrics`
reports declared reopened status and approval deadlines; `close_gate` supplies the verified
dependency-bounded expiry. Metrics contain identifiers/counts/times only, not participant or
financial content. A metrics snapshot is not proof of approval.

## 9. Adoption and remaining acceptance

Adopt before shared design files are created; keep sanitized imported research read-only. Root
publishes and obtains separate non-author Core, Design, Security, Privacy and QA reviews for this
source change. Required findings block integration; author reviews and tests are not those reviews.
The existing native dependency is
[PenniLogic/infra#3](https://github.com/PenniLogic/infra/issues/3); its closure and mirrored blocked-by
edge must be checked independently of this source change.

Source evidence can satisfy the five original acceptance responsibilities without pretending
operations exist. Full Definition of Done still requires protected merge, actual coordinator and
every named discipline's rights acceptance, operational access evidence where applicable and native
dependency verification. Qualified Legal/store/research start authority remains unassigned.
Neither this proposal nor the tabletop claims live Figma, user research or full docs#64 acceptance.
