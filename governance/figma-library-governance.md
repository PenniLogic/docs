# Figma library governance and component contribution contract

Plan task T-DSY-02, [PenniLogic/docs#78](https://github.com/PenniLogic/docs/issues/78). Draft contract
(version in section 11): proposed by this source change and awaiting the Design Systems, DesignOps, Accessibility,
UX Engineering and CDO decisions. Nothing here is an approval, a Figma permission change, a published
library or live evidence.

Records live in [`figma-libraries.json`](figma-libraries.json), validated against
[`figma-libraries.schema.json`](figma-libraries.schema.json) by `python scripts/check_figma_libraries.py`
(complete check; prints `NOT GREEN: readiness incomplete` with exact gap counts until every held input
exists) or `--structure` (structure only). Section 11 is generated from the JSON by `--mirror` and a unit
test fails when it drifts; the other sections are the contract text.

## 1. Sources and boundaries

| Input | Used for | Owner |
| --- | --- | --- |
| [`design-gates.json`](design-gates.json) | Role IDs, the `components` and `foundations_tokens` artifact classes (accountable and responsible roles), reserved Figma files and pages, the proposal-branch pattern, the `shared_system_major` CDO-equivalent scope | docs#64 (accepted, byte-pinned; read only) |
| [`design-operations.md`](design-operations.md) section 6 | Figma topology, branch grammar, SemVer classes, promotion, archive, restoration and rollback freeze | docs#64 (read only; section 5 below adds H07's labelled proposals on top of it) |
| [`design-operations.md`](design-operations.md) section 7 | Default-deny grants, no public links or external sharing, offboarding revocation | docs#64 (read only) |
| Imported registry `planning/source/evidence/experience-coverage.json` at `1722fc79` | Component IDs (`C-*`) and their platforms, pinned by commit, path and sha256 (`registry_ref`) | docs#75 (moves to `product/experience-coverage.json` when docs#75 integrates; the re-pin changes `registry_ref` and the checker's `REGISTRY_PIN` together, then regenerates section 11 and updates the published-data test expectations) |
| docs#76 visual direction (D2) | `direction_ref`; stays `null` until the decision exists | docs#76 (held) |
| docs#55 token grammar | `token_refs`; stays empty until a grammar is published | docs#55 (held) |

This contract owns library governance metadata and checks only. It does not select a visual direction,
define tokens, allocate registry IDs, edit the registry or its generated output, or change any Figma
account, plan, permission, link or export setting.

## 2. Library topology

Six libraries, in a strict layer order; a library may consume only libraries of a lower layer and must
consume the layers it builds on: `LIB-COMPONENTS` consumes `LIB-FOUNDATION`; the platform-variant and
candidate libraries consume both (`topology.invalid_consumption`, `topology.missing_dependency`).

| Library | Layer | Role in the system | Reserved location |
| --- | --- | --- | --- |
| `LIB-FOUNDATION` | 0 | Foundations and assets; token values arrive from docs#55, never authored here | `02 - Foundations library` / `Foundations` |
| `LIB-COMPONENTS` | 1 | Shared semantic components: one semantic contract per component, whichever platforms support it | `03 - Components library` / `Components` |
| `LIB-ANDROID`, `LIB-WEB`, `LIB-ADMIN` | 2 | Platform variants; each record is a variant of one `LIB-COMPONENTS` component and supports only its own platform | `03 - Components library` / `Android variants`, `Web variants`, `Admin variants` |
| `LIB-CANDIDATE` | 3 | Feature-squad contribution candidates; no shared file, never published | none (proposal branches only) |

Owners are the accountable role of the artifact class in `design-gates.json` (`systems` for both
classes); no person is named. Library `status` is `shell` (no published release), `active` (a published
release exists) or `frozen` (rollback freeze, section 7). Today every library is an empty governed
`shell`: the rollout publishes empty shells before component work, and even that publication is held
(section 10).

## 3. Component records

Each record is keyed by its registry `C-*` ID in the ID-authority grammar `C-[A-Z0-9]+(-[A-Z0-9]+)*`
(at most 64 characters); `C-SYN-*` is reserved for test fixtures and refused in this data
(`id.synthetic_reserved`). Pinned IDs are read with the registry schema's own grammar `C-[A-Z0-9-]+`, so
a pinned ID outside the record grammar never fails the check: it cannot have a record and stays a
readiness gap. A record keyed by a pinned ID copies the pinned name verbatim
(`component.registry_name_mismatch`, so a registry rename surfaces at the re-pin) and supports exactly
the pinned platforms (`component.registry_platform_mismatch`). IDs absent from the pin and pinned IDs
without a record are readiness gaps, never structure failures.

Lifecycle: `draft` (imported, unpublished) -> `candidate` (`LIB-CANDIDATE` only) -> `published` ->
`deprecated`. Status `candidate` holds exactly in `LIB-CANDIDATE` (`contribution.candidate_library`).
The ticket's rollout phrase "existing drafts import as unpublished candidates" is implemented as
status `draft` in `LIB-COMPONENTS`, not as this contract's `candidate` state (a squad proposal). A published or deprecated record (criterion 1) must name an owner role that maintains its
library, a description, a semantic role, a non-empty property contract, accessibility behavior (role,
accessible name, focus, announcements), supported platforms, and a `since_version` that is a published
release of its library (`published.*` rules). Property contracts have unique names; enums carry at
least two values and a default from that list (or none); booleans default to `true`, `false` or none;
text may carry a default; slots and instances carry no values and no default; names are unique after
case and punctuation normalization (`component.property_contract`).

**Proposed placement (awaiting Design Systems confirmation).** All pinned components are imported as
unpublished `draft` records in `LIB-COMPONENTS` with their pinned platforms (`shared` = android, web and
admin). Platform libraries hold only variants of a `LIB-COMPONENTS` component, and the registry records
semantic components, not variants, so single-platform components (for example the admin-only operator
components) keep a semantic record limited to their platform. Platform-variant records, semantic roles,
descriptions, property contracts and accessibility behavior are Design Systems content for the registry's
design tickets (T-DSY-04, T-DSY-05, T-DSY-06); this change authors none of them. `owner_role` is
`systems`, the accountable role for components. No component is published (`held.publication`) because
no visual direction is selected.

## 4. Contribution flow

1. **Request.** A feature squad (`android_design`, `web_design`, `admin_design`: the owners of the
   platform product files) proposes a component as a `candidate` in `LIB-CANDIDATE`, owned by the
   proposing role (`owner_role`), with a semantic role and a non-empty property contract so the
   duplicate lint can judge it (`contribution.candidate_incomplete`), on a proposal branch or proposal file named by the
   [`design-operations.md`](design-operations.md) section 6 grammar
   `<plan-ticket>__<squad>__<change-slug>` with a known squad (`contribution.branch_grammar`). The
   branch's squad is the squad of the proposing owner role's reserved file (`contribution.squad_mismatch`),
   and a branch backs one record only, because a reused branch stops promotion
   (`contribution.branch_duplicate`). Proposal branches belong to candidates only
   (`contribution.branch_outside_candidates`). The permission model lets feature squads edit
   `LIB-CANDIDATE` (their candidates) but never edit or publish a shared library directly (section 8).
2. **Duplicate review (criterion 2).** Before review, the registry lint compares every record with every
   published or deprecated record of every shared library (`LIB-COMPONENTS` and the platform libraries).
   Names and semantic roles are compared as lower-case word sets with a plural `s` dropped, so word
   order, case, punctuation and plurals do not hide a duplicate. A record is a duplicate when its name or
   semantic role equals the other's, or when it contains the other's whole property signature (property
   names and types) and shares a name or role word with it; an equal signature alone is not a duplicate,
   because distinct components may share property names and types (`duplicate.semantic_component`). The
   only exemptions are a record and its own platform parent or variant, and a declared replacement pair;
   two variants of one parent are compared like any other pair. A published variant needs a published
   parent (`component.variant_parent_unpublished`). The lint matches words, not meaning: synonyms are
   left to the Design Systems review, and reviewers reuse the published component instead.
3. **Review and test.** Design Systems (`systems`) reviews the candidate against the published-component
   contract (section 3); Accessibility, UX Engineering and Design QA verification follow the gate rules of
   [`design-operations.md`](design-operations.md) sections 3 and 6. Promotion needs the evidence that
   section 6 lists (descriptions, property names, variants, accessibility notes, content limits, code
   targets, a versioned manifest, consumer compatibility evidence, independent verification, fresh gates).
4. **Release.** Only the assigned Systems context prepares promotion and DesignOps serializes it from
   the last recorded canonical revision (section 6). The accepted candidate becomes a new record in the
   target library under its registry ID. The candidate record leaves `figma-libraries.json` in the same
   change and survives only in Git history (kept beside its promoted record it would be refused as a
   duplicate); it is never published itself (`component.candidate_published`).

## 5. Versioning, release notes and dependency updates

Releases are keyed by (library, SemVer) and form one linear chain per library through `previous`: the
previous version exists and is lower, each library has exactly one root release and each release has at
most one successor (`release.previous_unknown`, `release.version_not_increasing`, `release.chain_invalid`).
[`design-operations.md`](design-operations.md) section 6 defines the classes by content (patch fixes
without contract change, minor additive components/tokens, major breaking changes; coordinator approval
only for a shared-system major). The table cites those classes; the exact version arithmetic, additive
properties as minor content and the first-release row are **H07 proposals awaiting Design Systems,
DesignOps and CDO confirmation**, not section 6 text. The class must match the version step exactly
(`release.class_mismatch`):

| Class | Version step | Content | Decision right |
| --- | --- | --- | --- |
| patch | `x.y.z` -> `x.y.(z+1)` | Fixes without a contract change | Design Systems (`systems`) |
| minor | `x.y.z` -> `x.(y+1).0` | Additive components, properties or tokens | Design Systems Lead (`systems`, accountable) |
| major | `x.y.z` -> `(x+1).0.0`, or a first `x.0.0` (proposal) | Breaking component or token changes; first releases (proposal) | CDO (`decision_coordinator` within `shared_system_major`) |

Proposal: a library's first release is classified major and therefore carries a CDO record, so each
empty shell's `1.0.0` is behind a `pending` CDO decision (section 11). If section 6 is confirmed to
cover breaking changes only, the first-release row is dropped and those five gaps go with it.

Breaking changes (criterion 3) must be major (`release.breaking_not_major`), carry a migration plan
reference (`release.migration_plan_missing`) and a CDO approval record (`release.cdo_approval_missing`).
References are `PenniLogic/<repo>#N` or `pending:PenniLogic/<repo>#N`; free text is refused
(`reference.invalid`). A CDO record is `pending` with no decision source, or `recorded` with a
`{commit, path, sha256}` decision source (`approval.source_mismatch`). A pending CDO approval or a pending
migration plan blocks publishing (`release.cdo_pending_published`,
`release.migration_plan_pending_published`), and a published release must sit on a published previous
release (`release.previous_unpublished`), so nothing pending lies below a published version. Every
`pending:` migration plan is a visible gap (`readiness.migration_plan_pending`). No session in this change records a CDO decision
(`held.cdo_recorded`); a recorded decision is reported as `readiness.cdo_decision_unverified` until it
can be verified, never as a pass.

Release notes are the release record plus the pull request that changes it; consumers update by pinning
the new library version in their D6 handoff (section 6 of `design-operations.md`: D6 pins
platform/library/frame versions). Expand, migrate consumers, then retire: no silent replacement.

## 6. Deprecation and migration

A deprecated component (criterion 4) keeps its record and its status `deprecated`; the deprecation
record names:

- a replacement: another published component of the same library (`deprecation.replacement_missing`,
  `deprecation.replacement_invalid`);
- a removal version: a major `N.0.0` above the library's current published major, because removal is a
  breaking change (`deprecation.removal_version_missing`, `deprecation.removal_version_invalid`);
- continued availability until that removal (`deprecation.unavailable`).

A deprecation record on a non-deprecated component, or a deprecated component without one, is refused
(`deprecation.unexpected`, `deprecation.missing`). The removal itself is a breaking major release under
section 5 (migration plan and CDO approval).

## 7. Rollback and restoration

Rollback unpublishes a bad version and restores the prior library without deleting dependent
instances. A `rolled_back` release names `rollback_to`, which must be its own `previous` version and a
published release of the same library; any other release keeps `rollback_to` empty
(`release.rollback_target`). Under [`design-operations.md`](design-operations.md) section 6 the rollback
also appends a publishing-freeze decision, preserves every proposal, decision and version, keeps the last
verified library available read-only and stops promotion. The validator enforces the freeze on the
records: a library is `frozen` exactly when it has a `rolled_back` release (`library.freeze_mismatch`),
and because a published release needs a published previous release on a linear chain, nothing above the
rolled-back version can be published (`release.previous_unpublished`). Restoration copies a known
snapshot into a new higher version (a draft), does not clear the freeze and does not inherit the old
approval. This source has no enable-publishing action. Process obligation, not checked by the validator:
component records are not removed by a rollback, so dependent instances keep resolving (record removal
is not detected across revisions; section 10).

## 8. Permission model and offboarding (criterion 5)

| Action | Who the model permits | Rule |
| --- | --- | --- |
| publish to a shared library | only its named maintainer roles (`publish_roles`, a subset of the artifact class's responsible and accountable roles: `systems`) | `permission.publish_not_maintainer` |
| publish to a shared library by a feature squad | never | `permission.feature_squad_publish` |
| publish to `LIB-CANDIDATE` | never; candidates have no publish roles | `permission.candidate_publish` |
| edit a shared library | its maintainers only; squads contribute through proposal branches | tabletop |
| edit `LIB-CANDIDATE` | feature squads (their candidates, on their own proposal branches) and the maintainers | tabletop |
| view, comment | any known role that is not offboarded; real access still needs a default-deny grant under section 7 of `design-operations.md` | tabletop |
| public link, external sharing, asset export | nobody (E34-F06) | `access.public_links`, `access.external_sharing`, `access.asset_export` |
| any action after offboarding | nobody; offboarding revokes every grant and session | `access.offboarding_not_revoking` |

`model_permitted` means only that this role model would allow the request once real access is verified
and publishing is enabled by a separate authorized decision. Today
[`design-operations.md`](design-operations.md) section 7 grants no publish action and every live Figma
request fails until real access has been verified; nothing here changes that.

The tabletop (section 11) applies the model to synthetic requests. Every scenario is
`evidence_class: tabletop` with `live_verified: false` (`tabletop.live_claim`); its expected outcome must
equal the model's decision (`tabletop.outcome_mismatch`), and it must cover a non-offboarded feature
squad and an offboarded maintainer publishing to each shared library, a public link, an export and a
feature squad editing a candidate in `LIB-CANDIDATE` (`tabletop.coverage_missing`). A tabletop is not Figma enforcement: live publishing, offboarding and
external-access audit evidence stay missing (`readiness.live_verification_missing`).

## 9. Observability (definitions only)

Measured per platform once real libraries exist; no data is collected or reported by this change.

| Metric | Definition |
| --- | --- |
| Library adoption | Instances of published library components divided by all component instances in a platform product file |
| Duplicate components | Records or local components refused by `duplicate.semantic_component`, and their open count |
| Deprecated instances | Instances of `deprecated` components still in use, with the removal version they block |
| Review age | Time from a candidate's proposal to its accepted or rejected review decision |
| Version lag | Published major and minor versions between a platform's pinned library version and the latest published one |

## 10. Acceptance status and held gates

The validator refuses a structure failure with a static rule ID plus, at most, identifiers that passed
their own grammar; it never echoes input text and fails closed. Its default mode reports every readiness
gap (section 11 lists the current counts) and stays `NOT GREEN` while any exists.

| Item | Status in this change |
| --- | --- |
| Criterion 1: published-component contract | Rules and synthetic published fixtures; no real component is published |
| Criterion 2: duplicate rejected by review and lint | Registry lint and fixtures; review by Design Systems is process, not yet exercised |
| Criterion 3: breaking change needs major, migration plan, CDO | Rules and fixtures; every real CDO approval is `pending` |
| Criterion 4: deprecation replacement, removal version, availability | Rules and fixtures |
| Criterion 5: feature squads cannot publish to shared libraries | Permission model and synthetic tabletop only; live Figma enforcement unverified |
| DoD 1: topology and contribution contract operational | Authored as a draft; not operational until live access, publishing and the decisions below exist |
| DoD 2: Design Systems, DesignOps, Accessibility, UX Engineering, CDO approvals | `not_recorded` (section 11) |
| DoD 3: versioning, permission and duplicate tests pass | `scripts/tests/test_figma_libraries.py` (synthetic fixtures; no network) |
| DoD 4: native blocked-by edges | Administrative; not changed here |

Held: the docs#76 direction decision (`direction_ref` stays `null`); the docs#55 token grammar
(`token_refs` stay empty); authorized access to the real governed Figma libraries and live verification
of publishing, offboarding and external-access audit; the Design Systems, DesignOps, Accessibility,
UX Engineering and CDO decisions; independent reviews and native CI on the exact head; re-pinning the
registry after docs#75 integrates.

## 11. Generated records (do not edit)

Regenerate with `python scripts/check_figma_libraries.py --mirror` and replace the marked block; the
unit tests fail when it differs from the JSON.

<!-- BEGIN GENERATED: governance/figma-libraries.json (check_figma_libraries.py --mirror) -->

Contract version 0.1.0; registry pin 1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4 planning/source/evidence/experience-coverage.json; direction reference -.

### Library topology

| Library | Kind | Layer | Figma file | Figma page | Owner role | Publish roles | Consumes | Status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| LIB-FOUNDATION | foundation | 0 | 02 - Foundations library | Foundations | systems | systems | - | shell |
| LIB-COMPONENTS | shared_semantic | 1 | 03 - Components library | Components | systems | systems | LIB-FOUNDATION | shell |
| LIB-ANDROID | platform_variant | 2 | 03 - Components library | Android variants | systems | systems | LIB-FOUNDATION, LIB-COMPONENTS | shell |
| LIB-WEB | platform_variant | 2 | 03 - Components library | Web variants | systems | systems | LIB-FOUNDATION, LIB-COMPONENTS | shell |
| LIB-ADMIN | platform_variant | 2 | 03 - Components library | Admin variants | systems | systems | LIB-FOUNDATION, LIB-COMPONENTS | shell |
| LIB-CANDIDATE | candidate | 3 | - | - | systems | - | LIB-FOUNDATION, LIB-COMPONENTS | shell |

### D14 component dependency and variant map

- LIB-FOUNDATION consumes -; 0 component records; variants: -
- LIB-COMPONENTS consumes LIB-FOUNDATION; 57 component records; variants: -
- LIB-ANDROID consumes LIB-FOUNDATION, LIB-COMPONENTS; 0 component records; variants: -
- LIB-WEB consumes LIB-FOUNDATION, LIB-COMPONENTS; 0 component records; variants: -
- LIB-ADMIN consumes LIB-FOUNDATION, LIB-COMPONENTS; 0 component records; variants: -
- LIB-CANDIDATE consumes LIB-FOUNDATION, LIB-COMPONENTS; 0 component records; variants: -

### Releases

| Release | Previous | Change | Breaking | Status | Migration plan | CDO approval | Rollback to |
| --- | --- | --- | --- | --- | --- | --- | --- |
| LIB-FOUNDATION@1.0.0 | - | major | no | draft | - | pending | - |
| LIB-COMPONENTS@1.0.0 | - | major | no | draft | - | pending | - |
| LIB-ANDROID@1.0.0 | - | major | no | draft | - | pending | - |
| LIB-WEB@1.0.0 | - | major | no | draft | - | pending | - |
| LIB-ADMIN@1.0.0 | - | major | no | draft | - | pending | - |

### Component records and proposed placement

| Component | Name | Library | Status | Platforms | Variant of | Owner role | In registry pin |
| --- | --- | --- | --- | --- | --- | --- | --- |
| C-ACTION | Primary secondary tonal text and icon actions | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-ACTION-FAB | Contextual Android floating action button | LIB-COMPONENTS | draft | android | - | systems | yes |
| C-ACTION-MENU | Menu context menu and command action | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-AI-ANSWER | Model answer citation refusal and override | LIB-COMPONENTS | draft | android, web | - | systems | yes |
| C-BILLING-PLAN | Plan channel quota invoice and lifecycle | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-AMOUNT | Currency amount balance and delta | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-CHART | Accessible financial chart with table equivalent | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-COMPARISON | Neutral strategy and scenario comparison | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-DEBT | Debt summary schedule and status | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-DERIVATION | Explain why this number derivation | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-GOAL | Goal contribution and progress | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-HOLDING | Holding valuation and composition | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-LIST | Responsive list and card collection | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-PROGRESS | Debt goal and milestone progress | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-PROVENANCE | Source confidence freshness and provenance | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-SEARCH | Search filter sort and saved view | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-STATUS | Typed status and state badge | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-TABLE | Data table pagination selection and bulk action | LIB-COMPONENTS | draft | web, admin | - | systems | yes |
| C-DATA-TIMELINE | Chronological transaction bill and event timeline | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-DATA-TRANSACTION | Transaction summary and detail | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-FEEDBACK-BANNER | Persistent system and risk banner | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-FEEDBACK-ERROR | Inline error summary retry and recovery | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-FEEDBACK-SNACKBAR | Transient snackbar and toast status | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-FEEDBACK-STATUS | Skeleton progress empty and completion feedback | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-FEEDBACK-UNDO | Time-bounded undo and reversal action | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-INPUT-DATE | Date time and quiet-hours input | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-INPUT-FILE | File receipt and attachment input | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-INPUT-MONEY | Integer minor-unit money input | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-INPUT-OTP | Verification and recovery code input | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-INPUT-PASSKEY | Passkey and biometric action | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-INPUT-RATE | Rate and percentage input | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-INPUT-SELECT | Select autocomplete chips radio and checkbox | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-INPUT-SLIDER | Exact-value slider with keyboard and switch alternative | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-INPUT-SWITCH | Boolean and preference switch | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-INPUT-TEXT | Text and multiline input | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-NAV-ADMIN | Role-aware admin side navigation and queue switcher | LIB-COMPONENTS | draft | admin | - | systems | yes |
| C-NAV-ANDROID | Android app bar navigation bar rail and drawer | LIB-COMPONENTS | draft | android | - | systems | yes |
| C-NAV-STEPPER | Onboarding and high-risk task stepper | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-NAV-WEB | Customer web side navigation drawer breadcrumbs and tabs | LIB-COMPONENTS | draft | web | - | systems | yes |
| C-OP-AUDIT | Immutable audit timeline and verification | LIB-COMPONENTS | draft | admin | - | systems | yes |
| C-OP-CLOCK | SLA statutory and elevation clock | LIB-COMPONENTS | draft | admin | - | systems | yes |
| C-OP-DIFF | Before after impact and immutable change diff | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-OP-INCIDENT | Anomaly incident and blocked action | LIB-COMPONENTS | draft | admin | - | systems | yes |
| C-OP-QUEUE | Operator queue assignment and SLA ordering | LIB-COMPONENTS | draft | admin | - | systems | yes |
| C-OP-REDACTED | Redacted value and authorized reveal | LIB-COMPONENTS | draft | admin | - | systems | yes |
| C-OVERLAY-CONTAINER | Dialog alert sheet drawer and focus container | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-OVERLAY-TOOLTIP | Popover and tooltip disclosure | LIB-COMPONENTS | draft | web, admin | - | systems | yes |
| C-TRUST-ACCESSLOG | Subject-visible access event | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-TRUST-APPROVAL | Provenance and four-eyes approval | LIB-COMPONENTS | draft | admin | - | systems | yes |
| C-TRUST-CONSENT | Purpose consent and withdrawal | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-TRUST-DESTRUCTIVE | Destructive action consequence and recovery | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-TRUST-DISCLOSURE | Projection AI billing and policy disclosure | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-TRUST-GRANT | Per-person category aggregate and detail grant | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-TRUST-PERMISSION | Permission rationale status and recovery | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-TRUST-PRIVACY | Privacy mask lock and concealment | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |
| C-TRUST-SAFEEXIT | Discreet exit and duress concealment | LIB-COMPONENTS | draft | android, web | - | systems | yes |
| C-TRUST-STEPUP | Step-up cooling-off and recovery restriction | LIB-COMPONENTS | draft | android, web, admin | - | systems | yes |

### Permission and offboarding tabletop (synthetic, not live-verified)

| Scenario | Action | Role | Library | Offboarded | Expected | Live verified |
| --- | --- | --- | --- | --- | --- | --- |
| TT-01 | publish | android_design | LIB-FOUNDATION | no | refused | no |
| TT-02 | publish | web_design | LIB-FOUNDATION | no | refused | no |
| TT-03 | publish | admin_design | LIB-FOUNDATION | no | refused | no |
| TT-04 | publish | android_design | LIB-COMPONENTS | no | refused | no |
| TT-05 | publish | web_design | LIB-COMPONENTS | no | refused | no |
| TT-06 | publish | admin_design | LIB-COMPONENTS | no | refused | no |
| TT-07 | publish | android_design | LIB-ANDROID | no | refused | no |
| TT-08 | publish | web_design | LIB-WEB | no | refused | no |
| TT-09 | publish | admin_design | LIB-ADMIN | no | refused | no |
| TT-10 | publish | systems | LIB-FOUNDATION | yes | refused | no |
| TT-11 | publish | systems | LIB-COMPONENTS | yes | refused | no |
| TT-12 | publish | systems | LIB-ANDROID | yes | refused | no |
| TT-13 | publish | systems | LIB-WEB | yes | refused | no |
| TT-14 | publish | systems | LIB-ADMIN | yes | refused | no |
| TT-15 | publish | systems | LIB-COMPONENTS | no | model_permitted | no |
| TT-16 | publish | systems | LIB-CANDIDATE | no | refused | no |
| TT-17 | publish | design_ops | LIB-COMPONENTS | no | refused | no |
| TT-18 | publish | decision_coordinator | LIB-COMPONENTS | no | refused | no |
| TT-19 | edit | android_design | LIB-COMPONENTS | no | refused | no |
| TT-20 | edit | systems | LIB-COMPONENTS | no | model_permitted | no |
| TT-21 | comment | admin_design | LIB-COMPONENTS | no | model_permitted | no |
| TT-22 | view | design_qa | LIB-ANDROID | no | model_permitted | no |
| TT-23 | view | android_design | LIB-ANDROID | yes | refused | no |
| TT-24 | public_link | systems | LIB-COMPONENTS | no | refused | no |
| TT-25 | public_link | web_design | LIB-WEB | no | refused | no |
| TT-26 | export | systems | LIB-FOUNDATION | no | refused | no |
| TT-27 | export | admin_design | LIB-ADMIN | no | refused | no |
| TT-28 | edit | android_design | LIB-CANDIDATE | no | model_permitted | no |

### Required approvals

| Role | Status |
| --- | --- |
| systems | not_recorded |
| design_ops | not_recorded |
| accessibility | not_recorded |
| ux_engineering | not_recorded |
| decision_coordinator | not_recorded |

### Readiness gaps (default mode)

| Rule | Count |
| --- | --- |
| readiness.direction_missing | 1 |
| readiness.tokens_unpublished | 1 |
| readiness.approval_not_recorded | 5 |
| readiness.cdo_decision_pending | 5 |
| readiness.cdo_decision_unverified | 0 |
| readiness.migration_plan_pending | 0 |
| readiness.live_verification_missing | 28 |
| readiness.component_not_in_registry | 0 |
| readiness.registry_component_ungoverned | 0 |

<!-- END GENERATED: governance/figma-libraries.json -->
