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
import os
import subprocess
from pathlib import Path

import pytest

from _origin_stamp import (
    append_trailer_to_message,
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


def test_parse_origin_env_rejects_embedded_newline_no_forged_trailer():
    """A SULIS_ORIGIN value carrying a newline (a trailer-injection attempt)
    must NOT yield an origin — it returns None (the graceful unstamped path),
    so no second, forged trailer line can be smuggled in."""
    malicious = (
        "autonomous; run=abc\n"
        "Malicious-Trailer: pwned; confidence=0.9"
    )
    assert parse_origin_env(malicious) is None
    # A carriage return is equally rejected.
    assert parse_origin_env("autonomous; run=abc\rconfidence=0.9") is None
    # Any other control character (e.g. a vertical tab) is rejected too.
    assert parse_origin_env("autonomous; run=ab\x0bc") is None


def test_format_trailer_refuses_control_char_value():
    """Belt-and-braces: even if a control char reaches format_trailer, it must
    refuse rather than emit a multi-line / forged trailer."""
    with pytest.raises(ValueError):
        format_trailer({"kind": "autonomous", "run": "abc\nMalicious: x"})
    with pytest.raises(ValueError):
        format_trailer(
            {"kind": "assisted", "conversation": "sess\n1", "turn": 1}
        )


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


# ─── WP-007: Sulis-Origin is a FORMAL git trailer (blank-line separator) ──
#
# Conventional Commit subjects (`feat: x`, `fix: y`) contain a colon with no
# space before the key, so the old last-non-blank-line heuristic misdetected
# them as an existing trailer line and appended Sulis-Origin with no blank-line
# separator — so git's own trailer machinery (`git interpret-trailers --parse`,
# `git log --format='%(trailers:…)'`) did not recognise it. These tests pin
# the trailer as a FORMAL git trailer: separated from the body by a blank line,
# in the last paragraph, so git RECOGNISES it.

_HOOK = Path(__file__).resolve().parents[2] / "hooks" / "prepare-commit-msg"


def _install_hook(repo: Path) -> None:
    """Point git's core.hooksPath at the scripts hooks/ dir (the shipped wiring),
    so the real prepare-commit-msg hook runs in place on a real commit."""
    subprocess.run(
        ["git", "-C", str(repo), "config", "core.hooksPath", str(_HOOK.parent)],
        check=True,
    )


def _commit(repo: Path, fname: str, msg: str, env: dict | None = None) -> str:
    (repo / fname).write_text("real work product\n")
    subprocess.run(["git", "-C", str(repo), "add", fname], check=True)
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-q", "-m", msg],
        check=True, env=full_env,
    )
    return subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%B"],
        check=True, capture_output=True, text=True,
    ).stdout


def _git_recognised_trailer(repo: Path) -> str:
    """What git's OWN trailer parser extracts for Sulis-Origin on HEAD. Empty
    string means git does not recognise a formal trailer (the bug)."""
    return subprocess.run(
        ["git", "-C", str(repo), "log", "-1",
         "--format=%(trailers:key=Sulis-Origin,valueonly=true)"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()


def test_conventional_subject_yields_git_recognised_formal_trailer(local_git_repo):
    """RED→GREEN: a real commit with a Conventional Commit subject through the
    prepare-commit-msg hook must produce a trailer that git ITSELF recognises
    (not just the cockpit's regex reader). On the pre-fix heuristic this fails:
    `feat:` is misread as a trailer line, the separator is a single `\\n`, and
    git's `%(trailers:…)` returns empty."""
    repo = local_git_repo
    _install_hook(repo)
    _commit(
        repo, "real.txt", "feat: real autonomous work",
        env={"SULIS_ORIGIN":
             "autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN; confidence=0.9"},
    )
    # git's own parser must extract the value — proves a FORMAL trailer.
    assert _git_recognised_trailer(repo) == (
        "autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN; confidence=0.9"
    )
    # Cross-check with git interpret-trailers --parse.
    msg = subprocess.run(
        ["git", "-C", str(repo), "log", "-1", "--format=%B"],
        check=True, capture_output=True, text=True,
    ).stdout
    parsed = subprocess.run(
        ["git", "-C", str(repo), "interpret-trailers", "--parse"],
        input=msg, check=True, capture_output=True, text=True,
    ).stdout
    assert "Sulis-Origin: autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN" in parsed


# ─── append_trailer_to_message: the three Contract cases + idempotency ─────

_ORIGIN = autonomous_origin(run="01KT500K2JTE2EGW6TPPQ4D4VN", confidence=0.9)
_TRAILER = "Sulis-Origin: autonomous; run=01KT500K2JTE2EGW6TPPQ4D4VN; confidence=0.9"


def _last_paragraph(message: str) -> list[str]:
    """The lines after the final blank line — git's notion of the trailer block."""
    blocks = message.rstrip("\n").split("\n\n")
    return blocks[-1].splitlines()


def test_append_bare_conventional_subject_opens_new_block_with_blank_line():
    """`feat: x` is a one-paragraph subject, NOT a trailer block: the trailer
    must open a new block after a blank line."""
    out = append_trailer_to_message("feat: x", _ORIGIN)
    assert out == f"feat: x\n\n{_TRAILER}\n"
    # The blank-line separator makes it git-formal: the last paragraph is the
    # trailer alone.
    assert _last_paragraph(out) == [_TRAILER]


def test_append_subject_plus_body_opens_new_trailer_block():
    """Subject + a body paragraph: the trailer opens a new block after a blank
    line (it is not part of the body paragraph)."""
    message = "feat: x\n\nThis body explains the change in prose: with a colon."
    out = append_trailer_to_message(message, _ORIGIN)
    assert out == f"{message}\n\n{_TRAILER}\n"
    assert _last_paragraph(out) == [_TRAILER]


def test_append_joins_existing_coauthored_by_trailer_block_no_extra_blank():
    """A message already ending in a real trailer block (Co-Authored-By,
    preceded by a blank line): the new trailer JOINS that same block — no extra
    blank line between trailers."""
    message = (
        "feat: x\n\n"
        "Body paragraph.\n\n"
        "Co-Authored-By: Someone <s@example.com>"
    )
    out = append_trailer_to_message(message, _ORIGIN)
    assert out == (
        "feat: x\n\n"
        "Body paragraph.\n\n"
        "Co-Authored-By: Someone <s@example.com>\n"
        f"{_TRAILER}\n"
    )
    # Both trailers share the last paragraph (one block, no blank between them).
    assert _last_paragraph(out) == [
        "Co-Authored-By: Someone <s@example.com>",
        _TRAILER,
    ]


def test_append_is_idempotent_no_duplicate_on_second_call():
    """A second call must never add a duplicate Sulis-Origin trailer."""
    once = append_trailer_to_message("feat: x", _ORIGIN)
    twice = append_trailer_to_message(once, _ORIGIN)
    assert twice == once
    assert twice.count("Sulis-Origin:") == 1
