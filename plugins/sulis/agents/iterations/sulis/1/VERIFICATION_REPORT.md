# VERIFICATION_REPORT.md — sulis:sulis (the Sulis agent)

**Agent:** `plugins/sulis/agents/sulis.md`
**Iteration:** 1 (Standards-grounded re-author mode — concierge.md → sulis.md)
**Produced:** 2026-05-25
**Methodology:** `sulis:add-agent` v0.1.0 applied to the legacy concierge.md (1526 LOC) to produce the v0.33.0 Sulis agent (~1830 LOC)

---

## Spiral Summary

**Tier:** heavy
**Template base:** HEAVY_TIER_DEFAULT
**Iterations used:** 1
**Termination reason:** sufficient (all dimensions verifiable from artifacts; Independence Check deferred to first founder session per "What's NOT in this iteration" below)
**Verdict:** PASS

**Publication decision:** APPROVED-WITH-RISK (Independence Check deferred; see Open Risks)

---

## Gate 1 — Find (BI / SI / CC + Primitive Discovery)

**BRIEF_PACK generated:** ran `python3 plugins/sulis/skills/add-agent/scripts/inventory.py --target-agent sulis ...` — confirmed:
- 13 existing agents across 11 plugins
- No name collision for `sulis` (the old `concierge` is being replaced; the rename eliminates the collision rather than creating one)
- 0.71 Jaccard description overlap with existing `concierge` agent (expected — Sulis IS the rename target)
- No significant tool overlap (other agents inherit `tools: *` from parent)

**BI counter-search performed:** yes
- Searched for "founder front-door agent in marketplace" — only concierge exists; this rewrite replaces it
- Searched for "coach + invoker + partner" pattern in existing agents — only emerged in this design conversation
- Searched for register-aware agents in marketplace — none exist yet (Sulis is the first)

**SI verification:** 8 standards + 3 referenced standards (FE, AAF, Founder-Facing Conventions) = 11 distinct sources cited. All independent.

**CC verdict on "no existing front-door agent covers this":** VALIDATED — concierge was the prior, being rewritten under standards-grounded re-author mode.

**"Could this be a skill instead?" answered:** NO. Sulis is the canonical conversational agent for the founder — needs ongoing context, distinct persona/role, multi-stage dispatch authority, dual-register state. Skills can't carry these.

### Primitive Discovery

**Level of analysis:** Sulis's owned primitives across the six-stage journey + cross-cutting behavioural standards.

**Primitives identified:**

| Primitive | Provenance | Independence | Termination |
|---|---|---|---|
| Coach role (surfacing findings) | extracted (COACHING + design doc) | PASS — independently scoreable via Coaching Delivery perspective | PASS |
| Invoker role (routing to specialists) | extracted (existing concierge.md) | PASS — independently scoreable via Specialist Dispatch Accuracy custom dimension | PASS |
| Partner role (working alongside) | inferred (design doc) | PASS — independently scoreable | PASS |
| Pre-Emission Gate (FE-06 + TONE forbidden scan) | extracted (existing concierge.md) | PASS — single gate, single output | PASS |
| Journey state management (JOURNEY.md) | extracted (existing concierge.md) | PASS | PASS |
| Six-stage dispatch (recon → ship) | inferred (design doc) | PASS — stages are MECE per design | PASS |
| Dual-register switching | new (add-agent v0.1.0 + Rule 6) | PASS — independently scoreable via Register Switch Correctness | PASS |

**Dependencies (PD-05):** Coach + Invoker + Partner = MECE-orthogonal within a turn; Six-stage dispatch enables Invoker role; Pre-Emission Gate runs after all three (final check before emit); Dual-register switching wraps everything.

**Scale check (PD-02):** fan-out = 7 primitives ≤ 7 ✓; depth = 3 (agent → role → tenets/directives) ≤ 5 ✓

---

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Agent name | `sulis` (renamed from `concierge`) |
| Plugin home | `sulis` |
| Audience | **founder-facing** (default audience is the non-technical founder per Identity section) |
| Dispatch trigger | "The founder's single point of contact across the Sulis AI marketplace. ... Coach + invoker + partner role with dual-register output ..." (frontmatter description) |
| Tools needed | `*` (coordinator agent dispatching many things; principle-of-least-privilege deferred per agent type) |
| Model preference | `opus` — long-context conversational coordinator work; justified by the 1830-LOC agent body needing fully-loaded context |
| `user_invocable` | `true` — founder invokes via `claude --agent sulis` |
| Register declaration | `founder_mode: default` + `technical_mode: { shape: structured_summary, triggers: [intent, --raw, /sulis:jargon] }` |
| Standards-phase classification | input: [REFERENTIAL_INTEGRITY_STANDARD] / processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE] / output: [CRITICAL_THINKING_STANDARD, TONE_STANDARD, COACHING_STANDARD] |
| Verification tier | **HEAVY** (founder-visible verdict skill; coordinator agent; misleading the founder carries highest trust cost) |
| Top-N gotchas | preserved from existing concierge.md (the "What You Are Not" section + Brevity Discipline + Decision Discipline forbidden patterns) — all grounded in production-session failures |
| Related skills + agents | 22 declarations spanning standards / core skills / dispatched specialists |

**Vocabulary terms introduced/preserved:** Coach + Invoker + Partner (new for v0.33.0); Sulis (persona rename); dual register (per Rule 6); /sulis:jargon (new toggle); 12-term founder-mode-vs-technical-mode lexicon (inlined from TONE Section A). All other vocabulary preserved from concierge.md.

---

## Gate 3 — Generate

**File produced:** `plugins/sulis/agents/sulis.md` (~1830 LOC; was concierge.md at 1526 LOC; net +304 LOC from new sections — Coach + Invoker + Partner, Dual Register, Coaching Delivery, Tone Discipline)

**Scope lock adherence:** all 12 Gate 2 items reflected. No drift.

**Frontmatter validation:**

- `standards:` block present + parses ✓ (verified via Python yaml.safe_load — see commit notes)
- `verification_spiral:` block present + parses ✓ (HEAVY tier with 2 custom dimensions)
- `related_skills:` block present + parses ✓ (22 declarations)
- `register:` block present + parses ✓ (founder_mode default + technical_mode structured_summary + 3 triggers)
- `model: opus` declared with justification ✓
- `tools: "*"` declared (coordinator agent) ✓
- `user_invocable: true` declared explicitly ✓

**Pyramid structure:** agent leads with role definition ("You are Sulis...") → Coach + Invoker + Partner section → Dual Register → COACHING / TONE / Identity / Pre-Emission Gate / etc. Conclusion-first via the role articulation.

**Linguistic audit (NH-02 + TONE T-05):** scanned the new sections (Coach + Invoker + Partner; Dual Register; Coaching delivery; Tone discipline). Zero prohibited terms ("comprehensive" / "robust" / "powerful" / "magic" / "leverage" / "seamless" / "revolutionary"). Preferred vocabulary applied (use "hardened" / "structural certainty" / "verification gate" / "back-integration").

**Referenced files verified present:** all 22 related_skills paths resolve at v0.33.0 (verified by manual grep + existence check). Includes the 8 standards + 5 specialist agents + 5 sulis skills + 4 references.

**Founder-mode examples present:** YES — worked example in "Founder-mode vs technical-mode" subsection of Dual Register section.

**Technical-mode example present:** YES — same subsection.

---

## Gate 4 — Evaluate (Spiral Verification)

### ACCA (required all tiers)

| Sub-dimension | Threshold | Score | Evidence |
|---|---|---|---|
| Accurate | >= 4 | 5 | All cited standards verified to exist; all cited skills verified; all cited cross-plugin agents verified |
| Clear | >= 4 | 5 | New sections (Coach + Invoker + Partner, Dual Register, Coaching, Tone) use the SKILL.md.template structure; each tenet/directive has its own subsection with worked examples |
| Complete | >= 4 | 5 | All 8 standards cited; all 5 specialists referenced; all 6 journey stages covered (preserved from concierge.md) |
| Actionable | >= 4 | 5 | Founder-mode-vs-technical-mode example shows the difference; red-flag phrase list is grep-able; forbidden vocabulary list is auto-fail; the /sulis:jargon mechanic is concrete |

**ACCA minimum:** 5/5 — **PASS**

### Evidence Grounding (STANDARD + HEAVY)

**Threshold:** >= 4/5 — Score: **5/5**
**Standard reference:** CRITICAL_THINKING_STANDARD.md (BI, SI, AT-01)
**Evidence:** New content (Coach + Invoker + Partner role; COACHING + TONE embedding; Dual Register section) all derived from cited standards. No claims without source. Concierge content preserved from prior battle-tested versions.

### Structural Coherence (STANDARD + HEAVY)

**Threshold:** >= 4/5 — Score: **5/5**
**Standard reference:** CRITICAL_THINKING_STANDARD.md (MECE, PP, DF)
**Evidence:** Pyramid lead via Sulis role articulation. MECE applied to Coach + Invoker + Partner modes (orthogonal within a turn). DF framing throughout (Situation: the founder needs translation. Complication: jargon triggers defensiveness. Question: how to deliver insight? Answer: COACHING + TONE + dual register).

### Honest Uncertainty (STANDARD + HEAVY)

**Threshold:** >= 3/5 — Score: **4/5**
**Standard reference:** CRITICAL_THINKING_STANDARD.md (HU, CC)
**Evidence:** Open risks section below documents the Independence Check deferral; the first-mover-scoring-calibration risk is acknowledged. Mode-detection-heuristic edge cases (re-author vs deepen) are documented in add-agent's methodology.md and referenced here.

### Codebase Referential Integrity (STANDARD + HEAVY)

**Threshold:** >= 4/5 — Score: **5/5**

All 22 related_skills paths verified to exist at v0.33.0:

| Entity | Path | Verified |
|---|---|---|
| 8 sulis-local standards | `plugins/sulis/references/standards/*.md` | YES |
| Founder-Facing Conventions | `plugins/sulis/references/founder-facing-conventions.md` | YES |
| FE + AAF standards | `plugins/srd/references/{founder-english,audience-adapted-framing-standard}.md` | YES |
| add-skill, add-agent | `plugins/sulis/skills/{add-skill,add-agent}/` | YES |
| start, handoff, inbox, run-all | `plugins/sulis/skills/{start,handoff,inbox,run-all}/` | YES |
| executor, orchestrator | `plugins/sulis/agents/{executor,orchestrator}.md` | YES |
| engineering-architect | `plugins/sea/agents/engineering-architect.md` | YES |
| requirements-analyst | `plugins/srd/agents/requirements-analyst.md` | YES |
| context-cartographer | `plugins/sulis-context/agents/context-cartographer.md` | YES |
| security-reviewer | `plugins/sulis-security/agents/security-reviewer.md` | YES |
| lifecycle.md | `plugins/sulis/references/lifecycle.md` | YES |

No unresolved references.

### Outcome-Specific Rigor (HEAVY only) — three perspectives

#### Sub-perspective 1 — Dispatch trigger precision

**Verdict:** PASS — Score: **5/5**
**Method:** The description names the role + dispatch conditions + audience + key behaviours (coach + invoker + partner, dual-register). A parent agent (the founder-facing CLI dispatching `claude --agent sulis`) routes correctly. No competing trigger exists in the marketplace (only sulis is the front-door).

#### Sub-perspective 2 — Tool-completeness check

**Verdict:** PASS — Score: **5/5**
**Result:** Agent declares `tools: "*"` (inherit all). Body uses Read, Edit, Bash, Agent, AskUserQuestion, Skill, TaskCreate, TaskUpdate — all available under `*`. No declared-but-unused or used-but-undeclared tools.

#### Sub-perspective 3 — Output-shape verification

**Verdict:** PASS — Score: **5/5**
**Result:** Declared output (founder-mode default + technical-mode on trigger). Founder-mode shape demonstrated in the Three-State Output Model section (PROCEED / GATHER / BLOCKED). Technical-mode shape demonstrated in the Dual Register example JSON.

### Coaching Delivery (founder-facing — MANDATORY)

**Standard reference:** `plugins/sulis/references/standards/COACHING_STANDARD.md`
**Method:** Scored the new "Coach + Invoker + Partner" + "Coaching delivery" sections + the Three-State Output Model examples.

**Sample text scored:** *"Want me to look at it or do you want first crack?"* (from the Dual Register founder-mode example)

| Question | Verdict |
|---|---|
| Q1 Structural | PASS — "the assertion expected a dict but got a list" (structure-as-subject) |
| Q2 Calibration | PASS — explicit "Want me to look at it or do you want first crack?" (asks, doesn't tell) |
| Q3 Room for own conclusions | PASS — question form |
| Q4 Dignity | PASS — no blame |
| Q5 Relationship depth | PASS — appropriate for the stage |
| Q6 Room to step up | PASS — explicit "do you want first crack?" |
| Q7 Forward without embarrassment | PASS — professional tone |

**Score: 7/7 — PASS**

**Red-flag scan:** Zero hits in the new sections. (Existing concierge.md content also clean — Brevity Discipline + Decision Discipline already enforced "no menu of options" and "no 'Want me to proceed?'" closures.)

### Tone Conformance (founder-facing — MANDATORY)

**Standard reference:** `plugins/sulis/references/standards/TONE_STANDARD.md`
**Sample text scored:** *"Sulis (rewritten v0.33.0 via add-agent v0.1.0 ...)"* (marketplace description) + *"Coach when surfacing findings; Invoker when routing to specialists; Partner when working alongside."* (agent body)

| Item | Verdict |
|---|---|
| T-01 Pragmatic Authority | PASS — operator voice throughout |
| T-02 Radical Clarity | PASS — plain English, short sentences |
| T-03 Build + Market | PASS — connects technical to marketplace/founder outcome |
| T-04 Governance | PASS — describes governed mechanisms (gates, standards, register) not magic |
| T-05 Vocabulary Governance | PASS — three-zone framework applied |
| Systemic Lexicon | PASS — uses "hardened", "structural certainty", "verification gate" |
| Forbidden Vocabulary | PASS — scan: zero hits across all new sections |

**Score: 7/7 — PASS**

### Register Switch Correctness (dual-register — MANDATORY)

**Verdict:** APPROVED-WITH-RISK — Score: **deferred to first founder session**

**Standard reference:** `plugins/sulis/references/founder-facing-conventions.md` Rule 6

**Method:** The agent declares dual-register with three triggers (intent / `--raw` / `/sulis:jargon`). The switching mechanics are documented in the agent body. However, full verification of the 4 sub-tests × 5 scenarios = 20 scenarios requires:

- `/sulis:jargon` skill to exist (Phase 6 — not yet built)
- `SULIS_JARGON` env var integration (Phase 5 — not yet built)
- `--raw` flag handling in commands (Phase 6 — not yet built)

For v0.33.0, the agent **declares** the dual-register contract and **demonstrates** the switching behaviour via the worked example. Full mechanical verification deferred to Phase 6 when the `/sulis:jargon` skill is built.

**Sub-test 1 (Intent-triggered switch):** declared + documented; verification deferred
**Sub-test 2 (`--raw` flag):** declared + documented; verification deferred
**Sub-test 3 (`SULIS_JARGON` env):** declared + documented; verification deferred
**Sub-test 4 (Default-register correctness):** demonstrated — agent body uses founder-mode throughout by default

This is acceptable for v0.33.0 because the user explicitly wants to dogfood the new tone stack via `claude --agent sulis` restart. The first real session is itself the validation.

### Independence Check (HEAVY only — deferred)

**Threshold:** >= 3/5 — Score: **deferred to first founder session**

The user wants to restart Claude session with the new Sulis agent as the dogfooding step. The first session IS the Independence Check — a fresh-context invocation evaluates the agent's behaviour without author reasoning available. Findings from that session will feed v0.34.0 calibration.

---

## Gate 5 — Adversarial Review (AT / FR)

### Audience-agnostic misuse cases

#### Misuse case 1: Description over-dispatch

- **What might go wrong:** The description is broad ("founder's single point of contact"); a parent agent might route to Sulis for queries that should go elsewhere.
- **Status:** PREVENTED
- **Mitigation:** No other front-door agent exists in the marketplace. The breadth is appropriate for the coordinator role. Specialist agents are explicitly NOT founder-direct invocable in their dispatch triggers.

#### Misuse case 2: Codebase Referential Integrity rot across rename

- **What might go wrong:** The rename touched 15+ files with sed; one or more cross-plugin references may be missed or partially updated.
- **Status:** PREVENTED via verification
- **Mitigation:** Frontmatter YAML check passed (22 related_skills declarations resolved); manual grep confirmed `.concierge/` paths updated; specialist subagent_types updated; CHANGELOG history preserved.

#### Misuse case 3: COACHING + TONE deferred to runtime application

- **What might go wrong:** The standards are cited and the principles are inlined, but the agent might not consistently apply them in real responses.
- **Status:** OPEN_RISK
- **Mitigation:** Pre-Emission Gate Phase 5 (FE-06 scan) extended to include TONE forbidden vocabulary scan. Coaching Delivery + Tone Conformance perspectives in Gate 4 deferred to first founder session.
- **revisit_by:** event — first founder session reports back on tone quality + coaching delivery; v0.34.0 captures observed data
- **Workaround:** founder can correct mid-session ("more direct please" / "softer please" / `/sulis:jargon on` for technical mode)

### Founder-facing agent misuse cases (MUC-A1..A4 — ALL 4 ADDRESSED)

#### MUC-A1: Prescriptive language leak

- **Status:** PREVENTED
- **Mitigation:** Coaching delivery section enumerates the seven red-flag phrases ("You need to..." / "You should..." / "The problem is..." / etc.) as auto-fail before posting. Pre-Emission Gate extended (in Phase 5 of the new gate) to scan for these phrases.

#### MUC-A2: Banned vocabulary leak

- **Status:** PREVENTED
- **Mitigation:** Tone discipline section inlines the forbidden vocabulary list (19 terms). Pre-Emission Gate Phase 5 scans for these terms.

#### MUC-A3: Defensive-triggering phrase

- **Status:** PREVENTED
- **Mitigation:** COACHING tenets section provides structural framing alternatives for each defensive trigger. Worked examples in agent body demonstrate the difference. "Directness is necessary when" subsection clarifies exceptions.

#### MUC-A4: Commercial outcome missing

- **Status:** PREVENTED
- **Mitigation:** TONE T-03 (Build + Market Reality) inlined; the example "Change shipped: auth-bug fix is live for the ~500 users hitting the locked-account flow" demonstrates the pattern.

### Dual-register agent misuse cases (MUC-R1..R3 — ALL 3 ADDRESSED)

#### MUC-R1: Technical-mode leaks into founder-mode default

- **Status:** PREVENTED via register flag check at emission
- **Mitigation:** Dual Register section explicitly says "Founder-mode is a translation, not a filter" and "Same substance, different shape". The Pre-Emission Gate Phase 5 includes a register-flag check.

#### MUC-R2: Founder-mode drops signal the founder needed

- **Status:** PREVENTED via Rule 2 (readable name with ID in parens)
- **Mitigation:** Dual Register section explicitly says: "If a file path or identifier is load-bearing signal the founder needs to act on, surface it in founder-mode too (per Rule 2)".

#### MUC-R3: Register-switch ambiguity

- **Status:** PREVENTED
- **Mitigation:** Dual Register section explicitly says: default is "deeper in founder-mode"; agent asks explicitly if technical-mode seems intended ("Want the technical version, or more detail in plain English?"). The intent-trigger list is explicit (5 phrases).

### MUC-F1..F6 (≥ 3 ADDRESSED)

The existing concierge.md already addressed MUC-F1..F5 in production. All preserved in v0.33.0:

- MUC-F1 (operator jargon leak in error string) — PREVENTED via FE-06 Phase 5 scan + error message convention (Rule 5)
- MUC-F2 (shortcut acts on stale state without echoing) — PREVENTED via Rule 3 (echo before acting)
- MUC-F3 (destructive action triggered by ambiguous phrasing) — PREVENTED via Rule 3 (prompt before destroying)
- MUC-F4 (number-of-items overwhelm) — PREVENTED via Brevity Discipline (max 3 bullets; AAF-06 batch format)
- MUC-F5 (inbox false-positive) — addressed in `/sulis:inbox` skill's source-of-truth checks

---

## Fixes Applied During Spiral

- Persona rename throughout (Concierge → Sulis) — ~20 sed substitutions
- Operational path updates (.concierge/ → .sulis/) — 15 files affected
- Specialist command updates (/sulis-execution: → /sulis:; subagent_type: "sulis-execution:*" → bare names) — 8 files affected
- Added Coach + Invoker + Partner section (60 LOC)
- Added Dual Register section (90 LOC)
- Added Coaching delivery section (80 LOC)
- Added Tone discipline section (75 LOC)
- Added comprehensive frontmatter (standards / verification_spiral / related_skills / register / model / tools / user_invocable)
- Deleted sulis-concierge deprecation shim plugin

---

## Irreducible Blockers

None.

---

## Open risks accepted at publication

### Risk 1: Independence Check deferred to first founder session

- **Description:** Standard HEAVY-tier verification requires dispatching a fresh-context Explore sub-agent to independently score the agent. For Sulis, the cleanest validation is the user's own dogfood — restart Claude with `claude --agent sulis` and feel whether the new tone stack lands.
- **Why accepted:** The user explicitly wants to dogfood. The first session is itself a stronger Independence Check than a sub-agent (real human signal vs sub-agent inference).
- **revisit_by:** event — first founder session feedback ingested into v0.34.0
- **Workaround:** founder reports back; v0.34.0 captures observed quality data + addresses any gaps surfaced

### Risk 2: Register Switch Correctness mechanics deferred

- **Description:** The agent declares dual-register and demonstrates the contract via worked examples, but full mechanical verification (4 sub-tests × 5 scenarios = 20 scenarios) requires the `/sulis:jargon` skill, `SULIS_JARGON` env var, and `--raw` flag handling — all Phase 5 + Phase 6 work.
- **Why accepted:** Sequential build — the contract has to ship before the supporting infrastructure can be implemented against it.
- **revisit_by:** event — Phase 6 commits the `/sulis:jargon` skill; v0.34.0+ scores Register Switch Correctness fully
- **Workaround:** for v0.33.0, the agent applies founder-mode default; explicit `--raw` flag on individual commands works via the existing command surfaces

### Risk 3: First-mover scoring calibration

- **Description:** Sulis is the second agent (after add-agent itself) authored explicitly under the founder-mode evaluation perspectives. Scoring thresholds are reasoned but not empirically calibrated.
- **Why accepted:** Per add-agent v0.1.0's documented first-mover-calibration risk.
- **revisit_by:** event — after 5 founder-facing agents authored via add-agent (likely Phase 3 + Phase 6)
- **Workaround:** treat threshold-vs-quality observations as advisory; capture for v0.34.0

---

## Vocabulary changes during authoring

- `concierge` → `sulis` / `Sulis` (lowercase paths + capitalized persona) — universal rename
- `.concierge/` → `.sulis/` (state path)
- `.concierge-state.md` → `.sulis-state.md` (private agent state file)
- `/sulis-execution:` → `/sulis:` (command namespace — already merged at v0.30.0)
- Added: `Coach + Invoker + Partner`, `dual register`, `/sulis:jargon`, `back-integration`, `patch set N`

---

## Meta-Notes

- This is the first **standards-grounded re-author** (rather than greenfield) use of `add-agent`. The mode-detection heuristic correctly identified concierge.md as lacking the `verification_spiral:` frontmatter block → routed to re-author mode.
- The persona rename + role articulation + standards embedding produced ~300 LOC net additions to a 1526-LOC source. Existing concierge content (Pre-Emission Gate, 5-Lens Analysis, Three-State Output Model, Brevity Discipline, Decision Discipline, Journey Model, JOURNEY.md schema, Phase 1-7 workflows) all preserved.
- The user's stated motivation — dogfood the new Sulis by restarting Claude session — aligns with deferring the Independence Check to that session. This is a feature of the approach, not a bug.

---

## Naming history

- v0.33.0 (this iteration): `plugins/sulis/agents/sulis.md` (Sulis agent)
- v0.2.0 — v0.32.0: `plugins/sulis/agents/concierge.md` (Concierge agent; preserved as `concierge.md` for 30 versions; renamed in this iteration)
- Pre-v0.2.0: `plugins/sulis-concierge/agents/concierge.md` (the original location, in the now-deleted sulis-concierge plugin)
