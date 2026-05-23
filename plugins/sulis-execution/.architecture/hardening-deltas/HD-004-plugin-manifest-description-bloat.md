---
id: HD-004
title: Replace cumulative plugin-manifest descriptions with one-line summaries + CHANGELOG.md
status: implemented
severity: HIGH
pillar: form
sources:
  - SEA audit report 2026-05-23 (Pattern H — Plugin manifest description as cumulative changelog IS the bug)
  - Two prior JSON-corruption incidents in plugin.json (v0.19.x, v0.20.0+)
created: 2026-05-23
implemented: 2026-05-23
---

## Context

The plugin marketplace manifest's `description` field had become a cumulative changelog (~10,000 words for sulis-execution; ~5,000 for sea; etc.). Each release appended its history to the description as a freeform string. Two real incidents this month:

1. **v0.19.x** — unescaped double-quote characters in a description paragraph corrupted the JSON. Required surgical Python repair.
2. **v0.20.0+** — same class. Same fix needed.

The pattern is fundamentally a category error. JSON has no escape forgiveness for embedded prose; the description grows linearly with releases; the field is supposed to be a one-sentence marketplace surface (per Claude Code plugin convention, mirroring npm `package.json` and VSCode extensions).

## Defect

- Plugin `description` field is treated as the canonical changelog
- Each release appends a paragraph (including quoted commit messages and shell snippets)
- JSON manifest corrupts when any appended content contains unescaped `"`, `\\`, or control chars
- Founders + tooling that read the description (CLI plugin listings, marketplace UIs) see thousands of words instead of a one-sentence summary
- No CHANGELOG.md to refer to instead — the history existed nowhere else

## Resolution

### ADDED

- `plugins/sulis-execution/CHANGELOG.md` — receives the entire prior description content; new section "Cumulative history (through v0.21.2)"
- `plugins/sea/CHANGELOG.md` — same migration
- `plugins/srd/CHANGELOG.md` — same migration
- `plugins/sulis-concierge/CHANGELOG.md` — same migration
- This delta document (`.architecture/hardening-deltas/HD-004-*.md`) as the audit trail

### MODIFIED

- `plugins/sulis-execution/.claude-plugin/plugin.json` — description: 22,882 chars → 275 chars (one sentence)
- `plugins/sea/.claude-plugin/plugin.json` — 10,841 → 305 chars
- `plugins/srd/.claude-plugin/plugin.json` — 5,353 → 288 chars
- `plugins/sulis-concierge/.claude-plugin/plugin.json` — 3,949 → 290 chars
- `plugins/sulis-execution/.claude-plugin/plugin.json` — version 0.21.2 → 0.21.3
- `.claude-plugin/marketplace.json` — sulis-execution 0.21.2 → 0.21.3; metadata 1.38.2 → 1.38.3

### REMOVED

- Nothing was deleted; content was migrated to `CHANGELOG.md` files.

## Plugins NOT touched in this delta

These plugins had descriptions under 1,800 chars and don't yet hit the corruption threshold:

| Plugin | Description length | Action |
|---|---|---|
| sulis-business-strategy | 1,782 chars | Defer (plugin slated for retirement anyway) |
| idc | 1,566 chars | Watch; migrate if it grows |
| sulis-security | 1,165 chars | Watch |
| sulis-product-development | 1,002 chars | Watch |
| sulis-design | 720 chars | OK |
| sulis-strategy | 701 chars | OK |
| sulis-builder | 696 chars | Defer (slated for retirement) |
| sulis-context | 253 chars | OK |
| sulis-platform-sdk | 178 chars | OK |

Future releases of any plugin should write release notes to the plugin's `CHANGELOG.md` rather than appending to the description. The description should stay roughly the same length forever — it's a marketplace summary, not a release log.

## Acceptance criteria

- All 4 migrated plugin.json files parse cleanly under `json.load`
- All 4 descriptions are < 350 chars (single-sentence summaries)
- All 4 CHANGELOG.md files contain the migrated history under a "Cumulative history" section
- The marketplace.json metadata + sulis-execution version are bumped consistently
- This delta document exists and is marked `status: implemented`

## Tests

No characterisation test was added — HD-004 is a manifest-shape fix, not a code behaviour change. The test that would catch a regression already exists: the failure-propagating JSON validation that runs before every commit (since v0.19.x). If a future release re-introduces a bloated description with corruption, that check fails the commit.

A future delta (e.g., HD-NNN) could add a CI check that asserts `len(description) < 500` for every plugin manifest. Not in this delta's scope.

## Verification

```bash
# All 4 manifests parse cleanly
python3 -c "
import json
for f in [
    'plugins/sulis-execution/.claude-plugin/plugin.json',
    'plugins/sea/.claude-plugin/plugin.json',
    'plugins/srd/.claude-plugin/plugin.json',
    'plugins/sulis-concierge/.claude-plugin/plugin.json',
]:
    m = json.load(open(f))
    assert len(m['description']) < 500, f'{f} description still too long'
print('All checks pass.')
"
```

## What this DOESN'T fix (deferred)

- **CI check enforcing description length** — could add an automated assertion in CI. Not in this delta's scope.
- **Retroactive cleanup of mid-sized descriptions** (idc, sulis-security, sulis-product-development at ~1000-1600 chars) — not at corruption threshold yet; migrate when they cross ~2000 chars or when bandwidth allows.
- **CHANGELOG.md format standardisation** — Keep-a-Changelog format vs current freeform. The migrated content is a single freeform block; future structured releases could adopt Keep-a-Changelog. Out of scope for HD-004.

## See also

- SEA audit report (`Pattern H`): the architectural diagnosis that triggered this delta
- The two prior JSON-corruption commits referenced in the SEA audit
- Plan: `/Users/iain/.claude/plans/eager-crunching-quail.md` (Batch 1 of 6)
