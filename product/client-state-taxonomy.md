# Client state and copy taxonomy

> **Status: published vocabulary, version 1.0.0.** Source ticket `T-UX-01`,
> [PenniLogic/docs#1](https://github.com/PenniLogic/docs/issues/1) (migrated from
> PenniLogic-old/docs#52). The machine-readable data is
> [`product/client-state-taxonomy.json`](client-state-taxonomy.json), its schema is
> [`product/client-state-taxonomy.schema.json`](client-state-taxonomy.schema.json), and both are
> validated by `python scripts/check_client_states.py` and `scripts/tests/test_client_states.py`.
> This document publishes a shared vocabulary. It implements no state in any client, changes no
> contract, and implies no coverage of any existing client surface.

## 1. Why one vocabulary

Every client ticket used to list its non-happy-path states in its own words, so the same condition
was offline in one ticket, stale in another and an error in a third. A quality gate cannot assert
that a screen handles offline when offline has no definition, and the inconsistency shows exactly
where trust is thinnest: a denied permission, a failed refresh of shared money, an exhausted AI
allowance. Android, customer web and admin therefore share the eight states below, each with a
definition, the condition that produces it, what the surface must and must not show, whether the
underlying data may still be displayed, exactly one recovery action, canonical copy and the client
signal that records it. Client tests and the client quality gates assert the machine-readable
identifiers, never a display string.

## 2. How to read a state

| Field | Meaning |
| --- | --- |
| Identifier | Lowercase `snake_case` value that clients and tests assert, for example `permission_denied`. Stable across versions; renaming is a major change. |
| Name | The hyphenated human name used in tickets, for example permission-denied. |
| Scope | Where the state may be rendered: a whole **surface**, a **region** of it, or the outcome of one **action**. At most one surface-scope state is shown at a time; region and action states coexist with the surface's content. |
| Data display | Whether the data the state concerns may still be shown: `none` (nothing to show), `hidden` (exists but must not be shown), `shown` (unchanged) or `shown_marked` (shown with the state's text marker on every figure). |
| Auto-resolves | Whether the state clears without the user acting once its condition ends. |
| Recovery action | The single action offered. Its identifier is stable; its label is canonical copy. |
| Canonical copy | The headline and body every client renders verbatim, varying only in the enumerated placeholders of section 7. |
| Signal | The client signal `client_state.<identifier>` recorded when the state is entered (section 10). |

## 3. The states

### 3.1 `empty`

- **Definition.** The request for this surface or region completed successfully and there is
  nothing to show yet.
- **Triggering condition.** A read completed with zero items, or a locally backed surface has no
  records, and no filter is narrowing the result. A filtered result with zero matches is a content
  state with a no-results message, not `empty`.
- **Scope:** surface, region. **Data display:** `none`. **Auto-resolves:** no.
- **Must show.** The canonical headline; one or two sentences from the surface registration saying
  what will appear here and how it gets here (recorded, captured, imported or shared); the surface's
  single primary action when it has one, otherwise a link to the place its content originates; an
  accessible name so a screen reader reads headline then body once.
- **Must not show.** Wording that frames the absence as the user's omission; fabricated sample
  figures, charts or transactions that could pass for real data; error styling, warning icons or a
  retry; a permission prompt (a denied permission is `permission_denied`, not `empty`).
- **Recovery action `primary_action`.** Label `{primary_action}`; starts the surface's primary way
  of creating content. The label is registered once per surface and identical on every client.
- **Copy.** Headline "Nothing here yet". Body `{what_appears_here}`.
- **Signal** `client_state.empty`.

### 3.2 `loading`

- **Definition.** The surface, region or action has asked for data it does not yet have, and the
  request is still within its expected time.
- **Triggering condition.** A first read, or a read after all displayable data was discarded, has
  started and has neither succeeded nor failed. A refresh of data already on screen is not
  `loading`: the data stays visible with a refresh indicator, and a failed refresh produces `stale`.
- **Scope:** surface, region, action. **Data display:** `none`. **Auto-resolves:** yes; the state
  is bounded and ends in `empty`, content, `offline`, `error` or `stale`.
- **Must show.** A skeleton or progress indicator shaped like the content it replaces so the layout
  does not jump; after the slow threshold, the canonical headline and body; exactly one
  assistive-technology announcement of loading and one of completion. The slow threshold and the
  timeout are published by the client performance budgets (`T-QA-06`, `T-QA-08`, `T-QA-13`), not
  here.
- **Must not show.** Placeholder numbers or currency amounts in a skeleton; an indicator with no
  end; blocking of regions that do not depend on the pending request; copy before the slow
  threshold.
- **Recovery action `cancel`.** Label "Cancel"; stops waiting and returns to the last usable
  surface, or to `empty` when there is nothing to return to; discards nothing the user entered;
  offered only after the slow threshold.
- **Copy.** Headline "Still loading". Body "This is taking longer than expected."
- **Signal** `client_state.loading`.

### 3.3 `error`

- **Definition.** A request failed, or a response could not be used, for a reason the client cannot
  or must not explain, and the surface, region or action cannot fulfil its purpose.
- **Triggering condition.** A read or write receives a failure response, an unusable response, or
  no response within its timeout while the platform reports connectivity, and no displayable data
  exists for the affected region (if it does, the region is `stale`). A field-level validation
  rejection uses this state at action scope with the field named.
- **Scope:** surface, region, action. **Data display:** `none`. **Auto-resolves:** no.
- **Must show.** The canonical headline naming what was attempted in plain words; the single
  recovery action; the user's unsaved input preserved exactly after a failed write; for a validation
  rejection, the affected field and what is needed, never what the user did wrong; the correlation
  identifier the service returned (owned by `T-CON-12`) carried with any support report opened from
  the surface, not part of the state copy; focus moved to the headline or an assertive announcement
  of it.
- **Must not show.** A cause the client did not receive from the service in a user-facing form;
  internal identifiers, stack detail, status codes, exception names, provider names or raw service
  messages; any claim about whether a write took effect unless the service confirmed it; wording
  that blames the user or labels their input as faulty; another person's existence, name or account
  state.
- **Recovery action `retry`.** Label "Try again"; repeats the failed request with the same input.
  A write repeats under the same idempotency key so it cannot duplicate a ledger entry; whether a
  failure is retryable comes from the retry classification `T-CON-12` publishes.
- **Copy.** Headline "Couldn't `{attempt}`". Body "Try again in a moment." Validation variant, when
  the service identified a rejected field: same headline, body `{field_guidance}`.
- **Signal** `client_state.error`.

### 3.4 `offline`

- **Definition.** The platform reports that the device has no connectivity, and the surface,
  region or action needs the service and has no displayable data.
- **Triggering condition.** The platform reports no network connectivity and the affected read has
  no displayable data, or the affected action needs the service and could not be queued locally.
  If displayable data exists, the region is `stale` with the offline marker, not `offline`. Requests
  that fail while the platform reports connectivity are `error`, not `offline`. Android surfaces
  backed by the local database are never `offline` for reads.
- **Scope:** surface, region, action. **Data display:** `none`. **Auto-resolves:** yes; reads are
  repeated automatically when connectivity returns.
- **Must show.** The canonical headline stating the known condition; the single recovery action;
  continued access to everything that works without the service (local records, manual entry,
  saved answers, navigation); for a write that was queued locally, the pending marker of the happy
  path rather than this state; a polite announcement when the state is entered and when it clears.
- **Must not show.** The condition presented as an unknown failure or as the service being at
  fault; features that do not need connectivity hidden or disabled; the user's unsaved input
  discarded; any figure the client has not received.
- **Recovery action `retry`.** Label "Try again"; repeats the request now. Reads are also repeated
  automatically as soon as connectivity returns; an action that could not be queued waits for the
  user.
- **Copy.** Headline "You're offline". Body "Try again when you're back online."
- **Signal** `client_state.offline`.

### 3.5 `stale`

- **Definition.** The surface or region shows data it holds but could not refresh, or data older
  than its declared freshness window, so the figures may not be current.
- **Triggering condition.** Displayable data exists and either the most recent refresh attempt
  failed or could not be made (for any cause, including no connectivity), or the data's age exceeds
  the freshness window the surface declares in its registration, for example a currency rate under
  E30.
- **Scope:** surface, region. **Data display:** `shown_marked`. **Auto-resolves:** yes, on the next
  successful refresh.
- **Must show.** The data exactly as last received, money in the integer minor units and currency
  the service sent and never recomputed on the client; the canonical marker with the time of the
  last successful refresh adjacent to the figures it qualifies, as text and not colour alone; the
  single recovery action; the offline marker (the `offline` headline) beside the stale marker when
  the platform reports no connectivity, without leaving this state; for shared data, display only
  while the offline lease bound published by `T-CON-04` has not elapsed, after which the region
  becomes `permission_denied` and the cached shared data leaves the view; a visual treatment
  distinct from confirmed values (`T-DSY-01` owns the treatment; the marker text is the minimum).
- **Must not show.** A stale figure without its marker; a money-committing action (settle, pay,
  transfer, confirm) pre-filled from stale figures without a successful refresh first, and if that
  refresh fails the action is `offline` or `error` at action scope; any figure derived on the client
  from stale data (projections, deltas, amounts since the last update); detail the active grant did
  not cover; blame toward another person or an invented cause for the failed refresh.
- **Recovery action `refresh`.** Label "Refresh"; requests current data and replaces the stale
  figures only when the request succeeds.
- **Copy.** Headline (rendered as the marker) "Last updated `{last_updated}`". Body "Showing what
  was last saved."
- **Signal** `client_state.stale`.

### 3.6 `permission_denied`

- **Definition.** Something on the surface cannot be shown or done because access to it is not
  currently available to this client: a device permission is not granted, the plan does not include
  the feature, no active sharing grant covers the data, or the operator's role does not include the
  capability. Everything else on the surface stays usable.
- **Triggering condition.** The platform reports a permission or restricted setting as not granted;
  or the service refuses a request because the account's plan does not include the feature (an
  entitlement deny); or the service refuses a cross-user read because no active grant covers it,
  whether the grant is absent, revoked or expired; or cached shared data passes the offline lease
  bound without confirmation; or an administrative capability is outside the operator's role. The
  concrete refusal shapes are bound to this identifier by `T-CON-12`.
- **Scope:** surface, region, action. **Data display:** `hidden`. **Auto-resolves:** no.
- **Cause classes.** `device` (platform permission or restricted setting; client-determined),
  `plan` (entitlement deny; contract-level, server-authoritative under ADR-007), `sharing` (no
  active grant under the default-deny model of ADR-005, or the offline lease bound elapsed;
  contract-level for the refusal, client-determined for the bound) and `role` (administrative
  capability outside the operator's role; contract-level). The cause selects the copy variant and
  the recovery label; it is recorded on the signal.
- **Must show.** The affected capability in product terms and the kind of access it needs; that
  everything else keeps working, and it does: navigation, unaffected regions, manual alternatives
  and previously permitted features stay fully operable because the app is usable with every
  optional permission denied; the single recovery action leading to the one place where this access
  is controlled, which for the sharing cause never contacts the other person; removal from view of
  any cached data behind the denial within the bounds `T-CON-04` publishes; identical copy for the
  sharing cause whether the grant is absent, revoked, expired or unverifiable.
- **Must not show.** Anything that reveals whether data exists behind the denial (counts, totals,
  hidden-item hints, names, or that a grant once existed); a blocked surface, hidden unaffected
  features, or repeated prompts (a rationale at most once per session unless the user asks); a
  bypass, an attempt of the denied operation, or an action that notifies or asks the other person
  for access; blame or an invented reason; the condition treated as `error` or `empty`.
- **Recovery action `review_access`.** One action whose destination follows the cause: the
  platform's permission request, or the app's system settings page when the platform will not
  prompt again (`device`, label "Allow `{permission}`"); the plan overview (`plan`, "See plans");
  the user's own sharing overview (`sharing`, "See what's shared with you"); the administrative
  access request flow (`role`, "Request access"). The default label "Review access" and the default
  copy apply only while a service refusal is not yet bound to a cause, that is before `T-CON-12`
  lands; the cause variants replace them. It never attempts the denied operation and never contacts
  another person.
- **Copy.** Default headline "You don't have access to this right now", body "Everything else keeps
  working." Variants: `device` "`{capability}` needs `{permission}`" / "You can keep using
  everything else without it."; `plan` "Not included in your plan" / "Everything in your current
  plan keeps working."; `sharing` "You don't have access to this right now" / "Everything else keeps
  working." (no placeholders, so no name can appear); `role` "Not part of your current access" /
  "Everything else keeps working."
- **Declared guarantees, asserted by the validator:** `rest_of_surface_usable` is true and
  `discloses_hidden_data` is false.
- **Signal** `client_state.permission_denied`, with the `cause` attribute.

### 3.7 `quota_exceeded`

- **Definition.** A metered capability is unavailable because the allowance for the current window
  has been used, while everything else on the surface, including what the capability already
  produced, stays available.
- **Triggering condition.** The service refuses a metered request because the plan's request or
  token allowance for the window is used, or because a short-window rate limit was reached; both
  are stated by the service and never estimated by the client. Applies to server-metered
  capabilities such as AI questions. Usage through a user's own provider key is metered but not
  charged against plan quota and does not produce this state.
- **Scope:** region, action. **Data display:** `shown`. **Auto-resolves:** yes, when the service
  stops refusing.
- **Must show.** What is still available, stated positively (previously produced results and every
  capability outside the metered one); the limit reached in the plain terms the service stated (a
  count and its window, never a monetary amount); when the allowance resets, only when the service
  stated it; the single recovery action; metered controls disabled but visible, exposing the
  disabled state and the headline as its reason to assistive technology.
- **Must not show.** Anything the quota does not cover hidden or disabled, including the history of
  what was produced; a reason the service did not give, a counter it did not send, or a reset time
  the client computed; any monetary amount, price or balance in the state copy; a bypass or repeated
  refused attempts; wording that frames the exhaustion as misuse.
- **Recovery action `view_usage`.** Label "See usage and plans"; opens the account's usage view
  with the limit, what was used, the reset time when known and the plans available. Informational:
  it never claims a purchase will restore the capability unless the service states so.
- **Copy.** Headline "You've reached this period's limit of `{limit}`". Body
  "`{still_available}` still work." With a service-stated reset: "`{still_available}` still work.
  Resets `{resets_at}`."
- **Declared guarantee, asserted by the validator:** `states_what_remains_available` is true.
- **Signal** `client_state.quota_exceeded`.

### 3.8 `degraded`

- **Definition.** A capability the surface offers is unavailable because a dependency is down or
  paused, but the surface still does what it exists for with what it shows.
- **Triggering condition.** A region or capability enters `error`, `offline`, `permission_denied`
  or `quota_exceeded`, or a platform capability such as automatic capture is paused (the
  capture-health conditions `T-AND-07` publishes), while the surface's purpose remains achievable.
  Decision test: can the user still do what this surface exists for? Yes gives `degraded` with the
  capability named; no gives `error`.
- **Scope:** surface only. **Data display:** `shown`. **Auto-resolves:** yes, when the dependency
  returns.
- **Must show.** The surface's content and primary purpose, fully operable; the canonical headline
  naming the unavailable capability in product terms; the single recovery action plus automatic
  recovery; the affected region's own state rendered where the capability would appear, so the
  notice and the gap agree; a polite announcement on appearance and clearance that never takes
  focus from the user's task.
- **Must not show.** Provider, vendor or service names, internal identifiers or status detail;
  full-surface blocking, modal dialogs or content replaced by the notice; a cause the client was not
  given; the capability silently omitted with no notice; substitute figures computed on the client
  for the unavailable dependency, such as a locally estimated currency rate.
- **Recovery action `retry`.** Label "Try again"; re-checks the affected capability now; the client
  also re-checks automatically at the cadence the surface declares.
- **Copy.** Headline "`{capability}` isn't available right now". Body "Everything else is working.
  We'll keep checking."
- **Signal** `client_state.degraded`.

## 4. Precedence and composition

When more than one condition holds for the same region, the earliest identifier in this list is
rendered:

1. `permission_denied` — data behind a denial is never shown, even when cached.
2. `quota_exceeded` — a metered action stays blocked whatever the data shows.
3. `stale` — held data is shown with its marker rather than hidden behind `offline` or `error`.
4. `offline` — a known offline condition is never presented as an unknown error.
5. `error`
6. `degraded` — the surface-scope notice that accompanies a region state without replacing it.
7. `loading` — only before the first data.
8. `empty` — only after a successful read.

Composition follows from scope. A surface is made of regions; each region has its own state; the
surface shows at most one surface-scope state. When a region that is supplementary to the surface's
purpose is in `error`, `offline`, `permission_denied` or `quota_exceeded`, the surface is `degraded`
and names that capability. When the region that *is* the surface's purpose fails, the surface is
`error`. `T-CON-12` binds each published error code to exactly one identifier at the scope of the
request that received it; the surface-level presentation follows this section, not the code.

## 5. Offline versus stale

Both can start from the same lost connection. The difference the user sees is whether the figures
are on screen.

| | `offline` | `stale` |
| --- | --- | --- |
| What is on screen | No figures; the headline "You're offline" stands where they would be | The last received figures, each with the text marker "Last updated `{last_updated}`" |
| Data display | `none` | `shown_marked` |
| Cause shown | Yes, connectivity is a platform-reported fact | Only the marker; when connectivity is the known cause, the offline marker is added beside it without changing state |
| Recovery action | `retry` "Try again", plus automatic retry of reads on reconnect | `refresh` "Refresh", replacing figures only on success |
| Resolution | Clears when a request succeeds; nothing was shown meanwhile | Clears when a refresh succeeds; the old figures stayed visible meanwhile |
| Money | No figure is shown | Figures are the service's integer minor units with currency, never recomputed; no money action is pre-filled from them without a successful refresh |

A surface signals data it has but cannot refresh by staying in `stale`: the marker is the signal,
the figures remain, and `Refresh` is the single action. It never switches to `offline` while it
holds displayable data.

## 6. Error versus degraded

The decision test is whether the user can still complete the surface's purpose.

| | `error` | `degraded` |
| --- | --- | --- |
| What is on screen | The content the user came for is absent; "Couldn't `{attempt}`" stands in its place | The content is present and usable; a non-blocking notice "`{capability}` isn't available right now" names the one missing capability, and that capability's region shows its own state |
| Data display | `none` | `shown` |
| Scope | Surface, region or action | Surface only |
| Recovery action | `retry` "Try again" on the failed request | `retry` "Try again" on the affected capability, plus automatic re-check |
| Resolution | Waits for a new attempt | Clears itself when the dependency returns |
| Example | The AI question surface cannot obtain an answer: `error` | The debt payoff surface cannot obtain its AI explanation but every figure and action works: `degraded`, with the AI region in `error` |

## 7. Copy rules

Every canonical string in the data file obeys these rules; the validator enforces the forbidden
terms and the placeholder list, and independent design review holds the rest.

| Rule | Statement |
| --- | --- |
| `no_blame` | Copy never attributes fault to the user. It does not say the user failed, denied, forgot or entered something wrong; it describes the condition and what is needed. |
| `no_invented_cause` | Copy states only what the client knows. A cause is named only for `offline` (platform-reported) and for conditions the service stated in a user-facing form. `error` and `degraded` copy never guess a cause such as a service being down, a network problem or high demand. |
| `no_internal_detail` | No internal identifiers, stack detail, status codes, exception names, provider or vendor names, or raw service messages. A correlation identifier travels with a support report, never in the copy. |
| `no_hidden_data_disclosure` | Copy never reveals whether data exists behind a denial, how much of it there is, or another person's existence, decision or account state. |
| `same_wording` | The same state uses the same canonical copy on Android, web and admin, differing only in the enumerated placeholders. Clients do not paraphrase. Localisation (E30) translates the canonical strings in the data file, not per-client variants. |
| `one_action` | Exactly one recovery action per state; the body contains no second call to action. Navigation and help chrome are not recovery actions. |
| `positive_framing` | `permission_denied`, `quota_exceeded` and `degraded` copy states what still works, not only what is blocked. |
| `plain_language` | Short sentences in sentence case, no exclamation marks, no jargon, headline of at most sixty characters before placeholders are filled. |
| `no_money_in_state_copy` | State copy carries no monetary amount, price or balance; figures belong to the content the state qualifies. |
| `calm_tone` | No humour, apology theatre or promotional language; calm and evidence-led, as PRODUCT.md requires. |

**Placeholders.** Canonical copy varies only through these placeholders, each with one permitted
source. A value is never a monetary amount, balance, count of hidden items, internal identifier,
another person's name, provider or vendor name, or raw message content.

| Placeholder | Source | Example |
| --- | --- | --- |
| `{item}` | surface registration | transactions |
| `{attempt}` | surface registration | load your transactions |
| `{capability}` | surface registration | Automatic capture |
| `{permission}` | client platform copy | SMS access |
| `{last_updated}` | client cache metadata, locale-formatted | 2 hours ago |
| `{limit}` | service response only | 5 AI questions |
| `{resets_at}` | service response only; its sentence is omitted when absent | 1 October |
| `{still_available}` | surface registration | Saved answers and everything outside AI |
| `{primary_action}` | surface registration | Add a transaction |
| `{what_appears_here}` | surface registration | Transactions you record, capture or import will appear here. |
| `{field_guidance}` | component copy (design system), under these rules | Enter an amount above zero. |

**Forbidden terms.** The validator rejects canonical copy containing, as whole words, any of the
terms listed under `forbidden_terms` in the data file: apology and blame words (oops, sorry,
invalid, illegal, wrong, you failed, you denied, you must), internal vocabulary (error code,
exception, stack, null, undefined, server, backend, api, database, timeout, unexpected), the
cause-asserting word because, and the exclamation mark.

## 8. Accessibility requirements common to every state

- Entering a state is announced once to assistive technology: politely for `loading`, `offline`,
  `stale` and `degraded`; by moving focus to the headline, or an assertive announcement, for
  `error`, `permission_denied` and `quota_exceeded`.
- Every state and marker is conveyed by text, never by colour or icon alone; the visual treatment
  `T-DSY-01` publishes is additional.
- The recovery action is a focusable control reachable by keyboard and switch access, with the
  headline as its accessible context.
- Non-blocking notices (`degraded`, `stale`, the offline marker) never move focus away from the
  user's task.
- Controls disabled by a state (`quota_exceeded`) stay visible and expose the disabled state and its
  reason.
- Canonical copy remains readable at two hundred percent text scale; headlines wrap rather than
  clip.
- Loading indicators respect the reduced-motion preference; no state depends on animation.
- The conformance target is WCAG 2.2 AA on web and admin; Android follows current Material
  accessibility guidance and the applicable WCAG outcomes (PRODUCT.md).

## 9. Contract-level conditions

The taxonomy names the conceptual conditions that produce each state so a client state maps to a
real service result. It defines **no error codes, status codes or wire fields**: `T-CON-12`
([PenniLogic/contracts#16](https://github.com/PenniLogic/contracts/issues/16)) publishes the error
catalogue and binds each code to exactly one identifier here, and a code without a binding fails
its contract validation. The schema cannot express a code, and the validator rejects code-like
tokens in this table. Bare `repo#N` numbers elsewhere in this repository are PenniLogic-old
identities; stable ticket identifiers are used here instead.

| Condition | Binds to | Cause | Contract-level | Owner of the binding |
| --- | --- | --- | --- | --- |
| `entitlement_denied` — the plan does not include the feature or it is disabled | `permission_denied` | `plan` | yes | `T-CON-12`; entitlements are server-authoritative (ADR-007) |
| `grant_not_active` — no active grant covers the member, category and detail level; absent, revoked and expired are one condition with identical copy | `permission_denied` | `sharing` | yes | `T-CON-04` shapes and bounds; `T-CON-12` refusal shape |
| `offline_lease_elapsed` — cached shared data passed the offline lease bound without confirmation | `permission_denied` | `sharing` | no (client applies the published bound) | `T-CON-04` |
| `device_permission_not_granted` | `permission_denied` | `device` | no | client platform layer; `T-AND-07` restricted-settings matrix |
| `role_capability_denied` — administrative capability outside the operator's role or needing a second approver | `permission_denied` | `role` | yes | `T-CON-12` within the administrative contract |
| `quota_exhausted` — request or token allowance for the window used | `quota_exceeded` | — | yes | `T-CON-12`; model in ADR-023 (`T-ADR-ENT-09`) |
| `rate_limited` — short-window limit reached within quota; the shape must state the limit and window | `quota_exceeded` | — | yes | `T-CON-12` |
| `dependency_unavailable` — AI provider, rate source or similar dependency unavailable; bound at the request's scope, host surface composes to `degraded` | `error` | — | yes | `T-CON-12`, distinguishing it from a refusal and from quota exhaustion |
| `request_failed` — failure, unusable response or timeout while connected | `error` | — | yes | `T-CON-12`, with retry classification |
| `validation_rejected` — field-level rejection naming the field without a monetary value | `error` (validation variant, action scope) | — | yes | `T-CON-12` |
| `capture_paused_by_platform` — force-stop, standby bucket or private-space pause | `degraded` | — | no | `T-AND-07` |
| `capture_blocked_by_setting` — permission or restricted setting blocks capture | `permission_denied` | `device` | no | `T-AND-07` |
| `resource_pressure` — low storage or memory pauses optional cache growth | `degraded` until `T-AND-06` adds identifiers here first | — | no | `T-AND-06` |

**Conditions that are not taxonomy states.** A locally queued write awaiting sync is the pending
marker of the happy path (domain model section 7, `T-SYN-03`). A filter matching nothing is a
content state. An AI refusal within the advice boundary is a successful response whose content is
a refusal (E17, E18); `T-CON-12` distinguishes it from a provider failure and from quota exhaustion
by code. Sign-in, session expiry, step-up and recovery are authentication states owned by
`T-AUTH-01`. Success, destructive confirmation, cooling-off, undo and recovery-flow states are
decision or happy-path states owned by the design-system components (E34). The states PRODUCT.md
calls "offline or degraded" and "denied" are `offline`/`degraded` and `permission_denied` here.

## 10. Observability

Each identifier names its own signal, `client_state.<identifier>`, recorded once when the state is
entered and once more when its recovery action is taken, so the frequency of each non-happy path
is measured rather than guessed. Attributes: `client`, `surface_id`, `scope`, `cause` (for
`permission_denied`), `permission` (for the `device` cause, the platform's permission name),
`recovery_action_taken` and `taxonomy_version`. Signals carry no amount, balance, price or count of
hidden items; no identifier of the denied resource, grant or account; no other person's identity or
decision; no message content and no device identifier. They are counted and never joined to
financial content.

## 11. Worked examples

### 11.1 Permission-denied capture surface

*Android transactions home with automatic capture of payment messages; `permission_denied`, cause
`device`.* The person declined SMS access at install, or a restricted setting blocks the
notification listener, and opens the home to record a cash payment and check this week's spending.

- **Shown.** The transaction timeline with every manually recorded and previously captured entry,
  fully scrollable and editable; the primary action to record a transaction by hand, operable
  exactly as when capture is on; budgets, debt summaries and every other region unchanged; in the
  capture region only, the headline "Automatic capture needs SMS access", the body "You can keep
  using everything else without it." and the single action "Allow SMS access".
- **Not shown.** Any count or hint of payment messages on the device (the client cannot read them
  and must not imply it knows they exist); a full-screen permission wall, a blocked primary action
  or a system prompt repeated on every launch; error styling or a retry; wording that the person
  denied or forgot something; cached content from before a revoked permission presented as captured
  today.
- **Transitions.** Granted: the capture region returns to content, or to `empty` until the first
  captured message. Declined again: nothing changes and the rationale is not repeated this session.
  Platform will not prompt again: the action opens the app's system settings page. Capture paused by
  the platform after a force-stop while the permission is granted: the surface is `degraded`, not
  `permission_denied` (`T-AND-07`).
- **Privacy and money.** The client never reads or counts messages to decorate the state, and the
  state discloses nothing about data it cannot access. The signal carries the cause and the
  permission name only. Manually recorded amounts are entered and stored in integer minor units with
  currency exactly as when capture is on; the denial changes no arithmetic.
- **Signal.** `client_state.permission_denied` with `client=android`,
  `surface_id=transactions_home`, `scope=region`, `cause=device`.

### 11.2 Quota-exceeded AI surface

*AI explanations panel on the debt payoff surface and the AI question history; `quota_exceeded`.*
A person on the free plan asks a sixth AI question this month. The service refuses, stating the
allowance of five questions for the month and the date it resets.

- **Shown.** Every previous question and answer, readable and searchable; the debt payoff figures,
  projections and every non-AI capability unchanged; the composer disabled but visible with the
  headline "You've reached this period's limit of 5 AI questions", the body "Saved answers and
  everything outside AI still work. Resets 1 October." and the single action "See usage and plans".
  The reset sentence appears only because the service stated the reset time.
- **Not shown.** Hidden or greyed history, or a disabled surface beyond the composer; a price,
  monetary amount or balance in the state copy (plan prices live on the plans view); a reset date the
  client computed, a counter the service did not send, or a reason such as demand; a provider or
  model name, or a way to send the question anyway; wording that the person asked too much.
- **Transitions.** Allowance reset by the service: the composer is enabled again on the next
  successful request or refresh. Plan change confirmed by the service: the state clears when the
  service stops refusing; the client never assumes a purchase succeeded. Provider failure instead of
  quota: the AI region is `error` and the payoff surface is `degraded`, distinguishable by the
  service's shape, not by prose. Own provider key in use: metered but not charged against plan
  quota, so this state does not appear.
- **Privacy and money.** The question text is never included in the state or the signal; usage
  counts stay with the service. No amount appears in the state; the limit is a count of questions.
- **Signal.** `client_state.quota_exceeded` with `client=web`, `surface_id=ai_explanations`,
  `scope=action`.

### 11.3 Stale shared balance

*Household shared aggregate: a partner's groceries total for the month under an aggregate-only
grant; `stale`.* A household member opens the total on a train with no signal. The client holds
the figure from a refresh two hours earlier and the platform reports no connectivity.

- **Shown.** The total exactly as last received, formatted from its integer minor units and
  currency by the client's locale formatter (a synthetic 1234000 INR minor units renders as twelve
  thousand three hundred and forty rupees); the text marker "Last updated 2 hours ago" beside the
  figure and the body "Showing what was last saved."; the offline marker "You're offline" beside the
  stale marker; the single action "Refresh".
- **Not shown.** The figure without its marker or styled as a confirmed current value; a
  client-computed delta, projection or amount since the last update; any transaction detail, because
  the grant covers the aggregate only and staleness never widens it; a settle or transfer action
  pre-filled from the stale figure without a successful refresh first; wording that the partner has
  not updated or that blames anyone; the figure after the offline lease bound from `T-CON-04` has
  elapsed without a successful refresh.
- **Transitions.** Connectivity returns and the refresh succeeds: the marker disappears and the
  current figure replaces the old one. Refresh fails while connected: figure and marker stay, the
  offline marker is removed, no cause is invented. Offline lease bound elapses without confirmation:
  the region becomes `permission_denied` with the `sharing` cause, the copy "You don't have access to
  this right now", the action "See what's shared with you", and the cached figure leaves the view.
  Grant revoked by the partner and the client reconnects: the service refuses, the region shows the
  identical sharing copy, and nothing indicates that a grant existed or was withdrawn.
- **Privacy and money.** The sharing-cause copy is identical for a revoked grant, an expired grant,
  a never-granted view and an elapsed lease, so the viewer learns nothing about the partner's
  decision from the copy. A figure that was visible and then leaves the view is a signal inherent
  to revocation itself, which ADR-005 makes unilateral; the taxonomy adds nothing to that signal and
  the copy never confirms or explains it. The recovery action after denial opens the viewer's own
  sharing overview and never notifies or asks the partner. The cached figure is the service's
  deterministic result in integer minor units with currency; the client formats it and never
  recalculates, projects or nets it. A money-committing action against a stale figure requires a
  successful refresh first.
- **Signal.** `client_state.stale` with `client=android`, `surface_id=household_shared_aggregate`,
  `scope=region`; no amount, member identity or grant identifier.

## 12. Future client-gate adoption

This section describes how the Android, web and admin quality gates (`T-QA-08`, `T-QA-06`,
`T-QA-13`) will consume the taxonomy. **No client registers surfaces today, and publishing this
taxonomy implies no coverage of any existing client.** Clients adopt it as their surfaces are
built, pinning `taxonomy_version`.

Each gate keeps a surface registry, one entry per surface, in the shape of
`definitions.surface_registration` in the schema: `surface_id`, `client`, `applicable_states`,
`item`, `attempt`, and optionally `primary_action`, `what_appears_here`, `capabilities` and
`freshness_window_seconds`. The data file carries one illustrative, synthetic entry
(`example_transactions_home`), validated by the tests and belonging to no real client.

The gates run two assertions:

- `client_state_coverage` — for every registered surface and every applicable identifier, the
  client renders that state with the canonical copy and exactly the one recovery action published
  at the pinned version. A surface that omits an applicable identifier fails; the gate proves itself
  with a planted omission. This is the coverage assertion the ticket names: every listed surface
  handles every applicable state identifier.
- `taxonomy_first` — the client's state enumeration is a subset of the identifiers published at the
  pinned version. An identifier present in a client and absent here fails. This is the review test
  that a new state cannot be added to a client without adding it to the taxonomy first.

`T-DSY-01` consumes the same identifier list for its state-treatment completeness test, and the
design-system component tickets (E34) consume the required, forbidden and recovery content per
state, adding platform adaptations without changing the vocabulary.

## 13. Extending the taxonomy

Identifiers are added here first, never in a client. To add a state or a `permission_denied`
cause class: open a PenniLogic/docs issue naming the identifier, its condition and the surfaces
that need it; add it to the data file and this document with its definition, triggering
condition, required and forbidden content, exactly one recovery action, canonical copy and signal
(a new state also joins the precedence list); bump `taxonomy_version` (minor for additions, major
for a removed or renamed identifier); run `python scripts/check_client_states.py` and
`python -m unittest discover -s scripts/tests`; obtain the independent reviews this repository
requires. Clients bump their pin only after the change is merged.

Pending extensions already owned elsewhere: `T-CON-12` binds codes to identifiers and adds none
without this procedure; `T-AND-06` adds resource-degraded identifiers; `T-AND-07` publishes
Android platform-capability and capture-health condition identifiers, each bound to exactly one
state here; `T-SEC-05` names a cause class for operations denied by an adverse integrity verdict if
the existing classes do not fit.

## 14. Validation and evidence

`python scripts/check_client_states.py` (also invoked by `python scripts/check_docs.py`) validates
the data against the schema with a strict draft-07 subset that rejects any keyword it does not
implement, then enforces: the eight required identifiers; the hyphenated name and the
`client_state.` signal per identifier; exactly one recovery action whose label offers one action;
only declared placeholders and no forbidden term in canonical copy; the required copy rules; a
precedence list naming every state once; the `offline`/`stale` and `error`/`degraded` distinctions
with data display that genuinely differs and matches the states; conceptual contract conditions
including `entitlement_denied` and `grant_not_active`, bound to known states and causes and free of
code-like tokens; the declared guarantees of `permission_denied` (data hidden, rest of surface
usable, no hidden-data disclosure) and `quota_exceeded` (what remains available is stated); exactly
the three worked examples with matching states, causes, signals and declared signal attributes;
the two coverage assertions and a valid illustrative registration; and that this document carries
every canonical headline, body and action label verbatim and mentions every identifier, recovery
action, distinction, example, condition, rule and the version, so the document and the data cannot
drift apart.

`python -m unittest discover -s scripts/tests` runs `scripts/tests/test_client_states.py`, which
maps each acceptance criterion to a named test and proves the checks bite with planted defects: a
removed identifier, a second recovery action, a blaming phrase, an undeclared placeholder, an
invented code, identical data display for a distinguished pair, a missing worked example, a
document that omits an identifier or alters canonical copy, and a schema keyword the validator does
not implement. These prove the published data and this document; they are not a client build, and
no client coverage is claimed.

## 15. Rollout, rollback and observability notes

Published once as documentation and data; clients adopt it as their surfaces are built and pin the
version. Rollback is reverting this document and the data file, which leaves clients with their
existing per-ticket wording and no shared identifiers to assert. Observability is the per-identifier
signal of section 10, which becomes measurable only when a client records it. Nothing here enables
a paid service, changes a contract, or claims a build, test, accessibility or load gate passed for
any client.

## 16. References

- Ticket: `T-UX-01`, [PenniLogic/docs#1](https://github.com/PenniLogic/docs/issues/1); parent epic
  [PenniLogic/docs#2](https://github.com/PenniLogic/docs/issues/2).
- Error catalogue and code bindings: `T-CON-12`,
  [PenniLogic/contracts#16](https://github.com/PenniLogic/contracts/issues/16).
- Sharing contract and revocation bounds: `T-CON-04`; sharing model ADR-005; entitlements ADR-007;
  entitlement and quota model ADR-023 (`T-ADR-ENT-09`); domain model
  [`architecture/01-domain-model.md`](../architecture/01-domain-model.md) sections 3, 5 and 7.
- Consumers: `T-QA-06`, `T-QA-08`, `T-QA-13` (client quality gates), `T-DSY-01` (state
  treatments), E34 (components), E30 (localisation), `T-AND-06`, `T-AND-07`, `T-AUTH-01`,
  `T-SEC-05`, `T-SYN-03`.
- Product truth: [`PRODUCT.md`](../PRODUCT.md); delivery policy
  [`governance/DELIVERY.md`](../governance/DELIVERY.md).
