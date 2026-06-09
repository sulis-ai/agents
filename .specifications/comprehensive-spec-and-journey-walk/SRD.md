# Software Requirements Document: Comprehensive Spec & Two-Surface Journey Walk

**Change:** CH-CQRWWR (`01KTPWDWJ7CQRWWRGPQEQ22P1M`)
**Primitive:** `harden`
**Slug:** `comprehensive-spec-and-journey-walk`
**Status:** specified
**Author:** Sulis Requirements Analyst (AI)
**Date:** 2026-06-09
**Classification:** Methodology / tooling change to the Sulis marketplace itself
**Target model:** `features/entity-crud/DESIGN.md` (repo `platform`) — the comprehensive design document this change makes Sulis always produce.

---

## Summary

Sulis's specify/design stages currently treat **depth** (lite/standard/deep) as
how *thin* the specification is: lite and standard produce a short `SPEC.md` and
skip use cases, NFR, threat model, and diagrams entirely; only deep (the
requirements-analyst) builds the comprehensive document. **That is backwards.**

This change makes three corrections, in three phases:

1. **Decouple depth from doc-existence.** The comprehensive design document is
   ALWAYS produced — use cases with flows, NFR, personas, scope, problem
   discovery. Depth sizes only the *interview*, never which documents exist.
2. **Two-surface outside-in journey walk + UC-derived scenarios.** Extend the
   existing single-surface (UI) journey walk to a second surface — the
   API/SDK/MCP **tool** surface — so the machine consumer's path gets the same
   outside-in proof the human's does. Derive verifiable scenarios from every
   use-case flow (main/alternate/exception), for both surfaces, and add a
   **UC-flow-coverage gate**.
3. **Round out the comprehensive document.** Add an always-on STRIDE threat
   model, architecture-at-levels (C4 context/container/component), and Business
   Decision Records (BDR) alongside the existing ADRs.

The two actors are the non-technical **founder** (running `/sulis:specify`,
`/sulis:design`) and the **Sulis agent** (executing the stages). The misuse
cases enumerate the bypasses — skip use cases, walk one surface, write
happy-path-only scenarios — the change must close.

---

### 1. Introduction

#### 1.1 Purpose

Specify the methodology change that makes Sulis always produce a comprehensive
design document, walk both consumer surfaces outside-in, derive verifiable
scenarios from every use-case flow, and round out the document with a threat
model, architecture-at-levels, and business decision records.

#### 1.2 Scope

In scope: the behaviour of `/sulis:specify`, `/sulis:design`
(`draft-architecture`), the depth classifier, the requirements-analyst agent,
the requirements/TDD templates, the scenario authoring + coverage tooling, and
the gates that block a change from advancing. Out of scope: implementation of
the changes (this is a requirements document); the brain entity schema beyond
what scenarios already use; runtime products built *by* the methodology.

#### 1.3 Intended Audience

The engineering architect (`/sulis:draft-architecture`) who will design the
implementation; the founder who owns the methodology direction; future agents
maintaining the specify/design stages.

#### 1.4 Definitions and Acronyms

See [GLOSSARY.md](GLOSSARY.md) for the full domain glossary. Key terms:
*comprehensive design document*, *depth*, *doc-existence*, *UI surface*, *tool
surface*, *journey walk*, *EXISTS/planned-WP/GAP*, *UC-flow-coverage gate*,
*ADR*, *BDR*, *architecture-at-levels*.

#### 1.5 References

- Target model: `features/entity-crud/DESIGN.md` (platform repo)
- Methodology discipline: `methodology/studios/product-development/STANDARDS.md` (platform repo)
- Current depth classifier: `plugins/sulis/scripts/_specify_classifier.py`
- Current UI journey walk (#85): `plugins/sulis/skills/draft-architecture/SKILL.md` step 8.5
- Current scenario coverage gate: `plugins/sulis/scripts/_verify_scenario_coverage.py`
- Verification substrate (#98): `plugins/sulis/scripts/sulis-verify-acceptance`, `_scenario_authoring.py`
- Verification Plan section name: ADR-001 (`.architecture/verification-by-design/`)

---

### 2. Overall Description

#### 2.1 Product Perspective

The product is the Sulis specify→design→plan methodology pipeline. Today it is a
depth-gated pipeline: small intake ⇒ thin document. After this change it is a
depth-sized-intake / always-comprehensive-document pipeline whose design stage
walks two surfaces and whose coverage gate enforces flow-level scenario
completeness.

#### 2.2 Product Functions (Summary)

- **F-01** — Always produce the comprehensive design document (depth-independent).
- **F-02** — Size only the intake by depth; never gate doc-existence by depth.
- **F-03** — Restructure the Sulis design artifact toward the comprehensive `DESIGN.md` shape.
- **F-04** — Walk the UI surface journey outside-in (existing, retained).
- **F-05** — Walk the tool (API/SDK/MCP) surface journey outside-in (new second surface).
- **F-06** — Derive verifiable scenarios from every use-case flow, for both surfaces.
- **F-07** — Enforce a UC-flow-coverage gate before a change ships.
- **F-08** — Always include a STRIDE threat model section.
- **F-09** — Produce architecture-at-levels (context/container/component).
- **F-10** — Produce Business Decision Records (BDR) alongside ADRs.

#### 2.3 User Classes and Characteristics

| Class | Description | Technical level |
|-------|-------------|-----------------|
| Founder | Runs `/sulis:specify`, `/sulis:design`; owns product direction | Non-technical (default Novice) |
| Sulis agent | Executes the stages; produces artifacts; runs gates | N/A (automated actor) |
| Engineering architect (downstream) | Consumes the comprehensive document to design implementation | Technical |

#### 2.4 Operating Environment

Claude Code with the `sulis` plugin installed; a change worktree under
`~/.sulis/changes/<id>/worktree`; the brain instance store under
`.brain/instances/`; the verification substrate (`sulis-verify-acceptance`).

#### 2.5 Design and Implementation Constraints

| ID | Constraint | Impact |
|----|------------|--------|
| C-01 | The comprehensive document MUST match the canonical `entity-crud/DESIGN.md` section structure (the target model). | Section names and ordering are fixed by the target, not invented. |
| C-02 | The `## Verification Plan` heading is fixed verbatim by ADR-001. | P-VER anchors regex on it; no renaming. |
| C-03 | The depth classifier MUST stay deterministic and pure (no I/O). | Reuse `classify_depth`'s shape; change semantics, not purity. |
| C-04 | Tool-surface walking MUST reuse the #98 verification substrate (scripted `http_call`/`subprocess` + agent-step tiers). | No new driver mechanism. |
| C-05 | Scenario coverage MUST reuse the brain as objective source of truth. | Extend `_verify_scenario_coverage.py`, do not bypass the brain. |
| C-06 | Founder-facing output MUST stay in founder English (FE-01..FE-10). | No internal IDs / jargon in `/sulis:specify` / `/sulis:design` chat. |

#### 2.6 Assumptions and Dependencies

See [§4.4](#44-assumptions) and [§4.5](#45-dependencies).

---

### 3. External Interface Requirements

#### 3.1 User Interfaces

The founder interacts only through `/sulis:specify` and `/sulis:design` chat,
in plain English. The depth proposal sentence (echo-before-act) is retained but
reworded: depth proposes interview size, NOT document thinness.

#### 3.3 Software Interfaces

| Interface | Surface | Role in this change |
|-----------|---------|---------------------|
| `_specify_classifier.py::classify_depth` | internal | Semantics change: depth = gather-effort, not doc-gate. |
| `draft-architecture/SKILL.md` step 8.5 | internal | Extended to a two-surface walk. |
| `_verify_scenario_coverage.py` | internal | Extended with UC-flow + both-surface coverage. |
| `sulis-author-scenario` / `_scenario_authoring.py` | internal | Authors scenarios per flow per surface. |
| `sulis-verify-acceptance` (#98) | internal | Drives tool-surface scenarios for real. |
| Brain instance store | internal | Objective source of scenario/coverage truth. |

#### 3.4 Communications Interfaces

For the tool surface walk, the agent exercises the system's real protocol
round-trips (HTTP / subprocess / MCP tool calls) via the verification substrate
— not mocks.

---

### 4. Requirements

#### 4.1 Functional Requirements

> Phase 1 — Decouple depth from doc-existence

| ID | Requirement | Priority | Acceptance criterion (testable) |
|----|-------------|----------|---------------------------------|
| FR-01 | The comprehensive design document MUST be produced for EVERY behavioural change regardless of depth (lite/standard/deep). | Must | Driving `/sulis:specify` + `/sulis:design` at depth=lite on a sample behavioural change produces a document containing all mandatory sections (FR-11). |
| FR-02 | Depth MUST size ONLY the intake (how much context is gathered), never which document sections exist. | Must | For the same sample change, lite/standard/deep produce documents with the SAME section set; only the populated *detail* (interview-derived content) differs. |
| FR-03 | The depth classifier MUST classify intake size and MUST NOT be consulted to decide whether use cases / NFR / threat model / diagrams are produced. | Must | `classify_depth` output is referenced only by the interview-sizing path; no doc-section emission branches on its result (verified by code inspection + a driven assertion). |
| FR-04 | The depth proposal sentence shown to the founder MUST describe interview size, not document completeness. | Must | The founder-facing proposal contains no claim that a section will be "skipped"; lite reads as "fewer questions", not "shorter doc". |
| FR-05 | The Sulis design artifact MUST be restructured from the current `TDD.md` shape (Overview/Form/Armor/Proof/Trade-offs/Open-questions/Verification-Plan) toward the comprehensive `DESIGN.md` shape (FR-11). | Must | The produced design artifact's section headers match the mandatory structure in FR-11, not the legacy seven-part TDD shape. |
| FR-06 | NFR MUST be always-on: the design document MUST carry a non-functional-requirements section with measurable targets for every behavioural change. | Must | The produced document's NFR section exists and contains at least one measurable target (a threshold, not an adjective) for performance, security, and reliability. |

> Phase 2 — Two-surface journey walk + UC-derived scenarios

| ID | Requirement | Priority | Acceptance criterion (testable) |
|----|-------------|----------|---------------------------------|
| FR-07 | The design stage MUST walk the UI surface journey outside-in, hop-by-hop, each hop classified EXISTS (cite file+function) / planned-WP / GAP. | Must | (Retained #85.) The produced `## Journey Walk` UI table classifies every hop; a bare GAP blocks design completion. |
| FR-08 | The design stage MUST ALSO walk the tool (API/SDK/MCP) surface journey outside-in — the machine consumer's path end-to-end — each operation classified EXISTS / planned-WP / GAP. | Must | The produced `## Journey Walk` carries a second, tool-surface table covering every tool operation in the journey. |
| FR-09 | For a tool-surface hop, EXISTS MUST require BOTH the tool/handler cited AND its ServiceSpec binding cited; a serving interface without a binding is a GAP. | Must | A tool hop whose handler exists but whose ServiceSpec binding is absent is classified GAP, not EXISTS, and blocks the gate. |
| FR-10 | Verifiable scenarios MUST be derived from the use-case flows for BOTH surfaces: every main/alternate/exception flow yields at least one scenario; UI scenarios drive the screen, tool scenarios drive the real MCP/SDK/API call end-to-end (observed-or-blocked). | Must | For the sample change, each UC flow maps to ≥1 scenario; tool scenarios carry a real driver (`http_call`/`subprocess`/agent-step) and report observed-or-blocked when driven. |
| FR-11 | The comprehensive design document MUST contain, in order, the mandatory section set (the target structure). | Must | See the **Target Structure** requirement below. Each listed section is present and non-empty (or an explicit, justified `n/a`). |
| FR-12 | A UC-flow-coverage gate MUST block a change from shipping if any main/alternate/exception flow of any in-scope use case has no covering scenario. | Must | A sample change with one uncovered flow yields verdict `gaps`; covering it yields `covered`. |
| FR-13 | The UC-flow-coverage gate MUST be a companion to (not a replacement for) the scenario-required gate (#103) and the journey-coverage gate (#86) — all three apply. | Must | All three gates run on a behavioural change; each can independently block. |
| FR-14 | The tool-surface scenarios MUST be driven via the existing #98 verification substrate (scripted `http_call`/`subprocess` + agent-step tiers), not a new mechanism. | Must | Driven tool scenarios resolve through `driver_for_step` / `sulis-verify-acceptance`; no parallel driver is introduced. |

> Phase 3 — Round out the comprehensive document

| ID | Requirement | Priority | Acceptance criterion (testable) |
|----|-------------|----------|---------------------------------|
| FR-15 | The comprehensive design document MUST always include a STRIDE threat model section (modelled on entity-crud §4.6): STRIDE analysis table, trust boundaries, attack surface, summary. | Must | The produced document's threat-model section contains all four sub-parts with at least one row each (or justified N/A per category). |
| FR-16 | The comprehensive design document MUST produce architecture-at-levels: a context diagram, a container diagram, and a component diagram (C4 levels). | Must | The produced document's solution-design section carries three distinct diagrams at the three levels, beyond the existing 5 flat Mermaid types. |
| FR-17 | The methodology MUST support Business Decision Records (BDR) alongside ADRs: a business/product decision (scope cut, sequencing, pricing) is recorded as a BDR, distinct from a technical ADR. | Must | A sample business decision is recorded as a BDR with context + decision + consequences; the ADR/BDR distinction is documented and the templates support both. |

##### Target Structure (the comprehensive design document) — FR-11 expanded

The document MUST carry these sections, in this order, modelled on
`features/entity-crud/DESIGN.md`:

1. **§1 Executive Summary**
2. **§2 Problem Discovery** — problem statement, current behaviour, desired behaviour, why now, impact of not doing
3. **§3 Stakeholders / Personas** — stakeholder table + user personas
4. **§4 Requirements**
   - §4.1 Functional Requirements (IDs, priority, notes)
   - §4.2 Non-Functional Requirements (measurable targets: performance, security, reliability)
   - §4.3 Constraints
   - §4.4 Assumptions (+ risk if invalid)
   - §4.5 Dependencies (classification: consume / build / blocks)
   - §4.6 STRIDE Threat Model (STRIDE table, trust boundaries, attack surface, summary)
5. **§5 Scope** — in scope, out of scope, MVP vs future
6. **§6 Use Cases** — UC-NN with Actor / Trigger / Preconditions / Main Flow / Alternate Flows / Exception Flows (numbered 3a/6a/7a branches)
7. **§7 Solution Design** — solution overview, architecture-at-levels (context/container/component), data flow, component model
8. **Technical Decisions (ADRs) + Business Decisions (BDRs)**
9. **Migration / Rollback / Security / Performance**
10. **`## Verification Plan`** (verbatim heading per ADR-001; six required subsections)

Sections that are genuinely inapplicable carry `n/a — <one-sentence justification>`,
never a bare omission.

#### 4.2 Non-Functional Requirements

See [NFR.md](NFR.md) for the full non-functional specification. In summary:
depth classification is deterministic; the always-comprehensive document adds a
bounded token cost; the gates are fast; the tool-surface walk uses real
round-trips.

#### 4.3 Constraints

See [§2.5](#25-design-and-implementation-constraints).

#### 4.4 Assumptions

| ID | Assumption | Risk if invalid |
|----|------------|-----------------|
| A-01 | The canonical `entity-crud/DESIGN.md` structure is the agreed target shape. | The mandatory section set in FR-11 would be wrong. (Mitigated: scope settled in design conversation + canonical research.) |
| A-02 | The #98 verification substrate can already drive tool calls (scripted `http_call`/`subprocess` + agent-step). | FR-14 would need new driver work. (Confirmed: `driver_for_step`, `http_call` driver present in `sulis-verify-acceptance`.) |
| A-03 | Every behavioural change has at least one tool surface OR is explicitly exempt (pure docs/infra). | A change with neither UI nor tool surface would mis-fire the two-surface walk. (Mitigated: exemption path retained from #85.) |
| A-04 | Producing the comprehensive document at lite depth does not exceed acceptable token cost. | FR-01 would be too expensive to be always-on. (Bounded by NFR; see NFR.md.) |

#### 4.5 Dependencies

| Dependency | Type | Status | Classification |
|------------|------|--------|----------------|
| #98 verification substrate (scripted + agent-step driving) | Internal | Ready | Consume |
| #85 UI journey walk (draft-architecture step 8.5) | Internal | Ready | Extend |
| #103 scenario-required gate | Internal | Ready | Compose (companion) |
| #86 journey-coverage gate | Internal | Ready | Compose (companion) |
| `_specify_classifier.py` | Internal | Ready | Modify (semantics) |
| requirements-templates / TDD template | Internal | Ready | Restructure |
| Canonical `entity-crud/DESIGN.md` target | External (platform repo) | Ready | Reference |

#### 4.6 STRIDE Threat Model

The system under specification is a *methodology pipeline*; its "attackers" are
the **bypasses** by which a change advances while skipping the discipline. Full
treatment is in [MISUSE_CASES.md](MISUSE_CASES.md). Summary STRIDE table:

| Category | Threat (against the methodology) | Applicable? | Mitigation | Status |
|----------|----------------------------------|-------------|------------|--------|
| **S**poofing | A change claims a hop EXISTS that is not actually wired (false EXISTS). | Yes | EXISTS requires cited file+function; tool EXISTS requires the ServiceSpec binding too (FR-09). | Mitigated |
| **T**ampering | A flow is silently dropped so no scenario is required for it. | Yes | UC-flow-coverage gate enumerates ALL flows; an uncovered flow ⇒ `gaps` (FR-12). | Mitigated |
| **R**epudiation | A business decision (scope cut) is made with no record. | Yes | BDR captures business decisions (FR-17). | Mitigated |
| **I**nformation disclosure | N/A — methodology produces design docs, no sensitive runtime data. | N/A | Founder English already strips internal IDs from founder-facing output. | N/A |
| **D**enial of service | The always-comprehensive document makes specify so slow/expensive founders skip it. | Yes | Bounded token cost (NFR); depth still sizes the interview to keep small changes light. | Mitigated |
| **E**levation of privilege | A change skips the design stage entirely (no walk, no scenarios). | Yes | Gates are companions and run on every behavioural change; pure-docs exemption is explicit + recorded. | Mitigated |

Trust boundary (methodology terms): the boundary is between the **founder's
stated intent** (untrusted-for-completeness — they may not know what to ask for)
and the **produced comprehensive document** (the trusted, complete record). The
agent's job is to cross that boundary by always producing the full document, so
completeness does not depend on the founder thinking to ask for it.

---

### 5. System Features

#### 4.1 Always-Comprehensive Design Document [F-01]

Every behavioural change produces the full document (FR-01, FR-02, FR-11). Depth
sizes the interview only.

#### 4.2 Two-Surface Journey Walk [F-04, F-05]

The design stage walks the UI surface (FR-07) and the tool surface (FR-08, FR-09)
outside-in; each hop EXISTS/planned-WP/GAP; a bare GAP blocks.

#### 4.3 UC-Derived Scenarios + Coverage Gate [F-06, F-07]

Scenarios are derived from every UC flow for both surfaces (FR-10), driven via
#98 (FR-14), and a UC-flow-coverage gate enforces completeness (FR-12, FR-13).

#### 4.4 Rounded-Out Document [F-08, F-09, F-10]

Always-on STRIDE threat model (FR-15), architecture-at-levels (FR-16), BDR
alongside ADR (FR-17).

---

## 6. Use Cases

The two actors are the **founder** and the **Sulis agent**. Use cases below
carry main, alternate, and exception flows. Each flow is the source of one or
more verifiable scenarios (see [scenarios](#7-scenario-derivation)).

### UC-01: Founder specifies a user-facing change at lite depth

**Actor:** Founder
**Description:** A founder runs `/sulis:specify` on a small user-facing change and receives a comprehensive design document despite the small intake.
**Trigger:** Founder runs `/sulis:specify` on a change classified lite by the depth classifier.

**Preconditions:**
- A change exists (worktree present).
- The change touches a behavioural surface (not pure docs/infra).

**Main Flow:**
1. Founder runs `/sulis:specify`.
2. Agent classifies intake depth = lite (deterministic).
3. Agent proposes the interview size in founder English ("a few quick questions"), not doc thinness.
4. Founder answers the (short) interview.
5. Agent produces the comprehensive design document with ALL mandatory sections (FR-11) — use cases with flows, NFR with measurable targets, personas, scope, problem discovery, threat model.
6. Founder sees a complete document.

**Alternate Flows:**
- **2a.** Depth classifies standard or deep: interview is longer; the SAME section set is produced (FR-02).
- **3a.** Founder overrides the proposed depth: interview resizes; doc-existence unchanged.

**Exception Flows:**
- **5a.** A mandatory section cannot be populated from the (short) intake: the agent marks it with an explicit `n/a — <justification>` or an open question, never a silent omission.
- **5b.** Token budget for the always-comprehensive document is exceeded: the agent degrades section *detail* (per NFR bound), never section *existence*.

---

### UC-02: Agent produces the comprehensive document regardless of depth

**Actor:** Sulis agent
**Description:** The agent emits a document whose section set is independent of depth.
**Trigger:** The specify/design stage reaches document production for any behavioural change.

**Preconditions:**
- Depth has been classified (lite/standard/deep).
- The intake (sized by depth) has completed.

**Main Flow:**
1. Agent reads the target structure (FR-11).
2. Agent produces every mandatory section in order.
3. Agent populates section detail from the depth-sized intake.
4. Agent writes the document.

**Alternate Flows:**
- **3a.** Intake was lite: detail is lighter but every section is present.
- **3b.** Intake was deep: detail is richer; section set is identical.

**Exception Flows:**
- **2a.** A doc-emission branch is found to be gated on `classify_depth` output: this is a defect (violates FR-03); the gate must be removed.
- **4a.** The produced document is missing a mandatory section: the design stage does not complete (P-VER + structure check block it).

---

### UC-03: Agent walks the UI surface journey outside-in

**Actor:** Sulis agent
**Description:** The agent walks the human consumer's path hop-by-hop, classifying each hop.
**Trigger:** Design stage step 8.5 begins for a change with a UI surface.

**Preconditions:**
- The change has a UI surface (not exempt).
- The journey's scenario set is enumerable from the brain.

**Main Flow:**
1. Agent pulls the journey's complete scenario set.
2. Agent walks each scenario's steps in order (first action → final observable result).
3. For every UI hop, agent cites the handling component (file + function) ⇒ EXISTS, or names a planned WP ⇒ planned-WP, or finds neither ⇒ GAP.
4. Agent writes the UI `## Journey Walk` table.

**Alternate Flows:**
- **3a.** A hop crosses into a host-rendered surface (MCP App / extension): the sharper EXISTS bar applies (binding both sides + real-host round-trip).

**Exception Flows:**
- **3b.** A hop is a bare GAP (neither built nor planned): design completion is blocked until it becomes planned-WP or recorded out-of-scope.

---

### UC-04: Agent walks the API/MCP tool surface journey outside-in

**Actor:** Sulis agent
**Description:** The agent walks the MACHINE consumer's path — an agent/SDK calling the tools end-to-end — classifying each operation, with the ServiceSpec-binding bar.
**Trigger:** Design stage step 8.5 begins for a change with a tool surface.

**Preconditions:**
- The change exposes or consumes API/SDK/MCP tool operations.
- The journey's tool operations are enumerable.

**Main Flow:**
1. Agent identifies the machine consumer's path through the tool operations.
2. For each operation, agent cites the tool/handler AND its ServiceSpec binding ⇒ EXISTS.
3. An operation whose handler exists but ServiceSpec binding is absent ⇒ GAP (FR-09).
4. An operation with neither handler nor planned WP ⇒ GAP; with a planned WP ⇒ planned-WP.
5. Agent writes the tool-surface `## Journey Walk` table (second table).

**Alternate Flows:**
- **2a.** The operation is provided by an external system (Stripe, AWS): classified EXISTS by external-system reference, no local binding required.

**Exception Flows:**
- **3a.** A tool serves an interface but has no ServiceSpec binding ("looks-built-but-isn't-wired"): classified GAP; blocks completion.
- **5a.** No tool surface exists and the change is not pure-docs/infra: the agent surfaces this as a gap in surface coverage (a behavioural change should have at least one walkable surface).

---

### UC-05: Agent derives verifiable scenarios from use-case flows for both surfaces

**Actor:** Sulis agent
**Description:** Every UC flow becomes at least one drivable, observable scenario, on the appropriate surface.
**Trigger:** Use cases are specified and the design stage reaches scenario derivation.

**Preconditions:**
- Use cases with main/alternate/exception flows exist.
- The verification substrate (#98) is available.

**Main Flow:**
1. Agent enumerates every flow (main + alternate + exception) of every in-scope use case.
2. For each flow, agent authors at least one scenario, tagged with its surface (UI or tool).
3. UI scenarios drive the screen; tool scenarios carry a real driver (`http_call`/`subprocess`/agent-step).
4. Agent emits each scenario via `sulis-author-scenario` into the brain.

**Alternate Flows:**
- **2a.** A flow maps to scenarios on BOTH surfaces (same behaviour exercised by human and machine): two scenarios are authored.

**Exception Flows:**
- **2b.** A flow has no observable check possible: `sulis-author-scenario` rejects the unverifiable journey; the agent reworks the flow until it has an observable outcome.
- **3a.** A tool scenario cannot be driven for real yet (no sandbox/credentials): it is recorded as an infrastructure need (deferred), not silently dropped.

---

### UC-06: Founder ships a change; the UC-flow-coverage gate blocks if a flow has no covering scenario

**Actor:** Founder (with the Sulis agent running the gate)
**Description:** A change cannot ship while a use-case flow has no covering scenario.
**Trigger:** Founder runs the ship/review gate on a change.

**Preconditions:**
- The change has specified use cases with flows.
- Scenarios have been authored (or not).

**Main Flow:**
1. Founder initiates ship/review.
2. Agent runs the UC-flow-coverage gate: for every flow, is there a covering scenario?
3. Agent also runs the scenario-required gate (#103) and journey-coverage gate (#86).
4. All flows covered + all gates pass ⇒ verdict `covered`; change may ship.

**Alternate Flows:**
- **2a.** A flow is consciously out-of-scope: recorded as out-of-scope (never silently dropped); the gate treats it as covered-by-decision.

**Exception Flows:**
- **2b.** A flow has no covering scenario and no out-of-scope record ⇒ verdict `gaps`; the gate BLOCKS the ship. The agent reports the uncovered flow in plain English.
- **3a.** A scenario exists but only covers the happy path (main flow), leaving an exception flow uncovered ⇒ the gate flags the uncovered exception flow as a gap (closes the happy-path-only bypass).

---

## 6.1 Negative Requirements (per use case)

| ID | Negative requirement | Source |
|----|----------------------|--------|
| NR-01 | The system MUST NOT skip any mandatory document section based on depth. | UC-02 / MUC-01 |
| NR-02 | The system MUST NOT classify a tool hop EXISTS when the ServiceSpec binding is absent. | UC-04 / MUC-02 |
| NR-03 | The system MUST NOT pass the coverage gate when any UC flow (incl. alternate/exception) lacks a covering scenario or out-of-scope record. | UC-06 / MUC-03, MUC-04 |
| NR-04 | The system MUST NOT walk only one surface for a behavioural change that has both. | UC-03/UC-04 / MUC-05 |
| NR-05 | The system MUST NOT drop a use-case flow silently; an out-of-scope flow MUST be recorded. | UC-06 / MUC-04 |
| NR-06 | The system MUST NOT mark a tool scenario green without a real driven round-trip (observed-or-blocked). | UC-05 / MUC-06 |

---

## 7. Scenario Derivation

Every use-case flow yields at least one verifiable scenario. The full set is in
[`.changes/harden-comprehensive-spec-and-journey-walk.scenarios.jsonld`](../../.changes/harden-comprehensive-spec-and-journey-walk.scenarios.jsonld).
Coverage matrix (flow → scenario → surface):

| UC | Flow | Scenario | Surface | Drives |
|----|------|----------|---------|--------|
| UC-01 | main | SC-01 always-comprehensive-at-lite | tool | `/sulis:specify` lite ⇒ doc has all sections |
| UC-01 | 2a (standard/deep) | SC-02 same-section-set-across-depths | tool | three depths ⇒ identical section set |
| UC-01 | 5a (n/a marking) | SC-03 unpopulated-section-marked-na | tool | thin intake ⇒ explicit n/a, no silent omission |
| UC-02 | 2a (doc gated on depth = defect) | SC-04 no-doc-branch-on-depth | tool | inspect: no emission branches on `classify_depth` |
| UC-02 | main | SC-05 nfr-always-on | tool | produced doc has measurable NFR section |
| UC-03 | main | SC-06 ui-walk-classifies-all-hops | UI | UI walk table classifies every hop |
| UC-03 | 3b (bare GAP blocks) | SC-07 ui-bare-gap-blocks | UI | a UI GAP ⇒ design incomplete |
| UC-04 | main | SC-08 tool-walk-second-table | tool | tool-surface walk table present + complete |
| UC-04 | 3a (binding absent ⇒ GAP) | SC-09 tool-no-binding-is-gap | tool | handler w/o ServiceSpec binding ⇒ GAP |
| UC-05 | main | SC-10 every-flow-has-scenario | tool | each UC flow ⇒ ≥1 scenario |
| UC-05 | 3a (deferred infra) | SC-11 undrivable-tool-recorded-deferred | tool | undrivable tool scenario ⇒ recorded deferred |
| UC-06 | main | SC-12 all-flows-covered-passes | tool | full coverage ⇒ verdict covered |
| UC-06 | 2b (uncovered ⇒ block) | SC-13 uncovered-flow-blocks | tool | one uncovered flow ⇒ verdict gaps |
| UC-06 | 3a (happy-path-only) | SC-14 happy-path-only-flagged | tool | exception flow uncovered ⇒ gap |
| FR-15 | threat model always-on | SC-15 stride-section-present | tool | produced doc has STRIDE section |
| FR-16 | architecture-at-levels | SC-16 c4-three-levels-present | tool | doc has context+container+component diagrams |
| FR-17 | BDR alongside ADR | SC-17 bdr-recorded-distinct-from-adr | tool | a business decision ⇒ BDR, distinct from ADR |

---

## 8. Diagrams

| Diagram | File | Shows |
|---------|------|-------|
| Use cases | [diagrams/use-cases.md](diagrams/use-cases.md) | Founder/agent actor-goal relationships |
| Process flows | [diagrams/process-flows.md](diagrams/process-flows.md) | The decoupled depth→intake flow; the gate flow |
| Sequence | [diagrams/sequence-diagrams.md](diagrams/sequence-diagrams.md) | Two-surface walk + scenario driving |
| State | [diagrams/state-diagrams.md](diagrams/state-diagrams.md) | Hop classification + flow-coverage lifecycle |
| Data flow | [diagrams/data-flows.md](diagrams/data-flows.md) | Intake/depth/document/scenario/brain data movement |
| Architecture-at-levels | [diagrams/architecture-at-levels.md](diagrams/architecture-at-levels.md) | C4 context/container/component for the methodology pipeline |

---

## 9. Traceability Matrix

| Goal | Use Cases | FRs | Scenarios | NFRs | Misuse |
|------|-----------|-----|-----------|------|--------|
| Always-comprehensive doc | UC-01, UC-02 | FR-01..FR-06, FR-11 | SC-01..SC-05 | NFR-01, NFR-02 | MUC-01 |
| Two-surface walk | UC-03, UC-04 | FR-07, FR-08, FR-09 | SC-06..SC-09 | NFR-04 | MUC-02, MUC-05 |
| UC-derived scenarios + gate | UC-05, UC-06 | FR-10, FR-12, FR-13, FR-14 | SC-10..SC-14 | NFR-03 | MUC-03, MUC-04, MUC-06 |
| Rounded-out doc | UC-02 | FR-15, FR-16, FR-17 | SC-15..SC-17 | NFR-02 | MUC-01 |

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

### What user-observable behaviour are we verifying?

We are verifying that the Sulis specify/design process, when driven on a sample
behavioural change, (a) produces a comprehensive design document containing every
mandatory section *regardless of the depth chosen*, (b) walks BOTH the UI surface
and the tool surface outside-in with every hop classified, (c) derives a
verifiable scenario from every use-case flow on both surfaces, and (d) blocks the
change at the coverage gate when any flow has no covering scenario. A founder
observes a complete document for a tiny change; an agent observes both journey
tables and a `covered`-or-`gaps` verdict that responds correctly to a deliberately
uncovered flow.

### Verification environment(s)

- **Local dev / CI** — drive `/sulis:specify` + `/sulis:draft-architecture` on a
  fixture change in a scratch worktree; assert the produced document's section set,
  both journey-walk tables, and the gate verdict. Deterministic; no external creds.
- **Dev tier** — drive a tool-surface scenario for real against a running Sulis
  tool endpoint via the #98 substrate, to confirm tool scenarios are observed-or-blocked.
- Difference: local/CI proves *structure + gate logic*; dev tier proves the
  tool-surface scenarios actually drive a real round-trip.

### Bootstrap-from-zero case

A fresh clone with no prior change: the verification creates a fixture change
(worktree + manifest), runs specify at depth=lite, and asserts the comprehensive
document is produced from zero intake context. Seed data: the fixture change
manifest (primitive, slug, one user-facing path so the surface heuristic fires).
Credentials: none for the structure/gate checks; a dev-tier tool credential only
for the real tool-drive check (SC-08/SC-09 real-drive variant). Configuration:
the sulis plugin installed; `SCRIPTS_DIR` resolvable.

### Per-integration verification strategy

| Integration | Approach | Classification |
|-------------|----------|----------------|
| Depth classifier (`_specify_classifier.py`) | Real — call `classify_depth`; assert depth never gates doc-existence | existing |
| #98 verification substrate (`sulis-verify-acceptance`) | Real — drive a tool scenario; observe round-trip | existing |
| Scenario coverage (`_verify_scenario_coverage.py`) | Real — feed a journey with one uncovered flow; assert `gaps` | existing |
| Brain instance store | Real — author scenarios; read them back via `_brain_query` | existing |
| Canonical `entity-crud/DESIGN.md` target | Reference only — compare produced section set against it | out-of-scope (read-only reference) |
| Tool endpoint (dev tier, real call) | Real where credentials exist; recorded otherwise | deferred (sandbox-dependent) |

### Per-kind verification adapter

This change's `kind` is **methodology**. Per the canonical per-kind adapter:
methodology changes are verified by driving the methodology stage on a fixture
input and asserting the produced *artifacts and gate verdicts* match the
specification — not by deploying a service. The adapter row: drive
specify/design on the sample change; assert the comprehensive document section
set, both journey-walk tables, the scenario set per flow, and the
covered/gaps verdict under both a fully-covered and a deliberately-uncovered
fixture.

### Infrastructure needs surfaced (deferred)

- `tool-drive-sandbox` — a dev-tier tool endpoint + credential so tool-surface
  scenarios (SC-08, SC-09 real-drive variant) can be driven for real in CI, not
  only attested. Until present, those scenarios verify structure locally and are
  driven on dev tier ad hoc.
- `methodology-fixture-change` — a reusable fixture change (worktree + manifest)
  the verification can spin up from zero; reduces per-run setup. Singleton need;
  surface to founder for defer-or-draft at slice end.
