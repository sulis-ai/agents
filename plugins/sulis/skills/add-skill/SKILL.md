---
name: add-skill
description: Use when the user wants to author a new skill in the Claude Code marketplace, formalise an existing repeatable workflow as a published skill, deepen an existing skill ("upsurge"), or get methodology-driven quality consistency rather than ad-hoc SKILL.md authoring. Walks a five-gate flow grounded in the five sulis standards (Critical Thinking / Decomposition Procedure / Spiral Templates / Standards Rubric / Referential Integrity).
standards:
  input: [REFERENTIAL_INTEGRITY_STANDARD]
  processing: [CRITICAL_THINKING_STANDARD, DECOMPOSITION_PROCEDURE]
  output: [CRITICAL_THINKING_STANDARD]
verification_spiral:
  tier: heavy
  template_base: HEAVY_TIER_DEFAULT
  custom_dimensions:
    - name: "Methodology Self-Consistency"
      threshold: ">= 4/5"
      standard_reference: "this SKILL.md applied to its own production"
      scorer: external_sub_agent
      evidence_required: "Independence Check sub-agent confirms add-skill's own gates pass when applied to add-skill v0.7.0 SKILL.md"
related_skills:
  - relationship: depends_on
    skill: ../../references/standards/CRITICAL_THINKING_STANDARD.md
    notes: 13 principles cited across all 5 gates
  - relationship: depends_on
    skill: ../../references/standards/DECOMPOSITION_PROCEDURE.md
    notes: Gate 1 Primitive Discovery sub-step + tier composition review
  - relationship: depends_on
    skill: ../../references/standards/SPIRAL_TEMPLATES.md
    notes: Gate 4 verification rubric (ACCA + dimensions); VERIFICATION_REPORT.md template
  - relationship: depends_on
    skill: ../../references/standards/STANDARDS_RUBRIC.md
    notes: Gate 2 standards-phase classification
  - relationship: depends_on
    skill: ../../references/standards/REFERENTIAL_INTEGRITY_STANDARD.md
    notes: cross-skill relationship declaration (related_skills frontmatter block)
  - relationship: optional_input
    skill: ../../references/founder-facing-conventions.md
    notes: applies when Audience=founder-facing or both
---

# Add Skill

## Conclusion (Pyramid Principle — lead with the answer)

A five-gate methodology for authoring or upsurging a skill in this marketplace. Each gate cites specific principles from the five sulis standards under `plugins/sulis/references/standards/`. The output is a skill plus a `VERIFICATION_REPORT.md` on disk scored against the SPIRAL_TEMPLATES rubric — a single filesystem check (`test -f ... && grep "Verdict:.*PASS"`) determines whether the skill is shipped.

Skills are **deep + thorough, never fast**. The "fast pattern scan vs deep audit" framing is rejected. Every analysis / audit skill uses real tools (Semgrep, Gitleaks, Trivy, lizard, jscpd, hadolint, testssl.sh, curl) with Docker → native-binary → NOT_ASSESSED degradation. Skills that cannot meet this bar block at Gate 4.

The methodology applies in three modes:

1. **Greenfield** — authoring a wholly new skill
2. **Deepening (upsurge)** — extending an existing skill against the standards to reach the next depth threshold
3. **Standards-grounded re-author** — rewriting an existing pre-standards skill to cite the standards explicitly

If you have not read `references/methodology.md`, read it once. It explains why each gate exists and what failure mode it prevents. If you have not read the five standards, read `plugins/sulis/references/standards/README.md` for the adoption guide.

## The five gates

Each gate has explicit pass/fail criteria + an explicit standards citation. Do not skip gates. Do not move backwards from gate N to gate N-1 without a full re-author (this prevents the silent vocabulary drift documented in `references/kinds-and-tools-learnings.md`).

The output of running this skill is two artifacts:

1. The skill itself (`plugins/<plugin>/skills/<skill-name>/`)
2. A `VERIFICATION_REPORT.md` co-located with the skill (in the skill's root or under `iterations/{N}/`), documenting per-dimension scores per SPIRAL_TEMPLATES

### Gate 1 — Find (discovery + primitive discovery, deterministic-first)

**Standards:** Balanced Investigation (BI-01..04), Source Independence (SI-01..04), Confidence Calibration (CC), Primitive Grounding (PG-01..04), Decomposition Procedure (PD-01..06). See `plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md` §§1, 2, 4, 11 and `DECOMPOSITION_PROCEDURE.md`.

**Goal:** the author starts writing with full visibility into existing vocabulary, references, prior art, and collision risks — AND with an explicit primitive decomposition of the skill's scope.

#### Sub-step 1a: BRIEF_PACK (existing prior-art discovery)

Run the inventory script:

```bash
python3 plugins/sulis/skills/add-skill/scripts/inventory.py \
  --marketplace-root . \
  --target-plugin <plugin-name> \
  --target-skill <skill-name> \
  --proposed-description "<one-line trigger condition>" \
  --proposed-vocabulary "<comma-separated terms the skill will introduce>"
```

The script produces a structured BRIEF_PACK (Markdown to stdout) covering:

- Every existing skill name + description across the marketplace
- Every `references/*.md` file (so the author sees what knowledge already exists)
- Every existing "Gotchas" section in the target plugin's domain (prior art)
- Vocabulary collision check: does the proposed terminology overlap with existing skills?

Then **Claude interprets** the BRIEF_PACK per BI / SI / CC:

- **BI-01:** for every "is there a skill that does X?" search, also search "is there a reference doc that already covers X?"
- **SI-01:** when multiple existing skills cite the same reference doc, count as one source not many
- **CC:** the "no existing skill covers this" judgment carries an explicit confidence (VALIDATED if 5+ independent sources checked; SUPPORTED if 3-4; EMERGING if 2; UNVALIDATED if <2)

#### Sub-step 1b: Primitive Discovery (new in v0.7.0)

For analysis / audit / aggregator skills, decompose the skill's scope into primitives per PG-01..04 + PD-01..06.

1. **Declare the level of analysis (PG-03 / PD-04):** what decision will this skill inform? E.g., "what primitives should check-security cover?" (level: skill-scope) vs "which Semgrep rules to enable for SEC-03?" (level: rule-pack).
2. **Identify candidate primitives (PG-01):** irreducible units at that level. For check-* skills authored against codebase-assess, the 25-primitive catalogue is the starting candidate set; some primitives may need restructuring per the independence test.
3. **Apply the independence test (PG-02 / PD-03):** each candidate primitive must be independently changeable, validatable, falsifiable. If changing A requires changing B to preserve correctness, they are one primitive or share a hidden dependency.
4. **Apply termination condition (PG-04 / PD-04):** stop decomposing when further splitting wouldn't change the next action. Over-decomposition is as harmful as under-decomposition (AP-09).
5. **Type the inter-primitive dependencies (PD-05):** depends-on / enables / conflicts-with.
6. **Record provenance (PD-06):** extracted (from codebase patterns / existing standards) / inferred (from domain research) / user-stated.
7. **Verify scale constraints (PD-02):** fan-out ≤ 7 per node, depth ≤ 5.

For non-analysis skills (e.g., a pure-content authoring skill), the primitive discovery sub-step is skipped — record "N/A — non-analysis skill" in the VERIFICATION_REPORT.

**Pass criteria for Gate 1:**

- BRIEF_PACK produced and reviewed
- Collisions resolved or explicitly waived with reason
- "No existing skill covers this" carries an explicit CC verdict
- Primitive decomposition completed (or marked N/A); primitives pass PG-02 + PG-04; provenance recorded per primitive

### Gate 2 — Scope Lock (decide phase)

**Standards:** STANDARDS_RUBRIC phase classification; Outside-In Reasoning (OI-01..03); MECE-01..04. See `plugins/sulis/references/standards/STANDARDS_RUBRIC.md` and `CRITICAL_THINKING_STANDARD.md` §§5, 12.

**Goal:** the skill's scope, audience, standards-phase classification, trigger condition, primitive coverage, top-N gotchas, and verification tier are written down BEFORE drafting SKILL.md.

The author commits to:

- **Skill name** (kebab-case; verified non-colliding via Gate 1)
- **Plugin home** (which plugin will own it; create new plugin only if no existing one fits)
- **Audience** — `founder-facing` / `operator-facing` / `both`. Affects subsequent gates. Founder-facing skills MUST follow `plugins/sulis/references/founder-facing-conventions.md` (FE-06 application, no internal IDs in chrome, echo-before-act, prompt-before-destroy, etc.). `both` requires declaring a mode-selection strategy.
- **Category** — pick exactly one from:
  - Operator-facing: Library/API Reference, Product Verification, Data Fetching, Business Process, Code Scaffolding, Code Quality, Runbook
  - Founder-facing: Founder UX & Navigation, Concierge Translation, Founder Aggregator
- **Trigger condition** — the one-line `description:` field; a trigger, not a summary. Founder-facing uses ONLY user-facing vocabulary.
- **Standards-phase classification (new in v0.7.0)** — declare which sulis standards apply at which phase per STANDARDS_RUBRIC. Goes into SKILL.md frontmatter `standards:` block:
  - `input:` — typically REFERENTIAL_INTEGRITY_STANDARD for skills that name pre-existing cross-references
  - `processing:` — typically CRITICAL_THINKING_STANDARD for analytical skills; + DECOMPOSITION_PROCEDURE for skills with primitive-level decomposition
  - `output:` — typically CRITICAL_THINKING_STANDARD (secondary, for SCQA / Pyramid framing) for founder-mode output
- **Verification tier (new in v0.7.0)** — per SPIRAL_TEMPLATES tiering rules:
  - LIGHT — mechanical skills only; justification required
  - STANDARD (default) — most analysis / audit skills
  - HEAVY — methodology / authoring skills; founder-visible verdict skills; any skill where misleading the founder carries high trust cost
- **Tool stack (new in v0.7.0)** — audit-pattern skills must declare which real tools they invoke (Semgrep / Gitleaks / Trivy / lizard / jscpd / hadolint / testssl.sh / curl / coverage tools). Pure-regex skills (without tool integration) require explicit justification in VERIFICATION_REPORT — the depth bar applies; regex-only is the floor not the ceiling.
- **Top-N gotchas** (≤ 7 per PD-02 fan-out constraint) — each must have a concrete prior-failure source. If Audience is founder-facing or both, at least one addresses operator-vocab leakage and one addresses destructive-action confirmation.
- **Related skills** — declare per REFERENTIAL_INTEGRITY_STANDARD in SKILL.md frontmatter `related_skills:` block. Forward-only declarations using the four canonical types: depends_on / optional_input / related_to / supersedes.
- **Depth modes** if the skill needs them (Quick / Full / Audit) — declare the selection strategy (auto / user-explicit / context-derived). Note: "Quick" mode is rejected for audit-pattern skills — see Tool Stack lock above.

**Pass criteria for Gate 2:**

- All ten items written down in `VERIFICATION_REPORT.md`'s "Scope Lock" section
- No item is "TBD"; if something cannot be locked, return to Gate 1
- For founder-facing or both: founder-facing-conventions.md has been read
- Tool stack declared for audit-pattern skills (or explicit justification for regex-only)
- For analysis skills: standards-phase classification reflects primitive-discovery output from Gate 1

### Gate 3 — Generate (authoring, LLM-driven)

**Standards:** MECE (MECE-01..04), Pyramid Principle (PP-01..04), Decision Framing / SCQA (DF-01..04), No Hyperbole (NH-01..04). See `plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md` §§5, 6, 7, 10.

**Goal:** produce the skill files using the Gate 2 lock as the contract, structured per MECE + Pyramid + SCQA.

Files to produce:

```
plugins/<plugin>/skills/<skill-name>/
├── SKILL.md                  # use templates/SKILL.md.template as starter
├── references/               # optional but encouraged
│   └── <whatever>.md
├── scripts/                  # optional
└── templates/                # optional
```

The SKILL.md must:

- Have a `description:` frontmatter field matching the Gate 2 trigger condition verbatim
- Have `standards:`, `verification_spiral:`, `related_skills:` frontmatter blocks per Gate 2 lock
- Lead with a "## Conclusion" (or equivalent) section per Pyramid (PP-01..04) — conclusion first, supporting legs, details last. Burying the conclusion is a Gate 4 Structural Coherence failure.
- Have `## When to invoke` + `## When NOT to invoke` sections that pass the MECE check (mutually exclusive, collectively exhaustive)
- Include a `## Gotchas` section with the Gate 2 top-N (≤ 7 per PD-02) ordered by likelihood × impact
- Pass the linguistic audit (NH-02): no prohibited terms ("comprehensive", "robust", "powerful", "revolutionary", "disruptive", "game-changing", etc. — see CRITICAL_THINKING_STANDARD.md §6 for the full list)
- Include a `## Vocabulary` section if the skill introduces ≥ 2 domain terms
- Use progressive disclosure: point to `references/` for long-form rationale rather than inlining it
- Reference any wrapped standards via the canonical filenames in `plugins/sulis/references/standards/` rather than restating them

**Pass criteria for Gate 3:**

- All files exist and parse (SKILL.md frontmatter is valid YAML; `standards:` + `verification_spiral:` + `related_skills:` blocks present)
- The skill matches the Gate 2 lock (scope, category, trigger condition, standards-phase classification, verification tier, tool stack, gotchas, related skills)
- No reference file declared in SKILL.md is missing on disk (Codebase Referential Integrity precursor)
- Pyramid structure verified: SKILL.md's first heading or paragraph states the conclusion
- Linguistic audit passes: zero prohibited terms

### Gate 4 — Evaluate (verification spiral, scored under SPIRAL_TEMPLATES)

**Standards:** SPIRAL_TEMPLATES (tier templates + ACCA + Codebase Referential Integrity + Independence Check + VERIFICATION_REPORT.md template). See `plugins/sulis/references/standards/SPIRAL_TEMPLATES.md`.

**Goal:** prove the skill actually works before publishing it — by scoring it against the SPIRAL_TEMPLATES rubric for its declared tier and producing VERIFICATION_REPORT.md on disk.

#### The spiral run

Per SPIRAL_TEMPLATES tier defaults:

| Tier | Dimensions scored | Independence Check |
|------|-------------------|---------------------|
| LIGHT | ACCA only | No |
| STANDARD | ACCA + Evidence Grounding + Structural Coherence + Honest Uncertainty + Codebase Referential Integrity | No |
| HEAVY | STANDARD dimensions + Outcome-Specific Rigor + Independence Check | Yes (external sub-agent, fresh context) |

Each dimension gets a 1-5 score with threshold per SPIRAL_TEMPLATES; aggregate verdict = PASS only if all dimensions meet threshold.

**Outcome-Specific Rigor** for HEAVY-tier authoring skills = the three legacy perspectives folded into the dimension:

1. **Trigger accuracy.** Hand a fresh context the `description:` + skill name only. Ask: in what conversation contexts would this skill be invoked? Measure precision against intended trigger set. Threshold: ≥ 85%.
2. **Gotchas coverage.** Each gotcha must have a concrete prior-failure source (prior art / BRIEF_PACK / author experience). Speculation-sourced gotchas removed.
3. **Functional completeness.** Run the skill against 3-5 real scenarios. Each produces the promised output. ≥ 80% scenario success rate.

For full criteria see `references/completeness-perspectives.md` (preserved as the detail-page for these three dimensions).

#### Codebase Referential Integrity (highest-leverage dimension)

Every pre-existing technical entity the skill names must trace to the codebase with a verified file path:

- Tool wrappers (`plugins/sulis/_lib/tools/semgrep.py`, `plugins/sulis/_lib/tools/gitleaks.py`, etc.)
- Helper modules (`plugins/sulis/_lib/baseline.py`, etc.)
- Orchestrator entry-points (`plugins/sulis/skills/code-health/scripts/orchestrator.py`)
- Baseline + allowlist paths (`.checkup/{project}/baseline.json`, etc.)

Entities marked "NEW — to be created" are exempt but MUST be explicitly flagged. Unflagged new entities count as unverified pre-existing entities (= score reduction).

This is the dimension that catches the hallucination failure mode ("we use Semgrep" without actually wiring it).

#### Independence Check (HEAVY tier only)

Spawn an Agent with `subagent_type=Explore` (read-only) in fresh context. Inputs: the skill's artifact paths + applicable standards references. Explicit exclusion: NO access to the generating agent's reasoning. Task: score the skill against the declared dimensions using only the standards.

Independence dimension threshold: ≥ 3/5. If below, spiral BLOCKED even if self-scored dimensions pass.

#### Iteration termination

Per SPIRAL_TEMPLATES: max 3 iterations; terminate on sufficient (all thresholds met), max_iterations (capture irreducible blocker), or irreducible blocker declared up-front.

**Pass criteria for Gate 4:**

- VERIFICATION_REPORT.md exists at `plugins/<plugin>/skills/<skill>/VERIFICATION_REPORT.md` or `plugins/<plugin>/skills/<skill>/iterations/{N}/VERIFICATION_REPORT.md`
- File contains "Verdict: PASS"
- All scored dimensions meet threshold; for HEAVY tier, Independence Check ≥ 3
- Single filesystem check: `test -f ... && grep -q "Verdict:.*PASS" ...` returns 0

### Gate 5 — Adversarial Review (publish gate)

**Standards:** Adversarial Testing Posture (AT-01..03), Falsifiability Requirement (FR-01..04). See `plugins/sulis/references/standards/CRITICAL_THINKING_STANDARD.md` §§3, 13.

**Goal:** name the top ways the skill could mislead Claude or produce bad outcomes. For each, either prevent it in the skill or document it as an open risk with revisit-trigger.

AT-01 default posture: seek evidence the skill WILL fail before evidence it won't. AT-02 ordering: test riskiest assumptions first.

Misuse cases sometimes surface during Gate 4 functional-completeness scenarios. Maintain a running candidate list during Gate 4; finalise + categorise (PREVENTED / OPEN_RISK) at Gate 5.

#### Audience-agnostic categories

- Trigger-condition jargon leakage (Claude triggers it without context)
- Premature commitment to a reference version
- Unbounded gotchas section (grows past readable ≤ 7 per PD-02)
- Authorization leakage (skill requires a tool but doesn't declare it)
- Vocabulary collision with another skill
- Silent failure of progressive disclosure (declared reference missing — Codebase Referential Integrity = 0/5)
- Trigger condition matches too broadly
- Depth-mode selection ambiguity
- Tool degradation silently weakens to regex (audit-pattern; violates Tool Stack lock)

#### Audience-conditional categories (founder-facing or both)

- **MUC-F1:** Operator jargon leak in error string
- **MUC-F2:** Shortcut acts on stale state without echoing
- **MUC-F3:** Destructive action triggered by ambiguous founder phrasing
- **MUC-F4:** Number-of-items overwhelm (aggregator skills especially)
- **MUC-F5:** Source-of-truth false-positive (state not updated after out-of-band resolution)
- **MUC-F6:** Stubbed-vs-active rendering blur (wrapper skills with partial coverage)

Founder-facing or both skills MUST address at least 3 of MUC-F1..F6 in addition to the audience-agnostic categories.

For each top 3+ risk identified:

- **Name** the misuse case (use MUC-F numbering for the audience-conditional ones; free-form for others)
- **Describe** what Claude might do wrong (per FR-03 pre-mortem)
- **State** what the skill does to prevent it (PREVENTED with mechanism) or document it (OPEN_RISK with structured `revisit_by:` trigger — date / event / condition / never)

**Pass criteria for Gate 5:**

- ≥ 3 misuse cases named in VERIFICATION_REPORT.md's "Adversarial Review" section
- For founder-facing or both: at least 3 of those are MUC-F1..F6
- All marked as either PREVENTED (with mechanism) or OPEN_RISK (with documented impact + rationale + revisit-trigger)
- AT-03: any confirmation-seeking validation in Gate 4 documented as deliberate deviation

## Modes

### Greenfield mode (default)

All 5 gates from scratch. Use `templates/SKILL.md.template` as the starting shape.

### Deepening (upsurge) mode (new in v0.7.0)

When invoked on an existing skill (e.g., re-running add-skill on `check-security` to add SEC-01..06 coverage):

- **Gate 1** still runs — BRIEF_PACK + primitive discovery; existing skill counted as prior art; the question becomes "what primitives does this skill currently miss, and what does it now need?"
- **Gate 2** locks the deepening scope — what new primitives are in scope this iteration?
- **Gate 3** EXTENDS existing files (does not rewrite); preserves existing wiring (orchestrator entries, baseline format, allowlist semantics)
- **Gate 4** re-scores the full skill — not just the delta; produces VERIFICATION_REPORT.md at `iterations/{N}/VERIFICATION_REPORT.md` to preserve history
- **Gate 5** runs adversarial sweep on the new primitives + checks for regressions on existing ones
- Iteration termination: VERIFICATION_REPORT.md shows all dimensions ≥ threshold AND author marks "no productive lines of inquiry remain"

Documented as the **Deepening pattern** in `references/methodology.md`.

### Standards-grounded re-author mode (new in v0.7.0)

For pre-standards skills (authored before v0.7.0): one-time re-author against the standards. Same as Greenfield mode but with existing files as the starting Gate 3 output.

## Publishing

After all five gates pass:

1. Bump the owning plugin's version in `plugins/<plugin>/.claude-plugin/plugin.json`
2. Bump marketplace version in `.claude-plugin/marketplace.json`
3. Update the plugin's `CHANGELOG.md`
4. Commit + push following conventional-commits style

## Gotchas

- **Do not skip Gate 1 even if you "already know" the marketplace.** The vocabulary cascade in kinds-and-tools (turn 24) only worked because turn 23's grounding was actually done. Skipping Gate 1 because the skill feels obvious is exactly when collisions slip through.
- **The `description:` field is the highest-impact text in the whole skill.** Claude scans it to decide whether to trigger. Write it as a trigger condition ("Use when …"), not a summary. See `references/methodology.md`.
- **Codebase Referential Integrity catches hallucination.** A skill that says "uses Semgrep" without a wrapper at `plugins/sulis/_lib/tools/semgrep.py` scores 0/5 on this dimension and blocks at Gate 4. Flag NEW entities explicitly — unflagged new entities count as hallucinations.
- **Gotchas without a concrete prior-failure source are speculation.** Gate 4 Gotchas-Coverage will remove them; do not add them in Gate 3 to look thorough.
- **If Gate 2 cannot be locked, the problem is in Gate 1.** Do not draft SKILL.md with unresolved scope; the drafting process will commit you to choices you haven't actually made.
- **VERIFICATION_REPORT.md is part of the skill, not metadata.** Commit it alongside SKILL.md. The single filesystem check (`test -f ... && grep "Verdict:.*PASS"`) determines whether the skill is shipped.
- **Re-running Gate 1 on every authoring session is cheap.** The marketplace changes; cached BRIEF_PACKs go stale within weeks. Don't reuse a BRIEF_PACK from an old authoring session.
- **Depth bar applies to audit-pattern skills.** "Quick" mode is rejected. Pure-regex skills without tool integration need explicit justification — regex is the floor, not the ceiling.

## Vocabulary

- **Gate** — a methodology checkpoint with explicit pass/fail criteria. The five gates are sequential.
- **BRIEF_PACK** — the structured output of `inventory.py`; Gate 1's deliverable.
- **Scope Lock** — the Gate 2 commitment that prevents scope creep during drafting.
- **Primitive Discovery** — Gate 1 sub-step applying PG + PD to decompose skill scope into irreducible primitives.
- **Dimension** — one of the scored axes in a SPIRAL_TEMPLATES tier (ACCA / Evidence Grounding / Structural Coherence / Honest Uncertainty / Codebase Referential Integrity / Outcome-Specific Rigor / Independence Check).
- **Outcome-Specific Rigor** — the HEAVY-tier dimension that absorbs the three legacy completeness perspectives (Trigger accuracy / Gotchas coverage / Functional completeness).
- **Adversarial sweep** — the Gate 5 process of naming misuse cases under AT-01..03.
- **MUC-F1..F6** — sulis-local audience-conditional misuse cases for founder-facing skills.
- **VERIFICATION_REPORT.md** — the per-skill audit artifact required on disk by SPIRAL_TEMPLATES. Single filesystem check determines compliance. Formerly named COMPLETENESS_REPORT.md (renamed in v0.7.0 to align with SPIRAL_TEMPLATES).
- **Deepening (upsurge) mode** — running add-skill on an existing skill to extend coverage, preserving existing wiring.

## When to invoke this skill

- Author has identified a repeatable workflow and wants to publish it as a skill
- An existing skill needs upsurging — extending coverage against the standards (deepening mode)
- A pre-standards skill needs re-authoring against the v0.7.0 standards
- Multiple skills are being authored or upsurged in batch

## When NOT to invoke this skill

- The work is a one-off (write it inline; don't make every workflow a skill)
- The author wants a single-gotcha edit on an existing skill (Edit the SKILL.md directly; full five-gate is overkill)
- The proposed skill is actually a slash command, an agent, or a plugin (those have different shapes)
