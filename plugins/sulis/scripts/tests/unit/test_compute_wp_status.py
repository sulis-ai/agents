"""Unit tests for HD-008 — `compute_wp_status`.

The function returns the computed status for a WP from authoritative
sources (origin git state + train-runs/ records), falling back to the
caller-supplied `stored_status` for operator-intent states that have
no authoritative-state correlate.

These tests pin the four resolution cases:

1. done — merge SHA recorded AND on origin/<base_branch>.
2. step-7-shipping — in-flight `*.state.json` lists the WP in bundle.
3. step-7-complete — origin branch exists AND cases 1 + 2 are False.
4. fall-through — none of the above; returns stored_status (or
   "pending" when unset).

Plus auxiliary behaviour:

5. `is_sha_on_branch` returning False (revert / not pushed) downgrades
   from done to step-7-complete when the origin branch exists, or to
   the fall-through when it doesn't.
6. `_in_flight_train_has_wp` ignores terminal-phase state files,
   ignores corrupt state files, returns False when train-runs is
   missing.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

from _wpxlib import (  # noqa: E402
    WpxPaths,
    _in_flight_train_has_wp,
    compute_wp_status,
)


# ─── Fixture helpers ───────────────────────────────────────────────────


def _make_paths(tmp_path: Path, project: str = "demo") -> WpxPaths:
    """Build a WpxPaths anchored at tmp_path/{repo_root}.

    `WpxPaths` only takes (repo_root, project); wp_dir / train_runs_dir
    are derived properties under `.architecture/{project}/`. We pre-create
    those directories so the helpers we test (which glob inside them)
    have something to find.
    """
    paths = WpxPaths(repo_root=tmp_path, project=project)
    paths.wp_dir.mkdir(parents=True, exist_ok=True)
    paths.train_runs_dir.mkdir(parents=True, exist_ok=True)
    return paths


def _make_wp_file(wp_dir: Path, wp_id: str, slug: str = "demo-slug") -> Path:
    """Create a minimal WP file so _wp_slug_from_file can derive a branch."""
    path = wp_dir / f"{wp_id}-{slug}.md"
    path.write_text(f"---\nid: {wp_id}\ntitle: demo\n---\nbody\n",
                    encoding="utf-8")
    return path


def _write_state_json(
    train_runs_dir: Path, train_id: str, phase: str, bundle: list[dict],
) -> Path:
    """Write an in-flight train state JSON."""
    path = train_runs_dir / f"{train_id}.state.json"
    path.write_text(json.dumps({
        "train_id": train_id,
        "phase": phase,
        "bundle": bundle,
    }), encoding="utf-8")
    return path


def _write_yaml_record(
    train_runs_dir: Path, train_id: str, bundle: list[dict],
) -> Path:
    """Write a terminal-train YAML record (mimics write_train_run_record)."""
    path = train_runs_dir / f"{train_id}.yaml"
    lines = [f"train_id: {train_id}", "bundle:"]
    for item in bundle:
        lines.append(f"  - wp: {item.get('wp', '')}")
        for k in ("branch", "pre_train_sha", "rebased_to_sha",
                  "merge_sha_on_dev"):
            v = item.get(k)
            if v is None:
                lines.append(f"    {k}: null")
            else:
                lines.append(f"    {k}: {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ─── compute_wp_status — Case 1: done ──────────────────────────────────


def test_returns_done_when_merge_sha_on_branch(tmp_path):
    """Case 1: train YAML record exists with merge_sha; SHA is on dev."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-001")
    _write_yaml_record(
        paths.train_runs_dir, "train-001",
        [{"wp": "WP-001", "merge_sha_on_dev": "abc12345"}],
    )
    with patch("_wpxlib.is_sha_on_branch") as mock_on_branch:
        mock_on_branch.return_value = True
        result = compute_wp_status(
            "WP-001", paths, "acme/repo", "dev",
            stored_status="step-7-complete",
        )
    assert result == "done"
    # Confirm we asked about the right SHA + branch.
    mock_on_branch.assert_called_once()
    args, _kwargs = mock_on_branch.call_args
    assert args[0] == "acme/repo"
    assert args[1] == "abc12345"
    assert args[2] == "dev"


def test_does_not_return_done_when_merge_sha_not_on_branch(tmp_path):
    """Case 1 negative: merge SHA recorded but is_sha_on_branch returns
    False (revert / never landed on dev). Falls through to step-7-complete
    if branch exists, else stored."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-001")
    _write_yaml_record(
        paths.train_runs_dir, "train-001",
        [{"wp": "WP-001", "merge_sha_on_dev": "abc12345"}],
    )
    with patch("_wpxlib.is_sha_on_branch") as mock_on_branch, \
         patch("_wpxlib._gh_branch_exists") as mock_branch:
        mock_on_branch.return_value = False
        mock_branch.return_value = True
        result = compute_wp_status(
            "WP-001", paths, "acme/repo", "dev",
            stored_status="done",
        )
    assert result == "step-7-complete"


# ─── compute_wp_status — Case 2: step-7-shipping ───────────────────────


def test_returns_step_7_shipping_when_in_flight_train_has_wp(tmp_path):
    """Case 2: an in-flight *.state.json lists the WP in its bundle."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-002")
    _write_state_json(
        paths.train_runs_dir, "train-002", phase="verifying",
        bundle=[{"wp": "WP-002"}],
    )
    with patch("_wpxlib._gh_branch_exists") as mock_branch:
        mock_branch.return_value = True  # irrelevant; case 2 wins first
        result = compute_wp_status(
            "WP-002", paths, "acme/repo", "dev",
            stored_status="step-7-complete",
        )
    assert result == "step-7-shipping"


def test_step_7_shipping_takes_priority_over_step_7_complete(tmp_path):
    """When both case 2 (in-flight train) and case 3 (origin branch)
    would apply, case 2 wins — the train owns the WP mid-flight."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-003")
    _write_state_json(
        paths.train_runs_dir, "train-003", phase="ci_running",
        bundle=[{"wp": "WP-003"}],
    )
    with patch("_wpxlib._gh_branch_exists") as mock_branch:
        mock_branch.return_value = True
        result = compute_wp_status(
            "WP-003", paths, "acme/repo", "dev",
            stored_status="pending",
        )
    assert result == "step-7-shipping"
    # _gh_branch_exists should not be called (case 2 hits first).
    mock_branch.assert_not_called()


def test_terminal_phase_train_state_is_not_in_flight(tmp_path):
    """A *.state.json file with phase=success/failed/aborted is terminal
    and MUST NOT be treated as in-flight."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-004")
    _write_state_json(
        paths.train_runs_dir, "train-004", phase="success",
        bundle=[{"wp": "WP-004"}],
    )
    with patch("_wpxlib._gh_branch_exists") as mock_branch:
        mock_branch.return_value = False
        result = compute_wp_status(
            "WP-004", paths, "acme/repo", "dev",
            stored_status="pending",
        )
    # Not in-flight; no branch; no merge SHA → fall-through to stored.
    assert result == "pending"


# ─── compute_wp_status — Case 3: step-7-complete ───────────────────────


def test_returns_step_7_complete_when_origin_branch_exists_no_train(tmp_path):
    """Case 3: origin branch exists; no in-flight train; no merge record."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-005")
    with patch("_wpxlib._gh_branch_exists") as mock_branch:
        mock_branch.return_value = True
        result = compute_wp_status(
            "WP-005", paths, "acme/repo", "dev",
            stored_status="in_progress",
        )
    assert result == "step-7-complete"


def test_step_7_complete_requires_wp_file_for_branch_derivation(tmp_path):
    """Without a WP file, the branch name cannot be derived → fall-through."""
    paths = _make_paths(tmp_path)
    # Deliberately no WP file
    with patch("_wpxlib._gh_branch_exists") as mock_branch:
        # _gh_branch_exists must NOT be called when slug derivation fails
        mock_branch.return_value = True
        result = compute_wp_status(
            "WP-006", paths, "acme/repo", "dev",
            stored_status="pending",
        )
    assert result == "pending"
    mock_branch.assert_not_called()


# ─── compute_wp_status — Case 4: fall-through ──────────────────────────


def test_falls_back_to_stored_when_no_authoritative_signal(tmp_path):
    """Case 4: no merge SHA, no in-flight train, no origin branch →
    return stored_status."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-007")
    with patch("_wpxlib._gh_branch_exists") as mock_branch:
        mock_branch.return_value = False
        result = compute_wp_status(
            "WP-007", paths, "acme/repo", "dev",
            stored_status="auto-draft",
        )
    assert result == "auto-draft"


def test_falls_back_to_pending_when_stored_status_unset(tmp_path):
    """Case 4 default: no signal AND no stored_status → 'pending'."""
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-008")
    with patch("_wpxlib._gh_branch_exists") as mock_branch:
        mock_branch.return_value = False
        result = compute_wp_status(
            "WP-008", paths, "acme/repo", "dev",
            # stored_status omitted
        )
    assert result == "pending"


# ─── _in_flight_train_has_wp ───────────────────────────────────────────


def test_in_flight_returns_false_when_dir_missing(tmp_path):
    """No train-runs/ dir at all → False, no crash."""
    assert _in_flight_train_has_wp(tmp_path / "nope", "WP-001") is False


def test_in_flight_returns_false_when_no_state_json_files(tmp_path):
    """Dir exists, no *.state.json files (only terminal YAML) → False."""
    (tmp_path / "train-runs").mkdir()
    _write_yaml_record(
        tmp_path / "train-runs", "train-001",
        [{"wp": "WP-001", "merge_sha_on_dev": "abc"}],
    )
    assert _in_flight_train_has_wp(tmp_path / "train-runs", "WP-001") is False


def test_in_flight_returns_true_when_wp_in_active_bundle(tmp_path):
    """State JSON with in-flight phase AND wp in bundle → True."""
    runs = tmp_path / "train-runs"
    runs.mkdir()
    _write_state_json(runs, "train-001", phase="merging",
                      bundle=[{"wp": "WP-001"}, {"wp": "WP-002"}])
    assert _in_flight_train_has_wp(runs, "WP-001") is True
    assert _in_flight_train_has_wp(runs, "WP-002") is True
    assert _in_flight_train_has_wp(runs, "WP-003") is False


def test_in_flight_ignores_terminal_phase_state(tmp_path):
    """phase=success → False even if WP is in bundle (terminal trains
    don't own WPs anymore)."""
    runs = tmp_path / "train-runs"
    runs.mkdir()
    _write_state_json(runs, "train-001", phase="success",
                      bundle=[{"wp": "WP-001"}])
    assert _in_flight_train_has_wp(runs, "WP-001") is False


def test_in_flight_includes_paused_and_verifying_gates(tmp_path):
    """Both 'paused' and 'verifying_gates' are still in-flight per
    _IN_FLIGHT_TRAIN_PHASES — the bundle hasn't been finalised."""
    runs = tmp_path / "train-runs"
    runs.mkdir()
    _write_state_json(runs, "train-001", phase="paused",
                      bundle=[{"wp": "WP-001"}])
    assert _in_flight_train_has_wp(runs, "WP-001") is True
    # New state file for the second case
    _write_state_json(runs, "train-002", phase="verifying_gates",
                      bundle=[{"wp": "WP-002"}])
    assert _in_flight_train_has_wp(runs, "WP-002") is True


def test_in_flight_skips_corrupt_state_files(tmp_path):
    """A corrupt *.state.json MUST NOT mask other in-flight trains."""
    runs = tmp_path / "train-runs"
    runs.mkdir()
    (runs / "broken.state.json").write_text("{not valid json",
                                            encoding="utf-8")
    _write_state_json(runs, "train-001", phase="rebasing",
                      bundle=[{"wp": "WP-001"}])
    assert _in_flight_train_has_wp(runs, "WP-001") is True


# ─── WP-004: change_scope threading + current_change_scope helper ──────────


def test_compute_status_threads_scope(tmp_path):
    """compute_wp_status threads change_scope to resolve_wp_branch: a scoped
    branch yields step-7-complete; a foreign-only feat/ branch is suppressed
    under a scope and falls through to the stored cell."""
    import _wpxlib
    paths = _make_paths(tmp_path)
    _make_wp_file(paths.wp_dir, "WP-005", "mine")

    def fake_branch_exists(repo, branch, *, gh=None):
        return False  # no literal hit

    # Scenario A — scoped branch exists → step-7-complete.
    def list_scoped(repo, pattern, *, gh=None):
        return {"wp/change-a/wp-005-*": [
            {"name": "wp/change-a/wp-005-mine",
             "committerdate": "2026-06-02T00:00:00Z"}]}.get(pattern, [])

    with patch("_wpxlib._gh_branch_exists", fake_branch_exists), \
         patch("_wpxlib._gh_list_matching_branches", list_scoped):
        result = compute_wp_status(
            "WP-005", paths, "acme/repo", "dev",
            stored_status="pending", change_scope="change-a",
        )
    assert result == "step-7-complete"

    # Scenario B — only a foreign feat/ branch exists → suppressed → stored.
    def list_foreign_only(repo, pattern, *, gh=None):
        return {
            "wp/change-a/wp-005-*": [],
            "feat/wp-005-*": [
                {"name": "feat/wp-005-foreign",
                 "committerdate": "2026-06-09T00:00:00Z"}],
        }.get(pattern, [])

    with patch("_wpxlib._gh_branch_exists", fake_branch_exists), \
         patch("_wpxlib._gh_list_matching_branches", list_foreign_only):
        result = compute_wp_status(
            "WP-005", paths, "acme/repo", "dev",
            stored_status="pending", change_scope="change-a",
        )
    assert result == "pending"


def test_current_change_scope_none_when_unset(tmp_path, monkeypatch):
    """current_change_scope returns None when SULIS_CHANGE_ID is unset, so
    callers fall back to legacy feat/... resolution."""
    from _wpxlib import current_change_scope
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    assert current_change_scope(tmp_path) is None
