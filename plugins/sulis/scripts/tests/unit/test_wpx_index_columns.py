"""Unit tests for the shared WP INDEX column resolver (L-02).

Two parsers used to disagree on the "depends" column header — wpx-index
keyed on "depends", parse_index_md on "depends on" — so a correctly-
generated INDEX (canonical header "Depends On") was silently rejected by
list-ready. `resolve_wp_columns` is now the single source of truth both
call; these tests pin that every spelling variant collapses to one key, and
that parse_index_md reads dependencies regardless of which spelling the
INDEX uses.
"""

from __future__ import annotations

from pathlib import Path

from _wpxlib import parse_index_md, resolve_wp_columns


def _parse(tmp_path: Path, index_text: str):
    """parse_index_md reads a file path; write the INDEX to tmp and parse."""
    p = tmp_path / "INDEX.md"
    p.write_text(index_text, encoding="utf-8")
    return parse_index_md(p)


# ─── resolve_wp_columns: spelling variants collapse to canonical keys ───────


def test_depends_spellings_all_resolve_to_one_key():
    for header in ["Depends", "Depends On", "depends on", "DEPENDS ON",
                   "Depends_On", "depends-on", "Depends On *"]:
        cols = resolve_wp_columns(["ID", "Status", header])
        assert cols.get("depends") == 2, f"{header!r} did not resolve to 'depends'"


def test_canonical_columns_resolve():
    cols = resolve_wp_columns(
        ["ID", "Title", "Primitive", "Status", "Depends On", "Blocks"]
    )
    assert cols == {
        "id": 0, "title": 1, "primitive": 2,
        "status": 3, "depends": 4, "blocks": 5,
    }


def test_unknown_headers_are_ignored():
    cols = resolve_wp_columns(["ID", "Status", "Token (in/out)", "TDD §"])
    assert set(cols) == {"id", "status"}  # extras not in the alias map


def test_kind_resolves_as_primitive_alias():
    # kind: backend|frontend|... is the WP kind; primitive is the change
    # primitive. They share the column slot in some tables — accept "kind".
    cols = resolve_wp_columns(["ID", "Kind", "Status"])
    assert cols.get("primitive") == 1


# ─── parse_index_md: both header spellings now read dependencies ────────────

_INDEX_DEPENDS_ON = """# Work Packages

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | Foundation | create | pending | — | WP-002 |
| WP-002 | Builds on it | create | pending | WP-001 | — |
"""

_INDEX_DEPENDS = """# Work Packages

| ID | Title | Primitive | Status | Depends | Blocks |
|---|---|---|---|---|---|
| WP-001 | Foundation | create | pending | — | WP-002 |
| WP-002 | Builds on it | create | pending | WP-001 | — |
"""


def test_parse_index_reads_depends_on_header(tmp_path):
    rows = _parse(tmp_path, _INDEX_DEPENDS_ON)
    by_id = {r.id: r for r in rows}
    assert by_id["WP-002"].depends_on == ["WP-001"]
    assert by_id["WP-001"].depends_on == []


def test_parse_index_reads_depends_header(tmp_path):
    # This spelling silently lost dependencies before L-02 (parse_index_md
    # only looked for "depends on").
    rows = _parse(tmp_path, _INDEX_DEPENDS)
    by_id = {r.id: r for r in rows}
    assert by_id["WP-002"].depends_on == ["WP-001"]


def test_parse_index_extras_exclude_resolved_columns(tmp_path):
    index = """# Work Packages

| ID | Title | Primitive | Status | Depends On | Blocks | Token |
|---|---|---|---|---|---|---|
| WP-001 | Foo | create | pending | — | — | 5k |
"""
    rows = _parse(tmp_path, index)
    # Token is the only non-standard column → the only extra.
    assert list(rows[0].extras) == ["Token"]
