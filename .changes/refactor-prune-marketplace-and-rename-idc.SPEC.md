---
founder_facing: false
---
# Spec — prune marketplace + rename idc

**Change:** CH-01KSNV · refactor
**Scope:** marketplace structure only; no functional code change

## What this should do

Reshape the `sulis-ai/agents` marketplace from 13 plugins down to 2,
and rename the surviving second plugin from `idc` to `investor-coach`.

### Part A — prune the marketplace

Remove the following 11 plugin entries from
`.claude-plugin/marketplace.json` and delete the `plugins/<name>/`
directories under git:

**Already-deprecated stubs** (5 — functionality consolidated into sulis):
- `srd` (deprecated v1.23.0 → sulis v0.37.0)
- `sea` (deprecated v0.21.0 → sulis v0.38.0)
- `sulis-context` (deprecated v0.4.0 → sulis v0.35.0)
- `sulis-security` (deprecated v0.7.0 → sulis v0.40.0)
- `sulis-execution` (deprecated → sulis recent consolidation)

**Active OFM-studio plugins** (6 — founder-confirmed out of scope):
- `sulis-strategy`
- `sulis-business-strategy`
- `sulis-product-development`
- `sulis-builder`
- `sulis-design`
- `sulis-platform-sdk`

Git history preserves all of them — recoverable if needed.

### Part B — rename idc → investor-coach

- Move `plugins/idc/` → `plugins/investor-coach/` via `git mv`.
- Update `plugins/investor-coach/.claude-plugin/plugin.json` `name`
  field: `"idc"` → `"investor-coach"`.
- Update `.claude-plugin/marketplace.json` — the surviving entry's
  `name` and `source`.
- Rewrite all 85 `/idc:` references inside the renamed plugin to
  `/investor-coach:` (in skills, agent.md, references, scripts,
  README, templates). The plugin namespace IS the slug, so every
  cross-reference is in scope.
- Keep historical references in `plugins/investor-coach/CHANGELOG.md`
  intact — `idc` IS what it was called when those entries were
  written; rewriting them would destroy the audit trail.

### Part C — update top-level README

- Drop the tables / links that reference removed plugins.
- Rewrite `/idc:` mentions to `/investor-coach:`.
- Drop references to the old `idc` slug.
- Ensure the README only describes the two remaining plugins
  (sulis + investor-coach).

## How we'll know it's done

- `.claude-plugin/marketplace.json` lists exactly 2 plugins:
  `sulis` and `investor-coach`.
- `plugins/` contains exactly two directories: `sulis/` and
  `investor-coach/`.
- `git grep "/idc:"` returns ZERO matches under
  `plugins/investor-coach/`; matches in `CHANGELOG.md` are
  historical-only.
- `git grep "\"idc\""` in marketplace.json or
  investor-coach/plugin.json returns ZERO.
- Top-level `README.md` contains no `/idc:` references and no live
  references to the removed plugins (historical "[DEPRECATED]" line
  items deleted; the removed-plugin tables gone).
- Full unit + integration suite green (the change is structural; no
  sulis tests should fail — verifying belt-and-braces).
- Step 4.5 review gate (#30) PASS.

## What to avoid

- **Do NOT rewrite historical CHANGELOG entries in
  `plugins/investor-coach/CHANGELOG.md`.** They record what happened
  when the plugin was called `idc`; rewriting them is dishonest.
- **Do NOT delete the cached installs at
  `~/.claude/plugins/cache/sulis-ai-agents/idc/*` on the founder's
  machine.** Claude Code's plugin loader handles the transition on
  next reload (the old name simply disappears from the registry;
  the new name appears).
- **Do NOT bump the marketplace.json `metadata.version` field.** That
  field is stale (currently `1.98.1` vs git-tag `v1.110.0`); it's
  not the source of truth for releases (tags are). Fixing it is a
  separate cleanup.
- **Do NOT touch `.pitch/{project}/` artifact paths.** They never
  contained the plugin slug; founders who used `idc` keep their
  pitch artefacts unaffected.

## References

- `.claude-plugin/marketplace.json` — registry to prune
- `plugins/idc/` — directory to rename
- `README.md` (top-level) — references to remove/rename
- The 6 OFM-studio plugins each have their own `plugins/<name>/`
  tree; deletion is recursive `git rm`
