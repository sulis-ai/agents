# VERIFICATION_REPORT.md — sulis:add-agent

**Skill:** `plugins/sulis/skills/add-agent`
**Iteration:** 1 (first run — Greenfield mode)
**Produced:** 2026-05-25
**Methodology:** `sulis:add-skill` v0.7.0 applied to author add-agent

---

## Spiral Summary

**Tier:** heavy
**Template base:** HEAVY_TIER_DEFAULT
**Iterations used:** 1
**Termination reason:** sufficient (all thresholds met on first iteration)
**Verdict:** PASS

**Publication decision:** APPROVED

---

## Gate 1 — Find (BI / SI / CC + Primitive Discovery)

**BRIEF_PACK generated:** ran `python3 plugins/sulis/skills/add-agent/scripts/inventory.py --marketplace-root . --target-plugin sulis --target-agent change-classifier ...` as a smoke test of the script while authoring; confirmed it produces a well-formed Markdown output covering 13 agents across 11 plugins.

**BI counter-search performed:** yes
- Searched for "existing agent-authoring methodology" in the marketplace — none found (add-agent is the first)
- Searched for "could this be a skill instead?" — answer: no, agents are structurally different from skills (single-file artifact, dispatch contract as load-bearing description, register state)
- Searched for "what makes agents different" — found three concentrated differences (Gate 2 register declaration, Gate 4 founder-mode perspectives, Gate 5 MUC-A1..A4) plus shared scaffolding with add-skill

**SI verification:** 8 standards cited (CRITICAL_THINKING / DECOMPOSITION / SPIRAL / STANDARDS_RUBRIC / REFERENTIAL_INTEGRITY / COACHING / TONE / Founder-Facing Conventions). All independent sources (no echo chamber).

**CC verdict on "no existing meta-skill covers this":** VALIDATED (5+ checks: marketplace skill list, add-skill body, sulis CHANGELOG, design doc reference, methodology.md absence of prior art)

**"Could this be a skill instead?" answered:** NO — agents need their own methodology because:

1. Dispatch contract is load-bearing (a skill's description is important; an agent's is critical — the parent agent routes based on it)
2. Agents carry register state across turns; skills produce one-shot output
3. The founder-mode evaluation perspectives (Coaching Delivery, Tone Conformance, Register Switch Correctness) require agent-specific scoring methods

### Primitive Discovery

**Level of analysis:** the five gates of agent authoring methodology

**Primitives identified:**

| Primitive | Provenance | Independence test | Termination test |
|---|---|---|---|
| Gate 1 Find | extracted (from add-skill v0.7.0) | PASS — independently changeable (BRIEF_PACK can evolve without affecting other gates) | PASS — further decomposition would make it sub-steps not separate primitives |
| Gate 2 Scope Lock | extracted + agent-specific extensions (register, tools, model, user_invocable, dispatch trigger) | PASS — independently changeable | PASS — terminating; further decomposition wouldn't change the next action |
| Gate 3 Generate | extracted (from add-skill) — agent shape conventions added | PASS | PASS |
| Gate 4 Evaluate | extracted + agent-specific perspectives (Coaching Delivery, Tone Conformance, Register Switch Correctness) | PASS | PASS |
| Gate 5 Adversarial Review | extracted + agent-specific misuse cases (MUC-A1..A4, MUC-R1..R3) | PASS | PASS |

**Dependencies:** sequential (Gate N+1 depends_on Gate N)

**Scale check (PD-02):** fan-out = 5 (gates) ≤ 7 ✓; depth = 2 (gates → sub-steps) ≤ 5 ✓

---

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Skill name | `add-agent` |
| Plugin home | `sulis` |
| Audience | founder-facing (the author is the founder; the skill produces founder-readable docs) |
| Category | Code Quality (methodology authoring) |
| Trigger condition | "Use when the user wants to author a new Claude Code agent in the Sulis marketplace, formalise an existing dispatch pattern as a published agent, deepen an existing agent ('upsurge'), or get methodology-driven quality consistency rather than ad-hoc agent.md authoring." |
| Standards-phase classification | input: [REFERENTIAL_INTEGRITY_STANDARD] / processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE] / output: [CRITICAL_THINKING_STANDARD, TONE_STANDARD, COACHING_STANDARD] |
| Verification tier | HEAVY (methodology skill; founder-visible verdict on agent quality) |
| Tool stack | none (this is a methodology skill; the only script is `inventory.py` for BRIEF_PACK generation) |
| Top-N gotchas | 8 gotchas — each grounded in either add-skill's existing gotchas (adapted for agents) or Independence Check sub-agent's findings |
| Related skills + agents | depends_on: add-skill + 8 standards + founder-facing-conventions; no agents directly dispatched |
| Depth modes | three modes (Greenfield default, Deepening, Standards-grounded re-author) — auto-detected via mode-detection heuristic |

**Vocabulary terms introduced:** 12 terms in the Vocabulary section (Gate, BRIEF_PACK, Dispatch trigger, Register, Dual register, MUC-A1..A4, MUC-R1..R3, Coaching Delivery, Tone Conformance, Register Switch Correctness, Dispatch trigger precision, VERIFICATION_REPORT.md)

---

## Gate 3 — Generate

**Files produced:**

- `plugins/sulis/skills/add-agent/SKILL.md` (~460 LOC)
- `plugins/sulis/skills/add-agent/references/methodology.md` (~150 LOC)
- `plugins/sulis/skills/add-agent/references/agent-shape-conventions.md` (~225 LOC)
- `plugins/sulis/skills/add-agent/references/founder-mode-perspectives.md` (~250 LOC)
- `plugins/sulis/skills/add-agent/templates/agent.md.template` (~95 LOC)
- `plugins/sulis/skills/add-agent/templates/VERIFICATION_REPORT.md.template` (~280 LOC)
- `plugins/sulis/skills/add-agent/scripts/inventory.py` (~330 LOC)

**Scope lock adherence:** all 12 Gate 2 items reflected in the SKILL.md and supporting files. No drift detected.

**Frontmatter validation:**

- `standards:` block present + parses ✓
- `verification_spiral:` block present + parses (HEAVY tier with 2 custom dimensions) ✓
- `related_skills:` block present + parses ✓
- `register:` block present (founder_mode + technical_mode shapes) ✓

**Pyramid structure:** SKILL.md leads with "## Conclusion (Pyramid Principle — lead with the answer)" stating the five-gate methodology + three modes before the gate details ✓

**Linguistic audit (NH-02 + TONE T-05):** zero prohibited terms detected ✓
- Manually scanned for "comprehensive", "robust", "powerful", "magic", "leverage", "seamless", "revolutionary", "game-changing", "amazing", "incredible", "utilize" — none found in founder-facing surfaces

**Referenced files verified present:** YES — Independence Check confirmed all cited paths exist (see Gate 4 Codebase Referential Integrity below)

---

## Gate 4 — Evaluate (Spiral Verification)

**Scoring source:** Independence Check sub-agent (Agent subagent_type=Explore in fresh context, no access to author reasoning). See "Independence Check" section below for the full sub-agent report.

### ACCA (required all tiers)

| Sub-dimension | Threshold | Score | Evidence |
|---|---|---|---|
| Accurate | >= 4 | 5 | 37 specific standard citations with section numbers |
| Clear | >= 4 | 5 | Five-gate structure explicit with pass criteria per gate |
| Complete | >= 4 | 5 | All gates + modes + audiences covered |
| Actionable | >= 4 | 5 | Specific inventory script invocation syntax, frontmatter examples, misuse case numbering |

**ACCA minimum:** 5/5 — **PASS**

### Evidence Grounding (STANDARD + HEAVY)

**Threshold:** >= 4/5 — Score: **4/5**
**Standard reference:** CRITICAL_THINKING_STANDARD.md (BI, SI, AT-01)
**Evidence:** All claims cite specific standards (BI-01..04, PG-03/PD-04, AT-01..03); sources traced to codebase verified; counter-searches documented in Gate 1 (BRIEF_PACK + "could this be a skill?" question). Minor finding: custom_dimensions originally declared without principle citation — fixed in v0.1.0 (added `principle_reference:` field).

### Structural Coherence (STANDARD + HEAVY)

**Threshold:** >= 4/5 — Score: **5/5**
**Standard reference:** CRITICAL_THINKING_STANDARD.md (MECE, PP, DF)
**Evidence:** Pyramid lead in Conclusion section; MECE applied (Find / Scope Lock / Generate / Evaluate / Adversarial — complete set, no overlap); DF framing (situation/complication/question/answer in Conclusion); consistency with add-skill v0.7.0 verified.

### Honest Uncertainty (STANDARD + HEAVY)

**Threshold:** >= 3/5 — Score: **4/5**
**Standard reference:** CRITICAL_THINKING_STANDARD.md (HU, CC)
**Evidence:** Deferrals documented (agent.md is single-file artifact — deliberate exclusion of templates/scripts); VERIFICATION_REPORT location explicitly chosen with rationale in methodology.md; Gotchas section surfaces real risks. Minor: deepening-mode triggers not exhaustively enumerated — addressed by adding mode-detection heuristic decision tree in v0.1.0.

### Codebase Referential Integrity (STANDARD + HEAVY)

**Threshold:** >= 4/5 — Score: **5/5**
**Standard reference:** SPIRAL_TEMPLATES.md (derived from platform ADR-164)
**Evidence (per pre-existing entity named):**

| Entity | Path | Verified exists | Notes |
|---|---|---|---|
| CRITICAL_THINKING_STANDARD | `plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md` | YES | |
| DECOMPOSITION_PROCEDURE | `plugins/sulis/references/standards/DECOMPOSITION_PROCEDURE.md` | YES | |
| SPIRAL_TEMPLATES | `plugins/sulis/references/standards/SPIRAL_TEMPLATES.md` | YES | |
| STANDARDS_RUBRIC | `plugins/sulis/references/standards/STANDARDS_RUBRIC.md` | YES | |
| REFERENTIAL_INTEGRITY_STANDARD | `plugins/sulis/references/standards/REFERENTIAL_INTEGRITY_STANDARD.md` | YES | |
| COACHING_STANDARD | `plugins/sulis/references/standards/COACHING_STANDARD.md` | YES (ported in v0.31.0 Phase 0) | |
| TONE_STANDARD | `plugins/sulis/references/standards/TONE_STANDARD.md` | YES (ported in v0.31.0 Phase 0) | |
| Founder-Facing Conventions | `plugins/sulis/references/founder-facing-conventions.md` | YES (Rule 6 added v0.31.0) | |
| add-skill | `plugins/sulis/skills/add-skill/SKILL.md` | YES | The methodology mirrored |
| executor agent (example cited) | `plugins/sulis/agents/executor.md` | YES | |
| orchestrator agent (example cited) | `plugins/sulis/agents/orchestrator.md` | YES | |
| concierge agent (example cited) | `plugins/sulis/agents/concierge.md` | YES | |
| requirements-analyst (example cited) | `plugins/srd/agents/requirements-analyst.md` | YES | |
| engineering-architect (example cited) | `plugins/sea/agents/engineering-architect.md` | YES | |
| security-reviewer (example cited) | `plugins/sulis-security/agents/security-reviewer.md` | YES | |
| context-cartographer (example cited) | `plugins/sulis-context/agents/context-cartographer.md` | YES | |

No unresolved citations. All paths verified by Independence Check sub-agent.

### Outcome-Specific Rigor (HEAVY only) — three perspectives

#### Sub-perspective 1 — Dispatch trigger precision

**Verdict:** PASS — Score: **4/5**
**Method:** Description-only test on 5 parent-agent scenarios
**Result:** description correctly routes for "author new agent", "formalise dispatch pattern", "deepen existing agent", "standards-grounded consistency" — 4/5 (the phrase "consistency rather than ad-hoc" could be tighter but acceptable in context)

#### Sub-perspective 2 — Tool-completeness check

**Verdict:** PASS — Score: **5/5**
**Result:** Skill declares no tools (`tools:` absent, inherits from parent). Body text claims no tool invocations that would fail at runtime. inventory.py script is a reference tool invoked by the author, not a dispatch-time tool. No mismatches.

#### Sub-perspective 3 — Output-shape verification

**Verdict:** PASS — Score: **5/5**
**Result:** Declared output (agent.md + VERIFICATION_REPORT.md on disk) is precisely specified at every gate. Templates provided. Founder-mode and technical-mode shapes documented for dual-register agents. Filesystem-check compliance mechanism explicit.

### Coaching Delivery (founder-facing — MANDATORY)

**Standard reference:** `plugins/sulis/references/standards/COACHING_STANDARD.md`
**Method:** Seven-question Pass/Fail validation checklist applied to skill's instructional text (the skill is methodology documentation, not a chat agent — scoring against the guidance the skill emits to its author user)

**Sample text scored:** *"For every 'is there an agent that does X?' search, also search 'is there a skill that already covers X without needing a dedicated agent?' — agents are heavier than skills; prefer skill if the work doesn't require its own conversational context."*

| Question | Verdict |
|---|---|
| Q1 Structural | PASS — "the work doesn't require its own conversational context" (structure-as-subject) |
| Q2 Calibration | PASS — "prefer skill IF..." (conditional, invites judgment) |
| Q3 Room for own conclusions | PASS — invites the author to decide |
| Q4 Dignity | PASS — no blame |
| Q5 Relationship depth | PASS — methodological guidance, not directive |
| Q6 Room to step up | PASS — "read the methodology if you want the rationale" |
| Q7 Forward without embarrassment | PASS — professional tone throughout |

**Score: 7/7 — PASS**

**Red-flag scan:** zero hits ("You need to..." / "You should..." / "The problem is..." — none found in founder-facing surfaces)

### Tone Conformance (founder-facing — MANDATORY)

**Standard reference:** `plugins/sulis/references/standards/TONE_STANDARD.md`
**Sample text scored:** *"A five-gate methodology for authoring or upsurging an agent in the Sulis marketplace. Mirrors `add-skill` v0.7.0's structure."*

| Item | Verdict |
|---|---|
| T-01 Pragmatic Authority | PASS — operator voice, technical grounded |
| T-02 Radical Clarity | PASS — short sentences, plain English |
| T-03 Build + Market | PASS — connects to marketplace outcome |
| T-04 Governance | PASS — methodology described as principled |
| T-05 Vocabulary Governance | PASS — three-zone framework applied |
| Systemic Lexicon | PASS — preferred operator terms used ("gate", "lock", "primitives", "dispatch") |
| Forbidden Vocabulary | PASS — scan confirms no banned terms |

**Score: 7/7 — PASS**

### Register Switch Correctness

**Verdict:** N/A — `add-agent` is a methodology skill, not a chat agent that switches modes mid-conversation. The skill's frontmatter declares a dual-register output shape (founder-mode prose vs technical-mode markdown-with-paths) but the switching is binary at invocation time, not stateful. Sub-tests 1-4 are not applicable.

### Independence Check (HEAVY only)

**Threshold:** >= 3/5 — Score: **5/5**
**Scorer:** Agent (subagent_type=Explore) in fresh context (no access to author reasoning)
**Sub-agent verdict:** PASS across all dimensions

**Top 3 improvements identified by sub-agent (all applied in v0.1.0):**

1. ~~Add explicit CT principle citation to custom_dimensions in frontmatter~~ → APPLIED — `principle_reference:` field added to both custom dimensions
2. ~~Add mode-detection decision tree to SKILL.md~~ → APPLIED — new "Mode-detection heuristic" section in Modes section
3. ~~Add worked example of OPEN_RISK with revisit-trigger in Gate 5~~ → APPLIED — "What an acceptable OPEN_RISK looks like" sub-section in Gate 5

---

## Gate 5 — Adversarial Review (AT / FR)

### Audience-agnostic misuse cases

#### Misuse case 1: Trigger-condition jargon leakage

- **What might go wrong:** The description uses "upsurge" / "standards-grounded" — terms only operators recognise. A parent agent dispatching based on a founder's "I want to author an agent" request might not route correctly.
- **Status:** PREVENTED
- **Mitigation:** Description includes "author a new Claude Code agent" (founder-readable phrasing) as the primary trigger. Operator-friendly terms ("upsurge", "standards-grounded") are secondary triggers for operators who know them. Description tested against the BRIEF_PACK Section 6 decision prompts.

#### Misuse case 2: Codebase Referential Integrity rot

- **What might go wrong:** The skill cites many agents and standards by path. If any are renamed or moved, the skill's references break silently.
- **Status:** OPEN_RISK
- **Description:** All cited paths verified at v0.1.0 time. Future renames (e.g., concierge → sulis in Phase 2) will require updating add-agent's references.
- **revisit_by:** event — every consolidation of an external plugin's agent into sulis (Phase 3 of the change-as-primitive build), update add-agent's example list
- **Workaround in the meantime:** sub-agent Independence Check at next invocation will surface broken references

#### Misuse case 3: Methodology drift between add-skill and add-agent

- **What might go wrong:** add-skill evolves (v0.8.0+) but add-agent stays on the v0.7.0 mirroring assumption — divergence accumulates silently.
- **Status:** PREVENTED
- **Mitigation:** Documented in methodology.md §"Composition with add-skill" and the related_skills frontmatter block (`depends_on: add-skill`). Any future add-skill version bump triggers a Codebase Referential Integrity check on add-agent — broken assumptions surface as findings.

### Founder-facing agent misuse cases (MUC-A1..A4 — ALL 4 MANDATORY)

**Note:** These cases apply to AGENTS authored via add-agent, not to add-agent itself (which is a skill). However, since this skill *teaches* the misuse cases, the cases are first-class content in the SKILL.md. Verified: all four are named, described, and have prevention/risk status in the SKILL.md Gate 5 section.

#### MUC-A1: Prescriptive language leak — PREVENTED via Gate 4 Coaching Delivery perspective
#### MUC-A2: Banned vocabulary leak — PREVENTED via Gate 4 Tone Conformance perspective
#### MUC-A3: Defensive-triggering phrase — PREVENTED via Gate 4 Coaching Delivery + worked OPEN_RISK example provided
#### MUC-A4: Commercial outcome missing — PREVENTED via TONE T-03 + output-shape template field

### Dual-register agent misuse cases (MUC-R1..R3 — ALL 3 MANDATORY)

**Note:** Same as above — these apply to agents authored via add-agent. Verified named and described in SKILL.md.

#### MUC-R1: Technical-mode leaks into founder-mode default — PREVENTED via register flag + Gate 4 default-register check
#### MUC-R2: Founder-mode drops signal — PREVENTED via founder-facing-conventions Rule 2 (readable name with ID in parens)
#### MUC-R3: Register-switch ambiguity — PREVENTED via "default is deeper founder-mode; ask explicitly if technical-mode seems intended"

### MUC-F1..F6

**Note:** Same as above — taught by SKILL.md for downstream agents to address.

---

## Fixes Applied During Spiral

Three improvements applied in v0.1.0 based on Independence Check feedback:

1. Added `principle_reference:` field to both custom dimensions in frontmatter (Evidence Grounding strengthening)
2. Added "Mode-detection heuristic" section to SKILL.md Modes section (mirrors methodology.md content; previously only in references)
3. Added "What an acceptable OPEN_RISK looks like (worked example)" sub-section in Gate 5 (clarifies the bar for OPEN_RISK vs PREVENTED)

---

## Irreducible Blockers

None.

---

## Open risks accepted at publication

### Risk 1: Codebase Referential Integrity rot

- **Description:** add-agent cites many external paths (agents, standards, methodology). Future renames break references silently.
- **Why accepted:** Inevitable for any reference-heavy skill; mitigated by sub-agent Independence Check at next invocation.
- **revisit_by:** event — every consolidation in the change-as-primitive build (Phase 3 onwards)
- **Workaround for users in the meantime:** Run the Independence Check during deepening / upsurge to surface broken references

### Risk 2: First-mover scoring calibration

- **Description:** add-agent is the first sulis skill authored explicitly using the founder-mode evaluation perspectives (Coaching Delivery + Tone Conformance + Register Switch Correctness). The scoring thresholds (≥ 6/7, ≥ 18/20) are reasoned but not empirically calibrated.
- **Why accepted:** Empirical calibration requires authoring ≥ 5 founder-facing agents and observing score distribution. v0.1.0 ships with reasoned thresholds; v0.2.0 calibrates based on observed data.
- **revisit_by:** event — after 5 founder-facing agents authored via add-agent (likely Phase 3 + Phase 6 of the change-as-primitive build)
- **Workaround for users in the meantime:** Treat threshold failures as advisory in v0.1.0; document any threshold-vs-quality mismatches in the agent's VERIFICATION_REPORT for the v0.2.0 calibration pass

---

## Vocabulary changes during authoring

None — all 12 introduced terms remained stable from Gate 2 lock through Gate 5.

---

## Meta-Notes

- This skill ate its own dogfood by being authored via add-skill v0.7.0 (the methodology it mirrors). The five-gate process produced a coherent output on the first iteration.
- The Independence Check sub-agent's verdict came back PASS across all dimensions, surfacing only three refinement-grade improvements (all applied in v0.1.0 before publish).
- The skill is positioned as the foundation for Phase 2 of the change-as-primitive build (the Sulis agent rewrite from concierge.md). Phase 2 will be the first real test of add-agent on a non-trivial agent (~1500 LOC source body).
- The two empirical-calibration risks (CRI rot, scoring thresholds) are acknowledged and have concrete revisit triggers in the change-as-primitive build phases.

---

## Naming history

This is the first iteration of `add-agent` — no naming history.
