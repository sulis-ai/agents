---
id: HD-010
title: cmd_mark_gates_complete silently truncates the train YAML record (read_train_run_record does not exist)
status: proposed
severity: CRITICAL
pillar: form
source: code-review:PR-batch5-2026-05-23T124318Z
lens: architecture + quality
created: 2026-05-23
---

## Context

`scripts/wpx-train::cmd_mark_gates_complete` (Batch 5 — HD-007) finalises a
train paused at `phase=verifying_gates` by overwriting its YAML record at
`<train-runs>/<train_id>.yaml`. The intent (per HD-007 §"## Decision",
`scripts/wpx-train:1842-1852`) is to preserve the fields previously written
by `_finalise_awaiting_gates` (`bundle`, `deploy_url`, `final_merge_sha`,
`health_status`, `smoke_verdict`, `started_at`, `train_id`, `batch_size`,
`awaiting_gates_at`) and only mutate `outcome` + `completed_at` (+
optionally `gate_findings_path`).

The implementation reads the existing record before re-writing:

```python
# scripts/wpx-train:1842-1852 (HEAD)
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

**`read_train_run_record` does not exist in `_wpxlib.py`.** Confirmed by
`grep -n 'def read_train_run_record' scripts/_wpxlib.py` returning no
matches. Only `write_train_run_record` (line 2223) exists.

The bare `except Exception: pass` swallows the `ImportError`, leaving
`record = {}`. Subsequent code adds only `outcome` and `completed_at`
(line 1898-1899), then calls `write_train_run_record` (line 1904), which
opens the file with `path.write_text(...)` (line 2272 in `_wpxlib.py`) —
**truncating the file**.

**Result:** every gate-handoff train that completes successfully writes
a 2-field YAML record to the historical archive, **silently destroying**
the bundle / deploy_url / final_merge_sha / health_status / smoke_verdict
/ batch_size / started_at fields. The state file is then cleaned up so
the original data is unrecoverable from disk.

The trailing comment "Reader may not exist; harmless — we overwrite
minimal fields" suggests the author knew the function might not exist
but did not understand that `write_train_run_record` truncates rather
than merges. The same pattern repeats for the `--critical-found` branch
(line 1882-1886) — gate-blocker records also get truncated.

## Why the test suite missed this

`test_mark_gates_complete_finalises_train_to_success` (line 397) only
asserts `final.get("outcome") == "success"`. It does not assert that
`bundle`, `deploy_url`, or `final_merge_sha` are preserved. Same for the
`--critical-found` test. The behaviour is broken end-to-end; the test
contract is too loose to catch it.

## Severity

**CRITICAL.** This is silent data loss on every successful gate-handoff
train completion. It only fires when `--enable-gate-handoff` is passed
(today: opt-in, no production callers yet). But the moment `run-all/SKILL.md`
starts passing the flag (which the same Batch 5 documents as the
recommended path), every train run permanently truncates its own
historical archive.

The train YAML record is the audit trail. Losing the bundle field means
losing the WP → merge_sha mapping; losing final_merge_sha means losing
the deploy SHA; losing deploy_url means losing the only link to the
deploy run. These are the fields downstream tools (`/sea:code-review`
diff range derivation, `backfill-code-review` SHA discovery,
`/sulis-execution:backfill-gates`) consume.

## Verification — failing test (RED)

```python
def test_mark_gates_complete_preserves_bundle_and_deploy_fields(train_testbed):
    """HD-010 RED — mark-gates-complete must preserve bundle, deploy_url,
    final_merge_sha, started_at, batch_size from the awaiting_gates record."""
    _seed_three_wp_bundle(train_testbed)
    args = train_testbed.make_args(enable_gate_handoff=True)
    record, _ = train_testbed.run_train(args)
    awaiting_record_text = (
        train_testbed.workspace / ".architecture" / train_testbed.project /
        "train-runs" / f"{record['train_id']}.yaml"
    ).read_text()
    # Sanity: _finalise_awaiting_gates wrote a full record
    assert "bundle:" in awaiting_record_text
    assert "deploy_url:" in awaiting_record_text
    assert "final_merge_sha:" in awaiting_record_text or "merge_sha_on_dev:" in awaiting_record_text

    # Run mark-gates-complete (clean verdict)
    wpx = _load_wpx_train_module()
    mark_args = SimpleNamespace(
        project=train_testbed.project,
        repo_root=str(train_testbed.workspace),
        repo="acme/test-repo",
        train_id=record["train_id"],
        gate_findings=None,
        critical_found=False,
    )
    try:
        wpx.cmd_mark_gates_complete(mark_args)
    except SystemExit:
        pass

    # The record after finalise must STILL contain the fields _finalise_awaiting_gates wrote
    final_text = (
        train_testbed.workspace / ".architecture" / train_testbed.project /
        "train-runs" / f"{record['train_id']}.yaml"
    ).read_text()
    assert "outcome: \"success\"" in final_text, "outcome must update"
    assert "bundle:" in final_text, (
        "HD-010: bundle: field was truncated by mark-gates-complete. "
        "Historical archive is now incomplete."
    )
    assert "deploy_url:" in final_text, "deploy_url was truncated"
    assert "started_at:" in final_text, "started_at was truncated"
```

This test fails today (the post-mark-gates-complete record contains
only `outcome` and `completed_at`).

## Recommendation

Two paths to fix. Pick one based on speed vs. cleanness.

### Option A — Add `read_train_run_record` to `_wpxlib.py` (5-10 lines)

Mirror the YAML-lite parser already used by `find_wp_merge_sha`
(`_wpxlib.py:2520-2570`) into a reusable reader. The function exists
in pieces already; lift it into a named function and import it from
`cmd_mark_gates_complete`. Remove the bare-except — the function MUST
exist; failure here is a bug, not "harmless".

### Option B — Preserve the record in memory across the awaiting-gates → mark-gates-complete boundary via the state file

Write the awaiting-gates record into the JSON state file (which is
already preserved across the gate-handoff boundary), then read it back
from there in `cmd_mark_gates_complete`. Reuses existing infrastructure;
avoids new YAML parser code. Probably cleaner long-term.

Either way:
- Remove the bare-except. ImportError is a bug.
- Tighten the test contract: assert bundle / deploy_url / started_at
  are preserved.

## ADDED / MODIFIED / REMOVED

### MODIFIED

- `scripts/wpx-train` lines 1842-1852, 1882-1886, 1900-1906: replace the
  `from _wpxlib import read_train_run_record` import with either Option A
  (new `read_train_run_record` function) or Option B (state-file-mediated
  preservation). Remove the bare-except.

### ADDED (Option A)

- `scripts/_wpxlib.py`: new `read_train_run_record(record_path: Path) -> dict`
  function paralleling `write_train_run_record`. Parses the YAML-lite format
  the writer emits.

### ADDED (Option B)

- `scripts/_wpxlib.py`: extend `init_train_state` (or a new
  `stash_record_for_gates` helper) to embed the awaiting-gates record
  in the state file's JSON. `cmd_mark_gates_complete` reads it back.

### ADDED (either option)

- `scripts/tests/integration/test_train_failure_paths.py`: new test
  `test_mark_gates_complete_preserves_bundle_and_deploy_fields` (Red above).
- Tighten `test_mark_gates_complete_finalises_train_to_success` and
  `test_mark_gates_complete_with_critical_marks_gate_blocker` to also
  assert at least `bundle:` and `deploy_url:` survive.

## Sequence

This delta blocks the v0.23.0 commit. Fix before merge.
