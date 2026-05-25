# srd — [DEPRECATED at v1.23.0]

> **This plugin has been consolidated into [`sulis`](../sulis/) at v0.37.0 (commit chain `6ed9e9b..` on 2026-05-25).**

## What moved where

### Skills

| Old (in this plugin) | New (in `sulis`) | Notes |
|---|---|---|
| `/srd:codebase-mapping` | `/sulis:codebase-mapping` | No rename — already verb-noun |
| `/srd:critical-thinking` | `/sulis:critical-thinking` | No rename — operator-only methodology utility |
| `/srd:requirements-validation` | `/sulis:requirements-validation` | No rename — already verb-noun |
| `/srd:spec-index` | `/sulis:index-specifications` | Tin-test rename (abbreviation + abstract noun) |
| `/srd:srd-templates` | `/sulis:requirements-templates` | Tin-test rename (internal SRD acronym) |
| `/srd:tree-synthesis` | `/sulis:map-architecture` | Tin-test rename (abstract methodology noun) |

### Agent

| Old | New |
|---|---|
| `requirements-analyst` (at `plugins/srd/agents/`) | `requirements-analyst` (at `plugins/sulis/agents/`) — invoked via `claude --agent requirements-analyst` |

### References (the marketplace-wide standards)

Moved from `plugins/srd/references/` to `plugins/sulis/references/`:

- `audience-adapted-framing-standard.md` (AAF — question-triage discipline)
- `change-work-standard.md` (CW — change-as-primitive)
- `coaching-without-conflict.md` (coexists with `plugins/sulis/references/standards/COACHING_STANDARD.md` as the platform-source version)
- `cognitive-load.md`
- `content-quality.md`
- `convention-preference-standard.md` (CP-01..05)
- `engineering-principles.md` (EP)
- `executor-loop-standard.md` (EL-01..08)
- `founder-english.md` (FE-01..11 — founder-tone discipline)
- `git-workflow-standard.md` (GIT-01..10)
- `pr-hygiene-standard.md` (PH-01..08)
- `repository-contract-standard.md` (RC-01..13)
- `security-standard.md`

### Docs / example specifications

`docs/specifications/` moved to `plugins/sulis/docs/srd-specifications/` with the `srd-` prefix per the consolidation convention.

## Why this plugin shell remains

Per the Sulis AI marketplace's consolidation convention (set by `sulis-execution` → `sulis` v0.30.0, `sulis-context` → `sulis` v0.35.0, and earlier `sulis-concierge` → `sulis` v0.2.0): consolidated source plugins are marked `[DEPRECATED]` in-place rather than deleted outright. No shim skills get written.

This gives:

- Marketplace compatibility (any external listing or link still resolves)
- Audit trail (the old layout is preserved as historical record)
- Forward pointer (this README + the deprecation marker in `plugin.json`)

For future development, work directly in `plugins/sulis/`. This shell will be removed only when the marketplace's deprecation window for `srd` (one major release after v1.23.0) closes.

### Hooks deferred

`.claude-plugin/hooks/codebase-mapping.sh` and `tree-synthesis.sh` remain in this DEPRECATED shell. They were experimental SubagentStart hooks matching the old `srd:requirements-analyst` dispatch pattern. If they're wanted active under sulis, they need re-authoring against the new matcher (`requirements-analyst`, no plugin prefix) — out of scope for this consolidation; tracked in the run's VERIFICATION_REPORT.md as a follow-up.

## Original README

Preserved below for historical context.

---

# SRD: Requirements Analyst Plugin for Claude Code (historical)

A Claude Code plugin that produces handover-ready Software Requirements Documents
through guided conversation. One question at a time. Structured artifacts out the
other end.

(For the full historical README content, see git history at commit `cd7e2e9^` and earlier.)
