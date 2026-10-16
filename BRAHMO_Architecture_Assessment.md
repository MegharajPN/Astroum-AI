# BRAHMO Clinical AI
## Architecture Assessment — Merged Candidate Pack
**Principal Lead / Staff Engineer · Same assessment · Written only · v1.0 · October 2026**

### 00 · Instructions and purpose
Produce one complete architecture and doctor-readiness plan for BRAHMO Clinical AI in India. Improve our current approach where it is weak, retain it where it is right, and add the important considerations it omits. We are assessing your decisions and judgment, not agreement with our design or the polish of AI-generated prose.

This document consolidates all four candidate inputs: instructions (00), architecture (01), product context (02), and the supplied current build plan (03). Read it fully. No codebase, setup, prior candidate submission, private medical database, coding exercise, presentation or live defense is required.

| Assessment condition | Requirement |
|---|---|
| Time | One sitting, up to **four hours**, including reading, research and writing. Record the opening and submission times. |
| AI | Expected and encouraged. Import this complete file into your AI tool. You remain responsible for the submitted decisions and factual claims. |
| Submission | **One clean final file**, Markdown preferred; searchable PDF or DOCX accepted. Use sections S1–S9. Include your name and submission date. |
| Length | Maximum **15 pages of substantive content**, including diagrams, tables and references. Use normal readable formatting. For Markdown, use its standard readable A4 rendering. Only the first 15 pages are graded. |
| Build context | Implementation will be AI-assisted and fast. BRAHMO manages delivery scheduling and staffing; this is not a scheduling assessment. |
| Confidentiality | Do not publish or share the supplied material, another candidate’s work, or your submission. Any NDA and IP terms are those separately agreed with BRAHMO. Do not include real patient data, employer code or confidential third-party material. |

### What is fixed; what is open
The **twelve laws and fences in 01 §2 are fixed assessment requirements**. They are product rules, not a claim that Indian law is identical to this list. Everything else—including the working architecture, source choices, technology, contracts at the component boundary, and build-stage design—is open to a reasoned retain/change/remove/add decision. Do not silently breach a fixed law or fence.

A well-defended existing choice can earn full credit. A well-defended replacement can also earn full credit. Neither novelty nor conformity earns points on its own. Make your proposed final design consistent where current statements differ.

### What not to submit
Do not include a delivery timeline, weekly build plan, alternative duration, engineer-day allocation, team-size estimate, hiring plan, build-cost budget or defect-fixing schedule. Undated dependencies and data/licensing considerations are welcome. **QA operating cadence, response targets, source/legal effective dates and the assessment timestamps are not prohibited delivery schedules.**

The supplied materials estimate the current plan at **30–40% of the desired all-India end state**. Treat that as BRAHMO’s planning estimate, not a measured completeness score. Your task is to expose and close the decision gaps, not to certify that percentage.

<!-- PAGE BREAK -->

## 00 · Your single final output
Title the file **“BRAHMO Clinical AI — Final Architecture and Doctor-Readiness Plan.”** Use exactly these nine sections. Integrate supporting diagrams, tables, sources and examples into the same file; do not return a folder of alternatives or raw AI conversations.

### S1 · Final Architecture
Give your complete end-state architecture, improving on both 01 and 03. Include **one diagram** and the end-to-end doctor path: input, patient context, evidence/drug retrieval, checks, clarification, review, approval, saved/exported output and audit. Identify component responsibilities, trust boundaries, important entities and interfaces. Define the Scribe and patient-context contracts without assuming access to their code.

Choose one coherent, implementable design. Flag material departures by section, position P01–P09 or stage A–G and link to S2/S6. Show a reference-question path and a medication-review path with doctor-facing outputs. Use cited or clearly fictional examples, not invented clinical facts.

### S2 · Decision Register
This is the spine of your submission. For every significant choice record:

**Current position or omission → your choice → why → strongest rejected alternative → accepted cost/trade-off → how the choice will be validated.**

Cover at least these ten areas: grounding sources; chunking mechanism; retrieval design; embedding/index strategy; drug-data strategy; safety-check boundaries; model/provider posture; data residency; multi-tenancy; audit. Cross-reference detailed designs rather than repeating them.

“Accepted cost” means the downside you knowingly accept—such as latency, review burden, coverage, complexity or dependence on a provider. It does **not** require a monetary build estimate. An entry lacking a real rejected alternative or accepted cost earns no decision-register credit. Defend retained choices as your own; merely restating 01/03 earns nothing.

### S3 · Grounding & Sources Plan
Name the specific clinical, medicine/ingredient/brand and regulatory sources you recommend. State each source’s purpose, coverage, authority, version/date, limitations, free-versus-licensed-versus-curated status, and intended-use rights. Distinguish access from permission for storage, extraction, indexing, displayed excerpts and any proposed training use.

Show the full knowledge lifecycle: acquisition, extraction, review, chunking, versioning, publication, retrieval eligibility, updates and withdrawal. Defend the retrieval and embedding/index approach. Explain how chunking preserves clinical scope, headings, tables, units, exceptions, footnotes and cross-page relationships. Include one compact chunk/citation example and explain how applicability and citation support are validated separately from retrieval relevance.

Address conflicts, supersession, specialty/population scope, local/national precedence and any international/background pathway. Identify missing permissions or sources and their consequence for affected capabilities.

### S4 · Rules of Behavior for India
Produce enforceable product rules, not a legal essay: **condition → required or prohibited behavior → evidence/reason → enforcement → verification/approval needed**. Explain what the AI may answer, must refuse, must show, and must never do, given the proposed use, Indian requirements and clinical context.

For material legal/regulatory and source/provider claims, give the primary source/link, version/date, relevant provision, current status/effective date, applicability and technical consequence. Distinguish law, guidance, contract terms, product policy and your interpretation. Mark unverified matters honestly; identify the qualified reviewer and what cannot be enabled until resolved. No paid source purchase, vendor quotation or contact with doctors is required.

<!-- PAGE BREAK -->

## 00 · Output requirements, continued
### S5 · Correctness & Safety Design
Define deterministic versus generated behavior and enforce the fixed safety boundary. Specify drug identity, combination ingredients, patient context, provenance, uncertainty and check results—including a finding with incomplete coverage. Explain missing, conflicting, stale or unavailable inputs, evidence and services.

Connect patient/source corrections and pending approvals to the doctor workflow, access control, multi-tenancy, languages, degraded operation and audit. Do not leave integration or the clinician-facing surface unspecified.

### S6 · What You Added
Rank omissions, weak assumptions and weaknesses in our architecture/build plan. Use **factor → current section or omission → consequence → severity → proposed handling**; link the resulting change to S2 or validation.

Go beyond the starter list. A named factor earns improvement credit only for a concrete mechanism or meaningful depth beyond the mention. Generic filler and invented weaknesses earn nothing.

### S7 · Validation & QA Plan
Specify evaluation-set construction/provenance, clinician-approved references, independent held-out cases, release gates, daily/weekly QA duties, production sampling and revalidation after model/prompt/source/mapping/rule changes.

Use **capability → test data/reference standard → method → pass criterion → evidence → validator**. Separate engineering/QA checks from clinical/legal approval. Define metrics and denominators for confidently wrong answers, useful supported answers and appropriate abstentions. Explain how our QA person and qualified reviewers maintain quality at all-India scale without reviewing every answer manually. Design these checks; do not invent completed benchmarks or sign-offs.

### S8 · Doctor-Handover Checklist
Give the runnable completion checklist for released capabilities: clinical, legal, knowledge/data, engineering/integration, operational and organizational readiness.

Use **item → required result → verification/evidence → responsible validator/approver → handover blocker**. Cover content, permissions, configurations, usable coverage, user instructions, support and operating evidence. Separate national availability from validated coverage. Missing approval is not a completed checkbox; disabling nearly everything is not a complete solution.

### S9 · AI-Usage Note
Three lines: how you used AI; one recommendation checked, changed or rejected and why; the most important remaining uncertainty. Report a genuine override where one occurred. Otherwise say none and describe a material recommendation independently checked.

### Grading and submission
**Written scoring /100:** S2 Decisions **25**; S6 Added factors **20**; S3 Sources **15**; S4 India behavior **15**; S7 Validation/QA **15**; S8 Doctor handover **10**.

S1/S5 correctness feeds the scored sections; S9 is required. Missing diagram: −2; missing AI note: −2; material unflagged departures: −2 each, capped at −6. A fixed-law/fence breach, verified materially false regulatory/approval claim, fabricated source, prohibited delivery schedule or unassessable Decision Register prevents a pass. A withheld area deferred to an unseen “internal plan” earns zero for that area. The operating-cadence exception in 00 still applies.

Email the one file through the invitation’s submission channel within four hours, with opening and submission times. Excess pages receive no credit. Late work is flagged for a consistent cohort-level decision, not treated as dishonesty.

<!-- PAGE BREAK -->

## 01 · Architecture Pack
### 1. The component and the design posture
A clinical intelligence layer inside a doctor-facing app for Indian outpatient practice: it answers clinical questions grounded in Indian medical sources with citations, resolves Indian brand-name prescribing to the ingredient level, and runs deterministic medication-safety checks that never guess. The current approach is a frontier LLM wrapped in an India-specific clinical layer—not a generic chatbot or a custom-trained medical model. The doctor always decides.

The supplied pack describes a design informed by prior build-and-test cycles and six independent implementations. Those descriptions are context, not new test evidence or proof of production readiness. The fixed layer below is retained from the supplied Architecture Pack. Everything outside it is the current working proposal and is open to challenge.

### 2. Binding laws and fences — fixed assessment layer
1. **The doctor decides.** Nothing consequential finalizes without doctor confirmation; the system drafts, checks, and cites — it never acts.
2. **Grounded or honest.** Consequential clinical claims — doses, numbers, safety statements, regulatory status — come only from retrieved, versioned evidence with citations, or the system states plainly that it cannot confirm.
3. **Claim-level provenance.** Every consequential claim maps to source, version/date, and location within the source.
4. **Safety outside the LLM.** Medication-safety checks are pure lookup/rules over versioned data. No model call anywhere in a check path.
5. **Unknown is first-class.** Every check returns exactly one of: `HIT · CHECKED_NO_HIT · PARTIAL_COVERAGE · UNVERIFIED_INPUT · NOT_CHECKED · DATA_EXPIRED · SOURCE_CONFLICT · SERVICE_UNAVAILABLE`. **Missing data must never render as "safe."**
6. **No silent ambiguity.** An uncertain brand/strength/formulation resolution is queued with a reason code, never auto-resolved. Fuzzy matching may assist search; it is never truth.
7. **Regulatory truth is event-sourced.** Status derives from effective-dated regulatory events (notification id, dates, source, supersession, scope). A `banned = true/false` boolean is a design failure.
8. **Everything versioned, everything replayable.** Any past output must be reconstructable against exactly the data, rules, prompts, and model versions that produced it.
9. **Untrusted input.** Documents, transcripts, and imported data are data, never instructions.
10. **No silent upgrades.** A model, prompt, or data change triggers re-evaluation before it serves.
11. **Fail visibly.** A degraded dependency produces a visible degraded state, never a quiet fallback that looks normal.
12. **Fences.** This version does **not** build: patient-specific dose calculation (including pediatric mg/kg), diagnostic ranking, triage/severity scoring, auto-generated treatment plans, or any patient-facing advice surface.

These twelve requirements govern this exercise. A concern about a fixed requirement may be documented explicitly, but the recommended in-scope solution must still satisfy it; a proposed exception is not permission to ship it. Ordinary technical choices outside this layer remain yours.

<!-- PAGE BREAK -->

## 01 · Current working architecture — open layer
### 3. Logical relationships
The following redraw preserves the relationships in the supplied diagram. These are logical responsibilities, not a requirement for separate services or a particular database.

```text
Scribe: structured Rx          Patient-context:
entities + transcript refs     versioned snapshot
       |                              |
       v                              v
INDIA DRUG MASTER              GROUNDED CLINICAL Q&A
- alias->brand->salt graph     - decision-unit chunks of
- FDC decomposition              Indian sources
- effective-dated reg status   - hybrid retrieval
- ambiguity queue              - claim-level citations
       |                       - abstention; conflicts
       | salts                   shown, never merged
       v                              |
DETERMINISTIC SAFETY RAIL             | evidence
- duplicate ingredient                |
- restricted/banned FDC               v
- severe interactions    verdicts
- cumulative exposure   --------> ORCHESTRATION
- 8-state output contract         - structured-first routing
                                  - grounded composition
                                  - labelled fallback tiers
                                  - abstention
                                       |
                                       v
             Doctor-facing output + full audit trace
```

### Current positions P01–P04
**P01.** **Structured-first routing:** drug identity, strengths, alternatives, prices, regulatory status answer from the graph/event store directly — never from retrieval or generation.

**P02.** **FDC decomposition before any check:** Indian prescriptions are fixed-dose-combination dense; all safety logic runs at ingredient level, with cumulative same-ingredient exposure totaled across the whole prescription.

**P03.** **Answer-source laddering:** verified Indian corpus first; an organization's own protocols second (tenant-scoped, labeled); recognized international sources third (flagged as non-India); general model knowledge only for background-class content, always visibly labeled, never for doses, safety claims, or regulatory status; otherwise an honest "cannot confirm" that names what's missing.

**P04.** **Supersession ≠ conflict:** when a source has editions, current serves and older is retained flagged; only genuinely concurrent disagreements are shown side-by-side with dates.

These are starting decisions, not answers to reproduce. Show whether and why each important position survives in your final architecture. Any changes remain subject to the twelve fixed laws and fences.

<!-- PAGE BREAK -->

## 01 · Current positions, continued
### Current positions P05–P09
**P05.** **Trust-tiered corpus:** content moves raw → structured → verified → live; only verified-live content serves clinical answers; safety-rail content requires 100% qualified human review, never sampling.

**P06.** **Evidence-sufficiency gate:** before any generation, a deterministic pass decides whether retrieved material actually answers the question's class; if not, the ladder descends or the system abstains. (The supplied pack reports out-of-corpus mismatches in prior tests; test evidence is not included here.)

**P07.** **Cross-source skepticism:** canonical sources can be wrong. The pipeline must be able to flag a record that contradicts sibling records, cross-references, or market reality — a poisoned canonical row must be catchable, queueable, and must never silently become truth. *(Mechanism deliberately unspecified — yours to design.)*

**P08.** **Inventory-vs-register checking:** a product can be in stock and illegal; stock data and regulatory events must be cross-checked, not just prescriptions.

**P09.** **Population and form scope:** regulatory events and clinical guidance carry scope (adult/pediatric, tablet/suspension, trimester); checks and answers must respect scope, not string-match names.

### 4. What the design must survive
The supplied operating reality ranges from high-volume general practice to gynaecology, pediatrics, orthopaedics and other specialties. Inputs include regional brand names, inconsistent spelling, transliteration and non-Latin scripts. Knowledge and drug-regulatory sources may conflict, supersede one another or carry population/formulation restrictions. Clinics may have shared machines and unreliable connectivity. The full context follows in 02.

### 5. Known open questions — starter list only
Corpus scale-up strategy and source rights; the full verification operating model and review throughput; behavior rules under Indian law and medical-practice regulation; clinical answer boundaries by specialty and population; multi-tenant and organization-overlay governance; observability and audit at all-India scale; and the complete pre-doctor-handover readiness definition.

This is not an exhaustive gap register. Your S6 should add consequential factors and mechanisms that this pack does not provide. Do not treat the current positions or the source hints in 02 as an answer key.

<!-- PAGE BREAK -->

## 02 · Product and practice context
The following is **BRAHMO’s supplied design context**, not a new market study. Quantities and usability statements are scenario assumptions or product targets to design against, not independently verified national statistics.

### 1. Who the doctor is
**General physician.** The supplied scenario is 60–100 patients per day and 3–7 minutes per consultation, often single-handed. Pen and paper remain the practical comparison. Each interruption must provide visible value.

**Specialists.** Gynaecology/obstetrics raises pregnancy-specific considerations; pediatrics raises population, guardian and vaccination-schedule questions; orthopaedics involves analgesic-heavy workflows and procedure notes; internal medicine includes chronic disease, polypharmacy and elderly patients taking several medicines. These are needs to handle within the fixed scope—not permission to add excluded patient-specific dose calculation.

**Settings.** Solo clinics, nursing homes and small-hospital OPD departments in metro and tier-2/3 settings. Shared front-desk computers, doctors’ own phones, and intermittent power or connectivity are part of the scenario.

**Languages.** Consultations may mix English with Hindi, Telugu, Tamil, Kannada and other languages mid-sentence. The source brief notes English records and a need for patient-language instructions in the wider workflow. This assessment retains the fixed exclusion of a patient-facing AI advice surface; make the clinician-facing language and export boundaries explicit.

### 2. What the doctor asks an AI
The supplied question categories include first-/second-line treatment references; national programme or guideline questions; alternatives when medicines are unavailable or unaffordable; interactions and pregnancy/lactation safety; dose-reference text to read, not calculate; brand differences; whether a combination product is appropriate or restricted; and what changed in a guideline. Doctors ask during a consultation and value concise answers. Define how reference information remains distinct from an excluded patient-specific treatment plan.

### 3. The drug-data environment
The scenario is brand-first prescribing: many brands for one molecule, brand variants with different ingredients, collisions, misspellings and transliteration on stock records. Combination products can hide repeated ingredients across one prescription. The architecture must handle ingredient-level identity and evidence rather than trusting a brand string.

The supplied context flags dated bans/restrictions, population/form scope, stays, reversals, stock-versus-sale eligibility, price control and Jan Aushadhi. Treat specific legal claims about these as research questions requiring evidence; do not infer the legal status of stock from its existence. Authoritative-looking data may still be wrong, stale or inconsistent.

### 4. The clinical-knowledge landscape
The source brief names national programmes (TB, vector-borne disease, immunization, maternal health), ICMR Standard Treatment Workflows, specialty societies, formularies, and hospital protocols/antibiograms. It describes national-programme priority in their domains and local contractual expectations. These are starting assertions to assess—not a prevalidated universal precedence rule. Editions, scope, concurrent disagreement and reuse rights must be addressed in your chosen design.

<!-- PAGE BREAK -->

## 02 · India-specific research and product goals
### 5. Regulatory and legal surface — indicative research leads
The supplied brief identifies the areas below. **It does not supply the underlying instruments, verified current dates or a legal opinion.** In S4, verify their current status and actual applicability, then turn the findings into enforceable product behavior. Do not copy an unsupported headline as a settled legal conclusion.

| Supplied research area | What your plan must determine |
|---|---|
| Digital personal data protection | Applicable provisions and phased commencement; consent/purpose; children/guardians; breach duties; retention/erasure; any significant-fiduciary requirements; processing and transfer posture. |
| Medical-purpose software | Intended use and functions; applicable medical-device rules/guidance; classification/approval implications; what doctor supervision or a disclaimer does and does not establish. |
| Telemedicine practice | Applicability to the proposed workflow, registered practitioner responsibilities, remote-prescribing categories, and the clinician/AI boundary. |
| Professional regulation | Prescriber eligibility; prescription format and generic-name requirements where applicable; practitioner/developer accountability and contractual implications. |
| Drug schedules and pharmacovigilance | Relevant H/H1/X, narcotic/psychotropic and adverse-event reporting requirements for the functions actually enabled. |

This list is indicative, not complete. Add further relevant areas you identify. Source rights, provider contracts and deployment-specific obligations require their own evidence, not a generic “compliant” label.

### 6. Operating constraints from the supplied brief
**Alert fatigue.** The brief’s examples emphasize that excessive low-value warnings undermine attention. Design the alert-governance mechanism and validation rather than treating the rhetoric as a measured threshold.

**Latency.** The supplied aspiration is roughly two seconds for mid-consult interaction. State which response stage this applies to and how responsiveness will be verified. It is not a benchmark already achieved by the prototype.

**Trust.** Visible citations, admitted uncertainty and an explained inability to confirm are central product expectations. The brief’s “one wrong answer undoes fifty right ones” is a trust heuristic, not a scored clinical metric.

**Offline, shared devices and corrections.** Offline/degraded operation and shared-machine use must be considered. The correction-capture goal is one tap with minimal disruption; specify what is captured and what review is needed rather than assuming a correction automatically becomes clinical truth.

### 7. The end state
Design for a clinical AI component available to doctors across India: generalists and specialists, varied populations, settings and languages. It should be honest under uncertainty and operable by a small team with a QA function and qualified clinical reviewers rather than an army.

**National availability is not the same as validated coverage of every question, medicine, specialty or language.** Make intended breadth, actual validated support and transparent limitations part of one coherent product. Do not quietly reduce the assignment to an English-only adult-GP demonstration, or claim unrestricted national clinical readiness without validation and required approvals.

BRAHMO supplies product priorities. Your document should resolve routine technical decisions and give engineering, QA and appropriate reviewers usable work and acceptance definitions, rather than require daily architecture decisions or code reviews from leadership.

<!-- PAGE BREAK -->

## 03 · Current Build Plan — Candidate Edition
### 1. What is shared and what is withheld
This is the supplied current build plan, not a replacement executive summary. **The stage deliverables and statuses below are retained from file 03.** They are BRAHMO-provided assessment context; no code, raw validation evidence, signed source rights or reviewer contracts accompanies this exercise. A status label is not an independent certification or a completed doctor-handover checklist.

Dates, durations, team composition, build costs and partner identities have been removed. The stage order is the current dependency proposal, not a required delivery calendar; you may challenge it through S2/S6 without adding a schedule.

| Internal material not supplied | Candidate section that must supply your own design |
|---|---|
| Source catalog, rights strategy and detailed ingestion | S3 · Grounding & Sources Plan |
| India behavior rules and regulatory feature analysis | S4 · Rules of Behavior for India |
| Full QA/validation machinery and evaluation-suite definitions | S7 · Validation & QA Plan |
| Internal gap register | S6 · What You Added |

Existing source hints, requirements and gate philosophy are still visible elsewhere in this packet. The withheld content is the detailed internal answer—not all mention of those subjects. Do not defer to an unseen internal document.

**Status legend:** VALIDATED = reported built/tested at prototype or pilot scale, not production deployment; IN FLIGHT = partially built; PLANNED = designed, not built; OPEN = not yet designed. Clinical/legal/consent work is a parallel human lane whose approvals are not produced by faster code generation.

### 2. Stages A–C — reported foundation and first slice

#### A — Platform & contracts
**Reported status: VALIDATED.**

Repo/CI and tenant baseline; core schemas; conformance stubs for the two upstream contracts (scribe entities in, versioned patient-context snapshot in); the 8-state status-contract service; evaluation skeleton with held-out answer keys owned outside engineering.

#### B — Data foundation
**Reported status: VALIDATED at subset scale — thousands of SKUs, not all-India.**

Bulk load of rights-cleared free sources into raw/structured tiers (nothing serves yet); drug-master spine — alias→brand→salt graph with strengths and dose forms; pharmacy-overlay ingestion (overlay never redefines canonical truth); FDC decomposition; ambiguity queue with reason codes; regulatory feed written as effective-dated events with supersession and scope; retrieval skeleton; exact-quote binding and dual-source agreement pipelines for extraction quality.

#### C — First serving slice
**Reported status: VALIDATED at pilot scale — a handful of specialties, small workflow set.**

Duplicate-ingredient and banned/restricted rails live with coverage states; first verified corpus slice serving a small number of specialties' top conditions with claim-level citations; abstention live; the consequential-vs-background query classifier guarding the answer ladder; clinic alias dictionary exported back upstream for recognition biasing.

<!-- PAGE BREAK -->

## 03 · Current Build Plan, continued
### Stages D–G — remaining design and readiness work

#### D — Verified rule content
**Reported status: IN FLIGHT.**

Clinician-verified interaction / allergy / pregnancy rule batches wired into the rail. Current strategy: a **curated critical set under named clinical-pharmacologist sign-off**, scoped to the molecules Indian primary care actually prescribes — not a licensed comprehensive database; the scale-up/licensing trigger is an open decision. Organization-overlay precedence (a tenant's protocol outranks the national default only for that tenant, visibly labeled). End-to-end golden-thread scenario automated; simulated-consult dogfooding.

#### E — Hardening
**Reported status: PLANNED.**

Full-loop alpha; corpus depth driven by logged misses and eval failures (never bulk ingestion); alert-fatigue defaults — high-severity only, tuned by acted-vs-dismissed telemetry; cross-tenant negative suites; PHI-in-logs scanning; prompt-injection corpus (instructions embedded in documents/transcripts must be inert); byte-consistent audit replay proven end to end.

#### F — Supervised live use
**Reported status: PLANNED.**

First pilot doctors live under supervision; one-tap correction loop wired into review queues; latency and cost measured on real usage before any commitments; clinical sign-off recorded for everything shipped; incident runbook active; release manifest and rehearsed rollback.

#### G — Scale-out to all-India
**Reported status: OPEN — largely what your Sections 1–8 must supply.**

All-specialty corpus depth; hospital/multi-tenant overlays at scale; multilingual and transliteration handling at scale; offline/degraded modes; observability and audit at national volume; the operating model that keeps quality up without an army.

### 3. Gates between stages — supplied philosophy
The full suite definitions are withheld. These current gates are starting requirements for your proposed validation machinery, not evidence that every gate has passed.

- **Gate 1 (after C):** held-out drug-mapping key green with **zero silent wrong mappings**; the verified slice serves with citations; every one of the 8 check states reachable and correctly rendered.
- **Gate 2 (after E):** a seeded end-to-end golden-thread run passes; all hard blockers green at pilot scope — a missed trap, an uncited consequential number, an unknown rendered as safe, a cross-tenant leak, an unlabeled general-knowledge answer are each *individually* release-blocking.
- **Gate 3 (after F):** clinical sign-off recorded for everything shipped; stable daily usage; the regulatory position documented for exactly what shipped.
- **Standing rules:** no weighted average outvotes a catastrophe; held-out keys never belong to the implementer being graded; editing a test to make it pass is treated as an incident.

<!-- PAGE BREAK -->

## 03 · Human lane, operating model and open work
### 4. Human lane — supplied operating assumptions
The source describes these arrangements as in place or expected. For the assessment, assume the stated partner inputs exist and design how to consume them; do not invent named partners, verification outcomes or capacity figures.

- A clinical pharmacologist is contracted as a **release-gating reviewer**; review batches are ordered by real usage weight, and **when review throughput backs up, supported safety scope shrinks before unreviewed content ships — never the reverse.**
- Legal counsel works milestone-based; the feature-classification memo is drafted mid-build, not at the end.
- Consent operations are physically staged in clinics before any live use.
- Pilot doctors supply prescribing exports, ranked condition lists, local brand/alias review sessions, specialty review labor, and corrections. (The partner programme's details are withheld; assume these inputs exist and design for them.)

### 5. Operating rules described in the supplied plan
AI-native development: agents write most of the code, every module lands with its own tests and a named accountable human · no self-approval on safety- or security-critical PRs · prompts and evals live in the repo, versioned and pinned like code · any model/prompt/data change triggers its mapped regression before promotion · releases are diff-first with a reviewed changelog ("what changed, on which source, effective when") · corpus growth is strategic-increment only — serve narrow, deepen where query logs and eval failures point, bulk token-chunking banned.

These are existing operating positions to examine, except where they restate a fixed law. A proposed change must explain its consequence and remain consistent with the twelve laws/fences. Dependencies and operating controls are appropriate; a delivery schedule or defect calendar is not.

### 6. What the plan still needs from you
The full internal gap register is not shared. Your S6 should identify both missing factors and weaknesses in the current architecture/build plan, including where existing claims, interfaces or stage choices are incomplete or inconsistent. The 01 starter list is not the limit of the problem.

Your final plan must stand alone for its readers: engineering should understand the design; QA should know how to verify behavior; qualified reviewers should know what they must approve; and the person handing the product to doctors should be able to run S8. Do not mark any real-world verification or approval complete merely because the source calls a prototype stage VALIDATED.

### Source note for this merged candidate edition
Merged from BRAHMO's four assessment source documents — instructions (00), architecture pack (01), context brief (02) and current build plan (03). The evaluator guide and answer keys are intentionally excluded. No prior codebase, original assessment archive, older executive specification or private reference is required to answer this exercise.

**Improve on this. Where it is wrong, say so with an argument and an accepted trade-off. Where it is silent, fill it. Where it is right, defend it as your own decision.**
