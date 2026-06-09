"""WP-003 wiring — the WP done-transition runs the seam-close gate.

The seam-close gate must actually fire at the `wpx-step12 wrap`
done-transition (step 12.2a, immediately after the `in_progress→done`
flip), or it's a gate in name only. These are structural assertions over
the live tool/skill text — the same shape as
`test_ship_acceptance_gate_wiring.py` asserts over `change/SKILL.md`.

Two layers (mirrors TDD §Test surface File 2):
  - `wpx-step12` invokes `_seam_close_gate.evaluate(...)` after the flip,
    emits a `gate_block` on a `blocked` seam, and threads `--allow-deferred`
    (observed-or-blocked) — **made green by WP-003 (this WP).**
  - `run-wp`/`run-all` SKILL.md document the seam-close gate at WP-done —
    **made green by WP-004.** Authored failing-first here; WP-004 appends
    its run-wp/run-all assertions to this same file (it is the sole appender,
    `dependsOn` WP-003).

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[5]
_STEP12 = _REPO_ROOT / "plugins" / "sulis" / "scripts" / "wpx-step12"
_RUNWP = _REPO_ROOT / "plugins" / "sulis" / "skills" / "run-wp" / "SKILL.md"
_RUNALL = _REPO_ROOT / "plugins" / "sulis" / "skills" / "run-all" / "SKILL.md"


def _step12_text() -> str:
    assert _STEP12.is_file(), f"missing {_STEP12}"
    return _STEP12.read_text(encoding="utf-8")


def _runwp_text() -> str:
    assert _RUNWP.is_file(), f"missing {_RUNWP}"
    return _RUNWP.read_text(encoding="utf-8")


def _runall_text() -> str:
    assert _RUNALL.is_file(), f"missing {_RUNALL}"
    return _RUNALL.read_text(encoding="utf-8")


# ── wpx-step12 wiring (made green by WP-003) ─────────────────────────────────


def test_wpx_step12_invokes_seam_close_gate() -> None:
    """The done-transition must reference + call the seam-close gate, and do so
    AFTER the status flip (step 12.2a) — not a gate in name only."""
    text = _step12_text()
    assert "_seam_close_gate" in text, (
        "wpx-step12 must reference the seam-close gate module (_seam_close_gate)"
    )
    assert "evaluate(" in text, (
        "wpx-step12 must call _seam_close_gate.evaluate(...) at the done-transition"
    )
    # The gate fires AFTER the flip (12.2a), not before — the seam-close
    # predicate must read post-flip INDEX state (ADR-003).
    flip_pos = text.find("flip-status")
    eval_pos = text.find("evaluate(")
    assert flip_pos != -1, "wpx-step12 must still perform the status flip (12.2)"
    assert eval_pos > flip_pos, (
        "the seam-close gate (evaluate) must be invoked AFTER the status flip "
        "(step 12.2a is after 12.2) — ADR-003"
    )


def test_seam_gate_blocks_on_blocked_verdict() -> None:
    """A `blocked` seam must emit a gate-block signal the calling session reads
    to halt seam-close — mirrors test_ship_blocks_on_blocked_verdict."""
    text = _step12_text()
    assert "gate_block" in text, (
        "wpx-step12 must emit a gate_block field on a blocked seam so the "
        "calling session halts seam-close as 'not done'"
    )
    assert "blocked" in text, (
        "wpx-step12 must branch on the gate's blocked verdict"
    )
    # The flip is NOT rolled back on a block (ADR-003): the wrap still emits ok.
    assert "seam_close" in text, (
        "wpx-step12 must thread the seam_close result into the wrap envelope"
    )


def test_seam_gate_treats_deferred_as_blocking_by_default() -> None:
    """Observed-or-blocked by default, with the conscious --allow-deferred
    escape threaded through — mirrors test_ship_treats_deferred_as_blocking."""
    text = _step12_text()
    assert "allow-deferred" in text or "allow_deferred" in text, (
        "wpx-step12 must thread the --allow-deferred escape through to the gate"
    )
    assert "allow_deferred" in text, (
        "wpx-step12 must pass allow_deferred to _seam_close_gate.evaluate(...)"
    )


# ── run-wp / run-all documentation (made green by WP-004) ────────────────────


def test_runwp_documents_seam_close_gate() -> None:
    """run-wp/SKILL.md documents the seam-close gate: it names a seam-close
    subsection, the WP-done firing point (the wpx-step12 done-transition), the
    observed-or-blocked discipline, and the --allow-deferred escape (WP-004)."""
    text = _runwp_text().lower()
    assert "seam-close" in text or "seam close" in text, (
        "run-wp/SKILL.md must document the seam-close gate at WP-done (WP-004)"
    )
    # Names the WP-done firing point (the done-transition / wpx-step12 wrap).
    assert (
        "wpx-step12" in text or "done-transition" in text or "done transition" in text
    ), (
        "run-wp/SKILL.md must name the WP-done firing point (the wpx-step12 "
        "done-transition) where the seam-close gate runs"
    )
    # The observed-or-blocked discipline + the --allow-deferred escape.
    assert "observed" in text and "blocked" in text, (
        "run-wp/SKILL.md must state the seam-close observed-or-blocked verdict"
    )
    assert "allow-deferred" in text or "allow_deferred" in text, (
        "run-wp/SKILL.md must document the --allow-deferred escape (the "
        "conscious, recorded deferral; default is observed-or-blocked)"
    )


def test_runall_documents_seam_close_gate() -> None:
    """run-all/SKILL.md documents the seam-close gate firing when a
    seam-spanning WP completes, with the observed-or-blocked discipline and the
    --allow-deferred escape (WP-004)."""
    text = _runall_text().lower()
    assert "seam-close" in text or "seam close" in text, (
        "run-all/SKILL.md must document the seam-close gate firing when a "
        "seam-spanning WP completes (WP-004)"
    )
    # The seam-spanning-WP completion trigger.
    assert "seam-spanning" in text or "seam spanning" in text, (
        "run-all/SKILL.md must name the seam-spanning-WP completion as the "
        "seam-close gate's firing trigger"
    )
    # The observed-or-blocked discipline + the --allow-deferred escape.
    assert "observed" in text and "blocked" in text, (
        "run-all/SKILL.md must state the seam-close observed-or-blocked verdict"
    )
    assert "allow-deferred" in text or "allow_deferred" in text, (
        "run-all/SKILL.md must document the --allow-deferred escape"
    )
