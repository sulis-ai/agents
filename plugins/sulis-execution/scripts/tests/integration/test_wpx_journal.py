"""Integration tests for wpx-journal.

Focuses on the v0.10.0 plan-generation surface (seed-plan / mark-plan-item /
add-plan-item / read --field plan) since those are the newest moving parts.
Basic lifecycle ops (init, start-step, complete-step) covered briefly.
"""

from __future__ import annotations

import json


def _common(tmp_project):
    return [
        "--project", tmp_project.project,
        "--repo-root", str(tmp_project.repo_root),
    ]


def test_journal_init_creates_file_with_all_sections(tmp_project, run_tool):
    r = run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    assert r.ok
    text = tmp_project.journal("WP-001").read_text()
    assert "## Pre-flight checks" in text
    assert "## Plan" in text
    assert "## Step trace" in text
    assert "## Self-heal attempts" in text
    assert "## Post-deploy verification" in text
    assert "## Notes" in text


def test_journal_step_trace_round_trip(tmp_project, run_tool):
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    r1 = run_tool("wpx-journal", "start-step", "--wp", "WP-001", "--step", "2", *_common(tmp_project))
    assert r1.ok
    r2 = run_tool(
        "wpx-journal", "complete-step",
        "--wp", "WP-001", "--step", "2", "--outcome", "3 tests written",
        *_common(tmp_project),
    )
    assert r2.ok
    # Read back via wpx-journal read
    r3 = run_tool(
        "wpx-journal", "read",
        "--wp", "WP-001", "--field", "step-2-status",
        *_common(tmp_project),
    )
    assert r3.ok
    assert r3.data["value"] == "completed"


def test_seed_plan_populates_plan_section(tmp_project, run_tool, tmp_path):
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps([
        {"description": "Write test_foo", "step": "2 (RED)"},
        {"description": "Implement foo()", "step": "3 (GREEN)"},
    ]))
    r = run_tool(
        "wpx-journal", "seed-plan", "--wp", "WP-001",
        "--approach", "Create primitive; new foo() with 1 test",
        "--plan-json", f"@{plan}",
        *_common(tmp_project),
    )
    assert r.ok
    assert r.data["item_count"] == 2
    text = tmp_project.journal("WP-001").read_text()
    assert "Create primitive; new foo() with 1 test" in text
    assert "Write test_foo" in text


def test_mark_plan_item_atomic_check(tmp_project, run_tool, tmp_path):
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps([{"description": "x", "step": "2"}]))
    run_tool(
        "wpx-journal", "seed-plan", "--wp", "WP-001",
        "--approach", "x", "--plan-json", f"@{plan}",
        *_common(tmp_project),
    )
    # Atomic flip with correct --expected
    r1 = run_tool(
        "wpx-journal", "mark-plan-item",
        "--wp", "WP-001", "--item", "1",
        "--status", "in-progress", "--expected", "pending",
        *_common(tmp_project),
    )
    assert r1.ok
    # Atomic flip with WRONG --expected should fail
    r2 = run_tool(
        "wpx-journal", "mark-plan-item",
        "--wp", "WP-001", "--item", "1",
        "--status", "done", "--expected", "pending",
        *_common(tmp_project),
    )
    assert not r2.ok
    assert "expected 'pending'" in r2.error


def test_read_field_plan_returns_structured_json(tmp_project, run_tool, tmp_path):
    run_tool("wpx-journal", "init", "--wp", "WP-001", *_common(tmp_project))
    plan = tmp_path / "plan.json"
    plan.write_text(json.dumps([
        {"description": "Item 1", "step": "2"},
        {"description": "Item 2", "step": "3", "notes": "conditional"},
    ]))
    run_tool(
        "wpx-journal", "seed-plan", "--wp", "WP-001",
        "--approach", "test", "--plan-json", f"@{plan}",
        *_common(tmp_project),
    )
    r = run_tool(
        "wpx-journal", "read",
        "--wp", "WP-001", "--field", "plan",
        *_common(tmp_project),
    )
    assert r.ok
    items = r.data["value"]["items"]
    assert len(items) == 2
    assert items[0]["description"] == "Item 1"
    assert items[1]["notes"] == "conditional"
