"""WP-010 — the e2e live-terminal backend (the REAL session manager + socket).

Boots a REAL :class:`SessionManager` serving a REAL pty-backed fake child over a
REAL AF_UNIX :class:`SocketServer` — the exact backend the cockpit talks to in
production (MEA-09: no mocks in the integration round-trip). The Node WS proxy
(``terminal-proxy.ts``) connects to this socket and bridges the browser's
WebSocket to it; Playwright drives the cockpit UI against the proxy.

It pre-seeds the change's pty session with a known scrollback banner BEFORE the
browser attaches, so the e2e can prove the "render existing scrollback, not a
blank pane" guarantee (acceptance #1, §2.12.2) and the "reopen catches up"
guarantee (acceptance #3, §2.12.3).

Usage (invoked by terminal-proxy.ts):
    python3 terminal-backend.py --socket /tmp/x.sock --change-id CH-... --cwd DIR

It prints ``READY <socket_path>`` on stdout once the socket is serving, then
runs until killed (SIGTERM/SIGINT) — the proxy owns its lifetime.

The binding guard is deliberately permissive here (single-tenant e2e): the
local AF_UNIX filesystem permission is the gate the real deployment relies on
(§2.13.4 first gate); cross-change denial is unit/integration-proven in
test_socket_server.py::test_cross_change_attach_denied (not re-proven in the UI
e2e, which is single-change).
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import threading
import time
from pathlib import Path

# The session manager package lives under plugins/sulis/scripts; its test lib
# carries the real pty child + adapter (the same ones the backend suites use).
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS = _REPO_ROOT / "plugins" / "sulis" / "scripts"
sys.path.insert(0, str(_SCRIPTS))
sys.path.insert(0, str(_SCRIPTS / "tests" / "lib"))

from _session_manager.adapter import SessionSpec  # noqa: E402
from _session_manager.manager import SessionManager  # noqa: E402
from _session_manager.socket_server import SocketServer  # noqa: E402

import fake_claude_child  # noqa: E402
from session_child_adapters import PtyChildAdapter  # noqa: E402

#: The banner seeded into the pty scrollback before any browser attaches — the
#: deterministic token the e2e asserts the snapshot phase renders.
SCROLLBACK_BANNER = b"WP010_SCROLLBACK_BANNER\r\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--socket", required=True)
    parser.add_argument("--change-id", required=True)
    parser.add_argument("--cwd", required=True)
    args = parser.parse_args()

    cwd = args.cwd
    os.makedirs(cwd, exist_ok=True)

    # A real pty-backed child (echoes stdin, emits PTY_PONG on __PTY_PING__).
    child = fake_claude_child.write_child(Path(cwd))
    manager = SessionManager(
        {"pty": PtyChildAdapter(child)}, start_maintenance=False
    )

    # Open the change's pty session up front and seed its scrollback with the
    # banner (write to the master so the child echoes it into the ring), so a
    # browser attach renders existing scrollback (acceptance #1) — not blank.
    session = manager.open(
        args.change_id,
        SessionSpec(provider="pty", cwd=cwd, io_mode="pty"),
    )
    os.write(session.pty_master_fd, SCROLLBACK_BANNER)
    # Wait until the banner has reached the scrollback ring (the pump drained
    # the master) so attach is guaranteed to find it in the snapshot.
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        if b"WP010_SCROLLBACK_BANNER" in session.scrollback.snapshot():
            break
        time.sleep(0.01)

    server = SocketServer(manager, args.socket)
    server.start()

    # Signal readiness to the proxy (it waits for this line before accepting
    # browser connections).
    sys.stdout.write(f"READY {args.socket}\n")
    sys.stdout.flush()

    stop = threading.Event()

    def _shutdown(*_a: object) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        stop.wait()
    finally:
        server.stop()
        manager.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
