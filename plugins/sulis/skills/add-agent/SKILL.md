---
name: add-agent
description: Use when the user wants to author a new Claude Code agent in the Sulis marketplace, formalise an existing dispatch pattern as a published agent, deepen an existing agent ("upsurge"), or get methodology-driven quality consistency rather than ad-hoc agent.md authoring. Walks a five-gate flow grounded in the eight sulis standards (six methodology + two founder-communication for founder-facing agents).
standards:
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE]
  output: [CRITICAL_THINKING_STANDARD, TONE_STANDARD, COACHING_STANDARD]
verification_spiral:
  tier: heavy
  template_base: HEAVY_TIER_DEFAULT
  custom_dimensions:
    - name: "Methodology Self-Consistency"
      threshold: ">= 4/5"
      standard_reference: "this SKILL.md applied to its own production"
      principle_reference: "CRITICAL_THINKING_STANDARD AT-01 (adversarial posture) + FR-03 (pre-mortem)"
      scorer: external_sub_agent
      evidence_required: "Independence Check sub-agent confirms add-agent's own gates pass when applied to add-agent v0.1.0 SKILL.md"
    - name: "Dispatch Trigger Precision"
      threshold: ">= 4/5"
      standard_reference: "the agent's description must produce the intended dispatch routing in ≥85% of plausible parent-agent contexts"
      principle_reference: "CRITICAL_THINKING_STANDARD BI-01 (balanced investigation — counter-search for over- and under-dispatch contexts)"
      scorer: external_sub_agent
related_skills:
  - relationship: depends_on
    skill: ../add-skill
    notes: add-agent is authored via add-skill v0.7.0 (the meta-skill); it mirrors add-skill's five-gate structure
  - relationship: depends_on
    skill: ../../references/standards/CRITICAL_THINKING_STANDARD.md
    notes: 13 principles cited across all 5 gates
  - relationship: depends_on
    skill: ../../references/standards/DECOMPOSITION_PROCEDURE.md
    notes: Gate 1 Primitive Discovery sub-step
  - relationship: depends_on
    skill: ../../references/standards/SPIRAL_TEMPLATES.md
    notes: Gate 4 verification rubric; VERIFICATION_REPORT.md template
  - relationship: depends_on
    skill: ../../references/standards/STANDARDS_RUBRIC.md
    notes: Gate 2 standards-phase classification
  - relationship: depends_on
    skill: ../../references/standards/REFERENTIAL_INTEGRITY_STANDARD.md
    notes: cross-agent + agent-to-skill relationship declaration
  - relationship: depends_on
    skill: ../../references/standards/COACHING_STANDARD.md
    notes: Gate 4 Coaching-Delivery perspective (founder-facing agents only)
  - relationship: depends_on
    skill: ../../references/standards/TONE_STANDARD.md
    notes: Gate 4 Tone-Conformance perspective (founder-facing agents only)
  - relationship: depends_on
    skill: ../../references/founder-facing-conventions.md
    notes: Rule 6 (Dual register) cited by Gate 2 register declaration + Gate 4 Register-Switch perspective
register:
  founder_mode: default
  technical_mode:
    shape: markdown_with_paths_and_frontmatter_examples
    triggers: [intent, --raw]
---

# Add Agent

## Conclusion (Pyramid Principle — lead with the answer)

A five-gate methodology for authoring or upsurging an agent in the Sulis marketplace. Mirrors `add-skill` v0.7.0's structure — Find / Scope Lock / Generate / Evaluate / Adversarial Review — adapted for the agent shape (single `agent.md` file with dispatch contract, tools declaration, register declaration, and body that defines role + workflow + output shape).

The output is an `agent.md` plus a `VERIFICATION_REPORT.md` on disk scored against the SPIRAL_TEMPLATES rubric. A single filesystem check (`test -f ... && grep "Verdict:.*PASS"`) determines whether the agent is shipped.

Agents are **dual-register-by-default** if founder-facing — they speak founder-mode by default, switch to technical-mode on request via natural language intent, `--raw` flag, or `/sulis:jargon on` toggle. Single-register agents (operator-only or agent-internal) declare a single register at Gate 2.

The methodology applies in three modes:

1. **Greenfield** — authoring a wholly new agent
2. **Deepening (upsurge)** — extending an existing agent against the standards to reach the next depth threshold (typical use: porting an old agent.md to v0.1.0+ register-aware methodology)
3. **Standards-grounded re-author** — rewriting an existing pre-standards agent (e.g., the legacy `concierge.md`) to cite the standards explicitly

If you have not read `references/methodology.md`, read it once. It explains why each gate exists and what failure mode it prevents — specifically for the agent shape (vs the skill shape `add-skill` handles).

If you have not read the eight standards, read `plugins/sulis/references/standards/README.md` for the adoption guide. For founder-facing agents, additionally read `plugins/sulis/references/founder-facing-conventions.md` (Rule 6 in particular — dual register pattern).

## What's different from `add-skill`

`add-agent` borrows `add-skill`'s scaffolding wholesale. The differences are concentrated in three places:

| Where | What's different |
|---|---|
| **Gate 2** | Register declaration (founder + technical mode shapes); dispatch trigger as the load-bearing description; tools declaration; model preference; `user_invocable` flag |
| **Gate 4** | Two new perspectives for founder-facing agents — **Coaching Delivery** (passes the COACHING_STANDARD seven-question checklist) + **Register Switch Correctness** (correctly switches on intent / `--raw` / `/sulis:jargon`); new **Tone Conformance** perspective (passes the TONE_STANDARD seven-item checklist) |
| **Gate 5** | New misuse cases — MUC-A1..A4 (founder-facing agent specific) + MUC-R1..R3 (register-aware specific) layered on top of the audience-agnostic + MUC-F1..F6 categories |

Everything else (BRIEF_PACK, Primitive Discovery, SPIRAL_TEMPLATES tier choice, Codebase Referential Integrity, Independence Check, Adversarial Testing Posture, Iteration termination) is identical to `add-skill`.

## The five gates

Each gate has explicit pass/fail criteria + an explicit standards citation. Do not skip gates. Do not move backwards from gate N to gate N-1 without a full re-author.

The output of running this skill is two artifacts:

1. The agent itself (`plugins/<plugin>/agents/<agent-name>.md`)
2. A `VERIFICATION_REPORT.md` co-located near the agent (in the plugin's `agents/` directory or under `iterations/{N}/`), documenting per-dimension scores per SPIRAL_TEMPLATES

### Gate 1 — Find (discovery + primitive discovery, deterministic-first)

**Standards:** BI-01..04, SI-01..04, CC, PG-01..04, PD-01..06. See `plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md` §§1, 2, 4, 11 and `DECOMPOSITION_PROCEDURE.md`.

**Goal:** the author starts writing with full visibility into existing agents, their dispatch triggers, vocabulary, tools used, and collision risks — AND with an explicit primitive decomposition of what the new agent will own.

#### Sub-step 1a: BRIEF_PACK (existing agent prior-art discovery)

Run the inventory script:

```bash
python3 plugins/sulis/skills/add-agent/scripts/inventory.py \
  --marketplace-root . \
  --target-plugin <plugin-name> \
  --target-agent <agent-name> \
  --proposed-description "<dispatch trigger — one or two sentences>" \
  --proposed-tools "<comma-separated tools the agent will request>" \
  --proposed-vocabulary "<comma-separated terms the agent will introduce>"
```

The script produces a structured BRIEF_PACK (Markdown to stdout) covering:

- Every existing agent across the marketplace (name + description + plugin home + audience + tools + dispatch triggers)
- Vocabulary collision check against existing agent names and dispatch triggers
- Dispatch-trigger overlap analysis — for each existing agent, does the proposed description risk being confused for that agent's trigger?
- The eight standards inventory (canonical paths + which apply at which phase per audience)
- Founder-facing-conventions Rule 6 (Dual register) summary if the proposed agent is founder-facing or both

Then **Claude interprets** the BRIEF_PACK per BI / SI / CC:

- **BI-01:** for every "is there an agent that does X?" search, also search "is there a skill that already covers X without needing a dedicated agent?" — agents are heavier than skills; prefer skill if the work doesn't require its own conversational context
- **SI-01:** when multiple existing agents cite the same reference doc or share the same tools, count as one source not many
- **CC:** the "no existing agent covers this" judgment carries an explicit confidence (VALIDATED if 5+ independent agents checked; SUPPORTED if 3-4; EMERGING if 2; UNVALIDATED if <2)

#### Sub-step 1b: Primitive Discovery

For agents that orchestrate or specialise (most agents), decompose the agent's scope into primitives per PG-01..04 + PD-01..06.

1. **Declare the level of analysis (PG-03 / PD-04):** what decision will this agent inform? E.g., "what stages of the six-stage journey does this agent own?" or "what failure modes does this agent handle?"
2. **Identify candidate primitives (PG-01):** irreducible units at that level. For a specialist agent (requirements-analyst, engineering-architect), the primitives are the stages and sub-stages it owns. For a coordinator agent (Sulis), the primitives are the dispatch triggers it routes between.
3. **Apply the independence test (PG-02 / PD-03):** each candidate primitive must be independently changeable, validatable, falsifiable.
4. **Apply termination condition (PG-04 / PD-04):** stop decomposing when further splitting wouldn't change the next action.
5. **Type the inter-primitive dependencies (PD-05):** depends-on / enables / conflicts-with.
6. **Record provenance (PD-06):** extracted (from codebase patterns / existing agents) / inferred (from journey design) / user-stated.
7. **Verify scale constraints (PD-02):** fan-out ≤ 7 per node, depth ≤ 5.

For pure-router agents (e.g., a stage-classifier that simply picks a depth mode), primitive discovery is shallow — record one paragraph of "this agent owns the classifier function; primitives are the inputs it considers (file count, primitive count, founder-facing flag)" and move on.

**Pass criteria for Gate 1:**

- BRIEF_PACK produced and reviewed
- Dispatch-trigger collisions resolved or explicitly waived with reason
- "No existing agent covers this" carries an explicit CC verdict
- "Could this be a skill instead?" question explicitly answered — record the answer in VERIFICATION_REPORT
- Primitive decomposition completed; primitives pass PG-02 + PG-04; provenance recorded

### Gate 2 — Scope Lock (decide phase)

**Standards:** STANDARDS_RUBRIC phase classification; Outside-In Reasoning (OI-01..03); MECE-01..04. See `plugins/sulis/references/standards/STANDARDS_RUBRIC.md` and `CRITICAL_THINKING_STANDARD.md` §§5, 12.

**Goal:** the agent's scope, audience, dispatch contract, tools, register, standards-phase classification, top-N gotchas, and verification tier are written down BEFORE drafting `agent.md`.

The author commits to:

- **Agent name** (kebab-case; verified non-colliding via Gate 1; this is what becomes `subagent_type` when dispatched)
- **Plugin home** (which plugin will own it; create new plugin only if no existing one fits — but prefer sulis as the canonical front-door)
- **Audience** — `founder-facing` / `operator-facing` / `both` / `agent-internal`. Affects subsequent gates significantly:
  - `founder-facing` — dispatched directly by the founder via `claude --agent {name}` or routed-from-Sulis; MUST cite all eight standards; MUST declare register
  - `operator-facing` — dispatched by operators or skills; cites the six methodology standards
  - `both` — declare mode-selection strategy + register
  - `agent-internal` — dispatched only by other agents (not founders, not operators); cites the six methodology standards; never user-invocable
- **Dispatch trigger** — the one-or-two-sentence `description:` field. This is the highest-impact text in the whole agent — the parent agent (Sulis, an orchestrator, the user-facing CLI) scans descriptions to decide whether to route. Must be specific enough to route correctly and general enough not to require knowing the agent's internals.
- **Tools needed** — explicit list (`[Read, Edit, Bash, Agent]`) or `*` for all (defaults to inheriting from parent). Per the principle of least privilege: declare only what the agent needs.
- **Model preference** — `haiku` (fast cheap; mechanical routing or simple specialists) / `sonnet` (default; most specialist agents) / `opus` (complex reasoning, large-context work) / omit (inherits from parent). Justify the choice in VERIFICATION_REPORT.
- **`user_invocable` flag** — `true` if the founder can invoke directly via `claude --agent {name}` (true for Sulis, executor, orchestrator); `false` for agent-internal agents (true default for founder-facing agents). Skipping the flag defaults to `false` per Claude Code conventions.
- **Register declaration (NEW for founder-facing or both)** — declare the dual-register shape in frontmatter:

  ```yaml
  register:
    founder_mode: default
    technical_mode:
      shape: json_envelope | markdown_with_paths | diff | raw_tool_output | structured_summary
      triggers: [intent, --raw, /sulis:jargon]
  ```

  Operator-facing or agent-internal agents declare `register: { technical_mode: default }` and skip the founder-mode shape entirely.

- **Standards-phase classification** — declare which sulis standards apply at which phase per STANDARDS_RUBRIC. For founder-facing agents, this includes COACHING + TONE in the `output` phase:

  ```yaml
  standards:
    input: [REFERENTIAL_INTEGRITY_STANDARD]
    processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE]
    output: [CRITICAL_THINKING_STANDARD, TONE_STANDARD, COACHING_STANDARD]
  ```

- **Verification tier** — per SPIRAL_TEMPLATES tiering rules:
  - LIGHT — mechanical routing agents only (e.g., a pure classifier); justification required
  - STANDARD — most specialist agents (requirements-analyst, engineering-architect, security-reviewer)
  - HEAVY — coordinator + founder-facing agents (Sulis); any agent where misleading the founder carries high trust cost

- **Top-N gotchas** (≤ 7 per PD-02 fan-out constraint) — each must have a concrete prior-failure source (existing agent's body, prior-art transcript, methodology learning). For founder-facing or both: at least one addresses operator-vocab leakage in dispatched-specialist output; at least one addresses register-switch ambiguity.

- **Related skills + agents** — declare per REFERENTIAL_INTEGRITY_STANDARD in `agent.md` frontmatter `related_skills:` block. Include both skills the agent dispatches AND agents it dispatches as sub-agents.

**Pass criteria for Gate 2:**

- All twelve items written down in `VERIFICATION_REPORT.md`'s "Scope Lock" section
- No item is "TBD"; if something cannot be locked, return to Gate 1
- For founder-facing or both: founder-facing-conventions.md Rule 6 has been read; register declaration matches the Rule 6 shape
- For founder-facing or both: COACHING + TONE standards in `output:` phase classification
- "Could this be a skill instead?" answered NO with explicit justification (the agent needs its own conversational context, its own tool set, its own role definition that wouldn't fit in a skill)

### Gate 3 — Generate (authoring, LLM-driven)

**Standards:** MECE (MECE-01..04), Pyramid Principle (PP-01..04), Decision Framing / SCQA (DF-01..04), No Hyperbole (NH-01..04). See `plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md` §§5, 6, 7, 10. For founder-facing or both, additionally: TONE_STANDARD + COACHING_STANDARD.

**Goal:** produce the `agent.md` file using the Gate 2 lock as the contract, structured per MECE + Pyramid + SCQA.

Files to produce:

```
plugins/<plugin>/agents/<agent-name>.md
```

(Agents are single-file artifacts. No subdirectory. No scripts. No templates. The agent body IS the entire artifact.)

If the agent needs structured references (e.g., the Sulis agent cites founder-facing-conventions.md, COACHING_STANDARD.md, lifecycle.md), those references live at the plugin level (`plugins/<plugin>/references/`), not under the agent. Reference them via path in the agent.md body.

The `agent.md` must:

- Have a `description:` frontmatter field matching the Gate 2 dispatch trigger verbatim
- Have `standards:`, `verification_spiral:`, `related_skills:` frontmatter blocks per Gate 2 lock
- Have `register:` frontmatter block if Audience is founder-facing or both
- Optionally have `model:`, `tools:`, `user_invocable:` frontmatter fields per Gate 2 lock
- Lead with a "## Role" or equivalent section per Pyramid (PP-01..04) — role definition first, then workflow, then specifics
- Have a "## Required reading" section if the agent depends on standards or references the founder won't have in immediate context
- Have a "## Workflow" or "## Main loop" or "## When dispatched" section describing what the agent does step-by-step
- Have an "## Output shape" or "## Output contract" section describing what the agent produces (founder-mode shape AND technical-mode shape if dual-register)
- For founder-facing or both: include a section showing examples of founder-mode output passing TONE + COACHING (these become the agent's behavioural anchors)
- Pass the linguistic audit (NH-02 + TONE T-05): no prohibited terms ("comprehensive", "robust", "powerful", "revolutionary", "leverage", "magic", "seamless"); preferred vocabulary from TONE Section A used
- Use progressive disclosure: point to standards/references rather than restating them

**Pass criteria for Gate 3:**

- `agent.md` exists at `plugins/<plugin>/agents/<agent-name>.md` and parses (frontmatter is valid YAML)
- All Gate 2 frontmatter blocks present (`standards:`, `verification_spiral:`, `related_skills:`, optionally `register:` / `model:` / `tools:` / `user_invocable:`)
- The agent matches the Gate 2 lock (scope, audience, dispatch trigger, register, standards, verification tier, tools, gotchas, related)
- No reference file declared in `agent.md` is missing on disk (Codebase Referential Integrity precursor)
- Pyramid structure verified: first heading or paragraph states the role / what-the-agent-does
- Linguistic audit passes: zero prohibited terms; preferred vocabulary applied
- For founder-facing or both: at least one founder-mode example present; at least one technical-mode example present

### Gate 4 — Evaluate (verification spiral, scored under SPIRAL_TEMPLATES)

**Standards:** SPIRAL_TEMPLATES (tier templates + ACCA + Codebase Referential Integrity + Independence Check); for founder-facing or both: COACHING_STANDARD + TONE_STANDARD evaluated against agent output. See `plugins/sulis/references/standards/SPIRAL_TEMPLATES.md`, `COACHING_STANDARD.md`, `TONE_STANDARD.md`.

**Goal:** prove the agent actually works before publishing — by scoring it against the SPIRAL_TEMPLATES rubric for its declared tier and producing VERIFICATION_REPORT.md on disk. Founder-facing agents get extra perspectives.

#### The spiral run

Per SPIRAL_TEMPLATES tier defaults:

| Tier | Dimensions scored | Independence Check |
|---|---|---|
| LIGHT | ACCA only | No |
| STANDARD | ACCA + Evidence Grounding + Structural Coherence + Honest Uncertainty + Codebase Referential Integrity | No |
| HEAVY | STANDARD dimensions + Outcome-Specific Rigor + Independence Check | Yes (Agent subagent_type=Explore, fresh context) |

Each dimension gets a 1-5 score with threshold per SPIRAL_TEMPLATES; aggregate verdict = PASS only if all dimensions meet threshold.

#### Outcome-Specific Rigor for agents (HEAVY tier)

Three perspectives — the agent equivalent of add-skill's three (Trigger accuracy / Gotchas coverage / Functional completeness):

1. **Dispatch trigger precision** — hand a fresh context the `description:` + agent name only. Ask: in what parent-agent contexts would this agent be dispatched? Measure precision against intended dispatch set. Threshold: ≥ 85%.
2. **Tool-completeness check** — for every tool the agent's body claims to use, verify it's in the declared tools list. For every reference (skill, standard, agent) the body cites, verify it exists at the declared path (Codebase Referential Integrity feeds this). Threshold: 100% (any miss is a Gate-3 regression to fix).
3. **Output-shape verification** — run the agent against 3-5 representative scenarios. Each produces the declared output shape (founder-mode AND technical-mode if dual-register). ≥ 80% scenario success rate.

For full criteria see `references/founder-mode-perspectives.md` (the detail page for the founder-mode evaluation perspectives).

#### Coaching Delivery perspective (founder-facing or both only)

Score the agent's founder-mode example outputs against the COACHING_STANDARD seven-question Pass/Fail validation checklist:

1. Frames issues structurally, not personally? — PASS / FAIL
2. Invites calibration, not demands acceptance? — PASS / FAIL
3. Gives room to reach own conclusions (questions, hypotheses)? — PASS / FAIL
4. Preserves dignity, avoids blame? — PASS / FAIL
5. Matches relationship depth (no hard truths before trust)? — PASS / FAIL
6. Gives room to step up? — PASS / FAIL
7. Could the founder forward without embarrassment? — PASS / FAIL

Score: number-of-PASS / 7. Threshold: ≥ 6/7 (i.e., at most one FAIL with documented mitigation).

#### Tone Conformance perspective (founder-facing or both only)

Score the agent's founder-mode example outputs against the TONE_STANDARD seven-item validation checklist:

1. T-01 Pragmatic Authority (operator voice, not theorist)
2. T-02 Radical Clarity (plain English, fewest words)
3. T-03 Build + Market (technical connected to outcome)
4. T-04 Governance (AI as governed activity)
5. T-05 Vocabulary Governance (three-zone framework applied)
6. Systemic Lexicon (preferred terms; established terms preserved)
7. Forbidden Vocabulary (none present)

Score: number-of-PASS / 7. Threshold: ≥ 6/7.

#### Register Switch Correctness perspective (founder-facing or both only)

For agents declaring dual register, verify the register-switch mechanics work:

1. **Intent-triggered switch:** present the agent with a fresh context including a request like "show me the technical version" — does it correctly switch and emit the declared technical-mode shape? Threshold: 5/5 test scenarios pass.
2. **`--raw` flag handling:** present the agent with `--raw` in a tool invocation — does it emit the declared technical-mode shape directly with no confirmation? Threshold: 5/5 pass.
3. **Session toggle integration:** verify the agent reads `SULIS_JARGON` env var (or equivalent session state) and toggles register accordingly. Threshold: 5/5 pass.
4. **Default-register correctness:** absent any trigger, agent emits founder-mode. Threshold: 5/5 pass.

Score: total-passes / 20. Threshold: ≥ 18/20.

#### Codebase Referential Integrity (all tiers, very high leverage for agents)

Every pre-existing entity the agent names must trace to the codebase with a verified path:

- Standards (`plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md`, etc.)
- Skills cited as dispatchable (`/sulis:run-wp`, `/sulis:specify`, etc.)
- Reference docs (`plugins/sulis/references/lifecycle.md`, `founder-facing-conventions.md`)
- Other agents dispatched (`subagent_type=executor`, `subagent_type=Explore`)
- Tool wrapper modules (`plugins/sulis/_lib/tools/*.py`)

Entities marked "NEW — to be created" are exempt but MUST be explicitly flagged. Unflagged new entities count as unverified pre-existing entities (= score reduction).

This is the dimension that catches the hallucination failure mode for agents ("dispatches the engineering-architect" without that agent existing yet at the named path).

#### Independence Check (HEAVY tier only)

Spawn `Agent(subagent_type="Explore")` in fresh context. Inputs: the agent's `agent.md` path + applicable standards references + (for founder-facing) a sample of declared founder-mode examples. Explicit exclusion: NO access to the generating agent's reasoning. Task: score the agent against the declared dimensions using only the standards.

Independence dimension threshold: ≥ 3/5. If below, spiral BLOCKED even if self-scored dimensions pass.

#### Iteration termination

Per SPIRAL_TEMPLATES: max 3 iterations; terminate on sufficient (all thresholds met), max_iterations (capture irreducible blocker), or irreducible blocker declared up-front.

**Pass criteria for Gate 4:**

- VERIFICATION_REPORT.md exists at `plugins/<plugin>/agents/<agent>.VERIFICATION_REPORT.md` (sibling to the agent file) or at `plugins/<plugin>/agents/iterations/{agent-name}/{N}/VERIFICATION_REPORT.md` (for deepening mode)
- File contains "Verdict: PASS"
- All scored dimensions meet threshold; for HEAVY tier, Independence Check ≥ 3
- For founder-facing or both: Coaching Delivery ≥ 6/7; Tone Conformance ≥ 6/7; Register Switch Correctness ≥ 18/20
- Single filesystem check: `test -f ... && grep -q "Verdict:.*PASS" ...` returns 0

### Gate 5 — Adversarial Review (publish gate)

**Standards:** Adversarial Testing Posture (AT-01..03), Falsifiability Requirement (FR-01..04). See `plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md` §§3, 13.

**Goal:** name the top ways the agent could mislead the parent agent (dispatch routing failure), the founder (output shape failure), or downstream systems (output contract failure). For each, either prevent it in the agent or document it as an open risk with revisit-trigger.

AT-01 default posture: seek evidence the agent WILL fail before evidence it won't. AT-02 ordering: test riskiest assumptions first.

Misuse cases sometimes surface during Gate 4 functional-scenario testing. Maintain a running candidate list during Gate 4; finalise + categorise (PREVENTED / OPEN_RISK) at Gate 5.

#### Audience-agnostic categories

- **Over-dispatch:** description matches too broadly, parent agent routes to this agent in contexts it doesn't own
- **Under-dispatch:** description matches too narrowly, parent agent fails to route in contexts it should own
- **Tool leakage:** agent body uses a tool not in declared tools list (would fail at runtime)
- **Tool over-declaration:** agent declares tools it doesn't use (principle of least privilege violation)
- **Context bloat:** agent body inlines content that should be progressive-disclosed via references
- **Vocabulary collision** with another agent's dispatch trigger
- **Silent failure of progressive disclosure** (declared reference missing — Codebase Referential Integrity = 0/5)
- **Model misalignment:** declared model can't handle the complexity (haiku for an agent that needs long-context reasoning)
- **Reference rot:** the agent depends on a skill or other agent that may be renamed or deleted — handle via the standard `related_skills:` block with explicit notes

#### Audience-conditional: founder-facing agent misuse cases (NEW in add-agent v0.1.0)

- **MUC-A1: Prescriptive language leak** — agent emits "You need to..." / "You should..." / "The problem is..." despite COACHING citation. Mitigation: Gate 4 Coaching Delivery perspective; pre-emission scan.
- **MUC-A2: Banned vocabulary leak** — agent emits "robust" / "comprehensive" / "powerful" / "magic" / "leverage" despite TONE citation. Mitigation: Gate 4 Tone Conformance perspective; pre-emission scan against TONE forbidden list.
- **MUC-A3: Defensive-triggering phrase in a recommendation** — agent surfaces a finding using language that triggers founder defensiveness (e.g., "Your code has 5 security issues"). Mitigation: COACHING Tenet 1 (structural framing); pre-emission validation against the Pass/Fail checklist.
- **MUC-A4: Commercial outcome missing when describing a feature/change** — agent reports completion without connecting to user impact (e.g., "Change shipped" not "Change shipped: auth-bug fix is live for the ~500 users affected"). Mitigation: TONE T-03; output-shape template includes "outcome" field.

Founder-facing or both agents MUST address all 4 of MUC-A1..A4.

#### Audience-conditional: dual-register agent misuse cases (NEW in add-agent v0.1.0)

- **MUC-R1: Technical-mode leaks into founder-mode default** — agent emits JSON envelope or IDs-only string when founder expected plain English. Mitigation: register flag checked at emission time; default-register check in Gate 4.
- **MUC-R2: Founder-mode drops signal the founder needed** — file path or identifier stripped when it was the actionable signal. Mitigation: surface load-bearing identifiers in founder-mode too (per founder-facing-conventions Rule 2: readable name with ID in parens).
- **MUC-R3: Register-switch ambiguity** — founder says "more detail" — agent unsure whether to deepen founder-mode or switch to technical-mode. Mitigation: default is "deeper in founder-mode"; ask explicitly if technical-mode seems intended.

Dual-register agents (any agent with a `register:` frontmatter block declaring both modes) MUST address all 3 of MUC-R1..R3.

#### MUC-F1..F6 (founder-facing skills extended to agents)

The six MUC-F cases from `founder-facing-conventions.md` also apply to founder-facing agents:

- MUC-F1: Operator jargon leak in error string
- MUC-F2: Shortcut acts on stale state without echoing
- MUC-F3: Destructive action triggered by ambiguous founder phrasing
- MUC-F4: Number-of-items overwhelm
- MUC-F5: Source-of-truth false-positive (state not updated after out-of-band resolution)
- MUC-F6: Stubbed-vs-active rendering blur

Founder-facing or both agents MUST address at least 3 of MUC-F1..F6 (per Founder-Facing Conventions).

For each top 3+ risk identified:

- **Name** the misuse case (use MUC-A / MUC-R / MUC-F numbering for the typed categories; free-form for audience-agnostic)
- **Describe** what the agent might do wrong (per FR-03 pre-mortem)
- **State** what the agent does to prevent it (PREVENTED with mechanism) or document it (OPEN_RISK with structured `revisit_by:` trigger — date / event / condition / never)

#### What an acceptable OPEN_RISK looks like (worked example)

OPEN_RISK is acceptable when the residual likelihood is low, the impact is bounded, and there's a concrete revisit-trigger. PREVENTED is preferred but not always achievable in v0.1.0.

Worked example for a hypothetical specialist agent that occasionally slips to defensive-triggering phrasing under high-context load:

> **MUC-A3 (defensive-triggering phrase in a recommendation) — OPEN_RISK**
>
> - **Description:** Agent detects structural framing correctly in ~95% of cases but may slip to "Your code has X issues" under high-context load (>50K tokens consumed before the recommendation).
> - **Why accepted:** Likelihood is low (~5%); impact is recoverable (founder can request rephrasing); requires fixing requires a context-length monitor that's out of scope for v0.1.0.
> - **revisit_by:** trigger — first 5 reported instances of defensive-triggering phrasing OR Q3 2026, whichever comes first
> - **Workaround for users in the meantime:** if the agent emits defensive-triggering phrasing, the founder can run `/sulis:jargon on` for the technical version (operator-direct doesn't carry the coaching layer's softening obligations).

OPEN_RISK without a structured revisit-trigger = automatic Gate 5 BLOCK. The trigger must be concrete (date / event / condition / never), not vague ("eventually" / "when we get to it").

**Pass criteria for Gate 5:**

- ≥ 3 misuse cases named in VERIFICATION_REPORT.md's "Adversarial Review" section
- For founder-facing or both: ALL 4 of MUC-A1..A4 addressed
- For dual-register agents: ALL 3 of MUC-R1..R3 addressed
- For founder-facing or both: ≥ 3 of MUC-F1..F6 addressed
- All marked as either PREVENTED (with mechanism) or OPEN_RISK (with documented impact + rationale + revisit-trigger)
- AT-03: any confirmation-seeking validation in Gate 4 documented as deliberate deviation

## Modes

### Greenfield mode (default)

All 5 gates from scratch. Use `templates/agent.md.template` as the starting shape.

### Deepening (upsurge) mode

When invoked on an existing agent (e.g., re-running add-agent on `executor` to add a new step or to embed COACHING):

- **Gate 1** still runs — BRIEF_PACK + primitive discovery; existing agent counted as prior art; the question becomes "what does this agent currently miss?"
- **Gate 2** locks the deepening scope — what new primitives are in scope this iteration? What new standards are being adopted?
- **Gate 3** EXTENDS the existing agent.md (does not rewrite); preserves existing dispatch trigger if it still routes correctly
- **Gate 4** re-scores the full agent — not just the delta; produces VERIFICATION_REPORT.md at `iterations/{agent-name}/{N}/VERIFICATION_REPORT.md` to preserve history
- **Gate 5** runs adversarial sweep on the new primitives + checks for regressions on existing ones
- Iteration termination: VERIFICATION_REPORT shows all dimensions ≥ threshold AND author marks "no productive lines of inquiry remain"

### Standards-grounded re-author mode

For pre-standards agents (authored before v0.1.0 of add-agent): one-time re-author against the standards. Same as Greenfield mode but with existing agent.md as the starting Gate 3 output. This is the path for renaming `concierge.md` → `sulis.md` and embedding COACHING + TONE.

### Mode-detection heuristic

When `add-agent` is invoked, it auto-detects which mode applies:

| Heuristic | Mode |
|---|---|
| Target agent file does not exist on disk | **Greenfield** |
| File exists AND has `verification_spiral:` frontmatter block | **Deepening (upsurge)** |
| File exists AND lacks `verification_spiral:` frontmatter block | **Standards-grounded re-author** |

The author can override via explicit `--mode greenfield\|deepen\|re-author` flag if the heuristic is wrong. See `references/methodology.md` §"The mode-detection heuristic" for the rationale.

## Publishing

After all five gates pass:

1. Bump the owning plugin's version in `plugins/<plugin>/.claude-plugin/plugin.json`
2. Bump marketplace version in `.claude-plugin/marketplace.json`
3. Update the plugin's `CHANGELOG.md` with a v entry naming the new agent
4. Commit + push following conventional-commits style

## Gotchas

- **The `description:` field IS the dispatch contract.** Parent agents (Sulis, orchestrators, user-facing CLI) scan descriptions to route. A vague or overly-broad description causes routing chaos; a too-specific description gets dispatched in fewer contexts than intended. Write it as a trigger condition that the parent agent can match on.
- **Codebase Referential Integrity catches more for agents than for skills.** Agents typically cite many references (standards, other agents, skills, tool modules) — every cited path must resolve. Unresolved refs = silent failure at dispatch time.
- **"Could this be a skill instead?" is a real question.** Agents are heavier than skills — they carry their own context window, their own tool budget, their own dispatch overhead. If the work doesn't require a conversational context or a distinct role, prefer a skill.
- **Founder-facing agents inherit the founder-tone stack obligations.** Forgetting to cite TONE / COACHING / Founder-Facing Conventions at Gate 2 = Gate 4 will catch it via Coaching Delivery + Tone Conformance perspectives, but at the cost of a Gate-3 redraft. Lock it at Gate 2.
- **Dual-register declaration is binding.** If you declare `register: { founder_mode: default, technical_mode: { ... } }`, Gate 4 verifies the technical-mode mechanics work. Don't declare dual-register on an agent that doesn't actually support it.
- **Tools list defaults to `*` (inherit-all).** Per principle of least privilege, declare only what's needed. `*` is acceptable for orchestrator/coordinator agents that dispatch many things; not acceptable for specialist agents.
- **Model preference matters for cost + latency.** Haiku for routing/classification; Sonnet for most specialists; Opus for long-context coordinator agents (like Sulis). Omitting = inherit, which may surprise.
- **`user_invocable` defaults to `false`.** Forgetting it means the founder can't `claude --agent {name}`. Always declare it explicitly for agents intended to be founder-callable.

## Vocabulary

- **Gate** — a methodology checkpoint with explicit pass/fail criteria. Five gates are sequential.
- **BRIEF_PACK** — the structured output of `scripts/inventory.py`; Gate 1's deliverable.
- **Dispatch trigger** — the `description:` field; the contract by which a parent agent routes to this agent.
- **Register** — the language register an agent speaks. Founder-mode (full tone stack) or technical-mode (operator-direct).
- **Dual register** — an agent that supports both founder-mode (default) and technical-mode (on request) per founder-facing-conventions.md Rule 6.
- **MUC-A1..A4** — founder-facing agent-specific misuse cases (Prescriptive / Banned-Vocab / Defensive-Trigger / Missing-Outcome).
- **MUC-R1..R3** — dual-register misuse cases (Mode-Leak / Signal-Drop / Switch-Ambiguity).
- **Coaching Delivery** — Gate 4 perspective scoring founder-mode output against COACHING_STANDARD seven-question checklist.
- **Tone Conformance** — Gate 4 perspective scoring founder-mode output against TONE_STANDARD seven-item checklist.
- **Register Switch Correctness** — Gate 4 perspective scoring dual-register mechanics (intent / `--raw` / `/sulis:jargon`).
- **Dispatch trigger precision** — Gate 4 sub-perspective measuring how accurately a parent agent routes based on the description.
- **VERIFICATION_REPORT.md** — the per-agent audit artifact required on disk by SPIRAL_TEMPLATES. Single filesystem check determines compliance.

## When to invoke this skill

- A new agent is needed for a stage or specialist role that no existing agent owns
- An existing agent needs to be re-authored against the v0.1.0 standards (the legacy `concierge.md` → `sulis.md` rename)
- An existing agent needs upsurging — extending coverage against the standards (deepening mode)
- A plugin consolidation requires bringing an agent from another plugin into sulis (the consolidation skill dispatches add-agent for the agent-rewrite step)

## When NOT to invoke this skill

- The work is a one-off agent for a single project (write it inline; don't ship every agent as a marketplace artifact)
- The proposed agent is actually a skill (skills are lighter; if the work doesn't need its own conversational context, use `add-skill` instead)
- The proposed work is a slash command (slash commands invoke skills, not agents — use `add-skill`)
- The proposed work is a plugin (plugins host agents + skills; use the plugin scaffolding pattern, not `add-agent`)
- A small edit to an existing agent (Edit the agent.md directly; full five-gate is overkill — but consider the deepening mode if the edit adds primitives or changes the dispatch contract)
