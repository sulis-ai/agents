# Contributing to Sulis AI Standards

## Adding a New Skill

Before you start, read the **[Skill Authoring Guide](docs/skill-authoring-guide.md)**.

1. **Create a skill directory** under the relevant plugin:
   ```
   plugins/sulis/skills/your-skill-name/
   ```

2. **Write `SKILL.md`** — this is the skill's prompt entrypoint. A skill is a folder, not just a markdown file — include `references/`, `scripts/`, `assets/`, or `examples/` subdirectories as needed.

3. **Build a Gotchas section** in your `SKILL.md` — even a short one. Update it as Claude hits new edge cases.

4. **Test locally** — point your local Claude Code at this repo (see [CLAUDE.md](CLAUDE.md#testing-locally)) and run the slash command to verify it works.

5. **Open a PR** with a clear description of what the skill does and how to test it.

## Adding a New Reference Standard

Reference standards live in `plugins/sulis/references/` and define governing rules
that skills and agents load and apply. Unlike skills, reference standards are not
directly user-invocable — they are loaded by skills (e.g. `critical-thinking` loads
`references/critical-thinking-standard.md`) or referenced in agent prompts.

### Naming Convention

Each standard uses a two-letter prefix that identifies its domain:

| Prefix | Domain |
|--------|--------|
| `EP-` | Engineering Principles |
| `BR-` | Brand Identity |
| `CQ-` | Content Quality |
| `SEC-` | Security |

New prefixes follow the same pattern: two uppercase letters reflecting the domain,
hyphen, sequential number (e.g. `DS-01`, `UX-01`).

### Required Structure

Every reference standard file MUST follow this structure:

1. **`# Title`** — document title
2. **`<!-- summary -->`** — opening summary (10–30% of total length; self-sufficient)
3. **`<!-- detail -->`** — detail section boundary marker
4. **`## Provenance`** — intellectual lineage; mark as practitioner knowledge if not peer-reviewed
5. **`## Severity Convention`** — MUST / SHOULD / MAY table (copy from an existing standard)
6. **Numbered sections** with stable IDs (e.g. `BR-01`, `CQ-03`) for targeted loading
7. **`## Version History`** — table with version, date, and change description

### Version Bump Rule

Adding a new reference standard is a **minor** version bump for the containing plugin.

### Steps

1. Create the file at `plugins/sulis/references/your-standard.md`.
2. Follow the required structure above.
3. Update `plugins/sulis/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` with the
   new minor version.
4. If a skill will load this standard, update that skill's `SKILL.md` to reference it.
5. Open a PR with a description of the standard's scope and the evidence base for its
   first principles.

---

## Adding a New Plugin

1. Create a new directory under `plugins/` (e.g. `plugins/your-plugin/`).
2. Add `.claude-plugin/plugin.json` with the plugin manifest:
   ```json
   {
     "name": "your-plugin",
     "description": "What this plugin does",
     "version": "0.1.0",
     "author": { "name": "Your Name" }
   }
   ```
3. Add a `README.md` documenting the plugin.
4. Register the plugin in `.claude-plugin/marketplace.json` under the `plugins` object.
5. Open a PR.

## Testing Before Merging

- Always test skills locally before opening a PR.
- Verify JSON files are valid (`.claude-plugin/marketplace.json`, `plugin.json`).
- Check that any new skill's slash command runs without errors in a test project.

## Release Process

### Releasing a Plugin Update

1. **Bump the version** in the plugin's `.claude-plugin/plugin.json` following [semver](https://semver.org/):
   - Patch (`1.8.0` -> `1.8.1`): bug fixes, minor prompt tweaks
   - Minor (`1.8.0` -> `1.9.0`): new skills, new features
   - Major (`1.8.0` -> `2.0.0`): breaking changes
2. **Update `.claude-plugin/marketplace.json`** to match the new plugin version.
3. **Commit** with a message like: `release: srd v1.9.0 — add new-skill-name skill`
4. **Tag** the commit: `git tag srd-v1.9.0`
5. **Push** the commit and tag: `git push origin main --tags`

## PR and Review Workflow

- All changes go through PRs against `main`.
- PRs should include a description of what changed and how to test it.
- Keep PRs focused — one skill or one feature per PR where possible.
