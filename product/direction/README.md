# Concept directions and pending D2 direction record (T-UXR-07)

> **Status: proposal; D2 decision pending.** Generated from `candidates.json`, `probes.json` and
> `direction-record.json` by `python scripts/check_direction.py --render > product/direction/README.md`; do not edit by hand.
> Source issue PenniLogic/docs#76. Nothing here is user evidence, a review, an approval or a
> selected direction: candidates and probes are authored proposals with synthetic figures, persona
> assumptions are unvalidated, illustrative values are non-binding and are not a token contract.

## Readiness

`python scripts/check_direction.py` reports **NOT GREEN: readiness incomplete**.
Direction structure valid: 7 candidates, 4 probes, 42 contrast pairs (8 failing), record 0.1.0 pending.

| Readiness rule | Open gaps |
|---|---|
| readiness.user_evidence_missing | 1 |
| readiness.persona_unvalidated | 7 |
| readiness.review_pending | 5 |
| readiness.contrast_failing | 8 |
| readiness.decision_pending | 1 |
| readiness.held_gate | 6 |

## Candidates

| ID | Name | Material | Graphic | Failing contrast pairs |
|---|---|---|---|---|
| DIR-01 | Ledger and Margin | ruled_ledger_paper | double_entry_bookkeeping | 1 |
| DIR-02 | Route Atlas | folded_paper_map | cartographic_wayfinding | 1 |
| DIR-03 | Almanac Grid | uncoated_offset_print | international_typographic | 0 |
| DIR-04 | Cut Paper Household | layered_cut_paper | paper_collage | 3 |
| DIR-05 | Drafting Table | drafting_vellum | technical_drawing | 1 |
| DIR-06 | Painted Shopfront | enamel_painted_tin | indic_hand_painted_signage | 0 |
| DIR-07 | Handloom Weave | handloom_textile | warp_and_weft_pattern | 2 |

### DIR-01 Ledger and Margin

Material tradition `ruled_ledger_paper`; graphic tradition `double_entry_bookkeeping`.

- **Rationale:** Debt is a running balance with a known end state (product spec section 1). A ruled household ledger makes every figure traceable to its entry, so provenance and the payoff date read as the closing line of an account the person keeps, not as a score the product awards.
- **Intended feel:** Calm, orderly and accountable: a well-kept account book on a kitchen table, where nothing is hidden and every correction stays visible.
- **Form language:** Horizontal rules and a narrow margin column carry structure; figures sit in tabular columns; a red margin rule marks focus and corrections; surfaces are flat paper with no depth effects.
- **Signature interaction:** Struck-through correction: when a transaction is clarified, the old reading stays visible with a strike and a margin note naming its source, so the change is auditable rather than silently replaced.
- **Content behavior:** Plain declarative entries in the margin column (source, date, who changed it); the payoff date is written as the closing line of the debt account; no exclamations.

Risks:

- May read as old-fashioned or administrative to younger households (unvalidated).
- Dense ruled columns can become cramped on narrow phone screens.
- Illustrative control boundary fails the non-text contrast minimum against the paper surface; a darker rule is needed.

Accessibility notes:

- Tabular figures need programmatic row and column headers so screen readers announce each balance with its account.
- The red margin focus rule must be paired with a non-color cue such as a thickened rule for color-vision deficiencies.
- Strike-through corrections need a text equivalent, not only a visual strike.

Persona assumptions (unvalidated until docs#66):

- Households that already keep paper or spreadsheet records will recognise the ledger metaphor.
- Seeing a correction history increases trust in categorised transactions rather than causing worry.

Contrast feasibility (illustrative, non-binding values; WCAG 2.x relative luminance):

| Kind | Foreground | Background | Ratio | Minimum | Result |
|---|---|---|---|---|---|
| text | text_primary `#1F2A44` | surface `#F7F3E8` | 12.85 | 4.5 | pass |
| text | text_secondary `#5B6475` | surface `#F7F3E8` | 5.37 | 4.5 | pass |
| ui | control_boundary `#8A8F99` | surface `#F7F3E8` | 2.92 | 3.0 | fail |
| ui | focus_indicator `#B03A2E` | surface `#F7F3E8` | 5.42 | 3.0 | pass |
| ui | progress `#2F6B4F` | surface `#F7F3E8` | 5.67 | 3.0 | pass |
| text | warning `#9A3412` | surface `#F7F3E8` | 6.59 | 4.5 | pass |

Feasibility:

| Criterion | Assessment |
|---|---|
| density | High density suits tabular history; on compact phones the margin column collapses under each row. |
| reduced_motion | Static by nature; strike and margin notes appear without animation, so reduced motion loses nothing. |
| localization_expansion | Margin notes wrap below the entry when translated labels grow; numeric columns stay aligned for Indian digit grouping. |
| android | Maps to Material list and table patterns with custom dividers; no platform-specific identity is required. |
| web | Native tables with sticky headers carry the ledger on wide screens. |
| admin | Ledger rows suit operator queues, but operator views must show metadata only, never user line items. |

Grounding (pins on accepted main; bytes verified by digest, relevance not machine-checked):

- `product/01-product-spec.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:6f3c55a64eeb2c5a4138f0c6cdea59151871a8807f0a0305e2210639a4872221`)
- `product/08-experience-design-and-sdlc-plan.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:0310f45a7feb23454f600248f83bb040baab2ac0d2743a69fc66aec6f820d880`)

### DIR-02 Route Atlas

Material tradition `folded_paper_map`; graphic tradition `cartographic_wayfinding`.

- **Rationale:** The product frames a payoff date as a destination rather than a chore (product spec section 1). A route map shows where the household is, the remaining distance and the alternative routes (avalanche, snowball, hybrid) without ranking people.
- **Intended feel:** Oriented and unhurried: a trip planner open on the table, with the destination fixed and several honest routes to it.
- **Form language:** A single route line with stations for milestones; contour shading for uncertainty bands; a legend that names every symbol; muted terrain surfaces.
- **Signature interaction:** Route comparison: switching strategies redraws the route and moves the arrival station, showing time and interest difference side by side instead of a single verdict.
- **Content behavior:** Wayfinding phrasing such as you are here, remaining distance and arrival estimate; every estimate names its assumptions; missed payments read as a detour, not a failure.

Risks:

- The journey metaphor can imply the product steers the route, close to advice the spec forbids (section 2.3).
- Contour shading for uncertainty is faint on the illustrative surface and fails the non-text contrast minimum.
- Map literacy varies; the metaphor may confuse some people (unvalidated).

Accessibility notes:

- Every route and station needs a text summary; the map is never the only carrier of the payoff estimate.
- Uncertainty must be stated in words and ranges, not only by shading.
- Strategy switching must not rely on drag gestures; plain buttons are required.

Persona assumptions (unvalidated until docs#66):

- People in repayment respond to a destination framing with less anxiety than to a budget framing.
- A detour framing for missed payments avoids shame for people with irregular income.

Contrast feasibility (illustrative, non-binding values; WCAG 2.x relative luminance):

| Kind | Foreground | Background | Ratio | Minimum | Result |
|---|---|---|---|---|---|
| text | text_primary `#1B3A2F` | surface `#EEF3EC` | 11.02 | 4.5 | pass |
| text | text_secondary `#4F6B5E` | surface `#EEF3EC` | 5.18 | 4.5 | pass |
| ui | control_boundary `#6E8B7D` | surface `#EEF3EC` | 3.30 | 3.0 | pass |
| ui | focus_indicator `#1D4ED8` | surface `#EEF3EC` | 5.95 | 3.0 | pass |
| ui | progress `#C2410C` | surface `#EEF3EC` | 4.60 | 3.0 | pass |
| ui | uncertainty `#8FA79A` | surface `#EEF3EC` | 2.28 | 3.0 | fail |

Feasibility:

| Criterion | Assessment |
|---|---|
| density | Medium; the map needs space, so compact phones show a linear route strip with stations. |
| reduced_motion | Route redraw becomes an instant swap with the changed arrival stated in text. |
| localization_expansion | Station labels sit beside the line and can wrap; the legend grows vertically. |
| android | A custom canvas view for the route strip; standard Material controls for strategy choice. |
| web | A wider route view with the comparison table beside it. |
| admin | Not applicable to operator views beyond a neutral status strip; operators never see user routes. |

Grounding (pins on accepted main; bytes verified by digest, relevance not machine-checked):

- `product/01-product-spec.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:6f3c55a64eeb2c5a4138f0c6cdea59151871a8807f0a0305e2210639a4872221`)
- `product/08-experience-design-and-sdlc-plan.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:0310f45a7feb23454f600248f83bb040baab2ac0d2743a69fc66aec6f820d880`)

### DIR-03 Almanac Grid

Material tradition `uncoated_offset_print`; graphic tradition `international_typographic`.

- **Rationale:** Deterministic, verifiable claims are the product's value (product spec section 1). A strict typographic grid with one typeface family lets figures, dates and sources carry the identity, so clarity and provenance are the brand rather than decoration.
- **Intended feel:** Precise and quiet: a well-set reference timetable where the answer is always in the same place.
- **Form language:** Asymmetric column grid, strong type hierarchy, flush-left text, black on white with a single signal red; rules instead of boxes; no illustration.
- **Signature interaction:** Expanding footnote: every figure carries a numbered note that expands in place to show its source, method and uncertainty range.
- **Content behavior:** Short headline statements followed by figures and footnotes; numbers lead sentences; hedges are explicit ranges, never adjectives.

Risks:

- Can feel cold or clinical at moments of debt anxiety (unvalidated).
- Heavy reliance on typography makes the direction sensitive to script coverage beyond Latin.
- Close to generic minimal product styling; distinctness depends on disciplined grid and note behavior.

Accessibility notes:

- Footnote expansion must be keyboard and screen-reader operable with the expanded state announced.
- Signal red is reserved for warnings and focus and must always be paired with text or an icon shape.
- Type hierarchy must survive user text scaling without overlapping columns.

Persona assumptions (unvalidated until docs#66):

- People comparing payoff strategies prefer exact figures with sources over reassurance.

Contrast feasibility (illustrative, non-binding values; WCAG 2.x relative luminance):

| Kind | Foreground | Background | Ratio | Minimum | Result |
|---|---|---|---|---|---|
| text | text_primary `#111111` | surface `#FFFFFF` | 18.88 | 4.5 | pass |
| text | text_secondary `#595959` | surface `#FFFFFF` | 7.00 | 4.5 | pass |
| ui | control_boundary `#767676` | surface `#FFFFFF` | 4.54 | 3.0 | pass |
| ui | focus_indicator `#D7261E` | surface `#FFFFFF` | 5.01 | 3.0 | pass |
| ui | progress `#111111` | surface `#FFFFFF` | 18.88 | 3.0 | pass |
| text | warning `#D7261E` | surface `#FFFFFF` | 5.01 | 4.5 | pass |

Feasibility:

| Criterion | Assessment |
|---|---|
| density | Supports high density on web and admin; compact phones reduce to a single column with footnotes inline. |
| reduced_motion | Footnotes expand without animation; no motion is load-bearing. |
| localization_expansion | Flush-left text tolerates growth; the grid must allow columns to stack when labels expand. |
| android | Fits Material layout grids and typography roles with a constrained palette. |
| web | Natural fit for responsive grids. |
| admin | Well suited to operator queues and audit views that need dense, scannable metadata. |

Grounding (pins on accepted main; bytes verified by digest, relevance not machine-checked):

- `product/01-product-spec.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:6f3c55a64eeb2c5a4138f0c6cdea59151871a8807f0a0305e2210639a4872221`)
- `product/08-experience-design-and-sdlc-plan.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:0310f45a7feb23454f600248f83bb040baab2ac0d2743a69fc66aec6f820d880`)

### DIR-04 Cut Paper Household

Material tradition `layered_cut_paper`; graphic tradition `paper_collage`.

- **Rationale:** Household debt is a household problem (product spec section 1) and sharing must stay consent-based and revocable (section 2.1). Layered cut paper makes each person's share a separate, removable layer, so what is shared and what is private is physically legible.
- **Intended feel:** Warm, handmade and human: a family planning sheet made together, where pieces can be added or taken away.
- **Form language:** Overlapping flat paper shapes with torn or cut edges; each household member has a separate layer; warm pastel surfaces; soft offset edges instead of drop shadows.
- **Signature interaction:** Lift a layer: revoking a grant lifts that person's layer away at once, and the remaining view shows only what is still shared.
- **Content behavior:** Warm, second-person language; sharing states are named in full (shared totals only, shared with whom, until revoked); no blame wording for overdue items.

Risks:

- Pastel surfaces fail the non-text contrast minimum for the illustrative control boundary and progress shape, and provenance text fails body-text contrast.
- A playful craft look may undercut credibility for large debts (unvalidated).
- Layer metaphors can be hard to express to screen-reader users without careful structure.

Accessibility notes:

- Each layer needs a named region and an explicit owner and scope label.
- Control edges need a darker boundary than the illustrative value to meet non-text contrast.
- Torn-edge shapes must not obscure text or focus outlines.

Persona assumptions (unvalidated until docs#66):

- Couples managing shared debt understand separate layers as separate consent.
- A warm craft look lowers anxiety without trivialising debt.

Contrast feasibility (illustrative, non-binding values; WCAG 2.x relative luminance):

| Kind | Foreground | Background | Ratio | Minimum | Result |
|---|---|---|---|---|---|
| text | text_primary `#3B1F2B` | surface `#FBE9D7` | 12.51 | 4.5 | pass |
| text | text_secondary `#7A5C66` | surface `#FBE9D7` | 4.99 | 4.5 | pass |
| ui | control_boundary `#C98F7A` | surface `#FBE9D7` | 2.30 | 3.0 | fail |
| ui | focus_indicator `#3B1F2B` | surface `#FBE9D7` | 12.51 | 3.0 | pass |
| ui | progress `#E07A5F` | surface `#FBE9D7` | 2.49 | 3.0 | fail |
| text | provenance `#5E7A5A` | surface `#FBE9D7` | 4.02 | 4.5 | fail |

Feasibility:

| Criterion | Assessment |
|---|---|
| density | Low density; suits summaries and household views, poor for long transaction lists. |
| reduced_motion | Layer lift becomes an instant removal with a text confirmation of what is no longer shared. |
| localization_expansion | Labels sit on layers that must grow; fixed cut shapes would clip longer translations. |
| android | Custom drawn shapes are feasible but need care to keep Material touch targets and focus visible. |
| web | Layered shapes are feasible with vector drawing; performance on low-end devices needs a check. |
| admin | Not suited to operator tooling; admin would need a separate neutral treatment under the same thesis. |

Grounding (pins on accepted main; bytes verified by digest, relevance not machine-checked):

- `product/01-product-spec.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:6f3c55a64eeb2c5a4138f0c6cdea59151871a8807f0a0305e2210639a4872221`)
- `product/08-experience-design-and-sdlc-plan.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:0310f45a7feb23454f600248f83bb040baab2ac0d2743a69fc66aec6f820d880`)
- `product/client-state-taxonomy.json` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:040d2f0c27332ce3f6794a90139e714b3c50afb5b7340aa596d47b8866f2b3fb`)

### DIR-05 Drafting Table

Material tradition `drafting_vellum`; graphic tradition `technical_drawing`.

- **Rationale:** The what-if simulator is instant and deterministic (product spec section 3.2). A technical drawing shows a plan with dimensions, tolerances and revision marks, so a payoff plan reads as an engineered, checkable model and uncertainty is a stated tolerance.
- **Intended feel:** Competent and transparent: an engineer's plan you can check line by line, with every assumption dimensioned.
- **Form language:** Fine line work on a deep plan surface, dimension lines for amounts and durations, dashed lines for projected or uncertain values, a title block naming source and revision.
- **Signature interaction:** Revision block: each change to the plan adds a dated revision row naming what changed and why, and earlier revisions stay viewable.
- **Content behavior:** Labels in a measured, specification register; projections carry an explicit tolerance; every figure names its basis in the title block.

Risks:

- A dark plan surface may feel technical or intimidating to people new to debt planning (unvalidated).
- Dashed uncertainty lines are faint on the illustrative surface and fail the non-text contrast minimum.
- Thin line work degrades on low-density screens and in bright outdoor light.

Accessibility notes:

- Dimensioned values need text equivalents; the drawing is never the only source of a figure.
- Dashed lines need a second cue (a label such as projected) because dash patterns are hard to perceive.
- A light-surface variant must exist for people who need positive polarity.

Persona assumptions (unvalidated until docs#66):

- People who use the simulator want to inspect assumptions rather than only see a result.

Contrast feasibility (illustrative, non-binding values; WCAG 2.x relative luminance):

| Kind | Foreground | Background | Ratio | Minimum | Result |
|---|---|---|---|---|---|
| text | text_primary `#F2F6FA` | surface `#0B3D6B` | 10.21 | 4.5 | pass |
| text | text_secondary `#A9C2DB` | surface `#0B3D6B` | 6.03 | 4.5 | pass |
| ui | control_boundary `#7FA6CC` | surface `#0B3D6B` | 4.34 | 3.0 | pass |
| ui | focus_indicator `#FFD166` | surface `#0B3D6B` | 7.68 | 3.0 | pass |
| ui | progress `#FFFFFF` | surface `#0B3D6B` | 11.08 | 3.0 | pass |
| ui | uncertainty `#5E88B3` | surface `#0B3D6B` | 2.98 | 3.0 | fail |

Feasibility:

| Criterion | Assessment |
|---|---|
| density | High density for plans and schedules; title blocks collapse to a summary row on phones. |
| reduced_motion | Revisions appear as new rows without transitions. |
| localization_expansion | Dimension labels must reflow off the line when translations grow; fixed label boxes would clip. |
| android | Feasible with Material surfaces in a dark scheme plus a required light variant. |
| web | Feasible; vector line work scales on high-density displays. |
| admin | Revision blocks fit audit and change-history views for operators. |

Grounding (pins on accepted main; bytes verified by digest, relevance not machine-checked):

- `product/01-product-spec.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:6f3c55a64eeb2c5a4138f0c6cdea59151871a8807f0a0305e2210639a4872221`)
- `product/08-experience-design-and-sdlc-plan.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:0310f45a7feb23454f600248f83bb040baab2ac0d2743a69fc66aec6f820d880`)

### DIR-06 Painted Shopfront

Material tradition `enamel_painted_tin`; graphic tradition `indic_hand_painted_signage`.

- **Rationale:** The product serves households paying in rupees (product spec section 1). Hand-painted shopfront signage is a familiar public language of plain, bold, trustworthy statements; it can make the payoff date and next action unmistakable without banking imagery.
- **Intended feel:** Direct, local and confident: a clear painted sign that tells you what is here and what to do next.
- **Form language:** Bold display lettering for one headline figure, flat saturated panels, painted borders around actions, simple pictograms; body text stays in a plain readable face.
- **Signature interaction:** Next-step panel: one painted panel always names the single next action and its effect on the payoff date; other options sit below in plain text.
- **Content behavior:** Short imperative headlines and plain sentences; bilingual labels are anticipated; no slang, no hype, no urgency theatre.

Risks:

- Risk of cultural caricature if the signage tradition is used decoratively without local designers (unvalidated).
- Display lettering may not cover every Indic script equally well; body text must not use it.
- Saturated panels can feel loud during stressful moments.

Accessibility notes:

- Display lettering is limited to large text; body copy uses a highly legible face.
- Saturated yellow surfaces need checks for glare and for people with light sensitivity.
- Pictograms always carry visible text labels.

Persona assumptions (unvalidated until docs#66):

- Households outside metro areas find signage-style statements clearer than app conventions.
- A single named next step reduces decision anxiety more than a list of options.

Contrast feasibility (illustrative, non-binding values; WCAG 2.x relative luminance):

| Kind | Foreground | Background | Ratio | Minimum | Result |
|---|---|---|---|---|---|
| text | text_primary `#1A1A1A` | surface `#FFD23F` | 12.05 | 4.5 | pass |
| text | text_secondary `#5A3E00` | surface `#FFD23F` | 6.84 | 4.5 | pass |
| ui | control_boundary `#B3261E` | surface `#FFD23F` | 4.52 | 3.0 | pass |
| ui | focus_indicator `#1A1A1A` | surface `#FFD23F` | 12.05 | 3.0 | pass |
| ui | progress `#0F5132` | surface `#FFD23F` | 6.48 | 3.0 | pass |
| text | warning `#B3261E` | surface `#FFD23F` | 4.52 | 4.5 | pass |

Feasibility:

| Criterion | Assessment |
|---|---|
| density | Low to medium; one headline panel per view, plain lists below. |
| reduced_motion | Static panels; no motion is needed. |
| localization_expansion | Display headlines must shrink or wrap for longer scripts; panels are flexible rectangles. |
| android | Feasible with Material components inside painted panel containers. |
| web | Feasible; display lettering limited to headlines keeps performance acceptable. |
| admin | Operators need a calmer neutral variant; signage panels would overload queue views. |

Grounding (pins on accepted main; bytes verified by digest, relevance not machine-checked):

- `product/01-product-spec.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:6f3c55a64eeb2c5a4138f0c6cdea59151871a8807f0a0305e2210639a4872221`)
- `product/08-experience-design-and-sdlc-plan.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:0310f45a7feb23454f600248f83bb040baab2ac0d2743a69fc66aec6f820d880`)

### DIR-07 Handloom Weave

Material tradition `handloom_textile`; graphic tradition `warp_and_weft_pattern`.

- **Rationale:** A household budget is many threads held together: income, debts, goals and members (product spec sections 1 and 3.5). A woven pattern shows each thread separately and the cloth they form together, so shared totals and private details are distinct threads.
- **Intended feel:** Patient and resilient: cloth built row by row, where a dropped thread is mended rather than hidden.
- **Form language:** Fine woven textures as quiet backgrounds, coloured threads for each debt or goal, rows of weave as months, indigo and natural cloth surfaces.
- **Signature interaction:** Row by row: each month adds a woven row; a missed payment shows as a mended thread with its note, not a hole.
- **Content behavior:** Gentle, steady phrasing; progress is described as rows completed and rows remaining; mending language for setbacks.

Risks:

- Illustrative control boundary and uncertainty threads fail the non-text contrast minimum on the cloth surface.
- Textures can reduce text legibility and add visual noise for some readers.
- Weaving metaphors may not translate across all audiences (unvalidated).

Accessibility notes:

- Textures sit behind text only at very low intensity, with a plain-surface option.
- Thread colours need distinct patterns or labels so meaning does not rely on colour alone.
- Monthly rows need a text table equivalent.

Persona assumptions (unvalidated until docs#66):

- A mending framing for missed payments supports people with irregular income.

Contrast feasibility (illustrative, non-binding values; WCAG 2.x relative luminance):

| Kind | Foreground | Background | Ratio | Minimum | Result |
|---|---|---|---|---|---|
| text | text_primary `#2E1F3D` | surface `#F4EFE6` | 13.29 | 4.5 | pass |
| text | text_secondary `#6B5B7B` | surface `#F4EFE6` | 5.38 | 4.5 | pass |
| ui | control_boundary `#A08FB3` | surface `#F4EFE6` | 2.59 | 3.0 | fail |
| ui | focus_indicator `#B5179E` | surface `#F4EFE6` | 5.12 | 3.0 | pass |
| ui | progress `#1E5AA8` | surface `#F4EFE6` | 5.94 | 3.0 | pass |
| ui | uncertainty `#C9B8D9` | surface `#F4EFE6` | 1.61 | 3.0 | fail |

Feasibility:

| Criterion | Assessment |
|---|---|
| density | Medium; the weave suits monthly summaries, while transaction lists use plain rows. |
| reduced_motion | New rows appear without a weaving animation. |
| localization_expansion | Labels sit outside the weave and can wrap freely. |
| android | Feasible with textured surfaces as optional backgrounds behind Material components. |
| web | Feasible; textures must be lightweight and removable. |
| admin | Operators use the plain-surface variant only. |

Grounding (pins on accepted main; bytes verified by digest, relevance not machine-checked):

- `product/01-product-spec.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:6f3c55a64eeb2c5a4138f0c6cdea59151871a8807f0a0305e2210639a4872221`)
- `product/08-experience-design-and-sdlc-plan.md` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:0310f45a7feb23454f600248f83bb040baab2ac0d2743a69fc66aec6f820d880`)
- `product/client-state-taxonomy.json` at `1722fc79ab2abee15d3adc2ed2f3baaad4bd6ed4` (`sha256:040d2f0c27332ce3f6794a90139e714b3c50afb5b7340aa596d47b8866f2b3fb`)

## Probes (static, synthetic, text only)

### PRB-01 debt_progress

Format `text`; data origin `synthetic`; access depiction `none`.

Synthetic household with two fictional debts: a card balance of INR 40,000 and a personal loan of INR 1,20,000. The projected payoff is 18 months away under the avalanche strategy and 20 months under snowball; one payment last month was late. The probe asks whether progress, the projection's uncertainty and the person's control are legible without praise or blame.

| Candidate | Rendering |
|---|---|
| DIR-01 | Two ledger accounts, each closing with a payoff line; the late payment is an entry with a margin note, not a red mark on the person. A footer line states the projection range of 17 to 20 months and its assumptions. |
| DIR-02 | A route strip with a you-are-here station and an arrival station 18 months on; the late payment appears as a short detour. Switching to snowball moves the arrival two months later and shows the interest difference in text. |
| DIR-03 | Headline figure 18 months, followed by two columns for the debts and footnote 1 giving the method and a range of 17 to 20 months. The late payment is a neutral row in the history. |
| DIR-04 | Two paper shapes shrinking as balances fall, labelled with remaining amounts; a calm note says one payment arrived late and the plan has adjusted. Text states the 18-month estimate and its range. |
| DIR-05 | A plan drawing with a dimension line from today to the payoff date, tolerance marked as 17 to 20 months; the late payment is revision 3 in the title block with its effect stated. |
| DIR-06 | One painted panel: Debt free in about 18 months; next step: pay INR 2,000 extra on the card. Below, plain text lists both debts and notes the late payment without judgement. |
| DIR-07 | Woven rows for each month paid, two coloured threads for the debts, and remaining rows shown as unwoven warp; the late month is a mended row with a note. Text gives 18 months and the range. |

### PRB-02 transaction_clarification

Format `text`; data origin `synthetic`; access depiction `none`.

Synthetic imported transaction of INR 1,500 from a fictional merchant called Sample Grocer, auto-categorised as dining with low confidence. The person corrects it to groceries. The probe asks whether the source of the original reading, the uncertainty and the correction are legible and reversible.

| Candidate | Rendering |
|---|---|
| DIR-01 | The entry shows dining struck through and groceries written beside it, with a margin note: imported from statement, categorised automatically with low confidence, corrected by you; undo is available. |
| DIR-02 | The transaction is a waypoint with a dotted connector marked uncertain; after correction the connector becomes solid and a legend line names the change and its source. |
| DIR-03 | The row reads INR 1,500, Sample Grocer, groceries, with footnote 2 explaining the original automatic category, its low confidence and the correction; the footnote offers undo. |
| DIR-04 | A paper tag on the transaction flips from dining to groceries; a small note under it names where the first guess came from and how to reverse the change. |
| DIR-05 | The transaction appears in a schedule with a dashed category field marked unconfirmed; correcting it adds a revision row stating the old value, the new value and the reason. |
| DIR-06 | A painted panel asks: Is this groceries? with two plain buttons; after the answer the panel states what changed and offers undo in plain text. |
| DIR-07 | The transaction is a thread with a loose end marked unsure; after correction it is woven into the groceries row with a note naming the original guess and an undo action. |

### PRB-03 household_privacy

Format `text`; data origin `synthetic`; access depiction `explicit_revocable_grant`.

Synthetic household of two fictional members, Member A and Member B. Member A has granted Member B a view of debt totals only, not transactions; Member A can revoke at any time without notifying the reason, and every view by Member B appears in Member A's access log. The probe asks whether the scope of the grant, who can see what and the way out are legible, and that shared access never looks like ordinary browsing.

| Candidate | Rendering |
|---|---|
| DIR-01 | A shared summary page headed: Shared with Member B by Member A, totals only, revocable. Transaction rows are not present. Member A's own view has an access-log column listing each view by Member B and a plain stop-sharing action. |
| DIR-02 | Member B sees a separate shared route showing totals only, framed with a legend line naming the grant and its scope; Member A's map shows a viewer marker and a stop-sharing action that removes the shared route at once. |
| DIR-03 | A labelled shared section: Grant from Member A, scope debt totals, revocable at any time. Member A's settings list the grant, the access log and a stop-sharing action in the same grid position every time. |
| DIR-04 | Member B sees one separate layer marked shared by Member A, totals only. Member A can lift the layer away at once; the log of views sits beside the layer, and leaving sends no dramatic notification. |
| DIR-05 | The shared view carries a title block stating grantor, scope and revocability; Member A's plan has a revision row for each grant change and a view log, with a stop-sharing action. |
| DIR-06 | A painted header on the shared view says: Shared by Member A, totals only. Member A's panel offers one plain action, Stop sharing, and a line of text showing the latest views by Member B. |
| DIR-07 | Member B sees only the combined cloth of totals, with a woven label naming Member A's grant; Member A sees which threads are shared, the view log and an action to pull the shared thread out at once. |

### PRB-04 operator_urgency

Format `text`; data origin `synthetic`; access depiction `audited_elevation`.

Synthetic operator scenario: a fictional support ticket reports a failed statement import for a fictional user. The operator sees system metadata only. Opening any user financial detail requires a time-boxed elevation with a stated reason, recorded in an audit trail the user can see. The probe asks whether urgency, the boundary of operator access and the audited elevation are legible, and that admin access never looks like ordinary browsing.

| Candidate | Rendering |
|---|---|
| DIR-01 | An operator queue in ledger rows with import status and age; user amounts are absent. Requesting detail opens an elevation entry requiring a reason and showing its expiry, written to the audit ledger. |
| DIR-02 | A neutral status strip shows the import failure as a blocked segment; detail access is a separate gated step that names the reason, duration and audit record before anything is shown. |
| DIR-03 | A dense grid of tickets sorted by urgency with metadata only; the elevation request is a distinct form with reason, scope and expiry, and the granted view carries a persistent elevated banner with time remaining. |
| DIR-04 | Operators use a plain neutral variant: a ticket list with metadata only and a separate elevation request naming reason and expiry; no household layers are shown to operators. |
| DIR-05 | A ticket sheet with a title block for system metadata; elevation adds a stamped revision row with reason and expiry, and the elevated view is framed and labelled until the time box ends. |
| DIR-06 | Operators use a calm neutral variant; one panel names the urgent ticket and its next step, and elevation is a separate step with a reason field, an expiry and an audit notice. |
| DIR-07 | Operators use the plain-surface variant: a metadata-only list, and an elevation step stating reason, scope and expiry; the elevated view stays visibly framed and logged. |

## Direction record (pending)

Version `0.1.0`, gate `D2`, status `pending`, prepared by role `systems` (PenniLogic/docs#76). Participant count: not recorded (null; no study has run). Decision: none (null). Token contract: `not_started` (PenniLogic/docs#55).

Evidence:

| Kind | Reference | Origin | State |
|---|---|---|---|
| representative_user_study | pending:PenniLogic/docs#53 | pending | pending |

Reviews:

| Role | State | Reviewer |
|---|---|---|
| accessibility | pending | none recorded |
| content | pending | none recorded |
| android_design | pending | none recorded |
| web_design | pending | none recorded |
| admin_design | pending | none recorded |

Semantic roles:

| Role | Meaning |
|---|---|
| surface | The base reading plane on which every other role sits. |
| surface_raised | A plane set apart from the base to group a related task without implying depth or status. |
| text_primary | Body copy, figures and labels that carry the main meaning. |
| text_secondary | Supporting copy such as sources, dates and explanations. |
| control_boundary | The visible edge of any control a person can act on. |
| focus_indicator | The location of keyboard or switch focus, always visible. |
| emphasis | The one figure or statement a view exists to answer. |
| progress | Debt paid down and time remaining, shown as fact rather than reward. |
| uncertainty | Ranges, low-confidence readings and projections, always stated with their basis. |
| provenance | Where a figure came from, who changed it and when. |
| warning | Conditions needing attention, stated without blame or alarm. |
| control | Actions that change the person's plan, sharing or data, including how to reverse them. |

Platform consequences:

| Platform | Consequence |
|---|---|
| android | Whichever direction is selected is expressed through Material components and semantic roles only; no Android-specific identity, palette or type system may be introduced, and the selected direction's feasibility notes for Android apply. |
| web | The customer web app adopts the same semantic roles and thesis as Android; responsive layouts may reflow but may not invent a separate web identity. |
| admin | The admin console uses a neutral, metadata-first variant of the same direction; operator access to user financial detail is always shown as an audited, time-boxed elevation, never as ordinary browsing. |

Unresolved risks:

| Risk | Disposition | Owner |
|---|---|---|
| No representative-user concept evidence exists yet; preference, comprehension and identification for every candidate are unknown (docs#53). | open | PenniLogic/docs#53 |
| Persona-dependent assumptions in every candidate are unvalidated (docs#66). | open | PenniLogic/docs#66 |
| D2 requires the D1 experience architecture, which is not accepted: personas (docs#66), journeys and service blueprints (docs#67), platform allocation and sitemaps (docs#74) and the traceability registry (docs#75). | open | PenniLogic/docs#76 |
| Illustrative contrast values fail for some candidates; the selected direction's final values must be set and verified by the token contract (docs#55). | open | PenniLogic/docs#55 |
| Accessibility, Content and Android, web and admin feasibility reviews have not been recorded. | open | PenniLogic/docs#76 |
| Cultural fit of the signage and textile traditions needs review by designers from those traditions. | open | PenniLogic/docs#76 |

Implementation consequences:

- Component and screen work waits for an approved direction; no platform team may start a separate visual system.
- The token contract is authored in docs#55 after approval and consumes only the semantic roles named here.
- The governed library (docs#78) references the approved record version, never a pending one.
- The token contract (docs#55) and the platform tickets must cite the selected record version once it is approved; this pending record is not a version they may cite.
- Reversal requires a superseding D2 record and a design-system migration plan.

Consumers:

- PenniLogic/docs#55
- PenniLogic/docs#78

Held gates:

- pending:PenniLogic/docs#53
- pending:PenniLogic/docs#66
- pending:PenniLogic/docs#67
- pending:PenniLogic/docs#74
- pending:PenniLogic/docs#75
- pending:PenniLogic/infra#22

Supersession: A superseding D2 record signed by the decision coordinator and a design-system migration plan.
