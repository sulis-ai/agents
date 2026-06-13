"""L2 file-tools — the four scoped tools end-to-end on a real filesystem (WP-005).

Proves the full L2 scenario set against `_file_tools` (read/write/move/remove),
each routing its path(s) through WP-004's `within_allowed_scope` BEFORE any I/O
and refusing out-of-scope paths fail-closed:

  * SC-L2.1 — in-scope read/write/move succeed; bytes actually land/move on disk.
  * SC-L2.2 — out-of-scope read refused (incl. ~/.ssh, a sibling change's
    worktree, and the canonical /tmp->/private/tmp footgun).
  * SC-L2.3 — out-of-scope write/move/remove refused fail-closed; the #130
    sibling-worktree replay leaves the sibling directory untouched.
  * SC-L2.4 — `..`-traversal and a symlink escaping scope are refused for every
    op.
  * SC-L2.5 — THE HONEST LIMIT. A raw subprocess (`bash -c 'cat <out-of-scope>'`)
    bypasses the file-tool and the read SUCCEEDS — this is asserted on purpose,
    with the test confirming `_file_tools`' module docstring names L3
    (`l3-os-egress-denial`, the OS sandbox) as the owner of the confinement L2
    structurally cannot provide (ADR-001 / ADR-005). No false sense of security.

These build a real worktree layout under `SULIS_STATE_DIR` (isolated to tmp by
the repo-wide conftest) and pass `repo_root` so the tools build the allowlist
exactly as production does.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_state import change_dir, change_worktree_dir  # noqa: E402
from _file_scope import resolve_allowed_roots  # noqa: E402
from _file_tools import (  # noqa: E402
    FileToolResult,
    move_file,
    read_file,
    remove_file,
    write_file,
)

_CID = "0123456789ABCDEFGHJKMNPQRS"
_OTHER = "1ABCDEFGHJKMNPQRSTVWXYZ012"


def _mk(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture()
def repo_root(tmp_path) -> Path:
    """A real (non-git) repo root; the git-common-dir falls back to repo/.git."""
    return _mk(tmp_path / "repo")


@pytest.fixture()
def worktree() -> Path:
    """The change's worktree, materialised under the tmp SULIS_STATE_DIR."""
    return _mk(change_worktree_dir(_CID))


@pytest.fixture()
def sibling_worktree() -> Path:
    """A DIFFERENT change's worktree — the #130 cross-worktree victim."""
    return _mk(change_worktree_dir(_OTHER) / "wp-006-worktree")


# ─── SC-L2.1 — in-scope ops succeed (bytes land on disk) ────────────────────


def test_sc_l2_1_in_scope_write_then_read_roundtrip(worktree, repo_root):
    target = worktree / "notes" / "todo.txt"
    w = write_file(target, "hello scope", _CID, repo_root=repo_root)
    assert isinstance(w, FileToolResult) and w.ok, w.reason
    assert target.read_text() == "hello scope"  # actually written

    r = read_file(target, _CID, repo_root=repo_root)
    assert r.ok, r.reason
    assert r.payload == "hello scope"


def test_sc_l2_1_in_scope_move_succeeds(worktree, repo_root):
    src = worktree / "a.txt"
    src.write_text("payload")
    dst = worktree / "sub" / "b.txt"
    m = move_file(src, dst, _CID, repo_root=repo_root)
    assert m.ok, m.reason
    assert not src.exists()  # moved, not copied
    assert dst.read_text() == "payload"


def test_sc_l2_1_in_scope_remove_succeeds(worktree, repo_root):
    target = worktree / "gone.txt"
    target.write_text("x")
    rm = remove_file(target, _CID, repo_root=repo_root)
    assert rm.ok, rm.reason
    assert not target.exists()


def test_sc_l2_1_change_state_dir_in_scope(repo_root):
    """A write under the change-state dir (another allowlisted root) succeeds."""
    target = _mk(change_dir(_CID)) / "scratch" / "x.txt"
    w = write_file(target, "state", _CID, repo_root=repo_root)
    assert w.ok, w.reason
    assert target.read_text() == "state"


def test_sc_l2_1_prebuilt_roots_reused_across_tools(worktree, repo_root):
    """The `roots=` path: a caller may build the allowlist ONCE and pass it to
    every tool (the efficiency path mirroring the resolver's own API), instead
    of rebuilding it per call from `repo_root`. In-scope ops still succeed and
    out-of-scope ops are still refused via the pre-built allowlist.
    """
    roots = resolve_allowed_roots(_CID, repo_root=repo_root)
    target = worktree / "via-prebuilt.txt"
    w = write_file(target, "reused", _CID, repo_root=repo_root, roots=roots)
    assert w.ok, w.reason
    r = read_file(target, _CID, repo_root=repo_root, roots=roots)
    assert r.ok and r.payload == "reused"
    # an out-of-scope path is still refused through the same pre-built allowlist
    refused = read_file(
        Path.home() / ".ssh" / "id_rsa", _CID, repo_root=repo_root, roots=roots
    )
    assert not refused.ok


# ─── SC-L2.2 — out-of-scope read refused (incl. canonical footgun) ──────────


def test_sc_l2_2_ssh_read_refused(worktree, repo_root):
    r = read_file(Path.home() / ".ssh" / "id_rsa", _CID, repo_root=repo_root)
    assert not r.ok
    assert r.payload is None
    assert "outside" in r.reason.lower() or "scope" in r.reason.lower()


def test_sc_l2_2_sibling_worktree_read_refused(sibling_worktree, worktree, repo_root):
    secret = sibling_worktree / "secret.txt"
    secret.write_text("other change's data")
    r = read_file(secret, _CID, repo_root=repo_root)
    assert not r.ok
    assert r.payload is None
    # The file is real and readable on disk — refusal is the tool's decision,
    # not a missing file.
    assert secret.exists()


def test_sc_l2_2_canonical_tmp_private_tmp_refused(worktree, repo_root):
    """A target handed in as /tmp/<x> (real path /private/tmp/<x> on macOS) is
    canonicalised before the scope check, so it is judged out-of-scope and
    refused — the footgun cannot smuggle an unresolved surface path past the
    decision.
    """
    import os
    import uuid

    name = f"sulis-wp005-{uuid.uuid4().hex}.txt"
    tmp_target = Path("/tmp") / name
    tmp_target.write_text("outside")
    try:
        r = read_file(tmp_target, _CID, repo_root=repo_root)
        assert not r.ok, "an out-of-scope /tmp path must be refused"
        assert r.payload is None
    finally:
        os.unlink(tmp_target)


# ─── SC-L2.3 — out-of-scope write/move/remove refused (#130 replay) ─────────


def test_sc_l2_3_sibling_worktree_remove_refused_fail_closed(
    sibling_worktree, repo_root
):
    """The exact #130 incident: a destructive op pointed at ANOTHER change's
    worktree. The tool refuses BEFORE touching the FS; the sibling is untouched.
    """
    victim = sibling_worktree / "important.txt"
    victim.write_text("do not delete me")
    rm = remove_file(victim, _CID, repo_root=repo_root)
    assert not rm.ok
    assert sibling_worktree.exists()  # the sibling worktree directory survives
    assert victim.exists()  # and its contents
    assert victim.read_text() == "do not delete me"


def test_sc_l2_3_sibling_worktree_write_refused_fail_closed(
    sibling_worktree, repo_root
):
    target = sibling_worktree / "injected.txt"
    w = write_file(target, "should never land", _CID, repo_root=repo_root)
    assert not w.ok
    assert not target.exists()  # nothing written into the sibling


def test_sc_l2_3_move_into_sibling_refused_no_partial(
    worktree, sibling_worktree, repo_root
):
    """move with an in-scope src but an out-of-scope dst is refused, and the
    src is NOT removed — no partial move (both endpoints checked first)."""
    src = worktree / "keep.txt"
    src.write_text("stays put")
    dst = sibling_worktree / "stolen.txt"
    m = move_file(src, dst, _CID, repo_root=repo_root)
    assert not m.ok
    assert src.exists() and src.read_text() == "stays put"  # src untouched
    assert not dst.exists()  # dst never created


def test_sc_l2_3_move_out_of_scope_src_refused(worktree, sibling_worktree, repo_root):
    """move with an out-of-scope src is refused even when dst is in-scope."""
    src = sibling_worktree / "theirs.txt"
    src.write_text("not yours")
    dst = worktree / "mine.txt"
    m = move_file(src, dst, _CID, repo_root=repo_root)
    assert not m.ok
    assert src.exists()  # src untouched
    assert not dst.exists()  # dst never created


# ─── SC-L2.4 — traversal / symlink escape refused ───────────────────────────


def test_sc_l2_4_traversal_escape_refused(worktree, sibling_worktree, repo_root):
    sneaky = worktree / ".." / ".." / _OTHER / "wp-006-worktree" / "x.txt"
    assert not read_file(sneaky, _CID, repo_root=repo_root).ok
    assert not write_file(sneaky, "x", _CID, repo_root=repo_root).ok
    assert not remove_file(sneaky, _CID, repo_root=repo_root).ok


def test_sc_l2_4_symlink_escape_refused(worktree, tmp_path, repo_root):
    outside = _mk(tmp_path / "outside-target")
    (outside / "loot.txt").write_text("outside")
    link = worktree / "escape"
    link.symlink_to(outside)  # inside-looking, resolves outside
    target = link / "loot.txt"
    assert not read_file(target, _CID, repo_root=repo_root).ok
    assert not write_file(target, "x", _CID, repo_root=repo_root).ok
    assert not remove_file(target, _CID, repo_root=repo_root).ok
    # the real outside file is untouched
    assert (outside / "loot.txt").read_text() == "outside"


# ─── SC-L2.5 — the honest limit (subprocess bypass SUCCEEDS) ────────────────


def test_sc_l2_5_subprocess_bypasses_tool_and_succeeds(tmp_path):
    """THE HONEST BOUNDARY. A raw subprocess never calls `within_allowed_scope`,
    so it is NOT confined by L2. We assert the bypass SUCCEEDS on purpose: this
    documents the limit and proves there is no false sense of security. The wall
    that would deny this is L3 (the OS sandbox), not L2.
    """
    out_of_scope = tmp_path / "totally-outside.txt"
    out_of_scope.write_text("L2 cannot stop a raw subprocess")

    proc = subprocess.run(
        ["bash", "-c", f"cat {out_of_scope}"],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0
    # The subprocess read the out-of-scope file — the tool was bypassed entirely.
    assert proc.stdout == "L2 cannot stop a raw subprocess"


def test_sc_l2_5_docstring_names_l3_as_owner_of_the_wall():
    """The module docstring must NAME L3 (l3-os-egress-denial / the OS sandbox)
    as the owner of the confinement L2 structurally cannot provide. This is the
    honest-limit contract: the limit is real, known, and documented in-code.
    """
    import _file_tools

    doc = (_file_tools.__doc__ or "").lower()
    assert "l3" in doc, "the module docstring must name L3"
    assert "l3-os-egress-denial" in doc or "os sandbox" in doc, (
        "the docstring must identify the OS sandbox / l3-os-egress-denial as "
        "the owner of the wall"
    )
    assert "subprocess" in doc or "bypass" in doc, (
        "the docstring must acknowledge a subprocess bypasses the tool"
    )


# ─── in-scope I/O failures degrade to a refusal (never raise) ───────────────
# These cover the fail-safe branches: the scope check PASSES but the OS I/O
# fails. The tool must return ok=False with a reason, never propagate OSError.


def test_in_scope_read_of_directory_degrades_to_refusal(worktree, repo_root):
    d = _mk(worktree / "a-directory")
    r = read_file(d, _CID, repo_root=repo_root)
    assert not r.ok and r.payload is None
    assert "read failed" in r.reason


def test_in_scope_write_under_a_file_degrades_to_refusal(worktree, repo_root):
    # A regular file stands where the write wants a parent directory: mkdir
    # of the parent raises in-scope -> refusal, not a crash.
    blocker = worktree / "blocker"
    blocker.write_text("i am a file, not a dir")
    target = blocker / "child.txt"
    w = write_file(target, "x", _CID, repo_root=repo_root)
    assert not w.ok
    assert "write failed" in w.reason


def test_in_scope_move_of_missing_src_degrades_to_refusal(worktree, repo_root):
    src = worktree / "does-not-exist.txt"
    dst = worktree / "dst.txt"
    m = move_file(src, dst, _CID, repo_root=repo_root)
    assert not m.ok
    assert "move failed" in m.reason
    assert not dst.exists()


def test_in_scope_remove_of_missing_file_degrades_to_refusal(worktree, repo_root):
    target = worktree / "never-existed.txt"
    rm = remove_file(target, _CID, repo_root=repo_root)
    assert not rm.ok
    assert "remove failed" in rm.reason
