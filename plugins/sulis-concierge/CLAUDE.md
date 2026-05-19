# Sulis Concierge

The founder's **VP of Engineering** across the Sulis AI marketplace —
their technical co-founder in everything but title.

## Purpose

Non-technical founders shouldn't have to know that nine specialised
agents exist, when to switch between them, or what slash command to
type next. The Concierge owns *how* the product gets built —
sequencing, tools, patterns, artifacts, which specialist to invoke and
when — and brings the founder only decisions a CEO would actually
field: product scope, users, business model, brand voice, risk
appetite. Everything else is decided silently and reported.

## Entry point

```bash
claude --agent sulis-concierge
```

Founders start here. Everything else flows from this command.

## What's in this plugin

- **`agents/concierge.md`** — the primary agent. Owns the 7-phase
  journey, dispatches specialists, translates output.
- **`references/journey-model.md`** — 7-phase model with entry/exit
  criteria.
- **`plugins/srd/references/founder-english.md`** (marketplace-wide FE-01..FE-10, v1.0.0+) — plain-language translation
  patterns for marketplace internal vocabulary.
- **`references/subagent-dispatch.md`** — decision rules for "spawn vs
  recommend" per specialist.
- **`skills/start/SKILL.md`** — `/sulis-concierge:start` — resume an
  existing journey.
- **`skills/status/SKILL.md`** — `/sulis-concierge:status` — show
  current state.
- **`skills/handoff/SKILL.md`** — `/sulis-concierge:handoff` — capture
  context when transitioning to a specialist.

## Journey state

`.concierge/{project}/JOURNEY.md` — single source of truth for "where
the founder is" across sessions. Persists between sessions.

`.concierge/{project}/handoffs/HANDOFF-{NN}-to-{specialist}.md` —
context notes for specialists, including non-technical-founder flag.

## Composition with other plugins

The concierge **invokes**:

- `sulis-context` (discovery)
- `srd` (requirements analyst)
- `sea` (architect, decomposer, verifier)
- `sulis-execution` (Work Package executor — ships in same v1.12.0)
- `sulis-security` (codebase assessor)

For non-build paths (pitch deck / brand / strategy), the concierge
routes to:

- `idc` (investor deck coach)
- `sulis-design` (design system)
- `sulis-strategy` (business strategy)

## Convention Preference + AAF compliance

The Concierge applies CP-01..CP-05 and AAF-01..AAF-09 aggressively at
every founder-facing message. Specialist agents apply their own AAF
internally; the concierge re-translates anyway.

## Versioning

v0.1.0 — initial release. Recommend-only pattern (founder runs slash
commands; concierge reads produced artifacts). Ships in marketplace
v1.12.0 alongside `sulis-execution`.

v0.2 (next commit in v1.12.0) — adds Agent-tool spawning for short-
running specialists.
