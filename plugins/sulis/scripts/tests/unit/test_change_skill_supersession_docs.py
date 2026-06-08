"""Doc-lint guard for WP-008 — supersession housekeeping + founder docs.

ADR-003 / TDD §6. With the shared-daemon model landed (WP-001..WP-007), the
prior terminal paths are superseded:

  * the standalone-``start``-window path (CH-01KTK7) — ``start --spawn`` used to
    open a Terminal running a *standalone* ``claude``; it now opens the desktop
    VIEWER attached to the change's shared session, and
  * the cockpit's own ephemeral host (CH-01KTHV) — ``startSessionManagerHost``
    on a per-run temp socket — folded into the shared daemon on the stable
    socket.

WP-008 is a **documentation reconciliation** (``primitive: document``,
trivial-change carveout). There is no runtime behaviour to drive, so the RED
gate is a *doc-lint*: it pins the realized invariants on the live
founder-facing ``/sulis:change`` skill and on the change record, and asserts no
dangling reference to the retired paths survives in the founder-facing copy.

The realized model the founder-facing narrative MUST describe:

  1. Starting a change opens a **desktop VIEW** onto the change's *one* session
     (not a standalone ``claude`` window).
  2. The cockpit Terminal and the desktop window are **two views of the same
     session** (the old "the in-cockpit terminal is NOT what start opens"
     separation is wrong under the shared model and must be gone).
  3. Closing the desktop window **detaches** — the session persists
     (detach-only; no kill-from-desktop).

Stdlib + pytest only, Python 3.11-safe. Paths resolve relative to this test
file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SKILL = _REPO_ROOT / "plugins" / "sulis" / "skills" / "change" / "SKILL.md"


def _read(path: Path) -> str:
    if not path.exists():
        pytest.fail(
            f"{path.name} missing at {path}. WP-008 reconciles this file; the "
            "doc-lint assertions cannot run until it exists."
        )
    return path.read_text(encoding="utf-8")


# ─── The founder-facing narrative describes the realized two-views model ─────


def test_skill_describes_desktop_view_onto_shared_session():
    """The ``start`` narrative says the window is a VIEW onto the change's
    session — not a standalone ``claude`` (ADR-003, supersedes CH-01KTK7)."""
    text = _read(_SKILL).lower()
    assert "view" in text and "session" in text
    # The realized framing: a desktop view onto the change's (one/shared)
    # session. We accept any of the natural phrasings the founder copy may use.
    assert re.search(
        r"(desktop\s+view|view\s+onto|window\s+(?:is\s+)?a\s+view)", text
    ), (
        "The start narrative must describe the spawned window as a VIEW onto "
        "the change's session (the desktop view), not a standalone claude "
        "window (ADR-003)."
    )


def test_skill_describes_two_views_one_session():
    """Cockpit + desktop are two views of the SAME session — the shared-model
    invariant (TDD §1, ADR-003)."""
    text = _read(_SKILL).lower()
    assert re.search(
        r"(two\s+views|same\s+session|one\s+session|both\s+views)", text
    ), (
        "The founder copy must state that the cockpit Terminal and the desktop "
        "window are two views of the SAME (one) session."
    )
    # And it must mention the cockpit as a co-view, not as a separate world.
    assert "cockpit" in text


def test_skill_describes_detach_on_close():
    """Closing the desktop window detaches; the session persists (detach-only,
    no kill-from-desktop) — acceptance #5 / TDD §7 Q1 default."""
    text = _read(_SKILL).lower()
    assert re.search(
        r"(detach|persist|stays?\s+(?:alive|running|open)|keeps?\s+running"
        r"|doesn'?t\s+end|never\s+ends?|session\s+(?:lives|survives))",
        text,
    ), (
        "The founder copy must make clear that closing the desktop window does "
        "NOT end the session — it detaches; the session persists."
    )


# ─── No dangling reference to the retired paths in the founder-facing copy ───


def test_skill_has_no_standalone_claude_window_reference():
    """No dangling 'standalone claude window' framing survives in the
    founder-facing skill (the retired CH-01KTK7 path)."""
    text = _read(_SKILL).lower()
    assert "standalone claude" not in text, (
        "Founder-facing SKILL.md still calls the window a 'standalone claude' "
        "— the retired CH-01KTK7 path. The window now runs the desktop viewer "
        "attached to the shared session (ADR-003)."
    )
    # The specific stale separation the WP-006 executor deferred: the old copy
    # claimed the in-cockpit terminal is NOT what start opens. Under the shared
    # model both are views of one session, so that disclaimer must be gone.
    assert "is not what `start` opens" not in text.replace("\n", " "), (
        "The stale 'the in-cockpit terminal is not what start opens' "
        "separation contradicts the two-views-one-session model and must be "
        "removed (ADR-003)."
    )


def test_skill_has_no_internal_supersession_ids_in_founder_prose():
    """Founder-facing copy carries no internal supersession identifiers in
    prose meant for the founder (CLAUDE.md non-negotiable #6/#7; WP-008
    Contract). The supersession framing — the prior-direction change IDs and
    the retired host-spawn symbol — belongs in the records/docstrings, never in
    the founder copy.

    (``ADR-003`` is *not* in this list: it has a legitimate pre-existing
    founder-doc citation in the ``start`` preflight that predates this WP and is
    out of its scope.)
    """
    text = _read(_SKILL)
    for token in ("CH-01KTK7", "CH-01KTHV", "startSessionManagerHost"):
        assert token not in text, (
            f"Internal supersession identifier {token!r} leaked into the "
            f"founder-facing SKILL.md. Supersession framing belongs in the "
            f"records/docstrings, not in the founder copy."
        )
