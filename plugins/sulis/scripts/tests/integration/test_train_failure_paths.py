"""End-to-end failure-path tests for `wpx-train`'s `cmd_run`.

Each test constructs a 3-WP bundle via the `TrainTestbed` fixture
(HD-002), injects a single named failure mode, runs `cmd_run`, and
asserts the recovery is as documented:

  - rebase conflict mid-batch       → conflicted WP → step-7-blocked; other WPs proceed
  - bundled-tip CI red              → no merges; train paused; founder action required
  - bundled-tip CI timeout          → no merges; train paused; founder action required
  - mid-batch merge failure (HD-003) → revert successful merges; restore branches
  - deploy timeout                  → paused state
  - deploy explicit failure         → ADR-212 revert path
  - health unhealthy                → ADR-212 revert path
  - smoke FAIL                      → ADR-212 revert path
  - happy path (baseline)           → all 3 merged, deploy green, health healthy, smoke PASS

These tests close the gap noted in the SEA audit report 2026-05-23:
``cmd_run``'s six failure modes were previously covered only by
per-helper monkeypatch tests. With the TrainTestbed they're covered
end-to-end through a single orchestrator entry point — the prerequisite
for HD-001 to safely refactor cmd_run into plan/commit/verify phases.

HD-001 + HD-007 additions (v0.23.0):
  - `test_phase_functions_exist` — RED proving the split happened.
  - `test_cmd_run_shrunk_after_phase_split` — RED proving cmd_run is no
    longer a 400+ LOC monolith.
  - `test_verify_phase_pauses_at_gate_boundary_when_handoff_enabled` —
    RED proving the HD-007 gate-handoff boundary fires.
  - `test_mark_gates_complete_finalises_train_to_success` — RED proving
    the new subcommand promotes verifying_gates → success.
  - `test_mark_gates_complete_with_critical_marks_gate_blocker` —
    RED proving --critical-found records gate_blocker without revert.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest  # noqa: F401 (used implicitly via parametrize, etc.)

# Import the testbed module-loader helper for the HD-007 tests that
# directly invoke cmd_mark_gates_complete (no test wrapper for that
# subcommand on the testbed; tests construct args + call directly).
from testbed import _load_wpx_train_module

# The `train_testbed` fixture is re-exported from
# scripts/tests/integration/conftest.py; pytest discovers it
# automatically. No explicit import here.


# Shared helper: seed 3 WPs at step-7-complete with one commit each.
def _seed_three_wp_bundle(testbed) -> list[str]:
    """Seed WP-001, WP-002, WP-003 on the bare repo + INDEX. Returns IDs."""
    wps = ["WP-001", "WP-002", "WP-003"]
    for wp in wps:
        slug = wp.lower().removeprefix("wp-")
        testbed.seed_wp_branch(wp, slug)
    testbed.seed_index_with_wps([
        (wp, f"{wp} title") for wp in wps
    ])
    return wps


# ─── Test 1: happy path — baseline ───────────────────────────────────


def test_happy_path_three_wp_bundle_all_merge_to_dev(train_testbed):
    """Three WPs at step-7-complete, no failures injected: all three merge
    onto dev; deploy green; outcome=success.
    """
    _seed_three_wp_bundle(train_testbed)
    args = train_testbed.make_args()
    record, exit_code = train_testbed.run_train(args)
    assert exit_code == 0, (
        f"Expected exit 0 on happy path; got {exit_code}. "
        f"Record: {record}"
    )
    assert record.get("outcome") == "success", (
        f"Expected outcome=success; got {record.get('outcome')}. Record: {record}"
    )
    train_testbed.assert_merged_on_dev("WP-001")
    train_testbed.assert_merged_on_dev("WP-002")
    train_testbed.assert_merged_on_dev("WP-003")
    # No INDEX flips to step-7-blocked on happy path
    assert not any(f["to_status"] == "step-7-blocked"
                   for f in train_testbed.index_flips), (
        f"Unexpected step-7-blocked flips on happy path: "
        f"{train_testbed.index_flips}"
    )
    assert not train_testbed.revert_calls, (
        f"Unexpected revert on happy path: {train_testbed.revert_calls}"
    )


# ─── Test 2: rebase conflict mid-batch ──────────────────────────────


def test_rebase_conflict_on_wp_002_flips_only_that_wp_to_blocked(train_testbed):
    """Inject a competing change on dev that conflicts with WP-002's branch.

    Expected: WP-002 is flipped to step-7-blocked + per-WP BLOCKER
    written; WP-001 and WP-003 proceed through the rebase chain (they
    don't conflict with the dev-side change because they touch
    different files).
    """
    _seed_three_wp_bundle(train_testbed)
    train_testbed.fail_rebase("WP-002")
    args = train_testbed.make_args()
    record, exit_code = train_testbed.run_train(args)
    # WP-002 ends up in step-7-blocked
    train_testbed.assert_index_flip("WP-002", "step-7-blocked")
    # WP-001 + WP-003 should NOT be flipped to step-7-blocked by the
    # rebase-conflict path (their merges proceed normally).
    assert not any(
        f["wp"] in ("WP-001", "WP-003") and f["to_status"] == "step-7-blocked"
        for f in train_testbed.index_flips
    ), (
        f"Unexpected step-7-blocked flips on healthy WPs: "
        f"{train_testbed.index_flips}"
    )


# ─── Test 3: bundled-tip CI red ─────────────────────────────────────


def test_bundled_tip_ci_red_pauses_train_without_merging(train_testbed):
    """CI returns failed on the bundled tip.

    Expected: train state moves to ``paused`` (founder action: inspect,
    fix, resume or abort). No merges. No reverts. The train YAML record
    has outcome=paused.
    """
    _seed_three_wp_bundle(train_testbed)
    train_testbed.fail_ci()
    args = train_testbed.make_args()
    record, exit_code = train_testbed.run_train(args)
    # No merges should have occurred — dev unchanged
    train_testbed.assert_not_merged_on_dev("WP-001")
    train_testbed.assert_not_merged_on_dev("WP-002")
    train_testbed.assert_not_merged_on_dev("WP-003")
    # No revert calls (nothing was merged → nothing to revert)
    assert not train_testbed.revert_calls, (
        f"Unexpected revert when CI red prevented all merges: "
        f"{train_testbed.revert_calls}"
    )
    # Outcome should be paused (not success, not blocker)
    assert record.get("outcome") == "paused", (
        f"Expected outcome=paused on CI-red; got {record.get('outcome')}. "
        f"Record: {record}"
    )


# ─── Test 4: bundled-tip CI timeout ─────────────────────────────────


def test_bundled_tip_ci_timeout_pauses_train_without_merging(train_testbed):
    """CI poll times out before reaching a verdict.

    Same recovery shape as CI-red: pause, no merges.
    """
    _seed_three_wp_bundle(train_testbed)
    train_testbed.timeout_ci()
    args = train_testbed.make_args()
    record, exit_code = train_testbed.run_train(args)
    train_testbed.assert_not_merged_on_dev("WP-001")
    train_testbed.assert_not_merged_on_dev("WP-002")
    train_testbed.assert_not_merged_on_dev("WP-003")
    assert not train_testbed.revert_calls
    assert record.get("outcome") == "paused", (
        f"Expected outcome=paused on CI-timeout; got {record.get('outcome')}. "
        f"Record: {record}"
    )


# ─── Test 5: mid-batch merge failure (HD-003 path) ──────────────────


def test_mid_batch_merge_failure_routes_through_revert_path(train_testbed):
    """Inject merge failure on WP-003 after WP-001 + WP-002 merge OK.

    This is the path HD-003 added: per-merge try/except routes to
    `_handle_post_merge_failure` with the partial bundle. The two
    successful merges are reverted; their branches are restored; all
    three WPs flip to step-7-blocked.
    """
    _seed_three_wp_bundle(train_testbed)
    train_testbed.fail_merge("WP-003")
    args = train_testbed.make_args()
    record, exit_code = train_testbed.run_train(args)
    # Revert was called exactly once with the partial bundle
    assert len(train_testbed.revert_calls) == 1, (
        f"Expected exactly one revert call; got "
        f"{len(train_testbed.revert_calls)}: {train_testbed.revert_calls}"
    )
    bundle = train_testbed.revert_calls[0]["bundle"]
    # WP-001, WP-002 have merge_sha_on_dev populated; WP-003 does not
    merged = [e for e in bundle if e.get("merge_sha_on_dev")]
    assert {e["wp"] for e in merged} == {"WP-001", "WP-002"}, (
        f"Expected merged subset = WP-001+WP-002; got {[e['wp'] for e in merged]}"
    )
    # All three end up blocked
    for wp in ("WP-001", "WP-002", "WP-003"):
        train_testbed.assert_index_flip(wp, "step-7-blocked")
    # Exit code 1 — terminal failure with revert
    assert exit_code == 1, f"Expected exit 1 on HD-003 path; got {exit_code}"
    assert record.get("outcome") == "blocker"


# ─── Test 6: deploy timeout → paused ────────────────────────────────


def test_deploy_timeout_pauses_train_without_revert(train_testbed):
    """Deploy poll times out (workflow still spinning, not yet a verdict).

    Recovery: pause. The founder checks the deploy URL; resumes if it
    eventually went green, aborts if it failed. No revert in this path.
    """
    _seed_three_wp_bundle(train_testbed)
    train_testbed.timeout_deploy()
    args = train_testbed.make_args()
    record, exit_code = train_testbed.run_train(args)
    # Merges DID land (the deploy is post-merge)
    train_testbed.assert_merged_on_dev("WP-001")
    train_testbed.assert_merged_on_dev("WP-002")
    train_testbed.assert_merged_on_dev("WP-003")
    # No revert on timeout (the deploy may still complete)
    assert not train_testbed.revert_calls, (
        f"Expected no revert on deploy timeout; got {train_testbed.revert_calls}"
    )
    assert record.get("outcome") == "paused", (
        f"Expected outcome=paused; got {record.get('outcome')}"
    )


# ─── Test 7: deploy explicit failure → ADR-212 revert ──────────────


def test_deploy_explicit_failure_triggers_revert_path(train_testbed):
    """Deploy workflow returns conclusion=failed. ADR-212 revert runs."""
    _seed_three_wp_bundle(train_testbed)
    train_testbed.fail_deploy()
    args = train_testbed.make_args()
    record, exit_code = train_testbed.run_train(args)
    # Merges happened, then revert ran
    assert len(train_testbed.revert_calls) == 1, (
        f"Expected one revert; got {len(train_testbed.revert_calls)}"
    )
    # Bundle passed to revert has all 3 with merge_sha_on_dev populated
    bundle = train_testbed.revert_calls[0]["bundle"]
    merged = [e for e in bundle if e.get("merge_sha_on_dev")]
    assert len(merged) == 3, (
        f"Expected all 3 WPs in merged subset; got {len(merged)}: "
        f"{[(e['wp'], e.get('merge_sha_on_dev')) for e in bundle]}"
    )
    for wp in ("WP-001", "WP-002", "WP-003"):
        train_testbed.assert_index_flip(wp, "step-7-blocked")
    assert record.get("outcome") == "blocker"
    assert exit_code == 1


# ─── Test 8: health unhealthy → ADR-212 revert ─────────────────────


def test_health_unhealthy_triggers_revert_path(train_testbed):
    """Health endpoint never returns 200 — train reverts the batch."""
    _seed_three_wp_bundle(train_testbed)
    train_testbed.fail_health()
    args = train_testbed.make_args(staging_url="https://staging.invalid")
    record, exit_code = train_testbed.run_train(args)
    assert len(train_testbed.revert_calls) == 1, (
        f"Expected one revert; got {len(train_testbed.revert_calls)}"
    )
    for wp in ("WP-001", "WP-002", "WP-003"):
        train_testbed.assert_index_flip(wp, "step-7-blocked")
    assert record.get("outcome") == "blocker"


# ─── Test 9: smoke FAIL → ADR-212 revert ───────────────────────────


def test_smoke_fail_triggers_revert_path(train_testbed):
    """Smoke command returns non-zero exit. Revert path runs."""
    _seed_three_wp_bundle(train_testbed)
    train_testbed.fail_smoke()
    args = train_testbed.make_args(smoke_cmd="echo running")
    record, exit_code = train_testbed.run_train(args)
    assert len(train_testbed.revert_calls) == 1, (
        f"Expected one revert; got {len(train_testbed.revert_calls)}"
    )
    for wp in ("WP-001", "WP-002", "WP-003"):
        train_testbed.assert_index_flip(wp, "step-7-blocked")
    assert record.get("outcome") == "blocker"


# ─── HD-001 RED tests — prove the cmd_run split happened ────────────


def test_phase_functions_exist():
    """HD-001 RED — _plan_phase / _commit_phase / _verify_phase exist
    as importable module-level functions on wpx-train.

    Before HD-001 these don't exist; cmd_run is a single ~415 LOC monolith.
    After HD-001 they're the testable unit-of-work boundaries the merge-
    queue spike's PARTIAL recommendation needs as the strategy-dispatcher
    seam.
    """
    wpx = _load_wpx_train_module()
    for name in ("_plan_phase", "_commit_phase", "_verify_phase",
                 "_commit_via_rebase_loop", "_finalise_success",
                 "_finalise_awaiting_gates"):
        assert hasattr(wpx, name), (
            f"HD-001: expected wpx-train.{name} after phase-split refactor; "
            f"missing means the decomposition didn't ship."
        )
        assert callable(getattr(wpx, name)), (
            f"HD-001: wpx-train.{name} exists but isn't callable"
        )


def test_cmd_run_shrunk_after_phase_split():
    """HD-001 RED — cmd_run is a thin orchestrator post-refactor.

    Pre-HD-001 cmd_run body is ~415 LOC. Post-HD-001 it shrinks to
    ~100 LOC of orchestration: discovery, batch packing, train-state
    init, three phase-function calls, finalise, exception handler.
    Anything substantially larger means the decomposition leaked.
    """
    import inspect
    wpx = _load_wpx_train_module()
    src = inspect.getsource(wpx.cmd_run)
    loc = sum(
        1 for ln in src.splitlines()
        if ln.strip() and not ln.strip().startswith("#")
    )
    assert loc < 130, (
        f"cmd_run is {loc} non-blank non-comment LOC; expected <130 "
        f"post-HD-001. The phase-split refactor should have moved most "
        f"of the body into _plan_phase / _commit_phase / _verify_phase."
    )


# ─── HD-007 RED tests — gate-handoff boundary semantics ─────────────


def test_verify_phase_pauses_at_gate_boundary_when_handoff_enabled(train_testbed):
    """HD-007 RED — with --enable-gate-handoff, the train stops at
    phase=verifying_gates after deploy/health/smoke green, emitting
    outcome=awaiting_gates instead of going directly to terminal success.

    Calling LLM session reads the gate_handoff envelope, dispatches
    Step 10.5 + Step 11, then invokes `mark-gates-complete` to finalise.
    """
    _seed_three_wp_bundle(train_testbed)
    args = train_testbed.make_args(enable_gate_handoff=True)
    record, exit_code = train_testbed.run_train(args)
    assert exit_code == 0, (
        f"Gate handoff is success-pending (exit 0), not failure. "
        f"Got exit={exit_code}; record={record}"
    )
    assert record.get("outcome") == "awaiting_gates", (
        f"Expected outcome=awaiting_gates with --enable-gate-handoff; "
        f"got {record.get('outcome')}. Record: {record}"
    )
    # All merges should have landed — the gate boundary is post-merge.
    train_testbed.assert_merged_on_dev("WP-001")
    train_testbed.assert_merged_on_dev("WP-002")
    train_testbed.assert_merged_on_dev("WP-003")


def test_mark_gates_complete_finalises_train_to_success(train_testbed):
    """HD-007 RED — `wpx-train mark-gates-complete` promotes a train
    paused at verifying_gates to terminal phase=success.

    HD-010 tightening — also asserts the awaiting-gates record fields
    (started_at, batch_size, bundle, deploy_url) survive the merge into
    the terminal record. The previous contract checked only ``outcome ==
    "success"`` and missed silent data loss.
    """
    _seed_three_wp_bundle(train_testbed)
    args = train_testbed.make_args(enable_gate_handoff=True)
    record, exit_code = train_testbed.run_train(args)
    assert record.get("outcome") == "awaiting_gates"
    train_id = record.get("train_id")
    assert train_id, f"Train ID missing from record: {record}"

    # Sanity: the awaiting-gates stub was written with the full record.
    awaiting_record = train_testbed.read_latest_train_record()
    assert awaiting_record.get("outcome") == "awaiting_gates"
    assert awaiting_record.get("started_at"), (
        f"awaiting-gates stub missing started_at: {awaiting_record}"
    )
    assert awaiting_record.get("batch_size") == "3" or \
        awaiting_record.get("batch_size") == 3, (
        f"awaiting-gates stub missing batch_size=3: {awaiting_record}"
    )
    assert awaiting_record.get("bundle"), (
        f"awaiting-gates stub missing bundle list: {awaiting_record}"
    )
    initial_started_at = awaiting_record["started_at"]
    initial_batch_size = awaiting_record["batch_size"]
    initial_bundle = awaiting_record["bundle"]

    wpx = _load_wpx_train_module()
    mark_args = SimpleNamespace(
        project=train_testbed.project,
        repo_root=str(train_testbed.workspace),
        repo="acme/test-repo",
        train_id=train_id,
        gate_findings=None,
        critical_found=False,
    )
    try:
        wpx.cmd_mark_gates_complete(mark_args)
        mgc_exit = 0
    except SystemExit as exc:
        mgc_exit = int(exc.code or 0)
    assert mgc_exit == 0, (
        f"mark-gates-complete should exit 0 on clean gates; got {mgc_exit}"
    )
    final = train_testbed.read_latest_train_record()
    assert final.get("outcome") == "success", (
        f"Expected outcome=success after mark-gates-complete; got "
        f"{final.get('outcome')}. Record: {final}"
    )
    # HD-010 — the historical archive must NOT be truncated to a 2-field
    # stub. bundle / started_at / batch_size are the audit-trail fields
    # downstream tools (find_wp_merge_sha, backfill-code-review,
    # backfill-gates) consume. Losing them silently is data corruption.
    assert final.get("started_at") == initial_started_at, (
        f"HD-010 — started_at was truncated by mark-gates-complete. "
        f"Before: {initial_started_at!r}; after: {final.get('started_at')!r}. "
        f"Full record: {final}"
    )
    assert final.get("batch_size") == initial_batch_size, (
        f"HD-010 — batch_size was truncated by mark-gates-complete. "
        f"Before: {initial_batch_size!r}; after: {final.get('batch_size')!r}"
    )
    assert final.get("bundle") == initial_bundle, (
        f"HD-010 — bundle list was truncated by mark-gates-complete. "
        f"Before: {initial_bundle!r}; after: {final.get('bundle')!r}"
    )
    # completed_at must be added by mark-gates-complete.
    assert final.get("completed_at"), (
        f"mark-gates-complete must record completed_at; got {final}"
    )


def test_mark_gates_complete_preserves_bundle_and_deploy_fields(train_testbed):
    """HD-010 RED — mark-gates-complete must preserve bundle, started_at,
    batch_size, and per-WP merge_sha_on_dev entries from the
    awaiting-gates record stub.

    Designed to fail BEFORE the fix (where the bare-except swallowed
    ImportError, leaving record={}, and write_train_run_record truncated
    the file to outcome + completed_at). Passes AFTER the fix
    (read_train_run_record + merge-into-existing).
    """
    _seed_three_wp_bundle(train_testbed)
    args = train_testbed.make_args(enable_gate_handoff=True)
    record, _ = train_testbed.run_train(args)
    assert record.get("outcome") == "awaiting_gates"
    train_id = record.get("train_id")

    # The awaiting-gates stub on disk must have the full payload before
    # mark-gates-complete runs.
    awaiting_text = (train_testbed.train_runs_dir / f"{train_id}.yaml").read_text()
    assert "bundle:" in awaiting_text, (
        f"awaiting-gates stub missing bundle: {awaiting_text}"
    )
    assert "started_at:" in awaiting_text, (
        f"awaiting-gates stub missing started_at: {awaiting_text}"
    )
    assert "batch_size:" in awaiting_text, (
        f"awaiting-gates stub missing batch_size: {awaiting_text}"
    )
    # The 3-WP bundle should expose at least one merge_sha_on_dev
    # (the testbed FakeGHClient.merge() returns a SHA for every merge).
    assert "merge_sha_on_dev:" in awaiting_text

    wpx = _load_wpx_train_module()
    mark_args = SimpleNamespace(
        project=train_testbed.project,
        repo_root=str(train_testbed.workspace),
        repo="acme/test-repo",
        train_id=train_id,
        gate_findings=None,
        critical_found=False,
    )
    try:
        wpx.cmd_mark_gates_complete(mark_args)
    except SystemExit:
        pass

    final_text = (train_testbed.train_runs_dir / f"{train_id}.yaml").read_text()
    assert 'outcome: "success"' in final_text, (
        f"mark-gates-complete must record outcome=success: {final_text}"
    )
    # HD-010 — every field below MUST survive the finalise call.
    for field in ("bundle:", "started_at:", "batch_size:",
                  "merge_sha_on_dev:"):
        assert field in final_text, (
            f"HD-010: {field!r} was truncated by mark-gates-complete. "
            f"The historical archive is now incomplete; downstream tools "
            f"(find_wp_merge_sha, backfill-code-review, backfill-gates) "
            f"will fail to recover the bundle's WP→SHA mapping.\n"
            f"Final record:\n{final_text}"
        )


def test_mark_gates_complete_emits_pending_step12_checklist(train_testbed, capsys):
    """#75 RED — on the clean-success path, the result envelope must carry a
    `pending_step12` checklist of the shipped WPs + their merged branches.

    The batched gate-handoff path never runs the per-WP Step 12 wrap
    (acceptance evidence + INDEX flip + worktree removal + branch delete) the
    legacy per-WP path does — the train doesn't own the executor worktrees.
    Emitting the checklist lets the calling run-all session drive the wrap
    deterministically (Step 12.6) instead of reconstructing the batch by hand,
    which is the repeated toil this lesson captured.
    """
    import json

    wps = _seed_three_wp_bundle(train_testbed)
    args = train_testbed.make_args(enable_gate_handoff=True)
    record, _ = train_testbed.run_train(args)
    assert record.get("outcome") == "awaiting_gates"
    train_id = record.get("train_id")

    capsys.readouterr()  # drain run_train's output

    wpx = _load_wpx_train_module()
    mark_args = SimpleNamespace(
        project=train_testbed.project,
        repo_root=str(train_testbed.workspace),
        repo="acme/test-repo",
        train_id=train_id,
        gate_findings=None,
        critical_found=False,
    )
    try:
        wpx.cmd_mark_gates_complete(mark_args)
    except SystemExit as exc:
        assert int(exc.code or 0) == 0

    raw = json.loads(capsys.readouterr().out.strip())
    assert raw.get("ok") is True, f"mark-gates-complete should succeed: {raw}"
    envelope = raw["data"]["result"]
    assert envelope.get("outcome") == "success"

    pending = envelope.get("pending_step12")
    assert pending is not None, (
        "clean-success envelope must carry a pending_step12 checklist so the "
        f"calling session can run the per-WP Step 12 wrap. Envelope: {envelope}"
    )
    # Every shipped WP must appear, each with a non-empty branch to wrap +
    # delete.
    assert {e["wp"] for e in pending} == set(wps), (
        f"pending_step12 must list all shipped WPs {wps}; got {pending}"
    )
    assert all(e.get("branch") for e in pending), (
        f"each pending_step12 entry needs a branch to delete; got {pending}"
    )
    assert envelope.get("next_action"), (
        "envelope must name the Step 12.6 follow-on action"
    )


def test_mark_gates_complete_with_critical_marks_gate_blocker(train_testbed):
    """HD-007 RED — --critical-found records gate_blocker (phase=failed)
    without invoking ADR-212 revert. The gate dispatchers already wrote
    BLOCKERs + drafted remediation WPs; the train just records the
    outcome.

    HD-010 tightening — also asserts the awaiting-gates record fields
    survive the gate-blocker merge (same data-loss class as the success
    path).
    """
    _seed_three_wp_bundle(train_testbed)
    args = train_testbed.make_args(enable_gate_handoff=True)
    record, exit_code = train_testbed.run_train(args)
    train_id = record.get("train_id")
    awaiting_record = train_testbed.read_latest_train_record()
    initial_bundle = awaiting_record["bundle"]
    initial_started_at = awaiting_record["started_at"]

    wpx = _load_wpx_train_module()
    mark_args = SimpleNamespace(
        project=train_testbed.project,
        repo_root=str(train_testbed.workspace),
        repo="acme/test-repo",
        train_id=train_id,
        gate_findings="/tmp/findings.json",
        critical_found=True,
    )
    try:
        wpx.cmd_mark_gates_complete(mark_args)
        mgc_exit = 0
    except SystemExit as exc:
        mgc_exit = int(exc.code or 0)
    assert mgc_exit == 1, (
        f"mark-gates-complete --critical-found should exit 1; got {mgc_exit}"
    )
    final = train_testbed.read_latest_train_record()
    assert final.get("outcome") == "gate_blocker", (
        f"Expected outcome=gate_blocker on --critical-found; got "
        f"{final.get('outcome')}. Record: {final}"
    )
    # HD-010 — same data-loss class applies to the gate-blocker path.
    assert final.get("started_at") == initial_started_at, (
        f"HD-010 — started_at was truncated on gate-blocker path. "
        f"Before: {initial_started_at!r}; after: {final.get('started_at')!r}"
    )
    assert final.get("bundle") == initial_bundle, (
        f"HD-010 — bundle list was truncated on gate-blocker path. "
        f"Before: {initial_bundle!r}; after: {final.get('bundle')!r}"
    )
    # gate_findings_path must be threaded into the historical record.
    assert final.get("gate_findings_path") == "/tmp/findings.json", (
        f"--gate-findings path must be recorded; got "
        f"{final.get('gate_findings_path')!r}. Record: {final}"
    )
    # Critically: no ADR-212 revert ran. Production stays live; founder
    # owns the remediation cycle.
    assert not train_testbed.revert_calls, (
        f"--critical-found must NOT invoke ADR-212 revert. Got revert "
        f"calls: {train_testbed.revert_calls}"
    )
