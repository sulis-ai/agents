---
id: HD-003
title: Explicit partial-failure handling in cmd_run's sequential squash-merge loop
status: implemented
severity: HIGH
pillar: armor
sources:
  - SEA audit report 2026-05-23 (Pattern B — silent merge-loop crash leaves dev in half-state)
  - Production incident 2026-05-23 (autonomous founder session crash mid-batch after WP-AUTO-001 merged)
created: 2026-05-23
implemented: 2026-05-23
---

## Context

`wpx-train`'s `cmd_run` packs eligible Work Packages into a batch, rebases each
branch onto a sequential rebase chain, runs bundled-tip CI against the final
rebased branch, then performs sequential squash-merges into the base branch
(typically `dev`). After the merges land, one deploy + health + smoke check
runs per batch.

The merge loop (formerly `wpx-train` lines 1440–1448) had no explicit
per-merge failure handling:

```python
final_merge_sha = None
for entry in bundle:
    _log(f"Squash-merging {entry['wp']} ({entry['branch']}) to dev")
    sha = _merge_squash(repo, entry["branch"], entry["wp"],
                        base_branch=base_branch)
    entry["merge_sha_on_dev"] = sha
    final_merge_sha = sha
record["bundle"] = bundle  # refresh with merge_sha_on_dev populated
```

If `_merge_squash` raises on merge N after merges 1..N-1 succeeded, the
`RuntimeError` propagates up to the outer handler at `cmd_run`'s tail:

```python
except RuntimeError as exc:
    record["outcome"] = "error"
    record["outcome_reason"] = f"internal: {exc}"
    ...
    emit_result(record, exit_code=2)
```

Result: dev has merges 1..N-1, but no revert ran, no INDEX status flips
happened for the remaining WPs, no train BLOCKER artifact was written, and
the train state is `error` rather than `blocker`. The shipped commits are
live in production; the unshipped branches sit in `step-7-complete` state;
the next train tries to pick them up, finds drift, and a founder has to
debug what happened by reading git log + the train state YAML side by side.

## Defect

- Sequential squash-merge loop has no per-merge try/except
- On exception at merge N, exception propagates to `except RuntimeError` outer handler
- Outer handler writes `outcome=error` but does NOT call the revert path
- Result: dev holds merges 1..N-1; no ADR-212 revert; no branch restoration; no train BLOCKER artifact; INDEX shows stale `step-7-complete` for unmerged WPs
- Founder session sees `outcome=error` in the train run yaml and has to manually reverse-engineer state from git log

## Today's manifestation

2026-05-23 autonomous founder session: WP-AUTO-001 merged successfully into
dev. The next batch's first merge attempted on a branch whose rebased state
had drifted (the underlying cause: ADR-212 partial-failure absence — this
delta). `_merge_squash` raised. The exception propagated. The train state
went to `error`. The maintainer had to read git log + the train-state YAML
to reconstruct what had landed, manually revert WP-AUTO-001, manually
unstick the affected WPs' INDEX rows.

## Resolution

### ADDED

- `plugins/sulis-execution/scripts/tests/unit/test_wpx_train_partial_merge_failure.py`
  — characterisation test that proves the failing path was previously
  unhandled and is now routed through `_handle_post_merge_failure` with the
  partial bundle intact.
- This delta document as the audit trail.

### MODIFIED

- `plugins/sulis-execution/scripts/wpx-train` — `cmd_run`'s sequential
  squash-merge loop wrapped in per-merge try/except. On exception:
  - Log the failure via the existing `_log` helper, naming the WP and
    branch.
  - Update `record["bundle"]` with the partial bundle (entries with a
    populated `merge_sha_on_dev` reflect what actually landed; entries
    without are the merges that never happened, including the one that
    failed).
  - Invoke `_handle_post_merge_failure(...)` with the partial bundle,
    using a reason string that names the failing WP and the underlying
    exception message.
  - `_handle_post_merge_failure` already filters the bundle internally
    (`merged = [e for e in bundle if e.get("merge_sha_on_dev")]`) so the
    revert path runs only against the merges that actually landed. It also
    only attempts branch restoration for entries with a `merge_sha_on_dev`
    populated. Passing the full partial bundle is therefore correct — the
    existing function handles the partial-bundle case without modification.
  - `_handle_post_merge_failure` calls `emit_result(record, exit_code=1)`
    which calls `sys.exit(1)`, so control does not return to the loop. The
    `entry["merge_sha_on_dev"] = sha` line after the try/except runs only
    on the success path, preserving the existing bundle-update semantics.

### REMOVED

- Nothing was deleted. The outer `except RuntimeError` handler that
  previously caught the propagated merge failures remains in place — it
  still catches unexpected RuntimeErrors from other parts of cmd_run that
  aren't covered by the new try/except.

## Acceptance criteria

1. The merge loop wraps each `_merge_squash` call in try/except.
2. On per-merge exception, the partial bundle (entries with populated
   `merge_sha_on_dev` representing actually-landed merges) is passed to
   `_handle_post_merge_failure`.
3. The reason string passed to `_handle_post_merge_failure` includes the
   failing WP ID and the exception message.
4. `_handle_post_merge_failure`'s existing revert path runs and reverts
   only the merged subset of the bundle (the existing `merged = [...]`
   filter inside that function handles this correctly).
5. The outer `except RuntimeError` handler is NOT reached for merge
   failures (no `outcome=error` for the half-state path).
6. No Python exception propagates out of cmd_run for the partial-merge
   failure path — `_handle_post_merge_failure` terminates via `sys.exit`.
7. The new characterisation test passes and the existing 264+ unit tests
   continue to pass.

## Tests

A new file at
`plugins/sulis-execution/scripts/tests/unit/test_wpx_train_partial_merge_failure.py`
covers the characterisation:

| Test | What it characterises |
|---|---|
| `test_merge_failure_mid_batch_routes_to_handle_post_merge_failure_with_partial_bundle` | Mocks `_merge_squash` to succeed on WP-001 and WP-002 then raise on WP-003. Mocks `_handle_post_merge_failure` to capture call args. Verifies it was called exactly once with bundle entries 1+2 carrying `merge_sha_on_dev` and entry 3 with `merge_sha_on_dev=None`. Verifies the reason string mentions WP-003 and the exception message. |
| `test_merge_failure_mid_batch_calls_revert_with_merged_subset` | Same fixture, but allows the real `_handle_post_merge_failure` to run and mocks `revert_train_on_dev` instead. Verifies `revert_train_on_dev` is called with the bundle (its internal filter selects only the merged entries). |
| `test_merge_failure_does_not_propagate_python_exception` | The failing merge's exception must be caught inside the loop and routed through `_handle_post_merge_failure`'s `emit_result`-driven `SystemExit`. Asserts the only exception escaping `cmd_run` is `SystemExit`, never the underlying `RuntimeError` raised by the mocked `_merge_squash`. |

The tests load `wpx-train` as a module via `importlib.util.spec_from_file_location`
(the file has no `.py` extension and isn't on `sys.path` normally), then
monkeypatch the rebase / CI / deploy / setup helpers on the loaded module
to return canned values, leaving only the squash-merge loop's behaviour
exercised against the actual fix.

## Verification

```bash
# From plugins/sulis-execution/
cd plugins/sulis-execution/

# The 3 new tests pass
python -m pytest scripts/tests/unit/test_wpx_train_partial_merge_failure.py -v

# The full unit-test suite stays green (existing 264+ pass; 3 new pass)
python -m pytest scripts/tests/ -q
```

## What this DOESN'T fix (deferred)

- **The broader `cmd_run` plan/commit/verify split** — HD-001 (Batch 5).
  HD-003 is a scoped patch to the merge loop only; HD-001 will restructure
  cmd_run so the merge step is an isolated "commit phase" with its own
  testable boundary.
- **Per-merge atomicity** — the existing ADR-212 revert path is a single
  wrapper commit on `dev`. It does not roll back to per-WP atomicity. If
  you want each WP's merge to be independently revertable, that's a
  larger ADR change.
- **Pre-merge protection against the underlying causes of merge failures**
  — what made today's merge fail (branch SHA drift between rebase and
  merge; remote branch deletion mid-train; gh API timeout) is a separate
  audit. HD-003 ensures the failure is RECOVERABLE, not PREVENTED.
- **Telemetry / per-merge observability** — when merges fail, the only
  signal is the train state YAML. A future delta could emit per-merge
  spans / metrics. Out of scope here.

## See also

- ADR-212 (`docs/architecture/ADR-212-train-revert-on-post-merge-failure.md`)
  — the original revert-on-post-merge-failure decision. HD-003 closes a
  coverage gap in ADR-212: the post-merge revert path was implemented for
  deploy / health / smoke failures, but not for failures DURING the merge
  loop itself.
- SEA audit report (`Pattern B`): the architectural diagnosis that
  triggered this delta.
- Plan: `/Users/iain/.claude/plans/eager-crunching-quail.md` (Batch 2 of 6)
- HD-001 (forthcoming, Batch 5): plan/commit/verify split for cmd_run
  which makes the merge step's failure boundary explicit at the function
  level rather than at the try/except level.
- HD-002 (forthcoming, Batch 4): TrainTestbed integration fixture that
  will allow this characterisation to be re-expressed as an end-to-end
  test rather than a focused unit test.
