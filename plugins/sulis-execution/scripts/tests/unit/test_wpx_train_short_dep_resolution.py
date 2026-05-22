"""Unit tests for v0.16.2 — short WP-name resolution in dep check.

The bug: INDEX.md "Depends On" column accepts short names (e.g. PERMS,
MANIFEST) but the dependency check compares them against full WP IDs
(WP-S2-PERMS, WP-S2-MANIFEST). String inequality → dep reads as not-
merged → WP marked ineligible even though deps are done.

Fix: normalise short → full at parse time via unique-suffix matching.
These tests pin all 4 cases:
- passthrough (already full)
- normalised (unique suffix match)
- unknown (no match; preserves original)
- ambiguous (multiple matches; raises clear error)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPTS_DIR))

from _wpxlib import (  # noqa: E402
    _normalise_wp_reference,
    parse_index_md,
)


# ─── _normalise_wp_reference helper ───────────────────────────────────────


def test_normalise_full_id_passes_through():
    """An already-full WP ID should pass through unchanged."""
    known = {"WP-S2-PERMS", "WP-S2-MANIFEST"}
    ref, status = _normalise_wp_reference("WP-S2-PERMS", known)
    assert ref == "WP-S2-PERMS"
    assert status == "passthrough"


def test_normalise_unique_suffix_match_resolves():
    """Short name matching exactly one full ID → normalised."""
    known = {"WP-S2-PERMS", "WP-S2-MANIFEST", "WP-S2-MCP-STUB"}
    ref, status = _normalise_wp_reference("PERMS", known)
    assert ref == "WP-S2-PERMS"
    assert status == "normalised"


def test_normalise_multi_word_short_name_resolves():
    """Short name with hyphen also works (e.g. MCP-STUB → WP-S2-MCP-STUB)."""
    known = {"WP-S2-MCP-STUB", "WP-S2-PERMS"}
    ref, status = _normalise_wp_reference("MCP-STUB", known)
    assert ref == "WP-S2-MCP-STUB"
    assert status == "normalised"


def test_normalise_unknown_name_returns_original():
    """No match → returns original ref with 'unknown' status."""
    known = {"WP-S2-PERMS"}
    ref, status = _normalise_wp_reference("NOTAREAL-WP", known)
    assert ref == "NOTAREAL-WP"
    assert status == "unknown"


def test_normalise_unknown_full_id_returns_original():
    """A WP- prefixed ref that isn't in known_wps → returns as 'unknown'."""
    known = {"WP-S2-PERMS"}
    ref, status = _normalise_wp_reference("WP-S3-NEW", known)
    assert ref == "WP-S3-NEW"
    assert status == "unknown"


def test_normalise_ambiguous_raises_with_candidates_listed():
    """Short name matching multiple WPs → ValueError naming all candidates."""
    known = {"WP-S1-PERMS", "WP-S2-PERMS"}
    with pytest.raises(ValueError) as exc_info:
        _normalise_wp_reference("PERMS", known)
    msg = str(exc_info.value)
    assert "Ambiguous" in msg
    assert "WP-S1-PERMS" in msg
    assert "WP-S2-PERMS" in msg
    assert "disambiguate" in msg.lower() or "Disambiguate" in msg


# ─── parse_index_md integration ───────────────────────────────────────────


def _write_index(path: Path, content: str) -> None:
    path.write_text(content.strip() + "\n", encoding="utf-8")


def test_parse_index_normalises_short_deps(tmp_path):
    """Real-world bug reproducer: INDEX with short-name deps should be
    parsed with full IDs after the normalisation pass."""
    index = tmp_path / "INDEX.md"
    _write_index(index, """
| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-S2-PERMS | Permission descriptors | create | done | — | — |
| WP-S2-MANIFEST | Instantiation manifest | create | done | — | — |
| WP-S2-MCP-STUB | MCP registry stub | create | done | — | — |
| WP-S2-LOADER-CORE | Orchestrator + errors | create | step-7-complete | PERMS, MANIFEST, MCP-STUB | — |
""")
    rows = parse_index_md(index)
    loader_core = next(r for r in rows if r.id == "WP-S2-LOADER-CORE")
    # All three short-name deps must be resolved to full IDs
    assert loader_core.depends_on == [
        "WP-S2-PERMS",
        "WP-S2-MANIFEST",
        "WP-S2-MCP-STUB",
    ]


def test_parse_index_passes_through_full_ids(tmp_path):
    """If INDEX already uses full IDs, they pass through unchanged."""
    index = tmp_path / "INDEX.md"
    _write_index(index, """
| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-S2-A | A | create | done | — | — |
| WP-S2-B | B | create | step-7-complete | WP-S2-A | — |
""")
    rows = parse_index_md(index)
    wp_b = next(r for r in rows if r.id == "WP-S2-B")
    assert wp_b.depends_on == ["WP-S2-A"]


def test_parse_index_mixed_short_and_full_deps(tmp_path):
    """An INDEX with a mix of short + full deps should resolve both."""
    index = tmp_path / "INDEX.md"
    _write_index(index, """
| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-S2-A | A | create | done | — | — |
| WP-S2-B | B | create | done | — | — |
| WP-S2-C | C | create | step-7-complete | A, WP-S2-B | — |
""")
    rows = parse_index_md(index)
    wp_c = next(r for r in rows if r.id == "WP-S2-C")
    assert wp_c.depends_on == ["WP-S2-A", "WP-S2-B"]


def test_parse_index_unknown_short_name_preserved(tmp_path):
    """A short name with no match should be preserved (not silently dropped)."""
    index = tmp_path / "INDEX.md"
    _write_index(index, """
| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-S2-A | A | create | done | — | — |
| WP-S2-B | B | create | step-7-complete | TYPO-NAME | — |
""")
    rows = parse_index_md(index)
    wp_b = next(r for r in rows if r.id == "WP-S2-B")
    # TYPO-NAME doesn't match anything; preserved as-is so downstream
    # dep check fails visibly (the WP is genuinely blocked)
    assert wp_b.depends_on == ["TYPO-NAME"]


def test_parse_index_ambiguous_short_name_raises(tmp_path):
    """If a short name matches multiple WPs, parsing raises ValueError."""
    index = tmp_path / "INDEX.md"
    _write_index(index, """
| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-S1-PERMS | Slice 1 perms | create | done | — | — |
| WP-S2-PERMS | Slice 2 perms | create | done | — | — |
| WP-S2-LOADER | Loader | create | step-7-complete | PERMS | — |
""")
    with pytest.raises(ValueError, match="Ambiguous"):
        parse_index_md(index)


def test_parse_index_normalises_blocks_column_too(tmp_path):
    """The Blocks column also uses dep-like references; normalised too."""
    index = tmp_path / "INDEX.md"
    _write_index(index, """
| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-S2-FOO | Foo | create | done | — | BAR, BAZ |
| WP-S2-BAR | Bar | create | pending | — | — |
| WP-S2-BAZ | Baz | create | pending | — | — |
""")
    rows = parse_index_md(index)
    wp_foo = next(r for r in rows if r.id == "WP-S2-FOO")
    assert wp_foo.blocks == ["WP-S2-BAR", "WP-S2-BAZ"]


def test_parse_index_verbose_normalisations_logs(tmp_path, capsys):
    """When verbose_normalisations=True, normalisations are logged to stderr."""
    index = tmp_path / "INDEX.md"
    _write_index(index, """
| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-S2-PERMS | Permissions | create | done | — | — |
| WP-S2-LOADER | Loader | create | step-7-complete | PERMS | — |
""")
    parse_index_md(index, verbose_normalisations=True)
    captured = capsys.readouterr()
    # The _log function writes to stderr
    assert "PERMS" in captured.err
    assert "WP-S2-PERMS" in captured.err
    assert "normalised" in captured.err
