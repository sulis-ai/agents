"""TEST-ONLY portable no-raw-egress shim (ADR-005).

A process-local block on raw outbound sockets, used by the L1 egress scenarios
(``tests/integration/test_safe_fetch_scenarios.py``) to **simulate** the OS-level
egress denial that production owns at **L3** (the deferred
``l3-os-egress-denial`` sandbox). Pure Python, identical on macOS/Linux/Windows
(no ``sandbox-exec`` / ``bubblewrap`` — those are L3's own scenarios and are
per-OS).

**This is NOT a production enforcement mechanism.** A monkeypatch on
``socket.create_connection`` / ``socket.socket.connect`` is bypassable by any
subprocess and by ``ctypes`` — that is precisely why ADR-001 places the real
egress wall at L3 and not in userland. The shim exists only so the L1
proxy-correctness half (the sanctioned door works; a bypass-of-the-door fails
when egress is denied) can be asserted now, under a simulated denial. It lives
under ``tests/`` and is asserted **un-importable** from any production module
(``test_no_egress_shim_is_not_importable_from_production_modules``) so it can
never be mistaken for a control.

Under :func:`deny_raw_egress`, an outbound connection to any destination other
than loopback (``127.0.0.0/8`` / ``::1`` / ``localhost``) raises ``OSError``
(``ConnectionRefusedError``), and every attempted destination is recorded on the
yielded :class:`_EgressRecord` so a test can assert *zero* connections to an
attacker host occurred. Loopback is allowed by default because the proxy's
sanctioned endpoint is co-located on loopback (the one egress L3 will also
allow-list).
"""

from __future__ import annotations

import socket
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


@dataclass
class _EgressRecord:
    """Audit of every outbound connection attempted while the shim is active.

    ``attempted_destinations`` is a list of ``(host, port)`` tuples in attempt
    order — refused attempts are recorded too, so a test can assert what the
    (hijacked) agent *tried* to reach, not only what succeeded.
    """

    attempted_destinations: list[tuple[str, int]] = field(default_factory=list)


def _is_loopback(host: str) -> bool:
    """Whether ``host`` is a loopback destination (the proxy's sanctioned home).

    Accepts the literal ``localhost`` plus any address in the IPv4/IPv6 loopback
    ranges. A non-numeric, non-``localhost`` host is treated as remote (the shim
    refuses it) — the scenarios use explicit loopback literals for the proxy leg,
    so no DNS resolution is performed here (and must not be: resolving could
    itself leave the host)."""
    if host in ("localhost", "127.0.0.1", "::1"):
        return True
    try:
        return __import__("ipaddress").ip_address(host).is_loopback
    except ValueError:
        return False


@contextmanager
def deny_raw_egress(allow_loopback: bool = True) -> Iterator[_EgressRecord]:
    """Refuse every raw outbound socket except loopback, recording all attempts.

    Monkeypatches ``socket.create_connection`` and ``socket.socket.connect`` for
    the duration of the ``with`` block. Yields an :class:`_EgressRecord` whose
    ``attempted_destinations`` lists every ``(host, port)`` the code under test
    tried to reach. A destination that is not loopback (or when
    ``allow_loopback`` is ``False``, any destination) raises
    ``ConnectionRefusedError`` *before* a real connection is made — simulating
    L3's OS denial inside this test process.

    The original functions are always restored on exit (success or exception),
    so the shim never leaks beyond its ``with`` block.
    """
    record = _EgressRecord()
    real_create_connection = socket.create_connection
    real_connect = socket.socket.connect

    def _check(host: str, port: int) -> None:
        record.attempted_destinations.append((host, port))
        if allow_loopback and _is_loopback(host):
            return
        raise ConnectionRefusedError(
            f"raw egress denied to {host!r}:{port} "
            "(simulated by the test no-egress shim; production owner is L3 "
            "`l3-os-egress-denial`)"
        )

    def _patched_create_connection(address, *args, **kwargs):
        host, port = address[0], address[1]
        _check(str(host), int(port))
        return real_create_connection(address, *args, **kwargs)

    def _patched_connect(self, address):  # type: ignore[no-untyped-def]
        # AF_INET / AF_INET6 addresses are ``(host, port[, ...])``; non-inet
        # sockets (AF_UNIX) carry a path string — those never leave the host, so
        # let them through unrecorded.
        if isinstance(address, tuple) and len(address) >= 2:
            _check(str(address[0]), int(address[1]))
        return real_connect(self, address)

    socket.create_connection = _patched_create_connection  # type: ignore[assignment]
    socket.socket.connect = _patched_connect  # type: ignore[assignment]
    try:
        yield record
    finally:
        socket.create_connection = real_create_connection  # type: ignore[assignment]
        socket.socket.connect = real_connect  # type: ignore[assignment]
