# Decomposition Procedure Standard

> **Adapted from platform v1.0.0 (2026-03-18). Sulis-local v1.0.0 (2026-05-24).**
> Only "Applicability" and "Relationship to Other Standards" sections diverge from the platform original.
> Vocabulary: "outcome" → "skill"; OFM-specific references dropped.

> **Version:** 1.0.0
> **Type:** Cross-cutting standard
> **Status:** Active

---

## Purpose

This standard governs the operational procedure for decomposing any domain into primitives. It applies to all sulis activities that perform primitive decomposition, extraction, or identification — most notably `add-skill` Gate 1 (Primitive Discovery), per-skill upsurge loops, and tier composition review.

Three related concerns are governed by separate standards:

- **PG-01 to PG-04** (CRITICAL_THINKING_STANDARD.md §11) govern analytical grounding — ensuring primitives are real and irreducible
- **PD-01 to PD-06** (this standard) govern the operational procedure — the structural rules for HOW decomposition is performed
- **SPIRAL_TEMPLATES.md** governs the verification rubric — how the decomposition result is scored (ACCA, Evidence Grounding, Structural Coherence, etc.)

---

## Requirements

### PD-01: Directed Graph with Acyclic Disclosure Ordering

Decomposition produces a directed graph. Dependency edges define recommended examination order and MUST be acyclic for initial disclosure — at least one root node with no incoming dependency edges MUST exist.

Agent traversal is unconstrained. OODA spiral facilitation permits revisiting any primitive when uncertainty reduction demands it. The dependency edges mean "should be examined before, initially" — not "must be complete before this can ever be touched."

**Rationale:** Disclosure ordering needs roots (you must show something first). Agent facilitation needs cycles (the "loop" in OODA is literal — downstream work may reveal that earlier primitives need re-evaluation).

### PD-02: Scale Constraints

Fan-out MUST NOT exceed 7 per node. Depth MUST NOT exceed 5 levels.

These are cognitive load constraints (Miller, 1956). They apply to the graph as authored, not to runtime traversal.

Bounded context partitioning is RECOMMENDED when leaf count exceeds 40.

### PD-03: Independence Gate

Each candidate primitive MUST pass the PG-02 independence test:

- Independently changeable
- Independently validatable
- Independently falsifiable

If changing primitive A requires changing primitive B to preserve correctness, they are one primitive or share a hidden dependency that MUST be made explicit as a typed edge (PD-05).

### PD-04: Termination Condition

Decomposition MUST stop when further splitting would not change the next action at the stated level of analysis (PG-04).

The level of analysis MUST be declared before decomposition begins. Primitives are relative to the decision context, not absolute.

Over-decomposition is as harmful as under-decomposition (AP-09).

### PD-05: Dependency Typing

Dependencies between primitives MUST be typed using one of three relationships:

| Type | Semantics | Example |
|------|-----------|---------|
| `depends-on` | Prerequisite — B cannot meaningfully start until A is satisfied | "SEC-07 git-history scan" depends-on "Gitleaks tool wrapper available" |
| `enables` | Unlocks downstream — completing A makes B possible but not required | "check-security HEAVY verification" enables "code-health green verdict" |
| `conflicts-with` | Mutual exclusion — A and B cannot both be active simultaneously | Rare; used for alternative approaches |

Untyped dependencies are not permitted.

### PD-06: Provenance and Phase

Each primitive MUST carry:

**Provenance** — how it was identified:

| Value | Meaning |
|-------|---------|
| `extracted` | Derived from existing practice, codebase patterns, or documented standards (e.g., a codebase-assess primitive ported into a sulis skill scope) |
| `inferred` | Derived from domain research or analytical decomposition |
| `user-stated` | Explicitly stated by a user |

**Phase** — the lifecycle phase where the primitive first becomes relevant. Phase assignment indicates earliest relevance, not exclusive applicability. A "Safe" tier primitive may remain relevant through "Polished."

---

## Applicability

This standard applies to any sulis activity that produces primitives, including but not limited to:

| Activity | Primary Step | Level of Analysis |
|---------|-------------|-------------------|
| `add-skill` Primitive Discovery (Gate 1 extension) | Gate 1 sub-step after BRIEF_PACK interpretation | Skill scope primitives |
| Per-skill upsurge loop (`check-*`) | Gate 1 re-run for an existing skill in deepening mode | Per-skill primitive coverage |
| Tier composition review | Cross-skill primitive review after Phase 2 upsurge complete | Tier-level primitive allocation (MECE across tiers) |
| `code-health` tier registry | One-time + version bumps | Tier identity + founder-question wording |
| `inbox` source enumeration | One-time + when new sources added | Aggregator source primitives |

**Wiring:** `add-skill` invokes this standard at Gate 1 (Primitive Discovery sub-step). Other sulis activities adopt PD on their own timelines as add-skill's deepening pattern propagates outward.

---

## Relationship to Other Standards

| Standard | Relationship |
|----------|-------------|
| CRITICAL_THINKING_STANDARD.md §11 (PG-01..04) | PD references PG-02 (independence) and PG-04 (termination) directly. PG governs thinking; PD governs doing. |
| CRITICAL_THINKING_STANDARD.md AP-09 | PD-04 references AP-09 as the anti-pattern for violating termination. |
| SPIRAL_TEMPLATES.md | PD output is scored under Structural Coherence dimension (MECE-aligned graph). VERIFICATION_REPORT.md cites PD compliance when the artifact under review is a decomposition. |
| STANDARDS_RUBRIC.md | PD is a `processing` phase standard. |
| REFERENTIAL_INTEGRITY_STANDARD.md | PD-05 typed dependencies map to the four canonical relationship types (depends-on / enables / conflicts-with → depends_on / enables / conflicts_with — naming aligned at the canonical-vocabulary level). |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-05-24 | Initial sulis-local port. Adapted from platform v1.0.0 (2026-03-18). Applicability table rewritten for sulis activities (add-skill primitive discovery, per-skill upsurge, tier composition review, code-health tier registry, inbox source enumeration). Relationship-to-other-standards section rewritten to reference sulis-local companions. |
