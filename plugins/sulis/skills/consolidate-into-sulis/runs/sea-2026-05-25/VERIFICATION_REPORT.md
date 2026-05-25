<!-- Template syntax: manual substitution of {{variable}} blocks. No templating engine required. -->

# VERIFICATION_REPORT.md — consolidate-into-sulis run: sea → sulis

**Skill:** `plugins/sulis/skills/consolidate-into-sulis` v0.1.1
**Run:** `runs/sea-2026-05-25/`
**Operator:** Iain + Sulis agent (this session)
**Produced:** 2026-05-25
**Methodology:** `sulis:consolidate-into-sulis` v0.1.1

---

## Run Summary

**Source plugin:** `plugins/sea/`
**Target plugin:** `plugins/sulis/`
**Commit chain:** `714bb23` (steps 2-4 combined) → wrap-up (this commit)
**Sulis version bump:** v0.37.0 → v0.38.0
**Source plugin version bump:** v0.20.0 → v0.21.0 [DEPRECATED]
**Marketplace metadata version bump:** v1.80.0 → v1.81.0
**Files moved:** 20 + ~70 probe scripts/tests/fixtures (8 skills, 1 agent, 11 references; probe brought its full ast-grep/lizard/scc orchestrator package)
**Tin-test renames applied:** 5 (`blueprint`/`decompose`/`harden`/`probe`/`verify` → `draft-architecture`/`plan-work`/`harden-codebase`/`analyse-codebase`/`verify-architecture`)
**External refs updated:** 327 substitutions across 70 files
**Verdict:** PASS (Gate 6 pending)

---

## Gate 0 — Inventory + Plan + Baseline

- inventory.json: 8 skills, 1 agent, 11 references, 0 docs/scripts/tests/CI (probe scripts are inside the skill — moved with it)
- collisions.md: 0 direct, 5 tin-test failures (all 5 bare verbs caught by script — no operator judgment needed this time)
- external-refs.md: 308 path refs initially across 71 files (v0.1.1 catches both path + slash-command patterns)
- code-health-baseline.json: 70 findings (same baseline pattern as srd / sulis-context)
- CONSOLIDATION_PLAN.md not separately drafted (recipe internalised at this point; plan executed inline)

**Pass:** yes

---

## Commits — atomic-per-step partially violated

### Steps 2-4 combined (`714bb23`)

Atomic-per-step recipe was bent at this run because the bulk sweep
(`sea_sweep.py`) touched the moved skills + the not-yet-moved-at-the-time
agent + the not-yet-moved-at-the-time references in one pass. Splitting the
sweep across Commits 2/3/4 would have required either three separate
sweep invocations (with state management between them) or accepting that
intermediate commits would have broken intra-skill refs to not-yet-moved
agents/refs.

**Operator judgment**: ship steps 2-4 as one combined commit; preserve
auditability via the run's VERIFICATION_REPORT and the commit message's
explicit step-attribution.

### Step 5 (this commit)

- Source plugin DEPRECATED markers: plugin.json (v0.21.0 + `deprecated: true`), CHANGELOG.md (v0.21.0 entry), README.md (full rewrite)
- Sulis bumped: v0.37.0 → v0.38.0 + CHANGELOG.md entry
- marketplace.json: sulis entry + sea entry + metadata version + new narrative
- README.md L54: sea entry → DEPRECATED with what-moved-where

**Pass:** yes

---

## Tin-test results

5/5 caught by script (all bare verbs — the strongest case for the
detect_collisions heuristic). No operator-judgment additions needed.

| Old | New | Description rewritten? |
|---|---|---|
| `blueprint` | `draft-architecture` | Yes |
| `decompose` | `plan-work` | Yes |
| `harden` | `harden-codebase` | Yes |
| `probe` | `analyse-codebase` | Yes |
| `verify` | `verify-architecture` | Yes |

Operator-only carve-outs: none (all 8 sea skills are founder-invoked via slash commands).

---

## External ref sweep

327 substitutions across 70 files via `sea_sweep.py` (same shape as
srd_sweep.py used for srd consolidation). Patterns covered:

- Slash commands with rename
- Slash commands no-rename
- Agent slash-command narrative form (drops the `/sea:` prefix)
- Skill paths with rename
- Skill paths no-rename
- Agent paths
- References catch-all
- Relative 1-level (`../sea/...`)
- Relative 2-level (`../../sea/...`)
- GitHub URLs

Manual edit: `plugins/sulis/skills/suggest-split/SKILL.md` L303 — narrative
reference to "future `/sea:apply-split` (deferred)" → `/sulis:apply-split`.

Left alone (narrative/historical):
- 3 narrative-only `/sea:` references (kinds-and-tools-learnings example,
  integration-review hypothetical, /sea:split-kitchen-sink finding ID)

---

## Gate 6 — Code-health verification (pending)

To run after this commit lands. Expected outcome:
- v0.1.1 `compare_baseline.py` signature improvement should catch the
  PH-103-on-sea-plugin.json case correctly (no false attribution).
- Gate 6 PASS expected (description deliberately kept short — 281 chars — to avoid the PH-103 false-NEW that the srd run had to fix-forward).

---

## Adversarial Review

### Misuse case 1: Steps 2-4 combined commit lost atomic-per-step discipline

- **What might have gone wrong:** Reviewers reading the chain expect to see 5 separate commits matching the 5 recipe steps. The combined commit could be confusing.
- **Mitigation:** Commit message explicitly names "steps 2-4/5 combined" + explains why (bulk sweep crossed step boundaries). VERIFICATION_REPORT.md captures the step-by-step audit trail.
- **Status:** ACCEPTED — operator judgment; recipe-improvement signal for v0.1.2 may add explicit guidance on when combined commits are acceptable.

### Misuse case 2: probe scripts/tests subdirectories accidentally fork

- **What might have gone wrong:** probe brings its own scripts/ + tests/ subdirectories (the deterministic ast-grep + lizard + scc orchestrator package). These contain absolute imports + path refs that could break on the move.
- **Mitigation:** sea_sweep.py rewrote internal path refs within the scripts (e.g., `from probe.X import Y` paths). Verified the script paths still resolve post-move.
- **Status:** PREVENTED.

### Misuse case 3: code-review skill bundle

- **What might have gone wrong:** sea:code-review is a major skill that other agents dispatch. Renaming or moving could break dispatch.
- **Mitigation:** No rename (code-review already verb-noun). Path swept via bulk script.
- **Status:** PREVENTED.

---

## Recipe-improvement signals for v0.1.2 (re-iterated)

Same 3 signals as srd run; one now stronger:

1. **`bulk_rewrite.py` as a first-class helper** — both srd and sea runs needed an ad-hoc python script. Should be packaged. **Strongest signal** — used twice now.
2. **Atomic-per-step vs combined-commit guidance** — combined commits aren't a violation when the sweep crosses step boundaries; the recipe should give explicit guidance.
3. **`detect_collisions.py` tin-test heuristic** — caught 5/5 sea renames cleanly (no operator-judgment additions). Less pressure to extend heuristic given srd's 1/3 catch was an outlier.

---

## Verdict (final, pending Gate 6)

**Steps 2-5:** PASS
**Gate 6:** TBD — pending post-Commit-5 code-health final run.
