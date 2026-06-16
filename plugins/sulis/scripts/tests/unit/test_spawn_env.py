"""Spawn-env wiring — Rule-of-Two credential exclusion at the spawn seam (WP-003).

TDD §Armor L1 (Rule-of-Two). SPEC §L1(d): secrets are kept **out of the fetch
path's environment** — the **primary** credential-exclusion control. WP-002's
outbound scrub is defence-in-depth on top; this exclusion is the wall it braces.

Two surfaces are proven here:

  1. **The pure policy** — ``child_spawn_env(parent_env, *, proxy_endpoint)``
     returns a child environment that (a) **excludes** every credential-bearing
     variable (the ``*_KEY`` / ``*_SECRET`` / ``*_TOKEN`` / ``*_PASSWORD`` name
     convention shared with ``_secret_patterns``), (b) **sets** the proxy
     endpoint variable the agent-facing tool reads, and (c) passes non-credential
     variables through unchanged so the session still works.

  2. **The seam is wired** — ``SessionManager._spawn_process`` passes an explicit
     ``env=`` to ``subprocess.Popen`` (today it inherits the full parent env).
     Proven with a ``Popen`` spy: the env actually handed to ``Popen`` excludes
     a marked credential var and includes the proxy endpoint var.
"""

from __future__ import annotations

import os
import subprocess

import pytest

from _session_manager.adapter import Capabilities, SessionSpec
from _session_manager.manager import SessionManager
from _session_manager.spawn_env import (
    PROXY_ENDPOINT_ENV,
    child_spawn_env,
    is_credential_var,
)


# ─── 1. the pure policy ───────────────────────────────────────────────────────


def test_child_env_excludes_credential_named_vars() -> None:
    parent = {
        "PATH": "/usr/bin",
        "ANTHROPIC_API_KEY": "pat_should_not_propagate_aaaaaaaaaaaa",
        "GITHUB_TOKEN": "pat_token_value_bbbbbbbbbbbbbbbbbbbb",
        "DB_PASSWORD": "hunter2",
        "STRIPE_SECRET": "pat_secret_cccccccccccccccccccc",
    }
    child = child_spawn_env(parent, proxy_endpoint="http://127.0.0.1:8080")

    assert "ANTHROPIC_API_KEY" not in child
    assert "GITHUB_TOKEN" not in child
    assert "DB_PASSWORD" not in child
    assert "STRIPE_SECRET" not in child


def test_child_env_excludes_well_known_non_suffix_credentials() -> None:
    """Credential variables whose names do not end in a catalogued suffix
    (``AWS_ACCESS_KEY_ID`` ends ``ID``; ``SSH_AUTH_SOCK`` is an agent-socket
    path) must still be excluded via the explicit name allowlist — they are the
    primary control's blind spot if only the suffix rule were used."""
    parent = {
        "PATH": "/usr/bin",
        "AWS_ACCESS_KEY_ID": "pat_akid_value_gggggggggggggggg",
        "GOOGLE_APPLICATION_CREDENTIALS": "/home/agent/gcp.json",
        "SSH_AUTH_SOCK": "/tmp/ssh-agent.sock",
    }
    child = child_spawn_env(parent, proxy_endpoint="http://127.0.0.1:8080")
    assert "AWS_ACCESS_KEY_ID" not in child
    assert "GOOGLE_APPLICATION_CREDENTIALS" not in child
    assert "SSH_AUTH_SOCK" not in child
    assert child["PATH"] == "/usr/bin"


def test_child_env_passes_non_credential_vars_through() -> None:
    parent = {"PATH": "/usr/bin", "HOME": "/home/agent", "LANG": "en_US.UTF-8"}
    child = child_spawn_env(parent, proxy_endpoint="http://127.0.0.1:8080")
    assert child["PATH"] == "/usr/bin"
    assert child["HOME"] == "/home/agent"
    assert child["LANG"] == "en_US.UTF-8"


def test_child_env_sets_the_proxy_endpoint_var() -> None:
    child = child_spawn_env(
        {"PATH": "/usr/bin"}, proxy_endpoint="http://127.0.0.1:9999"
    )
    assert child[PROXY_ENDPOINT_ENV] == "http://127.0.0.1:9999"


def test_child_env_does_not_mutate_the_parent() -> None:
    parent = {"PATH": "/usr/bin", "API_KEY": "pat_secret_dddddddddddddddddddd"}
    snapshot = dict(parent)
    child_spawn_env(parent, proxy_endpoint="http://127.0.0.1:8080")
    assert parent == snapshot  # the parent env is untouched (pure)
    assert "child" not in parent  # sanity


def test_child_env_with_no_endpoint_still_excludes_credentials() -> None:
    """The endpoint is optional (a session may run before the proxy is wired);
    the credential exclusion is unconditional."""
    parent = {"PATH": "/usr/bin", "OPENAI_API_KEY": "pat_x_eeeeeeeeeeeeeeeeeeee"}
    child = child_spawn_env(parent, proxy_endpoint=None)
    assert "OPENAI_API_KEY" not in child
    assert PROXY_ENDPOINT_ENV not in child


@pytest.mark.parametrize(
    "name,expected",
    [
        ("ANTHROPIC_API_KEY", True),
        ("GITHUB_TOKEN", True),
        ("DB_PASSWORD", True),
        ("MY_SECRET", True),
        ("PG_PASSWD", True),
        # Well-known credential names that do NOT end in a catalogued suffix —
        # caught by the explicit exact-name allowlist, not the suffix rule.
        ("AWS_ACCESS_KEY_ID", True),
        ("GOOGLE_APPLICATION_CREDENTIALS", True),
        ("SSH_AUTH_SOCK", True),
        ("PATH", False),
        ("HOME", False),
        ("SULIS_CHANGE_ID", False),
        ("LANG", False),
    ],
)
def test_is_credential_var_classifies_by_name_convention(
    name: str, expected: bool
) -> None:
    assert is_credential_var(name) is expected


# ─── 2. the seam is wired: _spawn_process passes env= to Popen ────────────────


class _StubAdapter:
    """Minimal ``ProviderAdapter`` whose ``spawn_argv`` returns a trivial argv;
    the spy intercepts ``Popen`` before any real process starts."""

    def __init__(self) -> None:
        self.capabilities = Capabilities(
            supports_resume=False,
            supports_tools=False,
            supports_partial_streaming=False,
        )

    def spawn_argv(self, spec: SessionSpec) -> list[str]:
        return ["/bin/true"]

    def encode(self, command: str) -> bytes:  # pragma: no cover - not exercised
        return command.encode()

    def decode(self, line: bytes):  # pragma: no cover - not exercised
        return None

    def turn_complete(self, event) -> bool:  # pragma: no cover - not exercised
        return False


class _PopenSpy:
    """Records the kwargs ``_spawn_process`` hands to ``subprocess.Popen``."""

    captured: dict | None = None

    def __init__(self, argv, **kwargs):
        type(self).captured = kwargs
        self.pid = 4321
        self.returncode = None

    def poll(self):
        return None

    def wait(self, timeout=None):
        return 0

    def kill(self):
        return None

    def terminate(self):
        return None


def test_spawn_process_passes_explicit_env_excluding_creds_including_proxy(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """The seam: ``_spawn_process`` must hand ``Popen`` an explicit ``env=``
    that EXCLUDES a marked credential var and INCLUDES the proxy endpoint var.

    Today Popen inherits the full parent env (no ``env=``); this WP makes it
    explicit (Rule-of-Two, SPEC §L1(d))."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "pat_marked_credential_ffffffffffff")
    monkeypatch.setenv("PATH", "/usr/bin")
    _PopenSpy.captured = None
    monkeypatch.setattr(subprocess, "Popen", _PopenSpy)

    mgr = SessionManager({"stub": _StubAdapter()}, start_maintenance=False)
    spec = SessionSpec(provider="stub", cwd=str(tmp_path))
    process, master_fd = mgr._spawn_process(_StubAdapter(), spec)

    assert _PopenSpy.captured is not None
    env = _PopenSpy.captured.get("env")
    assert env is not None, "_spawn_process must pass an explicit env= to Popen"
    assert "ANTHROPIC_API_KEY" not in env, "credential var must be excluded from child"
    assert PROXY_ENDPOINT_ENV in env, "proxy endpoint var must be set in child env"
    # Non-credential vars still flow so the session works.
    assert env.get("PATH") == "/usr/bin"

    mgr.shutdown()


# ─── 3. per-spawn SULIS_CHANGE_ID stamping (WP-001, this change's ADR-001) ─────
#
# The daemon leaked its own launch-time ``SULIS_CHANGE_ID`` into every spawned
# session because the pure policy passed every non-credential var through
# unchanged. The fix stamps ``SULIS_CHANGE_ID`` per spawn from
# ``SessionSpec.brief_change_id`` (override inherited) and removes it when the
# spawn has no target change (no stale inheritance), plus a daemon-startup clear
# as defence in depth.

_STALE_DAEMON_CHANGE_ID = "01DAEMON_STALE_0000000000000000"
_TARGET_CHANGE_ID = "01TARGET_CHANGE_1111111111111111"


def test_child_env_stamps_supplied_change_id_overriding_inherited() -> None:
    """A supplied ``change_id`` overrides any inherited ``SULIS_CHANGE_ID`` in
    the parent env — the child carries its own target change, not the daemon's
    launch-time value."""
    parent = {"PATH": "/usr/bin", "SULIS_CHANGE_ID": _STALE_DAEMON_CHANGE_ID}
    child = child_spawn_env(parent, proxy_endpoint=None, change_id=_TARGET_CHANGE_ID)
    assert child["SULIS_CHANGE_ID"] == _TARGET_CHANGE_ID


def test_child_env_removes_change_id_when_no_target() -> None:
    """``change_id=None`` removes any inherited ``SULIS_CHANGE_ID`` — a session
    with no bound change must not silently adopt the daemon's."""
    parent = {"PATH": "/usr/bin", "SULIS_CHANGE_ID": _STALE_DAEMON_CHANGE_ID}
    child = child_spawn_env(parent, proxy_endpoint=None, change_id=None)
    assert "SULIS_CHANGE_ID" not in child


def test_child_env_change_id_default_is_none_removes() -> None:
    """Back-compat lock: with NO ``change_id`` kwarg the defaulted-None
    behaviour removes (rather than leaks) any inherited ``SULIS_CHANGE_ID`` —
    callers must opt in to a target."""
    parent = {"PATH": "/usr/bin", "SULIS_CHANGE_ID": _STALE_DAEMON_CHANGE_ID}
    child = child_spawn_env(parent, proxy_endpoint=None)
    assert "SULIS_CHANGE_ID" not in child


def test_spawn_process_stamps_target_change_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """The seam: ``_spawn_process`` stamps the spec's ``brief_change_id`` onto
    the child env handed to ``Popen``, overriding a stale daemon value in
    ``os.environ``."""
    monkeypatch.setenv("SULIS_CHANGE_ID", _STALE_DAEMON_CHANGE_ID)
    _PopenSpy.captured = None
    monkeypatch.setattr(subprocess, "Popen", _PopenSpy)

    mgr = SessionManager({"stub": _StubAdapter()}, start_maintenance=False)
    spec = SessionSpec(
        provider="stub", cwd=str(tmp_path), brief_change_id=_TARGET_CHANGE_ID
    )
    mgr._spawn_process(_StubAdapter(), spec)

    assert _PopenSpy.captured is not None
    env = _PopenSpy.captured.get("env")
    assert env is not None
    assert env["SULIS_CHANGE_ID"] == _TARGET_CHANGE_ID

    mgr.shutdown()


def test_spawn_process_no_change_id_when_spec_has_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """A spec with ``brief_change_id=None`` yields no ``SULIS_CHANGE_ID`` in the
    child env, even when ``os.environ`` carries a stale daemon value."""
    monkeypatch.setenv("SULIS_CHANGE_ID", _STALE_DAEMON_CHANGE_ID)
    _PopenSpy.captured = None
    monkeypatch.setattr(subprocess, "Popen", _PopenSpy)

    mgr = SessionManager({"stub": _StubAdapter()}, start_maintenance=False)
    spec = SessionSpec(provider="stub", cwd=str(tmp_path), brief_change_id=None)
    mgr._spawn_process(_StubAdapter(), spec)

    assert _PopenSpy.captured is not None
    env = _PopenSpy.captured.get("env")
    assert env is not None
    assert "SULIS_CHANGE_ID" not in env

    mgr.shutdown()


# ─── 4. daemon-startup defence in depth (Armor) ───────────────────────────────


def test_daemon_main_clears_own_change_id_at_startup(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    """``session_manager_daemon.main()`` clears its own ``SULIS_CHANGE_ID`` from
    ``os.environ`` at startup, before any server is built — the belt to the
    per-spawn brace (ADR-001). The singleton lock + boot are stubbed so no real
    server starts."""
    import session_manager_daemon

    monkeypatch.setenv("SULIS_CHANGE_ID", _STALE_DAEMON_CHANGE_ID)
    # Stub the lock acquisition (return a sentinel fd) and the boot so main()
    # runs the startup clear without touching a real socket/lock/server.
    monkeypatch.setattr(
        session_manager_daemon, "_acquire_singleton_lock", lambda _path: 99
    )
    monkeypatch.setattr(
        session_manager_daemon, "_boot_and_serve", lambda _args, _lock_fd: 0
    )

    rc = session_manager_daemon.main(
        [
            "--socket",
            str(tmp_path / "sock"),
            "--lock",
            str(tmp_path / "lock"),
            "--pidfile",
            str(tmp_path / "pid"),
        ]
    )

    assert rc == 0
    assert "SULIS_CHANGE_ID" not in os.environ
