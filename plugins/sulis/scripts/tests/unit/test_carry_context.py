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


# ─── #124: walk the ancestry chain to origin (multi-hop back-nav) ──────────


def _chain_reader(records_by_id):
    return lambda cid: records_by_id.get(cid)


def test_walk_ancestry_follows_parent_change_to_origin():
    # C -> B -> A (A is origin, no parent_change).
    recs = {
        "C": {"change_id": "C", "handle": "CH-C", "parent_change": "B"},
        "B": {"change_id": "B", "handle": "CH-B", "parent_change": "A"},
        "A": {"change_id": "A", "handle": "CH-A"},
    }
    chain = _mod._walk_ancestry("C", _chain_reader(recs))
    assert [r["change_id"] for r in chain] == ["C", "B", "A"]  # immediate→origin


def test_walk_ancestry_is_cycle_safe():
    recs = {"X": {"change_id": "X", "parent_change": "Y"},
            "Y": {"change_id": "Y", "parent_change": "X"}}  # cycle
    chain = _mod._walk_ancestry("X", _chain_reader(recs))
    ids = [r["change_id"] for r in chain]
    assert ids == ["X", "Y"]  # each visited once, no infinite loop


def test_walk_ancestry_stops_at_missing_record():
    recs = {"C": {"change_id": "C", "parent_change": "GONE"}}
    chain = _mod._walk_ancestry("C", _chain_reader(recs))
    assert [r["change_id"] for r in chain] == ["C"]  # GONE doesn't resolve


def test_section_with_ancestry_lists_lineage_and_origin_excerpt():
    immediate = {"change_id": "B", "handle": "CH-B", "slug": "mid"}
    origin = {"change_id": "A", "handle": "CH-A", "slug": "the-origin-idea"}
    s = _carried_context_section(
        immediate, "builds_on", "B's working set.",
        ancestry=[origin], origin_working_set="A: the original idea was X.")
    assert "CH-B" in s and "B's working set." in s        # immediate hop
    assert "lineage" in s.lower()                          # the chain is shown
    assert "CH-A" in s                                     # origin link
    assert "A: the original idea was X." in s              # origin excerpt carried


def test_section_no_ancestry_is_unchanged_single_hop():
    # Backward-compat: ancestry omitted → the #123 single-hop section, no lineage.
    s = _carried_context_section(_PARENT, "builds_on", "body")
    assert "lineage" not in s.lower()


def test_resolve_carries_full_chain_for_a_two_hop_change(monkeypatch, tmp_path):
    # B started from A; C started from B. From C, the carry should surface the
    # lineage to A (origin) + A's Working Set, not just B.
    pwa = tmp_path / "wt-a"
    (pwa / ".changes").mkdir(parents=True)
    (pwa / ".changes" / "feat-origin.WORKING-SET.md").write_text(
        "Origin idea: the whole thing started here.", encoding="utf-8")
    pwb = tmp_path / "wt-b"
    (pwb / ".changes").mkdir(parents=True)
    (pwb / ".changes" / "feat-mid.WORKING-SET.md").write_text(
        "Mid hop reasoning.", encoding="utf-8")
    recs = {
        "B": {"change_id": "B", "handle": "CH-B", "slug": "mid",
              "primitive": "feat", "worktree_path": str(pwb), "parent_change": "A"},
        "A": {"change_id": "A", "handle": "CH-A", "slug": "origin",
              "primitive": "feat", "worktree_path": str(pwa)},
    }
    monkeypatch.setenv("SULIS_CHANGE_ID", "B")  # C is launched from B
    monkeypatch.setattr(_mod, "read_change_record", _chain_reader(recs))
    pid, section, rel = _mod._resolve_parent_carry("builds_on")
    assert pid == "B"
    assert "Mid hop reasoning." in section                 # immediate parent
    assert "Origin idea: the whole thing started here." in section  # origin carried
    assert "CH-A" in section and "lineage" in section.lower()       # lineage to origin
