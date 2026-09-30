# PenniLogic — Regulatory & Compliance Landscape
**Version:** 1.0-draft
**Research date:** September 2026
**Status:** Research findings — NOT legal advice. Requires qualified counsel review before reliance.
**Scope:** India (primary), EU, UK, US, UAE, Singapore, AI-specific regulation, certifications.

---

> **DISCLAIMER:** This document records research findings for internal planning purposes only. It does not constitute legal advice and must be reviewed by qualified legal counsel in each jurisdiction before any compliance decisions are made. Regulatory landscapes change; always verify current status with primary sources.

---

## Table of Contents
0. [Obligation-to-ticket ownership matrix](#0-obligation-to-ticket-ownership-matrix)
1. [India — Account Aggregator Framework](#1-india--account-aggregator-framework)
2. [India — Data Protection (DPDP Act & CERT-In)](#2-india--data-protection)
3. [India — Financial Advice Boundary](#3-india--financial-advice-boundary)
4. [Global Expansion — EU, UK, US, UAE, Singapore](#4-global-expansion)
5. [AI-Specific Regulation](#5-ai-specific-regulation)
6. [Certifications](#6-certifications)
7. [MVP India Launch Checklist](#7-mvp-india-launch-checklist)
8. [Before Global Launch Checklist](#8-before-global-launch-checklist)
9. [Risk Table](#9-risk-table)
10. [Sources Table](#10-sources-table)

---

## 0. Obligation-to-ticket ownership matrix

Every launch-relevant obligation below names the item that owns it. This table is the reconciliation
target: `T-CMP-04` runs an automated check that **fails when an obligation here has no owning ticket,
when a row names a ticket that does not exist, or when a row's claim contradicts that ticket's
state**. An obligation without an owner is a gap, not an omission.

**Numbers in this table are not legal conclusions.** Every statutory value - a reporting window, a
response clock, a retention period, a monetary threshold - is read at runtime from a **versioned,
counsel-reviewed jurisdiction profile** owned by `T-CMP-04`, with a reviewer, a review date and an
expiry. When no current profile exists for a jurisdiction, the dependent behaviour **fails closed**:
the system refuses to assert an unreviewed position rather than guessing one. The figures in the
sections below are research findings that a profile may confirm or correct.

| # | Obligation | Owning ticket | Epic | Gate |
|---|---|---|---|---|
| O-1 | Consent ledger and purpose registry, with versioned purposes and withdrawal | `T-CMP-01` | E27 | Beta |
| O-2 | Data-principal rights: access, correction, erasure, nomination, operator fulfilment and their status clocks | `T-CMP-01`, `T-ADM-13` | E27, E13 | Beta |
| O-3 | Grievance channel, named grievance officer, operator queue and published response clock | `T-CMP-01`, `T-ADM-13` | E27, E13 | Beta |
| O-4 | Retention, crypto-erasure and restore-safe deletion enforcing the published periods | `T-CMP-01`, `T-SEC-02`, `T-SEC-07` | E27, E19 | Beta |
| O-5 | Contract shapes for consent, rights requests, export and transparency | `T-CON-09` | E02 | Beta |
| O-6 | Pre-onboarding consent, age gate and permission dashboard | `T-CMP-02` | E27 | Beta |
| O-7 | Third-party component and SDK inventory, payload scrubbing, Play Data Safety declaration | `T-CMP-03` | E27 | Beta |
| O-8 | Evidence that no raw message content egresses: traffic capture on every release candidate | `T-QA-09` | E25 | Beta |
| O-9 | CERT-In breach reporting drill and log retention | `T-CMP-04` | E27 | Beta |
| O-10 | Versioned counsel-reviewed jurisdiction profiles and the fail-closed rule | `T-CMP-04` | E27 | Beta |
| O-11 | Automated obligation and risk reconciliation against the board | `T-CMP-04` | E27 | Beta |
| O-12 | Data protection floor before any environment holds real data: encryption, blind index, RLS | `T-SEC-01` | E19 | Beta |
| O-13 | Crypto-shredding erasure across shared data, with verification | `T-SEC-02` | E19 | Beta |
| O-14 | Key rotation, retirement and post-erasure blind-index handling | `T-SEC-06` | E19 | Beta |
| O-15 | User-visible transparency, export, deletion and consent surfaces (Android) | `T-TRU-02` | E23 | Beta |
| O-16 | User-visible consent centre, transparency and analytics opt-out (web) | `T-TRU-03` | E23 | Post-beta |
| O-17 | Cross-user access log visible to the data subject | `T-TRU-04` | E23 | Post-beta, gated on family sharing |
| O-18 | Advice-boundary disclaimers and the SEBI non-advice posture | `T-CMR-01` | E20 | Launch |
| O-19 | GST: GSTIN capture, place of supply, e-invoicing threshold, OIDAR treatment | `T-BIL-04` | E14 | First paid transaction |
| O-20 | Auto-renewal disclosure, cancellation parity and dark-pattern prohibitions | `T-BIL-03` | E14 | First paid transaction |
| O-21 | Immutable plan versions, advance notice and grandfathering on price or entitlement change | `T-BIL-10` | E14 | First price change |
| O-22 | Administrative access lifecycle, approver eligibility and recertification | `T-ADM-06` | E13 | Before any unmask capability |
| O-23 | Support intake, ticket verification for unmasking, and the SLA | `T-SUP-01` | E13 | Before any unmask capability |
| O-24 | AI disclosure, refusal boundary and harmful-answer containment | `T-AI-06`, `T-AIP-05` | E17, E18 | Before AI ships |
| O-25 | Account Aggregator posture: Route D, and the conditions that would change it | `T-AAG-01` | E29 | Not before launch |
| O-26 | Payment-data localisation posture and processor register | `T-CMR-01`, `T-PLT-03` | E20, E24 | Post-beta |
| O-27 | Private-beta evidence gate aggregating O-1 to O-15 and O-29 to O-31 | `T-REL-02` | E25 | Beta |
| O-28 | Public-launch evidence gate including the penetration test and support readiness | `T-REL-03` | E25 | Launch |
| O-29 | No standing human production-data access and governed break-glass reads | `T-PLT-05` | E24 | Before real data |
| O-30 | Google Play Financial features declaration, prohibited-permission scan and Contact Picker invitation path | `T-CMP-05` | E27 | Before any Play test track |
| O-31 | Android 16 / API 36 target and policy-behavior baseline | `T-AND-07` | E01 | Before Android feature implementation |

---

## 1. India — Account Aggregator Framework

**Applicability:** APPLIES AT SCALE (AA data pull is a future enhancement; SMS on-device parsing is the MVP path)

### 1.1 How the AA Framework Works

The Account Aggregator (AA) framework, introduced by RBI, enables consent-based digital sharing of financial data between regulated entities. Three roles exist:

- **FIP (Financial Information Provider):** Banks, NBFCs, mutual fund RTAs, insurance companies, pension funds, GSTN — entities that *hold* user financial data.
- **AA (Account Aggregator):** An NBFC-AA licensed by RBI that acts as a consent manager and encrypted data pipe. The AA never stores the actual data. Licensed AAs include **Finvu** (Cookiejar Technologies), **OneMoney**, **CAMSFinserv**, **NADL** (NSDL e-Governance), **Perfios Anumati**, and **PhonePe AA**. As of early 2026, ~6–8 live AAs exist.
- **FIU (Financial Information User):** An entity that *receives* user-permissioned data from an AA for a declared purpose (lending, PFM, wealth management, insurance, etc.).

The **Sahamati** collective (non-profit industry alliance) maintains the Central Registry of live FIPs/FIUs/AAs, provides sandbox access, and empanels certification bodies. It does not itself grant regulatory status.

*Sources:* [Sahamati FIU page](https://sahamati.org.in/fiu/); [Sahamati TSP page](https://sahamati.org.in/technology-service-provider-tsp/); [DFS AA Framework](https://financialservices.gov.in/account-aggregator-framework)

---

### 1.2 THE CRITICAL QUESTION: Can a Non-Regulated Fintech Be an FIU?

**Answer: No — not directly. An FIU must be registered and regulated by at least one Financial Sector Regulator (FSR): RBI, SEBI, IRDAI, or PFRDA.**

The Sahamati FIU onboarding page (the primary public-facing source) states explicitly:

> *"According to RBI's Account Aggregator Master Directive, entities who want to become FIUs need to be registered and regulated by at least any one of the Financial Service Regulators (FSR), namely — RBI, SEBI, IRDAI, PFRDA."*
— [https://sahamati.org.in/fiu/](https://sahamati.org.in/fiu/)

**What this means for PenniLogic:**

| Entity Type | FIU Eligibility |
|---|---|
| Bank / NBFC / RBI-regulated entity | ✅ Eligible |
| SEBI-registered Investment Adviser / Broker | ✅ Eligible |
| IRDAI-registered insurer/intermediary | ✅ Eligible |
| PFRDA-registered pension entity | ✅ Eligible |
| **Non-regulated fintech startup (e.g., PenniLogic as-is)** | ❌ **NOT eligible directly** |

**PenniLogic's viable routes to AA data:**

**Route A — Partner with a Regulated FIU (Recommended for MVP+)**
Work with a regulated entity (e.g., a bank, NBFC, or SEBI-IA partner) that is already an FIU. The partner pulls data via AA with user consent; PenniLogic receives the structured data from the partner under a data-sharing agreement. The regulated entity bears FIU responsibility. This is operationally viable and used by many non-regulated fintechs today.

**Route B — Use a Technology Service Provider (TSP) that builds FIU modules**
TSPs (Setu, Perfios, Digitap, Cygnet, FinBox, Finarkein, etc.) build and operate FIU-compliant modules. Critically, **the TSP builds the tech but the underlying legal FIU entity must still be regulated**. A TSP enables a regulated entity to connect to AA quickly; it does not allow a non-regulated party to circumvent the FIU eligibility requirement. TSPs cannot grant FIU status.
*Source:* [Sahamati TSP page](https://sahamati.org.in/technology-service-provider-tsp/fip-fiu-tsp/); [Setu Docs](https://docs.setu.co/data/account-aggregator/fi-data-types)

**Route C — Obtain Regulatory Status**
Register as an NBFC with RBI (capital requirement ~₹10 Cr for NBFC-ND, complex governance requirements), or obtain SEBI IA registration (lower barrier, relevant for a PFM-advisory product). SEBI IA registration would make PenniLogic both a regulated entity eligible for FIU status AND legitimize the financial advice features. This is the *strategically cleanest long-term path* but requires counsel and regulatory runway.

**Route D — Stay with SMS/On-Device Parsing for MVP**
Since raw SMS is parsed on-device and only structured transaction records leave the phone, PenniLogic avoids the AA FIU question entirely for MVP. This materially reduces compliance exposure because the AA Master Directive only governs entities accessing data *through the AA network*. On-device SMS parsing with user consent is a separate category not governed by the AA framework.

**⚠️ COUNSEL FLAG:** The RBI Master Direction on AA (2016, updated) should be reviewed directly with a legal adviser to confirm current FIU eligibility criteria, especially given evolving RBI guidance. The above is based on Sahamati's published guidance as of 2025–26.

---

### 1.3 Available FI Types via AA

As of 2024–2026, the AA framework supports 23+ FI types. Key ones relevant to PenniLogic's use case:

| FI Type | Data Available | Granularity |
|---|---|---|
| DEPOSIT | Savings/current balance, account profile | Up to 6 months transactions; date, amount, type, narration, counterparty |
| TERM_DEPOSIT | FD details, balance, maturity | Summary level |
| RECURRING_DEPOSIT | Schedule, contributions, balance | Summary level |
| MUTUAL_FUNDS | Folio summary, holdings, NAV, transaction history | Scheme-level; SIP, purchase, redemption history |
| EQUITIES / ETF | Portfolio positions, valuation | Holdings summary |
| NPS | PRAN, corpus, scheme breakdown, contribution history | Date-wise contributions, withdrawals |
| INSURANCE_POLICIES / ULIP | Policy summary, premiums paid, coverage | Summary level |
| EPF / PPF | Balance, transaction history | Summary level |
| GSTN (GSTR1/3B) | GST returns, sales summary, ITC | Monthly/quarterly filing summary |

*Source:* [Setu Docs — FI Data Types](https://docs.setu.co/data/account-aggregator/fi-data-types); [ReBIT AA Schemas](https://api.rebit.org.in/schema); [CyberSigma AA overview](https://cybersigmacs.com/knowledge-center/account-aggregator/)

**Transaction granularity:** Individual transaction records include date, amount, transaction type (credit/debit), narration/description, mode (NEFT/UPI/IMPS/etc.), and counterparty details where available. This is rich enough for PFM, cashflow analysis, and debt-tracking use cases.

**Costs:** AA data pull pricing is not publicly standardized; it is negotiated commercially between the FIU and the AA. As of 2025, costs are typically per-consent or per-data-fetch and range from nominal (for bulk enterprise deals) to a few rupees per transaction pull for smaller players. TSPs like Setu/Perfios bundle AA API access with analytics at SaaS pricing. UNVERIFIED — confirm with specific AAs.

**Is PFM an accepted AA use case?** Yes. "Personal Finance Management" is a recognized consent purpose under the AA ecosystem. The AA Consent Artefact requires a declared purpose; PFM, debt management, and financial planning are valid purposes.

*Scale indicator as of March 2026: 284.6M linked accounts, 179+ FIPs, ~1,000 FIUs.*

---

## 2. India — Data Protection

### 2.1 Digital Personal Data Protection (DPDP) Act 2023 & Rules 2025

**Applicability:** PHASED COMMENCEMENT (Rules notified; product obligations and exact commencement dates must be read from the Gazette notification and a versioned counsel-reviewed jurisdiction profile)

#### Current Status (September 2026)
- **DPDP Act 2023:** Notified August 2023. In force.
- **DPDP Rules 2025:** **Notified 13–14 November 2025** after 6,900+ public submissions. The Rules operationalize the Act.
- **Data Protection Board of India (DPBI):** Established post-Rules notification (late 2025).
- **Enforcement timeline:** Different provisions commence on different dates. The Consent Manager provisions govern entities that choose to register and operate as Consent Managers; they do **not** create a universal deadline requiring every Data Fiduciary to integrate with one.
- **PenniLogic decision:** Do not build or claim mandatory Consent Manager integration without a written applicability opinion. Implement direct, verifiable consent and rights handling now, and keep a contract boundary that could support a registered Consent Manager later.
- **Counsel gate:** Before onboarding, counsel must publish the applicable commencement dates and statutory values in the machine-readable jurisdiction profile owned by `T-CMP-04`; prose in this document is not a runtime source.

*Sources:* [PIB notification PDF](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf); [NitiBharat DPDP Guide](https://nitibharat.com/dpdp-rules-2025.html); [Taxmann DPDP analysis](https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/); [ConsentOS timeline](https://consentos.in/learn/dpdp-compliance-timeline/)

#### Key Obligations for PenniLogic as a Data Fiduciary

| Obligation | Detail | PenniLogic Action |
|---|---|---|
| **Lawful basis for processing** | Consent is primary basis for personal data processing | Must obtain granular, purpose-specific consent before processing bank/salary/debt data |
| **Consent language** | Must be clear, plain language; purpose-specific | Rewrite onboarding consent flows before Nov 2026 |
| **Consent Manager interoperability** | Optional unless a counsel-reviewed applicability decision says otherwise | Preserve an integration boundary; do not represent it as a launch obligation |
| **Data Principal rights** | Right to access, correct, erase personal data | Build in-app data request/deletion flows |
| **Breach notification** | Notify the Board and affected users using the applicable staged content and time requirements | Read values from the counsel-reviewed jurisdiction profile and rehearse the runbook |
| **Children's data** | Parental consent required for minors; verifiable mechanism needed | Restrict app to 18+ or build verifiable parental consent |
| **Data minimisation** | Collect only what is necessary | Audit what data is collected; justify each field |
| **Retention and Rule 6 security records** | Storage limitation must be reconciled with any applicable minimum retention of security logs and associated personal data | Counsel defines the exact classes, period and post-erasure treatment; engineering enforces the versioned profile |
| **Significant Data Fiduciary (SDF)** | Higher obligations if processing large volume of sensitive data at scale | Unlikely at MVP; monitor as user base grows (criteria TBD by DPBI) |
| **Cross-border transfers** | Transfers permitted to countries not on DPBI's "negative list"; adequacy-style regime | Monitor negative list; assess if US/EU AI API providers are covered |
| **Penalties** | Up to ₹250 crore for serious violations | Full enforcement from May 2027 |

**Financial data as personal data:** Bank transaction data, salary data, debt information, and AI-derived financial insights all constitute personal data (and likely sensitive personal data) under DPDP. Treat with highest care.

**Erasure versus mandatory security retention:** The notified Rule 6 text appears to require relevant
logs and personal data that enable detection, investigation, remediation or continued processing to
be retained for one year unless another law requires longer. Its exact scope and commencement for
PenniLogic require counsel confirmation. That can conflict with an immediate, absolute deletion
claim. `T-CMP-04`, `T-SEC-02` and `T-SEC-07` must distinguish user-visible erasure, cryptographic
inaccessibility, independently protected erasure barriers and any narrowly retained statutory
record. No production behavior ships until counsel records the applicable interpretation, data
classes, access restrictions and expiry.

**LLM/AI API sub-processors:** Sending user financial data to OpenAI, Anthropic, Google, etc. constitutes cross-border transfer and requires a Data Processing Agreement (DPA) and disclosure in privacy notice as a data processor. A no-training default is not the same as Zero Data Retention. Enable a provider/model/feature combination only after contractual and technical evidence confirms the required retention mode. See Section 5.

---

### 2.2 CERT-In Directions (April 2022)

**Applicability:** APPLIES NOW (broad applicability to all digital service providers)

| Requirement | Detail | PenniLogic Action |
|---|---|---|
| **6-hour incident reporting** | Report specified cyber incidents (breaches, DDoS, malicious app activity, identity theft, payment system attacks) to CERT-In within 6 hours of awareness | Draft incident response runbook; designate CERT-In point of contact |
| **180-day log retention** | Retain all ICT system logs for minimum 180 days, stored **within India** | Ensure India-region log storage (AWS Mumbai / GCP Mumbai / Azure India Central); no sending logs abroad |
| **NTP synchronisation** | All systems must sync to NIC/NPL NTP servers | Infrastructure config task |
| **Point of Contact** | Designate a PoC for CERT-In communications | Appoint CISO/tech lead as PoC |

**Applicability to PenniLogic:** The CERT-In Directions apply broadly to "service providers, intermediaries, data centres, body corporates" operating in India. A fintech app serving Indian users is covered. No sectoral exemptions.

*Sources:* [Trilegal CERT-In analysis](https://trilegal.com/wp-content/uploads/2022/05/2022-CERT-In-Directions-on-Reporting-Cyber-Incidents-1.pdf); [Adayptus CERT-In guide](https://www.adayptus.com/blog/cert-in-6-hour-incident-reporting); [RingSafe guide](https://ringsafe.in/cert-in-direction-guide/)

---

### 2.3 RBI Payment Data Localization

**Applicability:** DOES NOT APPLY (PenniLogic does not process payment transactions or operate on payment rails)

The RBI Payment System Data Storage circular (2018, reinforced 2021) requires all payment system data related to payment transactions processed in India to be stored only in India. This binds payment system operators (PSOs), payment aggregators, and payment gateways.

**PenniLogic's position:** PenniLogic never touches payment rails — it reads SMS transaction notifications on-device (no raw data transmitted) or will eventually receive AA-structured records. It does not initiate, process, or settle payments. **The RBI payment data localization circular does not bind a pure-PFM app.** However, CERT-In's 180-day India log retention effectively achieves similar localization for operational logs.

*Counsel should confirm this reading if PenniLogic later integrates any payment initiation feature.*

---

## 3. India — Financial Advice Boundary

### 3.1 SEBI Investment Adviser Regulations

**Applicability:** APPLIES NOW (must stay within safe harbour through disclaimer design; SEBI IA registration needed if advice crosses the line)

#### The Legal Line

SEBI (Investment Advisers) Regulations, 2013 (last amended July 2023) define "investment advice" as advice relating to investing, purchasing, selling, or dealing in securities or investment products. Registration as a SEBI IA is mandatory for anyone providing such advice for consideration.

**Key distinction:** Generic financial education, calculators, goal projections, and cashflow analysis are NOT regulated investment advice. The line is crossed when:
1. You recommend specific securities or investment products
2. You provide advice tailored to a specific client's investment portfolio
3. You charge a fee specifically for investment advice

**PenniLogic's specific scenarios:**

| App Feature | Analysis | SEBI Registration Required? |
|---|---|---|
| "At your savings rate, this goal completes Feb 2031" | Pure mathematical projection — no specific product recommendation | **No** — educational/calculational |
| "Closing the gap needs ₹31,000/month extra savings" | Factual gap analysis — no specific product named | **No** — educational |
| "Roles at next level typically pay 25–40% more" | General market information — not investment advice | **No** |
| "Consider investing surplus in an index fund" | Generic category suggestion without specific product | **Borderline** — use with strong disclaimer |
| "Invest in XYZ Mutual Fund scheme" | Specific product recommendation | **Yes** — triggers SEBI IA |
| "Rebalance your portfolio — sell Fund A, buy Fund B" | Specific portfolio action | **Yes** — triggers SEBI IA |
| AI insight suggesting specific debt repayment order (avalanche/snowball) | Debt management, not securities — outside SEBI IA scope | **No for SEBI IA** (but monitor) |

**Safe Harbour Practices Used by Indian Fintechs:**
- Frame all output as "informational," "illustrative," and "educational"
- Never name specific securities/schemes without SEBI IA status
- Add prominent disclaimer: *"This is not investment advice. Please consult a SEBI-registered investment adviser."*
- If SEBI IA status obtained: show registration number; maintain suitability assessments; keep 5-year records; have signed client agreements
- Paytm Money, Groww, and similar apps that *do* recommend MF schemes hold SEBI IA or AMFI ARN registrations

*Sources:* [SEBI IA Regulations (July 2023 version)](https://www.sebi.gov.in/legal/regulations/jul-2023/securities-and-exchange-board-of-india-investment-advisers-regulations-2013-last-amended-on-july-4-2023-_74007.html); [lawyervikasgupta.com SEBI IA Guide](https://lawyervikasgupta.com/blog/sebi-compliance-guide-for-investment-advisors-2025-edition/); [Aarnalaw SEBI 2026 digital compliance](https://www.aarnalaw.com/insights/sebis-new-digital-compliance-rules-what-investment-advisers-must-know-in-2026)

---

### 3.2 RBI Digital Lending Guidelines (2022)

**Applicability:** DOES NOT APPLY — unless PenniLogic intermediates loans

The RBI Digital Lending Guidelines (September 2022) apply to Regulated Entities (banks, NBFCs) and their Lending Service Providers (LSPs) / Digital Lending Apps (DLAs) that facilitate credit origination, approval, disbursal, or repayment.

**PenniLogic's position:** A pure debt-management and PFM app that only advises on debt strategy (avalanche vs. snowball repayment, debt tracking, payment scheduling reminders) does NOT fall under these guidelines. There is no loan origination, no connection to a lender as an LSP, and no payment facilitation.

**Trigger for applicability:** If PenniLogic adds a "loan marketplace" or "connect to lender" feature where it sources users to NBFCs or banks, it would become an LSP and the Digital Lending Guidelines would apply immediately.

*Sources:* [RBI Digital Lending FAQ](https://www.rbi.org.in/scripts/FAQView.aspx?Id=155); [Khaitan & Co analysis](https://www.khaitanco.com/thought-leaderships/RBI-notifies-Digital-Lending-Guidelines); [The Attorneys deep-dive](https://theattorneys.co/rbis-digital-lending-guidelines-a-legal-deep-dive-for-indias-fintech-ecosystem/)

---

### 3.3 Credit Bureau Data (CIBIL/Experian/Equifax/CRIF)

**Applicability:** APPLIES IF FEATURE ADDED — requires CICRA partnership

The Credit Information Companies (Regulation) Act, 2005 (CICRA) governs credit bureaus (TransUnion CIBIL, Experian India, Equifax India, CRIF High Mark). To access and display a user's credit score in-app, PenniLogic must:

1. **Enter into a commercial API/data-sharing agreement** with one or more credit bureaus
2. **Obtain user's explicit, verifiable consent** for each credit pull (OTP/e-signature)
3. **Comply with CICRA data use restrictions** — data can only be used for the declared purpose; cannot be sold or used for marketing

**The "Specified User" route:** Under CICRA, "specified users" (entities that can access credit information) include banks, NBFCs, insurance companies, credit card companies, and *any entity notified by RBI*. Pure fintechs without an NBFC or bank licence typically access credit scores by:
- Partnering with a CIBIL/Experian-licensed entity, OR
- Directly applying for CICRA "member" status (credit institutions) or "specified user" status via RBI notification — a commercial/regulatory process

**How CRED/Paisabazaar do it:** Both have formal agreements with credit bureaus under CICRA. Paisabazaar is a subsidiary of PB Fintech (a regulated financial services group). CRED operates as a specified-user-type arrangement via commercial agreements. The "free credit score" feature requires these commercial agreements. UNVERIFIED — confirm the exact regulatory route each uses with counsel.

**Cost:** Credit bureau API access involves per-pull fees (typically ₹15–₹50 per hard pull; lower for soft pulls). Negotiated commercially.

---

## 4. Global Expansion

### 4.1 European Union

**Applicability:** APPLIES ONLY IF EU users onboarded

#### GDPR (Financial Data)
- Financial transaction data is personal data. Sensitive financial profile data may constitute "special category" data — **counsel needed to determine exact categorisation**.
- Lawful basis for processing: **Consent** (Art. 6(1)(a)) or **Legitimate Interests** (Art. 6(1)(f)) — for a consumer app, explicit consent is safer.
- DPO appointment: Required if processing "large scale" sensitive data — likely triggered as PenniLogic scales.
- Privacy notice: Must be comprehensive, plain-language, provided at point of data collection.
- Data subject rights: Access, rectification, erasure, portability, objection — must be fulfilled within 1 month.
- Cross-border transfers: Standard Contractual Clauses (SCCs) or adequacy decisions for transfers out of EU/EEA.
- Breach notification: 72 hours to supervisory authority; without undue delay to affected individuals.
- **Penalties:** Up to €20M or 4% global annual turnover, whichever is higher.

#### PSD2 Open Banking — AISP Route
- To access EU users' bank account data via open banking, an entity needs AISP (Account Information Service Provider) authorization.
- **PenniLogic does not need its own AISP licence to start.** It can "ride" a licensed aggregator such as **Tink** (Visa-owned) or **TrueLayer** by integrating their API. The aggregator holds the AISP licence; PenniLogic is a downstream client.
- The aggregator (Tink/TrueLayer) manages regulatory bank connections; PenniLogic builds the UX on top.
- **Over time**, at scale, obtaining own AISP registration from an EU National Competent Authority (NCA) may become strategically worthwhile.

*Sources:* [OpenBankingTracker EU API Guide](https://openbankingtracker.com/open-banking-apis-europe); [dev.to Open Banking comparison 2026](https://dev.to/johnfrandsen/comparing-european-open-banking-api-providers-in-2026-plaid-truelayer-tink-gocardless-125c)

#### PSD3 / PSR / FiDA Status
- **PSD3** (revision of PSD2) and **PSR** (Payment Services Regulation) — proposed 2023; as of mid-2026 progressing through EU legislative process but not yet in force. **UNVERIFIED current status — check EUR-Lex.**
- **FiDA** (Financial Data Access regulation) — proposed 2023; would extend open finance beyond payments to investments, insurance, pensions. Still in legislative negotiation as of late 2025. **UNVERIFIED current status.**
- For planning purposes: assume PSD2/GDPR govern EU operations for the next 12–18 months minimum.

---

### 4.2 United Kingdom

**Applicability:** APPLIES ONLY IF UK users onboarded

- **FCA AISP Registration:** To offer account information services in the UK (access users' bank data via UK Open Banking), PenniLogic needs FCA authorisation as an AISP or to operate as an **agent of an FCA-authorised AISP** (e.g., TrueLayer UK, Yapily). The agent model is the practical MVP path.
- **UK GDPR:** Functionally equivalent to EU GDPR post-Brexit. Same obligations apply. ICO is the supervisory authority.
- **UK Open Banking:** Governed by the FCA and Payment Systems Regulator (PSR). The OBIE (Open Banking Implementation Entity) has transitioned oversight to a new entity in 2024. Functionally similar to EU PSD2.

---

### 4.3 United States

**Applicability:** APPLIES ONLY IF US users onboarded

#### CFPB Section 1033 — Open Banking Rule Status (September 2026)
The CFPB finalized the Personal Financial Data Rights rule implementing Section 1033 in **October 2024**. However:
- Industry groups (Bank Policy Institute, Kentucky Bankers Association) filed litigation challenging the rule.
- May 2025: CFPB (new administration) sided with plaintiffs, seeking to vacate the rule.
- July 29, 2025: Federal court (E.D. Kentucky) granted a stay.
- October/November 2025: Court issued **preliminary injunction — rule is enjoined, not enforceable.**
- August 2025: CFPB issued Advance Notice of Proposed Rulemaking to revise the rule from scratch.
- **Status as of September 2026: Section 1033 rule exists on paper but is enjoined. No compliance deadlines are operative. The CFPB is re-writing the rule.** Sixth Circuit appeal is paused pending new rulemaking.
- **For PenniLogic:** No binding federal open banking requirement in the US right now. Access to user financial data in the US relies on screen-scraping aggregators (Plaid, MX, Finicity/Mastercard) or direct bank partnerships. Plaid offers its own user consent framework.

*Sources:* [OpenBankingTracker Section 1033](https://openbankingtracker.com/guides/section-1033-status); [JDSupra Section 1033 injunction](https://www.jdsupra.com/legalnews/section-1033-compliance-date-open-8267590/); [ConsumerFinanceMonitor 2026](https://www.consumerfinancemonitor.com/2026/06/26/open-banking-regulation-in-2026-federal-regulation-resurfaces-as-states-bring-data-sharing-into-focus/)

#### GLBA (Gramm-Leach-Bliley Act)
- GLBA applies to "financial institutions" (broadly defined) that collect nonpublic personal financial information of US consumers.
- A PFM app handling US users' financial data is likely a GLBA-covered financial institution under the FTC's Safeguards Rule.
- **FTC Safeguards Rule (2023 updated):** Requires a written information security programme, designated security officer, risk assessment, annual reporting to board.
- **Privacy notices:** GLBA requires annual privacy notices and opt-out rights.

#### State Privacy Laws
- **CCPA/CPRA (California):** Applies to businesses meeting thresholds (gross revenue >$25M, or data of >100,000 consumers/households). Likely applies once US operations scale. Rights: access, deletion, opt-out of sale, correction, portability.
- **Other states:** Virginia (VCDPA), Colorado (CPA), Connecticut (CTDPA), Texas (TDPSA), and 15+ other states have enacted comprehensive privacy laws as of 2026. These are broadly similar to CCPA in consumer rights framework.
- **Data Broker registrations:** Some states (California, Vermont, Texas) require registration if PenniLogic is deemed a "data broker." Unlikely for a first-party PFM app, but worth monitoring.

---

### 4.4 UAE

**Applicability:** APPLIES ONLY IF UAE users onboarded

- **Federal PDPL** (Decree-Law No. 45 of 2021): Federal data protection law, broadly applicable.
- **DIFC Data Protection Law** (No. 5 of 2020, amended 2025): Applies within DIFC free zone; GDPR-modeled; Amendment Law 1 of 2025 adds individual right to sue, broader extraterritorial reach, AI-specific privacy considerations.
- **ADGM Data Protection Regulations (2021, updated 2025):** Applies within ADGM free zone; penalties up to $28M.
- **Fintech licensing:** DFSA (DIFC) or FSRA (ADGM) regulatory sandboxes available for new entrants. Strongly recommended before full market entry.
- **Open banking:** The UAE Central Bank has published open banking policy frameworks; full interoperable open banking is emerging but not yet mature.

*Sources:* [RecordingLaw UAE PDPL guide](https://www.recordinglaw.com/world-laws/world-data-privacy-laws/uae-data-privacy-laws/); [KPMG DIFC 2025](https://kpmg.com/ae/en/insights/ai-and-technology/strengthening-data-privacy-and-protection-in-difc.html); [WebVerseArena DIFC vs ADGM](https://www.webversearena.com/blog/uae-fintech-app-difc-adgm-2026)

---

### 4.5 Singapore

**Applicability:** APPLIES ONLY IF Singapore users onboarded

- **PDPA (Personal Data Protection Act, amended 2023/24):** Governs personal data processing; consent-based; mandatory breach notification (3 days for significant breaches).
- **MAS Technology Risk Management Notices:** Detailed cybersecurity and system resiliency requirements for MAS-regulated entities. PenniLogic would need MAS licensing if providing regulated financial services in Singapore.
- **Open banking:** MAS promotes open banking via the API Exchange (APIX) ecosystem; not mandated like PSD2 but available.
- **MAS RegTech/FinTech Fast Lane:** Available for pilot/sandbox approvals.
- For a PFM app serving Singapore consumers without regulated financial services, the PDPA is the primary obligation.

---

## 5. AI-Specific Regulation

### 5.1 EU AI Act — High-Risk Classification

**Applicability:** APPLIES ONLY IF EU users onboarded AND AI systems assess creditworthiness

The EU AI Act entered into force August 2024, with phased obligations:
- **February 2, 2025:** Prohibited practices and AI literacy rules in effect.
- **August 2, 2025:** General-purpose AI (GPAI) rules in effect.
- **August 2, 2026 ← NOW:** **Main obligations for Annex III high-risk AI systems apply.**

**Annex III, Point 5(b):** AI systems used for creditworthiness assessment or credit scoring are **classified as high-risk.**

**Does PenniLogic's AI fall in scope?**

| PenniLogic AI Feature | High-Risk under Annex III? |
|---|---|
| Goal-timeline projection ("savings rate → goal date") | Likely **No** — mathematical projection, not creditworthiness assessment |
| Cashflow forecasting | Likely **No** — forward projection, not scoring |
| Debt repayment strategy suggestion (avalanche/snowball) | Likely **No** — debt management, not credit scoring |
| Budget vs. actual variance insight | Likely **No** |
| "Your financial health score" or similar score/rating | **Potentially Yes** — if framed as creditworthiness-adjacent rating, may trigger Annex III |
| Loan eligibility estimation | **Yes** — clearly a creditworthiness assessment |

**If Annex III applies, obligations include:**
- Risk management system (Art. 9)
- Data governance and quality controls (Art. 10)
- Technical documentation (Art. 11)
- Detailed logging/record-keeping (Art. 12)
- Transparency to deployers (Art. 13)
- Human oversight mechanisms (Art. 14)
- Accuracy, robustness, cybersecurity requirements (Art. 15)
- Conformity assessment and EU database registration
- Fundamental Rights Impact Assessment (FRIA) for deployers

**Penalties:** Up to €15M or 3% of global annual turnover (high-risk violations); up to €35M or 7% (prohibited AI violations).

*Note:* The Digital Omnibus provision may have deferred some standalone Annex III obligations to December 2, 2027 — UNVERIFIED as of September 2026. Counsel should confirm current applicability.

*Sources:* [FinancialRegulations.eu EU AI Act guide](https://financialregulations.eu/blog/eu-ai-act-financial-services-guide); [BM Consulting Annex III obligations](https://bm.consulting/en/insights/ai-act-high-risk-system-obligations/); [ScanLex Annex III financial services](https://www.scanlex.eu/articles/eu-ai-act-annex-iii-financial-services/); [compliance-kit.eu credit scoring AI Act](https://compliance-kit.eu/en/knowledge/ai-act-credit-scoring-annex-iii-5)

---

### 5.2 India AI Governance (2025–2026)

**Applicability:** APPLIES NOW (advisory/voluntary; no binding AI statute yet)

**India AI Governance Guidelines (November 2025 / February 2026):** MeitY released AI Governance Guidelines under the IndiaAI Mission. Key characteristics:
- **Voluntary and principle-based** — not a binding statute. Relies on DPDP Act 2023 and IT Act 2000 for enforcement hooks.
- Seven foundational principles: Trust, People First, Innovation Over Restraint, Fairness & Equity, Accountability, Understandable by Design, Safety & Sustainability.
- **Three governance bodies created:** AI Governance Group (AIGG), Technology & Policy Expert Committee (TPEC), AI Safety Institute (AISI).
- **No comprehensive AI-specific binding legislation as of September 2026.**

**RBI FREE-AI Framework (August 2025):** "Framework for Responsible and Ethical Enablement of Artificial Intelligence" — sector-specific guidance for financial services AI. Principles-based, applies to RBI-regulated entities. Not directly binding on PenniLogic (non-regulated), but signals direction.

*Sources:* [India AI Governance Guidelines PDF (PIB)](https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc2026215790801.pdf); [IndiaAI article](https://indiaai.gov.in/article/india-ai-governance-guidelines-empowering-ethical-and-responsible-ai); [Regulations.AI India](https://regulations.ai/regulations/india); [EY India AI governance](https://www.ey.com/en_in/insights/ai/ai-governance-guidelines-a-bet-on-innovation)

**Practical obligations for PenniLogic (India):**
1. **AI disclosure:** Inform users when AI/automated systems are generating insights. Phrase: *"This insight is generated by an AI model and is for informational purposes only."*
2. **Human oversight:** Provide mechanisms for users to contest or override AI-generated categorisations.
3. **Explainability:** Be able to explain in plain language how AI recommendations are generated.
4. **Bias monitoring:** Establish processes to detect and correct demographic/income bias in AI outputs.

---

### 5.3 Sending Financial Data to Third-Party LLM Providers

**Applicability:** APPLIES NOW — critical design decision

When user financial data (transaction records, salary, debt details) is sent to OpenAI / Anthropic / Google for AI inference, it constitutes:
- **Under DPDP:** Transfer of personal data to a data processor (the LLM provider). Requires a Data Processing Agreement.
- **Under GDPR:** Same — Art. 28 DPA required; the LLM provider must be a data processor with adequate safeguards. If data leaves the EU/EEA, SCCs required.

**Required Actions:**

| Action | Requirement |
|---|---|
| **Prove the required retention mode per provider, model and feature** | ZDR is approval-, endpoint-, model- and feature-specific. Record eligibility evidence and expiry; no-training defaults alone are insufficient. |
| **Sign Data Processing Agreements (DPAs)** | With each LLM provider used. OpenAI, Anthropic, Google Cloud all offer DPAs for API customers. |
| **Sub-processor disclosure** | Name LLM providers in privacy policy as sub-processors/data processors. |
| **Consent language** | Privacy notice must disclose: "Your financial data may be processed by AI systems operated by [Provider] to generate personalised insights. [Provider] does not use your data to train its models under our enterprise agreement." |
| **Data minimisation** | Never send raw transactions. Send only abstracted/anonymised inputs; structured summaries preferred. Strip PII where possible before sending to LLM. |
| **Cross-border transfer compliance** | India: Monitor DPBI negative list; EU: SCCs with LLM providers needed. |

**Potential LLM providers for financial data:** OpenAI API, Anthropic API and Google Cloud Vertex AI may qualify only for the exact approved model and feature set under a signed DPA and verified retention configuration. Consumer-facing products **must never** receive user financial data. Provider onboarding remains default-deny when evidence is absent, expired or excludes a used feature such as caching, files, batch processing or abuse monitoring: under ADR-022 §2.2 a provider is enabled only when its code-managed allowlist entry carries the retention-mode and region evidence owned by `T-AI-07` (`retention_evidence_ref`) and the signed DPA and sub-processor disclosure owned by `T-CMP-04` (`processor_agreement_ref`).

---

### 5.4 AI Disclosure and Financial Advice Disclaimers

**Mandatory disclaimer framing for PenniLogic AI features (India):**

```
This analysis is generated by an AI model and is provided for informational and
educational purposes only. It does not constitute investment advice, financial planning
advice, or any other regulated advisory service. PenniLogic is not registered as a SEBI
Investment Adviser. Please consult a qualified financial professional before making
investment or financial decisions. Past trends are not indicative of future results.
```

---

## 6. Certifications

### 6.1 SOC 2 Type II

**Applicability:** APPLIES AT SCALE (customer/enterprise trust; required for B2B partnerships)

- **What it is:** American Institute of CPAs (AICPA) attestation covering Security, Availability, Processing Integrity, Confidentiality, Privacy Trust Service Criteria.
- **Timeline:** 3–6 months observation period (minimum) + readiness period. Realistically 6–9 months end-to-end for a startup.
- **Cost (2025–2026 estimates):**

| Platform | Annual Tool Cost | Audit Cost (separate) | Notes |
|---|---|---|---|
| Vanta | $7,500–$9,500/yr | $5,000–$15,000 | Strong UX, 100+ integrations |
| Drata | $7,000–$9,649/yr | $5,000–$15,000 | Deep integrations, risk mgmt |
| Sprinto | $6,000–$25,000/yr | $5,000–$15,000 | Budget-friendly for small SaaS |

- **All-in first-year cost for a startup (<50 employees): $10,000–$25,000** (tool + audit).
- **Recommendation:** Start Vanta/Sprinto setup at Series A or when first enterprise customer requests SOC 2. Begin 6 months before the report is needed.

*Sources:* [soc2auditors.org pricing bands](https://soc2auditors.org/insights/soc-2-software-pricing-comparison/); [SOC2Certification.com comparison](https://www.soc2certification.com/blog/soc2-automation-platforms-review); [ComplianceStronghold 2026](https://compliancestronghold.com/best-soc2-for-startups/)

---

### 6.2 ISO 27001:2022

**Applicability:** APPLIES AT SCALE (B2B, enterprise, financial institution partnerships; EU/global credibility)

- Information Security Management System (ISMS) standard.
- The 2022 revision adds 11 new controls including threat intelligence, cloud security, data masking.
- **Timeline:** 9–18 months for a startup. Includes gap analysis, ISMS build, internal audit, Stage 1 + Stage 2 external audit.
- **Cost:** ₹8–20 lakh (India-based certification bodies like Bureau Veritas, DNV, TÜV); $15,000–$40,000+ internationally.
- **Synergy:** SOC 2 and ISO 27001 share significant control overlap (~65%). Pursuing both concurrently with an automation platform (Vanta/Sprinto) reduces duplication.

---

### 6.3 ISO 27701 (Privacy Extension)

**Applicability:** APPLIES AT SCALE (strong signal for DPDP/GDPR compliance maturity)

- Privacy Information Management System (PIMS) — extension to ISO 27001.
- Provides a framework aligned with GDPR and DPDP obligations.
- Requires ISO 27001 certification first.
- **Timeline:** Add 3–6 months to ISO 27001 project.
- **Cost:** Additional $5,000–$15,000 on top of ISO 27001 audit cost.

---

### 6.4 PCI-DSS 4.0

**Applicability:** DOES NOT APPLY (likely) — unless PenniLogic directly handles card PANs

**Analysis:**
- PCI-DSS applies to entities that store, process, or transmit cardholder data (PANs, CVVs, magnetic stripe data).
- PenniLogic uses:
  - **In-app purchases:** Google Play Billing / Apple IAP — card data handled entirely by the platform. **PenniLogic never sees card PANs. PCI-DSS does not apply.**
  - **Subscription payments:** Via Razorpay or Stripe — both are PCI-DSS certified. If PenniLogic uses their hosted payment pages / SDKs and never touches the raw card data, PenniLogic may qualify for **SAQ A** (the most minimal SAQ — merchant outsources all payment functions).
  - **Bank account data (read-only):** Account numbers from AA or SMS. Bank account numbers are NOT card data under PCI-DSS scope. **Not in scope.**

**Conclusion:** If PenniLogic strictly uses Google Play Billing + Stripe/Razorpay hosted pages with no server-side card data handling, **PCI-DSS SAQ A (or SAQ A-EP) is the maximum exposure**, which requires ~22 controls (mostly confirming outsourced card processing). Full PCI-DSS Level 1/2/3 audits are NOT required.

**Action:** Complete the SAQ A self-assessment questionnaire before processing any subscription payments. Confirm no card data ever touches PenniLogic servers.

---

## 7. MVP India Launch Checklist

*Focus: Launch to Indian users with SMS on-device parsing, no AA integration, no credit score feature.*

### Immediate (before any user onboarding)

- [ ] **Legal entity:** Incorporate as Private Limited company (required for app store accounts, contracts)
- [ ] **Privacy Policy:** Draft DPDP-compliant privacy policy; disclose data collected, purpose, processors (LLM providers), user rights, contact for requests
- [ ] **Terms of Service:** Include financial advice disclaimer; not investment advice; for educational purposes only
- [ ] **Consent UI:** Implement granular, purpose-specific consent at onboarding for each data category (SMS access, salary input, debt data); record consent with timestamp
- [ ] **SEBI disclaimer:** All AI insights must display: "For informational purposes only. Not investment advice. Not a SEBI-registered Investment Adviser."
- [ ] **On-device SMS parsing confirmation:** Ensure SMS raw data never leaves device; only structured records transmitted. Document this architecture in privacy policy.
- [ ] **LLM DPAs and retention evidence:** Sign a DPA and verify the exact provider/model/feature retention mode before sending user data; record exclusions and evidence expiry.
- [ ] **LLM data minimisation:** Strip or abstract PII before sending to LLM; never send account numbers, names, phone numbers to external AI APIs
- [ ] **CERT-In compliance:**
  - [ ] Designate CERT-In PoC
  - [ ] Configure India-region log storage (AWS Mumbai / GCP Mumbai)
  - [ ] 180-day log retention policy
  - [ ] NTP sync to NIC/NPL
  - [ ] Incident response runbook with 6-hour CERT-In reporting trigger
- [ ] **Data retention and erasure opinion:** Reconcile DPDP Rule 6, CERT-In logs, storage limitation and crypto-shredding; publish machine-readable periods and prove erased subjects cannot reappear after restore.
- [ ] **Age restriction:** Restrict to 18+ users; add age gate at onboarding
- [ ] **Security basics:** HTTPS everywhere; encrypted storage for financial data at rest; no plaintext secrets in code

### Before First Real-Money Feature (e.g., premium subscription)
- [ ] Integrate Razorpay or Stripe with hosted payment page (no card data on PenniLogic servers)
- [ ] Complete PCI-DSS SAQ A self-assessment
- [ ] Razorpay/Stripe DPA signed

### Before Scaling (>10,000 users)
- [ ] Reassess whether a registered Consent Manager integration is commercially useful or legally required; do not infer a requirement from the registration-regime commencement date.
- [ ] Appoint a Data Protection Officer (or designated privacy lead)
- [ ] Review Significant Data Fiduciary criteria when announced by DPBI

---

## 8. Before Global Launch Checklist

*For expansion into EU/UK/US/UAE/Singapore.*

### EU / UK
- [ ] GDPR-compliant privacy policy (separate from India policy)
- [ ] Cookie consent (Cookiebot / OneTrust)
- [ ] Data Subject Request (DSR) portal
- [ ] DPA with all processors (cloud providers, LLM providers) updated for EU SCCs
- [ ] DPO appointment (required once processing special category data at scale)
- [ ] AISP partner selection (Tink or TrueLayer) for EU/UK open banking
- [ ] UK: FCA AISP agent agreement with TrueLayer/Yapily
- [ ] EU: Confirm GDPR supervisory authority (where is EU entity/main establishment?)
- [ ] Monitor PSD3/PSR/FiDA legislative progress
- [ ] EU AI Act compliance assessment for any AI features (creditworthiness scope?)

### US
- [ ] GLBA Safeguards Rule compliance: Written ISP, security officer, risk assessment
- [ ] GLBA annual privacy notices
- [ ] CCPA/CPRA: Privacy policy update; consumer rights portal; opt-out of sale mechanism
- [ ] Multi-state privacy law review (Virginia, Colorado, Texas, Connecticut +)
- [ ] Plaid / MX / Finicity agreement for US bank data access
- [ ] US legal entity (Delaware C-Corp standard)
- [ ] Monitor CFPB Section 1033 rulemaking developments

### UAE / Singapore
- [ ] UAE: Federal PDPL privacy policy update; DIFC/ADGM free zone selection if applicable
- [ ] UAE: DFSA/FSRA regulatory sandbox application
- [ ] Singapore: PDPA compliance; MAS licensing assessment; APIX open banking API evaluation

### Certifications
- [ ] SOC 2 Type II: Start 6 months before first enterprise customer or B2B partnership
- [ ] ISO 27001:2022: Target before Series A fundraise or first institutional partnership
- [ ] ISO 27701: Layer on top of ISO 27001 project

---

## 9. Risk Table

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Incorrect DPDP commencement, retention or Consent Manager interpretation** | HIGH | HIGH | Require a dated counsel opinion and versioned jurisdiction profile; fail closed when it is absent or expired |
| 2 | **SEBI IA regulatory action for AI features crossing into investment advice** | MEDIUM | HIGH | Strictly limit AI to projections/education; no specific product recommendations; strong disclaimers; seek legal opinion on specific features |
| 3 | **AA data access blocked — no FIU status** | HIGH | MEDIUM | Plan AA access via regulated FIU partner; begin partner conversations now; treat SMS on-device as long-term primary for PFM |
| 4 | **CERT-In 6-hour reporting missed in a breach incident** | MEDIUM | HIGH | Implement incident response runbook before launch; SIEM/alerting in place; practice drill |
| 5 | **LLM provider data breach / misuse of user financial data** | LOW–MEDIUM | HIGH | Require model- and feature-specific retention evidence, DPA, data minimisation, contractual audit rights and default-deny routing |
| 6 | **EU AI Act Annex III triggered by "financial health score" feature** | MEDIUM (if EU launched) | HIGH | Pre-classify all AI features against Annex III; avoid creditworthiness-adjacent scores; obtain EU AI Act legal opinion before EU launch |
| 7 | **CICRA violation — accessing credit data without proper agreement** | LOW (not built yet) | HIGH | No credit score feature at MVP; ensure formal CIBIL/Experian agreement before building |
| 8 | **US GLBA non-compliance if US users onboarded without preparation** | MEDIUM | HIGH | No US launch without GLBA ISP in place; appoint security officer; review FTC Safeguards Rule checklist |
| 9 | **Google Play SMS permission revoked / policy change** | LOW | HIGH | Maintain on-device processing architecture; document compliance with SMS policy exception; prepare fallback (AA, manual import) |
| 10 | **RBI Digital Lending scope creep if debt-to-lender referral added** | MEDIUM (future feature) | HIGH | Any referral or lender-connect feature triggers LSP status; obtain legal opinion before building; design for compliance from day 1 |
| 11 | **Cross-border data transfer to US LLM providers violates GDPR SCCs** | MEDIUM (EU users) | HIGH | SCCs with OpenAI/Anthropic/Google Cloud before EU launch; use EU data residency options where available |
| 12 | **Tax / financial advice liability from AI projections** | LOW | MEDIUM | Disclaimers on all AI outputs; professional consultation prompts; no guarantees language |

---

## 10. Sources Table

| # | Source | URL | Section Used |
|---|---|---|---|
| 1 | Sahamati — FIU page | https://sahamati.org.in/fiu/ | §1.2 |
| 2 | Sahamati — TSP page | https://sahamati.org.in/technology-service-provider-tsp/ | §1.2 |
| 3 | DFS Account Aggregator Framework | https://financialservices.gov.in/account-aggregator-framework | §1.1 |
| 4 | Setu Docs — AA FI Data Types | https://docs.setu.co/data/account-aggregator/fi-data-types | §1.3 |
| 5 | ReBIT AA API Schemas | https://api.rebit.org.in/schema | §1.3 |
| 6 | GitHub — Sahamati AA Standards | https://github.com/Sahamati/account-aggregator-standards/ | §1.3 |
| 7 | PIB — DPDP Rules 2025 Notification | https://static.pib.gov.in/WriteReadData/specificdocs/documents/2025/nov/doc20251117695301.pdf | §2.1 |
| 8 | NitiBharat DPDP Rules Guide | https://nitibharat.com/dpdp-rules-2025.html | §2.1 |
| 9 | Taxmann DPDP Analysis | https://www.taxmann.com/post/blog/analysis-indias-dpdp-act-and-rules/ | §2.1 |
| 10 | ConsentOS DPDP Timeline | https://consentos.in/learn/dpdp-compliance-timeline/ | §2.1 |
| 11 | HarunRaaj DPDP Consent Manager Nov 2026 | https://www.harunraaj.com/blog/2026-08-15-dpdp-consent-manager-november-2026 | §2.1 |
| 12 | Trilegal CERT-In 2022 Analysis | https://trilegal.com/wp-content/uploads/2022/05/2022-CERT-In-Directions-on-Reporting-Cyber-Incidents-1.pdf | §2.2 |
| 13 | Adayptus CERT-In Guide | https://www.adayptus.com/blog/cert-in-6-hour-incident-reporting | §2.2 |
| 14 | SEBI IA Regulations (July 2023) | https://www.sebi.gov.in/legal/regulations/jul-2023/securities-and-exchange-board-of-india-investment-advisers-regulations-2013-last-amended-on-july-4-2023-_74007.html | §3.1 |
| 15 | LawyerVikasGupta SEBI IA 2025 | https://lawyervikasgupta.com/blog/sebi-compliance-guide-for-investment-advisors-2025-edition/ | §3.1 |
| 16 | AarnaLaw SEBI Digital 2026 | https://www.aarnalaw.com/insights/sebis-new-digital-compliance-rules-what-investment-advisers-must-know-in-2026 | §3.1 |
| 17 | RBI Digital Lending FAQ | https://www.rbi.org.in/scripts/FAQView.aspx?Id=155 | §3.2 |
| 18 | The Attorneys RBI Digital Lending | https://theattorneys.co/rbis-digital-lending-guidelines-a-legal-deep-dive-for-indias-fintech-ecosystem/ | §3.2 |
| 19 | OpenBankingTracker EU APIs | https://openbankingtracker.com/open-banking-apis-europe | §4.1 |
| 20 | dev.to Open Banking 2026 | https://dev.to/johnfrandsen/comparing-european-open-banking-api-providers-in-2026-plaid-truelayer-tink-gocardless-125c | §4.1 |
| 21 | OpenBankingTracker Section 1033 | https://openbankingtracker.com/guides/section-1033-status | §4.3 |
| 22 | JDSupra Section 1033 Injunction | https://www.jdsupra.com/legalnews/section-1033-compliance-date-open-8267590/ | §4.3 |
| 23 | ConsumerFinanceMonitor Open Banking 2026 | https://www.consumerfinancemonitor.com/2026/06/26/open-banking-regulation-in-2026-federal-regulation-resurfaces-as-states-bring-data-sharing-into-focus/ | §4.3 |
| 24 | RecordingLaw UAE PDPL | https://www.recordinglaw.com/world-laws/world-data-privacy-laws/uae-data-privacy-laws/ | §4.4 |
| 25 | KPMG DIFC 2025 | https://kpmg.com/ae/en/insights/ai-and-technology/strengthening-data-privacy-and-protection-in-difc.html | §4.4 |
| 26 | FinancialRegulations.eu EU AI Act | https://financialregulations.eu/blog/eu-ai-act-financial-services-guide | §5.1 |
| 27 | BM Consulting Annex III | https://bm.consulting/en/insights/ai-act-high-risk-system-obligations/ | §5.1 |
| 28 | ScanLex Annex III Financial | https://www.scanlex.eu/articles/eu-ai-act-annex-iii-financial-services/ | §5.1 |
| 29 | compliance-kit.eu credit scoring AI Act | https://compliance-kit.eu/en/knowledge/ai-act-credit-scoring-annex-iii-5 | §5.1 |
| 30 | PIB India AI Governance Guidelines | https://static.pib.gov.in/WriteReadData/specificdocs/documents/2026/feb/doc2026215790801.pdf | §5.2 |
| 31 | IndiaAI.gov.in AI Governance article | https://indiaai.gov.in/article/india-ai-governance-guidelines-empowering-ethical-and-responsible-ai | §5.2 |
| 32 | soc2auditors.org pricing | https://soc2auditors.org/insights/soc-2-software-pricing-comparison/ | §6.1 |
| 33 | SOC2Certification.com comparison | https://www.soc2certification.com/blog/soc2-automation-platforms-review | §6.1 |
| 34 | CyberSigma AA overview | https://cybersigmacs.com/knowledge-center/account-aggregator/ | §1.3 |

---

## Notes on UNVERIFIED Items

- **AA data pull costs:** Not publicly listed; cited as "negotiated commercially." UNVERIFIED — confirm with Setu, Finvu, OneMoney directly.
- **CRED/Paisabazaar exact CICRA route:** Described based on industry knowledge; exact regulatory filings not verified. UNVERIFIED — confirm with counsel.
- **PSD3/PSR/FiDA current legislative status:** Status as of "late 2025 progressing" — UNVERIFIED for September 2026. Check EUR-Lex.
- **EU AI Act Digital Omnibus deferral of Annex III to Dec 2, 2027:** Mentioned in one source; not independently verified. UNVERIFIED — counsel must confirm.
- **RBI FREE-AI (August 2025):** Referenced in secondary source; original RBI circular not directly fetched. UNVERIFIED — check RBI notifications.
- **DPBI Significant Data Fiduciary thresholds:** Rules notified but specific SDF criteria/thresholds were not published in fetched sources. UNVERIFIED — check Rules text directly.

---

*Document prepared: September 2026. Research by AI subagent. All findings require qualified legal counsel review before compliance decisions. Regulatory positions change — verify all primary sources before acting.*
```

---

## Summary Confirmation

**Research is complete.** Here is a brief summary of key findings:

1. **AA / FIU (Critical):** A non-regulated fintech **cannot directly become an FIU** — RBI Master Directive requires FSR (RBI/SEBI/IRDAI/PFRDA) registration. PenniLogic's paths: (a) partner with a regulated FIU entity, (b) use TSPs to build tech for a regulated partner, or (c) obtain SEBI IA registration (strategically clean). For MVP, on-device SMS parsing sidesteps this entirely.

2. **DPDP:** Rules were notified with phased commencement. The Consent Manager regime does not itself require every Data Fiduciary to integrate. Counsel must settle PenniLogic's applicable dates, Rule 6 retention and erasure treatment before onboarding.

3. **CERT-In:** Fully applicable. 6-hour incident reporting + 180-day India log retention mandatory now.

4. **SEBI IA:** PenniLogic's projected-savings and gap-analysis features are safe. Strong disclaimers required. Never recommend specific securities without SEBI IA registration.

5. **RBI Digital Lending:** Does NOT apply to a pure PFM/debt-advice app. Triggered only if loan intermediation is added.

6. **CFPB Section 1033:** Enjoined by court, unenforceable as of September 2026, under active rewrite.

7. **EU AI Act:** Annex III high-risk obligations active August 2, 2026. Budget/goal projection likely outside scope; any creditworthiness-scoring feature requires Annex III compliance.

8. **India AI Governance:** Advisory/voluntary as of September 2026. No binding AI statute yet.

9. **Certifications:** PCI-DSS likely limited to SAQ A; SOC 2 + ISO 27001 all-in ~$10–25K for first year startup.
