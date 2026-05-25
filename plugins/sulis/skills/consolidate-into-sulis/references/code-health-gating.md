# Code-health gating — Gate 0 baseline + Gate 6 verification

The 5-commit recipe is mechanical (move files, edit references, mark deprecated, bump versions). The 2 verification gates are what prevent silent regression: Gate 0 captures the pre-state, Gate 6 verifies the post-state hasn't degraded.

## Why code-health (not test suite alone)

The test suite catches some regression types (broken imports, behaviour drift) but not all:

| Regression type | Caught by tests? | Caught by code-health? |
|---|---|---|
| Broken import after `git mv` | Yes (test run fails) | Yes (`check-build` / `check-tests`) |
| Path drift in docstring or comment | No | Yes (`check-readability` cross-reference scan) |
| Coverage drop because tests moved but coverage config didn't | Sometimes | Yes (`check-tests` coverage tier) |
| Dead code from removed cross-plugin imports | No | Yes (`check-maintainability`) |
| Documentation gaps from removed-then-not-recreated docs | No | Yes (`check-polish`) |
| Security finding in moved code | No | Yes (`check-security`) |
| Build script breakage | No | Yes (`check-build`) |

`/sulis:code-health` runs all 7 tiers (Exists / Safe / Works / etc.) — broader regression coverage than tests alone. Hence: code-health is the gate, not just tests.

## Gate 0 — Baseline capture

Run `/sulis:code-health --raw` at consolidation start. Save the JSON to the run directory:

```
plugins/sulis/skills/consolidate-into-sulis/runs/{source}-{YYYY-MM-DD}/code-health-baseline.json
```

The baseline captures:

- Total finding count per tier
- Per-finding signature (file, line, rule, severity)
- Tier-level verdict (Pass / Concerns / Fails)
- Tool versions invoked (so we know the comparison is apples-to-apples)

### What to do if Gate 0 itself surfaces findings

A pre-existing finding load is fine — the baseline records it. The consolidation just must not make it worse.

If pre-existing findings are blocking other work (e.g., the founder is in the middle of triaging a `check-security` regression), defer the consolidation until that work has cleared.

## Commits 1–5 happen here

The consolidation runs. Nothing about code-health gating fires during the commits themselves.

(Operator may choose to spot-check by running `/sulis:check-build` after Commit 1, etc., but this is not mandatory between commits.)

## Gate 6 — Verification

After Commit 5 lands, re-run `/sulis:code-health --raw`:

```
plugins/sulis/skills/consolidate-into-sulis/runs/{source}-{YYYY-MM-DD}/code-health-final.json
```

Then compare:

```bash
python3 plugins/sulis/skills/consolidate-into-sulis/scripts/compare_baseline.py \
  --baseline "$RUN_DIR/code-health-baseline.json" \
  --final    "$RUN_DIR/code-health-final.json" \
  > "$RUN_DIR/code-health-comparison.md"
```

The comparison classifies each finding in the final report as:

- **PRE-EXISTING** — also present in baseline. Pre-dates the consolidation. Document; do not gate on these.
- **NEW** — present in final, absent in baseline. Consolidation-caused (in attribution). Investigate.
- **RESOLVED** — present in baseline, absent in final. Consolidation accidentally improved things (e.g., dead code removed when a cross-plugin import was dropped). Note in `VERIFICATION_REPORT.md`.

## Regression rubric

For each NEW finding, classify:

### Regression-grade (gates the consolidation)

- **Broken import** — a moved file references a moved-from path
- **Coverage drop** — coverage configuration didn't follow the move
- **Build failure** — `check-build` reports the project no longer builds
- **Lint introduction** — style/format drift from the moves themselves (e.g., trailing whitespace from manual edits)
- **Security finding in moved code** — moved code now flagged that wasn't before (often a false positive from a config gap; investigate before dismissing)

→ Fix forward as Commit 6. Re-run Gate 6.

### Acceptable / pre-existing in disguise

- **Pre-existing but un-baselined** — the baseline missed it because the file wasn't in the pre-consolidation tree (e.g., a moved file was previously excluded by allowlist; now it's not). Update the baseline mentally; document in VERIFICATION_REPORT.md.
- **False attribution** — the consolidation moved code that had a finding, and the finding now appears under a different file path. Net new = zero; document the path change.

→ Document; do not gate.

## What "fix forward" looks like

Worked example: after sulis-execution → sulis consolidation, `check-build` finds:

```
ERROR plugins/sulis/scripts/wpx-pipeline:42 — ImportError: No module named '_wpxlib'
```

Investigation: `wpx-pipeline` references `from _wpxlib import …`, but `_wpxlib.py` was moved to `plugins/sulis/scripts/_wpxlib.py` and the relative import in `wpx-pipeline` still points at the old location.

Fix:

```bash
# Edit wpx-pipeline to update the import
git diff  # confirm only the import line changed
git add plugins/sulis/scripts/wpx-pipeline
git commit -m "fix(sulis): step 6 — post-consolidation broken import in wpx-pipeline"
```

Re-run Gate 6:

```
python3 plugins/sulis/skills/consolidate-into-sulis/scripts/compare_baseline.py \
  --baseline "$RUN_DIR/code-health-baseline.json" \
  --final    "$RUN_DIR/code-health-final-after-fix.json"
```

Expected: NEW = 0; PASS.

## Pass criteria summary

Gate 6 passes when **one of**:

- NEW = 0 in the comparison report; OR
- All NEW findings have been fix-forward'd to NEW = 0 in a re-run

The `VERIFICATION_REPORT.md` for the consolidation records the final verdict + the comparison report path + any fix-forward commits as audit trail.

## Patterns to watch for across multiple consolidations

After 2+ consolidations run via this skill, look for patterns in the fix-forward commits. Recurring patterns are signal the recipe needs improvement:

- If broken imports show up every time → Commit 1 needs a sweep step that catches this before commit
- If coverage drops every time → Commit 2 needs a coverage-config update step
- If lint findings show up every time → operator habits during edit pass need attention

The first 4 Phase 3 consolidations are the calibration data set for refining the recipe in a future version.
