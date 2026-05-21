"""Integration tests for `wpx-train queue-list` via subprocess.

These tests invoke wpx-train through the real shell, with a mocked gh
binary returning canned responses. They verify the end-to-end JSON
output shape and the eligibility algorithm under realistic conditions.
"""

from __future__ import annotations

from pathlib import Path


def _write_index(tmp_project, rows: list[tuple[str, ...]]) -> None:
    """Minimal helper: write an INDEX.md with one table from row tuples."""
    header = "| ID | Title | Primitive | Status | Depends On | Blocks |"
    sep = "|---|---|---|---|---|---|"
    lines = ["# Index", "", header, sep]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")
    tmp_project.wp_dir.mkdir(parents=True, exist_ok=True)
    tmp_project.index_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _seed_wp_files(tmp_project, ids_slugs: list[tuple[str, str]]) -> None:
    for wp_id, slug in ids_slugs:
        (tmp_project.wp_dir / f"{wp_id}-{slug}.md").write_text(
            f"# {wp_id}\n", encoding="utf-8"
        )


def test_queue_list_emits_eligible_and_ineligible_lists(
    tmp_project, run_tool, mock_gh
):
    """End-to-end: 3 WPs, 1 eligible, 2 ineligible — JSON shape matches contract."""
    _write_index(tmp_project, [
        # Ready: step-7-complete, branch exists, CI green, no deps
        ("WP-001", "Ready", "create", "step-7-complete", "—", "—"),
        # Pending: not step-7-complete
        ("WP-002", "Pending", "create", "pending", "—", "—"),
        # Done WPs are filtered out entirely (not even in ineligible list)
        ("WP-003", "Old", "create", "done", "—", "—"),
    ])
    _seed_wp_files(tmp_project, [
        ("WP-001", "ready"), ("WP-002", "pending"), ("WP-003", "old"),
    ])

    # Mock gh: WP-001 branch exists and is green
    mock_gh([
        {
            "match": "git/refs/heads/feat/wp-001-ready",
            "stdout": '{"object": {"sha": "deadbeef"}}',
        },
        {
            "match": "git/refs/heads/feat/wp-002-pending",
            "stdout": '{"object": {"sha": "cafebabe"}}',
        },
        {
            "match": "commits/feat/wp-001-ready/check-runs",
            "stdout": '{"check_runs": [{"name": "ci", "status": "completed", "conclusion": "success"}]}',
        },
        {
            "match": "commits/feat/wp-002-pending/check-runs",
            "stdout": '{"check_runs": [{"name": "ci", "status": "completed", "conclusion": "success"}]}',
        },
    ])

    result = run_tool(
        "wpx-train", "queue-list",
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
        "--repo", "acme/x",
    )
    assert result.ok, f"queue-list failed: stderr={result.stderr} stdout={result.stdout}"

    data = result.data
    assert data["project"] == tmp_project.project
    assert data["eligible_count"] == 1
    assert data["ineligible_count"] == 1  # WP-002 pending; WP-003 done is filtered out
    assert data["eligible"][0]["wp"] == "WP-001"
    assert data["eligible"][0]["branch"] == "feat/wp-001-ready"
    assert data["ineligible"][0]["wp"] == "WP-002"
    assert "status is 'pending'" in data["ineligible"][0]["reason"]


def test_queue_list_missing_index_errors(tmp_project, run_tool):
    """When INDEX.md doesn't exist, the tool exits 1 with a helpful message."""
    # Don't create INDEX.md
    result = run_tool(
        "wpx-train", "queue-list",
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
        "--repo", "acme/x",
    )
    assert result.returncode == 1
    assert result.json is not None
    assert result.json.get("ok") is False
    assert "INDEX.md not found" in result.json["error"]


def test_queue_list_respects_overrides_file(tmp_project, run_tool, mock_gh):
    """A WP held via train-overrides.yaml shows as ineligible with the right reason."""
    _write_index(tmp_project, [
        ("WP-001", "Ready", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project, [("WP-001", "ready")])

    # Pre-seed an override holding WP-001
    overrides_path = tmp_project.arch_root / "train-overrides.yaml"
    overrides_path.parent.mkdir(parents=True, exist_ok=True)
    overrides_path.write_text(
        "holds:\n  - WP-001\n", encoding="utf-8",
    )

    mock_gh([
        {
            "match": "git/refs/heads/feat/wp-001-ready",
            "stdout": '{"object": {"sha": "deadbeef"}}',
        },
        {
            "match": "commits/feat/wp-001-ready/check-runs",
            "stdout": '{"check_runs": []}',
        },
    ])

    result = run_tool(
        "wpx-train", "queue-list",
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
        "--repo", "acme/x",
    )
    assert result.ok
    assert result.data["eligible_count"] == 0
    assert result.data["ineligible_count"] == 1
    assert "held by override" in result.data["ineligible"][0]["reason"]
    assert result.data["overrides"]["holds"] == ["WP-001"]


def test_status_subcommand_returns_trigger_state(tmp_project, run_tool, mock_gh):
    """`wpx-train status` returns the trigger state and eligible-count summary."""
    _write_index(tmp_project, [
        ("WP-001", "A", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project, [("WP-001", "a")])
    mock_gh([
        {"match": "git/refs/heads/feat/wp-001-a",
         "stdout": '{"object": {"sha": "deadbeef"}}'},
        {"match": "commits/feat/wp-001-a/check-runs",
         "stdout": '{"check_runs": [{"name": "ci", "status": "completed", "conclusion": "success"}]}'},
    ])

    result = run_tool(
        "wpx-train", "status",
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
        "--repo", "acme/x",
    )
    assert result.ok
    # 1 eligible: trigger state is "waiting" (need ≥3 for size-trigger)
    assert result.data["eligible_count"] == 1
    assert result.data["trigger_state"] == "waiting"
    assert result.data["eligible_wps"] == ["WP-001"]


def test_status_three_eligible_reports_size_trigger(tmp_project, run_tool, mock_gh):
    """3+ eligible WPs → trigger_state == 'ready_size'."""
    _write_index(tmp_project, [
        ("WP-001", "A", "create", "step-7-complete", "—", "—"),
        ("WP-002", "B", "create", "step-7-complete", "—", "—"),
        ("WP-003", "C", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project, [
        ("WP-001", "a"), ("WP-002", "b"), ("WP-003", "c"),
    ])

    # All three branches exist + green
    mock_gh([
        {"match": "git/refs/heads/feat/wp-001-a",
         "stdout": '{"object": {"sha": "deadbeef"}}'},
        {"match": "git/refs/heads/feat/wp-002-b",
         "stdout": '{"object": {"sha": "cafebabe"}}'},
        {"match": "git/refs/heads/feat/wp-003-c",
         "stdout": '{"object": {"sha": "f00dbabe"}}'},
        {"match": "check-runs",
         "stdout": '{"check_runs": [{"name": "ci", "status": "completed", "conclusion": "success"}]}'},
    ])

    result = run_tool(
        "wpx-train", "status",
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
        "--repo", "acme/x",
    )
    assert result.ok
    assert result.data["eligible_count"] == 3
    assert result.data["trigger_state"] == "ready_size"


def test_doctor_reports_missing_wp_file(tmp_project, run_tool):
    """doctor flags WPs in INDEX without a corresponding WP-*.md file."""
    _write_index(tmp_project, [
        ("WP-001", "Real", "create", "step-7-complete", "—", "—"),
        ("WP-002", "Phantom", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project, [("WP-001", "real")])  # WP-002 file missing

    result = run_tool(
        "wpx-train", "doctor",
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
        "--repo", "acme/x",
    )
    assert result.ok
    issues = result.data["issues"]
    kinds = [i["kind"] for i in issues]
    assert "wp_file_missing" in kinds
    missing = [i for i in issues if i["kind"] == "wp_file_missing"]
    assert missing[0]["wp"] == "WP-002"


def test_run_subcommand_returns_not_implemented_in_skeleton(
    tmp_project, run_tool
):
    """`wpx-train run` in v0.11.0 is a placeholder; returns structured stub."""
    result = run_tool(
        "wpx-train", "run",
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
        "--repo", "acme/x",
    )
    assert result.returncode == 1  # exit 1 = expected failure (not_implemented)
    assert result.json is not None
    assert result.json.get("ok") is True  # JSON shape is still OK
    assert result.data["outcome"] == "not_implemented"
    assert result.data["skeleton_version"] == "0.11.0"
