"""Unit tests for wpx-index multi-table per-kind INDEX support (#50).

Contract-first decompose (#33–#37) produces one WP sub-table per kind
(Data contracts / Visual contracts / Backend / Frontend / Integration),
each with its own column set. Before this fix, flip-status / set-status /
list-ready / propagate-blocked used `_find_wp_table`, which returns only
the FIRST sub-table — so a WP in any later sub-table was invisible
(`flip-status WP-AJ-DC-01` reported "not found"). These tests pin the
multi-table-aware behaviour AND that single-table INDEX still works
byte-identically.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
import sys
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
_WPX_INDEX = _SCRIPTS / "wpx-index"


def _load_wpx_index():
    loader = SourceFileLoader("wpx_index_mod", str(_WPX_INDEX))
    spec = importlib.util.spec_from_loader("wpx_index_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


wpx = _load_wpx_index()


# ─── fixtures ────────────────────────────────────────────────────────────────

# A multi-table per-kind INDEX mirroring the contract-first decompose shape.
# Note: each sub-table has DIFFERENT columns (the visual-contract table
# carries "Data contract" not "Depends On").
_MULTITABLE_INDEX = """# Work Package Index — Test

## Orchestrator Config
max_parallel: 3

## WP table

### Data contracts (Wave 1)

| ID | Title | Status | Transport | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-DC-01 | Signed-call envelope | pending | RFC 9421 | — | DC-02, BE-01 |
| WP-DC-02 | Device grant | pending | HTTP | WP-DC-01 | BE-02 |

### Visual contracts

| ID | Title | Status | App | Data contract | Blocks |
|---|---|---|---|---|---|
| WP-VC-01 | Signup flow | done | founder | WP-DC-02 | WP-FE-01 |

### Backend

| ID | Title | Status | Primitive | Tier | Data contract | Depends On | Blocks |
|---|---|---|---|---|---|---|---|
| WP-BE-01 | Verifier | pending | create | T1 | WP-DC-01 | WP-DC-01 | — |
| WP-BE-02 | Grant handler | pending | create | T1 | WP-DC-02 | WP-DC-02 | — |
"""


def _write_project(tmp_path: Path, index_text: str,
                   frontmatter: dict[str, list[str]] | None = None) -> Path:
    """Create .architecture/{project}/work-packages/{INDEX.md + WP files}.

    `frontmatter` maps WP-ID → dependsOn list. When provided, writes a
    minimal WP-*.md file per entry so the frontmatter dep path is
    exercised. When None, no WP files exist → callers fall back to the
    per-table dep columns (single-table back-compat path).
    """
    wp_dir = tmp_path / ".architecture" / "proj" / "work-packages"
    wp_dir.mkdir(parents=True)
    (wp_dir / "INDEX.md").write_text(index_text, encoding="utf-8")
    if frontmatter:
        for wp_id, deps in frontmatter.items():
            deps_yaml = "[" + ", ".join(deps) + "]" if deps else "[]"
            (wp_dir / f"{wp_id}-stub.md").write_text(
                f"---\nid: {wp_id}\nstatus: pending\n"
                f"dependsOn: {deps_yaml}\nblocks: []\n---\n# {wp_id}\n",
                encoding="utf-8",
            )
    return tmp_path


def _ns(tmp_path: Path, **kw) -> argparse.Namespace:
    base = {"repo_root": str(tmp_path), "project": "proj"}
    base.update(kw)
    return argparse.Namespace(**base)


def _run(fn, ns) -> dict:
    """Invoke a cmd_* function; capture the emit JSON + SystemExit code."""
    buf = io.StringIO()
    code = None
    with redirect_stdout(buf):
        try:
            fn(ns)
        except SystemExit as exc:
            code = exc.code
    out = buf.getvalue().strip()
    data = json.loads(out) if out else {}
    data["_exit"] = code
    return data


def _index_text(tmp_path: Path) -> str:
    return (tmp_path / ".architecture" / "proj" / "work-packages"
            / "INDEX.md").read_text(encoding="utf-8")


# ─── flip-status across sub-tables ───────────────────────────────────────────


def test_flip_status_finds_wp_in_first_subtable(tmp_path):
    _write_project(tmp_path, _MULTITABLE_INDEX)
    ns = _ns(tmp_path, wp="WP-DC-01", to="in_progress", expected=None)
    result = _run(wpx.cmd_flip_status, ns)
    assert result["ok"] is True
    assert "| WP-DC-01 | Signed-call envelope | in_progress |" in _index_text(tmp_path)


def test_flip_status_finds_wp_in_later_subtable(tmp_path):
    """The bug: WP-BE-01 lives in the Backend sub-table (3rd table). The
    old single-table finder returned a different table and reported
    'not found'. Now it must be found + flipped."""
    _write_project(tmp_path, _MULTITABLE_INDEX)
    ns = _ns(tmp_path, wp="WP-BE-01", to="in_progress", expected=None)
    result = _run(wpx.cmd_flip_status, ns)
    assert result["ok"] is True, f"flip failed: {result}"
    txt = _index_text(tmp_path)
    assert "| WP-BE-01 | Verifier | in_progress |" in txt
    # Other sub-tables untouched
    assert "| WP-DC-01 | Signed-call envelope | pending |" in txt


def test_flip_status_data_contract_wp_in_first_table(tmp_path):
    """WP-AJ-DC-01-style: the platform agent's exact failing case —
    a data-contract WP that the old finder missed because it returned
    the Backend table (the only one with a Primitive column)."""
    _write_project(tmp_path, _MULTITABLE_INDEX)
    ns = _ns(tmp_path, wp="WP-DC-02", to="done", expected="pending")
    result = _run(wpx.cmd_flip_status, ns)
    assert result["ok"] is True
    assert "| WP-DC-02 | Device grant | done |" in _index_text(tmp_path)


def test_flip_status_errors_when_wp_in_no_subtable(tmp_path):
    _write_project(tmp_path, _MULTITABLE_INDEX)
    ns = _ns(tmp_path, wp="WP-NONEXISTENT", to="done", expected=None)
    result = _run(wpx.cmd_flip_status, ns)
    assert result["ok"] is False
    assert "not found" in result["error"].lower()


def test_flip_status_expected_mismatch_errors(tmp_path):
    _write_project(tmp_path, _MULTITABLE_INDEX)
    ns = _ns(tmp_path, wp="WP-BE-01", to="done", expected="in_progress")
    result = _run(wpx.cmd_flip_status, ns)
    assert result["ok"] is False
    assert "expected" in result["error"].lower()


# ─── list-ready across sub-tables, deps from frontmatter ─────────────────────


def test_list_ready_spans_all_subtables(tmp_path):
    """DC-01 has no deps → ready. DC-02 depends on DC-01 (not done) →
    not ready. BE-01/BE-02 depend on data contracts (not done) → not
    ready. Only DC-01 should be ready."""
    fm = {
        "WP-DC-01": [],
        "WP-DC-02": ["WP-DC-01"],
        "WP-VC-01": [],            # visual contract: no executable deps
        "WP-BE-01": ["WP-DC-01"],
        "WP-BE-02": ["WP-DC-02"],
    }
    _write_project(tmp_path, _MULTITABLE_INDEX, frontmatter=fm)
    ns = _ns(tmp_path)
    result = _run(wpx.cmd_list_ready, ns)
    assert result["ok"] is True
    assert result["data"]["ready"] == ["WP-DC-01"]


def test_list_ready_releases_dependents_when_dep_done(tmp_path):
    """After DC-01 is done, BE-01 (depends on DC-01) becomes ready."""
    index = _MULTITABLE_INDEX.replace(
        "| WP-DC-01 | Signed-call envelope | pending |",
        "| WP-DC-01 | Signed-call envelope | done |",
    )
    fm = {
        "WP-DC-01": [],
        "WP-DC-02": ["WP-DC-01"],
        "WP-VC-01": [],
        "WP-BE-01": ["WP-DC-01"],
        "WP-BE-02": ["WP-DC-02"],
    }
    _write_project(tmp_path, index, frontmatter=fm)
    result = _run(wpx.cmd_list_ready, _ns(tmp_path))
    ready = set(result["data"]["ready"])
    # DC-02 (dep DC-01 done) + BE-01 (dep DC-01 done) ready; BE-02
    # (dep DC-02 still pending) not.
    assert "WP-DC-02" in ready
    assert "WP-BE-01" in ready
    assert "WP-BE-02" not in ready


def test_list_ready_visual_contract_with_empty_deps(tmp_path):
    """A visual-contract WP carries its data-contract pairing in the
    'Data contract' INDEX column, but its frontmatter dependsOn is
    EMPTY (it gates the frontend, depends on nothing executable). It
    must NOT be treated as depending on its paired data contract.

    Here VC-01 is already `done` in the fixture, so it won't appear in
    ready regardless; this test instead pins that the 'Data contract'
    column value (WP-DC-02) is NOT read as a dependency — we flip VC-01
    to pending and confirm it's ready despite DC-02 being pending."""
    index = _MULTITABLE_INDEX.replace(
        "| WP-VC-01 | Signup flow | done |",
        "| WP-VC-01 | Signup flow | pending |",
    )
    fm = {
        "WP-DC-01": [], "WP-DC-02": ["WP-DC-01"],
        "WP-VC-01": [],  # empty — the 'Data contract' column is pairing, not a dep
        "WP-BE-01": ["WP-DC-01"], "WP-BE-02": ["WP-DC-02"],
    }
    _write_project(tmp_path, index, frontmatter=fm)
    result = _run(wpx.cmd_list_ready, _ns(tmp_path))
    ready = set(result["data"]["ready"])
    # VC-01 has no executable deps → ready, even though its paired
    # data contract WP-DC-02 is still pending.
    assert "WP-VC-01" in ready


def test_list_ready_counts_span_all_tables(tmp_path):
    fm = {k: [] for k in ["WP-DC-01", "WP-DC-02", "WP-VC-01", "WP-BE-01", "WP-BE-02"]}
    _write_project(tmp_path, _MULTITABLE_INDEX, frontmatter=fm)
    result = _run(wpx.cmd_list_ready, _ns(tmp_path))
    # 4 pending (DC-01, DC-02, BE-01, BE-02) + 1 done (VC-01) across all tables
    assert result["data"]["total_pending"] == 4
    assert result["data"]["total_done"] == 1


# ─── propagate-blocked across sub-tables ─────────────────────────────────────


def test_propagate_blocked_marks_dependents_in_other_subtables(tmp_path):
    """Blocking DC-01 should mark DC-02 (data-contracts table) AND
    BE-01 (backend table) as dependency_blocked — they transitively
    depend on DC-01, and they live in DIFFERENT sub-tables."""
    fm = {
        "WP-DC-01": [], "WP-DC-02": ["WP-DC-01"],
        "WP-VC-01": [], "WP-BE-01": ["WP-DC-01"], "WP-BE-02": ["WP-DC-02"],
    }
    _write_project(tmp_path, _MULTITABLE_INDEX, frontmatter=fm)
    result = _run(wpx.cmd_propagate_blocked, _ns(tmp_path, wp="WP-DC-01"))
    assert result["ok"] is True
    flipped = set(result["data"]["flipped_to_dependency_blocked"])
    # DC-02 (direct dep), BE-01 (direct dep), BE-02 (transitive via DC-02)
    assert flipped == {"WP-DC-02", "WP-BE-01", "WP-BE-02"}
    txt = _index_text(tmp_path)
    assert "| WP-DC-02 | Device grant | dependency_blocked |" in txt
    assert "| WP-BE-01 | Verifier | dependency_blocked |" in txt
    assert "| WP-BE-02 | Grant handler | dependency_blocked |" in txt
    # VC-01 (done, no dep on DC-01) untouched
    assert "| WP-VC-01 | Signup flow | done |" in txt


# ─── single-table back-compat (no WP files → table-dep fallback) ─────────────

_SINGLETABLE_INDEX = """# Work Packages

## Orchestrator Config
max_parallel: 3

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | Foundation | create | pending | — | WP-002 |
| WP-002 | Builds on it | create | pending | WP-001 | — |
"""


def test_single_table_flip_status_unchanged(tmp_path):
    _write_project(tmp_path, _SINGLETABLE_INDEX)  # no WP files
    result = _run(wpx.cmd_flip_status,
                  _ns(tmp_path, wp="WP-001", to="done", expected="pending"))
    assert result["ok"] is True
    assert "| WP-001 | Foundation | create | done |" in _index_text(tmp_path)


def test_single_table_list_ready_falls_back_to_table_deps(tmp_path):
    """No WP files → deps come from the table column (back-compat).
    WP-001 (no deps) ready; WP-002 (dep WP-001 pending) not ready."""
    _write_project(tmp_path, _SINGLETABLE_INDEX)  # no WP files
    result = _run(wpx.cmd_list_ready, _ns(tmp_path))
    assert result["data"]["ready"] == ["WP-001"]


def test_single_table_propagate_blocked_unchanged(tmp_path):
    _write_project(tmp_path, _SINGLETABLE_INDEX)  # no WP files
    result = _run(wpx.cmd_propagate_blocked, _ns(tmp_path, wp="WP-001"))
    assert result["ok"] is True
    assert result["data"]["flipped_to_dependency_blocked"] == ["WP-002"]
    assert "| WP-002 | Builds on it | create | dependency_blocked |" in _index_text(tmp_path)


def test_single_table_with_wp_files_uses_frontmatter_deps(tmp_path):
    """Single-table INDEX WITH WP files present → deps come from
    frontmatter (the canonical source), matching the multi-table path.
    Pins the review's flagged behaviour: frontmatter wins when a file
    exists. Here WP-002's frontmatter dep on WP-001 (pending) keeps it
    not-ready; WP-001 (empty deps) is ready."""
    fm = {"WP-001": [], "WP-002": ["WP-001"]}
    _write_project(tmp_path, _SINGLETABLE_INDEX, frontmatter=fm)
    result = _run(wpx.cmd_list_ready, _ns(tmp_path))
    assert result["data"]["ready"] == ["WP-001"]


# ─── partial WP-file existence (review finding #3/#4) ────────────────────────


def test_partial_wp_files_missing_falls_back_to_table_not_silent_empty(tmp_path):
    """The review's HIGH finding: when SOME WP files exist and others
    don't, a missing-file WP must NOT silently get empty deps (which
    would make it wrongly appear ready). It must fall back to its table
    dep cell.

    Here WP-002 depends on WP-001 (per the INDEX table column). WP-001
    has a frontmatter file; WP-002 does NOT. WP-002 must still be
    recognised as depending on WP-001 (from the table) and therefore
    NOT ready while WP-001 is pending."""
    wp_dir = tmp_path / ".architecture" / "proj" / "work-packages"
    wp_dir.mkdir(parents=True)
    (wp_dir / "INDEX.md").write_text(_SINGLETABLE_INDEX, encoding="utf-8")
    # Only WP-001 gets a file; WP-002 is fileless (mid-migration state).
    (wp_dir / "WP-001-stub.md").write_text(
        "---\nid: WP-001\nstatus: pending\ndependsOn: []\nblocks: []\n---\n",
        encoding="utf-8",
    )
    result = _run(wpx.cmd_list_ready, _ns(tmp_path))
    # WP-002 (fileless, table-dep on WP-001 pending) must NOT be ready.
    assert "WP-002" not in result["data"]["ready"], (
        "fileless WP-002 wrongly became ready — its table dep on WP-001 "
        "was silently dropped (the partial-existence silent-empty bug)"
    )
    assert result["data"]["ready"] == ["WP-001"]


def test_partial_wp_files_present_file_with_empty_deps_is_ready(tmp_path):
    """Distinguish 'file exists, deps empty' (ready) from 'no file'
    (fall back to table). WP-001 has a file with dependsOn: [] → ready
    regardless of any table column content."""
    wp_dir = tmp_path / ".architecture" / "proj" / "work-packages"
    wp_dir.mkdir(parents=True)
    # INDEX claims WP-001 depends on WP-999 (a non-existent WP), but the
    # frontmatter says dependsOn: [] — frontmatter wins, so WP-001 ready.
    index = _SINGLETABLE_INDEX.replace(
        "| WP-001 | Foundation | create | pending | — | WP-002 |",
        "| WP-001 | Foundation | create | pending | WP-999 | WP-002 |",
    )
    (wp_dir / "INDEX.md").write_text(index, encoding="utf-8")
    (wp_dir / "WP-001-stub.md").write_text(
        "---\nid: WP-001\nstatus: pending\ndependsOn: []\nblocks: []\n---\n",
        encoding="utf-8",
    )
    result = _run(wpx.cmd_list_ready, _ns(tmp_path))
    # Frontmatter [] beats the table's bogus WP-999 dep → WP-001 ready.
    assert "WP-001" in result["data"]["ready"]


# ─── WP-001 (CH-5DMB1N): widened WP-id matcher + back-compat guard ────────────
#
# WP ids gain a change-handle prefix `{CH-HANDLE}-WP-NNN` (e.g.
# CH-5DMB1N-WP-001) alongside the retained legacy bare `WP-NNN` and the existing
# source-tagged `WP-{SOURCE}-{NNN}`. The recognition is defined ONCE in
# _wpxlib.py (`_WP_ID_RE` + `is_wp_id` + `wp_nnn_suffix`) and every caller reuses
# it — mirroring the `_WP_TABLE_HEADER_RE` / `validate_wp_index_header`
# single-source-of-truth discipline (#60, EP-03; ADR-001/ADR-002).

import _wpxlib  # noqa: E402  (sys.path wired by tests/conftest.py)


# An INDEX carrying BOTH a prefixed row and a legacy bare row in the SAME table.
# The load-bearing back-compat fixture: parse_index_md must return both.
_BOTH_SHAPES_INDEX = """# Work Package Index — both shapes

## WP table

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| CH-5DMB1N-WP-001 | Prefixed mint | extend | pending | — | — |
| WP-002 | Legacy bare | create | pending | — | — |
| WP-HD-AA-001 | Source-tagged | create | pending | — | — |
"""


@pytest.mark.parametrize(
    "wp_id",
    ["CH-5DMB1N-WP-001", "WP-002", "WP-HD-AA-001"],
)
def test_parse_index_keeps_prefixed_and_bare_ids(tmp_path, wp_id):
    """LOAD-BEARING regression guard (ADR-002 one-release back-compat).

    A single parse of an INDEX containing one prefixed `CH-…-WP-NNN` row, one
    legacy bare `WP-NNN` row, and one source-tagged `WP-{SOURCE}-{NNN}` row must
    return ALL of them with their ids intact. FAILS today: the prefixed row is
    silently dropped by the `startswith("WP-")` row-filter in parse_index_md —
    proving the silent-drop the widened matcher closes.
    """
    wp_dir = tmp_path / ".architecture" / "proj" / "work-packages"
    wp_dir.mkdir(parents=True)
    index_path = wp_dir / "INDEX.md"
    index_path.write_text(_BOTH_SHAPES_INDEX, encoding="utf-8")

    rows = _wpxlib.parse_index_md(index_path)
    ids = {row.id for row in rows}
    assert wp_id in ids, (
        f"{wp_id!r} dropped by parse_index_md — both shapes must survive one "
        f"release (got ids: {sorted(ids)})"
    )


def test_parse_index_both_shapes_in_one_parse(tmp_path):
    """The same guard stated as a single both-shapes assertion: a prefixed and a
    legacy bare row survive the SAME parse."""
    wp_dir = tmp_path / ".architecture" / "proj" / "work-packages"
    wp_dir.mkdir(parents=True)
    index_path = wp_dir / "INDEX.md"
    index_path.write_text(_BOTH_SHAPES_INDEX, encoding="utf-8")

    ids = {row.id for row in _wpxlib.parse_index_md(index_path)}
    assert {"CH-5DMB1N-WP-001", "WP-002"} <= ids


# ─── is_wp_id — the single recogniser ────────────────────────────────────────


@pytest.mark.parametrize(
    "candidate",
    [
        "CH-5DMB1N-WP-001",   # prefixed (the new mint)
        "WP-001",             # legacy bare
        "WP-002",
        "WP-HD-AA-001",       # source-tagged
        "WP-S2-PERMS",        # source-tagged, alpha suffix
    ],
)
def test_is_wp_id_accepts_all_three_shapes(candidate):
    assert _wpxlib.is_wp_id(candidate) is True


@pytest.mark.parametrize(
    "candidate",
    [
        "",                    # blank
        "Totals",              # a summary row
        "SRD-001",             # a different artifact id
        "CH-5DMB1N",           # a change handle, not a WP id
        "WP",                  # bare prefix, no number
        "notes",
    ],
)
def test_is_wp_id_rejects_non_wp_strings(candidate):
    assert _wpxlib.is_wp_id(candidate) is False


# ─── wp_nnn_suffix — the clean-tail extractor (branch cleanliness) ───────────


@pytest.mark.parametrize(
    "wp_id,expected",
    [
        # Prefixed id: CH-<HANDLE>- AND the wp- prefix stripped → clean NNN tail
        # (the `wp-` is re-added by _branch_name's f-string, exactly as for a
        # bare id — so the branch is `wp/{scope}/wp-001-{slug}`, not the doubled
        # `wp/{scope}/wp-ch-5dmb1n-wp-001-{slug}`).
        ("CH-5DMB1N-WP-001", "001"),
        # Legacy bare: byte-for-byte what `wp_id.lower().removeprefix("wp-")`
        # produced before this change.
        ("WP-001", "001"),
        ("wp-7", "7"),
        # Source-tagged: tail unchanged (no CH- prefix to strip; the `wp-` is
        # stripped just as today).
        ("WP-HD-AA-001", "hd-aa-001"),
    ],
)
def test_wp_nnn_suffix_strips_change_prefix_only(wp_id, expected):
    """`wp_nnn_suffix` returns the NNN tail (lowercased, `wp-` stripped) that
    `_branch_name` re-prefixes with `wp-`. For a prefixed id the CH-<HANDLE>-
    prefix is stripped FIRST so the branch stays clean. For bare/source-tagged
    ids the result is byte-for-byte today's `removeprefix("wp-")` output."""
    assert _wpxlib.wp_nnn_suffix(wp_id) == expected


# ─── _normalise_wp_reference — prefixed full-id detection ────────────────────


def test_normalise_recognises_prefixed_full_id():
    """A prefixed ref is recognised as a FULL id (passthrough/unknown), not
    mistaken for a short suffix to resolve."""
    known = {"WP-002"}
    resolved, status = _wpxlib._normalise_wp_reference("CH-5DMB1N-WP-001", known)
    assert resolved == "CH-5DMB1N-WP-001"
    assert status == "unknown"


def test_normalise_short_suffix_resolves_to_prefixed_known_id():
    """The retained short-suffix path still resolves `PERMS` → a prefixed known
    id (the `endswith` logic is prefix-agnostic and untouched)."""
    known = {"CH-5DMB1N-WP-PERMS"}
    resolved, status = _wpxlib._normalise_wp_reference("PERMS", known)
    assert resolved == "CH-5DMB1N-WP-PERMS"
    assert status == "normalised"
