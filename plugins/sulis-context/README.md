# sulis-context — [DEPRECATED at v0.4.0]

> **This plugin has been consolidated into [`sulis`](../sulis/) at v0.35.0 (commit chain `a2b359e..` on 2026-05-25).**

## What moved where

| Old (in this plugin) | New (in `sulis`) |
|---|---|
| `/sulis-context:discover` | `/sulis:discover-context` |
| `/sulis-context:refresh` | `/sulis:refresh-context` |
| `/sulis-context:show` | `/sulis:show-context` |
| `context-cartographer` agent | Now at `plugins/sulis/agents/context-cartographer.md`; founder uses the slash commands above |
| `classification-taxonomy.md` reference | `plugins/sulis/references/classification-taxonomy.md` |
| `context-index-template.md` reference | `plugins/sulis/references/context-index-template.md` |
| `discovery-protocol.md` reference | `plugins/sulis/references/discovery-protocol.md` |

Slash-command names were renamed during the move per the **tin-test rubric** in `plugins/sulis/skills/consolidate-into-sulis/references/conflict-resolution.md`: bare verbs like `discover` / `refresh` / `show` were renamed to verb-noun form so a founder reading them in autocomplete can tell what they operate on.

## Why this plugin shell remains

Per the Sulis AI marketplace's consolidation convention (set by the `sulis-execution` → `sulis` migration at v0.30.0 and the `sulis-concierge` → `sulis` migration at v0.2.0): consolidated source plugins are marked `[DEPRECATED]` in-place rather than deleted outright. No shim skills get written.

This gives:

- Marketplace compatibility (any external listing or link still resolves)
- Audit trail (the old layout is preserved as historical record)
- Forward pointer (this README + the deprecation marker in `plugin.json`)

For future development, work directly in `plugins/sulis/`. This shell will be removed only when the marketplace's deprecation window for `sulis-context` (one major release after v0.4.0) closes.

## Original README

Preserved below for historical context.

---

# sulis-context — Context Cartographer (historical)

> Discover existing context in any project. Produce a classified index that
> downstream Sulis plugins respect instead of restating.

`sulis-context` solves a recurring failure mode of generative architecture
and requirements tooling: **agents writing artifacts in repos that already
have rich knowledge bases, ignoring everything that's already there.**

When SRD facilitates requirements, it should know that `DOMAIN_MODEL.md`
already defines the entity vocabulary. When SEA writes a TDD, it should
reference the existing `ARCHITECTURE.md` for Clean Architecture rather than
re-deriving it. When sulis-security audits, it should not flag a standard
that the team already enforces in `architecture/standards/`.

(For the full historical README content, see git history at commit
`4974818^` and earlier.)
