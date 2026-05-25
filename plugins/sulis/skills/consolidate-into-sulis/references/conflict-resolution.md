# Conflict Resolution — collisions + tin test + rename strategy

When a source plugin is folded into sulis, two kinds of naming conflict can arise:

1. **Direct collision** — source has a skill / agent / reference with the same name as one already in sulis.
2. **Tin-test failure** — the incoming skill name doesn't say what it does on the tin; the founder will see it in chrome and not know what it operates on.

This document gives the rubric for each, plus the worked rename strategy for the 4 Phase 3 consolidations.

## Direct collision — rename rule

When source and target both have an item named `X`:

- **Skill collision** → suffix the source-plugin's qualifier: `{source-qualifier}-{name}` (e.g., `status` → `wp-status` in the sulis-execution → sulis precedent)
- **Agent collision** → suffix the source-plugin's qualifier similarly (rare in practice — agent names tend to be specialist-role-specific)
- **Reference collision** → suffix the topic qualifier (e.g., `templates.md` → `srd-templates.md`)
- **Script collision** → suffix the source-plugin's qualifier in the filename (e.g., `inventory.py` → `srd-inventory.py`)
- **CI workflow collision** → always keep the source qualifier; new name is `sulis-{source-qualifier}-tests.yml`

The qualifier is whatever distinguishes the source plugin's purpose (`executor` from sulis-execution; `context` from sulis-context; etc.). If unsure, use the source plugin's name minus the `sulis-` prefix.

## Tin test — the founder-friendliness rubric

A skill name passes the tin test if the founder, seeing the name in autocomplete or a status message, can decode what it operates on.

| Test | Pass | Fail |
|---|---|---|
| **Bare verb test** | verb + noun (`check-tests`, `code-health`) | bare verb (`decompose`, `harden`, `probe`, `verify`, `blueprint`, `refresh`, `show`, `discover`) |
| **Acronym test** | only universal acronyms (`pr`, `ci`, `url`) | internal-jargon acronyms (`srd-templates`, `spec-index`, `wp-status` — though `wp-status` is grandfathered) |
| **Clear noun test** | recognisable noun alone (`inbox`, `status`, `start`) | abstract noun without context (`synthesis`, `audit` alone) |

A name that fails the tin test gets renamed during Commit 2 of the consolidation.

### When tin-test failure is acceptable

Two carve-outs:

1. **Skill is operator-only** — the founder never sees it. Examples: `critical-thinking` (a methodology utility the Sulis agent dispatches but the founder never types). Bare verbs are acceptable here because the audience is operators who recognise the term.
2. **Existing skill grandfathered** — existing sulis plugin skills (`retry`, `handoff`, `start`, `status`) are out of scope for this skill's rename pass. They get addressed in a separate focused commit if at all.

Operator-only carve-outs must be **explicitly justified in CONSOLIDATION_PLAN.md** — not "it's operator-only because I say so." The justification asks: is this skill listed in any founder-facing context (autocomplete, status output, journey docs)? If yes, it's founder-visible → apply the tin test.

## Worked rename strategy for Phase 3 consolidations

### sulis-context → sulis (smallest, practice run)

| Old | New | Rationale |
|---|---|---|
| `discover` | `discover-context` | Bare verb → verb + noun |
| `refresh` | `refresh-context` | Bare verb → verb + noun |
| `show` | `show-context` | Bare verb → verb + noun |

Agent: `context-cartographer` — no rename; already self-describing.

### sulis-security → sulis

| Old | New | Rationale |
|---|---|---|
| `codebase-assess` | (already [DEPRECATED], no rename needed) | Skill is superseded by `/sulis:code-health`; consolidation moves the source files into sulis as historical record only |

Agent: `security-reviewer` — no rename; already self-describing.

### sea → sulis

| Old | New | Rationale |
|---|---|---|
| `blueprint` | `draft-architecture` | Bare verb / abstract noun → verb + noun |
| `decompose` | `plan-work` | Bare verb → verb + noun (founder-friendlier than `decompose-design-into-tasks`) |
| `harden` | `harden-codebase` | Bare verb → verb + noun |
| `probe` | `analyse-codebase` | Bare verb → verb + noun |
| `verify` | `verify-architecture` | Bare verb → verb + noun |
| `code-review` | (keep) | Already verb + noun |
| `codebase-audit` | (keep) | Already verb + noun |
| `suggest-split` | (keep) | Already verb + noun (operates on PR; obvious from context) |

Agent: `engineering-architect` — no rename.

### srd → sulis (largest, last)

| Old | New | Rationale |
|---|---|---|
| `tree-synthesis` | `map-architecture` | Abstract noun → verb + noun |
| `srd-templates` | `requirements-templates` | Internal acronym → plain noun |
| `spec-index` | `index-specifications` | Acronym + abstract → verb + noun |
| `critical-thinking` | (keep — operator-only) | Methodology utility, never founder-visible |
| `codebase-mapping` | (keep) | Already verb-noun-shaped |
| `requirements-validation` | (keep) | Already verb-noun-shaped |

Agent: `requirements-analyst` — no rename.

Also relevant for srd: many of srd's references are foundational marketplace standards (AAF, FE, engineering-principles, etc.). They keep their current names but move to `plugins/sulis/references/`.

## What changes in the description field when a skill is renamed

When a skill's name changes (e.g., `decompose` → `plan-work`), the `description:` frontmatter field often references the skill's operation in operator vocabulary. The description should be rewritten to match the new name.

Worked example — sea's `decompose`:

Before:
```yaml
description: Use after /sea:blueprint has produced a TDD. Decomposes the TDD into atomic Work Packages (WP-NNN-*.md) that an execution agent (Claude Code, GSD, engineering team) can implement one at a time without merge conflicts.
```

After rename to `plan-work`:
```yaml
description: Use when the founder has a technical design and needs it broken into a to-do list of independent tasks that can ship one at a time without conflicting with each other. Produces a Work Package index (one task per file) ordered by dependency.
```

The rewritten description reads in founder English while still containing the operator keyword (`Work Package`) for the Sulis agent's dispatch routing.

## Conflict-resolution checklist (per consolidation)

Before Commit 2 begins:

- [ ] Direct collisions listed in CONSOLIDATION_PLAN.md
- [ ] Tin-test failures listed in CONSOLIDATION_PLAN.md with rename targets
- [ ] Each operator-only carve-out justified (one sentence: "not founder-visible because …")
- [ ] Each rename has a description rewrite plan if the description cites the old name
- [ ] CI workflow rename target set (always `sulis-{qualifier}-tests.yml`)
