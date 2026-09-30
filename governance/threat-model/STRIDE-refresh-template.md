# STRIDE threat-model refresh template

Use this template to refresh the threat model for one epic. The result is not this document filled
in; it is one refresh entry appended to `governance/threat-model/records/<epic>.json`, validated by
`python scripts/check_threat_model.py`. The prose here tells you what to think about per category and
what evidence the record must carry. `README.md` in this directory explains the cadence, the triggers,
the Definition of Ready item and the record schema.

## Before you start

1. Confirm the epic identifier (`E01` to `E38`) and its public issue (`PenniLogic/docs#N`).
2. Read the epic body, every child ticket, the baseline model in
   `architecture/02-security-architecture.md` section 1, the compliance obligations table in
   `compliance/01-regulatory-landscape.md` and any accepted decision record the epic depends on. List
   them in `sources`.
3. Note the trigger: `definition_of_ready` for a first refresh, otherwise the trigger from
   `categories.json` that forced it.
4. Record who performs the refresh: the accountable GitHub owner, the session identifier and the
   agent role. In this organisation the owner is always the same account; the session is what
   distinguishes one refresh from another.
5. **Data subjects and flows.** Inventory every class of personal data the epic introduces or touches
   as a `data_flows` entry before you review the categories: what the data is (`data_class`), whose it
   is (`subjects`: users, household members, counterparties, research participants, operators,
   contributors), the purpose-registry entry, consent record or decision that permits it, or the
   ticket that will create one (`purpose_ref`, compliance O-1), the retention period and its source
   (`retention`, O-4), how erasure reaches it including derived and multi-subject copies
   (`erasure_path`, O-2, O-4, O-13), how the flow is conditioned on the age gate or why children
   cannot be subjects (`children`, O-6), and every processor or cross-border destination it reaches
   (`processors`, O-7). The checker rejects a refresh whose `information_disclosure` review is
   anything but `not_applicable` while `data_flows` is empty; a research study, an analytics event,
   a push notification, a support ticket and a public issue comment are all flows.

## Rules the checker enforces

- Every category in `categories.json` at the current `model_version` is reviewed. A refresh that
  reviews fewer categories is invalid, not partially credited.
- Each category carries a disposition and an analysis of at least 40 characters that says something
  checkable:
  `controlled` (a control **exists today**; `evidence` required and each item must name a public
  ticket, a decision record, a repository path or a test; a control that a ticket will build is not a
  control, it is a `finding` handed to that ticket), `accepted` (the risk is knowingly accepted; cite
  the accepting decision in `evidence`), `finding` (action needed; at least one finding listed), or
  `not_applicable` (the analysis says why, and which later epic or ticket first introduces the
  surface).
- Every finding names its category, severity, an attack path and a recommended control of at least
  40 characters each, and is either `handed_off` to an existing public ticket (`PenniLogic/<repo>#N`,
  never an epic and never a historical PenniLogic-old number), `closed` with a resolution of at least
  40 characters that names a public ticket, a decision record, a repository path or a test, or
  `open`. An open finding is unowned and blocks Definition of Ready for the epic until a ticket
  exists. Do not invent a ticket to make a finding disappear; leave it open and ask the coordinator.
- A `definition_of_ready` refresh names at least one ticket in `tickets_in_scope`; no string anywhere
  in the refresh may be blank.
- A refresh is dated with a calendar date and stays current for 12 weeks; the categories
  reviewed are those of the `model_version` you name.
- The record contains attack paths and controls only: no credential, no live endpoint, no customer
  or participant data. The checker rejects URLs, `host:port` and IPv4 endpoints, `www.` hostnames
  and common key shapes anywhere in a record; cite repository paths and issue identifiers instead.

## PenniLogic-specific prompts every refresh answers

The test strategy (`governance/test-strategy.md` section 14) requires the refresh to cover three
things explicitly, not only application-layer risks. Answer them inside the categories named:

- **The ingestion boundary** (`information_disclosure`, `tampering`): where does captured message,
  notification, statement or receipt content stop and structured data begin? What crosses that
  boundary, in which direction, and what proves nothing else does?
- **Raw content never leaves the device** (`information_disclosure`): which code paths could carry a
  raw SMS, notification or statement string off the device (logs, analytics, crash reports, prompts,
  sync, support attachments), and which test or traffic capture proves they do not (compliance O-8)?
- **The parser-config signing chain** (`tampering`, `spoofing`): who signs remotely updatable parser
  rules and templates, how the device verifies them, how a key is rotated or revoked, and what a
  device does with an unsigned or downgraded configuration?

An epic that touches none of these says so under the category with a reason, exactly as for
`not_applicable`.

## Per-category prompts and required evidence

Each subsection lists the questions to answer in `analysis` and the evidence a `controlled` or
`accepted` disposition must cite. Evidence is a reference: a document path with section, an accepted
decision record, a public ticket identifier, a test name or a check in this repository.

### `spoofing` — Spoofing (S) · owner: security review

- Who or what must prove identity in this epic: users, devices, services, workflow jobs, webhook
  senders, third-party actions, research participants, the organisation itself?
- Can a stolen, replayed or forged credential, token, receipt or message pass? Where is the trust
  root (relying-party identifier, identity provider, signing key, commit pin) and who can change it?
- Do test identities, sandbox keys or mock providers exist, and can they be accepted outside tests?
- Evidence: the identity-verification design or decision record; the test that a forged or replayed
  credential is rejected; the pinning or allowlist that fixes the trust root.

### `tampering` — Tampering (T) · owner: security review, supporting money review

- What can be modified: ledger rows, migrations, parser rules, tokens, configuration, generated
  governance files, build inputs, design packages, test gates, quarantine lists, evidence artifacts?
- What makes modification detectable: append-only storage, hash chains, checksums, signatures,
  pinned versions, protected branches, regeneration checks?
- Can a displayed or computed value disagree with the authoritative one (client-side arithmetic,
  divergent rounding, unsynchronised caches)?
- Evidence: the integrity control by name; the gate or test that detects a planted modification.

### `repudiation` — Repudiation (R) · owner: security review, supporting compliance review

- Which actions must be attributable later: operator views and exports, approvals, consents and
  their versions, opt-outs, waivers, deployments, assignments, refreshes like this one?
- Is the trail append-only, time-synchronised, retained as long as the obligation requires, and
  attributed to a session or account rather than a shared identity?
- Where a single account performs many roles, is the procedural separation written down?
- Evidence: the audit or log location and retention; the attribution rule; the tamper test.

### `information_disclosure` — Information disclosure (I) · owner: privacy review, supporting security review

- Which data classes does the epic touch: raw messages, financial values, identity, keys, research
  participant material, secrets, analytics events, screenshots, captured traffic? Every class is a
  `data_flows` entry with its subjects, purpose, retention, erasure path, age-gate conditioning and
  processors (see "Before you start", step 5).
- Where could each leak: logs, fixtures, prompts, analytics payloads, notifications and their
  previews, push or e-mail providers, public repositories, third-party tools, small-cohort
  dashboards, error messages, the clipboard?
- Who else is a subject besides the account holder: household members and counterparties inside a
  user's records, research participants, operators, contributors? Can a child be one, and what stops
  it (compliance O-6)?
- What minimises, encrypts, redacts, coarsens or scrubs it, and is that a test rather than a review?
  Does erasure reach every copy, including derived values, multi-subject records and processors?
- Evidence: the data-class inventory; the purpose-registry or consent record, or the ticket that
  will create it; the scrubbing or allowlist gate; the encryption or access rule.

### `denial_of_service` — Denial of service (D) · owner: reliability review, supporting security review

- What can be exhausted: request capacity, quota, provider spend, runner minutes, API rate limits,
  storage, on-call attention, shared environments hit by test traffic?
- What bounds it: rate limits, budgets with alerts, timeouts, concurrency limits, kill switches,
  circuit breakers, target allowlists for load and chaos tools?
- Evidence: the published limit or budget; the test that the limit bites.

### `elevation_of_privilege` — Elevation of privilege (E) · owner: security review

- Where are authorisation decisions made, and are they server-side and default-deny? Can a client,
  a workflow token, a fork, a support role or a test fixture reach a higher capability?
- Can row-level security, the policy engine or the operator boundary be bypassed by a connection
  role, a trusted setter or a shared process?
- Evidence: the policy or role design; the negative test that denies the escalation.

### `billing_forgery` — Billing forgery · owner: money review, supporting security review

- Is every purchase, renewal, refund, chargeback and promotional event verified with the provider
  server-side before an entitlement or a balance changes?
- Are webhooks and callbacks authenticated, idempotent and replay-safe? Are trials, promotions and
  refund cycling bounded? Is money carried as integer minor units with currency end to end?
- Evidence: the verification design (decision record, contract, ticket); the replay and
  reconciliation tests; the provider sandbox boundary.

### `entitlement_tampering` — Entitlement tampering · owner: security review, supporting money review

- Is entitlement resolved server-side on every protected action? Does any client hold or display
  state the server did not just produce? Can a cached or replayed entitlement pass?
- Are quota reservation and reconciliation atomic and is the reset boundary fixed? How are
  bring-your-own-key users, plan changes and cross-channel subscriptions treated?
- Do components or screens offer an unlock, dismiss or retry that changes access locally?
- Evidence: the entitlement decision record and contract; the bypass scenarios in the attack suite.

### `ai_service_compromise` — AI service compromise · owner: security review, supporting reliability review

- Where do platform and user provider keys live, who can read them, and how are they rotated and
  revoked? Which destinations and models are allowed, and who changes the allowlist?
- Can a compromised gateway or provider response reach a money or data path without passing through
  deterministic tools? Are spend caps, circuit breakers and the kill switch proven to work?
- Do evaluation or load runs in continuous integration spend real money or expose keys?
- Evidence: the egress and runtime decision record; the gateway, spend-cap and kill-switch tickets
  and their tests.

### `request_forgery` — Request forgery · owner: security review

- Can a browser be made to issue a state-changing request against a customer or operator session
  (same-site cookies, anti-forgery tokens, origin checks)?
- Does the server fetch any user- or partner-supplied URL (custom AI endpoints, callbacks, import
  sources, scanners)? Are private, loopback, link-local and metadata destinations denied, and is
  resolution pinned?
- Are provider callbacks authenticated and idempotent? Can a signed request be replayed?
- Evidence: the egress policy; the adversarial request-forgery suite; the header and session tests.

### `prompt_injection` — Prompt injection · owner: security review, supporting privacy review

- Which untrusted strings reach a model or an AI agent: merchant names, message text, imported
  statements, notes, tool results, public issue or pull-request comments read by a delivery session?
- How are they delimited (structured tool results, never free text in a system prompt)? Is the tool
  allowlist immutable at runtime and does every state-changing tool require confirmation?
- Is model output rendered as text only, never executed or auto-followed? Do adversarial cases and
  red-team scenarios exercise each channel?
- Evidence: the runtime rule in the decision record; the defence and evaluation tickets and tests.

### `split_manipulation` — Split manipulation · owner: money review, supporting security review

- Are share computations deterministic in integer minor units with one published remainder rule
  that the ledger, the clients and the independent model all implement?
- Who may change a split after settlement? Are settlements append-only and visible to every
  counterparty? Does erasure of one member preserve the other members' evidence of the debt?
- Can adding, removing or disputing shift a balance without the counterparty's consent?
- Evidence: the money conventions decision record; the split ledger and authorisation tickets; the
  independent-model harness scenarios.

### `administrative_identity_compromise` — Administrative identity compromise · owner: security review, supporting compliance review

- Is the operator identity domain separate from the customer domain? Are elevation, unmask and bulk
  export four-eyes and time-boxed? Is break-glass recorded and re-keyed? Are joiner, mover, leaver
  and recertification defined?
- For this organisation: which account or credential controls the repositories, rulesets, Project,
  research tools and design files, and what is its hardening baseline and revocation drill?
- Do component or flow designs afford self-approval or hide who approved?
- Evidence: the administrative boundary decision record; the identity, lifecycle and audit tickets;
  the account baseline; the operator red-team suite.

## Writing the record

Append one object to `refreshes` in the epic's record. The `README.md` field table is the schema in
prose; `schema.json` is the schema the checker uses. Then run:

```text
python scripts/check_threat_model.py
python scripts/check_threat_model.py --epic <epic>
python scripts/check_threat_model.py --ticket PenniLogic/<repo>#N
```

The first command must pass. The second passes only when the epic is `current`; `blocked` means an
open finding needs a ticket, which is a correct result to report, not something to hide. The third is
the per-ticket gate: it passes only when the ticket is listed in `tickets_in_scope` of the epic's
latest refresh and that refresh is current, so a ticket added to an epic after its refresh, or one
that introduces a new data class, trust boundary, external party, AI capability, sharing path or
money flow, needs a `scope_changed` refresh that lists it before it is Ready.
