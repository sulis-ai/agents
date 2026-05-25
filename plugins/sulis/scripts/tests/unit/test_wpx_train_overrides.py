"""Unit tests for the overrides file IO (read/write) + the queue-add /
queue-remove subcommands.

Overrides file format is a tiny YAML-lite with two top-level keys:
`includes:` and `holds:`. Each is a list of WP IDs.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _wpxlib import (
    TrainOverrides,
    read_overrides,
    write_overrides,
)


def test_read_overrides_missing_file_returns_empty(tmp_path):
    """No file on disk → empty TrainOverrides, no error."""
    result = read_overrides(tmp_path / "nope.yaml")
    assert result.includes == []
    assert result.holds == []


def test_round_trip_includes(tmp_path):
    """Write then read; includes list survives."""
    path = tmp_path / "train-overrides.yaml"
    write_overrides(path, TrainOverrides(includes=["WP-001", "WP-AUTO-018"]))
    result = read_overrides(path)
    assert result.includes == ["WP-001", "WP-AUTO-018"]
    assert result.holds == []


def test_round_trip_holds(tmp_path):
    """Write then read; holds list survives."""
    path = tmp_path / "train-overrides.yaml"
    write_overrides(path, TrainOverrides(holds=["WP-005"]))
    result = read_overrides(path)
    assert result.holds == ["WP-005"]
    assert result.includes == []


def test_round_trip_both(tmp_path):
    """Both lists survive a round trip."""
    path = tmp_path / "train-overrides.yaml"
    write_overrides(path, TrainOverrides(
        includes=["WP-001"], holds=["WP-002", "WP-003"],
    ))
    result = read_overrides(path)
    assert result.includes == ["WP-001"]
    assert result.holds == ["WP-002", "WP-003"]


def test_write_creates_parent_dir(tmp_path):
    """Overrides path's parent dir doesn't exist → write creates it."""
    deep = tmp_path / "a" / "b" / "c" / "train-overrides.yaml"
    write_overrides(deep, TrainOverrides(includes=["WP-007"]))
    assert deep.exists()
    assert read_overrides(deep).includes == ["WP-007"]


def test_read_overrides_tolerates_comments_and_blanks(tmp_path):
    """Comments + blank lines + indented list items parse correctly."""
    path = tmp_path / "train-overrides.yaml"
    path.write_text(
        "# top-level comment\n"
        "\n"
        "includes:\n"
        "  - WP-001\n"
        "  # commented-out: WP-002\n"
        "  - WP-003\n"
        "\n"
        "holds:\n"
        "  - WP-099\n",
        encoding="utf-8",
    )
    result = read_overrides(path)
    assert result.includes == ["WP-001", "WP-003"]
    assert result.holds == ["WP-099"]


# ─── Integration: queue-add and queue-remove via subprocess ──────────────


def _write_minimal_index(tmp_project):
    """Helper: minimal INDEX.md so the tools don't bail on missing file."""
    tmp_project.wp_dir.mkdir(parents=True, exist_ok=True)
    tmp_project.index_md.write_text(
        "# Index\n\n"
        "| ID | Title | Primitive | Status | Depends On | Blocks |\n"
        "|---|---|---|---|---|---|\n"
        "| WP-001 | x | create | step-7-complete | — | — |\n\n",
        encoding="utf-8",
    )


def test_queue_add_writes_overrides_file(tmp_project, run_tool):
    """`wpx-train queue-add --wp WP-X` writes to train-overrides.yaml."""
    _write_minimal_index(tmp_project)
    overrides_path = tmp_project.arch_root / "train-overrides.yaml"
    assert not overrides_path.exists()

    result = run_tool("wpx-train", "queue-add",
                      "--project", tmp_project.project,
                      "--repo-root", str(tmp_project.repo_root),
                      "--wp", "WP-001",
                      "--repo", "acme/x")
    assert result.ok, f"queue-add failed: {result.stderr}"
    assert result.data["action"] == "force_include_added"
    assert overrides_path.exists()
    assert "WP-001" in overrides_path.read_text()


def test_queue_add_idempotent(tmp_project, run_tool):
    """Adding the same WP twice is a no-op."""
    _write_minimal_index(tmp_project)
    for _ in range(2):
        result = run_tool("wpx-train", "queue-add",
                          "--project", tmp_project.project,
                          "--repo-root", str(tmp_project.repo_root),
                          "--wp", "WP-001",
                          "--repo", "acme/x")
        assert result.ok
    # Final state: WP-001 appears exactly once in the file
    overrides = read_overrides(tmp_project.arch_root / "train-overrides.yaml")
    assert overrides.includes.count("WP-001") == 1


def test_queue_remove_writes_hold(tmp_project, run_tool):
    """`wpx-train queue-remove --wp WP-X` writes a hold marker."""
    _write_minimal_index(tmp_project)
    result = run_tool("wpx-train", "queue-remove",
                      "--project", tmp_project.project,
                      "--repo-root", str(tmp_project.repo_root),
                      "--wp", "WP-005",
                      "--repo", "acme/x")
    assert result.ok, f"queue-remove failed: {result.stderr}"
    assert result.data["action"] == "hold_added"
    overrides = read_overrides(tmp_project.arch_root / "train-overrides.yaml")
    assert overrides.holds == ["WP-005"]


def test_queue_add_clears_prior_hold(tmp_project, run_tool):
    """Adding a WP that was previously held removes the hold."""
    _write_minimal_index(tmp_project)
    # First hold it
    run_tool("wpx-train", "queue-remove",
             "--project", tmp_project.project,
             "--repo-root", str(tmp_project.repo_root),
             "--wp", "WP-001",
             "--repo", "acme/x")
    # Then force-include
    result = run_tool("wpx-train", "queue-add",
                      "--project", tmp_project.project,
                      "--repo-root", str(tmp_project.repo_root),
                      "--wp", "WP-001",
                      "--repo", "acme/x")
    assert result.ok
    overrides = read_overrides(tmp_project.arch_root / "train-overrides.yaml")
    assert overrides.includes == ["WP-001"]
    assert overrides.holds == []


def test_queue_remove_clears_prior_include(tmp_project, run_tool):
    """Holding a WP that was previously force-included removes the include."""
    _write_minimal_index(tmp_project)
    run_tool("wpx-train", "queue-add",
             "--project", tmp_project.project,
             "--repo-root", str(tmp_project.repo_root),
             "--wp", "WP-001",
             "--repo", "acme/x")
    result = run_tool("wpx-train", "queue-remove",
                      "--project", tmp_project.project,
                      "--repo-root", str(tmp_project.repo_root),
                      "--wp", "WP-001",
                      "--repo", "acme/x")
    assert result.ok
    overrides = read_overrides(tmp_project.arch_root / "train-overrides.yaml")
    assert overrides.includes == []
    assert overrides.holds == ["WP-001"]
