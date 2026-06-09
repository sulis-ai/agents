"""Unit tests for the #102 daemon version-skew guard in daemon_client.

The session daemon is a singleton that survives plugin updates, so a viewer
from a NEW plugin version could connect to a daemon running OLD code (the
crash/hang). The daemon now stamps its version in the `status` reply; these
tests pin: the version-match decision, the SIGTERM-stop of a skewed daemon, and
that `ensure_daemon` restarts on skew but reuses on match.
"""

from __future__ import annotations

import signal

from _session_manager import daemon_client as dc


def _reply(version, pid=4321, ok=True):
    return {"ok": ok, "meta": {"daemon_version": version, "daemon_pid": pid}, "result": []}


# ─── _version_ok ───────────────────────────────────────────────────────────


def test_version_match_is_ok(monkeypatch):
    monkeypatch.setattr(dc, "plugin_version", lambda *a, **k: "0.130.0")
    assert dc._version_ok(_reply("0.130.0")) is True


def test_version_mismatch_is_not_ok(monkeypatch):
    monkeypatch.setattr(dc, "plugin_version", lambda *a, **k: "0.130.0")
    assert dc._version_ok(_reply("0.126.1")) is False


def test_missing_version_stamp_is_not_ok(monkeypatch):
    # An old daemon (no version in meta) IS running old code → restart.
    monkeypatch.setattr(dc, "plugin_version", lambda *a, **k: "0.130.0")
    assert dc._version_ok({"ok": True, "result": []}) is False


def test_unknown_own_version_reuses(monkeypatch):
    # Dev / non-cache layout: can't compare → reuse, never spuriously restart.
    monkeypatch.setattr(dc, "plugin_version", lambda *a, **k: None)
    assert dc._version_ok(_reply("anything")) is True


# ─── _stop_stale_daemon ────────────────────────────────────────────────────


def test_stop_stale_daemon_sigterms_the_pid(monkeypatch):
    killed = {}
    monkeypatch.setattr(dc.os, "kill", lambda pid, sig: killed.update(pid=pid, sig=sig))
    # Daemon reports dead immediately so the wait loop exits at once.
    monkeypatch.setattr(dc, "daemon_is_live", lambda *a, **k: False)
    monkeypatch.setattr(dc.os.path, "exists", lambda p: False)
    dc._stop_stale_daemon("/tmp/x.sock", _reply("old", pid=4321), 0.1)
    assert killed == {"pid": 4321, "sig": signal.SIGTERM}


def test_stop_stale_daemon_no_pid_is_safe(monkeypatch):
    monkeypatch.setattr(dc, "daemon_is_live", lambda *a, **k: False)
    monkeypatch.setattr(dc.os.path, "exists", lambda p: False)
    # No meta/pid → must not raise.
    dc._stop_stale_daemon("/tmp/x.sock", {"ok": True}, 0.1)


# ─── ensure_daemon warm-path guard ─────────────────────────────────────────


def test_ensure_daemon_reuses_on_version_match(monkeypatch):
    monkeypatch.setattr(dc, "plugin_version", lambda *a, **k: "0.130.0")
    monkeypatch.setattr(dc, "_status_reply", lambda *a, **k: _reply("0.130.0"))
    stopped = {"n": 0}
    monkeypatch.setattr(dc, "_stop_stale_daemon", lambda *a, **k: stopped.__setitem__("n", stopped["n"] + 1))
    monkeypatch.setattr(dc, "_spawn_and_wait", lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not spawn")))
    out = dc.ensure_daemon("/tmp/match.sock", spawn_command=["never"])
    assert out == "/tmp/match.sock"
    assert stopped["n"] == 0  # matched → no restart


def test_ensure_daemon_restarts_on_version_skew(monkeypatch):
    monkeypatch.setattr(dc, "plugin_version", lambda *a, **k: "0.130.0")
    # Warm probe → skewed daemon; after stop, in-lock probe → gone (None).
    replies = iter([_reply("0.126.1"), None])
    monkeypatch.setattr(dc, "_status_reply", lambda *a, **k: next(replies, None))
    stopped = {"n": 0}
    monkeypatch.setattr(dc, "_stop_stale_daemon", lambda *a, **k: stopped.__setitem__("n", stopped["n"] + 1))
    spawned = {"n": 0}

    def _fake_spawn(socket_path, **k):
        spawned["n"] += 1
        return socket_path

    monkeypatch.setattr(dc, "_spawn_and_wait", _fake_spawn)
    out = dc.ensure_daemon("/tmp/skew.sock", spawn_command=["x"])
    assert out == "/tmp/skew.sock"
    assert stopped["n"] >= 1, "skewed daemon should be stopped"
    assert spawned["n"] == 1, "a fresh daemon should be cold-started"
