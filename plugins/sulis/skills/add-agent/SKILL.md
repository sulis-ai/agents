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

`add-agent` borrows `add-skill`'s scaffolding wholesale. The differences are concentrated in five places (three from v0.1.0, two new in v0.2.0):

| Where | What's different |
|---|---|
| **Gate 1 (v0.2.0)** | New sub-step 1c **Specialist Boundary Analysis** for coordinator/router agents — produces a binding Specialist Boundary Table mapping every artifact-producing skill to its owning specialist + the dispatch trigger that fires. Becomes the source-of-truth for Gate 2's `delegation:` block. |
| **Gate 2 (v0.1.0)** | Register declaration (founder + technical mode shapes); dispatch trigger as the load-bearing description; tools declaration; model preference; `user_invocable` flag |
| **Gate 2 (v0.2.0)** | Three new declarative frontmatter blocks lifted from `studios/.claude/agents/explorer.yaml`: `context_sources:` (startup file loads with `required:` + `purpose:`), `delegation:` (coordinator-only — `artifact_owners` map + `dispatch_via` map + `authorisation` policy; binding on body behaviour), `routes_to:` (specialist routing targets with founder-intent `triggers:`) |
| **Gate 3 (v0.2.0)** | Tier-aware body-size budget (LIGHT 150 / STANDARD 300 / HEAVY 500 lines target; 1.5× hard ceiling with mandatory `## Why this is big` rationale paragraph); per-section `> Standards:` citation header rule (cite, don't restate — the body's job is to apply the standard in the agent's context, not duplicate the standard's content) |
| **Gate 4 (v0.1.0)** | Two perspectives for founder-facing agents — **Coaching Delivery** (passes the COACHING_STANDARD seven-question checklist) + **Register Switch Correctness** (correctly switches on intent / `--raw` / `/sulis:jargon`); **Tone Conformance** perspective (passes the TONE_STANDARD seven-item checklist) |
| **Gate 4 (v0.2.0)** | Two more perspectives — **Delegation Discipline** (coordinator/router only; 4-check scoring whether the agent CAN delegate correctly) + **Body Density Conformance** (all agents; 4-check scoring Gate 3 body-size + citation rules are honoured) |
| **Gate 5 (v0.1.0)** | Misuse cases — MUC-A1..A4 (founder-facing agent specific) + MUC-R1..R3 (register-aware specific) layered on top of the audience-agnostic + MUC-F1..F6 categories |
| **Gate 5 (v0.2.0)** | New misuse case **MUC-A5 Specialist-Bypass** — coordinator agent authors specialist-owned artifact directly instead of dispatching. Catches the failure mode that drove v0.2.0 (Sulis authored WP-005..WP-007 inline instead of dispatching back to SEA's plan-work skill). |

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

#### Sub-step 1c: Specialist Boundary Analysis (NEW in v0.2.0 — coordinator/router agents only)

If the proposed agent is a **coordinator** (dispatches to specialists across multiple phases) or a **router** (chooses between specialists based on input), it MUST declare its delegation boundary explicitly. Skip this sub-step for pure-specialist agents (executor, requirements-analyst) — they're dispatched, not dispatchers.

Heuristic for whether this sub-step applies:

| Signal | Implication |
|---|---|
| Agent body contains "What You Are Not" or "specialists are your team" | coordinator → run sub-step |
| Agent has `kind: primary` or `kind: coordinator` (if marketplace adopts the field) | coordinator → run sub-step |
| Agent body cites ≥ 3 distinct specialist agents | coordinator → run sub-step |
| Agent body describes a multi-phase journey owned by it | coordinator → run sub-step |
| Agent dispatches via Agent tool to ≥ 2 distinct `subagent_type`s | coordinator → run sub-step |
| None of the above | specialist → skip sub-step |

When the sub-step applies, produce a **Specialist Boundary Table**:

| Specialist (subagent_type) | Owns these artifacts | Dispatch trigger (founder request that fires the dispatch) | Coordinator's role |
|---|---|---|---|
| engineering-architect | TDD.md, ADR-NNN.md, WP-NNN.md, INDEX.md, DECOMPOSE_VALIDATION.md | "design the technical blueprint" / "break this into tasks" / "amend the WP set" / "add a new WP" / mid-session detection of incomplete WP coverage | recommend `/sulis:draft-architecture` or `/sulis:plan-work`; read produced artifacts; translate to founder English |
| requirements-analyst | SRD.md, NFR.md, PRIMITIVE_TREE.jsonld, GLOSSARY.md, MISUSE_CASES.md | "interview me about what this needs to do" / "capture the requirements" | recommend `claude --agent requirements-analyst`; read produced artifacts |
| executor | implementation code + tests per WP; commits + branches | Phase 5 (WP execution); spawned by run-all skill | spawn via Agent tool; translate progress + blockers |
| security-reviewer | viability-report-*.md, SF-NNN-*.md | Phase 7 (security review); "audit the codebase" | recommend `/sulis:codebase-assess`; translate findings to business risk |

For each row, the coordinator's role MUST be one of: **dispatch (recommend)**, **dispatch (spawn)**, **read + translate**, or **never** — there's no "and also author this myself" option. If the body has a section like "What You Are Not" naming a specialist, the table must have a corresponding row.

**Specialist coverage check.** Every artifact-producing skill in the marketplace must appear in at least one row's "Owns these artifacts" column, OR be explicitly excluded with a documented reason (e.g., "out of scope for this coordinator's domain"). If a skill exists but isn't claimed by any specialist in the table, the coordinator's delegation policy has a gap — either add a row pointing to whichever specialist now owns it, or escalate to the user before Gate 2.

The table becomes the source-of-truth for the `delegation:` and `routes_to:` frontmatter blocks at Gate 2. If the coordinator later finds itself drafting an artifact whose row says "dispatch (recommend)" or "dispatch (spawn)", that's a Gate-5 MUC-A5 violation.

**Pass criteria for Gate 1:**

- BRIEF_PACK produced and reviewed
- Dispatch-trigger collisions resolved or explicitly waived with reason
- "No existing agent covers this" carries an explicit CC verdict
- "Could this be a skill instead?" question explicitly answered — record the answer in VERIFICATION_REPORT
- Primitive decomposition completed; primitives pass PG-02 + PG-04; provenance recorded
- **For coordinator/router agents:** Specialist Boundary Table produced + specialist-coverage check passes (no orphan artifact-producing skills); table is the source-of-truth for Gate 2's `delegation:` block

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

- **Context sources (NEW in v0.2.0)** — declarative frontmatter block listing every file the agent loads at startup. Each entry has `path:`, `required:` (true/false), and `purpose:` (one-line justification). This replaces ad-hoc "read X first" instructions scattered through the body. Pattern lifted from `studios/.claude/agents/explorer.yaml`:

  ```yaml
  context_sources:
    - path: .sulis/{project}/JOURNEY.md
      required: false
      purpose: "Current phase + decisions + open questions; null on first run"
    - path: plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md
      required: true
      purpose: "13 principles applied to every analytical decision"
    - path: plugins/sulis/references/standards/COACHING_STANDARD.md
      required: true
      purpose: "Seven tenets for surfacing findings without triggering defensiveness"
  ```

  Loaded at startup means the agent's first action (before any user-facing response) is to read every `required: true` source. The `purpose:` annotation makes verification easy: Gate 4 can check that each loaded source is actually referenced in the body for its stated purpose.

- **Delegation policy (NEW in v0.2.0 — coordinator/router agents only)** — declarative frontmatter block binding the agent's delegation behaviour. For coordinator/router agents identified at Gate 1 sub-step 1c, the Specialist Boundary Table from Gate 1 becomes a `delegation:` block:

  ```yaml
  delegation:
    artifact_creation: dispatch     # dispatch | direct | mixed
    direct_threshold: "JOURNEY.md updates; one-line decision-discipline journal entries"
    artifact_owners:
      # Maps artifact-class → specialist that owns it
      TDD.md: engineering-architect
      ADR-*.md: engineering-architect
      WP-*.md: engineering-architect
      INDEX.md: engineering-architect
      DECOMPOSE_VALIDATION.md: engineering-architect
      SRD.md: requirements-analyst
      NFR.md: requirements-analyst
      PRIMITIVE_TREE.jsonld: requirements-analyst
      GLOSSARY.md: requirements-analyst
      MISUSE_CASES.md: requirements-analyst
      viability-report-*.md: security-reviewer
      SF-*.md: security-reviewer
    dispatch_via:
      engineering-architect: ["recommend /sulis:draft-architecture", "recommend /sulis:plan-work", "Agent tool spawn"]
      requirements-analyst: ["recommend claude --agent requirements-analyst"]
      executor: ["Agent tool spawn (via run-all skill)"]
      security-reviewer: ["recommend /sulis:codebase-assess"]
    authorisation: silent           # silent | user-approval-required
  ```

  **The `artifact_owners` map is binding.** When the coordinator finds itself about to author a file whose extension matches a row in this map, it MUST dispatch instead. Direct authoring of a mapped artifact is a Gate-5 MUC-A5 violation (Specialist-Bypass).

  Operator-facing or specialist agents (not coordinators) declare `delegation: null` and skip this block.

- **Routes to (NEW in v0.2.0 — coordinator/router agents only)** — declarative frontmatter block listing the specialists this agent routes to + the founder-intent trigger that fires each route. Pattern lifted from `studios/.claude/agents/explorer.yaml`:

  ```yaml
  routes_to:
    - slug: engineering-architect
      description: "Technical design, architecture decisions, work-package authoring"
      triggers: ["design", "architect", "break this into tasks", "amend the WP set"]
    - slug: requirements-analyst
      description: "Requirements interview, specification capture"
      triggers: ["capture requirements", "interview me about", "what does this need to do"]
    - slug: executor
      description: "Implement a Work Package end-to-end"
      triggers: ["build it", "Phase 5", "run-all"]
    - slug: security-reviewer
      description: "Codebase security viability assessment"
      triggers: ["security review", "audit the codebase", "Phase 7"]
  ```

  The `triggers` array gives the parent-agent (or Sulis itself) explicit signals for routing. Verification at Gate 4 includes a "Routing precision" check — fresh-context test of each trigger producing the expected route.

  Specialist-only agents declare `routes_to: []` and skip the routing list.

**Pass criteria for Gate 2:**

- All fifteen items written down in `VERIFICATION_REPORT.md`'s "Scope Lock" section
- No item is "TBD"; if something cannot be locked, return to Gate 1
- For founder-facing or both: founder-facing-conventions.md Rule 6 has been read; register declaration matches the Rule 6 shape
- For founder-facing or both: COACHING + TONE standards in `output:` phase classification
- "Could this be a skill instead?" answered NO with explicit justification (the agent needs its own conversational context, its own tool set, its own role definition that wouldn't fit in a skill)
- **For coordinator/router agents:** `context_sources:`, `delegation:`, and `routes_to:` frontmatter blocks fully populated from the Gate 1 Specialist Boundary Table

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

#### Body-size budget (NEW in v0.2.0)

Per add-skill's right-sizing discipline (and SPIRAL_TEMPLATES tier limits), agent bodies have tier-aware size targets:

| Tier | Target body length | Hard ceiling (1.5× target — exceed only with rationale) |
|---|---|---|
| LIGHT | ≤ 150 lines | 225 lines |
| STANDARD | ≤ 300 lines | 450 lines |
| HEAVY | ≤ 500 lines | 750 lines |

If the draft exceeds the target, the author MUST do one of:

1. **Refactor**: move restated standards content out of the body. Cite standards via `> Standards: ...` headers (see citation rule below) and trust the reader to follow the reference.
2. **Add a `## Why this is big` paragraph** at the top of the body explaining what's load-bearing about the length. Acceptable rationales: "agent embeds a workflow that spans 7 phases each with non-skippable detail" or "agent is the marketplace's single front-door and consolidates 5 specialist roles". Unacceptable rationales: "comprehensive coverage" / "to be safe" / "in case the agent forgets".

If the draft exceeds the hard ceiling AND has no acceptable rationale, Gate 3 BLOCKS — return to refactor.

**Why this matters:** every line in the body costs tokens at every dispatch. A 1800-line body costs ~30K tokens per session start; a 500-line body costs ~8K. The difference compounds across 10+ sessions/day. Beyond cost: density defeats pattern-matching — when the same teaching shows up 5× in different shapes, the agent can't reliably extract the load-bearing rule.

#### Per-section standards-citation header (NEW in v0.2.0)

Every section that operationalises a standard MUST cite that standard at the top of the section as a `> Standards:` blockquote. Pattern lifted from `studios/.claude/agents/explorer.yaml`:

```markdown
### Facilitation Tone
> Standards: COACHING_STANDARD.md (seven tenets), TONE_STANDARD.md (T-01, T-02, NH-02)

You are a creative collaborator, not an evaluator. ...
```

The body's job is to **apply** the standard in the agent's context, not to **restate** it. Three rules:

1. **Cite the standard's canonical path + the specific principles** (e.g., `(EH, HU)` or `(T-01, T-02)`) at section top.
2. **Worked examples are OK** — they make the standard concrete in the agent's domain (e.g., "for Sulis, structural-not-personal looks like: 'There's a gap in the auth flow' not 'you missed authentication'"). They're cheap signal.
3. **Restating the principles is NOT OK** — if the body has a numbered list of the seven COACHING tenets identical to the standard's, delete the list and cite.

A body that cites N standards and restates none of them is dense + scannable. A body that restates 5 standards is bloated + brittle (when the standard updates, the body diverges).

**Verification at Gate 4:** Codebase Referential Integrity already checks that cited paths resolve. Gate 4 adds a check that each section with operational content (workflow steps, behaviour rules, output discipline) has a `> Standards:` header citing the standard it implements — OR a documented exception (e.g., "agent-specific behaviour not derived from a published standard").

**Pass criteria for Gate 3:**

- `agent.md` exists at `plugins/<plugin>/agents/<agent-name>.md` and parses (frontmatter is valid YAML)
- All Gate 2 frontmatter blocks present (`standards:`, `verification_spiral:`, `related_skills:`, optionally `register:` / `model:` / `tools:` / `user_invocable:` / `context_sources:` / `delegation:` / `routes_to:`)
- The agent matches the Gate 2 lock (scope, audience, dispatch trigger, register, standards, verification tier, tools, gotchas, related, context sources, delegation policy, routes)
- No reference file declared in `agent.md` is missing on disk (Codebase Referential Integrity precursor)
- Pyramid structure verified: first heading or paragraph states the role / what-the-agent-does
- Linguistic audit passes: zero prohibited terms; preferred vocabulary applied
- For founder-facing or both: at least one founder-mode example present; at least one technical-mode example present
- **Body within tier size target OR has documented `## Why this is big` rationale** (NEW in v0.2.0)
- **Every operational section has `> Standards:` citation header OR documented exception** (NEW in v0.2.0)

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

#### Delegation Discipline perspective (NEW in v0.2.0 — coordinator/router agents only)

For agents identified at Gate 1 sub-step 1c as coordinator/router, verify the delegation policy is binding (not aspirational):

1. **Declarative block present** — frontmatter contains a `delegation:` block with `artifact_creation`, `artifact_owners`, `dispatch_via`, and `authorisation` fields populated. PASS / FAIL.

2. **What-You-Are-Not coverage** — every specialist named in the body's "What You Are Not" (or equivalent) section has a corresponding row in the `delegation.artifact_owners` map OR is excluded with documented reason. PASS / FAIL.

3. **Unambiguous dispatch triggers** — for every specialist in `routes_to:`, the body has at least one section with an explicit "when you encounter X, dispatch via Y" instruction. No specialist is implicitly invoked only — every specialist has an explicit trigger. PASS / FAIL.

4. **Mid-session amendment trigger present** — body explicitly addresses the case where specialist output is incomplete and the coordinator notices a gap mid-session. The trigger must be "dispatch back to the specialist", not "fill the gap myself". This catches the Phase-5-WP-authoring failure mode that drove v0.2.0. PASS / FAIL.

Score: number-of-PASS / 4. Threshold: ≥ 3/4 (i.e., at most one FAIL with documented mitigation).

The Delegation Discipline perspective is the operational complement to Gate 5's MUC-A5 (Specialist-Bypass). Gate 4 measures whether the agent CAN delegate correctly; Gate 5 documents the residual risk if it doesn't.

For specialist agents (not coordinators), this perspective is skipped — record "N/A — specialist agent, not a coordinator" in VERIFICATION_REPORT.

#### Body Density Conformance perspective (NEW in v0.2.0 — all agents, HEAVY tier weighted)

Verify Gate 3's body-size + standards-citation rules are actually honoured:

1. **Body size within target** — agent body line count ≤ tier target (LIGHT 150 / STANDARD 300 / HEAVY 500); OR ≤ hard ceiling (1.5× target) with `## Why this is big` rationale paragraph present + acceptable. PASS / FAIL.

2. **Per-section standards citations** — every operational section (workflow steps, behaviour rules, output discipline, decision rules) has a `> Standards: ...` blockquote header at the top OR documents an exception. Sample 5 sections at random; threshold 4/5 PASS.

3. **No standard restatement** — for each standard cited in `standards:` frontmatter, the body does NOT contain a numbered list of the standard's principles identical to the standard's. Sample 3 standards; threshold 3/3 (any restatement = FAIL — refactor required at Gate 3).

4. **Citation paths resolve** — every `> Standards:` blockquote cites a file that exists at the cited path (overlaps with Codebase Referential Integrity but specific to the citation headers). PASS / FAIL.

Score: number-of-PASS / 4. Threshold: ≥ 3/4 for STANDARD tier; ≥ 4/4 for HEAVY tier (stricter because HEAVY agents are highest-cost-per-dispatch).

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
- **For coordinator/router agents:** Delegation Discipline ≥ 3/4 (NEW in v0.2.0)
- **For all agents:** Body Density Conformance ≥ 3/4 (STANDARD tier) or ≥ 4/4 (HEAVY tier) (NEW in v0.2.0)
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

- **MUC-A5: Specialist-Bypass (NEW in v0.2.0 — coordinator/router agents only)** — coordinator agent encounters mid-session work that belongs to a declared specialist (artifact authoring, finding triage, design edit, WP amendment) and authors the artifact directly instead of dispatching. Concrete failure pattern: SEA's `/sulis:plan-work` produces 4 WPs covering the mechanism; coordinator notices a gap in Phase-5/6 integration coverage; coordinator authors WP-005, WP-006, WP-007 directly + updates INDEX.md + DECOMPOSE_VALIDATION.md inline instead of dispatching back to SEA. Result: artifact provenance is wrong (specialist didn't produce it), specialist's validation rubric wasn't applied to the additions, and the coordinator silently absorbed the specialist's responsibility.

  Mitigation stack:
  - **Gate 2 declarative `delegation:` block** with `artifact_owners` map — body cannot author a mapped artifact without violating its own declared policy
  - **Gate 4 Delegation Discipline perspective check 4** — body explicitly addresses mid-session amendment with dispatch-not-direct trigger
  - **Body explicit trigger** — section like "When you encounter a gap in specialist output mid-session" naming the specific failure mode + the dispatch as the response
  - **Pre-emission scan in body** — coordinator's pre-emission gate (the silent check before any artifact write) includes "is this file's extension or path in `delegation.artifact_owners`? If yes, abort write + dispatch instead."

  Coordinator/router agents (any agent with a `delegation:` frontmatter block declaring `artifact_creation: dispatch`) MUST address MUC-A5.

Founder-facing or both agents MUST address all 4 of MUC-A1..A4. Coordinator/router agents (overlapping category) MUST also address MUC-A5.

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
- For coordinator/router agents: MUC-A5 addressed (NEW in v0.2.0)
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
- **MUC-A5** (NEW in v0.2.0) — Specialist-Bypass misuse case (coordinator authors specialist-owned artifact directly).
- **MUC-R1..R3** — dual-register misuse cases (Mode-Leak / Signal-Drop / Switch-Ambiguity).
- **Coaching Delivery** — Gate 4 perspective scoring founder-mode output against COACHING_STANDARD seven-question checklist.
- **Tone Conformance** — Gate 4 perspective scoring founder-mode output against TONE_STANDARD seven-item checklist.
- **Register Switch Correctness** — Gate 4 perspective scoring dual-register mechanics (intent / `--raw` / `/sulis:jargon`).
- **Delegation Discipline** (NEW in v0.2.0) — Gate 4 perspective scoring whether a coordinator/router agent CAN delegate correctly (declarative block present, what-you-are-not coverage, unambiguous triggers, mid-session amendment trigger).
- **Body Density Conformance** (NEW in v0.2.0) — Gate 4 perspective scoring whether Gate 3 body-size + standards-citation rules are honoured.
- **Specialist Boundary Table** (NEW in v0.2.0) — Gate 1 sub-step 1c artifact for coordinator/router agents; maps artifact classes → owning specialists + dispatch mechanism. Source-of-truth for the `delegation:` frontmatter block.
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
