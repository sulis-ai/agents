"""Tests for ``session_viewer._build_open_spec`` — the desktop viewer resumes
the prior conversation when one exists (focus-resumes-prior-session).

The viewer is what every change window execs (the launcher's default exec line).
It sends ``open {key, spec}`` to the daemon. When a prior transcript exists for
the change's pinned conversation, the spec carries ``resume_ref`` = the pinned
session id, so the daemon (when it actually spawns — focus / janitor-reaped /
recreate) resumes that conversation. When none exists (a never-opened change,
today's fresh-spawn case) the spec omits ``resume_ref`` and the session
self-orients from the brief — the #93 default, unchanged.

``open`` is get-or-spawn/idempotent: when a session is already live in the
daemon the existing spec wins and ``resume_ref`` is moot. It only takes effect
when the daemon actually spawns — exactly the focus/eviction case the resume is
for, and it does NOT depend on the daemon still holding the session (the
transcript persists on disk).
"""

from __future__ import annotations

from pathlib import Path

import _change_session as cs
import session_viewer

_CHANGE_ID = "01KTKB8KSD6G2EMZZNPD0TNPHH"


def test_open_spec_has_pty_basics():
    """The spec keeps the existing pty contract: provider/cwd/io_mode/
    brief_change_id are unchanged (the brief target is the same change id)."""
    spec = session_viewer._build_open_spec(_CHANGE_ID, "/tmp/wt")
    assert spec["provider"] == "pty"
    assert spec["cwd"] == "/tmp/wt"
    assert spec["io_mode"] == "pty"
    assert spec["brief_change_id"] == _CHANGE_ID


def test_open_spec_omits_resume_when_no_transcript(monkeypatch, tmp_path):
    """No prior transcript → no ``resume_ref``: the daemon spawns fresh and the
    session self-orients (today's #93 default preserved)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    wt = str(tmp_path / "wt")
    Path(wt).mkdir()
    spec = session_viewer._build_open_spec(_CHANGE_ID, wt)
    assert spec.get("resume_ref") is None


def test_open_spec_sets_resume_when_transcript_present(monkeypatch, tmp_path):
    """A prior transcript at the pinned id → ``resume_ref`` = that pinned id, so
    the resumed session loads the prior conversation (picks up where the founder
    left off)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    wt = str(tmp_path / "wt")
    Path(wt).mkdir()
    tp = cs.transcript_path(_CHANGE_ID, wt)
    tp.parent.mkdir(parents=True, exist_ok=True)
    tp.write_text('{"type":"summary"}\n')

    spec = session_viewer._build_open_spec(_CHANGE_ID, wt)
    assert spec["resume_ref"] == cs.change_session_id(_CHANGE_ID)


def test_open_spec_resume_independent_of_daemon_state(monkeypatch, tmp_path):
    """Resumability is a pure transcript check — no session.json / daemon lookup.
    A janitor-reaped session (intentionally shut down) whose transcript persists
    is still resumed via focus (Step 3)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    wt = str(tmp_path / "wt")
    Path(wt).mkdir()
    tp = cs.transcript_path(_CHANGE_ID, wt)
    tp.parent.mkdir(parents=True, exist_ok=True)
    tp.write_text('{"type":"summary"}\n')
    # No ~/.sulis/changes/<id>/session.json exists — proves no daemon dependency.
    spec = session_viewer._build_open_spec(_CHANGE_ID, wt)
    assert spec["resume_ref"] == cs.change_session_id(_CHANGE_ID)
