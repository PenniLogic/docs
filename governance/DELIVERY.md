# Public organization delivery

This is the operating policy for the new `PenniLogic` Free-plan organization,
created by the owner's September 29, 2026 migration decision. It does not change
the rules, findings, history or protected branches of `PenniLogic-old`.

There is one GitHub user and multiple independent AI sessions. GitHub's required
approving-review count is zero: the only user cannot approve their own PR.
Independent review is still required procedurally and recorded in each PR with
the non-author session, exact reviewed commit, role, findings and evidence.
This is not two-human review, cryptographic identity or independently verified
attestation provenance.

After the reviewed initial import, use PR-only, current-base integration with the
native `CI` job, resolved conversations, no force pushes, no branch deletion and
an empty bypass list. No custom CheckRun publisher, App key, signature gate,
two-phase instruction-hash admission or self-hosted runner is used here. Changes
to CI or this policy receive independent Core and Security review; normal behavior
changes receive Core and QA, plus specialists for affected risks. A substantive
unresolved independent finding blocks integration.

Work from the preserved backlog rather than inventing replacement product scope.
Use one source writer per checkout, additive provider/consumer contracts, and one
database migration at a time. Preserve existing branches and review records.
Each developer performs a correctness/diff self-review and an adversarial pass
before requesting independent review. Local checks, setup and old completed
governance tickets do not prove current product or release acceptance.

Authoritative money is integer minor units with currency and deterministic
server-side calculations. The ledger is append-only. Sharing is default-deny and
entitlements are enforced server-side. Raw messages, credentials and production
financial data do not enter source, issues, logs or model prompts. Optional
permissions can be denied without making the app unusable.

Only standard GitHub-hosted runners are configured. Free public runner minutes
do not grant free AI inference, Copilot subscriptions, hosting, larger runners,
or unlimited artifact/cache storage. No deployment, purchase or increased
spending allowance is part of repository setup.

## Initial import boundary

The initial commit is a reviewed snapshot of accepted source plus the new public
baseline, not a transfer of old private history or unmerged PRs. Branch rules are
enabled once the native job exists and the actual bootstrap run is observed.
Thereafter the same protections apply to the sole owner and all AI sessions.
New repository setup must not claim to resolve old private PR findings: they stay
in the old organization and must be reconsidered if that code is later imported.
