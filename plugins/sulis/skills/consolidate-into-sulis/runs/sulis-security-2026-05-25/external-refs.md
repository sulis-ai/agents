# External references to `sulis-security`

All file paths and agent dispatch points that mention `plugins/sulis-security/` or the source plugin's agents.
Every line below needs updating during Commits 2–4 of the consolidation.

## 1. Files citing source-plugin paths

### `.architecture/sulis-checkup/TDD.md`

- L10: `> `/sulis:verify-architecture`, `/sulis-security:codebase-assess`, `/sulis:code-review`.`
- L99: `| `plugins/sulis-security/skills/codebase-assess/references/primitives.md` | The 25-primitive catalogue; rows 5–8 of the…`
- L125: `| **2** | **Safe** — could anyone be harmed? | Hardcoded secrets in source/history. SQL/command/SSRF injection. Broken a…`
- L128: `| **5** | **Understandable** — can a new person read this? | Names are descriptive (no `wpx/wp/lib` jargon-density probl…`
- L129: `| **6** | **Evolves cleanly** — can we change it without breaking it? | Test coverage is real (not just count — coverage…`

### `README.md`

- L56: `| **[sulis-security](plugins/sulis-security/)** | 25-primitive codebase viability assessment via OODA spiral |`

### `plugins/sea/CHANGELOG.md`

- L42: `Senior Engineering Architect — designs hardened architectures, audits brownfield code for primitive gaps, and decomposes…`

### `plugins/sulis-execution/sdk/docs/recipes/backfill-security-review.md`

- L66: `1. The skill invokes `/sulis-security:codebase-assess` over the`
- L197: `- `plugins/sulis-security/skills/codebase-assess/SKILL.md` — the`

### `plugins/sulis/CHANGELOG.md`

- L1389: ``plugins/sulis-security/`:`
- L1418: `- plugins/sulis-security/.claude-plugin/plugin.json: 0.5.0 → 0.6.0`
- L1923: `+ degradation policy. Mirrors `plugins/sulis-security/skills/codebase-assess/references/tool-commands.md``

### `plugins/sulis/_lib/tools/REFERENCE.md`

- L3: `> **Adapted from** `plugins/sulis-security/skills/codebase-assess/references/tool-commands.md``

### `plugins/sulis/agents/context-cartographer.md`

- L209: `out of scope. Refer them to `/sulis:codebase-audit` or `/sulis-security:codebase-assess`.`

### `plugins/sulis/agents/engineering-architect.md`

- L394: ``/sulis-security:codebase-assess` for a broader audit beyond the MECE-3`

### `plugins/sulis/agents/requirements-analyst.md`

- L1466: `> If you'd rather do a security pass first: `/sulis-security:codebase-assess` runs`
- L1548: `> `/sulis-security:codebase-assess`. If you change your mind and want me to do a full`

### `plugins/sulis/agents/sulis.VERIFICATION_REPORT.md`

- L160: `| security-reviewer | `plugins/sulis-security/agents/security-reviewer.md` | YES |`

### `plugins/sulis/agents/sulis.md`

- L98: `skill: ../../sulis-security/agents/security-reviewer`
- L1151: `| 7 | **Secure** | Viability assessment, business-risk findings | `sulis-security:security-reviewer` — recommend `/sulis…`
- L1631: `> *`/sulis-security:codebase-assess`*`

### `plugins/sulis/references/code-review-standard.md`

- L290: ``plugins/sulis-security/skills/codebase-assess/references/primitives.md`,`

### `plugins/sulis/references/journey-model.md`

- L195: `- Recommend `/sulis-security:codebase-assess` to the founder.`

### `plugins/sulis/references/lifecycle.md`

- L398: `plugins/sulis-security/agents/security-reviewer.md.`
- L1758: `Run /sulis-security:codebase-assess <project> <repo> <staging-url>`

### `plugins/sulis/references/self-heal-budget.md`

- L107: ``/sulis-security:codebase-assess <project> <repo> <staging-url>``

### `plugins/sulis/references/subagent-dispatch.md`

- L63: `| sulis-security:codebase-assess | `/sulis-security:codebase-assess` | recommend | spawn (short-to-medium, returns repor…`

### `plugins/sulis/skills/add-agent/VERIFICATION_REPORT.md`

- L166: `| security-reviewer (example cited) | `plugins/sulis-security/agents/security-reviewer.md` | YES | |`

### `plugins/sulis/skills/add-agent/references/agent-shape-conventions.md`

- L248: `| Specialist auditor | `plugins/sulis-security/agents/security-reviewer.md` |`

### `plugins/sulis/skills/backfill-code-review/SKILL.md`

- L329: `skill for security backfill (uses `/sulis-security:codebase-assess`)`

### `plugins/sulis/skills/backfill-gates/SKILL.md`

- L6: `/sulis-security:codebase-assess; parses findings; registers`
- L41: `1. Invoke `/sulis-security:codebase-assess` — a whole-codebase scan`
- L98: `/sulis-security:codebase-assess <project> <repo> [<deployed-url>]`
- L270: `(`/sulis-security:codebase-assess`, parsing free-form markdown,`
- L299: `- `plugins/sulis-security/skills/codebase-assess/SKILL.md` — the`

### `plugins/sulis/skills/backfill-gates/recipes/post-rollout.md`

- L43: `1. Invoke `/sulis-security:codebase-assess``

### `plugins/sulis/skills/check-build/SKILL.md`

- L14: `standard_reference: "plugins/sulis-security/skills/codebase-assess/references/primitives.md INF-01 + INF-02"`

### `plugins/sulis/skills/check-maintainability/SKILL.md`

- L14: `standard_reference: "plugins/sulis-security/skills/codebase-assess/references/primitives.md CQ-05"`

### `plugins/sulis/skills/check-polish/SKILL.md`

- L14: `standard_reference: "plugins/sulis-security/skills/codebase-assess/references/primitives.md CQ-04"`
- L28: `skill: plugins/sulis-security/skills/codebase-assess`

### `plugins/sulis/skills/check-readability/SKILL.md`

- L14: `standard_reference: "plugins/sulis-security/skills/codebase-assess/references/primitives.md CQ-01 + CQ-03"`

### `plugins/sulis/skills/check-reliability/SKILL.md`

- L14: `standard_reference: "plugins/sulis-security/skills/codebase-assess/references/primitives.md INF-04 + DAT-05"`

### `plugins/sulis/skills/check-security/SKILL.md`

- L14: `standard_reference: "plugins/sulis-security/skills/codebase-assess/references/primitives.md SEC/DAT/SC categories"`
- L54: `skill: plugins/sulis-security/skills/codebase-assess`

### `plugins/sulis/skills/check-security/iterations/1/VERIFICATION_REPORT.md`

- L26: `**BI counter-search performed:** yes — checked that `plugins/sulis-security/skills/codebase-assess/references/primitives…`
- L175: `| `plugins/sulis-security/skills/codebase-assess` | `plugins/sulis-security/skills/codebase-assess/` | YES | exists; sup…`
- L255: `- **Workaround for users in the meantime:** founders can run `/sulis-security:codebase-assess --project NAME --repo OWNE…`

### `plugins/sulis/skills/check-tests/SKILL.md`

- L14: `standard_reference: "plugins/sulis-security/skills/codebase-assess/references/primitives.md CQ-02"`

### `plugins/sulis/skills/code-health/tests/cross_validation/README.md`

- L13: `2. Run `/sulis-security:codebase-assess acme NAME` → captures`

### `plugins/sulis/skills/code-health/tests/cross_validation/compare.py`

- L62: `plugins/sulis-security/skills/codebase-assess/SKILL.md §"Output format".`

### `plugins/sulis/skills/code-review/SKILL.md`

- L297: `Invoke `/sulis-security:codebase-assess` in "Quick" mode — Cycle 1 + Cycle 2`
- L299: `primitives at `plugins/sulis-security/skills/codebase-assess/references/primitives.md`,`
- L827: `- **With `/sulis-security:codebase-assess`** — invoked in Quick mode internally`
- L899: `- `plugins/sulis-security/skills/codebase-assess/SKILL.md` — the security lens this skill invokes`

### `plugins/sulis/skills/consolidate-into-sulis/runs/sea-2026-05-25/external-refs.md`

- L11: `- L10: `> `/sea:verify`, `/sulis-security:codebase-assess`, `/sea:code-review`.``
- L202: `### `plugins/sulis-security/README.md``
- L206: `### `plugins/sulis-security/agents/security-reviewer.md``
- L211: `### `plugins/sulis-security/skills/codebase-assess/SKILL.md``
- L219: `- L209: `out of scope. Refer them to `/sea:codebase-audit` or `/sulis-security:codebase-assess`.``

### `plugins/sulis/skills/consolidate-into-sulis/runs/srd-2026-05-25/external-refs-post-commit3.md`

- L158: `### `plugins/sulis-security/CHANGELOG.md``
- L162: `### `plugins/sulis-security/agents/security-reviewer.md``

### `plugins/sulis/skills/consolidate-into-sulis/runs/srd-2026-05-25/external-refs.md`

- L158: `### `plugins/sulis-security/CHANGELOG.md``
- L162: `### `plugins/sulis-security/agents/security-reviewer.md``

### `plugins/sulis/skills/handoff/SKILL.md`

- L22: ``/sulis-security:codebase-assess`).`

### `plugins/sulis/skills/run-all/SKILL.md`

- L553: `documented at plugins/sulis-security/agents/`
- L764: `documented at plugins/sulis-security/agents/`

### `plugins/sulis/skills/run-wp/SKILL.md`

- L289: `verdict JSON per plugins/sulis-security/agents/security-reviewer.md.`

## 2. Subagent_type dispatch references

None.

## 3. Sweep checklist (apply during Commits 2–4)

For each line above:
- Replace `plugins/{source}/` with `plugins/sulis/`
- Apply any skill / agent / reference renames from CONSOLIDATION_PLAN.md
- For subagent_type references: update to the new agent location after Commit 3 lands

After Commit 4:
```bash
git grep "plugins/sulis-security/" .
# Expected: zero hits outside the source plugin's own DEPRECATED shell
```

## Summary

- Path references: **67** across **38** files
- Subagent_type references: **0** across **0** files

