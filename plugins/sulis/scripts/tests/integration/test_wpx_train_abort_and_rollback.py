"""Regression tests for issue #62 — two failure-recovery bugs in wpx-train.

Bug 1 — `wpx-train abort` crashes on a pre-merge (rebasing-phase) train
with ``NameError: name 'TRAIN_HELD_STATUS' is not defined`` because the
constant is used in cmd_abort but missing from the `from _wpxlib import`
block. The supported recovery path is therefore broken.

Bug 2 — when `wpx-train run` errors during the `rebasing` phase (before
any merge SHA is produced), it leaves the in-flight `*.state.json`
behind. That stranded state file keeps the bundle WPs computed as
`step-7-shipping`, so the next `run` reports `nothing_to_pack` even
though the INDEX cells correctly say `step-7-complete`.

These tests use the TrainTestbed (HD-002) the same way the failure-path
suite does: a real local bare git repo + FakeGHClient. They are RED
against current dev (Bug 1 NameErrors; Bug 2 strands `step-7-shipping`)
and GREEN once the import is added and `run` cleans up its state file on
a pre-merge error.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest  # noqa: F401 (used implicitly via the train_testbed fixture)

import _wpxlib
from _wpxlib import (
    _in_flight_train_has_wp,
    compute_wp_status,
    init_train_state,
    update_train_phase,
    train_state_path,
)
from testbed import _load_wpx_train_module

# The `train_testbed` fixture is re-exported from
# scripts/tests/integration/conftest.py; pytest discovers it automatically.


def _seed_two_wp_bundle(testbed) -> list[str]:
    """Seed WP-001 + WP-002 at step-7-complete with one commit each."""
    wps = ["WP-001", "WP-002"]
    for wp in wps:
        slug = wp.lower().removeprefix("wp-")
        testbed.seed_wp_branch(wp, slug)
    testbed.seed_index_with_wps([(wp, f"{wp} title") for wp in wps])
    return wps


def _abort_args(testbed, train_id: str) -> SimpleNamespace:
    return SimpleNamespace(
        project=testbed.project,
        repo_root=str(testbed.workspace),
        repo="acme/test-repo",
        train_id=train_id,
    )


# ─── Bug 1 — abort works on a pre-merge rebasing-phase train ─────────


def test_abort_pre_merge_rebasing_train_does_not_nameerror(train_testbed):
    """RED on current dev: cmd_abort references TRAIN_HELD_STATUS which is
    not imported → NameError. GREEN once the import is added.

    Set up a train parked in the pre-merge `rebasing` phase (no merge
    SHAs landed), run `wpx-train abort`, and assert:
      - it exits 0 (no NameError),
      - the bundle WPs are flipped to step-7-held (pre-merge convention),
      - the in-flight state file is cleaned up so the WPs are no longer
        reported in-flight (step-7-shipping).
    """
    wps = _seed_two_wp_bundle(train_testbed)
    train_id = "train-2026-05-28T120000Z"
    initial_bundle = [
        {"wp": wp, "branch": train_testbed._branch_for(wp),
         "pre_train_sha": None}
        for wp in wps
    ]
    init_train_state(
        train_testbed.train_runs_dir, train_id, initial_bundle, {},
    )
    # Park it pre-merge (rebasing): no merge SHA produced.
    update_train_phase(
        train_state_path(train_testbed.train_runs_dir, train_id), "rebasing",
    )

    # Sanity: while the in-flight state exists, the WPs read as in-flight.
    assert _in_flight_train_has_wp(train_testbed.train_runs_dir, "WP-001")

    wpx = _load_wpx_train_module()
    args = _abort_args(train_testbed, train_id)
    try:
        wpx.cmd_abort(args)
        exit_code = 0
    except SystemExit as exc:
        exit_code = int(exc.code or 0)
    # NameError would propagate here (not a SystemExit) and fail the test.

    assert exit_code == 0, (
        f"Expected abort to exit 0 on a pre-merge rebasing train; got "
        f"{exit_code}"
    )
    # Pre-merge abort flips bundle WPs to step-7-held.
    for wp in wps:
        train_testbed.assert_index_flip(wp, "step-7-held")
    # The in-flight state file is cleaned up — WPs no longer in-flight.
    for wp in wps:
        assert not _in_flight_train_has_wp(
            train_testbed.train_runs_dir, wp,
        ), f"{wp} still reported in-flight after abort"


# ─── Bug 2 — run leaves WP status unchanged on a pre-merge error ─────


def test_run_pre_merge_error_does_not_strand_step_7_shipping(train_testbed):
    """RED on current dev: a `run` that errors during rebasing (before any
    merge) leaves the in-flight state file behind, stranding the bundle
    WPs in step-7-shipping → the next run reports nothing_to_pack.

    GREEN once `run` cleans up its in-flight state on a pre-merge error.
    The invariant: if no merge SHA was produced, the run leaves WP
    statuses exactly as it found them (step-7-complete → eligible).
    """
    wps = _seed_two_wp_bundle(train_testbed)

    # Before the run, the WPs are step-7-complete (branch pushed, no train).
    for wp in wps:
        assert compute_wp_status(
            wp, _wpxlib.WpxPaths(
                repo_root=train_testbed.workspace,
                project=train_testbed.project,
            ),
            "acme/test-repo", base_branch="dev",
        ) == "step-7-complete", f"{wp} not eligible before run"

    # Inject a rebasing-phase error: _gh_ref_sha (called to compute the
    # rebase-onto SHA, before any branch is rebased or merged) raises.
    train_testbed.gh.force_fail["ref_sha"] = RuntimeError(
        "gh ref-sha failed for dev: simulated 404",
    )

    args = train_testbed.make_args()
    record, exit_code = train_testbed.run_train(args)

    # The run errored before any merge — nothing landed on dev.
    train_testbed.assert_not_merged_on_dev("WP-001")
    train_testbed.assert_not_merged_on_dev("WP-002")
    assert record.get("outcome") == "error", (
        f"Expected a pre-merge error outcome; got {record.get('outcome')}. "
        f"Record: {record}"
    )

    # Clear the injected failure so the post-run status computation +
    # the second run see a healthy gh client again.
    train_testbed.gh.force_fail.pop("ref_sha", None)

    # The invariant: WPs are NOT stranded in step-7-shipping. The
    # in-flight state file must have been cleaned up on the error.
    for wp in wps:
        assert not _in_flight_train_has_wp(
            train_testbed.train_runs_dir, wp,
        ), (
            f"{wp} stranded in step-7-shipping after a pre-merge error — "
            f"in-flight state file was not cleaned up"
        )
        assert compute_wp_status(
            wp, _wpxlib.WpxPaths(
                repo_root=train_testbed.workspace,
                project=train_testbed.project,
            ),
            "acme/test-repo", base_branch="dev",
        ) == "step-7-complete", (
            f"{wp} computed status is not step-7-complete after a "
            f"pre-merge error — it is stranded"
        )

    # A subsequent run must therefore still see the WPs as eligible and
    # NOT report nothing_to_pack.
    record2, _ = train_testbed.run_train(train_testbed.make_args())
    assert record2.get("outcome") != "nothing_to_pack", (
        f"Second run reported nothing_to_pack — WPs were stranded by the "
        f"first run's failure. Record: {record2}"
    )
