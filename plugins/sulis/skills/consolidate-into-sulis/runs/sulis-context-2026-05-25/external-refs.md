# External references to `sulis-context`

All file paths and agent dispatch points that mention `plugins/sulis-context/` or the source plugin's agents.
Every line below needs updating during Commits 2–4 of the consolidation.

## 1. Files citing source-plugin paths

### `README.md`

- L52: `| **[sulis-context](plugins/sulis-context/)** | Discovers existing architecture, ADRs, conventions in a brownfield codeb…`

### `plugins/sulis/CHANGELOG.md`

- L2094: `- `plugins/sulis-context/CHANGELOG.md` (35 lines — reconstructed from`

### `plugins/sulis/agents/sulis.VERIFICATION_REPORT.md`

- L159: `| context-cartographer | `plugins/sulis-context/agents/context-cartographer.md` | YES |`

### `plugins/sulis/agents/sulis.md`

- L95: `skill: ../../sulis-context/agents/context-cartographer`

### `plugins/sulis/skills/add-agent/VERIFICATION_REPORT.md`

- L167: `| context-cartographer (example cited) | `plugins/sulis-context/agents/context-cartographer.md` | YES | |`

### `plugins/sulis/skills/consolidate-into-sulis/VERIFICATION_REPORT.md`

- L115: `- `find_external_refs.py` → initially 4 refs; **caught a bug** during smoke (missed `../../sulis-context/` relative-path…`

## 2. Subagent_type dispatch references

None.

## 3. Sweep checklist (apply during Commits 2–4)

For each line above:
- Replace `plugins/{source}/` with `plugins/sulis/`
- Apply any skill / agent / reference renames from CONSOLIDATION_PLAN.md
- For subagent_type references: update to the new agent location after Commit 3 lands

After Commit 4:
```bash
git grep "plugins/sulis-context/" .
# Expected: zero hits outside the source plugin's own DEPRECATED shell
```

## Summary

- Path references: **6** across **6** files
- Subagent_type references: **0** across **0** files

