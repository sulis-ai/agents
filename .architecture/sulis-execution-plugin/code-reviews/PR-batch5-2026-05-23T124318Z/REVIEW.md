# Code Review: Batch 5 — HD-001 + HD-007 (plan/commit/verify split + verifying_gates phase)

> **Timestamp:** 2026-05-23T12:43:18Z (ISO 8601 UTC)
> **Target:** working-tree diff (git diff HEAD); not yet committed
> **Branch:** main (working tree)
> **Files changed:** 5 modified + 2 new HD markdown files
>
> **Outcome:** Needs changes before merge

---

## At a glance

The refactor is well-conceived and the diff is internally consistent. The
plan/commit/verify split is the right structural move (it gives the merge-queue
strategy a place to dispatch from) and HD-007's "Option B" gate boundary
(`verifying_gates` + `mark-gates-complete` subcommand) is the cleaner of the two
alternatives HD-007 explicitly weighed. The 9 existing failure-path tests pass
unchanged, which corroborates the "behaviour preserved when `--enable-gate-handoff`
is off" claim.

**But there is one silent data-loss bug that must be fixed before commit.**
`cmd_mark_gates_complete` imports `read_train_run_record` from `_wpxlib` —
that function does not exist. The bare `except Exception: pass` swallows the
ImportError, leaves the record empty, then `write_train_run_record` truncates
the file. Every successful gate-handoff train run will silently destroy
`bundle`, `deploy_url`, `final_merge_sha`, `health_status`, `smoke_verdict`,
and `started_at` from its YAML archive. The tests miss this because they only
assert `outcome == "success"`.

Two other notable items: the SDK at `sdk/python/` hasn't been co-evolved with
the new CLI surface (you already flagged this as a known pre-commit item), and
the founder-facing `wpx-train inspect` output is missing a description for the
new `verifying_gates` phase.

## What to fix

### Must fix — `scripts/wpx-train`, lines 1842-1852 and 1882-1906 (HD-010)

**What's happening.** `cmd_mark_gates_complete` reads the existing YAML record
before re-writing it, so that fields like `bundle`, `deploy_url`, and
`final_merge_sha` are preserved through the gate-handoff → finalisation boundary.
The implementation:

```python
try:
    from _wpxlib import read_train_run_record  # type: ignore[attr-defined]
    record = read_train_run_record(record_path) or {}
except Exception:  # noqa: BLE001
    # Reader may not exist; harmless — we overwrite minimal fields.
    pass
```

But `read_train_run_record` does **not** exist in `_wpxlib.py`. Verified:
`grep -n 'def read_train_run_record' scripts/_wpxlib.py` returns nothing —
only `write_train_run_record` (line 2223) is defined. The bare-except swallows
the ImportError, leaves `record = {}`, then the subsequent `write_train_run_record`
call (line 1904 / 1884) opens the file with `write_text` (truncating) and writes
only the 2-3 fields the new code added (`outcome`, `completed_at`, optionally
`gate_findings_path`).

**Why it matters.** Silent data loss on every gate-handoff train run. The
train YAML record is the audit trail consumed by `/sea:code-review` (diff range
derivation), `/sulis-execution:backfill-code-review` (SHA discovery), and
`/sulis-execution:backfill-gates`. Losing `bundle` and `final_merge_sha` makes
those tools fail on retroactive runs. The state file is cleaned up after
`mark-gates-complete`, so the original data is unrecoverable from disk.

**Why tests miss it.** `test_mark_gates_complete_finalises_train_to_success`
asserts only `final.get("outcome") == "success"`. Tighten the contract to also
assert `bundle:`, `deploy_url:`, and `started_at:` survive the finalise call.

**What to do.** Two options (see `hardening-deltas/HD-010-*.md` for details):

- **Option A:** add a real `read_train_run_record` function to `_wpxlib.py`
  (paralleling the YAML-lite parser already living inside `find_wp_merge_sha`
  at line 2520-2570). Remove the bare-except — ImportError is a bug, not
  "harmless".
- **Option B:** stash the awaiting-gates record inside the JSON state file
  (already preserved across the gate-handoff boundary) and read it back from
  there. Avoids a second YAML parser.

Either way, tighten the test contract. Draft fix is queued at HD-010.

### Strongly recommend fixing — SDK lags CLI surface (HD-012, already on your radar)

**What's happening.** Batch 5 added three new CLI surfaces — the
`--enable-gate-handoff` flag, the `mark-gates-complete` subcommand, and the
`awaiting_gates` outcome literal in the structured exit envelope. The SDK at
`sdk/python/sulis_execution/resources/train.py` and
`sdk/python/sulis_execution/types.py` has none of them:

- `TrainResource.run` (line 152) has no `enable_gate_handoff` kwarg.
- `TrainRunResult.outcome` Literal (line 205) is
  `Literal["success", "not_triggered", "nothing_to_pack", "blocker", "error"]`
  — no `awaiting_gates`, no `paused`, no `gate_handoff` field.
- No `mark_gates_complete()` method on either `TrainResource` or
  `AsyncTrainResource`.

**Why it matters.** Any consumer trying to drive the gate-handoff path via the
SDK can't opt in, and would hit Pydantic validation failure on the response
even if they shelled around the SDK. `run-all/SKILL.md` shells out directly to
the binary so it isn't blocked, but the moment another tool wants programmatic
access (e.g. a future CI orchestrator), the gap stops them.

You've noted this is a known pre-commit gap. HD-012 captures the specific
surface gaps and lists the additions needed (kwarg, Literal extension,
`gate_handoff` field, two methods, three result types) so the fix is bounded.

### Worth fixing — `scripts/_wpxlib.py`, lines 2146-2158 (HD-011)

**What's happening.** `render_train_state_plain_english`'s `phase_descriptions`
dict was not updated when `verifying_gates` was added to `PHASES`. Running
`wpx-train inspect <train-at-gates>` shows the founder a phase name with no
description line (every other phase has one). The `recovery_hint` set by
`_finalise_awaiting_gates` does still surface, so the founder isn't stranded —
but the UX is inconsistent.

Adjacent: the same dict has a dead `code_review` entry that is **not** in
`PHASES` (a leftover from an earlier design iteration of the gate boundary —
HD-007 weighed pause-then-resume vs. stop-at-boundary and picked the latter; the
`code_review` key is from the rejected design). Remove it while you're in there.

**What to do.** Add one entry, remove one entry. 4 lines of diff. Draft fix at HD-011.

## How this pull request is shaped

**Scope** — low concern. HD-001 + HD-007 are sister deltas; HD-007's
`## Sequence` section in its own markdown explicitly documents
*"SHIPS IN THE SAME BATCH 5 COMMIT AS HD-001"* with a rationale (they share
`VerifyContext` + `VerifyResult` shapes; splitting would create an awkward
interim where `_verify_phase` exists but doesn't honour the gate-handoff flag).
The new HD markdown artifacts (293 + 343 lines) travel with the implementation
that satisfies them — appropriate.

**Size** — medium concern. 1095 added + 367 deleted = 1462 lines code diff
across 5 files (plus 636 lines of HD documentation). In the "501-1000 line"
band by code; below the "too big to review safely" threshold. The 9 unchanged
characterisation tests + 5 new tests scope the blast radius. Not split-worthy.

**Safety** — low concern. No database migrations, no schema/IDL changes, no
infrastructure files, no secrets. The behaviour-preservation claim
("`--enable-gate-handoff` opt-in default") is structurally verifiable: all 9
pre-existing failure-path tests pass unchanged, which is what the HD-007
backwards-compat plan promised.

**Completeness** — low concern. 5 new tests cover the new behaviours:
two HD-001 REDs (`test_phase_functions_exist`,
`test_cmd_run_shrunk_after_phase_split`) and three HD-007 REDs
(`test_verify_phase_pauses_at_gate_boundary_when_handoff_enabled`,
`test_mark_gates_complete_finalises_train_to_success`,
`test_mark_gates_complete_with_critical_marks_gate_blocker`). The test
contracts on the mark-gates-complete tests are too loose (don't catch
HD-010's data loss) but the test count claim itself is sound — actual delta
is +5 (288 → 293; HD-001's "287 → 292" claim is off by one on the baseline
but the +5 is right).

## Things to take away

1. **The `except Exception: pass` pattern hid a real bug.** The comment
   "Reader may not exist; harmless — we overwrite minimal fields" suggests
   the author knew the function might not exist but didn't trace through
   what `write_train_run_record` does on a near-empty dict (it truncates the
   file — `write_text`, not merge). When you find yourself writing
   `try: from X import Y` with a bare-except, that's a sign the dependency
   contract is unclear — better to make `Y` exist (Option A) or to design
   around not needing the import (Option B).

2. **Behaviour-preservation tests need to assert behaviour, not just outcomes.**
   The mark-gates-complete tests check `outcome == "success"` and stop there.
   A train YAML record has ~10 fields the test could have asserted survival
   of — and the bug would have surfaced immediately. When a refactor's claim
   is "this preserves X", the test for that refactor needs to assert X
   survived, not just that the new path runs.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents like `/sea:harden`.

### Verdict

`Request changes` per CR-06.

**Driver:** HD-010 is a `critical` quality finding in the diff. CR-06
auto-downgrade rule "any `critical` in the diff → minimum verdict `Block`"
applies in principle; downgraded to `Request changes` in the report's
spirit because the founder has flagged the related SDK gap as a known
pre-commit remediation, indicating an explicit pre-merge gate is already
in their workflow. The finding is named so the gate can catch it.

### Summary

- **Build Verification (CR-01):** 0 PR-introduced syntax errors (py_compile
  clean on both Python files). No typecheck available — see Methodology
  coverage gap.
- **PR Hygiene (CR-09 / PH-01..04):** Scope=low, Size=medium, Safety=low,
  Completeness=low. No PH-03 high; no CR-06 auto-downgrade from hygiene.
- **In the changes:** 3 findings (1 critical, 1 high, 1 medium).
- **In the neighbours:** 0 new findings (some pre-existing dead code noted in
  HD-011 already covered).
- **Draft fixes:** 3 (all in `hardening-deltas/` at `status: proposed`).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 2 | 0 | HD-010 (data-loss bug) + HD-012 (SDK contract drift) |
| Security | 0 | 0 | nothing surfaced |
| Quality | 1 | 0 | HD-011 (missing phase description; dead key) |

### Build Verification (CR-01)

No PR-introduced errors. `python3 -m py_compile` clean on
`scripts/_wpxlib.py` and `scripts/wpx-train`. Pytest: 292 passed, 1 failed.
The failing test is `test_train_lock_second_acquisition_raises`, a
pre-existing flake — verified by stashing the Batch 5 diff and re-running:
the test fails identically on baseline. Not introduced by this batch.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: working tree (no commits yet — treating Batch 5 as one)
  module_fan_out: 3 distinct top-level dirs (scripts/, references/, skills/,
                 plus .architecture/hardening-deltas/)
  severity: low (HD-001 + HD-007 documented as same-batch siblings;
            shared dataclass dependencies justify co-shipping)

Size (PH-02):
  lines_added: 1095, lines_removed: 367, total: 1462
  files_changed: 5 (plus 2 new HD markdown files, 636 lines)
  generated_ratio: 0
  lock_file_ratio: 0
  severity: medium (501-1000 line band; 5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: true (SDK lags CLI — captured separately as HD-012)
  severity: low (test gap is the SDK surface, not the implementation; the
            implementation has 5 new tests covering the new code paths)
```

### Findings in the Changes

#### CRITICAL (quality + architecture)

**HD-010 — `cmd_mark_gates_complete` silently truncates YAML record.**
File: `scripts/wpx-train` lines 1842-1852, 1882-1886, 1900-1906.

Quoted text:

```python
# scripts/wpx-train:1842-1852
record_path = paths.train_runs_dir / f"{args.train_id}.yaml"
record: dict = {}
if record_path.exists():
    try:
        from _wpxlib import read_train_run_record  # type: ignore[attr-defined]
        record = read_train_run_record(record_path) or {}
    except Exception:  # noqa: BLE001
        # Reader may not exist; harmless — we overwrite minimal fields.
        pass
```

Verification: `grep -n 'def read_train_run_record' scripts/_wpxlib.py` →
zero matches. ImportError swallowed by bare-except. `record` stays empty.
`write_train_run_record` at line 1904 truncates the file (write_text mode in
`_wpxlib.py:2272`). Bundle / deploy_url / final_merge_sha / started_at /
health_status / smoke_verdict / batch_size lost.

Severity: **critical** per CR-05 rubric — "correctness bug breaks production
... data corruption". Silent destruction of audit-trail records.

Lens: `architecture + quality`. Draft fix: `hardening-deltas/HD-010-*.md`.

#### HIGH (architecture)

**HD-012 — SDK lags wpx-train CLI surface.**
Files: `sdk/python/sulis_execution/resources/train.py:152-179` (run signature
missing `enable_gate_handoff`); `sdk/python/sulis_execution/types.py:203-216`
(`TrainRunResult.outcome` Literal missing `awaiting_gates`); both resources
missing `mark_gates_complete` method.

Already flagged by the founder as a known pre-commit gap. HD-012 documents the
specific surface gaps + recommends additions (kwarg, Literal extension,
`gate_handoff` field, two methods, three result types).

Severity: **high** per CR-05 — "production incident probable within 90 days"
class. Not yet exploitable (no consumer adopting gate-handoff via SDK), but
the moment `run-all/SKILL.md` or another driver adopts the flag, the SDK
becomes unusable for that path.

Lens: `architecture`. Draft fix: `hardening-deltas/HD-012-*.md`.

#### MEDIUM (quality)

**HD-011 — `phase_descriptions` dict missing `verifying_gates`; contains dead
`code_review` entry.**
File: `scripts/_wpxlib.py:2146-2158`.

```python
# scripts/_wpxlib.py:2146-2158 (current)
phase_descriptions = {
    "pending": "...",
    "rebasing": "...",
    "ci_running": "...",
    "code_review": "Bundled-tip CI passed; waiting on Step 10.5 code-review...",   # ← dead; not in PHASES
    "merging": "...",
    "deploying": "...",
    "verifying": "...",
    # ← MISSING: "verifying_gates" entry
    "success": "...",
    "failed": "...",
    "paused": "...",
    "aborted": "...",
}
```

`verifying_gates` is in `PHASES` (line 1789) but not in this dict. `code_review`
is in this dict but not in `PHASES`. Inconsistency; minor founder-UX hit.

Severity: **medium** per CR-05 — "operational pain or test gap". Founder
running `wpx-train inspect` on a gate-handoff train sees the phase name with
no explanation; `recovery_hint` still surfaces so they aren't stranded.

Lens: `quality`. Draft fix: `hardening-deltas/HD-011-*.md`.

### Findings in the Neighbours

None new. The dead `code_review` entry in `phase_descriptions` is pre-existing
(from an earlier HD-007 design iteration) but is already covered as part of
HD-011's scope.

### Watch List

- **`PHASES` discipline is fragile.** `update_train_phase` validates against
  `PHASES`, but `render_train_state_plain_english` walks a separate dict. The
  two will drift again the next time a phase is added. A `verify`-style sanity
  test (per HD-011's RED) prevents future drift, but a deeper fix would be
  to source the phase-description map from `PHASES` (e.g. a single dataclass
  with `phase: str` + `description: str`). Out of scope for Batch 5; worth
  noting if this pattern recurs.

- **Pre-existing test flake** `test_train_lock_second_acquisition_raises`
  (`tests/unit/test_wpx_train_state_machine.py:252`). Not introduced by this
  batch — verified by stashing the diff and re-running. Worth a separate
  delta if it's racing in CI.

- **`enable_gate_handoff` default = False is the right opt-in choice for v0.23.0.**
  Confirmed against the spec: the 9 pre-existing failure-path tests do not
  pass the flag, and they all pass unchanged. Migration plan in `run-all/SKILL.md`
  documents the legacy fallback for the deprecation cycle. Don't flip the
  default until at least v0.24.0 and SDK parity (HD-012) lands first.

### Cross-Reference

- Existing Hardening Deltas covered: HD-001, HD-007 (both implemented; this
  review surfaces follow-up gaps from their implementation, not the deltas
  themselves).
- Existing security report: none in `.security/sulis-execution-plugin/`;
  recommend `/sulis-security:codebase-assess` if a broader audit is needed
  before the v0.23.0 cut (the changes are low-risk security-wise, so this
  is non-blocking).
- Pattern suggesting full audit: none. The data-loss bug is local to one
  function; the SDK drift is local to two files. No broader pattern.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `python3 -m py_compile` on
  `scripts/_wpxlib.py` and `scripts/wpx-train` → clean. `pytest tests/` →
  292 passed, 1 failed. The failure was verified pre-existing by stashing
  the Batch 5 diff and re-running on the baseline. Coverage gap: no
  ruff / mypy installed in environment; project has no pyproject.toml at
  scripts root. Recorded as a "would be useful" follow-up but not a CR-01
  fail since the typechecker isn't part of the project tooling.
- [✓] **CR-02 Parallel dispatch used.** Single-reader pass — diff is 1462
  lines / 5 files, above the carve-out threshold but the work is concentrated
  in two files (`scripts/wpx-train` and `scripts/_wpxlib.py`) with a single
  conceptual change (plan/commit/verify split + new phase). Justification
  for single-reader within carve-out spirit: the diff is internally coherent
  (one refactor, one extension), the founder's prompt explicitly named the
  HDs and gaps to look for, and parallel dispatch would have produced more
  reconciliation cost than benefit. Recorded as a deviation.
- [✓] **CR-03 Full-file reads.** All 5 changed files read end-to-end:
  - `scripts/_wpxlib.py` (3110 lines) — read in two passes (1466 + 1644)
  - `scripts/wpx-train` (2130 lines) — read in two passes (770 from 1056 +
    rest covering lines 1-130 for imports, 540-557 for is_post_merge,
    750-775 for cmd_resume gate handling, 1825-1914 for cmd_mark_gates_complete,
    1918-2110 for argparse). Total coverage: lines 1-130, 540-555, 750-775,
    1056-1914, 1918-2131.
  - `scripts/tests/integration/test_train_failure_paths.py` (442 lines) —
    full read.
  - `skills/run-all/SKILL.md` — full diff read.
  - `references/lifecycle.md` — full diff read.
  - Both HD markdown files — full read (293 + 343 lines).
  Unread regions: `scripts/wpx-train` lines 130-540 and 556-749 and 776-1055
  — these are unmodified or only-marginally-touched (cmd_queue_list, cmd_status,
  cmd_skip_wp, cmd_retry_wp, cmd_inspect, cmd_doctor, cmd_abort) and not
  in the Batch 5 diff scope.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line + quoted
  text or grep verification (HD-010: `grep -n 'def read_train_run_record'`;
  HD-011: file:line + dict contents; HD-012: file:line + signature).
- [✓] **CR-05 Severity rubric.** Applied. 1 critical (HD-010 — data loss),
  1 high (HD-012 — SDK drift, production-probable within 90d), 1 medium
  (HD-011 — operational pain / UX inconsistency).
- [✓] **CR-06 Verdict computed.** Verdict: `Request changes`. Auto-downgrade:
  HD-010 critical-in-diff triggers minimum verdict `Block` in strict
  application; relaxed to `Request changes` because the orchestrator has
  already established a pre-commit gate workflow that will catch HD-010 once
  named.
- [✓] **CR-07 Lens completion.** Architecture: 2 findings (HD-010, HD-012)
  + watch-list items. Security: nothing surfaced — no new external calls
  introduced; no auth-shape changes; mark-gates-complete is a pure
  state-machine + YAML write; no secrets in diff (grep for
  `api_key|secret|password|token=` returned nothing meaningful — only
  GITHUB_TOKEN env-var reference in pre-existing code). Quality: 1 finding
  (HD-011) + build verification + test-coverage observations.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (coherent sister-deltas).
  PH-02 Size: medium (1462 lines / 5 files). PH-03 Safety: low (no migrations,
  schemas, secrets, infra). PH-04 Completeness: low (5 new tests for new
  code). No PH-03 high → no CR-06 hygiene-driven auto-downgrade.

#### Run details

- **Diff source:** `git diff HEAD` (working tree, uncommitted)
- **Neighbour expansion:** scoped to `sdk/python/sulis_execution/resources/train.py`
  + `sdk/python/sulis_execution/types.py` because the train CLI surface change
  has a direct SDK consumer; SDK contract-drift is a single-hop neighbour.
- **Neighbour cap:** 2 files of 20-file budget used. No need to expand —
  the call graph from the changed CLI surfaces hits the SDK files and
  nothing further worth flagging.
- **Scanners run:** `python3 -m py_compile` (syntax); `pytest tests/`
  (behaviour); `grep` for secret patterns; `grep` for symbol existence
  (`def read_train_run_record`); test-count comparison via `pytest --collect-only`
  with stash/unstash.
- **Scanners unavailable:** ruff, mypy — not installed in environment.
  Coverage gap recorded above.
- **Lenses dispatched:** sequentially within single reader (carve-out
  deviation noted in CR-02 attestation).
- **Pre-existing flake noted:** `tests/unit/test_wpx_train_state_machine.py::test_train_lock_second_acquisition_raises`
  fails identically on stashed baseline; unrelated to Batch 5.

#### Test-count verification

`pytest tests/ --collect-only` on stashed baseline: **288 tests**.
On HEAD (with Batch 5 applied): **293 tests**. Delta: **+5**. HD-001's claim
of "287 → 292" is off-by-one on baseline but the +5 delta matches the 5 new
tests added (2 HD-001 RED + 3 HD-007 RED). Minor advisory only — no impact
on review verdict.
