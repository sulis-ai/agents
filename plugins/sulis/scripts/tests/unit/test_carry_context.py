"""Unit tests for cross-session context-carry (#123).

When change B is started from inside change A's session (SULIS_CHANGE_ID set),
`sulis-change start` records a durable link (parent + relationship) and seeds
B's pre-spawn CONTEXT.md with a "Carried from {A}" section drawn from A's
Working Set — so the context travels (durable carry), and B *discovers* it via
the CONTEXT.md it already reads at startup. No live inter-session wire (the
critical-thinking spiral's call: it's a state gap, not a transport gap).

`_carried_context_section` + `_excerpt_working_set` are the pure builders;
cmd_start wires the parent resolution + the append. Tested here.
"""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]


def _load():
    loader = SourceFileLoader("sulis_change_mod", str(_SCRIPTS / "sulis-change"))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_mod = _load()
_carried_context_section = _mod._carried_context_section
_excerpt_working_set = _mod._excerpt_working_set

_PARENT = {"change_id": "01JPARENT0000000000000000", "handle": "CH-01JPAR",
           "slug": "introduce-payments"}


# ─── _excerpt_working_set ──────────────────────────────────────────────────


def test_excerpt_returns_short_text_whole():
    assert _excerpt_working_set("short body") == "short body"


def test_excerpt_truncates_long_text_with_marker():
    out = _excerpt_working_set("x" * 5000, max_chars=100)
    assert len(out) < 5000
    assert "truncated" in out.lower()


def test_excerpt_empty_is_empty_string():
    assert _excerpt_working_set("") == ""
    assert _excerpt_working_set(None) == ""
    assert _excerpt_working_set("   \n  ") == ""


# ─── _carried_context_section ──────────────────────────────────────────────


def test_section_names_parent_relationship_and_link():
    s = _carried_context_section(_PARENT, "builds_on", "Problem: ship payments.")
    assert "CH-01JPAR" in s            # the parent handle (the link)
    assert "builds_on" in s            # the relationship
    assert "01JPARENT0000000000000000" in s  # the durable change_id
    assert "introduce-payments" in s   # the readable slug


def test_section_includes_the_working_set_excerpt_when_present():
    s = _carried_context_section(_PARENT, "depends_on", "Problem: ship payments.")
    assert "Problem: ship payments." in s
    assert "depends_on" in s


def test_section_falls_back_when_parent_working_set_empty():
    s = _carried_context_section(_PARENT, "builds_on", "")
    # No excerpt → tell B to follow the link and read the parent's artifacts,
    # never a silent empty carry.
    assert "follow the link" in s.lower() or "read its artifacts" in s.lower()
    assert "CH-01JPAR" in s  # the link is still there to follow


def test_section_defaults_relationship_when_blank():
    s = _carried_context_section(_PARENT, "", "body")
    assert "builds_on" in s  # sensible default, never an empty relationship


# ─── _resolve_parent_carry (the resolution glue) ───────────────────────────


def test_resolve_no_parent_in_env_carries_nothing(monkeypatch):
    monkeypatch.delenv("SULIS_CHANGE_ID", raising=False)
    pid, section, rel = _mod._resolve_parent_carry("builds_on")
    assert pid is None and section is None


def test_resolve_reads_parent_working_set_and_builds_section(monkeypatch, tmp_path):
    # Parent worktree with a populated Working Set at the conventional path.
    pw = tmp_path / "parent-wt"
    (pw / ".changes").mkdir(parents=True)
    (pw / ".changes" / "feat-introduce-payments.WORKING-SET.md").write_text(
        "# Working Set\n## 1. Problem\nShip Stripe payments.\n", encoding="utf-8")
    monkeypatch.setenv("SULIS_CHANGE_ID", _PARENT["change_id"])
    monkeypatch.setattr(_mod, "read_change_record", lambda cid: {
        **_PARENT, "primitive": "feat", "worktree_path": str(pw)})
    pid, section, rel = _mod._resolve_parent_carry("depends_on")
    assert pid == _PARENT["change_id"]
    assert rel == "depends_on"
    assert "Ship Stripe payments." in section   # the real excerpt carried
    assert "CH-01JPAR" in section                # the link


def test_resolve_links_even_when_working_set_absent(monkeypatch, tmp_path):
    # Parent exists but has no Working Set → still link (section with fallback),
    # never a silent no-link.
    monkeypatch.setenv("SULIS_CHANGE_ID", _PARENT["change_id"])
    monkeypatch.setattr(_mod, "read_change_record", lambda cid: {
        **_PARENT, "primitive": "feat", "worktree_path": str(tmp_path / "nope")})
    pid, section, rel = _mod._resolve_parent_carry("builds_on")
    assert pid == _PARENT["change_id"]
    assert section is not None and "CH-01JPAR" in section


def test_resolve_degrades_when_parent_record_missing(monkeypatch):
    monkeypatch.setenv("SULIS_CHANGE_ID", "01JGHOST000000000000000000")
    monkeypatch.setattr(_mod, "read_change_record", lambda cid: None)
    pid, section, rel = _mod._resolve_parent_carry("builds_on")
    assert pid == "01JGHOST000000000000000000" and section is None
