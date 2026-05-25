# sea — [DEPRECATED at v0.21.0]

> **This plugin has been consolidated into [`sulis`](../sulis/) at v0.38.0 (commit chain `714bb23..` on 2026-05-25).**

## What moved where

### Skills

| Old (in this plugin) | New (in `sulis`) | Notes |
|---|---|---|
| `/sea:blueprint` | `/sulis:draft-architecture` | Tin-test rename (bare verb / abstract noun) |
| `/sea:decompose` | `/sulis:plan-work` | Tin-test rename (bare verb) |
| `/sea:harden` | `/sulis:harden-codebase` | Tin-test rename (bare verb) |
| `/sea:probe` | `/sulis:analyse-codebase` | Tin-test rename (bare verb); brings scripts/ + tests/ subdirs (ast-grep + lizard + scc deterministic orchestrator) |
| `/sea:verify` | `/sulis:verify-architecture` | Tin-test rename (bare verb) |
| `/sea:code-review` | `/sulis:code-review` | No rename — already verb-noun |
| `/sea:codebase-audit` | `/sulis:codebase-audit` | No rename — already verb-noun |
| `/sea:suggest-split` | `/sulis:suggest-split` | No rename — clear in context |

### Agent

| Old | New |
|---|---|
| `engineering-architect` (at `plugins/sea/agents/`) | `engineering-architect` (at `plugins/sulis/agents/`) — invoked via `claude --agent engineering-architect` |

### References (11)

Moved from `plugins/sea/references/` to `plugins/sulis/references/`:

- `architecture-patterns.md`
- `boring-code.md`
- `change-primitives.md` (the 22-primitive vocabulary of code change)
- `code-intelligence-template.md` (CODE_INTELLIGENCE.html shape)
- `code-review-standard.md` (CR-01..CR-10)
- `decompose-validation-rubric.md`
- `hardening-deltas.md` (HD-NNN format)
- `mece-3-architecture.md` (Form / Armor / Proof)
- `performance-procedural-checks.md`
- `red-green-blue.md` (RGB-TDD)
- `right-sizing.md`

## Why this plugin shell remains

Per the Sulis AI marketplace's consolidation convention (set by `sulis-execution` → `sulis` v0.30.0, `sulis-context` → `sulis` v0.35.0, `srd` → `sulis` v0.37.0, and earlier `sulis-concierge` → `sulis` v0.2.0): consolidated source plugins are marked `[DEPRECATED]` in-place rather than deleted outright. No shim skills get written.

This gives:

- Marketplace compatibility (any external listing or link still resolves)
- Audit trail (the old layout is preserved as historical record)
- Forward pointer (this README + the deprecation marker in `plugin.json`)

For future development, work directly in `plugins/sulis/`. This shell will be removed only when the marketplace's deprecation window for `sea` (one major release after v0.21.0) closes.

## Original README

(For the full historical README content, see git history at commit `714bb23^` and earlier.)
