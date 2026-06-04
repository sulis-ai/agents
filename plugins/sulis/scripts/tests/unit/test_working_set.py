"""Tests for `_working_set.py` — the Working Set's mechanical core.

The Working Set carries current thinking (problem/solution/decisions) + the *why*
across a session boundary. This module owns only the deterministic parts: the
six-section template, the append-only log, the conventional path.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from _working_set import append_log_line, render_initial, working_set_path

_AT = "2026-06-04T09:00:00Z"


class TestPath:
    def test_conventional_path_matches_sibling_change_artifacts(self) -> None:
        p = working_set_path("/repo", "feat-add-login")
        assert p == Path("/repo/.changes/feat-add-login.WORKING-SET.md")


class TestRenderInitial:
    def test_has_all_six_sections(self) -> None:
        t = render_initial("feat-x", at=_AT)
        for heading in (
            "## 1. Problem", "## 2. Current best solution",
            "## 3. Decisions in flight", "## 4. Open questions",
            "## 5. Rejected so far", "## 6. Working log",
        ):
            assert heading in t, f"missing {heading}"

    def test_seeds_problem_from_intent(self) -> None:
        t = render_initial("feat-x", intent="users can reset their password", at=_AT)
        assert "users can reset their password" in t

    def test_unseeded_problem_has_a_placeholder(self) -> None:
        t = render_initial("feat-x", at=_AT)
        assert "not yet framed" in t.lower()

    def test_log_seeded_with_creation_line(self) -> None:
        t = render_initial("feat-x", at=_AT)
        assert f"- {_AT} — Working Set created." in t


class TestAppendLog:
    def test_appends_timestamped_line_at_end(self) -> None:
        base = render_initial("feat-x", at=_AT)
        out = append_log_line(base, "locked the auth approach", at="2026-06-04T10:00:00Z")
        assert out.rstrip().endswith("- 2026-06-04T10:00:00Z — locked the auth approach")
        # original creation line still present (append-only, not overwritten)
        assert f"- {_AT} — Working Set created." in out

    def test_append_is_additive_not_destructive(self) -> None:
        base = render_initial("feat-x", at=_AT)
        out = append_log_line(base, "first", at="2026-06-04T10:00:00Z")
        out = append_log_line(out, "second", at="2026-06-04T11:00:00Z")
        assert "first" in out and "second" in out
        assert out.count("## 6. Working log") == 1  # didn't duplicate the section

    def test_malformed_file_raises(self) -> None:
        with pytest.raises(ValueError, match="Working log"):
            append_log_line("# not a working set\n", "x", at=_AT)
