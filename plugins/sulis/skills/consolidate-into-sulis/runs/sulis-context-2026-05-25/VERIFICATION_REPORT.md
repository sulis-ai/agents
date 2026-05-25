<!-- Template syntax: manual substitution of {{variable}} blocks. No templating engine required. -->

# VERIFICATION_REPORT.md — consolidate-into-sulis run: sulis-context → sulis

**Skill:** `plugins/sulis/skills/consolidate-into-sulis` v0.1.0
**Run:** `runs/sulis-context-2026-05-25/`
**Operator:** Iain + Sulis agent (this session)
**Produced:** 2026-05-25
**Methodology:** `sulis:consolidate-into-sulis` v0.1.0 (first real run)

---

## Run Summary

**Source plugin:** `plugins/sulis-context/`
**Target plugin:** `plugins/sulis/`
**Commit chain:** `0e5c9ea` → `584d438` → `2348bc5` → `c4f6358` → wrap-up (this commit)
**Sulis version bump:** v0.34.0 → v0.35.0
**Source plugin version bump:** v0.3.1 → v0.4.0 [DEPRECATED]
**Marketplace metadata version bump:** v1.77.0 → v1.78.0
**Files moved:** 7 (3 skills, 1 agent, 3 references)
**Tin-test renames applied:** 3 (`discover`, `refresh`, `show` → `*-context`)
**External refs updated:** 17 across 9 files (path + slash-command refs)
**Verdict:** PASS (Gate 6 confirmed — 1 false-attribution finding documented, net NEW = 0)

---

## Gate 0 — Inventory + Plan + Baseline

- Inventory JSON: `inventory.json` — 7 items catalogued (3 skills, 1 agent, 3 references)
- Collisions Markdown: `collisions.md` — 0 direct collisions, 3 tin-test failures (`discover`/`refresh`/`show`)
- External refs Markdown: `external-refs.md` — 6 path refs initially; **slash-command refs missed by script** (catch: see Gate 5 recipe-improvement signals below)
- Code-health baseline: `code-health-baseline.json` — 70 pre-existing findings, tier-2 hard-stop on critical security finding
- CONSOLIDATION_PLAN.md: complete, no TBDs

**Pass:** yes — all sub-step pass criteria met. Baseline captured cleanly after stripping a stderr line (orchestrator emits `code-health: tiers_walked=…` to stderr; `2>&1` redirect mixed it with JSON; documented as a recipe note).

---

## Commit 1 — Scripts + tests + CI

**Skipped — sulis-context had no scripts, tests, or CI workflows.**

The recipe accommodates this implicitly (find returns empty so Commit 1 has nothing to move). Consolidation effectively started at Commit 2.

---

## Commit 2 — Skills (with tin-test rename pass)

- **SHA:** `0e5c9ea` (rename) + `584d438` (continuation: description rewrites + slash-command sweep)
- **Skills moved:** 3
- **Renames applied:**

  | Old | New | Description rewritten? |
  |---|---|---|
  | `discover` | `discover-context` | Yes — founder-friendly framing |
  | `refresh` | `refresh-context` | Yes |
  | `show` | `show-context` | Yes |

- **Operator-only carve-outs:** none (all 3 are founder-invoked via slash commands)
- **`/sulis-context:` references in moved skills:** 0 remaining (verified by post-commit grep)
- **Re-run of `detect_collisions.py` after Commit 2:** 0 tin-test failures on migrated tree

**Pass:** yes — but **commit split observed**. The original intent was one commit; `git mv` staged the rename but my Edit calls happened post-staging, so the content changes landed as a follow-up commit (`584d438`). Recipe-improvement signal recorded below.

---

## Commit 3 — Agents

- **SHA:** `2348bc5`
- **Agents moved:** 1 (`context-cartographer`)
- **`related_skills:` reference updated in Sulis agent:** 1 hit at `plugins/sulis/agents/sulis.md:95` — `../../sulis-context/agents/context-cartographer` → `../agents/context-cartographer`
- **Subagent_type references updated:** 0 (no dispatch sites — agent invoked only via slash-command surface)
- **Slash-command references inside the moved agent body:** 4 hits in `context-cartographer.md` (table rows + body) — swept to `/sulis:*-context`
- **Manual smoke test:** N/A — no `subagent_type` dispatch sites exist; the agent is reachable via the renamed slash commands

**Pass:** yes — single commit this time (edits staged before commit per the Commit 2 lesson)

---

## Commit 4 — References + external ref sweep

- **SHA:** `c4f6358`
- **References moved:** 3 (`classification-taxonomy.md`, `context-index-template.md`, `discovery-protocol.md`)
- **References renamed on collision:** 0 (no name collisions in target)
- **External ref sweep categories addressed:**

  | Category | Hits | Where |
  |---|---|---|
  | Skill `description:` fields | 0 (handled in Commit 2) | — |
  | Agent body cross-references | 1 path + 3 slash-command | `plugins/sulis/agents/sulis.md` |
  | Reference docs citing other reference docs | 4 slash-command | The 3 moved reference docs themselves (self-referential) |
  | SKILL.md `related_skills:` blocks | 0 | — |
  | CLAUDE.md (root + per-plugin) | 0 | — |
  | README.md | 1 slash-command (L89) | `README.md` (root) — path link L52 deferred to Commit 5 [DEPRECATED] treatment |
  | CHANGELOG.md historical narration | (left alone — 4 hits) | — |
  | Cache path patterns in scripts | 0 | — |
  | Workflow YAML | 0 | — |
  | Settings JSON | 0 | — |
  | Template files | 0 | — |
  | Test fixtures | 0 | — |
  | Plus: `.architecture/sulis-checkup/TDD.md` (4 slash-command hits) — not in 12-category list; recipe-improvement signal | — | — |
  | Plus: `plugins/sea/agents/*.md`, `plugins/sea/skills/*/SKILL.md`, `plugins/srd/agents/*.md` (4 slash-command hits) | — | — |
  | Plus: `plugins/sulis/references/journey-model.md`, `plugins/sulis/references/subagent-dispatch.md` (4 slash-command hits) | — | — |

- **`git grep "plugins/sulis-context/" .` after Commit 4:** clean (only historical hits in CHANGELOG / VERIFICATION_REPORT files; per recipe these are left alone)
- **`git grep "/sulis-context:" .` after Commit 4:** clean (only historical hits + recipe's own pedagogical example in SKILL.md L233)

**Pass:** yes

---

## Commit 5 — Wrap-up

- **SHA:** (this commit, post-VERIFICATION_REPORT)
- **Source plugin DEPRECATED markers set in:** plugin.json (description + `deprecated: true`), CHANGELOG.md (v0.4.0 entry), README.md (full rewrite with pointer + historical preservation)
- **No CLAUDE.md in sulis-context** — N/A
- **Sulis plugin.json version:** v0.34.0 → v0.35.0
- **Sulis CHANGELOG.md entry:** present (v0.35.0 — describes the consolidation in full)
- **marketplace.json updated:**
  - sulis entry: v0.34.0 → v0.35.0
  - sulis-context entry: v0.3.1 → v0.4.0, description marked [DEPRECATED]
  - metadata version: v1.77.0 → v1.78.0 + new narrative
- **Checkup allowlists updated:** none affected
- **Run artifacts staged:** all of `runs/sulis-context-2026-05-25/`

**Pass:** yes

---

## Gate 6 — Code-health verification

**Verdict: PASS (with one documented false attribution).**

Captured at:
- `code-health-final.json` (7,777 bytes — same shape as baseline)
- `code-health-comparison.md` (compare_baseline.py output)

### Counts

| Category | Count |
|---|---|
| NEW (consolidation-attributed by signature) | 1 |
| PRE-EXISTING (carried over) | 8 |
| RESOLVED (gone vs baseline) | 1 |

### The "NEW" finding — false attribution

`plugins/sulis/.claude-plugin/plugin.json` PH-103 (manifest-hygiene; description over 500 chars). The finding appears as **NEW** in compare_baseline.py's report and the **same logical finding** appears as **RESOLVED**. Both are the same PH-103 rule on the same file at line 0; the only difference is the `message` field:

- Baseline: `"description is 710 chars (...)"`
- Final: `"description is 864 chars (...)"`

The signature function in `compare_baseline.py` looks for `rule` / `rule_id` / `check` fields but the code-health JSON uses `identifier` (with `extras.rule` as a secondary location). So the signature falls through to the hash-of-stable-JSON path, which hashes the `message` field's "710" vs "864" content → different signatures → false NEW + false RESOLVED for one finding.

**Per `references/code-health-gating.md`'s rubric, this is "pre-existing in disguise" — false attribution, do not gate on it.** The consolidation legitimately made the description longer (added mention of context cartographer surface); PH-103 was already present in baseline; it's still present in final; counted exactly once in reality.

### Net regression: 0

After classifying the one false attribution: NEW = 0. **Gate 6 PASSES.**

### Sixth recipe-improvement signal for v0.1.1

Add `identifier` (and `extras.rule`) to compare_baseline.py's signature-priority chain:

```python
rule = (
    finding.get("rule")
    or finding.get("rule_id")
    or finding.get("check")
    or finding.get("identifier")
    or (finding.get("extras") or {}).get("rule")
    or ""
)
```

Without this fix, every consolidation that changes a manifest description (which Commit 5 always does) will surface a false-attribution PH-103. Six runs ahead (sulis-security, sea, srd, plus future), this would compound.

---

## Adversarial Review

### Misuse case 1: External ref left behind

- **What might have gone wrong:** A reference cited from another file in the marketplace was missed during the sweep.
- **Mitigation applied:** `find_external_refs.py` for path refs + manual `git grep` for slash-command refs (helper script gap surfaced — see below).
- **Status:** PREVENTED — final `git grep` after Commit 4 showed zero non-historical hits.

### Misuse case 2: Subagent_type silent break

- **What might have gone wrong:** Renaming the context-cartographer agent without sweeping every `subagent_type` dispatch site would break dispatch.
- **Mitigation applied:** `find_external_refs.py` enumerated 0 `subagent_type` sites for context-cartographer; verified independently via direct `git grep -E "subagent_type.*context-cartographer"`.
- **Status:** PREVENTED — no dispatch sites existed; the agent is reachable only via the renamed slash commands.

### Misuse case 3: Tin-test rename without description rewrite

- **What might have gone wrong:** Skills renamed but `description:` fields still cite old vocabulary.
- **Mitigation applied:** Commit 2 included description rewrites for all 3 renamed skills; founder-friendly framing applied per `references/conflict-resolution.md` rubric.
- **Status:** PREVENTED.

### Misuse case 4: Atomic commits violated

- **What might have gone wrong:** Bundling moves and edits into mega-commits.
- **Mitigation applied:** Recipe + operator discipline. **Mild divergence in Commit 2** — the `git mv` and content edits landed as two consecutive commits because edits ran after staging. CLAUDE.md rule "prefer new commits over amend" was honored. Recipe-improvement signal recorded.
- **Status:** PARTIALLY PREVENTED — atomic-per-step principle held, but the per-step commit count drifted from 1 to 2 in Commit 2.

### Misuse case 5: Slash-command sweep missed

- **What might have gone wrong:** Slash-command references (`/sulis-context:*`) not surfaced by `find_external_refs.py`; could ship the consolidation with broken founder-visible command references.
- **Mitigation applied:** Manual `git grep -nE "/sulis-context:"` after Commit 3 surfaced 17 hits across 9 files; all fixed in Commit 4 + continuation.
- **Status:** OPEN_RISK — for this run mitigation was manual; future runs need the script gap fixed.
- **revisit_by:** event — script gap addressed in `consolidate-into-sulis` v0.1.1 before the next consolidation (sulis-security → sulis)
- **Workaround in the meantime:** operator runs `git grep -nE "/{source}:"` manually as a Gate 0 supplement.

---

## Patterns to feed back into the recipe (v0.1.1)

1. **`find_external_refs.py` slash-command pattern.** Currently scans `plugins/{source}/` (absolute) + `(../)+{source}/` (relative). Add `/{source}:` slash-command pattern to catch founder-visible command references. Without this, ~75% of the external refs in the sulis-context consolidation were not surfaced by the script.

2. **SKILL.md gotcha about staging edits before commit.** Add to the Gotchas section: *"`git mv` stages renames but not subsequent edits. After the edit pass, run `git add -A` before `git commit`; otherwise edits land as a follow-up commit, slightly violating atomic-per-step."*

3. **Code-health baseline capture: separate stderr from stdout.** Recipe sub-step 0d uses `> code-health-baseline.json`; using `2>&1` (as my background invocation did) mixes the orchestrator's stderr progress line with the JSON. Update sub-step 0d to use `2>/dev/null > file` or `> file 2>baseline.stderr` to keep streams separate.

4. **External-ref-sweep.md should mention `.architecture/` paths.** The 12-category checklist includes "CLAUDE.md / README.md / CHANGELOG.md" but doesn't explicitly mention `.architecture/` directories (where TDDs live). The sulis-checkup TDD had 4 slash-command refs that needed updating. Add `.architecture/**/*.md` as a category or sub-category.

5. **Commit 1 no-op handling.** When the source plugin has no scripts/tests/CI, the recipe should explicitly say "skip Commit 1; resume at Commit 2." Implicit handling worked but isn't documented.

All five fixes land in `consolidate-into-sulis` v0.1.1 before the next consolidation (sulis-security → sulis).

---

## Open risks accepted at publication

### Risk 1: Slash-command pattern in find_external_refs.py

- See Misuse case 5 above. OPEN_RISK with revisit-trigger: fix in v0.1.1 before next consolidation.

### Risk 2: Code-health regression attribution

- The baseline is tier-2 hard-stopped, meaning tiers 3-7 are skipped. The Gate 6 final run is expected to be similarly hard-stopped (the consolidation doesn't touch security primitives). If for any reason the final run progresses further than the baseline, the "extra" tiers' findings would falsely attribute as NEW.
- **Mitigation:** comparison report flags this if observed.
- **Status:** ACCEPTED — first run, low likelihood of attribution issue.

---

## Verdict (final)

**Commits 1-5:** PASS
**Gate 6:** PASS (1 false-attribution finding documented; net NEW = 0 after the rubric in `references/code-health-gating.md` is applied)

**Overall consolidation:** PASS — sulis-context successfully folded into sulis. 7 files moved, 17 external refs updated (paths + slash-commands), source plugin marked DEPRECATED, sulis bumped to v0.35.0, marketplace bumped to v1.78.0.

---

## Meta-Notes

- First real exercise of `consolidate-into-sulis` v0.1.0 — methodology held up with 5 recipe-improvement signals captured for v0.1.1
- Smallest of the four Phase 3 plugins — the easy practice run produced 5 v0.1.1 signals which is exactly the kind of calibration the change-as-primitive plan expected
- Next: sulis-security → sulis (also small; the only skill is already [DEPRECATED] so the rename pass is trivial)
- The slash-command pattern gap in `find_external_refs.py` is the single highest-leverage v0.1.1 patch — for the next 3 consolidations (sea, srd in particular), slash-command refs are much more numerous than path refs

---

## Recipe-improvement signals — full list for v0.1.1 (6 total)

1. **`find_external_refs.py` slash-command pattern** — add `/{source}:` scan alongside path patterns (caught 75% of refs manually)
2. **SKILL.md gotcha: stage edits before commit** — `git mv` + Edit-after-mv split into two commits
3. **Sub-step 0d: separate stderr from stdout** — orchestrator stderr line polluted JSON
4. **`external-ref-sweep.md`: add `.architecture/**/*.md` category** — 4 hits in sulis-checkup TDD not in 12-category checklist
5. **SKILL.md: document Commit 1 no-op handling** — when source plugin has no scripts/tests/CI
6. **`compare_baseline.py` signature function: prefer `identifier` field** — Gate 6 false attribution on manifest description length change

All six land in `consolidate-into-sulis` v0.1.1 before the next consolidation (sulis-security → sulis).
