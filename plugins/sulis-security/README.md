# sulis-security — [DEPRECATED at v0.7.0]

> **This plugin has been consolidated into [`sulis`](../sulis/) at v0.40.0 (commit chain `bdea2e8..` on 2026-05-25).**
>
> This is the **fourth and final Phase 3 consolidation** of the change-as-primitive build.

## What moved where

### Skill (1)

| Old | New | Notes |
|---|---|---|
| `/sulis-security:codebase-assess` | `/sulis:codebase-assess` | No rename. Skill was already DEPRECATED in favour of `/sulis:code-health` since sulis v0.22.0+; remains callable through its deprecation window |

### Agent (1)

| Old | New |
|---|---|
| `security-reviewer` (at `plugins/sulis-security/agents/`) | `security-reviewer` (at `plugins/sulis/agents/`) — invoked via `claude --agent security-reviewer` |

### References (1)

Moved from `plugins/sulis-security/references/` to `plugins/sulis/references/`:

- `viability-framework.md`

(Plus nested under skills/codebase-assess: `primitives.md`, `tool-commands.md` — moved with the skill.)

## Why this plugin shell remains

Per the Sulis AI marketplace's consolidation convention (set by `sulis-execution` → `sulis` v0.30.0, `sulis-context` → `sulis` v0.35.0, `srd` → `sulis` v0.37.0, `sea` → `sulis` v0.38.0, and earlier `sulis-concierge` → `sulis` v0.2.0): consolidated source plugins are marked `[DEPRECATED]` in-place rather than deleted outright.

This gives:

- Marketplace compatibility (any external listing or link still resolves)
- Audit trail (the old layout is preserved as historical record)
- Forward pointer (this README + the deprecation marker in `plugin.json`)

For future development, work directly in `plugins/sulis/`. This shell will be removed only when the marketplace's deprecation window for `sulis-security` (one major release after v0.7.0) closes.

## What's next

**Phase 3 of the change-as-primitive build is now complete.** All four specialist plugins (sulis-context, srd, sea, sulis-security) have been folded into the canonical `sulis` plugin. Marketplace surface reduced to one front-door plugin per the design.

Phases 4-7 remain (standards amendments, change-as-primitive infrastructure, founder-facing skills, end-to-end test). See `plugins/sulis/docs/change-as-primitive-design.md` for the full plan.
