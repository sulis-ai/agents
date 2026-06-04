"""End-to-end spike — the interaction-flow done-gate, proven on the real
clinics-scheme flow (CH-01KT9H / WP-004).

This is the change verifying its own thesis. It drives the **live** gate
(`wpx-index flip-status --to done`, shipped by WP-001's predicate +
WP-002's enforcer) through the full lifecycle on the real clinics-scheme
interaction-contract card:

    block  → an un-exercised interaction contract is REFUSED at flip-to-done,
             with a founder-readable reason;
    exercise → the six-step clinics flow is run end-to-end over STUB adapters
             (a PATH-shim `clinics` shim — no live Capsule/HubSpot/platform
             call), and the resulting evidence is recorded in the card
             frontmatter (ADR-001: exercised_at / exercised_by /
             exercised_attestation);
    release → the same gate now ALLOWS the flip to `done`.

The spike does NOT touch the gate code — it drives it. The committed card at
`.architecture/interaction-flow-gate/spike/work-packages/WP-CLINICS-*.md`
stays at empty-evidence; each test copies it into a hermetic temp workspace
so the block leg is always reproducible.

Verification artifact (WP-004):
    test_interaction_gate_clinics_spike.py::test_clinics_scheme_block_exercise_release
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

# Repo layout: this file is at plugins/sulis/scripts/tests/integration/.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
_REPO_ROOT = _SCRIPTS_DIR.parents[2]
_SPIKE_DIR = _REPO_ROOT / ".architecture" / "interaction-flow-gate" / "spike"
_CARD_SRC = _SPIKE_DIR / "work-packages" / "WP-CLINICS-clinics-scheme.md"
_STUB = _SPIKE_DIR / "stubs" / "clinics"

# The six steps of the clinics-scheme flow (mirrors the card's flow section).
_FLOW_STEPS = [
    "process-documents",
    "find-business",
    "look-up-business",
    "score-risk",
    "rate-quote",
    "push-indication",
]

_PROJECT = "interaction-flow-gate-spike"


# ─── workspace + gate invocation helpers ──────────────────────────────────


def _make_workspace(tmp_path: Path) -> Path:
    """Build a hermetic `.architecture/<project>/work-packages/` workspace
    holding a fresh (empty-evidence) copy of the clinics card + a minimal
    INDEX that names it, and return the repo-root the gate CLI runs against.
    """
    repo_root = tmp_path / "workspace"
    wp_dir = repo_root / ".architecture" / _PROJECT / "work-packages"
    wp_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(_CARD_SRC, wp_dir / "WP-CLINICS-clinics-scheme.md")
    (wp_dir / "INDEX.md").write_text(
        "# Spike INDEX\n\n## Work Packages\n\n"
        "| ID | Title | Primitive | Status | Depends | Blocks |\n"
        "|---|---|---|---|---|---|\n"
        "| WP-CLINICS | Clinics-scheme flow | Create | in_progress | — | — |\n",
        encoding="utf-8",
    )
    return repo_root


def _flip_to_done(repo_root: Path) -> subprocess.CompletedProcess:
    """Invoke the LIVE `wpx-index flip-status --to done` against the card."""
    return subprocess.run(
        [
            str(_SCRIPTS_DIR / "wpx-index"),
            "flip-status",
            "--wp", "WP-CLINICS",
            "--to", "done",
            "--project", _PROJECT,
            "--repo-root", str(repo_root),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )


def _record_evidence(
    repo_root: Path,
    *,
    exercised_by: str,
    attestation: str,
    when: str = "2026-06-04T16:40:00Z",
) -> None:
    """Write the three ADR-001 evidence fields into the workspace card's
    frontmatter (the act the author performs after exercising the flow)."""
    card = (
        repo_root / ".architecture" / _PROJECT / "work-packages"
        / "WP-CLINICS-clinics-scheme.md"
    )
    text = card.read_text(encoding="utf-8")
    text = text.replace("exercised_at:\n", f"exercised_at: {when}\n", 1)
    text = text.replace(
        "exercised_by:\n", f"exercised_by: {exercised_by}\n", 1
    )
    text = text.replace(
        "exercised_attestation:\n",
        f"exercised_attestation: {attestation}\n",
        1,
    )
    card.write_text(text, encoding="utf-8")


# ─── stub-harness exercise (agent-observed evidence) ──────────────────────


def _exercise_over_stubs(tmp_path: Path) -> Path:
    """Run the six-step clinics flow end-to-end over the PATH-shim stub
    harness, with NO live binary on PATH, and return the invocation-log path
    (the falsifiable `agent-observed` attestation).

    Each step is run by invoking the in-repo stub shim directly (by absolute
    path, so resolution never depends on PATH), with the stub dir prepended
    to PATH — so a bare-name `clinics` call would ALSO resolve to the shim,
    never a live install. The "no live call" guarantee rests on (a) the shim
    being the in-repo executable and (b) the invocation log recording exactly
    the stubbed steps (asserted in
    test_clinics_exercise_made_no_live_third_party_call).
    """
    log = tmp_path / "clinics-scheme.run.txt"
    stub_dir = _STUB.parent
    env = {
        **os.environ,
        # Stub dir FIRST: a bare `clinics` resolves to the shim, not a
        # live binary. The rest of PATH only provides the interpreter
        # (/usr/bin/env bash), never another `clinics`.
        "PATH": f"{stub_dir}{os.pathsep}{os.environ.get('PATH', '')}",
        "CLINICS_STUB_CALL_LOG": str(log),
        "STUB_MODE": "happy",
    }
    for step in _FLOW_STEPS:
        proc = subprocess.run(
            [str(_STUB), step],  # absolute path to the in-repo shim
            capture_output=True,
            text=True,
            env=env,
            timeout=30,
        )
        assert proc.returncode == 0, (
            f"stub step {step!r} failed: {proc.stderr}"
        )
    return log


# ─── the spike: block → exercise-over-stubs → release ─────────────────────


def test_clinics_scheme_block_exercise_release(tmp_path):
    """The WP-004 verification artifact. The full lifecycle in order against
    the live gate: block (no evidence) → exercise over stubs (record
    agent-observed evidence) → release (flip to done now succeeds)."""
    repo_root = _make_workspace(tmp_path)

    # ── BLOCK ──────────────────────────────────────────────────────────
    blocked = _flip_to_done(repo_root)
    assert blocked.returncode != 0, (
        "un-exercised clinics interaction contract MUST be refused at "
        "flip-to-done"
    )
    reason = (blocked.stdout + blocked.stderr).lower()
    assert "exercised" in reason, (
        f"block reason must name the un-exercised flow; got: {reason!r}"
    )

    # ── EXERCISE (over stubs, agent-observed) ──────────────────────────
    log = _exercise_over_stubs(tmp_path)
    invocations = log.read_text(encoding="utf-8").strip().splitlines()
    # Every flow step was driven through the stub harness, in order.
    assert [line.split()[1] for line in invocations] == _FLOW_STEPS, (
        f"all six steps must run over stubs, in order; got: {invocations!r}"
    )
    _record_evidence(
        repo_root,
        exercised_by="agent-observed",
        attestation=f"stub run transcript at {log}",
    )

    # ── RELEASE ────────────────────────────────────────────────────────
    released = _flip_to_done(repo_root)
    assert released.returncode == 0, (
        f"once exercised, the contract must flip to done: "
        f"{released.stdout}{released.stderr}"
    )


def test_clinics_scheme_releases_on_human_attested_evidence(tmp_path):
    """The second evidence source (ADR-001): a `human-attested` run with a
    named attestation also releases the gate — so the spike demonstrates
    BOTH evidence branches reach done, not just agent-observed."""
    repo_root = _make_workspace(tmp_path)

    # Un-exercised → blocked, same as the agent-observed path.
    assert _flip_to_done(repo_root).returncode != 0

    _record_evidence(
        repo_root,
        exercised_by="human-attested",
        attestation="Iain Niven-Bowling walked the clinics flow over stubs",
    )

    released = _flip_to_done(repo_root)
    assert released.returncode == 0, (
        f"human-attested evidence must release the gate: "
        f"{released.stdout}{released.stderr}"
    )


def test_clinics_exercise_made_no_live_third_party_call(tmp_path):
    """Stub-only guarantee (TDD §3): exercising the flow touches ONLY the
    PATH-shim stub — never a live `clinics`/Capsule/HubSpot binary. Proven
    three ways: (1) the invocation log records exactly the six stubbed steps
    and nothing else; (2) the in-repo shim is the executable that ran; (3) a
    bare-name `clinics` resolves to the in-repo shim with the stub dir first
    on PATH, so no system install could be reached even via PATH lookup."""
    log = _exercise_over_stubs(tmp_path)
    invocations = log.read_text(encoding="utf-8").strip().splitlines()
    assert len(invocations) == len(_FLOW_STEPS)
    assert all(line.startswith("clinics ") for line in invocations)
    # The stub is the in-repo shim (not a system install).
    assert _STUB.is_file() and os.access(_STUB, os.X_OK), (
        "the clinics stub shim must be the in-repo executable"
    )
    # With the stub dir first on PATH, a bare `clinics` resolves to the shim.
    resolved = shutil.which(
        "clinics",
        path=f"{_STUB.parent}{os.pathsep}{os.environ.get('PATH', '')}",
    )
    assert resolved == str(_STUB), (
        f"a bare `clinics` must resolve to the in-repo shim, got {resolved!r}"
    )


def test_committed_clinics_card_stays_at_empty_evidence():
    """Guard: the committed card carries NO exercise evidence, so the block
    leg is always reproducible from a fresh checkout. (Evidence is recorded
    only in the per-test temp workspace copy.)"""
    text = _CARD_SRC.read_text(encoding="utf-8")
    assert "exercised_at:\n" in text
    assert "exercised_by:\n" in text
    assert "exercised_attestation:\n" in text
