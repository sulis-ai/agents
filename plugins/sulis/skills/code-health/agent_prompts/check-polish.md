# Agent prompt — check-polish (tier 7 Polished)

You are an independent runner for tier 7 (Polished) of code-health.
Read `_shared-contract.md` for the output contract.

## Your scope

Tier 7 — Polished — covers:
- Documentation completeness (README, CHANGELOG, LICENSE, plugin.json keywords)
- CQ-04 technical debt density (TODO/FIXME/HACK markers — canonical owner)
- File hygiene (trailing whitespace, mixed line endings, trailing newline)

## Run the scanner

```bash
cd {repo_root}
python3 plugins/sulis/skills/check-polish/scripts/scanner.py \
  --repo-root {repo_root} \
  --project {project} \
  --scope codebase \
  --raw
```

## Apply interpretation lenses

1. **TD density context** — TD-001 (>5% TODO/FIXME density per file)
   is a concern for stable modules but expected in active development.
   If a finding is in a file with `WIP|wip|DRAFT` in path or first
   line, mark as informational.

2. **MUC-F4 cap** — ≤ 10 findings across all sub-categories.

## Verdict assignment

- PASS — 0 findings (this is the most common outcome on healthy repos)
- NEEDS_ATTENTION — 1+ concerns (missing README, TD-002 file with
  >20 markers)
- FAILED — rare for this tier; only if multiple plugins lack any
  documentation

## Return per the shared contract format
