<!-- Template syntax: manual substitution of {{variable}} blocks. No templating engine required. -->

# CONSOLIDATION_PLAN.md — srd → sulis

**Run directory:** `plugins/sulis/skills/consolidate-into-sulis/runs/srd-2026-05-25/`
**Source plugin:** `plugins/srd/`
**Target plugin:** `plugins/sulis/`
**Started:** 2026-05-25
**Operator:** Iain + Sulis agent (this session)
**Branch:** main
**Methodology:** `consolidate-into-sulis` v0.1.1 (post-sulis-context patches)

---

## 1. Inventory summary

| Category | Count | Items |
|---|---|---|
| Skills | 6 | `codebase-mapping`, `critical-thinking`, `requirements-validation`, `spec-index`, `srd-templates`, `tree-synthesis` |
| Agents | 1 | `requirements-analyst.md` |
| References | 13 | `audience-adapted-framing-standard.md`, `change-work-standard.md`, `coaching-without-conflict.md`, `cognitive-load.md`, `content-quality.md`, `convention-preference-standard.md`, `engineering-principles.md`, `executor-loop-standard.md`, `founder-english.md`, `git-workflow-standard.md`, `pr-hygiene-standard.md`, `repository-contract-standard.md`, `security-standard.md` |
| Docs | 25 | `docs/specifications/INDEX.md` + per-project SRD sets under `docs/specifications/{name}/` (4 example projects) |
| Scripts / tests / CI | 0 | (none) |
| Manifest files | 1 | `.claude-plugin/plugin.json` |
| Metadata files | 3 | `README.md`, `CHANGELOG.md`, `settings.json` |

**Scope** is ~5× sulis-context (151 vs 6 external refs).

---

## 2. Direct collisions

**Skills:** None.
**Agents:** None.
**References:** None by filename. **Content-level overlap** with `plugins/sulis/references/standards/COACHING_STANDARD.md` (sulis-local port of srd's `coaching-without-conflict.md`). Both keep their distinct filenames; the COACHING_STANDARD.md is the canonical sulis-local version going forward.

---

## 3. Tin-test failures + rename mappings

Script caught 1 (acronym). Operator judgment adds 2 (abstract methodology nouns):

| Old name | Tin-test failure | New name | Caught by | Description rewrite? |
|---|---|---|---|---|
| `srd-templates` | contains `srd` acronym | `requirements-templates` | script | Yes |
| `tree-synthesis` | abstract methodology noun | `map-architecture` | judgment | Yes |
| `spec-index` | abbreviation + abstract | `index-specifications` | judgment | Yes |

**Operator-only carve-outs** (skills that stay as-is):

| Name | Justification |
|---|---|
| `critical-thinking` | Methodology utility; not founder-invoked. Operator-only. |
| `codebase-mapping` | Already verb-noun shape; describes what it does. |
| `requirements-validation` | Already verb-noun shape; clear meaning. |

Agent: `requirements-analyst` — already role + domain; no rename.

---

## 4. External ref sweep checklist (151 hits across 59 files)

Categories present (counts from automated scan):

| Category | Hits | Files | Notes |
|---|---|---|---|
| other-plugin agent bodies | 43 | 7 | idc, sea, sulis-design, sulis-product-development, sulis-security, sulis-strategy, sulis-builder |
| sulis plugin (skills / refs / docs) | 35 | 25 | Internal sulis-to-srd refs (heavy after the v0.30.0+ consolidation history) |
| Sulis agent body + adjacent | 27 | 5 | `plugins/sulis/agents/sulis.md` (17 hits is the single largest file) + add-skill/add-agent VERIFICATION_REPORTs (historical — leave alone) |
| other | 14 | 6 | Settings, marketplace.json, other root files |
| root CLAUDE.md | 9 | 1 | Top-level project memory cites srd standards heavily |
| historical (CHANGELOGs + VERIFICATION_REPORTs) | 7 | 7 | LEAVE ALONE |
| `.architecture/` TDDs/ADRs | 6 | 3 | Includes `ADR-006-srd-gap.md` |
| other-plugin skill bodies | 5 | 3 | |
| root README.md | 3 | 1 | |
| other-plugin reference docs | 2 | 1 | |

**Active edits:** ~144 refs (excluding 7 historical).

Categories from `references/external-ref-sweep.md` to tick:

- [ ] 1. Skill `description:` fields (handled in Commit 2 for moved skills)
- [ ] 2. Agent body cross-references (43 + 27 hits)
- [ ] 3. Reference docs citing other reference docs (2 hits)
- [ ] 4. SKILL.md `related_skills:` blocks
- [ ] 5. CLAUDE.md (9 hits)
- [ ] 6. README.md (3 hits + the [DEPRECATED] treatment of the plugin listing entry — like sulis-context)
- [x] 7. CHANGELOG.md historical narration — LEAVE ALONE (7 hits, all historical)
- [ ] 8. Cache path patterns in scripts (0 hits — srd has no scripts)
- [ ] 9. Workflow YAML (0 hits — no CI)
- [ ] 10. Settings JSON (likely 0–2 hits in plugin settings.json files)
- [ ] 11. Template files (0 hits — no srd templates outside skills)
- [ ] 12. Test fixtures (0 hits)
- [ ] 13. `.architecture/**/*.md` (6 hits — v0.1.1 category)

Subagent_type sweep: **0 hits** (requirements-analyst is invoked via `claude --agent requirements-analyst` / dispatched by Sulis; not via `subagent_type` syntax).

---

## 5. Code-health baseline

To be populated when sub-step 0d completes (background process running at plan-draft time).

---

## 6. Per-commit checklist

### Commit 1 — Scripts + tests + CI

**Skipped** — srd has no scripts, tests, or CI workflows. Per `SKILL.md` v0.1.1 no-op handling, advance directly to Commit 2.

### Commit 2 — Skills (with tin-test rename pass)

For each skill, `git mv` to new path + apply rename if needed:

- [ ] `git mv plugins/srd/skills/codebase-mapping plugins/sulis/skills/codebase-mapping`
- [ ] `git mv plugins/srd/skills/critical-thinking plugins/sulis/skills/critical-thinking`
- [ ] `git mv plugins/srd/skills/requirements-validation plugins/sulis/skills/requirements-validation`
- [ ] `git mv plugins/srd/skills/spec-index plugins/sulis/skills/index-specifications` (renamed)
- [ ] `git mv plugins/srd/skills/srd-templates plugins/sulis/skills/requirements-templates` (renamed)
- [ ] `git mv plugins/srd/skills/tree-synthesis plugins/sulis/skills/map-architecture` (renamed)
- [ ] Description rewrites for the 3 renamed skills
- [ ] Internal `/srd:*` → `/sulis:*` references swept (inside each moved skill body)
- [ ] `git add -A` (v0.1.1 gotcha: stage edits before commit)
- [ ] Commit: `chore(sulis): step 2/5 — move 6 srd skills into sulis (with 3 tin-test renames)`

### Commit 3 — Agent

- [ ] `git mv plugins/srd/agents/requirements-analyst.md plugins/sulis/agents/requirements-analyst.md`
- [ ] Update `plugins/sulis/agents/sulis.md` `related_skills:` block (line ~92 — path now `../agents/requirements-analyst`)
- [ ] Sweep `/srd:requirements-analyst` references across marketplace if any (slash-command form sometimes used in narrative)
- [ ] Subagent_type sweep: 0 hits (no dispatch sites)
- [ ] Smoke test: `requirements-analyst` reachable via `claude --agent requirements-analyst` post-move
- [ ] Commit: `chore(sulis): step 3/5 — move srd agent (requirements-analyst) into sulis`

### Commit 4 — References + external ref sweep (the big one)

For each reference file:

- [ ] `git mv plugins/srd/references/audience-adapted-framing-standard.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/change-work-standard.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/coaching-without-conflict.md plugins/sulis/references/` (coexists with sulis/standards/COACHING_STANDARD.md as historical platform-source version)
- [ ] `git mv plugins/srd/references/cognitive-load.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/content-quality.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/convention-preference-standard.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/engineering-principles.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/executor-loop-standard.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/founder-english.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/git-workflow-standard.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/pr-hygiene-standard.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/repository-contract-standard.md plugins/sulis/references/`
- [ ] `git mv plugins/srd/references/security-standard.md plugins/sulis/references/`
- [ ] Apply external ref sweep — work through the 144 active edits (43 + 35 + 27 + 14 + 9 + 6 + 5 + 3 + 2 = 144)
- [ ] CLAUDE.md needs 9 updates (`plugins/srd/references/...` → `plugins/sulis/references/...`)
- [ ] `git grep "plugins/srd/" .` after sweep returns only historical hits
- [ ] `git grep "/srd:[a-zA-Z]" .` after sweep returns only historical hits + intentional pedagogical examples
- [ ] `git add -A` (v0.1.1 gotcha)
- [ ] Commit: `chore(sulis): step 4/5 — move 13 srd references into sulis + external ref sweep (151 → 0 active hits)`

### Commit 5 — Wrap-up

- [ ] Move `docs/specifications/` to `plugins/sulis/docs/srd-specifications/` (with prefix per sulis-execution precedent)
- [ ] Mark `plugins/srd/.claude-plugin/plugin.json` DEPRECATED (version bump + description prefix + `deprecated: true`)
- [ ] `plugins/srd/CHANGELOG.md` final [DEPRECATED] entry naming the commit chain
- [ ] Rewrite `plugins/srd/README.md` with deprecation notice + what-moved-where + historical preservation
- [ ] `plugins/srd/settings.json` — review/remove if no longer needed (or leave as-is)
- [ ] Bump `plugins/sulis/.claude-plugin/plugin.json` v0.36.0 → v0.37.0
- [ ] Add `plugins/sulis/CHANGELOG.md` v0.37.0 entry
- [ ] Bump `.claude-plugin/marketplace.json`: sulis v0.36.0 → v0.37.0; srd → [DEPRECATED]; metadata v1.79.0 → v1.80.0
- [ ] Update README.md L53 — `[srd]` plugin entry marked [DEPRECATED]
- [ ] Commit: `feat(sulis): v0.37.0 — srd consolidated into sulis (step 5/5 — wrap-up)`

### Gate 6 — Code-health verification

- [ ] Re-run `/sulis:code-health` (subprocess fast mode) — save as `code-health-final.json`
- [ ] Run `compare_baseline.py` (v0.1.1 — now catches `identifier` field) — save as `code-health-comparison.md`
- [ ] Net NEW findings = 0 (after false-attribution rubric) — verify
- [ ] Update VERIFICATION_REPORT.md with Gate 6 verdict

---

## 7. Notes + open questions

- **No `subagent_type` dispatches for `requirements-analyst`** — the agent is invoked via `claude --agent` or as a recommendation embedded in skills. Commit 3 is structurally simple.
- **CLAUDE.md heavyweight refs** — 9 lines of CLAUDE.md cite srd standards by path. These need careful editing during Commit 4. Per `external-ref-sweep.md` category 5, CLAUDE.md is an active edit target.
- **`docs/specifications/` are example SRDs from prior projects** — they move to `plugins/sulis/docs/srd-specifications/` (with `srd-` prefix per sulis-execution → sulis precedent for nested docs).
- **`coaching-without-conflict.md` vs `COACHING_STANDARD.md`** — both end up in `plugins/sulis/` under different paths (`references/coaching-without-conflict.md` and `references/standards/COACHING_STANDARD.md`). They coexist; the sulis-local version is the canonical going forward.
- **`/srd:requirements-analyst` slash-command form** — used in narrative ("escalate via `/srd:requirements-analyst`") but the agent is dispatched via `claude --agent`, not slash command. Treating these as text patterns to update: `/srd:requirements-analyst` → `requirements-analyst agent` (or `/sulis:requirements-analyst` if we adopt the convention later).
- **Volume** — 151 refs is substantial. Operator vigilance at every Edit pass. Expected time: 30–60 min for Commit 4 alone.
