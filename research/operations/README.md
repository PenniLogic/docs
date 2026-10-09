# Research operations preparation

**Source-only operations proposal 1.1.0, 2026-10-05. No contact authorized.**
The debt-first concept study is **UNRUN**; `participant_count` is `null`, not a
measured zero. There are no participants, consents, approvals or findings in
this pack. Test fixtures are software-test data, never research evidence.

This is the bounded preparation for
[#65 / T-UXR-02](https://github.com/PenniLogic/docs/issues/65), the explicit
pre-contact condition for [#53 / T-RES-01](https://github.com/PenniLogic/docs/issues/53).
Their historical source issues are PenniLogic-old/docs#78 and
PenniLogic-old/docs#63 respectively. The original specifications remain the
acceptance authority; this pack does not replace or close either issue.

## Sources and boundaries

The integrated source base is accepted Docs commit
`29741b431124f27751cb2bd4bd0f0dd4c94d6f3d`. The original preparation and published
pricing reference at `3e4afcb9575badf8669a50136da69fcc6f634500` remain historical
source; protocol, consent and empty report version 1.0.0 are unchanged. Plan
1.1.0 adds the accepted provider binding, not a new study method or consent.
Read [PRODUCT](../../PRODUCT.md),
[the product specification](../../product/01-product-spec.md),
[R2](../../product/02-risk-register.md),
[the accepted research programme](../../product/08-experience-design-and-sdlc-plan.md#13-research-programme)
and [delivery policy](../../governance/DELIVERY.md) with this pack.
This pack authors no DesignOps vocabulary, product policy, registry, ADR,
generated setup or application behavior; accepted upstream changes enter only
through the ordinary merge.

The native dependency is **#65 depends on #64**.
[#64](https://github.com/PenniLogic/docs/issues/64) is CLOSED/COMPLETED, verified
on 2026-10-05, following protected [#173](https://github.com/PenniLogic/docs/pull/173).
Its accepted source commit is `29741b431124f27751cb2bd4bd0f0dd4c94d6f3d`,
tree `83d8f5befb0a73e1e0172b54bfaf8a73b9e3df02`, not the earlier author branch.
Root confirmed completion of the original source-rights allocations. This
satisfies the source prerequisite only: provider activation/sharing flags remain
false, actual Legal/store responsibilities and research operating evidence
remain unmet. #53's empty native blocker list does not waive its owner-published
#65 pre-contact condition.

## Accepted source-rights interface

Consume [design-gates.json](../../governance/design-gates.json) and its
[schema](../../governance/design-gates.schema.json), with
[design operations section 4](../../governance/design-operations.md#4-t-uxr-06-and-research-disposition-interface).
Before executing repository-local dependencies, `check.py` independently reads
the fixed accepted Git objects and compares the installed policy, schema, prose,
checker and both executable schema helpers (`check_client_states.py` and
`check_threat_model.py`). It then executes the verified byte snapshot, including
the provider's helper import, without re-reading mutable Python files or using
bytecode caches. Later policy checks also parse the verified data snapshot.
Missing objects or changed bytes fail; the check never fetches evidence or
lets the provider supply its own integrity check. Only Git CRLF normalization
is allowed. This bounded import-closure check trusts the consumer, Git, Python
and its standard library; it is not a host sandbox or general Python
authentication mechanism.

The `research_disposition` function in `check.py` delegates to the accepted
`Checker.append_decision` rather than inventing another rights vocabulary,
decision schema or approval mechanism. Only `research_plan` and
`research_synthesis` dispositions are applicable: Research is accountable and
Privacy independently verifies accept/revise/decline/defer. All producing
contexts, including consumed evidence authors, must be disclosed; this pack's
author cannot act as its own independent Research decision maker or Privacy
verifier. Assignments, scope, immutable source/reason references, expiry,
independence and history must satisfy the provider.
Each disposition identifies exactly one immutable target in `proposals`, whose
actual Git bytes must match both its reference digest and `base_sha256`.
Alternative interpretations belong in the referenced reason; different target
sources need separate scoped decisions. This rule covers all four dispositions
and both Research artifact classes without changing the generic provider.

Root must supply the complete, current evidence/comment inventory, separately
verified actual assignments and trusted clock; the provider cannot discover
omitted dependencies or authenticate a self-written identity. Later D-gate
snapshots use the provider's `Checker.close_gate`, including recursive
prerequisites and unresolved-finder controls. Research dispositions are not
D-gate closure, proof of operational safeguards or consent. No genuine decision,
assignment or gate snapshot is seeded in this pack.

Legal, Accessibility and the actual store owner remain required where applicable.
`research_access` stays accountable to the actual store owner; the coded-evidence
roles in this pack describe separate, still-unprovisioned operational controls.
A source-role allocation does not grant access to participant data. Do not
change the provider's false `role_rights_approved`, contact, Figma or sharing
flags to represent Root's source-only rights decisions; they are not an
operational activation record.

## Pack

| Source | Purpose |
| --- | --- |
| [procedures.md](procedures.md) | Recruitment, matrix, consent, withdrawal, access, retention, stop and synthetic-device procedures |
| [debt-first-protocol.md](debt-first-protocol.md) | Before-study criteria, balanced cards, counterbalancing, actual published prices and neutral discussion guide |
| [concept-study.plan.json](concept-study.plan.json) | Versioned target, exclusions, limitations, schedule and explicit unresolved start conditions |
| [schema.json](schema.json) | Closed research-plan, participant-code, evidence, limitation, finding-disposition and aggregate-report shapes |
| [report-template.md](report-template.md) and [concept-study.report.json](concept-study.report.json) | Empty product-record templates; dissent and uncertainty are not subordinate to support |
| [household-tabletop.md](household-tabletop.md) | No-contact safe-recruitment tabletop and its negative-test mapping |
| [check.py](check.py) and [native tests](../../scripts/tests/test_research_operations.py) | Offline source, planted-data, expiry, access, consent, order and recruitment checks |

## Autonomous synthetic operations

The repository-specific
[docs65-synthetic-operations skill](../../.github/skills/docs65-synthetic-operations/SKILL.md)
runs the existing pack without routine human coordination, professional
approval or real participants. This is a finite **automated synthetic
assessment**, not a new policy, study or role-allocation mechanism.

From the repository root, choose a new directory under an existing local
session-artifact directory outside Git, then run:

```text
python research\operations\run_synthetic.py --output <new-local-directory>
```

[The runner](run_synthetic.py) invokes the existing source check and native
research-test discovery. It records command exits, actual per-test outcomes,
timings and source/output hashes in `assessment.json`; every expected research
case must execute once without a skip. Any failed command, missing case or
changed source fails the run. Raw child output is not copied into the report.
Only after both checks pass does it prepare byte-identical, schema-checked
`plan.source.json` and `report.UNRUN.json` in the new directory. It never
overwrites the source pack or a previous assessment. A persistence failure may
leave partial source copies or a staging file. A complete run requires a
successful runner exit (0) and `status: passed` in the final `assessment.json`.
The closed, flushed staging file is published without overwrite using a local
hard link; an unsupported filesystem fails explicitly, without a fallback.

Only the output destination is accepted. There is no participant-data input,
live mode, approval flag, recruitment integration, spending or nested agent.
The result does not invent consent, professional qualifications or operational
storage/deletion evidence. The existing method, published pricing, provider
rights and UNRUN/null-participant report remain unchanged.

This removes the manual coordination, copying and repeated command sequence
for **synthetic source preparation**. The contact conditions below do not block
that lane. Original #65 includes running a specific study as a non-goal; genuine
participants are therefore not a prerequisite for building or running this
automation. Its actual operational/qualified-approval criteria are not closed
by a passing assessment. #53's later real-study conditions still apply.

Use `/docs65-synthetic-operations` in a client that has discovered the project
skill. Supported clients expose `/skills reload`, `/skills info` or
`copilot skill list --json`. File presence, native discovery and actual skill
invocation are distinct; report any runtime limitation rather than claiming
an agent ran merely because this file exists. The Python command above is
independently executable and does not require a second AI session.

## Conditions that remain unmet

**All rows below are pending.** A person's absence for three days, owner
delegation to prepare source, a local commit or a passing test cannot supply
these facts.

| Condition before contact | Required external evidence / owner interface |
| --- | --- |
| Accepted #65 pack | Separate current-source Core, QA, Security, Privacy, Legal/compliance, Accessibility and qualified UX Research Lead review; required negative findings resolved |
| Responsibility assignment | Actual researcher, recruitment custodian, rights/withdrawal responder and restricted-store custodian; accepted separation of duties from #64 |
| Lawful recruitment | Qualified Legal/Privacy position on the proposed India route and minimum screening; a channel's permission for a neutral public opt-in notice |
| Safe consent and rights | Working private participant-initiated response/withdrawal route, truthful notice, approved retention periods and accessible comprehension procedure |
| Restricted storage | Existing approved encrypted stores, separate identity mapping, least-privilege grants, backups/exports controlled, and real expiry/deletion/withdrawal drill evidence |
| Research method | Independent leading-question, falsification, sampling and order review of the exact protocol version before any session |
| Inclusion | Qualified language/accessibility support for the offered session formats, with unsupported coverage explicitly recorded |
| Actual study | Genuine eligible, independently recruited consenting adults; no agents, staff network or fabricated participants |

No spending, recruitment, contact, incentive purchase, recording, account/device
operation or new service is authorized by this source. The proposed route is
no-cost, independent public opt-in **after** acceptance; it is not a list of
private contacts. If no lawful free route, qualified review or controlled
storage is available, remain blocked. Do not substitute convenience participants
or weaken consent to obtain a result.

## Checks and their limits

From the repository root on Windows:

```text
python research\operations\check.py
python scripts\check_repository.py
python scripts\check_docs.py
python scripts\check_test_strategy.py
python -m unittest discover -s scripts\tests
```

The existing native discovery command runs the original 28 research regressions
and the accepted-provider integration cases in
`scripts\tests\test_research_operations.py` alongside the other repository tests.
To run only these cases, use
`python -m unittest discover -s scripts\tests -p test_research_operations.py`.

The checker reuses the repository's strict JSON Schema subset. Its exceptions
report fixed rule text, not rejected keys or values. No live participant file
is accepted as a CLI argument; only the source plan/report and accepted local
provider sources are read.
IDs, issue references and timestamps must match their complete canonical
formats, including the actual string end; control-character aliases are
refused, never trimmed. Reported metadata retains the frozen method's minimum
limitations and requires a reasoned primary finding before a terminal decision.
The tests create marked synthetic metadata in memory, including deliberately
invalid money/credential fields; provider bootstrap tests use fresh processes
and owned temporary copies backed by actual local Git objects. They do not contact or simulate research
participants, issue a grant, store a recording or erase a device.

Passing proves source shape and the tested policy decisions only. The access
predicate is **not authentication or a storage service**. Real encryption,
revocation, automatic expiry, backup unreadability and deletion receipts require
separate operational evidence. The no-contact source check deliberately refuses
to turn this draft into an accepted pack or to populate its pending report.
The existing `CI` job already runs native discovery; no generated workflow,
command or profile was changed. Local execution proves test discovery and
behavior, not a hosted CI result or research acceptance.

Reviewers receive this source and synthetic tests. Designers receive only
independently privacy-reviewed anonymous aggregate findings later, never coded
rows, recruitment information or a participant-code mapping. Root owns
publication, protected integration and reviewer assignment.
