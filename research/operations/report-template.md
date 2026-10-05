# Debt-first concept finding: UNRUN

**Template only. Participant count: `null` / pending. No finding or approval.**
Do not turn unrun or missing evidence into a positive, negative or zero-sized
study. Populate a new version only after genuine eligible consenting sessions,
withdrawal processing and the required independent privacy/method review.

## Study identity and method

| Field | Current value / requirement |
| --- | --- |
| Issue and protocol | #53 / T-RES-01; proposed 1.0.0; [protocol](debt-first-protocol.md) |
| Accepted pack / protocol commit | Pending; #64 and #65 remain unaccepted |
| Study dates / report date | Pending, not the template preparation date |
| Participant count | `null` (target 16 is a plan, not a result) |
| Recruitment / exclusions | Pending; state independent route, eligibility, nonresponse, withdrawals and incomplete exposures safely |
| Method / order | Counterbalanced two-card comparison; report delivered orders, deviations and order-effect assessment |
| Pre-registered criteria and outcome | Pending for every criterion, including price and SMS assumptions |
| Reviewer decisions | Pending; actual separate reviewer session, role, reviewed commit, findings and evidence, not self-approval |

## Contradictory evidence

Pending. Record challenges to debt-first positioning, paid conversion, SMS
acceptance, comprehension, inclusion and safety here even if other evidence
supports the thesis. A minority concern is not omitted because its numeric cell
must be suppressed. Use a privacy-reviewed non-identifying summary without
quotes or participant codes; do not imply its prevalence.

## Supporting evidence

Pending. Use the same space and evidentiary standard as contradictions. A stated
preference is not product use, revealed willingness to pay or retained use.

## Mixed, uncertain and missing evidence

Pending. Keep equal/neither/unsure/skipped reactions, insufficient sample,
withdrawals, uncovered groups and order sensitivity visible. Do not manufacture
a "representative" sample or infer financial characteristics that were not asked.

## Safe aggregate tables

[concept-study.report.json](concept-study.report.json) is the machine-readable
shape. It contains no financial-value, identity, participant-code, quote or
raw-note field. It is a **proposed privacy-reviewable shape**, not approved
research evidence. Actual `participant_count` must be stated when safe and
supported. If even that count is identifying, withhold it with the limitation
and do not claim the unqualified #53 reporting criterion is fulfilled.

Publish at most one whole-study preference table, one paid/free/neither/unsure/
skip table and one SMS-reaction table, all using the same declared denominator.
No order-by-response, demographic, household or timestamp cross-tabs. Assess
order effects privately and report only the safe method/result classification.
For a table with any positive cell below 5, suppress **the whole table**,
including any complementary cell from which the small value could be inferred.
Zero is not a substitute for a suppressed count. Do not expose table differences
over time, versioned withdrawal deltas or exact small operational counts.
Even tables passing this numerical rule need an independent linkage/inference
review across the complete publication; the check is not anonymization.

Recruitment coverage, withdrawals, oldest evidence age and undispositioned
findings are reviewed from restricted aggregate operational metrics. Publish
only safe summaries, not individual event histories. Current observations are
all pending. No repeat aggregate release during withdrawal windows.

## Limitations

At minimum: purposive small sample, venue/nonresponse bias, unmeasured income
and within-debt diversity, unmet language/access/device/connectivity coverage,
hypothetical payment and SMS reactions, unresolved published BYOK/annual terms,
order effects/attrition, no usability or longitudinal-retention evidence and
suppressed results. Separate planned limitations from problems actually observed.

## Finding disposition and product decision

For every contradictory, supporting or mixed finding, record its non-identifying
ID, the prior criterion, interpretation, affected specification, decision owner,
and a resulting ticket **or** an explicit reasoned decline. Use the closed
`finding_disposition` shape for structured metadata and a privacy-reviewed prose
explanation. No ticket exists merely because a template names one.

**Current decision: pending; debt-first thesis not validated.**
Record revise/retest/stop/no-change with the qualified research assessment and
accepted product decision authority. Do not silently continue after a kill rule.
No-change requires addressing each contradiction, not just counting supportive
answers. Record the number of still-undispositioned findings; unresolved critical
findings block a validation claim. Merge/date the real finding and reference it
from the product record through Root's reviewed integration, not from this draft.
