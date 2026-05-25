# External Ref Sweep — the 12 categories

Commit 4 is the highest-risk step in a consolidation because cross-plugin references can be cited from anywhere — CLAUDE.md at the repo root, other plugins' bodies, the Sulis agent itself, hidden in test fixtures.

This document enumerates the 12 categories of references that need updating, plus the deterministic procedure to find them.

## The deterministic helper

`find_external_refs.py` does the heavy lifting. It runs `git grep` for `plugins/{source}/` across the marketplace (excluding the source plugin itself), plus a separate sweep for `subagent_type` references to any agent in the source plugin.

```bash
python3 plugins/sulis/skills/consolidate-into-sulis/scripts/find_external_refs.py \
  --marketplace-root . \
  --source-plugin {source} \
  --agent-names {agent-name},{another-name}
```

The output is grouped by file with line numbers — every line is an edit site for Commit 4 (or earlier commits, if the reference is in a file being moved in that commit).

## The 12 categories

These are the categories Commit 4 (and ancillary edits in Commits 1–3) needs to cover. Each category has a concrete locator and an edit pattern.

### 1. Skill `description:` fields

Where: `plugins/*/skills/*/SKILL.md` frontmatter.

Pattern: descriptions sometimes cite `/sea:blueprint`, `/srd:critical-thinking`, etc. These break on consolidation.

```bash
git grep -E "^description:.*plugins/{source}/" plugins/*/skills/*/SKILL.md
git grep -E "^description:.*/{source}:" plugins/*/skills/*/SKILL.md
```

### 2. Agent body cross-references

Where: `plugins/*/agents/*.md` (mostly the Sulis agent, plus any agent that dispatches another).

Pattern: agent bodies reference other agents by `subagent_type=…` or paths to standards/references in another plugin.

```bash
git grep "plugins/{source}/" plugins/*/agents/*.md
git grep -E "subagent_type[=:].*({agent1}|{agent2})" plugins/*/agents/*.md
```

### 3. Reference docs citing other reference docs

Where: `plugins/*/references/*.md`.

Pattern: standards cite other standards by path; when a cited standard moves, the citation breaks.

```bash
git grep "plugins/{source}/references/" plugins/*/references/*.md
```

### 4. SKILL.md `related_skills:` blocks

Where: `plugins/*/skills/*/SKILL.md` frontmatter, under `related_skills:`.

Pattern: `skill:` paths point at standards in another plugin or skills in another plugin.

```bash
git grep -E "skill:.*plugins/{source}/" plugins/*/skills/*/SKILL.md
git grep -E "skill:.*\.\.\/\.\.\/(\.\.\/)?{source}/" plugins/*/skills/*/SKILL.md
```

### 5. CLAUDE.md (root + per-plugin)

Where: `CLAUDE.md`, `plugins/*/CLAUDE.md`.

Pattern: CLAUDE.md often references specific standards by path for the "required reading" sections. Source-plugin paths break.

```bash
git grep "plugins/{source}/" CLAUDE.md plugins/*/CLAUDE.md
```

### 6. README.md (root + per-plugin)

Where: `README.md`, `plugins/*/README.md`.

Pattern: READMEs link to plugin features by path; can also cite the source plugin's standards.

```bash
git grep "plugins/{source}/" README.md plugins/*/README.md
```

### 7. CHANGELOG.md — leave historical narration alone

Where: `plugins/*/CHANGELOG.md`.

Pattern: CHANGELOG.md narrates prior commits. The paths were correct at the time those commits landed; rewriting them in CHANGELOG is **revisionist** — leave historical entries alone. The source plugin's own CHANGELOG gets a final `[DEPRECATED]` entry at Commit 5; that's the only CHANGELOG edit in the consolidation.

### 8. Cache path patterns in scripts

Where: `plugins/*/scripts/**.py`, `plugins/*/scripts/**.sh`, `plugins/sulis/_lib/**.py`.

Pattern: scripts that resolve the marketplace path via `~/.claude/plugins/cache/{org}/{plugin-source}/...` may cite the source plugin's name.

```bash
git grep -E "cache/.*{source}" plugins/*/scripts/ plugins/sulis/_lib/
```

### 9. Workflow YAML

Where: `.github/workflows/*.yml`.

Pattern: workflows reference plugin paths in `paths:` filters, `working-directory:`, and test invocations.

```bash
git grep "plugins/{source}/" .github/workflows/
git grep -E "name:.*{source}" .github/workflows/
```

### 10. Settings JSON

Where: `plugins/*/settings.json`, `.claude-plugin/marketplace.json`.

Pattern: settings.json hooks reference paths into the source plugin; marketplace.json lists the plugin (which it should keep listing as [DEPRECATED]).

```bash
git grep "plugins/{source}/" plugins/*/settings.json .claude-plugin/marketplace.json
```

### 11. Template files

Where: `plugins/*/skills/*/templates/*.template`, `plugins/*/skills/*/templates/*.md`.

Pattern: templates can hardcode paths to standards or other skills.

```bash
git grep "plugins/{source}/" plugins/*/skills/*/templates/
```

### 12. Test fixtures

Where: `plugins/*/scripts/tests/fixtures/**`.

Pattern: fixture files (markdown, YAML, JSON) can hardcode plugin paths.

```bash
git grep "plugins/{source}/" plugins/*/scripts/tests/fixtures/
```

## The sweep procedure

For each line in `find_external_refs.py` output:

1. **Classify** by category (1–12 above)
2. **Decide** whether it's a Commit-4 edit (the file isn't being moved in this consolidation) or a Commit-2/3 edit (the file is being moved and the path inside it needs updating during the move)
3. **Apply** the edit — replace `plugins/{source}/...` with `plugins/sulis/...`, applying any rename mappings from `CONSOLIDATION_PLAN.md`
4. **Verify** by re-running the grep after the edit; the line should be gone

After all categories are swept:

```bash
git grep "plugins/{source}/" .
# Expected: only hits inside the source plugin's now-DEPRECATED directory itself
# (CHANGELOG historical narration, README deprecation pointer, etc.)
```

Any hit outside the source plugin's own directory after Commit 4 = unfinished sweep = blocker on the consolidation.

## Known sweep traps

- **Markdown links.** A line like `[the lifecycle](plugins/sulis-execution/references/lifecycle.md)` has the path inside parens — `git grep` finds it, the edit must preserve link syntax.
- **Code-block paths inside markdown.** Inside fenced code blocks, paths might be example invocations the operator runs by hand — same edit, but verify the example still makes sense.
- **YAML anchors.** Some workflows use `&` anchors and `*` references; renaming the anchored value requires updating both. Rare but happens.
- **Multi-line ref blocks.** Some `related_skills:` blocks span multiple lines; `git grep -n` shows you the line but the edit might require updating the surrounding context.

When in doubt, edit one occurrence, re-run the grep, confirm it's gone, then move to the next category. Bulk `sed` across the marketplace is fast but produces unreviewable diffs.
