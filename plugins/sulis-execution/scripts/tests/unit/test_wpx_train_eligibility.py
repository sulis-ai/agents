"""Unit tests for parse_index_md + find_eligible_branches.

These tests cover the wpx-train eligibility algorithm at the
function level. They don't shell out — `gh` calls are
monkeypatched to deterministic stubs.

Coverage:
- parse_index_md: real-shape INDEX.md → list[WPRow]
- find_eligible_branches: five eligibility rules per ADR-212 D6
- overrides: force-include lifts CI requirement; hold blocks eligible
"""

from __future__ import annotations

from pathlib import Path

import pytest

import _wpxlib
from _wpxlib import (
    EligibilityResult,
    TrainOverrides,
    WPRow,
    find_eligible_branches,
    parse_index_md,
)


# ─── Fixtures (INDEX.md, WP files) ────────────────────────────────────────


def _write_index(wp_dir: Path, rows: list[tuple[str, ...]]) -> Path:
    """Write a minimal INDEX.md with one WP table.

    Each row tuple is (id, title, primitive, status, depends_on, blocks).
    """
    header = "| ID | Title | Primitive | Status | Depends On | Blocks |"
    sep = "|---|---|---|---|---|---|"
    lines = ["# Work Package Index — test", "", header, sep]
    for row in rows:
        lines.append("| " + " | ".join(row) + " |")
    lines.append("")  # trailing blank line so the table parser closes cleanly
    wp_dir.mkdir(parents=True, exist_ok=True)
    index = wp_dir / "INDEX.md"
    index.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return index


def _seed_wp_files(wp_dir: Path, wp_ids_with_slugs: list[tuple[str, str]]) -> None:
    """Create empty WP-{id}-{slug}.md files so wp_file() resolves."""
    for wp_id, slug in wp_ids_with_slugs:
        (wp_dir / f"{wp_id}-{slug}.md").write_text(f"# {wp_id}\n", encoding="utf-8")


# ─── parse_index_md ───────────────────────────────────────────────────────


def test_parse_index_md_basic(tmp_project):
    """Single WP table, simple rows."""
    index = _write_index(tmp_project.wp_dir, [
        ("WP-001", "First WP", "create", "done", "—", "WP-002"),
        ("WP-002", "Second WP", "extend", "pending", "WP-001", "—"),
    ])
    rows = parse_index_md(index)
    assert len(rows) == 2
    assert rows[0].id == "WP-001"
    assert rows[0].status == "done"
    assert rows[0].depends_on == []
    assert rows[0].blocks == ["WP-002"]
    assert rows[1].depends_on == ["WP-001"]


def test_parse_index_md_skips_non_wp_rows(tmp_project):
    """Rows whose first cell doesn't start with WP- are skipped."""
    index_text = """# Index

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | Real WP | create | done | — | — |
| Summary | Not a WP | — | — | — | — |

"""
    tmp_project.index_md.parent.mkdir(parents=True, exist_ok=True)
    tmp_project.index_md.write_text(index_text, encoding="utf-8")
    rows = parse_index_md(tmp_project.index_md)
    assert len(rows) == 1
    assert rows[0].id == "WP-001"


def test_parse_index_md_multiple_tables(tmp_project):
    """INDEX.md with two WP tables in different sections; both parsed."""
    index_text = """# Index

## Section A

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | A1 | create | done | — | — |

## Section B

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-002 | B1 | extend | pending | WP-001 | — |
| WP-003 | B2 | create | step-7-complete | WP-001 | — |

"""
    tmp_project.index_md.parent.mkdir(parents=True, exist_ok=True)
    tmp_project.index_md.write_text(index_text, encoding="utf-8")
    rows = parse_index_md(tmp_project.index_md)
    assert len(rows) == 3
    assert [r.id for r in rows] == ["WP-001", "WP-002", "WP-003"]
    assert rows[2].status == "step-7-complete"


def test_parse_index_md_handles_multi_dep_csv(tmp_project):
    """Depends-on cell with multiple WPs is split correctly."""
    index = _write_index(tmp_project.wp_dir, [
        ("WP-005", "Multi", "create", "step-7-complete",
         "WP-001, WP-002, WP-003", "—"),
    ])
    rows = parse_index_md(index)
    assert rows[0].depends_on == ["WP-001", "WP-002", "WP-003"]


def test_parse_index_md_tolerates_extra_columns(tmp_project):
    """Extra columns (Token, TDD §, ADR) are stored under extras."""
    index_text = """# Index

| ID | Title | Primitive | Status | Depends On | Blocks | Token | TDD § |
|---|---|---|---|---|---|---|---|
| WP-001 | A | create | done | — | — | 5k / 3k | §3.1 |

"""
    tmp_project.index_md.parent.mkdir(parents=True, exist_ok=True)
    tmp_project.index_md.write_text(index_text, encoding="utf-8")
    rows = parse_index_md(tmp_project.index_md)
    assert rows[0].extras["Token"] == "5k / 3k"
    assert rows[0].extras["TDD §"] == "§3.1"


def test_parse_index_md_missing_file_raises(tmp_project):
    """parse_index_md raises FileNotFoundError for missing INDEX.md."""
    with pytest.raises(FileNotFoundError):
        parse_index_md(tmp_project.wp_dir / "nope.md")


# ─── find_eligible_branches ───────────────────────────────────────────────


def _stub_gh(monkeypatch, *,
             branches_present: set[str],
             green_branches: set[str]) -> None:
    """Stub the gh-API helpers so find_eligible_branches doesn't shell out.

    Branches in `branches_present` exist on origin; branches in
    `green_branches` have green CI. The intersection is what's
    actually eligible (passes both checks).
    """

    def fake_branch_exists(repo, branch):
        return branch in branches_present

    def fake_ci_green(repo, branch):
        return branch in green_branches

    monkeypatch.setattr(_wpxlib, "_gh_branch_exists", fake_branch_exists)
    monkeypatch.setattr(_wpxlib, "_gh_branch_ci_green", fake_ci_green)


def test_find_eligible_basic_ready(tmp_project, monkeypatch):
    """One WP at step-7-complete, branch present, CI green, no deps → eligible."""
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Ready", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [("WP-001", "ready-feature")])
    _stub_gh(monkeypatch,
             branches_present={"feat/wp-001-ready-feature"},
             green_branches={"feat/wp-001-ready-feature"})
    rows = parse_index_md(tmp_project.index_md)
    results = find_eligible_branches(rows, repo="acme/x", wp_dir=tmp_project.wp_dir)
    eligible = [r for r in results if r.eligible]
    assert len(eligible) == 1
    assert eligible[0].wp == "WP-001"
    assert eligible[0].branch == "feat/wp-001-ready-feature"


def test_find_eligible_status_filter(tmp_project, monkeypatch):
    """WPs at status other than step-7-complete are ineligible."""
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Done", "create", "done", "—", "—"),
        ("WP-002", "Pending", "create", "pending", "—", "—"),
        ("WP-003", "Ready", "create", "step-7-complete", "—", "—"),
        ("WP-004", "Blocked", "create", "step-7-blocked", "—", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [
        ("WP-001", "done"), ("WP-002", "pending"),
        ("WP-003", "ready"), ("WP-004", "blocked"),
    ])
    _stub_gh(monkeypatch,
             branches_present={"feat/wp-001-done", "feat/wp-002-pending",
                               "feat/wp-003-ready", "feat/wp-004-blocked"},
             green_branches={"feat/wp-001-done", "feat/wp-002-pending",
                             "feat/wp-003-ready", "feat/wp-004-blocked"})
    rows = parse_index_md(tmp_project.index_md)
    results = find_eligible_branches(rows, repo="acme/x", wp_dir=tmp_project.wp_dir)
    # WP-001 (done) is filtered out entirely (not a candidate)
    by_id = {r.wp: r for r in results}
    assert "WP-001" not in by_id  # done WPs skipped
    assert not by_id["WP-002"].eligible  # pending
    assert by_id["WP-003"].eligible       # step-7-complete
    assert not by_id["WP-004"].eligible  # step-7-blocked


def test_find_eligible_branch_missing(tmp_project, monkeypatch):
    """WP at step-7-complete but branch absent → ineligible with clear reason."""
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Ghost", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [("WP-001", "ghost")])
    _stub_gh(monkeypatch,
             branches_present=set(),  # branch missing
             green_branches=set())
    rows = parse_index_md(tmp_project.index_md)
    results = find_eligible_branches(rows, repo="acme/x", wp_dir=tmp_project.wp_dir)
    assert len(results) == 1
    assert not results[0].eligible
    assert "branch missing" in results[0].reason


def test_find_eligible_ci_red_strict_mode(tmp_project, monkeypatch):
    """Strict mode (v0.11.0 behaviour): branch exists but CI is red → ineligible.

    With default (optimistic, v0.18.0+), CI red would NOT block eligibility —
    see test_find_eligible_ci_red_optimistic_passes below.
    """
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Red", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [("WP-001", "red")])
    _stub_gh(monkeypatch,
             branches_present={"feat/wp-001-red"},
             green_branches=set())  # CI not green
    rows = parse_index_md(tmp_project.index_md)
    results = find_eligible_branches(
        rows, repo="acme/x", wp_dir=tmp_project.wp_dir, strict_ci=True,
    )
    assert not results[0].eligible
    assert "CI not green" in results[0].reason


def test_find_eligible_ci_red_optimistic_passes(tmp_project, monkeypatch):
    """v0.18.0+ default (optimistic): CI red is informational, not gating.

    Bundled-tip CI at Step 8 is the real gate; per-WP CI is a hint.
    The WP-with-red-CI is still eligible; bundled-tip CI will catch
    any genuine breakage during the train run.
    """
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Red", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [("WP-001", "red")])
    _stub_gh(monkeypatch,
             branches_present={"feat/wp-001-red"},
             green_branches=set())  # CI not green
    rows = parse_index_md(tmp_project.index_md)
    # Default: strict_ci omitted → False → optimistic
    results = find_eligible_branches(
        rows, repo="acme/x", wp_dir=tmp_project.wp_dir,
    )
    assert results[0].eligible, (
        f"Expected WP-001 eligible under optimistic mode despite red CI; "
        f"got reason: {results[0].reason}"
    )


def test_find_eligible_unmet_deps(tmp_project, monkeypatch):
    """WP depends on a pending WP → ineligible."""
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Predecessor", "create", "pending", "—", "WP-002"),
        ("WP-002", "Successor", "extend", "step-7-complete", "WP-001", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [("WP-001", "pre"), ("WP-002", "post")])
    _stub_gh(monkeypatch,
             branches_present={"feat/wp-002-post"},
             green_branches={"feat/wp-002-post"})
    rows = parse_index_md(tmp_project.index_md)
    results = find_eligible_branches(rows, repo="acme/x", wp_dir=tmp_project.wp_dir)
    wp_002 = [r for r in results if r.wp == "WP-002"][0]
    assert not wp_002.eligible
    assert "dependencies not merged" in wp_002.reason
    assert "WP-001" in wp_002.reason


def test_find_eligible_force_include_bypasses_ci(tmp_project, monkeypatch):
    """Force-include override lifts the CI-green requirement."""
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Red", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [("WP-001", "red")])
    _stub_gh(monkeypatch,
             branches_present={"feat/wp-001-red"},
             green_branches=set())  # CI not green
    overrides = TrainOverrides(includes=["WP-001"])
    rows = parse_index_md(tmp_project.index_md)
    results = find_eligible_branches(rows, repo="acme/x", wp_dir=tmp_project.wp_dir,
                                     overrides=overrides)
    assert results[0].eligible
    assert results[0].forced is True


def test_find_eligible_hold_blocks_ready(tmp_project, monkeypatch):
    """Hold override marks an otherwise-eligible WP as ineligible."""
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Ready", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [("WP-001", "ready")])
    _stub_gh(monkeypatch,
             branches_present={"feat/wp-001-ready"},
             green_branches={"feat/wp-001-ready"})
    overrides = TrainOverrides(holds=["WP-001"])
    rows = parse_index_md(tmp_project.index_md)
    results = find_eligible_branches(rows, repo="acme/x", wp_dir=tmp_project.wp_dir,
                                     overrides=overrides)
    assert not results[0].eligible
    assert "held by override" in results[0].reason


def test_find_eligible_no_wp_file(tmp_project, monkeypatch):
    """WP in INDEX but no WP-*.md file on disk → ineligible, clear reason."""
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Phantom", "create", "step-7-complete", "—", "—"),
    ])
    # Deliberately don't seed the WP file
    _stub_gh(monkeypatch,
             branches_present=set(),
             green_branches=set())
    rows = parse_index_md(tmp_project.index_md)
    results = find_eligible_branches(rows, repo="acme/x", wp_dir=tmp_project.wp_dir)
    assert not results[0].eligible
    assert "no WP file found" in results[0].reason


# ─── v0.18.0+ optimistic-vs-strict eligibility ──────────────────────────


def test_optimistic_includes_pending_ci(tmp_project, monkeypatch):
    """v0.18.0+ optimistic mode: a WP with pending (not green) CI is still
    eligible. Bundled-tip CI at Step 8 is the real gate."""
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Pending CI", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [("WP-001", "pending-ci")])
    _stub_gh(monkeypatch,
             branches_present={"feat/wp-001-pending-ci"},
             green_branches=set())  # CI pending (not green)
    rows = parse_index_md(tmp_project.index_md)
    results = find_eligible_branches(
        rows, repo="acme/x", wp_dir=tmp_project.wp_dir,
    )  # Default = optimistic
    assert results[0].eligible


def test_strict_excludes_pending_ci(tmp_project, monkeypatch):
    """Strict mode: same WP-with-pending-CI is ineligible (v0.11.0 behaviour)."""
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "Pending CI", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [("WP-001", "pending-ci")])
    _stub_gh(monkeypatch,
             branches_present={"feat/wp-001-pending-ci"},
             green_branches=set())
    rows = parse_index_md(tmp_project.index_md)
    results = find_eligible_branches(
        rows, repo="acme/x", wp_dir=tmp_project.wp_dir, strict_ci=True,
    )
    assert not results[0].eligible
    assert "CI not green" in results[0].reason
    assert "strict-ci" in results[0].reason  # explains it's the strict flag


def test_optimistic_and_strict_agree_when_all_ci_green(tmp_project, monkeypatch):
    """When all branches have green CI, optimistic + strict produce identical results."""
    _write_index(tmp_project.wp_dir, [
        ("WP-001", "A", "create", "step-7-complete", "—", "—"),
        ("WP-002", "B", "create", "step-7-complete", "—", "—"),
    ])
    _seed_wp_files(tmp_project.wp_dir, [("WP-001", "a"), ("WP-002", "b")])
    _stub_gh(monkeypatch,
             branches_present={"feat/wp-001-a", "feat/wp-002-b"},
             green_branches={"feat/wp-001-a", "feat/wp-002-b"})
    rows = parse_index_md(tmp_project.index_md)
    optimistic = find_eligible_branches(
        rows, repo="acme/x", wp_dir=tmp_project.wp_dir,
    )
    strict = find_eligible_branches(
        rows, repo="acme/x", wp_dir=tmp_project.wp_dir, strict_ci=True,
    )
    assert [r.eligible for r in optimistic] == [r.eligible for r in strict]
    assert all(r.eligible for r in optimistic)
