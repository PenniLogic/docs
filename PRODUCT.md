# Product

<!-- impeccable:product-schema 1 -->

## Platform

adaptive

## Users

- India-first adults managing consumer debt, irregular or salaried income, daily expenses, savings,
  assets and financial goals.
- Partners and household members who deliberately share selected aggregates, details or joint goals
  under per-person grants and revocation.
- Temporary split-group participants who need transparent obligations, settlements and disputes.
- Customer-support, privacy, compliance, security, billing and platform operators using a separately
  deployed admin product with least privilege and four-eyes controls.
- Accessibility needs include screen readers, keyboard and switch access, large text, high contrast,
  reduced motion, constrained devices, low bandwidth, varied financial literacy and supported Indian
  languages.

## Product Purpose

PenniLogic helps a person understand where their money goes, become debt-free, plan goals and
coordinate shared obligations without surrendering control of sensitive financial data. Success is
not screen engagement alone: users can verify every figure, correct ambiguity, recover safely,
export or erase their data, and make sustained progress against a chosen goal.

## Positioning

PenniLogic is a debt-first personal finance operating system. Its differentiating mechanism combines
deterministic financial arithmetic, on-device capture of financial messages, explicit clarification,
privacy-preserving household and split workflows, and an optional backend-routed AI explanation
layer. AI never computes money or initiates a payment.

## Operating Context

- Native Android is the primary personal and capture surface. It must remain useful offline and when
  every optional permission is denied.
- Customer web is the large-screen analysis, bulk-management, planning, export and recovery surface.
- Admin is a distinct operator product with a separate authentication domain and no general-purpose
  financial browser.
- People may arrive anxious about debt, uncertain about a captured payment, under connectivity or
  device constraints, or in a coercive household situation. Operator users may be responding to a
  statutory clock or security incident.
- The product is India-first and must respect Google Play policy, DPDP/CERT-In obligations, INR
  conventions and future localization without embedding legal values in interface copy.

## Capabilities and Constraints

- Money is represented as integer minor units with currency and exponent. Floating-point financial
  arithmetic is prohibited.
- The ledger is balanced, append-only and corrected through reversing entries.
- Raw SMS, notification and email content never leaves the device; raw-derived digests are also
  prohibited at network, sync and export boundaries.
- Sharing is default-deny, per person and category. Aggregate and detail access are separate.
- Entitlements and quota are server-authoritative. Billing, refunds and plan versions are auditable.
- AI traffic is backend-routed. Provider keys and custom endpoints are step-up protected, revocable
  and suspended after account recovery.
- Android, customer web and admin share product truth and semantic tokens while honoring platform
  conventions and intentional role-specific divergence.
- Every production surface requires designed empty, loading, error, offline or degraded, stale,
  denied, destructive, success and recovery states where applicable.
- Current architecture and legal decisions remain blocked by their recorded ADR or counsel gates;
  interface work consumes those decisions and does not guess them.

## Brand Commitments

- Product name: PenniLogic.
- Debt-first, calm and evidence-led rather than shame-based, gamified or promotional.
- Trust is demonstrated through derivations, provenance, reversibility and control, not security
  theater or unsupported claims.
- The durable visual world, voice system, logo and production asset library are open decisions owned
  by the Chief Design Officer and the design-direction gate. No implementation team may invent them.

## Evidence on Hand

- Product truth and feature scope: `product/01-product-spec.md`.
- Architecture and security constraints: `architecture/` and `adr/`.
- Competitor and ingestion research: `research/`.
- Current design-first planning assurance and release authorization: `product/09-design-first-planning-assurance.md`.
- Durable implementation backlog and validation: `planning-automation/backlog-v2/`.
- No approved visual identity, production UI, user-research corpus, design library or final content
  system exists yet. Future work must not fabricate user quotes, outcomes or brand approval.

## Product Principles

1. Make the next financial action understandable and reversible.
2. Show the source, status and derivation of every consequential figure.
3. Ask rather than guess when capture or intent is ambiguous.
4. Preserve dignity, privacy and safe exit in personal and shared-money experiences.
5. Design once as product truth, adapt deliberately per platform, and validate with real users before
   frontend implementation.

## Accessibility & Inclusion

WCAG 2.2 AA is the minimum for web and admin; Android targets current Material accessibility
guidance and applicable WCAG outcomes. Critical journeys require screen-reader, keyboard or switch,
large-text/zoom, high-contrast, reduced-motion and non-color verification. Research recruitment must
include varied financial literacy, device capability, language, age and disability needs. Coercive
control, privacy in shared environments and safe concealment are first-class inclusion concerns.

## Explicitly Open Design Decisions

- Visual identity, type, color, illustration, data-visualization and motion direction.
- Final navigation models and information density per platform.
- Initial supported language set and localization rollout.
- Production Figma organization, library boundaries and design-token delivery tooling.
- Quantitative usability thresholds beyond the minimum gates defined by the design programme.
