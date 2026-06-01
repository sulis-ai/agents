---
id: ADR-004
title: Canonical question set lives at `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`
status: accepted
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
date: 2026-06-01
resolves: SRD Open Question 4
---

# ADR-004 — Canonical question set lives at `references/standards/VERIFICATION_QUESTIONS.md`

## Decision

The 20-question canonical set, the kind→adapter mapping table, and the
version field live in a **new standalone reference standard** at:

```
plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md
```

This file is the **single source of truth** (per NFR-004). Every
consuming skill prose and agent prompt cites the file by relative path
and must not inline-duplicate the question text or the adapter table.

## Context

SRD Open Question 4 surfaced two main locations:

- (a) A standalone standard at `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`
- (b) Embedded inside the existing `plugins/sulis/references/decompose-validation-rubric.md`

The choice is consequential. The canonical set is read by **three
agents** (requirements-analyst, engineering-architect, plan-work-skill)
and **two rubrics** (P-VER on SRD/TDD; P-VER on WP set), plus the
slice-end review. If it lives inside the rubric, then changes to the
question set conflate with changes to the rubric's pass/fail logic; if
it lives standalone, both can evolve independently with clean
versioning.

The existing pattern in the marketplace supports option (a) directly.
Every other named cross-cutting standard lives under
`references/standards/` — `CONTRACT_FIRST_STANDARD.md`,
`WORK_PACKAGE_STANDARD.md`, `WP_BACKEND_STANDARD.md`,
`CRITICAL_THINKING_STANDARD.md`, `UX_VISUAL_DESIGN_STANDARD.md`. The
naming convention (UPPERCASE_WITH_UNDERSCORES.md) is consistent across
them. A new `VERIFICATION_QUESTIONS.md` slots in immediately.

## Alternatives considered

1. **Embed in `decompose-validation-rubric.md` (rejected).** The
   rubric is one consumer of the canonical, not its owner. Embedding
   would couple "the questions to ask" with "the check that enforces
   they're answered" — two distinct concerns. Drift becomes likely:
   if the rubric evolves but agents read a snapshot of the old
   embedded version, the single-source-of-truth promise (NFR-004)
   silently breaks.

2. **Split — questions in one file, adapter table in another
   (rejected).** Three reasons. (a) The adapter table references the
   questions (specifically Q14-Q20 are *the* adapter questions);
   splitting forces a cross-file integrity check. (b) Doubles the
   surface for version drift. (c) Skill prose and agent prompts already
   manage one citation per concept; introducing two breaks
   citation-presence checks.

3. **Put it at the same level as the existing `decompose-validation-rubric.md`
   (i.e., `plugins/sulis/references/VERIFICATION_QUESTIONS.md`)
   (rejected).** Inconsistent with the existing
   `references/standards/` convention. Mixing standards-level docs
   with rubric-level docs makes the directory a junk drawer.

## File contract

The file MUST contain:

1. **Title + status** (`v1.0.0`, ACTIVE)
2. **Citation block** — *"This file is the canonical question set per
   ADR-004. Cite by relative path. Do not inline-duplicate."*
3. **Foundational questions Q1-Q4** — verbatim, numbered.
4. **Per-integration questions Q5-Q13** — verbatim, numbered.
5. **Per-kind adapter questions Q14-Q20** — verbatim, numbered.
6. **Kind→adapter table** — seven rows per ADR-007.
7. **Version field** — `1.0.0` initially; bumped per minor on any
   question addition/removal.
8. **Usage block** — instructions for consumers (read at runtime,
   cite by relative path, version-currency check).

The exact 20 questions and the table content are produced by WP-001
(see TDD Work Package preview).

## Consequences

**Positive.**
- SSOT enforced architecturally — there is one place to edit.
- Citation-presence check in P-VER (NFR-006) becomes a literal regex
  match for the canonical's path.
- Consistent with marketplace conventions; future contributors find
  it where they expect to find it.

**Negative.**
- Adds one more file under `references/standards/`. Marginal cost.

**Neutral.**
- The merge-date constant for grandfather check (per ADR-002) lives
  in `decompose-validation-rubric.md`, not here. The two files are
  edited in this same change but for different reasons.

## Discoverability

The file is added to:
- `plugins/sulis/references/standards/README.md` (the standards
  directory's index) as an entry.
- The relevant skill prose files cite it explicitly.
- The agent prompts cite it explicitly.
- The README of the plugin (if present) lists it among the standards.

This is enforced by WP-006 (skill prose + agent prompt updates).
