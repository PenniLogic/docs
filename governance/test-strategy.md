# Test strategy

> **Version 1.1.0.** Published by [PenniLogic/docs#22](https://github.com/PenniLogic/docs/issues/22)
> (source specification PenniLogic-old/docs#21). The machine-readable strategy is
> `governance/test-strategy.json`, validated against `governance/test-strategy.schema.json` and reconciled
> against the issue inventory snapshot `planning/issue-inventory.json` and the client state taxonomy
> `product/client-state-taxonomy.json` by `scripts/check_test_strategy.py`.
> This document is the human reading of that data: every table and list between `rendered` markers below
> is rendered from the data file and the check fails when they differ. **Nothing here claims that a
> harness exists, that a gate runs, that a coverage or mutation number is met, or that a device or
> emulator lane is available.** Every number is a requirement its owning issue must meet, and the check
> proves ownership and shape, not execution.

## 1. Why this exists

PenniLogic is financial software. Some classes of defect - a wrong balance, a payoff date that is off by a
month, a raw bank message leaving the device - are not recoverable reputationally, so the way the product
is verified is decided once, here, and not improvised per ticket. The strategy answers four questions for
every change: which kinds of evidence are mandatory, what numeric bar they must clear, who owns the
executable that produces them, and how the answer is observed in CI or release evidence.

The single most important principle is that **money-path code is verified against an independent source
of truth**: a second, independently written implementation, generated properties over the invariants, and
mutation testing of the production packages. Tests written by the same author against the same
misunderstanding pass happily; the independent model is what makes a wrong number a build failure.
Everything else in this document is conventional and exists so that it is written down, owned and
checkable.

This is a documentation and reconciliation deliverable. Implementing the harnesses is owned by the quality
epic and the other issues named below, and nothing in this repository executes them.

## 2. The contract between this document, the data and the backlog

### 2.1 Owner references

Every verification category, deliverable, device lane, fixture family and owned checklist item names at
least one **owning public issue** in the form `PenniLogic/<repository>#<number>` together with the
**identity** that issue must carry: its plan identity (for example `T-QA-01`) or, for tickets that predate
the planning source, its `PenniLogic-old/<repository>#<number>` source reference. The exact pattern the
check enforces is published as `reference_format` in the data file. Bare `repo#N` identifiers are
`PenniLogic-old` identities and never own anything here; the migrated reference tables on each issue map
them.

The identity requirement is what stops a wrong issue number from silently pointing at an unrelated issue:
the check resolves the reference in the inventory snapshot and then requires the snapshotted issue to carry
the claimed identity.

### 2.2 The reconciliation check

`python scripts/check_test_strategy.py` runs in this repository's `CI` job through
`python -m unittest discover -s scripts/tests`, and can be run directly. It fails when:

- a category, deliverable, device lane, fixture family or owned checklist item has **no owner**;
- an owner reference does not match the published format;
- an owner reference does not resolve to an issue in the inventory snapshot (**a dangling identifier**);
- the resolved issue does not carry the claimed identity;
- the resolved issue is closed as `not_planned` or `duplicate`, because such an issue has renounced the
  work and the category is unowned in practice (an issue closed as `completed` still owns its evidence);
- a required category, deliverable, change class, device lane or checklist item is missing, or a change
  class drops a category the reviewers made mandatory for it;
- a category loses a review-mandated phrase from its approach or evidence (for example the entitlement,
  rate-limiting, step-up and sharing-grant attack classes of `security_negative_tests`);
- a gate assertion published by the client state taxonomy (`adoption.coverage_assertions`) has no
  category claiming it, or two categories claim the same one;
- a **named package has no line or branch floor**, a money-path package has no mutation floor, a floor is
  below the published minimum for its class, or the ledger, debt, budget or split domain has no money-path
  package;
- a repository carries a money-path package but has neither a `mutation_testing` owner in that repository
  nor an explicit enforcement-gap record, or a recorded gap is stale because an owner now exists;
- the flake, retry, pipeline, performance, recovery, evidence or cadence numbers are missing or not
  numeric, or the text that states what happens when a number is exceeded is missing;
- the accessibility target is anything other than the explicit `WCAG 2.2 AA` statement in section 10, the
  automated gate is weaker than the published conformance bar, an assistive technology is made optional,
  the named checks or browser configurations are dropped, or the asserted taxonomy states differ from the
  taxonomy's;
- the device matrix lacks the API 31, current-release, large-text, TalkBack or physical mid-range
  Indian-SIM lane, records any lane as running, or records the physical device as available;
- the inventory snapshot is malformed, covers the wrong organization or repository ids, or disagrees with
  itself;
- any rendered table or list in this document differs from the one rendered from the data.

The unit tests in `scripts/tests/test_test_strategy.py` prove each of these with a planted defect: an
unowned category, a dangling identifier, a wrong identity, a not-planned and a duplicate owner, a package
without a number, a money-path floor without a mutation owner or gap, a dropped attack class, an
unclaimed taxonomy assertion, a weakened accessibility bar, a document that drifted from the data, and a
snapshot with a wrong repository id.

### 2.3 Two layers: offline snapshot and live refresh

CI has no network access to GitHub and no token, so the reconciliation is designed in two layers:

1. **Offline.** `governance/test-strategy.json` maps every category to its owners, and
   `planning/issue-inventory.json` is a committed snapshot of the public issue inventory (repository,
   number, title, state, state reason, `PenniLogic-old` source identity and plan identity for every issue
   in the nine repositories). The check validates the mapping against the snapshot with no network.
2. **Refresh.** `python scripts/check_test_strategy.py --refresh-inventory` regenerates the snapshot from
   the live API through the stored `gh` credential of `basiltt`, in a child process from which `GH_TOKEN`,
   `GITHUB_TOKEN` and `GIT_CONFIG_PARAMETERS` are removed. It verifies the login and user id, the
   organization id and every repository id before reading anything, derives each issue's identity from
   the `plan-id` marker and the original-specification link in its body rather than from its title, and
   never reads, prints or stores a token. The snapshot is never edited by hand: if a refreshed snapshot no
   longer carries an identity the strategy expects, the check fails and the strategy is corrected in the
   same pull request. Run the refresh in a process that has already confirmed `gh api user --jq .login`
   prints `basiltt`, then run the check, and commit the snapshot with the change that needed it.

The snapshot carries its `snapshot_at` time. The cadence in section 17 states when it must be refreshed;
the check does not fail on age, because a CI job with no network cannot fix it.

### 2.4 Change control

Any change to the data file is a pull request with Core and QA review under `governance/DELIVERY.md`. A
floor, ceiling or budget may only be relaxed with a recorded reason and an expiry on the pull request.
Renaming, adding or removing a package or category is likewise a reviewed change; a harness never infers a
floor for a name it does not find.

## 3. Principles

1. Money-path code is verified against an independent source of truth, never only against tests written
   by the same author against the same misunderstanding.
2. A verification category exists only if a public issue owns its executable evidence; the check fails an
   unowned category rather than tolerating a promise.
3. Numbers live in the data file and nowhere else: harnesses read the floors, ceilings and budgets and
   never restate them.
4. Test data is synthetic only; production data never reaches any lower environment.
5. Flaky tests are quarantined and fixed, never retried into green.

## 4. Verification categories and their owners

Each row is one category the strategy asserts. The **owning issues** are the public issues whose
acceptance criteria produce the executable evidence; the **pass/fail signal** states how the result is
observed in CI or in release evidence, so naming a category and being able to verify it are the same
act. The layer table the ticket requires (domain/ledger, debt maths, parsers, API, Android, web and admin,
security) is covered by the first rows; the rows that follow add load, stress and soak, chaos and fault
injection, disaster-recovery restore drills, accessibility with its stated conformance target,
performance budgets as CI gates, mutation-testing thresholds, automated privacy traffic inspection, billing
and webhook adversarial replay, model evaluation in CI, provider and consumer contract testing, security
regression smoke tests in the deploy pipeline, the log and evidence redaction gate, and both gate
assertions the client state taxonomy publishes. Security negative tests cover both halves of
authorization: tenancy and object authorization, and entitlement tampering, throttling, lockout, step-up
replay and sharing-grant default deny, each with its own owning issue.

<!-- rendered:categories:begin -->
| Category | Layer | Approach | Owning issues | Pass/fail signal |
|---|---|---|---|---|
| `unit_tests` | All repositories | Deterministic unit tests on every change, run by the native CI job of each repository; no network, no wall clock and no unseeded randomness | PenniLogic/api#75 (T-SCA-API-01), PenniLogic/contracts#2 (T-SCA-CON-01), PenniLogic/ai-service#1 (T-SCA-AIS-01), PenniLogic/android#1 (T-SCA-AND-01), PenniLogic/web#1 (T-SCA-WEB-01), PenniLogic/admin#1 (T-SCA-ADM-01), PenniLogic/infra#24 (T-SCA-INF-01), PenniLogic/infra#22 (PenniLogic-old/infra#1) | The repository's native CI check on the pull request head; per-package line and branch coverage compared with the floors in this file on every run |
| `domain_ledger_property` | Domain/ledger | Property-based tests over shared generators; the zero-sum invariant, non-negativity where required, rounding and period-boundary rules are machine-checked on generated cases | PenniLogic/api#22 (T-QA-01), PenniLogic/api#3 (PenniLogic-old/api#3) | Property suite in the api pull request gate; a planted rounding error fails the build and names the falsifying case |
| `debt_maths_independent_model` | Debt maths | Every debt, budgeting and allocation result is compared with a second, independently written implementation across the full case matrix, in addition to mutation testing of the production packages | PenniLogic/api#22 (T-QA-01), PenniLogic/api#16 (PenniLogic-old/api#16) | Oracle comparison report per run; any disagreement fails the api build and names the case |
| `mutation_testing` | Money-path packages | Mutation score measured per package and compared with the mutation floor published for that package in this file; every money-path package has one | PenniLogic/api#22 (T-QA-01) | Per-package mutation score published on every run against its floor; a score below the floor fails the build |
| `parser_golden_corpus` | Parsers | Golden-corpus regression: every newly observed bank or wallet format becomes a permanent synthetic, structurally faithful case; the corpus is privacy-scanned, versioned and published with coverage by issuer | PenniLogic/android#35 (T-QA-12), PenniLogic/android#46 (T-PRS-01), PenniLogic/android#47 (T-PRS-02) | Full-corpus run on every parser change with coverage by issuer and rule version published; a regression or a planted identifier in the corpus fails the merge |
| `api_contract` | API | Provider verification that the running service satisfies the published OpenAPI specification, with additive-versus-breaking classification of every change | PenniLogic/contracts#3 (T-QA-02), PenniLogic/api#3 (PenniLogic-old/api#3) | Provider verification on the api pull request against the published contract artifact; a removed field fails unless the expand-and-contract protocol was followed |
| `contract_provider_consumer` | Contracts | Consumer verification of the generated Kotlin, TypeScript and Python clients against the published artifact, with a compatibility report naming each consumer and its verified contract version | PenniLogic/contracts#3 (T-QA-02) | Compatibility report per contract version naming every consumer; a drifting consumer fails its own pipeline |
| `integration_tests` | api | Service tests against a real PostgreSQL instance from the idempotent local bootstrap, exercising database policies and migrations directly | PenniLogic/api#3 (PenniLogic-old/api#3), PenniLogic/api#23 (T-QA-03), PenniLogic/infra#2 (PenniLogic-old/infra#2) | Integration job in the api pull request gate using the bootstrap database; a failure names the service and the query |
| `android_unit_instrumented` | Android | Unit tests plus instrumented critical journeys on the device matrix in this file: the API 31, current-release and large-text emulator lanes are required on every pull request and the TalkBack, low-memory, OEM and physical lanes at release candidate, once the Android gate wires them; no emulator lane runs in android CI at publication | PenniLogic/android#15 (T-QA-08), PenniLogic/android#35 (T-QA-12) | Instrumented results per lane on the pull request and the release candidate; a failing lane is reported by lane and blocks |
| `web_e2e_journeys` | Web | Playwright end-to-end tests of the critical journeys (login, transaction entry, payoff view, import, export) against a seeded synthetic environment on latest-stable Chromium, Firefox and WebKit | PenniLogic/web#7 (T-QA-06) | Journey suite per engine on the web pull request; a browser-specific failure is reported by engine and blocks |
| `admin_e2e_journeys` | Admin | Playwright operator journeys (search, redacted read, unmask request, four-eyes approval, support-verified action) with a planted-defect gate proving that weakened redaction, an unmask without a verified ticket and a self-approval each fail | PenniLogic/admin#3 (T-QA-13) | Operator journey suite and planted-defect results on the admin pull request; a planted defect that passes fails the suite |
| `accessibility_conformance` | Web, admin, Android | WCAG 2.2 AA on web and admin: a named, pinned WCAG-tagged automated ruleset with zero violations at any impact level for rules tagged WCAG 2.0, 2.1 and 2.2 Level A and AA on the core journeys (best-practice rules that are not WCAG success criteria are advisory; an exception requires a recorded reason and an expiry on the pull request), run in every browser configuration in this file, plus keyboard-only and screen-reader walkthroughs; Android runs Accessibility Test Framework checks in the instrumented suite and Android Lint accessibility rules with pinned versions, meets the Material accessibility baseline and every applicable WCAG 2.2 AA outcome, and is walked through with TalkBack and Switch Access; every applicable client state taxonomy state on each core journey is asserted against client-state-taxonomy section 8 (announced once with the published politeness, focus target, no re-announcement on return, recovery action reachable by keyboard and switch, disabled controls exposing their reason) | PenniLogic/web#7 (T-QA-06), PenniLogic/android#15 (T-QA-08), PenniLogic/admin#3 (T-QA-13) | Automated scan with zero violations at any impact level for WCAG-tagged Level A and AA rules on core journeys in every browser configuration, Android Accessibility Test Framework and Lint results, and attached walkthrough evidence per release covering every applicable taxonomy state; a planted unlabeled control, undersized target, contrast failure, unannounced state or focus that does not move on an error fails the gate |
| `performance_budgets` | Web, admin, Android, API | The numeric budgets published in this file are enforced per pull request and per release candidate; a deliberate regression must fail | PenniLogic/web#7 (T-QA-06), PenniLogic/android#15 (T-QA-08), PenniLogic/admin#3 (T-QA-13), PenniLogic/infra#29 (T-QA-05) | Measured value against its budget on every run; a regressed budget fails the pull request or the release candidate |
| `security_negative_tests` | Security | Tests that actively attempt violations from inside the code and against the running service: cross-tenant reads, broken object authorization, mass assignment, authentication bypass and token replay; entitlement tampering by a client claiming a feature its plan lacks, with absence of an entitlement denying per gated feature; rate limiting, lockout and credential stuffing; step-up bypass and step-up token replay on export, deletion and sharing invitations; sharing-grant default deny with absent or expired grants, aggregate-versus-detail separation and differencing attacks; plus the AI request-forgery and operator red-team suites | PenniLogic/api#23 (T-QA-03), PenniLogic/api#29 (T-BIL-01), PenniLogic/api#40 (T-SEC-04), PenniLogic/api#34 (T-FAM-01), PenniLogic/ai-service#3 (T-AI-03), PenniLogic/admin#9 (T-ADM-12) | Attack suite and object-level authorization coverage report on every api, ai-service and admin pull request, with a negative test per gated feature and per grant scope, and throttling, lockout and step-up replay attempts rejected and audited; a deliberately weakened fixture must make the suite fail |
| `log_redaction_gate` | Backend logging and evidence artifacts | Structured logging with a published field allowlist; a static rule that fails the build when a money or personal-data type is logged; a runtime scan of sampled emitted records in CI with a planted money value; fail-closed scrubbing that drops a record rather than emitting it raw, on error paths and exception messages as well as the happy path; failure screenshots and recorded evidence artifacts scrubbed of money values, raw message text and personal data before upload | PenniLogic/api#21 (T-PLT-04), PenniLogic/android#18 (T-CMP-03), PenniLogic/web#7 (T-QA-06), PenniLogic/android#15 (T-QA-08) | Static rule and runtime scan results on every api pull request, and scrubbed-artifact confirmation in each client gate; a planted money value in an emitted record or an uploaded artifact fails the pipeline |
| `static_dependency_secret_gates` | Pipeline | Static application security testing per language, dependency review with an expiring exception process, full-history secret scanning and the SDK allowlist, all blocking | PenniLogic/infra#28 (T-QA-04), PenniLogic/infra#23 (PenniLogic-old/infra#3) | Blocking checks on every pull request; a planted injection pattern, advisory or secret fails, and a secret triggers a rotation ticket |
| `security_regression_smoke` | Deploy pipeline | Dynamic scanning of the ephemeral deployed build for the authenticated and unauthenticated surface, plus signed-artifact and provenance verification before deployment | PenniLogic/infra#28 (T-QA-04), PenniLogic/infra#31 (T-QA-11) | Dynamic scan report and artifact verification result attached to each deployment; a high-severity finding or an unsigned or tampered artifact fails the deploy gate |
| `supply_chain_verification` | Infrastructure, containers, Android binaries | Infrastructure-as-code policy scanning, container image scanning before publication and deployment, Android release static analysis, a CycloneDX bill of materials per artifact and signed provenance | PenniLogic/infra#31 (T-QA-11) | Per-artifact bill of materials and provenance linked from the release record; a planted misconfiguration, vulnerable image or insecure Android fixture fails |
| `load_stress_soak` | Backend at scale | Load profiles at realistic peak against the latency and error budgets in this file, a stress run to the breaking point that records the failure mode, and a sustained soak asserting no memory or connection growth and exact quota counters | PenniLogic/infra#29 (T-QA-05) | Dated run results against the budgets attached to the release candidate; a regression fails the release |
| `chaos_fault_injection` | Dependencies | Injected database failover, key-service outage, cache loss, provider outage and webhook storms, each with a defined expected behaviour; a key-service outage must never corrupt or expose data | PenniLogic/infra#29 (T-QA-05) | Per-fault observed-versus-expected behaviour report per release candidate; an undefined or violated behaviour fails |
| `disaster_recovery_restore` | Backups and recovery | A performed restore into a clean environment with measured recovery point and recovery time, a timed game day against the objectives in this file, and proof that user erasure survives restore | PenniLogic/infra#26 (T-PLT-02), PenniLogic/infra#29 (T-QA-05), PenniLogic/infra#33 (T-SEC-07) | Dated drill and game-day records with measured recovery point and time against the targets; the runbook correction is part of the record |
| `privacy_traffic_inspection` | Release candidate egress | Every release candidate runs its core journeys through an intercepting proxy; the capture must contain no raw message text, no monetary value in analytics and no host outside the allowlist shared with the payload-scrubbing hook | PenniLogic/android#16 (T-QA-09), PenniLogic/android#18 (T-CMP-03) | Signed evidence pack per release candidate consumed by the Data Safety declaration; a planted raw string, monetary value or unknown host fails the release |
| `billing_webhook_replay` | Billing | Webhook signature verification and idempotent processing plus an adversarial replay and forgery suite across purchase, renewal, refund and entitlement transitions, with nightly reconciliation against the provider | PenniLogic/api#32 (T-BIL-05), PenniLogic/api#48 (T-BIL-06) | Replay and forgery suite in the api pull request gate and a nightly drift alarm; a replayed or forged event must produce no second effect |
| `model_evaluation` | AI service | Grounding, refusal, advice-boundary, numeric-fidelity and prompt-injection evaluations against a governed synthetic corpus with the accuracy floor in this file and pinned provider model versions | PenniLogic/ai-service#7 (T-AI-06), PenniLogic/ai-service#4 (T-AI-05) | Evaluation report per pull request and on any model version change; a score below the floor or an altered number fails the merge |
| `threat_model_refresh` | Definition of Ready | A dated per-epic STRIDE refresh with a named owner before the epic's first ticket starts, covering the ingestion boundary, raw-content-never-leaves-device and the parser-config signing chain as well as application-layer risks, recorded machine-readably | PenniLogic/docs#48 (T-QA-14) | Refresh record per epic checked at Definition of Ready and in independent review; a stale or incomplete refresh is reported as invalid |
| `penetration_test` | Pre-launch | Independent external test scoped from the current threat model with every high and critical finding closed and retested; accepted risks carry an owner and an expiry | PenniLogic/docs#43 (T-QA-10) | Report, retest records and the accepted-risk register read by the public-launch gate; an open high finding or an expired accepted risk fails the gate |
| `flaky_test_quarantine` | Pipeline | Quarantine and fix, never silently retry into green: the numbers in this file bound automatic re-execution, trigger quarantine, cap the quarantine rate and age quarantined tests out | PenniLogic/infra#28 (T-QA-04) | Per-repository flake rate, quarantine list with owning tickets and retry counts published on every run; an exceeded ceiling fails the pipeline |
| `client_state_coverage` | Android, web, admin surfaces | Every registered surface handles every applicable identifier of the published client state taxonomy with the canonical copy and exactly one recovery action, proven with a planted omission (taxonomy coverage assertion client_state_coverage) | PenniLogic/docs#1 (T-UX-01), PenniLogic/web#7 (T-QA-06), PenniLogic/android#15 (T-QA-08), PenniLogic/admin#3 (T-QA-13) | Coverage assertion in each client gate against the taxonomy data file at the pinned taxonomy_version, extended with the section 8 semantics assertion for each rendered state (announced once, focus target, no re-announcement on return, recovery action operable by keyboard and switch); a planted omission or an unannounced state fails |
| `client_state_taxonomy_first` | Android, web, admin surfaces | The client's state enumeration is a subset of the identifiers in the taxonomy data file at the pinned taxonomy_version; a new state is added to the taxonomy first and only then to any client (taxonomy coverage assertion taxonomy_first) | PenniLogic/docs#1 (T-UX-01), PenniLogic/web#7 (T-QA-06), PenniLogic/android#15 (T-QA-08), PenniLogic/admin#3 (T-QA-13) | Subset assertion in each client gate against the identifiers at the pinned taxonomy_version; a planted unlisted identifier fails |
| `internationalization_checks` | Android, web | Locale-aware INR formatting, a pseudo-localization run over every core journey, and long-string and right-to-left layout safety; single-currency MVP, multi-currency not claimed | PenniLogic/web#7 (T-QA-06), PenniLogic/android#15 (T-QA-08), PenniLogic/android#34 (T-GLO-02) | Formatting, pseudo-localization and layout checks in the client gates; a hardcoded symbol, grouping or clipped label fails |
| `insider_risk_controls` | Admin | A planted-defect gate on redaction, unmask and four-eyes operator journeys plus the operator red-team suite as a blocking console release gate | PenniLogic/admin#3 (T-QA-13), PenniLogic/admin#9 (T-ADM-12) | Planted-defect and red-team results per admin release; a planted defect that passes fails the release |
| `release_rollback_rehearsal` | Deploy and store release | A rehearsed, dated deploy rollback and a rehearsed staged-rollout halt with a minimum supported version policy | PenniLogic/infra#25 (T-PLT-01), PenniLogic/android#37 (T-REL-01) | Dated rollback and halt rehearsal records read by the release evidence gates; a missing or stale record fails the gate |
| `android_release_gate` | Play release | Play App Signing custody, track promotion and a staged rollout that halts on the crash and ANR budgets published in this file | PenniLogic/android#37 (T-REL-01), PenniLogic/android#15 (T-QA-08) | Vitals measurements against the budgets per rollout stage; a breach halts promotion |
| `compliance_reconciliation` | Compliance | Obligation and risk matrices reconciled against the issue inventory, and versioned jurisdiction profiles that fail closed when a statutory value is missing | PenniLogic/docs#44 (T-CMP-04) | Reconciliation run per compliance pack version; an unowned obligation or an unknown ticket fails |
| `design_to_code_regression` | Design QA | Visual, interaction and semantic regression against the design source plus cross-platform parity and release design QA | PenniLogic/docs#135 (T-DQA-10), PenniLogic/docs#136 (T-DQA-11) | Regression and parity reports per client release; an unreviewed divergence fails design QA |
| `release_evidence_gates` | Release | Executable private-beta and public-launch gates read the named evidence artifact of every contributing category within the freshness window and fail naming the missing item and its owner; no manual override | PenniLogic/docs#49 (T-REL-02), PenniLogic/docs#50 (T-REL-03) | Gate run output naming each artifact, its age and its verdict; a missing, stale or failing artifact fails |
| `strategy_reconciliation` | This document | The check in this repository reconciles every category, deliverable, device lane and fixture family with an owning public issue and every named package with its numbers, and is re-run at each cadence trigger | PenniLogic/docs#22 (PenniLogic-old/docs#21) | python scripts/check_test_strategy.py in the docs CI job and its unit tests; an unowned category, a dangling identifier or a package without a number fails |
<!-- rendered:categories:end -->

**Not asserted.** The following are recorded rather than claimed; the list is rendered from the data.

<!-- rendered:not_asserted:begin -->
- No harness, gate, coverage, mutation, accessibility, load or device result is claimed by this file; every number is a requirement its owning issue must meet, and the check proves ownership and shape, not execution
- Delivery-protocol enforcement in CI (contract-first metadata, migration lock, dependency validation) has no migrated owning issue in the public inventory and is therefore not asserted as a category until one exists
- No emulator lane exists in PenniLogic/android CI at publication: the emulator lanes are provisionable on GitHub-hosted runners and become gates only when PenniLogic/android#15 (T-QA-08) wires them; until then any lane evidence is produced locally and attached to the pull request
- Android money-path mutation enforcement for android.ledger and android.parsers has no owning issue; the floors are published requirements and the gap is recorded in floor_policy.mutation_enforcement_gaps until an owner exists
- The ai-service integration job has no owning issue; integration_tests is scoped to api and no ai-service integration gate is asserted
<!-- rendered:not_asserted:end -->

Delivery-protocol enforcement in CI (formerly `T-GOV-04`) will be added as a category when an owner
exists; until then the Definition of Ready items in section 14 are checked procedurally in independent
review.

## 5. Named deliverables

The strategy names these artifacts as deliverables with owners rather than describing them as habits. The
independent-model verification harness and the black-box red-team scenarios are the two the ticket
requires; the others are the shared inputs the categories above depend on.

<!-- rendered:deliverables:begin -->
| Deliverable | What it is | Owning issues |
|---|---|---|
| `independent_model_harness` | A second, independently written implementation of debt, budgeting and allocation arithmetic used as the oracle for every money-path result, wired to the per-package floors in this file; the debt-mathematics reference schedules and fixed mutation catalogue are owned by the independent verification suite ticket | PenniLogic/api#22 (T-QA-01), PenniLogic/api#16 (PenniLogic-old/api#16) |
| `money_path_generators` | Property-based generators for amounts, currencies, dates, schedules and split shares reused by every repository that tests money | PenniLogic/api#22 (T-QA-01) |
| `red_team_scenarios` | Written scenarios for a malicious administrator, a malicious family member, a hostile merchant string and a stolen unlocked device, each with a recorded outcome, plus the operator red-team suite | PenniLogic/docs#43 (T-QA-10), PenniLogic/admin#9 (T-ADM-12) |
| `physical_test_device` | One mid-range Android device with an Indian SIM and a synthetic test account, provisioned, wiped between campaigns and inventoried; required by the device matrix and not yet available | PenniLogic/android#14 (T-QA-07) |
| `sanitized_parser_corpus` | Synthetic, structurally faithful bank and wallet message corpus with a privacy scan, a versioned schema and a contribution protocol that forbids pasting a real message | PenniLogic/android#35 (T-QA-12), PenniLogic/android#46 (T-PRS-01) |
| `evidence_gate_runner` | The private-beta and public-launch gate runners that read the named evidence artifacts and fail on a missing, stale or failing item | PenniLogic/docs#49 (T-REL-02), PenniLogic/docs#50 (T-REL-03) |
<!-- rendered:deliverables:end -->

## 6. Test taxonomy: what is mandatory for each change class

A pull request carries the mandatory set of every change class it touches. **Mandatory categories** must
show a pass signal on the merged head. **Manual evidence** is attached to the pull request and named in
the review record; it never substitutes for an automated category. Independent review roles follow
`.github/agent-policy.json`: Core always, QA for behaviour changes, and the specialist named for the risk.

<!-- rendered:change_classes:begin -->
| Change class | Mandatory categories | Manual evidence |
|---|---|---|
| `money_path` | `unit_tests`, `domain_ledger_property`, `debt_maths_independent_model`, `mutation_testing`, `integration_tests`, `log_redaction_gate` | Money review role recorded in the pull request |
| `parser` | `unit_tests`, `parser_golden_corpus`, `mutation_testing`, `privacy_traffic_inspection` | Corpus contribution reviewed as a synthetic transcription, never a real message |
| `contract` | `unit_tests`, `api_contract`, `contract_provider_consumer` | Contract review role confirms the additive-versus-breaking classification |
| `api_service` | `unit_tests`, `integration_tests`, `api_contract`, `security_negative_tests`, `static_dependency_secret_gates`, `log_redaction_gate` | none |
| `security_boundary` | `unit_tests`, `security_negative_tests`, `static_dependency_secret_gates`, `security_regression_smoke`, `threat_model_refresh`, `log_redaction_gate` | Security review role; the epic's threat-model refresh record is cited |
| `android_client` | `unit_tests`, `android_unit_instrumented`, `accessibility_conformance`, `performance_budgets`, `client_state_coverage`, `client_state_taxonomy_first`, `internationalization_checks`, `privacy_traffic_inspection` | TalkBack and Switch Access walkthrough evidence on the core journeys; Physical-device permission journey once the device lane is available |
| `web_client` | `unit_tests`, `web_e2e_journeys`, `accessibility_conformance`, `performance_budgets`, `client_state_coverage`, `client_state_taxonomy_first`, `internationalization_checks` | Keyboard-only and screen-reader walkthrough evidence on the core journeys |
| `admin_console` | `unit_tests`, `admin_e2e_journeys`, `accessibility_conformance`, `performance_budgets`, `client_state_coverage`, `client_state_taxonomy_first`, `insider_risk_controls` | Keyboard-only operator walkthrough evidence; Design review for intentional role-specific divergence |
| `ai_service` | `unit_tests`, `model_evaluation`, `security_negative_tests`, `static_dependency_secret_gates` | Prompt and tool contract review |
| `billing` | `unit_tests`, `billing_webhook_replay`, `mutation_testing`, `integration_tests`, `security_negative_tests`, `log_redaction_gate` | Money review role recorded in the pull request |
| `infrastructure` | `unit_tests`, `supply_chain_verification`, `static_dependency_secret_gates`, `security_regression_smoke` | Core and Security review for any CI or policy change |
| `data_migration` | `unit_tests`, `integration_tests`, `release_rollback_rehearsal` | One migration at a time with reversal evidence recorded |
| `documentation_and_planning` | `unit_tests`, `strategy_reconciliation` | Core review; QA review when a check's behaviour changes |
| `release` | `release_evidence_gates`, `privacy_traffic_inspection`, `load_stress_soak`, `chaos_fault_injection`, `security_regression_smoke`, `android_release_gate` | Release review role reads the gate output, never a checklist |
<!-- rendered:change_classes:end -->

## 7. Coverage and mutation floors per package

Coverage expectations are a **high bar on money paths and a pragmatic bar elsewhere**, published as
numbers per named package rather than one global percentage. A money-path package is any package whose
code produces, transforms or persists an amount: ledger, debt, budget, split, money types, goals, income,
billing arithmetic, idempotent financial writes and amount-extracting parsers. Every money-path package
carries a mutation-score floor; **a package without a mutation floor may not carry money-path code**, and
a package with no published line, branch or mutation number is a failure of this strategy, not an
exemption.

The floors are initial requirements, not measurements. The minimum a package of each class may publish is
`floor_policy` in the data file, rendered in section 9.4; the check fails a package whose floor is below
the minimum for its class. Money-path coverage is also a **ratchet**: a pull request may not reduce the
measured line or branch coverage of a money-path package even when the result is still above the floor.
The harness tickets `PenniLogic/api#22` (T-QA-01) and `PenniLogic/infra#28` (T-QA-04) and the client
gates read these numbers from the data file; a package present in a build but absent from this inventory
fails that repository's harness, so an unlisted package cannot silently escape the gate.

<!-- rendered:packages:begin -->
| Package | Repository | Money path | Line floor % | Branch floor % | Mutation floor % |
|---|---|---|---|---|---|
| `api.money` | PenniLogic/api | yes | 97 | 93 | 90 |
| `api.ledger` | PenniLogic/api | yes | 97 | 93 | 90 |
| `api.debt` | PenniLogic/api | yes | 97 | 93 | 90 |
| `api.budget` | PenniLogic/api | yes | 95 | 90 | 85 |
| `api.split` | PenniLogic/api | yes | 95 | 90 | 85 |
| `api.goals` | PenniLogic/api | yes | 95 | 90 | 85 |
| `api.income` | PenniLogic/api | yes | 95 | 90 | 85 |
| `api.billing` | PenniLogic/api | yes | 95 | 90 | 85 |
| `api.sync` | PenniLogic/api | yes | 95 | 90 | 85 |
| `api.identity` | PenniLogic/api | no | 90 | 85 | not required |
| `api.admin` | PenniLogic/api | no | 90 | 85 | not required |
| `api.http` | PenniLogic/api | no | 80 | 70 | not required |
| `api.notifications` | PenniLogic/api | no | 80 | 70 | not required |
| `contracts.spec` | PenniLogic/contracts | no | 80 | 70 | not required |
| `ai_service.gateway` | PenniLogic/ai-service | no | 85 | 75 | not required |
| `ai_service.tools` | PenniLogic/ai-service | no | 90 | 85 | not required |
| `ai_service.evaluation` | PenniLogic/ai-service | no | 85 | 75 | not required |
| `android.ledger` | PenniLogic/android | yes | 95 | 90 | 85 |
| `android.parsers` | PenniLogic/android | yes | 95 | 90 | 85 |
| `android.money_format` | PenniLogic/android | no | 90 | 85 | not required |
| `android.capture` | PenniLogic/android | no | 90 | 85 | not required |
| `android.sync` | PenniLogic/android | no | 90 | 85 | not required |
| `android.billing` | PenniLogic/android | no | 85 | 75 | not required |
| `android.ui` | PenniLogic/android | no | 70 | 60 | not required |
| `web.money_format` | PenniLogic/web | no | 90 | 85 | not required |
| `web.import_export` | PenniLogic/web | no | 85 | 75 | not required |
| `web.app` | PenniLogic/web | no | 70 | 60 | not required |
| `admin.redaction` | PenniLogic/admin | no | 90 | 85 | not required |
| `admin.four_eyes` | PenniLogic/admin | no | 90 | 85 | not required |
| `admin.app` | PenniLogic/admin | no | 70 | 60 | not required |
| `infra.governance` | PenniLogic/infra | no | 85 | 75 | not required |
| `infra.tooling` | PenniLogic/infra | no | 80 | 70 | not required |
| `docs.scripts` | PenniLogic/docs | no | 85 | 75 | not required |
<!-- rendered:packages:end -->

The inventory reflects the planned package layout of repositories that are mostly still scaffolds. When a
repository's real layout differs, the pull request that introduces the package also updates this file,
with review, before the harness will accept it.

### 7.1 Mutation enforcement ownership per repository

A mutation floor is only a gate where a harness in that repository is chartered to read it. The
`mutation_testing` owner keeps its harness and gate configuration in `PenniLogic/api`; other
repositories consume the published invariant list and implement their own tests. So the check requires
that **every repository carrying a money-path package has a `mutation_testing` owner in that repository,
or an explicit enforcement-gap record** naming the packages, the reason and the resolution. A gap is an
honest statement that a published number has no executable owner yet, not an exemption: the floors
stand, the Definition of Done item `mutation_floor_met` cannot be evidenced for those packages until an
owner exists, and the check fails if the record is removed without an owner or kept after one appears.

<!-- rendered:mutation_enforcement_gaps:begin -->
| Repository | Money-path packages without an enforcement owner | Reason | Resolution |
|---|---|---|---|
| PenniLogic/android | `android.ledger`, `android.parsers` | The only mutation_testing owner, PenniLogic/api#22 (T-QA-01), keeps its harness and gate configuration in api by its parallel boundary; no PenniLogic/android issue scopes mutation testing, and PenniLogic/android#15 (T-QA-08) covers instrumented journeys, accessibility, performance, internationalization and client state coverage only. | An Android money-path mutation owner is requested from the coordinator as a new issue or a scope change agreed with the T-QA-08 owner. Until it exists the Definition of Done item mutation_floor_met cannot be evidenced for these two packages and this gap entry must remain; the check fails if the entry is removed without an owner or kept after one exists. |
<!-- rendered:mutation_enforcement_gaps:end -->

## 8. Flaky-test policy: quarantine and fix, never silently retry into green

A test that fails and then passes has told you something about the product or the test, and the answer
is never "run it again until it is green". The numbers below bound automatic re-execution, trigger
quarantine, cap how much of a suite may be quarantined at once and age quarantined tests out. Quarantine
removes a test from the gating set but not from execution: it keeps running, its results are published,
and it has an owning ticket. Deleting a quarantined test requires recorded reviewer approval on that
ticket. The pipeline gate that enforces this is owned by `PenniLogic/infra#28` (T-QA-04).

<!-- rendered:flake_policy:begin -->
| Number | Value | Consequence when exceeded |
|---|---|---|
| Quarantine rate ceiling | 2% of a repository's tests | The repository's pipeline fails for every change except fixes to quarantined tests until the rate is back under the ceiling |
| Automatic retry limit | 1 re-execution (money-path change class: 0) | A pipeline step configured to retry beyond the limit fails the pipeline configuration check; a test that still fails after the permitted re-execution is a real failure and blocks |
| Quarantine trigger | 2 flake events within 14 days | One automatic re-execution is allowed only to classify a failure: a pass on re-execution is recorded as a flake event against the test and counts towards quarantine, never as a clean pass; the money-path change class gets no re-execution at all |
| Quarantine maximum age | 14 days | A test quarantined for longer than the maximum age fails the build until it is fixed, or deleted with recorded reviewer approval on its owning ticket |
<!-- rendered:flake_policy:end -->

## 9. Budgets

### 9.1 Pipeline budgets

The money-path harness, a pull request gate and a release-candidate gate each have a wall-clock budget
(`pipeline_budgets`, rendered in section 9.4). Exceeding a budget fails the run rather than warning, so a
slow harness cannot be quietly disabled for speed; the money-path harness budget must fit inside the pull
request gate budget.

### 9.2 Performance budgets as CI gates

Each budget is measured under its stated condition on every pull request or release candidate and compared
with the number below; a deliberate regression must fail the gate, and the gate tickets prove that with a
planted regression. The crash and ANR budgets are the same numbers the staged-rollout halt reads, so the
Android gate and the release gate cannot drift apart. Budgets are initial requirements grounded in the
delivery plan's non-functional gates and in published platform thresholds; a change is a reviewed pull
request.

<!-- rendered:performance_budgets:begin -->
| Budget | Surface | Metric | Budget | Condition | Gate |
|---|---|---|---|---|---|
| `android_cold_start` | Android | Cold start to first interactive frame | <= 2000 ms | p95 over ten launches of a release build on the mid-range physical device lane | `performance_budgets` |
| `android_timeline_frame_time` | Android | Frame time while scrolling the transaction timeline | <= 16 ms | p95 over a 10000-row synthetic history on the minimum-supported low-memory lane | `performance_budgets` |
| `android_janky_frames` | Android | Janky frames while scrolling the transaction timeline | <= 5 percent | 10000-row synthetic history on the minimum-supported low-memory lane | `performance_budgets` |
| `android_crash_rate` | Android | User-perceived crash rate | <= 1.09 percent | Per staged-rollout stage from Play Vitals; the Play core-vitals bad-behaviour threshold | `android_release_gate` |
| `android_anr_rate` | Android | User-perceived ANR rate | <= 0.47 percent | Per staged-rollout stage from Play Vitals; the Play core-vitals bad-behaviour threshold | `android_release_gate` |
| `web_lcp` | Web | Largest Contentful Paint on the dashboard route | <= 2500 ms | p75 on a throttled mid-tier mobile profile with a seeded synthetic account | `performance_budgets` |
| `web_inp` | Web | Interaction to Next Paint on the core journeys | <= 200 ms | p75 on a throttled mid-tier mobile profile | `performance_budgets` |
| `web_cls` | Web | Cumulative Layout Shift on the core journeys | <= 0.1 score | p75 on a throttled mid-tier mobile profile | `performance_budgets` |
| `web_initial_javascript` | Web | Compressed JavaScript transferred to render the dashboard route | <= 250 KB | Production build, first navigation | `performance_budgets` |
| `admin_lcp` | Admin | Largest Contentful Paint on the subject search route | <= 2500 ms | p75 on a desktop profile with a seeded synthetic environment | `performance_budgets` |
| `admin_inp` | Admin | Interaction to Next Paint on the operator journeys | <= 200 ms | p75 on a desktop profile | `performance_budgets` |
| `admin_list_render` | Admin | Subject list render time with 1000 rows | <= 500 ms | Seeded synthetic environment, desktop profile | `performance_budgets` |
| `api_read_latency` | API | Read endpoint latency at the published peak load | <= 300 ms | p95 during the load profile on the isolated load environment | `load_stress_soak` |
| `api_write_latency` | API | Write endpoint latency at the published peak load | <= 500 ms | p95 during the load profile on the isolated load environment | `load_stress_soak` |
| `api_error_rate` | API | Server error rate at the published peak load | <= 0.1 percent | During the load profile on the isolated load environment | `load_stress_soak` |
| `ai_task_accuracy` | AI service | Task accuracy on the governed evaluation corpus | >= 95 percent | Every pull request and every provider model version change | `model_evaluation` |
<!-- rendered:performance_budgets:end -->

### 9.3 Recovery objectives

The disaster-recovery game day is measured against the recovery point and recovery time objectives in
`recovery_objectives` (rendered in section 9.4). These are targets for the drill, not measured values; the
performed restore drill owned by `PenniLogic/infra#26` (T-PLT-02) measures the real numbers, and changing
the targets is a reviewed pull request, never a claim.

### 9.4 Published scalar numbers

Every scalar number the strategy publishes outside the tables above is rendered here from the data file,
exactly as the harnesses read it. Prose elsewhere in this document names no number that is not also in a
rendered block.

<!-- rendered:numbers:begin -->
| Number | Value | Read by |
|---|---|---|
| Money-path minimum floors (line / branch / mutation) | 95 / 90 / 85 percent | `mutation_testing`, `unit_tests` |
| Other-package minimum floors (line / branch) | 60 / 50 percent | `unit_tests` |
| Money-path harness pipeline budget | 20 minutes | `mutation_testing`, `debt_maths_independent_model` |
| Pull request gate pipeline budget | 30 minutes | every pull request gate |
| Release candidate gate pipeline budget | 120 minutes | `release_evidence_gates` |
| Recovery point objective | 15 minutes | `disaster_recovery_restore` |
| Recovery time objective | 240 minutes | `disaster_recovery_restore` |
| CI artifact retention (transient, never evidence) | 90 days | every category |
| Release evidence retention | 400 days | `release_evidence_gates` |
| Release evidence freshness window | 14 days | `release_evidence_gates` |
| Inventory snapshot age warning | 30 days | `strategy_reconciliation` |
<!-- rendered:numbers:end -->

## 10. Accessibility conformance target

**The conformance target is WCAG 2.2 AA.** It is stated as a standard, version and level in the data file
(`accessibility.standard`, `accessibility.version`, `accessibility.level`) and the check fails on anything
else. The automated bar is conformance, not an impact threshold: a "critical only" gate would pass the
contrast and target-size defects most common on a money-display product, so the gate is zero violations
for every WCAG-tagged Level A and AA rule, and the check fails the data if that bar is weakened anywhere.
Web and admin run a named, version-pinned ruleset in every browser configuration listed below; Android
names its automated mechanism as well, so `ruleset_named_and_pinned` holds for all three surfaces. A rule
the scanner cannot decide is routed to the manual walkthrough rather than silently passing, and Switch
Access is mandatory on Android, not an alternative to a keyboard.

Acceptance is tied to the client state taxonomy, not only to the happy path: every applicable state in
`product/client-state-taxonomy.md` (section 8, accessibility requirements common to every state) is
asserted on each core journey, so an `error` that never moves focus, a `loading` that is never announced
or a `quota_exceeded` that re-announces on every return fails. That is what the named checks for 4.1.3
Status Messages and 3.3.1 Error Identification verify; an automated ruleset cannot decide them. Everything
below is rendered from the data.

<!-- rendered:accessibility:begin -->
**The conformance target is WCAG 2.2 AA.** Standard `WCAG`, version `2.2`, level `AA`.

**Automated gate (web and admin):** zero violations at any impact level for rules tagged WCAG 2.0, 2.1 and 2.2 Level A and AA on the core journeys; best-practice rules that are not WCAG success criteria are advisory; an exception requires a recorded reason and an expiry on the pull request.

| Surface | Target | Automated mechanism |
|---|---|---|
| web | WCAG 2.2 AA is the minimum for customer web: a named, pinned WCAG-tagged automated ruleset with zero violations at any impact level for rules tagged WCAG 2.0, 2.1 and 2.2 Level A and AA on the core journeys in every browser configuration in this file, plus keyboard-only and screen-reader walkthrough evidence covering every applicable client state | A WCAG-tagged automated ruleset named and version-pinned in the web gate configuration (the rules tagged WCAG 2.0, 2.1 and 2.2 Level A and AA), run on every core journey in every browser configuration; a rule the scanner cannot decide is routed to the manual walkthrough |
| admin | WCAG 2.2 AA is the minimum for the operator console: the same named, pinned WCAG-tagged ruleset with zero violations at any impact level for rules tagged WCAG 2.0, 2.1 and 2.2 Level A and AA on the operator journeys in every browser configuration in this file, plus keyboard-only operator walkthrough evidence | The same WCAG-tagged automated ruleset, named and version-pinned in the admin gate configuration, run on every operator journey in every browser configuration |
| android | Material accessibility baseline (TalkBack order and labels, 48dp touch targets, contrast, reduced motion, largest supported font scale) plus every applicable WCAG 2.2 AA content criterion, checked by Accessibility Test Framework checks in the instrumented suite and Android Lint accessibility rules with pinned versions on the large-text and TalkBack lanes, and walked through with TalkBack and Switch Access | Accessibility Test Framework checks enabled in the instrumented suite (or Compose semantics assertions for label, role, traversal order and 48dp targets) and Android Lint accessibility rules, versions pinned, run on the large-text and TalkBack emulator lanes |

**Browser configurations (web and admin core journeys):**
- Default desktop viewport
- Representative mobile viewport
- 200 percent zoom
- prefers-reduced-motion: reduce
- forced-colors: active

**WCAG 2.2 criteria that need a named check or a recorded manual step:**
- 2.4.11 Focus Not Obscured (Minimum)
- 2.5.7 Dragging Movements
- 2.5.8 Target Size (Minimum)
- 3.2.6 Consistent Help
- 3.3.7 Redundant Entry
- 3.3.8 Accessible Authentication (Minimum)

**Other WCAG criteria that need a named check, automated where the ruleset can decide them and otherwise a recorded manual step:**
- 1.4.3 Contrast (Minimum)
- 1.4.4 Resize Text
- 2.4.3 Focus Order
- 3.3.1 Error Identification
- 4.1.2 Name, Role, Value
- 4.1.3 Status Messages

**Manual walkthrough:**
- Screen reader on every core journey and every applicable client state on it, every monetary value announced with its meaning
- Keyboard-only (web, admin) and Switch Access (Android) completing every core journey and reaching every recovery action
- 200 percent text scaling and zoom without truncation or overlap; headlines wrap rather than clip
- High-contrast and forced-colors mode
- Reduced motion; no state depends on animation
- State never conveyed by colour or icon alone
- Client-state-taxonomy section 8 on each applicable state: entering the state is announced once with the published politeness (polite for loading, offline, stale and degraded; focus to the headline or an assertive announcement for error, permission_denied and quota_exceeded; focus to the rejected field for a validation error), a region-scope denial or quota state present on a later return is not re-announced and does not take focus, non-blocking notices never move focus, the recovery action is reachable by keyboard and switch, and controls disabled by a state expose the disabled state and its reason

**Client state taxonomy states asserted on every core journey:** `empty`, `loading`, `error`, `offline`, `stale`, `permission_denied`, `quota_exceeded`, `degraded`.

**Not claimed:** AAA criteria such as 2.4.13 Focus Appearance are covered by the manual walkthrough as an enhancement and are not part of the conformance claim.
<!-- rendered:accessibility:end -->

The gates are owned by `PenniLogic/web#7` (T-QA-06), `PenniLogic/android#15` (T-QA-08) and
`PenniLogic/admin#3` (T-QA-13). The strategy is deliberately stricter than the critical-only automated
wording those tickets inherited; the number is owned here.

## 11. Device matrix

Android is verified on the lanes below. **No lane runs anywhere yet.** The android `CI` job at publication
is checkout, toolchain setup, the quality-gate scripts and unit tests: it has no emulator, virtual-device
or instrumented step. Emulator lanes are therefore recorded as `provisionable_in_ci` - they can be hosted
on the standard GitHub-hosted runner and become gates only when `PenniLogic/android#15` (T-QA-08) wires
them; until then any lane evidence is produced locally and attached to the pull request, never claimed as
a CI result. Once wired, the API 31, current-release and large-text lanes are required on every pull
request and the remaining lanes on release candidates. The large-text lane runs at the largest font scale
and display size with reduced motion on; the TalkBack lane runs with the screen reader enabled and
asserts traversal order, labels, announcements and focus, so the accessibility promises in section 10
have an executable lane rather than only a release-candidate walkthrough.

**The strategy requires one mid-range physical Android device with an Indian SIM.** Real Indian bank and
wallet SMS formats and real carrier permission behaviour cannot be emulated, so this lane is the only one
that can observe them. The device is procured and provisioned by `PenniLogic/android#14` (T-QA-07), which
needs owner input on the device and SIM budget; **the device does not exist yet**, the lane is recorded as
`required_not_yet_available`, and the check fails if the data ever records it as available before that
issue is done. Until it is available, release-candidate evidence for that lane is absent and the release
evidence gates report it as a missing artifact rather than skipping it.

<!-- rendered:device_matrix:begin -->
| Lane | Kind | API level | Configuration | Purpose | Required for | Availability | Owning issues |
|---|---|---|---|---|---|---|---|
| `emulator_api_31` | emulator | 31 | Default text size, no assistive technology | Oldest supported release: permission and restricted-settings behaviour baseline | pull_request, release_candidate | provisionable in CI, not yet running | PenniLogic/android#15 (T-QA-08), PenniLogic/android#35 (T-QA-12) |
| `emulator_api_33` | emulator | 33 | Default text size, no assistive technology | Notification runtime permission and restricted-settings introduction | release_candidate | provisionable in CI, not yet running | PenniLogic/android#35 (T-QA-12), PenniLogic/android#57 (T-AND-07) |
| `emulator_current` | emulator | current | Default text size, no assistive technology | Current stable release (API 36 at publication), tracked by the behaviour-baseline ticket | pull_request, release_candidate | provisionable in CI, not yet running | PenniLogic/android#15 (T-QA-08), PenniLogic/android#57 (T-AND-07) |
| `emulator_large_text` | emulator | current | Font scale at the largest the platform offers, display size largest, reduced motion on | Largest supported text scale without truncation or overlap, 48dp targets and reduced-motion behaviour on every core screen and state | pull_request, release_candidate | provisionable in CI, not yet running | PenniLogic/android#15 (T-QA-08) |
| `emulator_talkback` | emulator | current | TalkBack enabled; traversal order, label, announcement and focus assertions from the Accessibility Test Framework | Screen-reader traversal of every core screen and applicable client state: announced once, focus target, monetary values announced with their meaning | release_candidate | provisionable in CI, not yet running | PenniLogic/android#15 (T-QA-08) |
| `managed_low_memory` | managed_device | n/a | Minimum-supported low-memory profile | Minimum-supported low-memory profile: cold start, 10000-row timeline, offline queue and background capture budgets | release_candidate | required, not yet available | PenniLogic/android#35 (T-QA-12), PenniLogic/android#15 (T-QA-08) |
| `managed_oem_variant_a` | managed_device | n/a | OEM build with aggressive background restrictions | First representative OEM variant with aggressive background restrictions: capture and recovery | release_candidate | required, not yet available | PenniLogic/android#35 (T-QA-12) |
| `managed_oem_variant_b` | managed_device | n/a | Second OEM build with aggressive background restrictions | Second representative OEM variant with aggressive background restrictions: capture and recovery | release_candidate | required, not yet available | PenniLogic/android#35 (T-QA-12) |
| `physical_mid_range_indian_sim` | physical | n/a | Mid-range device, Indian SIM, synthetic test account, wiped between campaigns | Real SMS and notification permission behaviour, structurally realistic test SMS receipt, cold-start and list budgets; the only lane that observes real carrier traffic | release_candidate | required, not yet available | PenniLogic/android#14 (T-QA-07), PenniLogic/android#15 (T-QA-08) |
<!-- rendered:device_matrix:end -->

## 12. Test data policy: synthetic only

**Production data never reaches any lower environment.** Every fixture, corpus entry, seeded environment
and evaluation case is synthetic: generated by a governed builder or transcribed into synthetic structure
under review. Pseudonymised production exports are still production data and are excluded. Raw SMS,
notification or email content never enters a fixture; a newly observed real format is transcribed, never
pasted, attached or quoted. Fixtures carry provenance and a version so a golden case can be traced without
the original, and automated privacy scans with planted identifiers run over corpora and fixtures. The same
data must not leak back out at runtime: logs, exception messages, failure screenshots and evidence
artifacts are scrubbed of money values, raw message text and personal data before they leave the process
or are uploaded, and the scrubber is fail-closed (`log_redaction_gate`, section 4).

Fixture families are **owned**, so repositories reuse governed builders and golden cases instead of
inventing incompatible data:

<!-- rendered:fixture_families:begin -->
| Fixture family | Description | Consumers | Owning issues |
|---|---|---|---|
| `money_generators` | Property generators for amounts, currencies, dates, schedules and split shares | PenniLogic/api, PenniLogic/android, PenniLogic/web | PenniLogic/api#22 (T-QA-01) |
| `parser_corpus` | Synthetic, structurally faithful bank and wallet message corpus with schema and privacy scan | PenniLogic/android | PenniLogic/android#35 (T-QA-12), PenniLogic/android#46 (T-PRS-01) |
| `ai_evaluation_corpus` | Governed synthetic evaluation cases with provenance, including adversarial and prompt-injection cases | PenniLogic/ai-service | PenniLogic/ai-service#7 (T-AI-06) |
| `client_state_fixtures` | Client state taxonomy data and worked examples used by the surface coverage assertions | PenniLogic/android, PenniLogic/web, PenniLogic/admin | PenniLogic/docs#1 (T-UX-01) |
| `seeded_synthetic_environment` | Seeded synthetic accounts, households and split groups for end-to-end, operator and load runs | PenniLogic/web, PenniLogic/admin, PenniLogic/api, PenniLogic/infra | PenniLogic/web#7 (T-QA-06), PenniLogic/admin#3 (T-QA-13), PenniLogic/infra#29 (T-QA-05) |
| `billing_replay_fixtures` | Purchase, renewal, refund, replay and forgery event fixtures | PenniLogic/api, PenniLogic/android | PenniLogic/api#48 (T-BIL-06) |
| `physical_device_test_account` | Synthetic test account and structurally realistic test SMS for the physical device | PenniLogic/android | PenniLogic/android#14 (T-QA-07) |
| `local_database_bootstrap` | Idempotent local PostgreSQL bootstrap for integration and migration tests | PenniLogic/api, PenniLogic/ai-service | PenniLogic/infra#2 (PenniLogic-old/infra#2) |
<!-- rendered:fixture_families:end -->

## 13. Privacy traffic inspection is not code review

Reading the code does not prove what leaves the device. The categories that require **traffic inspection
as distinct from code review** are `privacy_traffic_inspection` itself, every `android_client` change
(mandatory at release candidate), every `parser` change and every `release`. The evidence is produced by
`PenniLogic/android#16` (T-QA-09), which drives the core journeys through an intercepting proxy and
asserts no raw message text, no monetary value in analytics and no host outside the allowlist, and by
`PenniLogic/android#18` (T-CMP-03), which owns the payload-scrubbing hook and the component inventory the
allowlist is shared with. What is emitted at runtime on the backend is covered separately by the
`log_redaction_gate` owned by `PenniLogic/api#21` (T-PLT-04): a static rule that fails the build when a
money or personal-data type is logged and a runtime scan with a planted money value, on error paths as
well as the happy path. The release evidence gates read both evidence packs; a release checklist has a
documented source rather than a reviewer's reading of the diff.

## 14. Definition of Ready and Definition of Done

The canonical Definition of Ready and Definition of Done for a ticket is section 5 of
`product/03-delivery-plan.md`; `governance/DELIVERY.md` additionally requires the two self-review rounds
and the separate non-author review. This section does not replace either. It adds the test-evidence
requirements a ticket must meet in addition to them, so that the categories, floors and numbers above are
reached from the ticket lifecycle. Where the delivery plan and this section name the same item, the
delivery plan's wording is canonical; the mechanics of the STRIDE threat-model item (record format,
cadence and the command that checks it) are defined by its owner, `PenniLogic/docs#48` (T-QA-14), and
this section only requires that the record exist and cover the named scope.

A ticket may be started when every item below holds. The threat-model item requires a refreshed STRIDE
model for the epic that explicitly covers the ingestion boundary, raw content never leaving the device and
the parser-config signing chain, not only application-layer risks; the privacy item requires a payload
review naming which categories need traffic inspection rather than code review.

### Definition of Ready

<!-- rendered:definition_of_ready:begin -->
- [ ] `outcome_stated` -- Outcome stated in user-observable terms
- [ ] `acceptance_criteria_testable` -- Acceptance criteria are testable and name the verification categories mandatory for the ticket's change class
- [ ] `dependencies_unblocked` -- Dependencies identified and unblocked in the issue graph; no historical Done status is treated as current acceptance
- [ ] `estimated_and_sized` -- Estimated below the split threshold, with component and phase assigned
- [ ] `design_adr_settled` -- Design and decision records settled where the ticket touches an architectural decision; open decisions are consumed, never guessed
- [ ] `threat_model_refreshed` -- A dated STRIDE threat-model refresh for the epic with a named owner, explicitly covering the ingestion boundary, raw content never leaving the device and the parser-config signing chain as well as application-layer risks (PenniLogic/docs#48 (T-QA-14))
- [ ] `privacy_payload_reviewed` -- A privacy payload review for the epic: every outbound payload and analytics event the epic adds is classified against the shared allowlist, and the categories that need traffic inspection rather than code review are named (PenniLogic/android#18 (T-CMP-03), PenniLogic/android#16 (T-QA-09))
- [ ] `synthetic_fixtures_identified` -- The fixture families the ticket reuses or extends are named; no new ungoverned test data
- [ ] `inventory_snapshot_current` -- For the first ticket of an epic: the issue inventory snapshot has been refreshed and the strategy check passes
<!-- rendered:definition_of_ready:end -->

### Definition of Done

<!-- rendered:definition_of_done:begin -->
- [ ] `acceptance_criteria_met` -- Acceptance criteria demonstrably met, with evidence named according to the evidence rules
- [ ] `mandatory_categories_evidenced` -- Every category mandatory for the change class has a recorded pass signal on the merged head
- [ ] `coverage_floors_met` -- Line and branch coverage of every touched package meet the published floors, and money-path coverage did not decline
- [ ] `mutation_floor_met` -- Mutation score of every touched money-path package meets its published floor
- [ ] `flake_policy_respected` -- No test was retried beyond the published limit, no quarantine was added without an owning ticket, and no quarantined test was deleted without recorded approval
- [ ] `independent_review_recorded` -- Separate non-author Core review, QA for behaviour changes and the affected specialists recorded with session, reviewed commit and findings; no substantive finding unresolved
- [ ] `no_secrets_no_production_data` -- No secret, production data, raw message content or real financial record introduced; dependency additions reviewed against the SDK policy
- [ ] `money_integer_minor_units_verified` -- Money paths use integer minor units with currency, verified by a test rather than assumed
- [ ] `docs_adr_updated` -- Documents, decision records and this strategy's data updated when behaviour, a decision or a published number changed
- [ ] `observability_in_place` -- Observability in place for anything user-facing or failure-prone, including per-run publication of coverage, mutation score, flake rate and retry count against their floors
<!-- rendered:definition_of_done:end -->

## 15. Evidence retention and naming

A release checklist must be able to consume current results without relying on links to expired CI
artifacts. Every category's evidence is a file named
`<repository>__<category_id>__<commit_sha12>__<YYYYMMDD>.<extension>` (for example
`api__mutation_testing__0123456789ab__20261005.json`) whose content records at least the category id, the
owner reference, the commit SHA, when it was produced, the verdict, the measured value, the floor or
budget it was compared with and the strategy version. CI artifacts are transient and are never the source
of truth; release evidence is attached to the release record of the artifact it proves and retained for
the period in section 9.4. The release evidence gates accept an artifact no older than the freshness
window in section 9.4 and fail naming the missing or stale item and its owner. The numbers are `evidence`
in the data file.

## 16. Observability of the numbers

Per-package line and branch coverage, mutation score, flake rate and retry count are published on every
run against their floors and ceilings, so a slow decline is visible before it becomes a breach. Each
category's owning issue states how its pass or fail signal is observed (the last column of the category
table), and the release evidence gates read those signals rather than a checklist.

## 17. Review cadence and refresh

The strategy is re-checked, not validated once and left stale. The triggers are: before an epic's first
ticket leaves Ready (each epic boundary); when a repository, package or verification category is added,
renamed or removed; when any published number changes; before each release evidence gate run; and when
the inventory snapshot is older than the warning age in section 9.4. At each trigger the inventory is
refreshed with `python scripts/check_test_strategy.py --refresh-inventory` as `basiltt`, the check is run,
and any category left unowned by a closed-as-not-planned or missing issue is re-homed in the same pull
request. Bumping `strategy_version` follows the same rule as the client state taxonomy: patch for wording,
minor for an added category, package or number, major for a removed or relaxed one.

## 18. Regenerating the tables in this document

Every table, list and checklist between `rendered:*:begin` and `rendered:*:end` markers is produced by
`python scripts/check_test_strategy.py --render` from the data file. Edit the data, run the command, paste
each block between its markers, and run the check; the check fails on any difference, so the prose and the
data cannot drift apart.

## 19. Limitations and what remains open

- No harness, gate, coverage, mutation, accessibility, load, chaos, restore, emulator or device result is
  claimed. The check proves that every category has an owner and every package has a number; the owning
  issues prove execution when they are done.
- No emulator lane exists in `PenniLogic/android` CI at publication; every emulator lane is recorded as
  provisionable, and the gate that runs them is `PenniLogic/android#15` (section 11).
- The physical mid-range Android device with an Indian SIM is a requirement, not an asset:
  `PenniLogic/android#14` is blocked on owner input for the device and SIM budget.
- The mutation floors for `android.ledger` and `android.parsers` have no executable owner in
  `PenniLogic/android`; the gap is recorded in section 7.1 and an owner is requested from the
  coordinator. Until one exists, `mutation_floor_met` cannot be evidenced for those packages.
- The ai-service integration job has no owning issue; `integration_tests` is scoped to api.
- The package inventory is the planned layout; it is corrected by reviewed pull requests as the
  repositories grow, never inferred by a harness.
- Delivery-protocol enforcement in CI has no migrated owner and is not asserted (section 4).
- The repository READMEs are generated by `PenniLogic/infra/governance`; linking this strategy from them
  is a generated-setup request to the generator owner, not an edit in this repository.
