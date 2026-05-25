<!-- Template syntax: manual substitution of {{variable}} blocks. No templating engine required. -->

# CONSOLIDATION_PLAN.md — sulis-context → sulis

**Run directory:** `plugins/sulis/skills/consolidate-into-sulis/runs/sulis-context-2026-05-25/`
**Source plugin:** `plugins/sulis-context/`
**Target plugin:** `plugins/sulis/`
**Started:** 2026-05-25
**Operator:** Iain + Sulis agent (this session)
**Branch:** main (matching the sulis-execution → sulis precedent's branching pattern)

---

## 1. Inventory summary

(From `inventory.json`)

| Category | Count | Items |
|---|---|---|
| Skills | 3 | `discover`, `refresh`, `show` |
| Agents | 1 | `context-cartographer.md` |
| References | 3 | `classification-taxonomy.md`, `context-index-template.md`, `discovery-protocol.md` |
| Scripts | 0 | (none) |
| Script tests | 0 | (none) |
| Docs | 0 | (none) |
| CI workflows | 0 | (none — no `.github/workflows/sulis-context*.yml`) |
| Manifest files | 1 | `.claude-plugin/plugin.json` |
| Metadata files | 2 | `README.md`, `CHANGELOG.md` (no CLAUDE.md, no settings.json) |

This is the smallest of the four Phase 3 consolidations — perfect practice run.

---

## 2. Direct collisions

(From `collisions.md`)

**None.** No incoming skill, agent, reference, or script collides with an existing name in sulis.

---

## 3. Tin-test failures + rename mappings

(From `collisions.md` tin-test section + `references/conflict-resolution.md` worked rename table)

| Old name | Tin-test failure | New name | Description rewrite needed? |
|---|---|---|---|
| `discover` | bare verb | `discover-context` | Yes — description likely says "discover existing architecture" → "discover the context of an existing codebase" |
| `refresh` | bare verb | `refresh-context` | Yes — description likely says "Re-validate an existing `.context/{project}/INDEX.md`" → "Re-validate the context index for an existing codebase" |
| `show` | bare verb | `show-context` | Yes — description likely says "Read-only display of the current `.context/{project}/INDEX.md`" → "Show the captured context for the current project" |

**Operator-only carve-outs:** none (all three skills are founder-invoked via `/sulis-context:<verb>` — they appear in autocomplete and journey docs).

Agent: `context-cartographer` — already self-describing (role + domain). **No rename.**

References: keep filenames as-is when moving into `plugins/sulis/references/`:
- `classification-taxonomy.md`
- `context-index-template.md`
- `discovery-protocol.md`

None collide with existing sulis references.

---

## 4. External ref sweep checklist

(From `external-refs.md` — 6 path references across 6 files)

Per `references/external-ref-sweep.md` category 7, CHANGELOG.md historical narration is **left alone** (rewriting historical paths is revisionist). Same principle applies to past VERIFICATION_REPORT.md files — they were correct at the time of authoring.

Classifying each ref:

| File | Line | Type | Action |
|---|---|---|---|
| `README.md` | L52 | Active link in marketplace plugin listing | **EDIT** — update entry to reflect sulis-context as [DEPRECATED]; consider whether to remove listing entirely or keep as historical |
| `plugins/sulis/CHANGELOG.md` | L2094 | Historical narration ("plugins/sulis-context/CHANGELOG.md (35 lines — reconstructed from…") | **LEAVE ALONE** — historical narration |
| `plugins/sulis/agents/sulis.VERIFICATION_REPORT.md` | L159 | Historical verification record (Codebase Referential Integrity scoring) | **LEAVE ALONE** — was correct at the time |
| `plugins/sulis/agents/sulis.md` | L95 | Active `related_skills:` declaration with relative path `../../sulis-context/agents/context-cartographer` | **EDIT** — update to point at new location after Commit 3 |
| `plugins/sulis/skills/add-agent/VERIFICATION_REPORT.md` | L167 | Historical verification record | **LEAVE ALONE** |
| `plugins/sulis/skills/consolidate-into-sulis/VERIFICATION_REPORT.md` | L115 | Historical narration of the bug fix | **LEAVE ALONE** |

**Active edits required: 2** (README.md L52 + sulis.md L95).
**Historical narrations left alone: 4.**

Categories present in this consolidation (tick when complete):

- [ ] 1. Skill `description:` fields (3 hits — within the 3 moved skills themselves; updated as part of Commit 2 edit pass)
- [ ] 2. Agent body cross-references (1 hit — sulis.md L95)
- [ ] 3. Reference docs citing other reference docs (0 hits)
- [ ] 4. SKILL.md `related_skills:` blocks (covered by category 1 above)
- [ ] 5. CLAUDE.md (root + per-plugin) (0 hits)
- [ ] 6. README.md (1 hit — L52)
- [x] 7. CHANGELOG.md historical narration — LEAVE ALONE (3 hits, all historical)
- [ ] 8. Cache path patterns in scripts (0 hits — no scripts in sulis-context)
- [ ] 9. Workflow YAML (0 hits — no CI workflows)
- [ ] 10. Settings JSON (0 hits)
- [ ] 11. Template files (0 hits)
- [ ] 12. Test fixtures (0 hits)

Subagent_type sweep for `context-cartographer`: **0 hits** (the agent is invoked via slash-command surface `/sulis-context:discover`, not via `subagent_type` dispatch).

---

## 5. Code-health baseline

Captured at: `code-health-baseline.json`
Mode: `fast` (subprocess-only, deterministic; suitable for regression comparison)
Scope: codebase

| Tier | Status | Findings | Notes |
|---|---|---|---|
| Tier 1 — Exists | needs_attention | 5 | Manifest-hygiene PH-103 issues (description length over recommended 500 chars) |
| Tier 2 — Safe | **failed** | 4 | Hard-stop trigger — critical finding(s) gate further tiers |
| Tier 3 — Works | skipped_by_gating | 0 | Not reached |
| Tier 4 — Survives | skipped_by_gating | 2 | Not reached |
| Tier 5 — Understandable | skipped_by_gating | 59 | Not reached (mostly readability findings) |
| Tier 6 — Evolves | skipped_by_gating | 0 | Not reached |
| Tier 7 — Polished | skipped_by_gating | 0 | Not reached |

**Pre-existing total: 70 findings** (tier 1: 5; tier 2: 4; tier 4: 2; tier 5: 59 — others skipped by tier-2 hard-stop).

**Gating reason:** hard-stop at tier 2 (Safe) due to critical security finding.

### Implication for Gate 6 comparison

The baseline is hard-stopped at tier 2, so tiers 3-7 are skipped. As long as Gate 6's final run is also hard-stopped at tier 2 (expected — the consolidation moves files, doesn't touch security), the comparison is apples-to-apples for tiers 1+2 and the tier 3-7 skip state is identical.

**Edge case to watch:** if the consolidation accidentally resolves the tier-2 critical finding (extremely unlikely — none of the moves touch security primitives), tiers 3-7 would suddenly emit findings that weren't in the baseline. `compare_baseline.py` would attribute these as NEW, which would be false attribution. If observed, document in VERIFICATION_REPORT.md and treat as "pre-existing in disguise."

---

## 6. Per-commit checklist

### Commit 1 — Scripts + tests + CI

**Skipped — no scripts, tests, or CI workflows in sulis-context.**

(Commit numbering preserved for consistency with the recipe; this consolidation effectively starts at Commit 2.)

### Commit 2 — Skills (with tin-test rename pass)

- [ ] `git mv plugins/sulis-context/skills/discover plugins/sulis/skills/discover-context`
- [ ] `git mv plugins/sulis-context/skills/refresh plugins/sulis/skills/refresh-context`
- [ ] `git mv plugins/sulis-context/skills/show plugins/sulis/skills/show-context`
- [ ] For each renamed skill: rewrite SKILL.md `description:` to reflect new name + founder-friendly framing
- [ ] For each renamed skill: update `related_skills:` paths (now under sulis)
- [ ] For each renamed skill: update internal cross-skill references (`/sulis-context:<verb>` → `/sulis:<verb>-context`)
- [ ] Verify `find plugins/sulis-context/skills -mindepth 1 -type d` returns empty
- [ ] Re-run `detect_collisions.py` against migrated tree → 0 tin-test failures remain
- [ ] Commit: `chore(sulis): step 2/5 — move 3 sulis-context skills into sulis (with 3 tin-test renames: discover/refresh/show → *-context)`

### Commit 3 — Agents

- [ ] `git mv plugins/sulis-context/agents/context-cartographer.md plugins/sulis/agents/context-cartographer.md`
- [ ] Sweep subagent_type references: 0 hits (no edits needed)
- [ ] Sweep `related_skills:` references: 1 hit (`plugins/sulis/agents/sulis.md:95` — `../../sulis-context/agents/context-cartographer` → `../context-cartographer`)
- [ ] Verify `find plugins/sulis-context/agents -name "*.md"` returns empty
- [ ] Manual smoke test: dispatch `context-cartographer` once from a Claude session (or document that no dispatch sites exist outside the slash-command surface)
- [ ] Commit: `chore(sulis): step 3/5 — move sulis-context agent (context-cartographer) into sulis`

### Commit 4 — References + external ref sweep

- [ ] `git mv plugins/sulis-context/references/classification-taxonomy.md plugins/sulis/references/classification-taxonomy.md`
- [ ] `git mv plugins/sulis-context/references/context-index-template.md plugins/sulis/references/context-index-template.md`
- [ ] `git mv plugins/sulis-context/references/discovery-protocol.md plugins/sulis/references/discovery-protocol.md`
- [ ] Apply external ref sweep — 2 active edits (README.md L52 + sulis.md L95 already covered by Commit 3 agent move)
- [ ] Verify `git grep "plugins/sulis-context/" .` returns only the 3 historical-narration hits (CHANGELOG L2094, sulis.VERIFICATION_REPORT.md L159, add-agent VERIFICATION_REPORT.md L167, consolidate-into-sulis VERIFICATION_REPORT.md L115)
- [ ] Commit: `chore(sulis): step 4/5 — move sulis-context references into sulis + external ref sweep`

### Commit 5 — Wrap-up

- [ ] `docs/` — none to move
- [ ] Mark `plugins/sulis-context/.claude-plugin/plugin.json` as DEPRECATED (description prefix `[DEPRECATED]`, add `deprecated: true` if Claude Code respects it; otherwise just the prefix)
- [ ] Add final `[DEPRECATED]` entry to `plugins/sulis-context/CHANGELOG.md` referencing the consolidation commit chain
- [ ] Replace `plugins/sulis-context/README.md` body with deprecation notice + pointer to `plugins/sulis/`
- [ ] No CLAUDE.md in sulis-context to update
- [ ] Bump `plugins/sulis/.claude-plugin/plugin.json` version → v0.35.0
- [ ] Add `plugins/sulis/CHANGELOG.md` entry describing the consolidation (v0.35.0)
- [ ] Bump `.claude-plugin/marketplace.json`: sulis → v0.35.0; marketplace metadata → v1.78.0
- [ ] Update marketplace.json sulis-context entry to reflect [DEPRECATED] status
- [ ] No checkup allowlists to update (sulis-context has none)
- [ ] Commit: `feat(sulis): v0.35.0 — sulis-context consolidated into sulis (step 5/5 — wrap-up)`

### Gate 6 — Code-health verification

- [ ] Re-run `python3 plugins/sulis/skills/code-health/scripts/orchestrator.py --mode fast --raw --scope codebase --repo-root . > code-health-final.json`
- [ ] Run `python3 plugins/sulis/skills/consolidate-into-sulis/scripts/compare_baseline.py --baseline runs/sulis-context-2026-05-25/code-health-baseline.json --final runs/sulis-context-2026-05-25/code-health-final.json > runs/sulis-context-2026-05-25/code-health-comparison.md`
- [ ] NEW findings = 0, OR fix-forward Commit 6 → re-run Gate 6
- [ ] Update `runs/sulis-context-2026-05-25/VERIFICATION_REPORT.md` with Gate 6 verdict

---

## 7. Notes + open questions

- **No scripts/tests/CI** — Commit 1 is effectively a no-op; the consolidation starts at Commit 2. SKILL.md recipe accommodates this implicitly (find returns empty so Commit 1 has nothing to move).
- **All 3 incoming skills hit the tin test** — this is unusually high concentration for a small plugin; confirms the rename pass is needed and the tin-test rubric is correctly tuned.
- **Description rewrites for renamed skills** will be the most time-consuming part of Commit 2 — three SKILL.md `description:` fields to rewrite for founder-friendly framing.
- **Slash-command surface change** — after consolidation, `/sulis-context:discover` becomes `/sulis:discover-context`. Founder-visible. README.md update should mention this explicitly so any operator linking to the old command knows where it went.
- **Marketplace.json sulis-context entry** — keep listed but mark [DEPRECATED] per the precedent (the sulis-execution shell stayed listed after consolidation; sulis-context follows the same pattern; sulis-concierge was deleted only because it had no remaining purpose).
