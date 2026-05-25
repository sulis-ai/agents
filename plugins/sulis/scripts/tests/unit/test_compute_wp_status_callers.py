"""HD-008 Commit B — tests for migrated callers of compute_wp_status.

Covers:

- `find_eligible_branches(paths=...)` uses computed status, so a WP
  whose stored cell says `done` but whose computed status is
  `step-7-complete` (revert / never-on-dev) is re-considered for
  eligibility instead of being skipped as already-done.
- `find_eligible_branches(paths=...)` uses computed status for the
  dependency-merged check, so a WP cannot ride a train when its
  dep's computed status is not `done` even if the stored cell lies.
- `find_eligible_branches` without `paths` preserves the pre-HD-008
  behaviour (test-only path; the historical eligibility test suite
  exercises this).
- `flip_index_status_via_cli` emits a DeprecationWarning on every
  call.
- `cmd_doctor`'s drift detection deliberately keeps using the
  lower-level `find_wp_merge_sha` + `is_sha_on_branch` primitives
  (NOT `compute_wp_status`) because the doctor MUST distinguish
  transient API errors from "SHA is not on dev"; `compute_wp_status`
  is conservative and falls back to stored on transient errors,
  which is right for eligibility but wrong for drift reporting.
  This is regression-checked by the existing
  `test_wpx_train_drift_detection.py` suite — no new doctor test is
  needed here.
"""
from __future__ import annotations

import sys
import warnings
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

from _wpxlib import (  # noqa: E402
    WPRow,
    WpxPaths,
    find_eligible_branches,
    flip_index_status_via_cli,
)


# ─── helpers ───────────────────────────────────────────────────────────


def _make_paths(tmp_path: Path, project: str = "demo") -> WpxPaths:
    paths = WpxPaths(repo_root=tmp_path, project=project)
    paths.wp_dir.mkdir(parents=True, exist_ok=True)
    paths.train_runs_dir.mkdir(parents=True, exist_ok=True)
    return paths


def _make_wp_file(wp_dir: Path, wp_id: str, slug: str) -> None:
    (wp_dir / f"{wp_id}-{slug}.md").write_text(
        f"---\nid: {wp_id}\n---\n", encoding="utf-8",
    )


# ─── migrated find_eligible_branches ──────────────────────────────────


def test_find_eligible_uses_computed_status_when_paths_provided(tmp_path):
    """A WP whose stored cell says `done` but whose origin branch
    exists with no merge SHA (reverted) computes to `step-7-complete`
    and becomes a candidate for the next train."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-001", "ready")

    wps = [WPRow(id="WP-001", title="Ready", primitive="create",
                 status="done")]

    with patch("_wpxlib.is_sha_on_branch") as mock_on_branch, \
         patch("_wpxlib._gh_branch_exists") as mock_branch_exists, \
         patch("_wpxlib._gh_branch_ci_green") as mock_ci:
        # No merge SHA known (no train records) → case 1 falls through.
        # No in-flight train → case 2 falls through.
        # Origin branch exists → computed = step-7-complete.
        mock_on_branch.return_value = False
        mock_branch_exists.return_value = True
        mock_ci.return_value = True

        results = find_eligible_branches(
            wps, "acme/repo", paths.wp_dir,
            paths=paths, base_branch="dev",
        )

    # WP-001's stored cell said done; the pre-HD-008 code would have
    # SKIPPED it via the candidate-skip check. Under HD-008, computed
    # value step-7-complete makes it eligible.
    assert len(results) == 1
    assert results[0].wp == "WP-001"
    assert results[0].eligible is True


def test_find_eligible_uses_computed_status_for_dep_check(tmp_path):
    """A WP's dependency whose stored cell says `done` but whose
    computed value is `step-7-complete` (reverted) blocks the
    downstream WP from boarding the train."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-DEP", "dep")
    _make_wp_file(paths.wp_dir, "WP-DOWN", "down")

    wps = [
        WPRow(id="WP-DEP", title="Dep", primitive="create", status="done"),
        WPRow(id="WP-DOWN", title="Downstream", primitive="create",
              status="step-7-complete", depends_on=["WP-DEP"]),
    ]

    with patch("_wpxlib.is_sha_on_branch") as mock_on_branch, \
         patch("_wpxlib._gh_branch_exists") as mock_branch_exists, \
         patch("_wpxlib._gh_branch_ci_green") as mock_ci:
        mock_on_branch.return_value = False  # no merge SHA on dev
        mock_branch_exists.return_value = True
        mock_ci.return_value = True

        results = find_eligible_branches(
            wps, "acme/repo", paths.wp_dir,
            paths=paths, base_branch="dev",
        )

    # Find WP-DOWN's result
    down = next(r for r in results if r.wp == "WP-DOWN")
    assert down.eligible is False
    assert "WP-DEP" in down.reason
    assert "dependencies not merged" in down.reason


def test_find_eligible_without_paths_preserves_pre_hd008_behaviour(tmp_path):
    """Calling find_eligible_branches without `paths` continues to read
    `wp.status` from the INDEX parse — no network access, no
    compute_wp_status, no computed-vs-stored second-guessing. This
    is the historical signature exercised by the in-memory
    eligibility test suite (test_wpx_train_eligibility.py)."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-001", "ready")

    wps = [WPRow(id="WP-001", title="Ready", primitive="create",
                 status="step-7-complete")]

    # Mocks would fire if computed status were taking the network path
    # — verify they don't by setting them to raise.
    def _should_not_be_called(*_args, **_kwargs):
        raise AssertionError(
            "compute_wp_status path entered without --paths — backward "
            "compatibility broken"
        )

    with patch("_wpxlib.is_sha_on_branch", side_effect=_should_not_be_called), \
         patch("_wpxlib._gh_branch_exists") as mock_branch_exists, \
         patch("_wpxlib._gh_branch_ci_green") as mock_ci:
        mock_branch_exists.return_value = True
        mock_ci.return_value = True

        # No `paths` kwarg → backward-compat path
        results = find_eligible_branches(
            wps, "acme/repo", paths.wp_dir,
        )

    assert len(results) == 1
    assert results[0].wp == "WP-001"
    assert results[0].eligible is True


# ─── flip_index_status_via_cli deprecation ────────────────────────────


def test_flip_index_status_via_cli_emits_deprecation_warning(tmp_path):
    """HD-008 deprecates flip_index_status_via_cli. Calling it MUST
    emit a DeprecationWarning so legacy callers surface in CI logs."""
    paths = _make_paths(tmp_path)
    scripts_dir = SCRIPTS_DIR  # the actual wpx-index script lives here

    with warnings.catch_warnings(record=True) as captured:
        warnings.simplefilter("always")
        # Call with a non-existent wp_id; the subprocess will fail but
        # the deprecation warning fires before the shell-out.
        ok, _msg = flip_index_status_via_cli(
            scripts_dir, paths, "WP-NONE", "blocked",
        )

    deprecation_warnings = [
        w for w in captured if issubclass(w.category, DeprecationWarning)
    ]
    assert len(deprecation_warnings) >= 1
    assert "HD-008" in str(deprecation_warnings[0].message)
    # The shell-out fails because INDEX.md doesn't exist; we don't care
    # about that — we just care the warning fires.
    assert ok is False


# Note: `cmd_doctor`'s drift detection is regression-tested by the
# existing scripts/tests/unit/test_wpx_train_drift_detection.py suite
# (covering find_wp_merge_sha + is_sha_on_branch). Since HD-008's
# migration deliberately keeps the doctor on those lower-level
# primitives (per the rationale in cmd_doctor's docstring), no new
# doctor test is added here — the existing tests still apply unchanged.
