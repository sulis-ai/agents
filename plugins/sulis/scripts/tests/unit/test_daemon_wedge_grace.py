"""WP-003 (harden-daemon-wedge-self-heal) — the wedge-grace window resolver.

Contract: ``WP-003-grace-window-wedge-detection.md`` Definition of Done > Red
+ spec §Constraints (a bad override degrades to the safe default, never crashes
— mirror ``resolve_idle_exit_secs``) + ADR-001. HD-003.

The grace window distinguishes a **mid-boot** holder (slow-but-legitimate boot,
socket comes live within the window → reused) from a **wedged** holder (lock
held, no live socket past the window → reclaimed). The window must be long
enough that a genuinely slow boot is never mistaken for a wedge, and a bad
tuning value (empty / non-numeric / non-positive) must degrade to the
conservative default rather than crash the daemon — exactly the contract
``resolve_idle_exit_secs`` already meets, cloned here for the new seam.

Verification posture (MEA-09, deterministic): pure config resolution driven by
``SULIS_DAEMON_WEDGE_GRACE_SECS`` via ``monkeypatch.setenv`` — no real process,
no sleeping. These mirror the existing ``resolve_idle_exit_secs`` tests
one-for-one so the two env seams stay behaviourally identical.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import given
from hypothesis import strategies as st

import session_manager_daemon


def test_resolve_wedge_grace_secs_default_when_unset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unset → the conservative ``DEFAULT_WEDGE_GRACE_SECS`` (ADR-001). Fails
    today: the symbol does not exist yet."""
    monkeypatch.delenv("SULIS_DAEMON_WEDGE_GRACE_SECS", raising=False)
    assert (
        session_manager_daemon.resolve_wedge_grace_secs()
        == session_manager_daemon.DEFAULT_WEDGE_GRACE_SECS
    )


def test_resolve_wedge_grace_secs_honours_a_valid_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A positive override is honoured (the test/CI injection seam) — so the
    integration suite can shrink the window without waiting the production
    default. Fails today: the symbol does not exist yet."""
    monkeypatch.setenv("SULIS_DAEMON_WEDGE_GRACE_SECS", "2.5")
    assert session_manager_daemon.resolve_wedge_grace_secs() == 2.5


@pytest.mark.parametrize(
    "bad",
    [
        "",
        "not-a-number",
        "0",
        "-5",
        # Non-finite overrides (#334-batch): `inf` / `1e400` PARSE cleanly via
        # float() AND pass `> 0`, so without an explicit finite check they would
        # be accepted as an *infinite* grace window — the daemon would then never
        # declare a wedge, silently defeating the self-heal. `nan` is already
        # caught by `> 0` (always False) but is pinned here for intent.
        "inf",
        "-inf",
        "1e400",
        "  inf  ",
        "nan",
    ],
)
def test_resolve_wedge_grace_secs_falls_back_on_bad_override(
    monkeypatch: pytest.MonkeyPatch, bad: str
) -> None:
    """THE LOAD-BEARING CONFIG TEST (WP verification artifact).

    An empty / non-numeric / non-positive / NON-FINITE override degrades to the
    conservative ``DEFAULT_WEDGE_GRACE_SECS`` — a bad tuning value must not crash
    the daemon or shrink the window so far it mistakes a slow boot for a wedge,
    and must never widen it to infinity (which would disable the self-heal
    entirely; spec §Constraints, mirroring ``resolve_idle_exit_secs``)."""
    monkeypatch.setenv("SULIS_DAEMON_WEDGE_GRACE_SECS", bad)
    assert (
        session_manager_daemon.resolve_wedge_grace_secs()
        == session_manager_daemon.DEFAULT_WEDGE_GRACE_SECS
    )


@given(raw=st.text().filter(lambda s: "\x00" not in s))
def test_resolve_wedge_grace_secs_is_always_positive_and_finite(raw: str) -> None:
    """Property (Hypothesis): for ANY override string, the resolved grace window
    is a positive, FINITE float — it is never ``inf``/``nan``/<=0.

    This is the property the four hand-picked examples in the parametrized test
    can only sample: example-based coverage missed the ``inf`` hole entirely
    (``float('inf') > 0`` is True), and a property sweep over the input space is
    exactly what surfaces it. The invariant the resolver must uphold is
    'a tuning override can only ever make the window a sane positive number, or
    fall back to the safe default' — so the result is always finite and > 0,
    whatever a user (or a typo, or a hostile env) puts in."""
    import os

    os.environ["SULIS_DAEMON_WEDGE_GRACE_SECS"] = raw
    try:
        value = session_manager_daemon.resolve_wedge_grace_secs()
    finally:
        del os.environ["SULIS_DAEMON_WEDGE_GRACE_SECS"]
    assert math.isfinite(value)
    assert value > 0


@given(raw=st.text().filter(lambda s: "\x00" not in s))
def test_resolve_idle_exit_secs_is_always_positive_and_finite(raw: str) -> None:
    """The sibling idle-exit parser carries the same shared pattern — and so the
    same ``inf`` hole — so it gets the same property guard."""
    import os

    os.environ["SULIS_DAEMON_IDLE_EXIT_SECS"] = raw
    try:
        value = session_manager_daemon.resolve_idle_exit_secs()
    finally:
        del os.environ["SULIS_DAEMON_IDLE_EXIT_SECS"]
    assert math.isfinite(value)
    assert value > 0


def test_default_wedge_grace_exceeds_the_legacy_mid_boot_poll() -> None:
    """The conservative default must be **longer** than the existing 5s mid-boot
    poll the old race-loser path used, so a slow-but-legitimate boot the old
    code already tolerated is strictly preserved — the breaker only trips
    *beyond* the legitimate window (WP Notes). Fails today: the symbol does not
    exist yet."""
    assert session_manager_daemon.DEFAULT_WEDGE_GRACE_SECS > 5.0
