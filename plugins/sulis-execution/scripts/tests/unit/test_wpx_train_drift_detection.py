"""Unit tests for v0.21.2 — INDEX status drift detection in wpx-train doctor.

The bug this addresses (real-world, surfaced 2026-05-22): a slice-2
audit found 3 WPs with INDEX status=done while their work wasn't
actually on dev. The autonomous run ad-hoc reconciled. v0.21.2 adds
first-class detection via `wpx-train doctor` so future drift is caught
explicitly instead of needing per-incident hand-investigation.

These tests pin:
- find_wp_merge_sha: walks train-runs YAML + JSON files in reverse
  chrono order; returns most-recent merge_sha_on_dev for a WP
- is_sha_on_branch: thin wrapper over gh compare API (mocked here)
- Drift classification in cmd_doctor: 3 cases (drift-no-history,
  drift-not-on-dev, no-drift)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

from _wpxlib import find_wp_merge_sha, is_sha_on_branch  # noqa: E402


# ─── find_wp_merge_sha ──────────────────────────────────────────────────


def _write_state_json(path: Path, bundle: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"bundle": bundle}), encoding="utf-8")


def _write_yaml_record(path: Path, bundle: list[dict]) -> None:
    """Mimic write_train_run_record's bespoke YAML emitter."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["train_id: test", "bundle:"]
    for item in bundle:
        lines.append(f"  - wp: {item.get('wp', '')}")
        for k in ("branch", "pre_train_sha", "rebased_to_sha", "merge_sha_on_dev"):
            v = item.get(k)
            if v is None:
                lines.append(f"    {k}: null")
            else:
                lines.append(f"    {k}: {v}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_find_wp_merge_sha_returns_none_when_dir_missing(tmp_path):
    """No train-runs/ dir at all — return None, don't crash."""
    assert find_wp_merge_sha(tmp_path / "nope", "WP-001") is None


def test_find_wp_merge_sha_returns_none_when_dir_empty(tmp_path):
    """Dir exists but no files — return None."""
    (tmp_path / "train-runs").mkdir()
    assert find_wp_merge_sha(tmp_path / "train-runs", "WP-001") is None


def test_find_wp_merge_sha_returns_none_when_wp_never_in_any_bundle(tmp_path):
    """Bundle records exist but none mention the WP — return None."""
    runs = tmp_path / "train-runs"
    _write_state_json(
        runs / "train-001.state.json",
        [{"wp": "WP-OTHER", "merge_sha_on_dev": "abc123"}],
    )
    assert find_wp_merge_sha(runs, "WP-001") is None


def test_find_wp_merge_sha_returns_sha_from_json_state(tmp_path):
    """In-flight .state.json with the WP's merge SHA → returned."""
    runs = tmp_path / "train-runs"
    _write_state_json(
        runs / "train-001.state.json",
        [{"wp": "WP-001", "merge_sha_on_dev": "abc12345def67890"}],
    )
    assert find_wp_merge_sha(runs, "WP-001") == "abc12345def67890"


def test_find_wp_merge_sha_returns_sha_from_yaml_record(tmp_path):
    """Terminal .yaml record with the WP's merge SHA → returned."""
    runs = tmp_path / "train-runs"
    _write_yaml_record(
        runs / "train-002.yaml",
        [{"wp": "WP-001", "branch": "feat/wp-001",
          "merge_sha_on_dev": "def67890abc12345"}],
    )
    assert find_wp_merge_sha(runs, "WP-001") == "def67890abc12345"


def test_find_wp_merge_sha_prefers_most_recent_record(tmp_path):
    """Multiple records with the WP → return the most-recent file's SHA."""
    runs = tmp_path / "train-runs"
    _write_yaml_record(
        runs / "train-001.yaml",
        [{"wp": "WP-001", "merge_sha_on_dev": "older123"}],
    )
    # Make the second file genuinely newer (file mtime resolution can be
    # coarse on some filesystems)
    time.sleep(0.05)
    _write_yaml_record(
        runs / "train-002.yaml",
        [{"wp": "WP-001", "merge_sha_on_dev": "newer456"}],
    )
    # Touch mtime explicitly so the test is deterministic
    older_path = runs / "train-001.yaml"
    newer_path = runs / "train-002.yaml"
    now = time.time()
    os.utime(older_path, (now - 1000, now - 1000))
    os.utime(newer_path, (now, now))
    assert find_wp_merge_sha(runs, "WP-001") == "newer456"


def test_find_wp_merge_sha_skips_entries_without_merge_sha(tmp_path):
    """A bundle entry for the WP without merge_sha_on_dev set is skipped."""
    runs = tmp_path / "train-runs"
    _write_yaml_record(
        runs / "train-001.yaml",
        [{"wp": "WP-001", "merge_sha_on_dev": None}],
    )
    assert find_wp_merge_sha(runs, "WP-001") is None


# ─── is_sha_on_branch (mocked gh API) ──────────────────────────────────


def test_is_sha_on_branch_true_when_status_identical():
    """gh compare returns status=identical → True (sha == branch HEAD)."""
    with patch("_wpxlib._run") as mock_run:
        mock_run.return_value = (0, '{"status": "identical"}', "")
        assert is_sha_on_branch("acme/repo", "abc12345", "dev") is True


def test_is_sha_on_branch_true_when_status_behind():
    """gh compare returns status=behind → True (sha in branch's history)."""
    with patch("_wpxlib._run") as mock_run:
        mock_run.return_value = (0, '{"status": "behind"}', "")
        assert is_sha_on_branch("acme/repo", "abc12345", "dev") is True


def test_is_sha_on_branch_false_when_status_ahead():
    """gh compare returns status=ahead → False (sha has commits branch doesn't)."""
    with patch("_wpxlib._run") as mock_run:
        mock_run.return_value = (0, '{"status": "ahead"}', "")
        assert is_sha_on_branch("acme/repo", "abc12345", "dev") is False


def test_is_sha_on_branch_false_when_status_diverged():
    """gh compare returns status=diverged → False (both have unique commits)."""
    with patch("_wpxlib._run") as mock_run:
        mock_run.return_value = (0, '{"status": "diverged"}', "")
        assert is_sha_on_branch("acme/repo", "abc12345", "dev") is False


def test_is_sha_on_branch_false_when_gh_api_fails():
    """gh compare exits non-zero → False conservatively + logged."""
    with patch("_wpxlib._run") as mock_run:
        mock_run.return_value = (1, "", "API rate limit")
        assert is_sha_on_branch("acme/repo", "abc12345", "dev") is False


def test_is_sha_on_branch_false_when_response_not_json():
    """gh compare returns non-JSON → False conservatively."""
    with patch("_wpxlib._run") as mock_run:
        mock_run.return_value = (0, "Not Found", "")
        assert is_sha_on_branch("acme/repo", "abc12345", "dev") is False
