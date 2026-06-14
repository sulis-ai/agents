"""Tests for ``_change_session`` — the deterministic per-change Claude session
identity + transcript-resumability helpers (focus-resumes-prior-session).

Design decision (recorded in the module + commit): we PIN a deterministic
``claude --session-id <uuid>`` at first spawn, derived from the change ULID, so
the id is known up front (no need to scrape the id claude assigned). On focus
the SAME derived id is passed as ``--resume <uuid>`` iff that change's transcript
actually exists under ``~/.claude/projects/<mangled-worktree>/<uuid>.jsonl``.
Pinned-id beats transcript-discovery: the id is a pure function of the change,
recorded at spawn, and resumability is a single deterministic file check — no
"most-recent transcript" heuristic, no dependency on the daemon still holding
the session (so a janitor-reaped session is still resumable; its transcript
persists).
"""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

import _change_session as cs

_CHANGE_ID = "01KTKB8KSD6G2EMZZNPD0TNPHH"
_OTHER_CHANGE_ID = "01KTGYDA7XJDGAMGBEMGXR9YF0"


# ── change_session_id: deterministic, valid UUID, per-change ────────────────


def test_session_id_is_a_valid_uuid():
    """``claude --session-id`` requires a valid UUID; the derived id must be one."""
    sid = cs.change_session_id(_CHANGE_ID)
    # Round-trips through uuid.UUID without raising → it is a valid UUID string.
    assert str(uuid.UUID(sid)) == sid


def test_session_id_is_deterministic():
    """Same change ULID → same session id, every call (so the spawn-time pin and
    the focus-time resume ref always agree without recording the raw uuid)."""
    assert cs.change_session_id(_CHANGE_ID) == cs.change_session_id(_CHANGE_ID)


def test_session_id_differs_per_change():
    """Two changes never collide onto the same conversation."""
    assert cs.change_session_id(_CHANGE_ID) != cs.change_session_id(_OTHER_CHANGE_ID)


def test_session_id_rejects_bad_change_id():
    """A non-ULID change id is refused rather than silently mangled into a uuid."""
    with pytest.raises(ValueError):
        cs.change_session_id("not-a-ulid")


# ── claude_project_dir: the ~/.claude/projects mangling ─────────────────────


def test_claude_project_dir_mangles_path(monkeypatch, tmp_path):
    """Claude stores transcripts under a dir named by replacing every ``/`` and
    ``.`` in the absolute worktree path with ``-`` (verified against a real
    ~/.claude/projects dir)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    wt = "/Users/iain/.sulis/changes/01KTR56K1ZRDJ8SD0KFRME81PT/worktree"
    got = cs.claude_project_dir(wt)
    assert got == (
        tmp_path
        / ".claude"
        / "projects"
        / "-Users-iain--sulis-changes-01KTR56K1ZRDJ8SD0KFRME81PT-worktree"
    )


# ── transcript_path + has_resumable_transcript ──────────────────────────────


def test_transcript_path_is_session_id_jsonl(monkeypatch, tmp_path):
    """The transcript filename IS the (pinned) session id + ``.jsonl`` inside the
    mangled project dir."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    wt = str(tmp_path / "wt")
    sid = cs.change_session_id(_CHANGE_ID)
    assert cs.transcript_path(_CHANGE_ID, wt).name == f"{sid}.jsonl"


def test_has_resumable_transcript_false_when_absent(monkeypatch, tmp_path):
    """No transcript on disk → not resumable (so focus falls back to a fresh
    self-orienting spawn — today's #93 default preserved)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    wt = str(tmp_path / "wt")
    Path(wt).mkdir()
    assert cs.has_resumable_transcript(_CHANGE_ID, wt) is False


def test_has_resumable_transcript_false_when_empty(monkeypatch, tmp_path):
    """An empty transcript file (claude wrote nothing) → not resumable."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    wt = str(tmp_path / "wt")
    Path(wt).mkdir()
    tp = cs.transcript_path(_CHANGE_ID, wt)
    tp.parent.mkdir(parents=True, exist_ok=True)
    tp.write_text("")
    assert cs.has_resumable_transcript(_CHANGE_ID, wt) is False


def test_has_resumable_transcript_true_when_present(monkeypatch, tmp_path):
    """A non-empty transcript at the pinned id → resumable (focus passes the
    derived id as the resume ref)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    wt = str(tmp_path / "wt")
    Path(wt).mkdir()
    tp = cs.transcript_path(_CHANGE_ID, wt)
    tp.parent.mkdir(parents=True, exist_ok=True)
    tp.write_text('{"type":"summary"}\n')
    assert cs.has_resumable_transcript(_CHANGE_ID, wt) is True


def test_has_resumable_transcript_does_not_need_daemon(monkeypatch, tmp_path):
    """Resumability is a pure filesystem check on the persisted transcript — it
    does NOT consult the daemon / session.json. A janitor-reaped (intentionally
    shut-down) session whose transcript persists is therefore still resumable
    via focus (Step 3)."""
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    wt = str(tmp_path / "wt")
    Path(wt).mkdir()
    tp = cs.transcript_path(_CHANGE_ID, wt)
    tp.parent.mkdir(parents=True, exist_ok=True)
    tp.write_text('{"type":"summary"}\n')
    # No session.json anywhere under ~/.sulis — proves no daemon/session-state
    # dependency.
    assert cs.has_resumable_transcript(_CHANGE_ID, wt) is True
