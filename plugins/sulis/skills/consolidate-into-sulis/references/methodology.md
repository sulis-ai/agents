# Methodology — Why each gate exists

This document explains the rationale for each of the 7 gates (Gate 0 + Commits 1–5 + Gate 6) in `consolidate-into-sulis`. SKILL.md tells you *what* to do; this tells you *why*.

The recipe is extracted from one proven precedent: the sulis-execution → sulis migration, commits `02c1e77` through `fa882b1` (5 commits, ~50 files moved, 0-finding self-test sustained). Each gate maps directly to one of those commits or to a verification step the precedent did informally.

## Why a runbook + gates and not a single execution script

A consolidation could be automated as one Python script that does all the `git mv`s in one go. We deliberately don't.

The reason: every plugin has shape variations the script can't predict — name collisions, naming gaps that fail the tin test, cross-plugin reference patterns specific to that plugin's role in the marketplace. A single script would either fail at the first variation (brittle) or paper over it silently (worse — the operator doesn't know what got hidden).

The 7-gate runbook makes every decision an operator-visible commit boundary. Reviewable. Rollback-able. Auditable. The cost is operator time per gate; the benefit is no silent drift.

## Gate 0 — Inventory + Plan + Baseline

### What failure mode it prevents

**Surprise mid-consolidation.** Without an explicit inventory + plan, halfway through Commit 3 the operator discovers a script that references the source plugin's CI workflow path — not noticed at Commit 1 because the script wasn't moved yet. Now the consolidation is in a half-state with no clean rollback.

### Why three deterministic helpers, not one

`inventory.py`, `detect_collisions.py`, `find_external_refs.py` separate **observation** (what's there) from **judgement** (what to do about it):

- `inventory.py` emits JSON — machine-readable, consumed by the other helpers
- `detect_collisions.py` emits Markdown — operator-readable, applies the tin-test rubric and collision detection
- `find_external_refs.py` emits Markdown — operator-readable, surfaces every line that needs editing during Commits 2–4

Each helper is independently testable. If the tin-test rubric evolves, only `detect_collisions.py` changes. If the external-ref sweep needs more categories, only `find_external_refs.py` changes.

### Why the code-health baseline is captured here

Code-health regressions during consolidation come from one of four sources:

1. Broken imports (a moved script references a moved-from path)
2. Ref rot in docstrings or comments (cited paths now wrong)
3. Coverage drop (tests moved but coverage config wasn't updated)
4. Lint regressions (style/format drift from the moves themselves)

All four show up as `/sulis:code-health` findings. Capturing the baseline at Gate 0 means Gate 6 can attribute new findings cleanly: NEW = consolidation-caused; PRE-EXISTING = unrelated.

## Commits 1–5 — Why this ordering

The order is **least-risky first**:

1. **Scripts + tests + CI** — self-contained inside `scripts/` directory; few external citations
2. **Skills** — citations between skills are mostly internal to the marketplace's plugin namespace
3. **Agents** — `subagent_type` citations span the marketplace but are programmatically findable
4. **References** — cited from anywhere (CLAUDE.md, other plugins' references, agent bodies); the highest-risk surface
5. **Wrap-up** — only safe to do after the moves are complete; bumps + deprecation markers

Operator reviewability stacks: at Commit 3, the operator can review whether agent moves landed correctly without the reference sweep having complicated the diff. At Commit 4, the operator can review the reference sweep in isolation.

### Why the rename pass is in Commit 2, not Commit 0

Renames are conditional on the tin-test rubric and the collision report. Doing them at Gate 0 would mean editing CONSOLIDATION_PLAN.md (and the rubric for what counts as a tin-test failure) before any moves have happened — a paper exercise.

By Commit 2, the rename target names are committed-by-action: the `git mv` itself is the rename. Editing the SKILL.md descriptions to match happens in the same commit.

### Why the external ref sweep is Commit 4, not woven through 2 + 3

Reference paths are cross-cutting. A reference cited from a Skill body (Commit 2) and an Agent body (Commit 3) both need updating to the new path. If we did partial sweeps in each commit, we'd have two diffs touching the same files for the same reason — review burden up, signal down.

Doing the full sweep at Commit 4 means: one diff per cited file, one logical change ("update path"), reviewable as a unit. Bonus: the sweep also catches refs the operator missed in earlier commits — defence in depth.

## Gate 6 — Code-health verification

### What failure mode it prevents

**Silent regression.** A consolidation can look complete (all 5 commits land cleanly, all `git grep` checks pass) and still ship broken: a moved import might fail only when the script actually runs; a coverage threshold might tip below its gate without anyone noticing.

`/sulis:code-health` runs the actual tools (lizard, jscpd, etc.) against the migrated tree. Findings that didn't exist at Gate 0 → consolidation-caused → fix forward.

### Why fix-forward, not roll-back

If Gate 6 surfaces regressions:

- Roll-back is cheap in principle (reset to before Commit 1), but expensive in practice (operator has already invested time; the right answer is usually a small fix, not a rewind)
- Fix-forward with a clearly-labelled Commit 6 (`fix(sulis): post-consolidation cleanup — broken imports in {file}`) preserves the consolidation history while making the regression auditable

A consolidation that requires more than 2–3 fix-forward commits to land clean is signal the recipe needs improvement — surface in the run's `VERIFICATION_REPORT.md` for future-pattern learning.

### Why Gate 6 is mandatory, not "if you remember"

The single forcing function (per SPIRAL_TEMPLATES): VERIFICATION_REPORT.md on disk must contain `Verdict: PASS`. Gate 6 produces the comparison artifact that makes that verdict honest. Skip Gate 6 → the verdict is uncalibrated.

## Why no `consolidate-into-sulis --auto` flag

It would be easy to add a `--yolo` flag that runs all 5 commits + Gate 6 without operator pause. We deliberately don't:

- Plugin shapes vary; the operator's judgement at gate boundaries is the safety mechanism
- Atomic commits with operator review match the precedent (5 inspectable commits, not one bulk)
- The Phase 3 plan is 4 consolidations across ~2 weeks of focused operator time — automation isn't the bottleneck; getting each one right is

When the recipe has been run 4+ times and patterns are stable across all of them, revisit whether an `--auto` flag is worth the risk.

## Composition with `add-skill`

`consolidate-into-sulis` was authored via `add-skill` v0.7.0 (the methodology that produces this kind of skill). Specifically:

- Gate 1 (Find) — BRIEF_PACK confirmed no existing consolidation skill in the marketplace; CC = VALIDATED across 90 skills
- Gate 2 (Scope Lock) — locked operator-facing audience, HEAVY tier, no COACHING/TONE, single-mode procedure
- Gate 3 (Generate) — this skill's files
- Gate 4 (Evaluate) — VERIFICATION_REPORT.md alongside SKILL.md with the HEAVY tier dimensions
- Gate 5 (Adversarial Review) — misuse cases for what could go wrong during a consolidation

If `add-skill` evolves to v0.8.0+, this skill should be re-evaluated against the new methodology and updated where the evolution applies.
