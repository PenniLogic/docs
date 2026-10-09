---
name: docs65-synthetic-operations
description: Run PenniLogic Docs65 research-operations preparation and synthetic software checks autonomously. Use for an automated, no-contact assessment of the existing pack, not participant research, consent, qualified approval or issue acceptance.
---

# Docs65 synthetic operations

Read the target repository's `AGENTS.md`, `.github/copilot-instructions.md`,
applicable path instructions, `.github/agent-policy.json`,
`governance/DELIVERY.md` and `research/operations/README.md` first. Use this
repository's existing pack; do not regenerate its policy, schema or study.

## Execute one finite assessment

No routine human coordination, role assignment, professional approval or
participant is required to run this **synthetic software lane**. Do not wait
for the real-study conditions in the source plan to become satisfied. They
still govern actual contact and are not waived by this skill.

1. Choose a new local output directory under the current session's artifact
   area, outside every Git checkout and Git metadata directory. Its parent
   must already exist. Do not reuse a prior report directory.
2. From the repository root, run:

   ```text
   python research\operations\run_synthetic.py --output <new-local-directory>
   ```

   On non-Windows hosts use the equivalent native path separators. The runner
   accepts only the output destination, never participant files, free-form
   scenarios, URLs, role grants, consent records or approval switches. It uses
   the current Python interpreter and the existing source checker and native
   `test_research_operations.py` discovery. It does not invoke another agent.
3. Read `assessment.json`. Report the actual classification, result, command
   exits, test counts and failing or incomplete checks. Only successful checks
   permit byte-identical, schema-checked `plan.source.json` and
   `report.UNRUN.json`. These are source copies, not new findings.
   A persistence failure may leave partial copies; only `status: passed` in a
   successfully persisted assessment indicates a complete run.
4. Give the output location and the remaining evidence limits, then stop.
   A failed command, skip, missing test or changed source fails the assessment.
   Do not relabel it, bypass a check, edit policy to obtain a pass, recruit a
   person or ask for professional approval as a way to finish this run.

Tool permissions and repository review policy still apply; this skill does
not pre-approve shell access, install services or enable automatic execution.

## Interpret the result honestly

An `automated_synthetic_operations_assessment` is evidence of source preparation
and software tests only. Test cases are not people. Never turn their counters
into participant counts or their fixture consent/grants into actual consent,
role appointments, Legal opinions or independent review.

The runner's command evidence includes exact exits, observed native test IDs,
timings and output hashes/sizes. It deliberately does not copy raw child output,
participant inputs, arbitrary workspace files or command error text into the
assessment. Use the identified existing command to investigate a failure
locally; do not upload private data to a third party.

Original Docs65 still requires accurate operational and qualified-approval
evidence. Its non-goals include running a specific study: do not invent real
participant recruitment as a prerequisite for this automation. Conversely,
Docs53 remains **UNRUN, participant_count null, contact denied**. Do not modify
the accepted study plan/report, its eleven contact conditions, the provider's
rights, the original issue criteria or any shared generated policy.

No recruitment/contact, real financial data, recordings, private contacts,
consent claims, live-store deletion claims, public writes, spending, account/
device operations, external integrations or nested agents/workflows belong to
this skill. Decline requests for those actions explicitly; do not silently
substitute synthetic evidence for the requested real-world outcome.

## Native discovery

This is one project skill in the documented `.github/skills/<name>/SKILL.md`
location, not a duplicate organization agent profile. In a supported client,
use `/skills reload` and `/skills info docs65-synthetic-operations`, or inspect
`copilot skill list --json`. A user can request `/docs65-synthetic-operations`.
Report actual discovery/invocation results; a file or a Python run alone does
not prove that a client loaded or invoked the skill.

Reference: [GitHub CLI skill documentation](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills).
