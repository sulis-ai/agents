# Referential Integrity Standard

> **Adapted from platform v1.0.1 (2026-02-26). Sulis-local v1.0.0 (2026-05-24).**
> Meaningful trim: Migration from Previous Vocabulary + Migration Phases removed (sulis adopts
> all-at-once). Vocabulary: "outcome" → "skill"; OUTCOME.md `## Related Outcomes` section →
> SKILL.md frontmatter `related_skills:` block (or `## Related Skills` markdown form).

<!-- summary -->
This standard ensures cross-skill dependency declarations remain consistent, complete, and mechanically verifiable. Four canonical relationship types — `depends_on`, `optional_input`, `related_to`, and `supersedes` — govern the inter-skill vocabulary. Declarations are forward-only: each skill declares what it depends on, and inverse relationships are derived computationally. Federated ownership means each SKILL.md is authoritative for its own relationships. Five validation rules (RI-01 through RI-05) cover dangling references, circular dependencies, non-standard vocabulary, missing sections, and registry drift.

**Read next:** add-skill Gate 1 (Find) explains how to declare relationships when authoring a skill.
<!-- detail -->

**Version:** 1.0.0
**Status:** Active
**Purpose:** Ensure cross-skill dependency declarations are consistent, complete, and mechanically verifiable.

---

## Why This Matters

Sulis skills do not exist in isolation. They depend on `_lib/` helpers, compose with `code-health` as wired tiers, share tool wrappers, and relate to other skills via cross-skill self-tests. When skills are added, removed, or modified, these relationships must remain accurate. Without enforcement, cross-skill references drift — creating broken links, missing dependencies, and inconsistent documentation.

This standard defines:

1. A **relationship taxonomy** for skill-to-skill declarations
2. **Declaration rules** (forward-only, federated ownership)
3. **Validation rules** (RI-01..05) — enforcement currently manual; sulis-local validator script deferred
4. **Two declaration forms** (frontmatter or markdown — author preference)

---

## Relationship Taxonomy

### Four Canonical Types

| Type | Meaning | Ordering Constraint | Validation |
|------|---------|---------------------|------------|
| `depends_on` | Hard prerequisite — must complete before this skill starts (or be present for this skill to function) | Yes (strict ordering) | ERROR if target missing; ERROR if cycle detected |
| `optional_input` | Soft prerequisite — will use outputs if available, but not required | No (enhances, not blocks) | ERROR if target missing |
| `related_to` | Conceptual association — no ordering constraint | No | WARN if target missing |
| `supersedes` | Replacement relationship — this skill replaces the target | No | ERROR if target missing |

### Declaration Format — Frontmatter Form (recommended)

In SKILL.md frontmatter:

```yaml
---
name: check-security
description: Use when ...
related_skills:
  - relationship: depends_on
    skill: code-health
    notes: invoked as wired tier 2 in code-health orchestrator
  - relationship: depends_on
    skill: _lib/tools/semgrep
    notes: tool wrapper for SEC-03 / SEC-04 / SEC-05 / SEC-06 / DAT-03 / INF-04
  - relationship: depends_on
    skill: _lib/tools/gitleaks
    notes: tool wrapper for SEC-07 / DAT-04 / INF-02
  - relationship: optional_input
    skill: _lib/tools/testssl
    notes: invoked only when --url provided (DAT-02)
  - relationship: related_to
    skill: check-readability
    notes: cross-skill self-test target
---
```

### Declaration Format — Markdown Form

In SKILL.md body, under a `## Related Skills` section:

```markdown
## Related Skills

| Relationship | Skill | Notes |
|--------------|-------|-------|
| depends_on | [code-health](../code-health/SKILL.md) | invoked as wired tier 2 |
| depends_on | [_lib/tools/semgrep](../../_lib/tools/semgrep.py) | tool wrapper |
| optional_input | [_lib/tools/testssl](../../_lib/tools/testssl.py) | invoked only when --url provided |
| related_to | [check-readability](../check-readability/SKILL.md) | cross-skill self-test target |
```

Both forms are valid. Frontmatter form is preferred when the SKILL.md author wants mechanical extractability; markdown form is preferred when relationships need extended notes.

### Column / Field Definitions

- **relationship / Relationship**: One of the four canonical types (case-sensitive, lowercase with underscore)
- **skill / Skill**: Identifier (frontmatter form) or markdown link with relative path (markdown form). Identifier convention: `{skill-name}` for sibling skills; `{plugin}:{skill-name}` for cross-plugin; `_lib/{module}` for shared helpers
- **notes / Notes**: Why this relationship exists (semantic context)

---

## Declaration Rules

### Rule 1: Forward-Only Declarations

Each skill declares only what it depends on or relates to. Inverse relationships ("who depends on me") are **derived computationally**, never stored.

| Stored | Derived |
|--------|---------|
| "A `depends_on` B" | "B is depended on by A" |
| "A `optional_input` B" | "B is optional input to A" |

**Rationale:** Forward-only declarations eliminate the bidirectional update problem. When B is created, only B's SKILL.md is modified. A's SKILL.md does not need to be updated because A's declaration already captures the relationship from A's perspective.

### Rule 2: Federated Ownership

Each skill owns its own dependency declarations. No external document is the authoritative source for individual relationships.

- **SKILL.md `related_skills:` frontmatter / `## Related Skills` section** — Authoritative for that skill's declarations
- **`code-health` tier-registry.md** — Authored for human readability; validated against declarations
- **`add-skill` BRIEF_PACK** — Reads declarations at Gate 1 to surface prior art

### Rule 3: Complete Vocabulary

All relationship declarations must use one of the four canonical types. Non-standard terms are flagged by RI-03.

---

## Validation Rules

(Enforcement currently manual via grep + author judgment. Sulis-local validator script — `plugins/sulis/_lib/standards/integrity_validator.py` — is deferred to a follow-up commit per the Phase 0 plan.)

| Rule ID | Check | Severity | Description |
|---------|-------|----------|-------------|
| **RI-01** | Dangling reference | ERROR | Referenced skill identifier does not exist in any `plugins/{plugin}/skills/` directory (or `_lib/` for shared helpers) |
| **RI-02** | Circular dependency | ERROR | Cycle detected in `depends_on` relationships (A depends_on B, B depends_on A) |
| **RI-03** | Non-standard vocabulary | ERROR | Relationship uses a term not in the four canonical types |
| **RI-04** | Missing section | WARN | Skill has no `related_skills:` frontmatter block AND no `## Related Skills` section |
| **RI-05** | Tier-registry drift | WARN | Skill referenced in `code-health/references/tier-registry.md` not found in its declared plugin, or relationship contradicts the skill's own declarations |

### Validation Scope

Manual check scans:

- `plugins/*/skills/*/SKILL.md` — every skill's frontmatter + markdown
- `plugins/sulis/skills/code-health/references/tier-registry.md` — for RI-05 cross-reference

Suggested grep for RI-01 spot-check during add-skill Gate 4:

```bash
# Extract every depends_on / optional_input / related_to / supersedes target from the skill,
# then verify each target file exists
grep -E '^\s+skill: ' plugins/{plugin}/skills/{skill}/SKILL.md
```

---

## Integration with Other Standards

| Standard | Relationship |
|----------|-------------|
| CRITICAL_THINKING_STANDARD.md | Critical Thinking's MECE requirement on skill scope is checked separately from RI; RI checks reference integrity, not scope hygiene. |
| DECOMPOSITION_PROCEDURE.md | PD-05 typed dependencies (depends-on / enables / conflicts-with) parallel RI's relationship types at the primitive level. RI applies between skills; PD applies between primitives within a decomposition. |
| SPIRAL_TEMPLATES.md | The Codebase Referential Integrity dimension (ADR-164) covers entity references within a skill (file paths, tool wrappers); RI covers skill-to-skill relationships. Both are about reference integrity at different scopes. |
| STANDARDS_RUBRIC.md | RI is an `input` phase standard. |

---

## References

| Document | Purpose |
|----------|---------|
| `plugins/sulis/skills/add-skill/SKILL.md` (Gate 1 + cross-cutting section) | How to declare relationships when authoring a skill |
| `plugins/sulis/skills/code-health/references/tier-registry.md` | Tier-level skill registry; validated against per-skill declarations via RI-05 |
| `plugins/sulis/_lib/standards/integrity_validator.py` | Sulis-local mechanical validator — DEFERRED to a follow-up commit; manual grep + author judgment in the meantime |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-24 | Initial sulis-local port. Adapted from platform v1.0.1 (2026-02-26). Migration from Previous Vocabulary + Migration Phases removed (sulis adopts all-at-once). Declaration format adapted: two forms documented (frontmatter recommended; markdown supported). Validation scope adapted to plugins/sulis/. RI-03 ships at ERROR severity from v1.0.0 (no migration WARN period needed). Mechanical validator script deferred to follow-up commit. |
