# Spiral Templates

> **Adapted from platform v2.1.0 (2026-05-05). Sulis-local v1.0.0 (2026-05-24).**
> Significant trim: Wired Outcomes Registry, STRICT MODE Sub-Agent Dispatches, and platform-specific
> Domain-Specific Spirals listings removed. ACCA inlined from platform EXECUTION_STANDARD §1
> so this document is self-contained. Vocabulary: "outcome" → "skill"; OUTCOME.md → SKILL.md;
> GRAPH.yaml → SKILL.md frontmatter.

> **Purpose:** Default verification spiral templates per tier. Every sulis skill declares a
> verification spiral. Most skills cite a default template; skills with specific rigor demands
> declare custom dimensions.

---

## How to Use This Document

Skill authors:

1. Determine your skill tier per the tiering rules below:
   - Methodology / authoring skills (e.g., `add-skill`) → MUST be HEAVY
   - Skills feeding founder-visible verdicts (e.g., `check-security`, `code-health`) → MUST be HEAVY
   - Most analysis / audit skills (other `check-*` skills) → STANDARD (default)
   - Mechanical skills with no analytical content (e.g., a pure file-mover) → LIGHT (with justification)

2. Cite the default template in your SKILL.md frontmatter:

```yaml
---
name: check-security
description: Use when ...
verification_spiral:
  tier: heavy
  template_base: HEAVY_TIER_DEFAULT
  custom_dimensions: []  # or list additions
---
```

3. Or declare custom dimensions (required for HEAVY tier skills that add domain-specific checks — see "Declaring a Custom Spiral" below).

---

## Universal Dimension: ACCA

Every tier includes ACCA. Scored 1-5 with threshold >= 4.

(Inlined from platform EXECUTION_STANDARD §1 — sulis does not port the full constitutional execution standard; the ACCA definition is the only sub-section needed.)

| Sub-dimension | Threshold | Evidence Required |
|---------------|-----------|-------------------|
| **Accurate** | >= 4 | Every claim cites specific evidence (file:line, quoted text, measured metric) |
| **Clear** | >= 4 | Unambiguous language, explicit cause-effect, no hyperbole (see CRITICAL_THINKING_STANDARD §6 NH) |
| **Complete** | >= 4 | All required sections present, no TODOs, no "see elsewhere" |
| **Actionable** | >= 4 | Concrete next steps, success/failure criteria, copy-paste ready commands where applicable |

**Scoring rule:** All four sub-dimensions must meet threshold. Overall ACCA score is the minimum of the four.

---

## LIGHT_TIER_DEFAULT

**Passes:** 1
**Dimensions:** ACCA only
**Max iterations:** 1
**Independence check:** No

**Use when:** Skill produces mechanical outputs without analytical content (e.g., a file-mover; a pure-renderer that converts a JSON envelope to markdown).

**Downgrade justification required:** Skill author declares in SKILL.md why the skill does not require analytical verification. Justification reviewed during skill authoring (add-skill Gate 4).

**Spiral process:**

1. Score ACCA sub-dimensions against artifact
2. If all thresholds met → PASS
3. If any threshold missed → apply fixes (typos, missing sections, vague language)
4. If fixes applied → re-score
5. If thresholds still missed → irreducible-blocker with explicit justification

---

## STANDARD_TIER_DEFAULT

**Passes:** 3 (max)
**Dimensions:** ACCA + Critical Thinking Principles (core subset) + Codebase Referential Integrity
**Max iterations:** 3
**Independence check:** No

**Use when:** Default for most sulis analysis / audit skills.

**Dimensions:**

| Dimension | Threshold | Standard Reference |
|-----------|-----------|-------------------|
| ACCA | >= 4/5 (min of sub-dimensions) | This document §"Universal Dimension: ACCA" |
| Evidence Grounding | >= 4/5 | CRITICAL_THINKING_STANDARD.md (BI, SI, AT-01) — claims backed by specific evidence, sources independent, adversarial counter-searches performed |
| Structural Coherence | >= 4/5 | CRITICAL_THINKING_STANDARD.md (MECE, PP, DF) — categories MECE, conclusion-first, situation→complication→question→answer |
| Honest Uncertainty | >= 3/5 | CRITICAL_THINKING_STANDARD.md (HU, CC) — gaps flagged as findings not hidden, confidence calibrated |
| Codebase Referential Integrity | >= 4/5 | (Sulis-local, derived from platform ADR-164) — every pre-existing technical entity named in the skill's artifacts must trace to the codebase with a verified file path; NEW entities exempt only if explicitly flagged. Scoring rubric below. |

**Codebase Referential Integrity scoring rubric:**

- **5/5** — All pre-existing technical entities named in the skill's artifacts (tool wrappers, helper modules, orchestrator entry-points, baseline file paths, allowlist file paths) appear in the codebase with verified file paths.
- **4/5** — All pre-existing entities verified; minor gaps in detail (e.g. missing line-number for one or two entries, but each entity itself is present and the file path resolves).
- **3/5** — Most entities verified; 1–2 unverified but plausible (named but not located in the codebase, with no evidence of absence).
- **2/5** — Several entities unverified, OR the skill references a subsystem (e.g. `_lib/tools/`) that is materially incomplete.
- **1/5** — Skill references entities not found in the codebase when checked.
- **0/5** — Skill references entities that are demonstrably absent from the codebase (entries hallucinated from training-data priors or analogical reasoning).

Entities marked "NEW — to be created" are exempt from verification but MUST be explicitly flagged as new in both the SKILL.md and any references / scripts. Unflagged new entities count as unverified pre-existing entities.

**Applicability:** This dimension applies whenever the SKILL.md or its references name pre-existing technical entities from the sulis codebase (tool wrappers, helper modules, orchestrators, paths). For skills that name no such entities (e.g. pure-content skills), the dimension scores 5/5 by inapplicability and the scorer records "N/A — no pre-existing technical entities named."

**Spiral process:**

1. **Observe:** Read artifact (SKILL.md + references + scripts) in full
2. **Orient:** Reference applicable standards (ACCA, critical thinking principles, codebase paths when relevant)
3. **Decide:** Score each dimension with evidence citation
4. **Act:** Fix what can be fixed autonomously (ACCA violations, missing citations, unclear language, MECE gaps; for Codebase Referential Integrity, return to the codebase-enumeration step or mark hallucinated entries as NEW where applicable)
5. Re-score after fix
6. Terminate on: sufficient (all thresholds met), max iterations (3), or irreducible (explicit blocker)

---

## HEAVY_TIER_DEFAULT

**Passes:** 3 (max)
**Dimensions:** ACCA + Critical Thinking Principles + Outcome-Specific Rigor + Codebase Referential Integrity + Independence Check
**Max iterations:** 3
**Independence check:** YES (mandatory)

**Use when:** MANDATORY for methodology / authoring skills (`add-skill`), founder-visible verdict skills (`check-security`, `code-health`), and any skill where misleading the founder carries high trust cost.

**Dimensions:**

| Dimension | Threshold | Standard Reference | Scorer |
|-----------|-----------|-------------------|--------|
| ACCA | >= 4/5 | This document §"Universal Dimension: ACCA" | Generating agent |
| Evidence Grounding | >= 4/5 | CRITICAL_THINKING_STANDARD.md (BI, SI, AT-01) | Generating agent |
| Structural Coherence | >= 4/5 | CRITICAL_THINKING_STANDARD.md (MECE, PP, DF) | Generating agent |
| Outcome-Specific Rigor | >= 4/5 | Skill author declares (e.g., for `add-skill`: gotchas-coverage + trigger-accuracy + functional-completeness) | Generating agent |
| Codebase Referential Integrity | >= 4/5 | See STANDARD_TIER_DEFAULT for full rubric. Same rule applies in HEAVY tier: every pre-existing technical entity in the artifact must trace to the codebase with a verified file path; NEW entities exempt only if explicitly flagged. | Generating agent |
| **Independence Check** | **>= 3/5** | **(Sulis-local, derived from platform C-07-E — defends against rubber-stamping)** | **External sub-agent (fresh context)** |

**Independence check mechanics:**

1. Spawn a sub-agent via the Agent tool with:
   - **Inputs:** Artifact path(s) (SKILL.md + references + scripts), applicable standards references, skill-declared dimensions
   - **Explicit exclusion:** NO access to the generating agent's reasoning, notes, or chain-of-thought
   - **Task:** Score the specified dimension(s) against the artifact using only the provided standards
2. Sub-agent returns: score per dimension + evidence citations
3. If independence-check score falls below threshold → spiral BLOCKED even if self-scored dimensions pass

**Recommended Agent type for sulis Independence Check:** `Explore` (read-only access; no risk of accidental edits).

**Spiral process:**

1. Generating agent scores internal dimensions (ACCA, evidence grounding, structural coherence, outcome-specific, codebase referential integrity)
2. External sub-agent scores independence dimension
3. Aggregate: PASS only if all dimensions meet threshold
4. If BLOCKED and fix possible: apply fix, re-score affected dimensions
5. Terminate on: sufficient (all thresholds met), max iterations (3), or irreducible (explicit blocker with justification)

---

## Declaring a Custom Spiral

When skill rigor demands dimensions beyond the defaults, declare a custom spiral in SKILL.md frontmatter:

```yaml
---
name: check-security
description: Use when ...
verification_spiral:
  tier: heavy
  template_base: HEAVY_TIER_DEFAULT
  custom_dimensions:
    - name: "Attack Chain Coverage"
      threshold: ">= 4/5"
      standard_reference: "sulis-local primitive catalogue §SEC chain patterns"
      scorer: generating_agent
      evidence_required: "Every {secret + endpoint}, {debug-mode + PII-in-logs}, {outdated-dep + reachable-code} chain pattern produces a finding when both sub-conditions present"
    - name: "Tool Degradation Verified"
      threshold: ">= 4/5"
      standard_reference: "plugins/sulis/_lib/tools/REFERENCE.md degradation policy"
      scorer: generating_agent
      evidence_required: "With Docker stopped AND native binary absent, each tool reports NOT_ASSESSED (never silent regex fallback)"
  irreducible_blocker_triggers:
    - "Required external credentials unavailable in current environment"
    - "Tool wrapper for declared dependency not yet authored"
---
```

---

## VERIFICATION_REPORT.md Template

**Every spiral execution MUST produce this file on disk in the skill's verification workspace.** The file's absence from disk is mechanical evidence of non-compliance. The file MUST follow this structure:

```markdown
# VERIFICATION_REPORT.md — {skill-name}

**Skill:** {plugin}/{skill-name}
**Iteration:** {N}
**Produced:** {ISO-8601 timestamp}

---

## Spiral Summary

**Tier:** {light | standard | heavy}
**Template base:** {LIGHT_TIER_DEFAULT | STANDARD_TIER_DEFAULT | HEAVY_TIER_DEFAULT}
**Iterations used:** {1-3}
**Termination reason:** {sufficient | max_iterations | irreducible_blocker}
**Verdict:** {PASS | BLOCKED}

---

## Per-Dimension Scores

### ACCA (required all tiers)

| Sub-dimension | Threshold | Score | Evidence |
|---------------|-----------|-------|----------|
| Accurate | >= 4 | {1-5} | {specific citations — file:line references, quoted text, measured metrics} |
| Clear | >= 4 | {1-5} | {evidence} |
| Complete | >= 4 | {1-5} | {evidence} |
| Actionable | >= 4 | {1-5} | {evidence} |

**ACCA minimum: {min(sub-scores)}/5 — {PASS | BLOCKED}**

### {Additional dimensions per template and custom declarations}

For each dimension in the skill's declared spiral:

**Dimension:** {name}
**Threshold:** {>= N/5}
**Score:** {1-5}
**Scorer:** {generating_agent | external_sub_agent}
**Evidence:** {citations}

### Independence Check (HEAVY tier only)

For HEAVY-tier skills, a dedicated section showing the external sub-agent's score and its produced artifact (e.g., INDEPENDENCE_CHECK.md sibling file with the sub-agent's full reasoning).

---

## Fixes Applied During Spiral

{List of autonomous fixes made during the spiral, or "None" if no fixes needed}

---

## Irreducible Blockers

{If BLOCKED: list of blocker declarations with:}
- **Dimension failed:** {name}
- **Why unfixable by current agent/tools:** {specific reason}
- **External action required to resolve:** {concrete next step}
- **Scope of blocking issue:** {bounded estimate}

{Or "None" if PASS}

---

## Meta-Notes

{Optional: any observations about the spiral execution itself, limitations encountered, or special considerations worth recording for future audits}
```

### File Location

VERIFICATION_REPORT.md MUST be written to the skill's verification workspace at one of:

- `plugins/{plugin}/skills/{skill}/VERIFICATION_REPORT.md` (for skills producing the file once)
- `plugins/{plugin}/skills/{skill}/iterations/{N}/VERIFICATION_REPORT.md` (for skills tracking iteration history; recommended for skills that upsurge over time)

### Verification

**A single filesystem check** determines compliance:

```bash
test -f "plugins/{plugin}/skills/{skill}/VERIFICATION_REPORT.md" && \
  grep -q "Verdict:.*PASS" "plugins/{plugin}/skills/{skill}/VERIFICATION_REPORT.md"
```

If this check fails, the skill is definitionally incomplete regardless of other artifacts or agent assertions.

### Sub-Agent Dispatches (STRICT MODE pattern, deferred)

Platform v1.3.0 adds a Sub-Agent Dispatches section to VERIFICATION_REPORT.md to record per-dispatch echo-back verification and TASKS.yaml coverage. Sulis does not currently use TASKS.yaml or echo-back templates; this pattern can be adopted later if sulis grows STRICT MODE orchestration needs.

---

## Domain-Specific Spiral Implementations

> **Skills MAY have specialised verification-spiral implementations** that inherit
> the universal OODA + fix-as-you-go + independence-check + VERIFICATION_REPORT.md
> structure from this document, while specialising the dimensions for their domain.

### Pattern

A domain-specific verification-spiral implementation MUST:

1. **Inherit universal structure:** Its behaviour is OODA (Observe, Orient, Decide, Act) with fix-as-you-go between iterations, max iterations per tier, termination conditions (sufficient / max iterations / irreducible blocker)
2. **Produce VERIFICATION_REPORT.md on disk** — same template as the universal verification-spiral, with domain-specific dimensions filled in
3. **Include external sub-agent independence check** when serving a HEAVY-tier skill
4. **Declare its dimensions** in either the implementation itself or the skill's verification_spiral frontmatter block (both must align)

A domain-specific spiral MAY:

- Retain pre-existing orchestration structure (e.g., parallel sub-validator execution) inside an OODA pass
- Add domain-specific fix-as-you-go capabilities (e.g., auto-correcting specific artifact patterns)
- Produce additional domain-specific output artifacts alongside the mandatory VERIFICATION_REPORT.md

### Registered Domain-Specific Spirals

| Skill | Tier | Notes |
|-------|------|-------|
| _(none yet — sulis-local domain-specific spirals will be registered here as they are authored)_ | | |

### Skill Binding

A skill that uses a domain-specific spiral declares this in its frontmatter:

```yaml
---
name: code-health
verification_spiral:
  tier: heavy
  template_base: HEAVY_TIER_DEFAULT
  implementation: plugins/sulis/skills/code-health/spiral/code-health-spiral.md
  external_sub_agent_dimension: cross-tier-chain-coverage
---
```

The verification workflow reads `implementation:` and invokes that skill (instead of the generic spiral) to execute. The output is still VERIFICATION_REPORT.md on disk.

### Relationship to Generic Spiral

The generic spiral (this document's defaults) remains the **default** for skills without a domain-specific implementation. Any skill can opt in to a domain-specific spiral by declaring `implementation:` in its verification_spiral block.

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-24 | Initial sulis-local port. Adapted from platform v2.1.0 (2026-05-05). Wired Outcomes Registry (50 platform outcomes) dropped. Sub-Agent Dispatches sub-section reduced to a deferred-pattern note. Registered Domain-Specific Spirals listing reset to empty. ACCA inlined from platform EXECUTION_STANDARD §1 (sulis does not port the full execution standard). Outcome Binding YAML example replaced with SKILL.md frontmatter example. Vocabulary aligned: outcome → skill; OUTCOME.md → SKILL.md; GRAPH.yaml → SKILL.md frontmatter. File location guidance adapted to sulis layout. |
