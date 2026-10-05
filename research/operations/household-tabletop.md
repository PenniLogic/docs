# Independent recruitment and safe-exit tabletop

**Source exercise, not a rehearsal with people; specialist review pending.**
No messages are sent, persons represented or accounts/devices operated. This
table specifies decisions tested with synthetic booleans by
[`test_research_operations.py`](../../scripts/tests/test_research_operations.py).
The human/specialist tabletop and real storage/scheduling drill remain required
before any relevant contact; passing these cases does not supply that approval.

#53 is not a coercion or household-interview study. Never ask about abuse,
identify a partner, schedule a pair, request a household referral or corroborate
one person's response with another. If safe independent participation cannot
be established without such disclosure, defer without preserving the reason.
Dedicated safe-exit/coercion studies require a new specialist-reviewed plan,
independent recruitment and participant-controlled stop path.

| Synthetic condition | Required decision | Test |
| --- | --- | --- |
| Reviewed public opt-in, no personal network, private scheduling and participant-controlled stop | Policy model permits independent recruitment only if all actual start conditions are separately satisfied | `test_recruitment_control_positive_is_only_synthetic` |
| Shared household email/calendar/phone or paired session | Refuse; no joint invitation, attendee list or calendar title revealing participation | `test_household_disclosure_paths_are_refused` |
| Partner asks whether another member enrolled or what they said | Neither confirm nor deny; do not query/forward the mapping; decline disclosure | `test_household_disclosure_paths_are_refused` |
| Household or team/personal-network referral | Refuse as this study's recruitment route; never ask the referrer to obtain consent | `test_household_disclosure_paths_are_refused` |
| Private context unknown, third party present, no stop route or no reviewed opt-in route | Do not start; neutral end, no follow-up notification | `test_recruitment_missing_safeguards_are_refused` |
| Household/coercion study without qualified specialist review | Refuse even if other booleans are favorable | `test_specialist_review_cannot_be_omitted` |
| A person stops or withdraws | End immediately; evidence reads denied; erase linked contribution without notifying another member | `test_consent_and_withdrawal_deny_access` |
| Evidence or grant reaches its deadline | Deny at the exact deadline, including attempted alternate-role reads | `test_expiry_boundary_and_roles` |

Before actual use, the qualified lead must also walk through accessible stop
language, safe page/window exit, private scheduling, lost withdrawal handle,
interpreter independence, an observer entering, erroneous group invitations,
shared-device notifications, backup restore and failed deletion. Record only
version, scenario, pass/fail, non-identifying defect, accountable owner and
remediation evidence. Do not invent a completed tabletop, safe contact method,
qualified reviewer, storage proof or sign-off.
