---
id: ADR-003
title: Skill name — /sulis:discover-project (canonical drives imperative)
status: accepted
date: 2026-06-01
deciders: [iain]
resolves: SRD Open Question 1
---

## Context

The skill that runs the discover-project Workflow needs a name. Two
candidates:

- `/sulis:setup` — more discoverable for a first-time consumer who
  doesn't know the vocabulary; matches the colloquial "set up the
  project" framing; shorter.
- `/sulis:discover-project` — matches the canonical Workflow name
  exactly; reinforces the Path A convention that the canonical drives
  the imperative; explicit about what the skill does.

The marketplace also has a few existing skills (`/sulis:specify`,
`/sulis:design`, `/sulis:change`, `/sulis:start`) using simple
verb-noun shapes. `/sulis:setup` would fit that shape; so would
`/sulis:discover-project` (verb-noun).

## Decision

**Adopt `/sulis:discover-project` as the primary skill name.**

Path A's discipline is that the canonical Workflow name and the skill
name match — when an operator reads the SKILL.md and looks for the
canonical it conforms to, the binding is obvious. `/sulis:setup` would
introduce a synonym layer ("which Workflow does this run?") and
weaken the canonical-as-spec convention.

If discoverability for first-time consumers matters, the skill prose's
front-matter `description` carries the friendlier surface — e.g.,
*"Set up Sulis for a project by minting its Project entity. Run this
once when adopting Sulis in a new repo."* The slash-command surface
stays canonical.

A future `/sulis:setup` could be added as a thin alias if real
discoverability data shows founders search for "setup" — but starting
with a single canonical name keeps the surface area small and the
binding to the Workflow definition unambiguous.

## Options Considered

- **`/sulis:discover-project` (CHOSEN).** Canonical drives imperative;
  explicit; matches Path A discipline; no synonym layer.
- **`/sulis:setup`** — rejected. More discoverable in isolation but
  introduces a synonym for the Workflow name; weakens the
  canonical-spec binding; would need the documentation to bridge "setup
  runs the discover-project Workflow" which is a translation step
  Path A is trying to eliminate.
- **Both — `/sulis:discover-project` as primary + `/sulis:setup` as
  alias** — rejected for v1. Aliases are easy to add later if needed;
  shipping two surfaces day-one creates an explainer-debt that might
  never get repaid. Founder can revisit at v1.1 if discoverability
  data demands it.

## Consequences

- **Positive:** Canonical-spec binding stays sharp. SKILL.md reader
  finds the canonical at the same name. No second source of truth.
- **Negative:** First-time consumers searching for "setup" don't find
  the skill on the first try. Mitigated by the skill's `description`
  field surfacing the "set up" framing in plain English.
- **Neutral:** If/when the next sibling skill (`env-init`) lands, the
  same convention applies: canonical name = skill name.

## Composition

WP-008 authors the skill at `plugins/sulis/skills/discover-project/SKILL.md`.
The skill's front matter `description` carries the founder-English
surface; the slash-command name is the canonical-driven binding.
