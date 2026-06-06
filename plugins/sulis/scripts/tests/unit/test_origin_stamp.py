"""WP-P12 — the origin-stamp writer (ADR-013).

Origin is stamped at commit time as a git commit trailer in the two existing
write paths (executor + chat-relay), the same family as `Co-Authored-By:`:

    Sulis-Origin: autonomous; run=<lifecyclerun-ulid>; confidence=<0..1>
    Sulis-Origin: assisted; conversation=<id>; turn=<n>

Append-only metadata on a commit the path already makes — no new commit, no
process, no network. A stamp FAILURE is non-fatal: the commit still lands and
origin falls back to inferred. Where a trailer can't be written, a sidecar
`.sulis/origin/<sha>.json` is the fallback.

These tests pin the writer (outside apps/cockpit/, the read-only surface).
"""

from __future__ import annotations

import json
import subprocess

import pytest

from _origin_stamp import (
    autonomous_origin,
    assisted_origin,
    format_trailer,
    parse_origin_env,
    stamp_origin,
    write_sidecar,
)


# ─── the trailer line (the CF-11 pinned shape) ────────────────────────────


def test_autonomous_trailer_shape():
    origin = autonomous_origin(run="01KT500K2JTE2EGW6TPPQ4D4VN", confidence=0.9)
    assert (
        format_trailer(origin)
        == "Sulis-Origin: autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN; confidence=0.9"
    )


def test_assisted_trailer_shape():
    origin = assisted_origin(conversation="sess-abc", turn=3)
    assert (
        format_trailer(origin)
        == "Sulis-Origin: assisted; conversation=sess-abc; turn=3"
    )


def test_autonomous_trailer_omits_absent_confidence():
    origin = autonomous_origin(run="01KT500K2JTE2EGW6TPPQ4D4VN", confidence=None)
    assert format_trailer(origin) == (
        "Sulis-Origin: autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN"
    )


# ─── parse_origin_env (the SULIS_ORIGIN env → origin, for the hook) ───────


def test_parse_origin_env_autonomous():
    origin = parse_origin_env(
        "autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN; confidence=0.7"
    )
    assert origin == {
        "kind": "autonomous",
        "run": "01KT500K2JTE2EGW6TPPQ4D4VN",
        "confidence": 0.7,
    }


def test_parse_origin_env_assisted():
    origin = parse_origin_env("assisted; conversation=sess-1; turn=5")
    assert origin == {
        "kind": "assisted",
        "conversation": "sess-1",
        "turn": 5,
    }


def test_parse_origin_env_rejects_garbage():
    assert parse_origin_env("") is None
    assert parse_origin_env("nonsense") is None
    assert parse_origin_env("autonomous; confidence=0.5") is None  # no run id


# ─── stamp_origin — real round-trip on a real commit ──────────────────────


def _commit_message(repo, ref="HEAD") -> str:
    return subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%B", ref],
        check=True, capture_output=True, text=True,
    ).stdout


def test_stamp_appends_autonomous_trailer_to_real_commit(local_git_repo):
    repo = local_git_repo
    (repo / "f.txt").write_text("work product\n")
    subprocess.run(["git", "-C", str(repo), "add", "f.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "feat: a thing"],
        check=True,
    )

    origin = autonomous_origin(run="01KT500K2JTE2EGW6TPPQ4D4VN", confidence=0.9)
    result = stamp_origin(repo, origin)

    assert result["outcome"] == "stamped"
    msg = _commit_message(repo)
    assert (
        "Sulis-Origin: autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN; confidence=0.9"
        in msg
    )
    # The structured log carries sha/origin/ref/outcome — never message text.
    assert result["sha"]
    assert result["ref"]
    assert "feat: a thing" not in json.dumps(result)


def test_stamp_assisted_trailer_to_real_commit(local_git_repo):
    repo = local_git_repo
    (repo / "g.txt").write_text("assisted work\n")
    subprocess.run(["git", "-C", str(repo), "add", "g.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "fix: helped"],
        check=True,
    )

    origin = assisted_origin(conversation="sess-xyz", turn=2)
    result = stamp_origin(repo, origin)

    assert result["outcome"] == "stamped"
    assert "Sulis-Origin: assisted; conversation=sess-xyz; turn=2" in _commit_message(
        repo
    )


def test_stamp_is_idempotent_does_not_duplicate_trailer(local_git_repo):
    repo = local_git_repo
    (repo / "h.txt").write_text("x\n")
    subprocess.run(["git", "-C", str(repo), "add", "h.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "chore: h"], check=True
    )
    origin = autonomous_origin(run="01KT500K2JTE2EGW6TPPQ4D4VN", confidence=0.5)
    stamp_origin(repo, origin)
    stamp_origin(repo, origin)
    msg = _commit_message(repo)
    assert msg.count("Sulis-Origin:") == 1


# ─── stamp failure is NON-FATAL (graceful degradation) ────────────────────


def test_stamp_failure_is_non_fatal_falls_back_to_sidecar(local_git_repo, monkeypatch):
    """If the trailer rewrite can't be written, stamp_origin must NOT raise —
    the commit stays intact and a sidecar is written as the fallback."""
    repo = local_git_repo
    (repo / "i.txt").write_text("y\n")
    subprocess.run(["git", "-C", str(repo), "add", "i.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "chore: i"], check=True
    )
    head_before = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()

    # Force the trailer-write path to fail.
    import _origin_stamp

    monkeypatch.setattr(
        _origin_stamp,
        "_rewrite_commit_message",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    origin = autonomous_origin(run="01KT500K2JTE2EGW6TPPQ4D4VN", confidence=0.5)
    result = stamp_origin(repo, origin)  # MUST NOT raise

    # Commit intact — HEAD did not move, message unchanged.
    head_after = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert head_after == head_before
    assert "Sulis-Origin:" not in _commit_message(repo)

    # Fell back to the sidecar.
    assert result["outcome"] in ("sidecar", "skipped")
    if result["outcome"] == "sidecar":
        sidecar = repo / ".sulis" / "origin" / f"{head_after}.json"
        assert sidecar.exists()
        data = json.loads(sidecar.read_text())
        assert data["kind"] == "autonomous"
        assert data["run"] == "01KT500K2JTE2EGW6TPPQ4D4VN"


def test_total_failure_is_swallowed_returns_skipped(local_git_repo, monkeypatch):
    """If BOTH the trailer and the sidecar fail, stamp_origin still must not
    raise — the commit is the source of truth and origin falls back to
    inferred (graceful degradation)."""
    repo = local_git_repo
    (repo / "j.txt").write_text("z\n")
    subprocess.run(["git", "-C", str(repo), "add", "j.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", "chore: j"], check=True
    )
    import _origin_stamp

    monkeypatch.setattr(
        _origin_stamp,
        "_rewrite_commit_message",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        _origin_stamp,
        "write_sidecar",
        lambda *a, **k: (_ for _ in ()).throw(OSError("disk full")),
    )

    origin = autonomous_origin(run="01KT500K2JTE2EGW6TPPQ4D4VN", confidence=0.5)
    result = stamp_origin(repo, origin)  # MUST NOT raise
    assert result["outcome"] == "skipped"


# ─── sidecar shape ────────────────────────────────────────────────────────


def test_write_sidecar_shape(tmp_path):
    origin = assisted_origin(conversation="c1", turn=4)
    path = write_sidecar(tmp_path, "deadbeef", origin)
    assert path == tmp_path / ".sulis" / "origin" / "deadbeef.json"
    data = json.loads(path.read_text())
    assert data == {"kind": "assisted", "conversation": "c1", "turn": 4}
