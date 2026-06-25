"""READ-ONLY introspection of the real ``agy`` binary (WP-001, CH-M7WSQ4;
PC-001 §10 re-grounding guard; TDD §Proof item 11).

These tests drive the **real** ``agy`` binary for **read-only** introspection
only — ``agy --version`` and ``agy --help``. They NEVER run ``agy`` with a
prompt or any state-changing / agent-executing invocation (no
``--prompt-interactive``, no ``--print``, no ``--dangerously-skip-permissions``);
those spawn an autonomous agent and are out of bounds for CI (the WP-009 lesson:
the real binary cannot always run a real session in CI; real Google auth is
required, which is the deferred ``agy-real-session-driver-google``).

The tests are the **grounding-stays-true guard**: they assert the binary's
version is contract-compatible (PC-001 is pinned to v1.0.x) and that ``--help``
still lists every flag the adapter emits. If a future ``agy`` upgrade changes the
flag surface, these fire so PC-001 §10 re-grounding is triggered before the
adapter is trusted in production.

They **skip cleanly** when ``agy`` is not on ``PATH`` (CI without the binary) —
exactly the WP-009 "real binary can't always run in CI" lesson.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

# Skip the whole module when the real binary is absent (CI without agy).
pytestmark = pytest.mark.skipif(
    shutil.which("agy") is None,
    reason="agy binary not on PATH (read-only introspection requires the real binary)",
)

# The flags the adapter emits (PC-001 §4); --help must list each.
_EMITTED_FLAGS = (
    "--prompt-interactive",
    "--add-dir",
    "--sandbox",
    "--conversation",
    "--model",
    "--dangerously-skip-permissions",
)


def _run_agy(*args: str) -> str:
    """Run a READ-ONLY ``agy`` introspection command, returning combined output.

    Only ``--version`` / ``--help`` are ever passed here — never a prompt or a
    state-changing invocation. A short timeout guards against an unexpected hang.
    """
    proc = subprocess.run(
        ["agy", *args],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    return (proc.stdout or "") + (proc.stderr or "")


def test_agy_version_contract_compatible():
    """``agy --version`` parses and reports a contract-compatible version.

    PC-001 is pinned to v1.0.x (grounded against 1.0.11, re-confirmed identical
    on 1.0.12). Assert major.minor is ``1.0`` (patch bumps OK); warn/xfail on a
    different major.minor so PC-001 §10 re-grounding is triggered."""
    out = _run_agy("--version").strip()
    assert out, "agy --version produced no output"

    # The version line may carry a prefix; find the first dotted numeric token.
    import re

    match = re.search(r"(\d+)\.(\d+)\.(\d+)", out)
    assert match is not None, f"could not parse a semver from agy --version: {out!r}"
    major, minor = match.group(1), match.group(2)

    if (major, minor) != ("1", "0"):
        pytest.xfail(
            f"agy reports v{major}.{minor}.x — PC-001 is pinned to v1.0.x. "
            f"Re-ground PC-001 §2/§4/§5 against the new flag surface (§10 trigger)."
        )


def test_agy_help_lists_emitted_flags():
    """``agy --help`` still lists every flag the adapter emits (PC-001 §4). This
    is the grounding-stays-true guard; it does NOT run agy with a prompt."""
    out = _run_agy("--help")
    assert out, "agy --help produced no output"
    missing = [flag for flag in _EMITTED_FLAGS if flag not in out]
    assert not missing, (
        f"agy --help no longer lists {missing} — the adapter emits flags the "
        f"binary may not accept. Re-ground PC-001 (§10 trigger)."
    )
