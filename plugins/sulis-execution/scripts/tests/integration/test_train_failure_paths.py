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
"""

from __future__ import annotations

import pytest  # noqa: F401 (used implicitly via parametrize, etc.)

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
