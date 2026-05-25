# Exploration Journal: Primitive Tree Architecture

**Date:** 2026-03-16
**Goal:** Specify the evolution of the SRD plugin's codebase mapping and facilitation model from a flat index into a structured primitive tree that drives question generation, gap detection, and artifact production.
**User:** Repo owner with deep understanding of the SRD plugin architecture. Clearly experienced in systems analysis — framing uses concepts like "decomposition," "primitives," "building blocks," and a layered interaction model. Calibrated at Level 3.

## Initial Assessment

**Scope:** Evolution of an existing system (the SRD plugin in this repo). Not greenfield — the current architecture exists in `srd/agents/requirements-analyst.md` and `srd/skills/`.

**Key context from prior conversation:**
- The user has a three-layer interaction model already articulated
- The core insight is that the LLM brings expertise the user doesn't have — the tree is not a blank checklist
- Codebase mapping evolves from flat index to structured decomposition
- Gaps in the tree become the questions the agent asks
- The tree drives artifact generation — SRD is a rendering of the tree

**What's clear:** The conceptual model (tree of primitives, gap-driven questioning, tree-to-artifact rendering)
**What needs exploration:** The tree structure itself, what constitutes a "primitive," how the tree interacts with the existing six-phase facilitation model, how it changes the codebase-mapping skill, state management across sessions

---

## Exchange Log

### Turn 1 (Phase 2 — Divergent Exploration)
**Domain:** Capabilities & Use Cases / Data
**Question:** What does the tree structure look like? Are primitives SA&D primitives or domain capabilities?
**Key points:**
- The SA&D primitives (S1-S7, A1-A7) are the agent's own methodology — how it analyses
- The tree is about the *target project's* domain-specific building blocks, not the SRD's own structure
- The agent decomposes the target codebase into domain primitives (e.g., "order management needs: data model, state lifecycle, payment integration, notifications")
**Patterns:** Two-layer primitive model: methodology primitives (SA&D) vs. domain primitives (target project)
**Coverage:** Capabilities strong, Actors thin, Business Rules untouched, Integrations emerging, Process/Workflow emerging, Constraints untouched

### Turn 2 (Phase 2 — Divergent Exploration)
**Domain:** Capabilities & Use Cases / Integrations
**Question:** Where does the decomposition knowledge come from? Is it LLM training or something more structured?
**Key points:**
- LLM training knowledge drives the decomposition — it recognises the domain and projects expected shape
- Codebase inventory tells it what already exists
- Delta between expected shape and existing pieces = gaps in the tree
**Patterns:** Knowledge synthesis: LLM domain expertise + codebase evidence = tree structure
**Coverage:** Capabilities strong, Data source for tree clear

### Turn 3 (Phase 2 — Divergent Exploration)
**Domain:** Process & Workflow
**Question:** How does the tree relate to the existing six-domain exploration model? Replace or restructure?
**Key points:**
- Tree provides targeting for the OODA spiral (not loop — iterative passes that tighten understanding)
- Six domains remain as analytical lens
- Tree tells the agent where to focus — which gaps to observe, orient on, decide about, act on
- Restructures exploration, doesn't replace it
**Patterns:** OODA spiral: iterative passes through tree gaps, each pass applying six-domain lens with increasing precision
**New glossary terms:** OODA spiral (vs. loop), domain primitive, primitive tree
**Coverage:** Process/Workflow strong on the facilitation model. Still thin: Actors (who interacts with the tree?), Business Rules (what governs tree construction?), Constraints (NFRs for the tree itself)

### Turn 4 (Phase 2 — Divergent Exploration)
**Domain:** Process & Workflow / Data
**Question:** Is the tree built once upfront or does it evolve during facilitation?
**Key points:**
- The tree is a living structure — reshaped as facilitation progresses
- User confirms, corrects, extends; branches get pruned or added
- Each OODA spiral pass operates on the current shape, not the original
- Tree lifecycle: starts as hypothesis (LLM + codebase), converges toward ground truth via user input
**Patterns:** Living document pattern — the tree has its own lifecycle across the session

### Turn 5 (Phase 2 — Divergent Exploration)
**Domain:** Data / Process & Workflow
**Question:** Is the tree a persisted artifact or internal working state?
**Key points:**
- Persisted artifact — lives in `.specifications/` folder
- Updated as facilitation progresses
- User-inspectable (transparency)
- Survives across sessions (continuity)
- Serves triple role: agent working model, user transparency artifact, session continuity mechanism
**Patterns:** Tree replaces/extends CODEBASE_INDEX.json as the primary structured representation
**New glossary terms:** Primitive tree (persisted artifact)
**Coverage:** Data strong (persistence, format emerging). Process/Workflow strong. Still thin: Actors, Business Rules (what governs decomposition quality?), Constraints (tree size limits? depth limits?), Integrations (how does tree relate to existing CODEBASE_INDEX.json?)

### Turn 6 (Phase 2 — Divergent Exploration)
**Domain:** Integrations & Data
**Question:** How does the tree relate to the existing CODEBASE_INDEX.json? Replace, layer, or merge?
**Key points:**
- Layered model: codebase-mapping skill still produces flat CODEBASE_INDEX.json (raw evidence)
- New synthesis step reads index and produces PRIMITIVE_TREE.json (structured interpretation)
- Both persist as artifacts — evidence and interpretation separated
- Pipeline: (1) codebase mapping → CODEBASE_INDEX.json, (2) synthesis → PRIMITIVE_TREE.json, (3) tree drives facilitation
**Patterns:** Evidence/interpretation separation — debuggable, auditable

### Turn 7 (Phase 2 — Divergent Exploration)
**Domain:** Data / Capabilities
**Question:** What does a tree node look like? What properties does it have?
**Key points:**
- Starting node structure: name, type (system/capability/primitive), status (exists/partial/gap), evidence (links to codebase index), confidence
- User explicitly said "to begin with" — evolvable, don't over-specify
- Three-level type hierarchy: system → capability → primitive
- Status captures the delta between expected and actual
**Patterns:** Minimal viable schema — start simple, evolve with use

---

## Coverage Assessment (after Turn 7)

| Domain | Coverage | Key Findings |
|--------|----------|-------------|
| Actors & Stakeholders | Thin | Who are the actors? The user, the agent, the execution agent who reads artifacts. Not yet explored. |
| Capabilities & Use Cases | Strong | Core capabilities clear: tree construction, tree-driven facilitation, tree evolution, tree-to-SRD rendering. |
| Business Rules & Logic | Thin | What governs decomposition quality? How does the agent decide tree depth? What makes a "good" tree? |
| Integrations & Data | Strong | Layered model clear (index → tree), node structure defined, persistence model established. |
| Process & Workflow | Strong | OODA spiral model, tree lifecycle (hypothesis → ground truth), six-domain lens preserved. |
| Constraints & NFRs | Untouched | No discussion of tree size limits, depth, performance, greenfield handling, error cases. |

**Saturation signal:** Last 2 turns confirmed rather than introduced new concepts. Core model is solid. Remaining gaps are in actors, business rules, and constraints.

### Turn 8 (Phase 2 — Divergent Exploration)
**Domain:** Capabilities & Use Cases / Data
**Question:** How does the tree change artifact generation? (Initial phrasing too abstract — rephrased with e-commerce example)
**Key points:**
- Tree is an INPUT to artifact generation, not the source of content
- Conversation remains primary source for SRD content
- Tree provides structure and completeness checking — ensures all identified capabilities are covered in artifacts
- User explicitly invited challenge on this point
**Patterns:** Separation of concerns: tree = structure/completeness, conversation = content

### Turn 9 (Phase 2 — Divergent Exploration)
**Domain:** Capabilities & Use Cases
**Question:** How does the tree handle greenfield projects with no codebase?
**Key points:**
- Tree still created for greenfield projects
- Built from user description alone (no codebase evidence)
- All nodes start with status "gap"
- Same facilitation model applies — tree just starts emptier
**Patterns:** Graceful degradation — tree works across the codebase/no-codebase spectrum

### Turn 10-12 (Phase 2 — Divergent Exploration)
**Domain:** Capabilities & Use Cases / Process & Workflow
**Question:** How is the tree presented to users during facilitation?
**Key points:**
- Agent DOES surface the tree during facilitation
- Rendered as human-friendly exec summary, not raw JSON
- "Straight to the point, crystal clear" — shows what's covered, what's left
- Plain language presentation, structured around progress and gaps
- User never interacts with the JSON structure directly
**Patterns:** Abstraction layer between internal representation and user-facing presentation
**Coaching:** Suppressed — Level 3 user, no significant gaps

---

## Coverage Assessment (after Turn 12)

| Domain | Coverage | Key Findings |
|--------|----------|-------------|
| Actors & Stakeholders | Thin | Who are the actors? The user, the agent, the execution agent who reads artifacts. Not yet explored in depth. |
| Capabilities & Use Cases | Strong | Core capabilities clear: tree construction, tree-driven facilitation, tree evolution, tree-to-artifact rendering, greenfield handling, user-facing presentation. |
| Business Rules & Logic | Thin | What governs decomposition quality? How does the agent decide tree depth? What makes a "good" tree? |
| Integrations & Data | Strong | Layered model clear (index → tree), node structure defined, persistence model established. |
| Process & Workflow | Strong | OODA spiral model, tree lifecycle (hypothesis → ground truth), six-domain lens preserved, presentation model clear. |
| Constraints & NFRs | Untouched | No discussion of tree size limits, depth, performance, error cases. |

**Saturation signal:** Turns 8-12 refined existing concepts (artifact generation role, greenfield handling, presentation). No major new concepts introduced. Core model is solid. Three domains still need coverage before transitioning to Phase 3.

### Turn 13 (Phase 2 — Divergent Exploration)
**Domain:** Actors & Stakeholders
**Question:** What role does the tree play for the execution agent / dev team? Audit trail or execution-useful artifact?
**Key points:**
- Tree is a first-class execution artifact, not just an audit trail
- Provides what the SRD doesn't: a dependency-aware map of what exists vs. what's new
- Complements the SRD — SRD is behavioural specification, tree is structural inventory
- Positioned in HANDOVER.md reading order explicitly
- Analogy: SRD = architectural drawings, tree = site survey showing existing foundations
**Patterns:** Complementary artifact pair — behavioural (SRD) + structural (tree)
**Coaching:** Suppressed — Level 3 user

### Turn 14 (Phase 2 — Divergent Exploration)
**Domain:** Business Rules & Logic
**Question:** What determines the right granularity for decomposition?
**Key points:**
- Granularity test = architectural relevance. "Would an architect put this on a whiteboard?"
- Primitives are domain objects, actions, components, integrations — building blocks that drive architectural design decisions
- Too shallow: single node that doesn't reveal what pieces are needed
- Too deep: implementation detail (individual fields, individual transitions, individual validation rules)
- Just right: enough specificity to drive design at an architectural level, not so much that you're designing the implementation
- Implies leaf-level node types should be more specific than generic "primitive" — they should reflect the kind of architectural building block (domain object, action, integration, etc.)
**Patterns:** Architectural relevance as the granularity governing principle
**New glossary terms:** Architectural primitive (a domain building block at the level that drives design decisions)
**Coaching:** Suppressed — Level 3 user, user articulated the rule themselves

---

## Coverage Assessment (after Turn 14)

| Domain | Coverage | Key Findings |
|--------|----------|-------------|
| Actors & Stakeholders | Moderate | Three consumers identified (agent, facilitation user, execution agent). Roles clear. Could be deeper on execution agent's specific needs. |
| Capabilities & Use Cases | Strong | Core capabilities clear across all major features. |
| Business Rules & Logic | Moderate | Granularity rule established (architectural relevance). Node type taxonomy emerging. Still need: what makes a decomposition "wrong"? Error cases? |
| Integrations & Data | Strong | Layered model, node structure, persistence, presentation all clear. |
| Process & Workflow | Strong | OODA spiral, tree lifecycle, six-domain lens, presentation model all clear. |
| Constraints & NFRs | Thin | Tree scale management discussed (levelled decomposition, 7+/-2 fan-out, bounded context scoping). Concrete limits not yet specified. |

### Turn 15 (Phase 2 — Divergent Exploration)
**Domain:** Constraints & NFRs
**Question:** Is there a ceiling on tree size? How should the agent handle scale?
**Key points:**
- Discussed established conventions: Miller's 7+/-2 per level, levelled decomposition (DeMarco/Yourdon), WBS 3-7 fan-out with 3-4 levels, DDD bounded contexts for scoping
- User asked for best practice guidance — provided structured analysis methodology reference
- Three convergent rules: fan-out constraint per node, depth constraint (3-5 levels), scoping mechanism for large systems

### Turn 16 (Phase 2 — Divergent Exploration)
**Domain:** Integrations & Data / Business Rules
**Question:** N/A — user surfaced the tria project's existing PRIMITIVE_TREE implementation
**Key points — MAJOR NEW CONTEXT:**
- The tria project at /Users/iain/Documents/repos/platform/ has a MATURE primitive tree implementation
- primitive-decomposition outcome: produces PRIMITIVE_TREE.jsonld with Decomposition Quality Triad
- primitive-testing outcome: adversarial testing with dual-path (Scout/Tribunal), evidence-graded health_status transitions
- product-capability-decomposition: bridges primitives to buildable product capabilities
- Schema (PRIMITIVE_TREE_SCHEMA.jsonld v1.2.0): JSON-LD with typed nodes (value-proposition, revenue-model, channel, customer-segment, key-resource, key-activity, cost-structure), typed dependencies (depends-on, enables, conflicts-with), health statuses (untested → testing → validated | failed | accepted-as-risk), phases (validate → build → activate → operate → scale), attack patterns and kill signals per type, open vocabulary for custom types
- CRITICAL DISTINCTION: tria primitives are BUSINESS MODEL building blocks (Osterwalder ontology). SRD primitives are SOFTWARE ARCHITECTURE building blocks (domain objects, actions, components). Same structural pattern, different domain.
- The user is describing adapting this proven pattern for software domain decomposition
**Patterns:** Pattern reuse across domains — the tree structure, dependency typing, health status lifecycle, and testing model transfer. The domain vocabulary changes but the mechanics don't.
**New glossary terms:** Business primitive (tria), Software/architectural primitive (SRD), DAG (directed acyclic graph)

**Key schema elements that likely transfer directly:**
- DAG structure (not strict tree — dependencies create cross-links)
- Dependency types: depends-on, enables, conflicts-with
- Health status lifecycle: untested → testing → validated | failed | accepted-as-risk
- Open vocabulary with extensible node types
- Phase ordering for progressive testing/validation
- Attack patterns and kill/invalidation signals per node type

**Key schema elements that need domain adaptation:**
- Node types: from Osterwalder (value-proposition, revenue-model, etc.) to software architecture (domain-object, action, component, integration, state-machine, etc.)
- Phases: from business lifecycle (validate → build → activate → operate → scale) to... what? Requirements lifecycle? Implementation phases?
- Attack patterns: from business model attack vectors to software architecture attack vectors
- Function affinity: from business functions (blueprint, product, marketing) to... SRD artifact types?
- Success criteria: from business measurables to architectural/requirements measurables

---

## Coverage Assessment (after Turn 16)

| Domain | Coverage | Key Findings |
|--------|----------|-------------|
| Actors & Stakeholders | Moderate | Three consumers clear. Tria adds context: triads (Architect, Independence Validator, Completeness Assessor) — does the SRD agent play all roles? |
| Capabilities & Use Cases | Strong | Core capabilities clear. Tria context enriches: decomposition quality triad, testing model, capability bridging are proven patterns. |
| Business Rules & Logic | Strong | Granularity rule + tria schema provides the structural template. Key remaining question: what are the SOFTWARE-SPECIFIC node types? |
| Integrations & Data | Strong | Layered model + tria schema (JSON-LD, DAG, typed dependencies) provides proven data model. |
| Process & Workflow | Strong | OODA spiral + tria's topological ordering and dual-path testing provide process depth. |
| Constraints & NFRs | Thin | Scale management discussed but not specified. Tria's batch mode (8 primitives advisory max) provides reference. |

**TRANSITION SIGNAL:** The tria context is a major new concept that reshapes the specification significantly. We now have a proven pattern to adapt rather than designing from scratch. All six domains have at least moderate coverage. The remaining work is convergent: specifying exactly how the tria pattern adapts for software domain decomposition.

### Turn 17 (Phase 2 — Divergent Exploration)
**Domain:** Business Rules & Logic
**Question:** Is there an established framework providing a bounded vocabulary of software architecture node types, or do we need a composite?
**Key points:**
- No single framework maps cleanly — C4 focuses on zoom levels, DDD on domain patterns, structured analysis on data/process
- Composite vocabulary drawn from all three: 7 node types confirmed
- domain-entity, action, integration, data-store, state-machine, policy, event
- These are "the things an architect puts on a whiteboard" — the granularity test applied
- Tria's open vocabulary extensibility model carries over — custom types allowed, promoted to standard after repeated use
**Patterns:** Composite ontology — drawing from multiple established frameworks to cover the software architecture domain
**Coaching:** Suppressed — Level 3 user

### Turn 18 (Phase 2 — Divergent Exploration)
**Domain:** Business Rules & Logic
**Question:** Confirmation of the 7-type vocabulary with open extensibility
**Key points:**
- User confirmed the composite: domain-entity, action, integration, data-store, state-machine, policy, event
- Tria's extensibility model (custom type with declared category, promotion after 10+ uses) transfers directly
- User said to continue facilitation
**Coaching:** Suppressed — Level 3 user

### Turn 19 (Phase 2 → Phase 3 transition)
**Domain:** Process & Workflow
**Question:** Should the tree's `phase` property map to facilitation phases or implementation priority?
**Key points:**
- User chose facilitation phases over implementation priority
- Reasoning: "there is already a well understood set of stages software needs to follow to get to value"
- Phases should map to natural stages of software requirements facilitation/specification
- Implementation ordering is a known, separate concern — doesn't need to be encoded in the tree
- This means: the phase tells the agent WHEN during facilitation a node becomes relevant, not when it should be built
**Patterns:** Separation of concerns — facilitation ordering vs. implementation ordering
**Coaching:** Suppressed — Level 3 user

---

## Coverage Assessment (after Turn 19)

| Domain | Coverage | Key Findings |
|--------|----------|-------------|
| Actors & Stakeholders | Moderate | Three consumers clear (agent, user, execution agent). Roles defined. |
| Capabilities & Use Cases | Strong | Full capability set mapped including tria pattern transfer. |
| Business Rules & Logic | Strong | Node type vocabulary confirmed (7 types + open extensibility). Granularity rule established. |
| Integrations & Data | Strong | Layered model, DAG structure, typed dependencies, health statuses all specified via tria transfer. |
| Process & Workflow | Strong | OODA spiral, tree lifecycle, phase property mapped to facilitation stages. |
| Constraints & NFRs | Moderate | Scale management discussed (fan-out ≤7, depth 3-5, bounded contexts). Concrete limits pending. |

**PHASE TRANSITION:** Moving to Phase 3 (Convergent Specification). Saturation confirmed — last 3 turns refined/confirmed concepts. All domains at moderate or above.

### Turn 20 (Phase 3 — Convergent Specification)
**Domain:** All — convergent synthesis
**Question:** Facilitation phase vocabulary — what are the actual phase names?
**Key points:**
- Proposed 5 phases: discover, define, connect, constrain, verify
- User confirmed the mapping
- Phases parallel tria's 5 business lifecycle phases structurally, but domain is completely different
- Each phase makes different node types relevant as natural candidates for OODA selection

### Turn 21 (Phase 3 — Convergent Specification)
**Domain:** All — convergent synthesis of 7 remaining items
**Question:** Drafted complete convergent specifications for: per-node-type properties, attack patterns/invalidation signals, health status adaptation, tree synthesis process, exec summary format, gap-driven question selection, common properties adaptation
**Key points:**
- User reviewed all 7 convergent specifications and approved: "please proceed"
- Per-node-type properties follow tria convention: definition + success_criterion + health_status as universal, type-specific properties capture what makes each type distinct
- Attack patterns adapted from business model testing to specification completeness testing
- Health status transitions adapted from desk research evidence to facilitation conversation evidence
- Three-tier evidence grading: STRONG (codebase), FAIR (user), WEAK (inferred) — parallels tria's STRONG/FAIR/WEAK
- OODA scoring formula made explicit: (fan_out * 3) + (invalidations * 2) + (phase_match * 1) + (low_confidence * 1)
- Exec summary format specified: grouped by status, max 20 nodes, ends with next target
- artifactAffinity replaces functionAffinity; source replaces contentProduction

---

## Coverage Assessment (Final — after Turn 21)

| Domain | Coverage | Key Findings |
|--------|----------|-------------|
| Actors & Stakeholders | Strong | Three actors fully specified: SRD Agent, Facilitation User, Execution Agent. Roles, interactions, and goals clear. |
| Capabilities & Use Cases | Strong | 8 use cases covering synthesis, facilitation, evolution, rendering, verification, artifact generation, handover. All with flows. |
| Business Rules & Logic | Strong | 17 business rules. Node type schema with 7 types, 3 attack patterns and 3 invalidation signals each. Evidence grading. Scoring formula. |
| Integrations & Data | Strong | Layered pipeline (index → tree → conversation → artifacts). Data flows specified. JSON-LD format. |
| Process & Workflow | Strong | 4 process flows. 2 state machines. OODA spiral fully specified. Phase progression defined. |
| Constraints & NFRs | Strong | 17 NFRs across 5 categories. All measurable with specific targets and measurement methods. |

**STATUS:** Artifact generation complete. All 6 domains at strong coverage. Proceeding to completeness verification and handover.
