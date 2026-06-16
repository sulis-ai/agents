"""DaemonStartError surfaces the cause (#131).

A wedged daemon holds the singleton flock and never serves the socket, so a new
spawn times out. The bug the founder hit wasn't the timeout — it was that the
error gave NO cause (the real reason, "singleton lock held but no live socket",
sat in a log the operator had to know to find). These pin that the daemon log
tail + the spawned process's exit status are now folded INTO the error.
"""

from __future__ import annotations

import time

import pytest

from _session_manager import daemon_client as dc


# ─── _daemon_log_tail ───────────────────────────────────────────────────────


def test_log_tail_reads_last_lines(tmp_path, monkeypatch):
    log = tmp_path / "session-manager-daemon.log"
    log.write_text("\n".join(f"line{i}" for i in range(30)), encoding="utf-8")
    monkeypatch.setenv("SULIS_SESSION_MANAGER_LOG", str(log))
    assert dc._daemon_log_tail("/x.sock", lines=4).splitlines() == \
        ["line26", "line27", "line28", "line29"]


def test_log_tail_empty_when_absent(tmp_path, monkeypatch):
    monkeypatch.setenv("SULIS_SESSION_MANAGER_LOG", str(tmp_path / "nope.log"))
    assert dc._daemon_log_tail("/x.sock") == ""


# ─── the error folds in the cause ───────────────────────────────────────────


def test_spawn_failure_surfaces_log_cause_and_exit_code(tmp_path, monkeypatch):
    # A "daemon" that writes a cause to stderr and exits without serving a socket
    # — exactly the wedged-singleton shape. The error must NAME the cause + the
    # exit code, not just say "did not become live within Ns".
    monkeypatch.setenv("SULIS_SESSION_MANAGER_LOG", str(tmp_path / "session-manager-daemon.log"))
    sock = str(tmp_path / "x.sock")
    fake = ["python3", "-c",
            "import sys; sys.stderr.write('singleton lock held but no live socket "
            "— wedged\\n'); sys.exit(1)"]

    with pytest.raises(dc.DaemonStartError) as ei:
        dc._spawn_and_wait(
            sock, python="python3", spawn_command=fake,
            probe_timeout=0.2, ready_timeout=1.0, deadline=time.monotonic() + 1.0,
        )

    msg = str(ei.value)
    assert "singleton lock held but no live socket" in msg   # the real cause
    assert "exited with code 1" in msg                       # the process status
    assert "daemon log tail" in msg
