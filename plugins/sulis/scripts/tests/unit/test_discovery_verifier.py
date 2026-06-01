"""Unit tests for the Verify phase of the discover-project skill.

Module under test: ``_discovery.verifier``.

These tests pin the contract defined in WP-007 (verify-phase) per TDD
§Armor §Cross-tenant drift semantics + FR-008 + MUC-005. The verifier:

1. Invokes the existing drift detector
   (``plugins/sulis/scripts/check-canonical-drift.py``) scoped to ONE
   just-minted Project entity, with
   ``--cross-tenant-refs-allowed-for release_workflow_ref,belongs_to_product_ref``
   so the legitimate cross-tenant boundary at ``release_workflow_ref``
   isn't reported as drift.
2. Rolls back (``entity_path.unlink(missing_ok=False)``) when the
   detector exits non-zero, then raises ``DriftVerifyFailed`` so the
   skill prose can surface the structured failure message verbatim
   (MUC-005 system response).
3. Distinguishes "detector ran and flagged drift" (normal failure;
   ``DriftVerifyFailed``) from "detector doesn't yet recognise our
   flag" (WP-009 race; ``DriftDetectorExtensionMissingError``) so the
   operator sees a clear diagnostic rather than a silent pass.

The drift detector is invoked via ``subprocess.run`` — tests inject a
fake ``subprocess.run`` via monkeypatch. No real subprocess calls.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


# ─── Helpers ──────────────────────────────────────────────────────────────


def _fake_completed_process(
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
    argv: list[str] | None = None,
) -> subprocess.CompletedProcess:
    """Build a CompletedProcess as if subprocess.run had executed."""
    return subprocess.CompletedProcess(
        args=argv or [],
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
    )


def _install_fake_subprocess_run(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> dict:
    """Replace ``_discovery.verifier``'s ``subprocess.run`` with a recorder.

    Returns a dict whose ``"argv"`` key gets populated with the argv
    list passed to the recorded invocation, so individual tests can
    assert on the flags + scope path the verifier built.
    """
    capture: dict = {"argv": None, "kwargs": None, "calls": 0}

    def _fake_run(argv, **kwargs):
        capture["argv"] = list(argv)
        capture["kwargs"] = kwargs
        capture["calls"] += 1
        return _fake_completed_process(
            returncode=returncode,
            stdout=stdout,
            stderr=stderr,
            argv=list(argv),
        )

    # Patch the symbol on the _discovery.verifier module so its
    # bound ``subprocess.run`` reference resolves to our fake.
    from _discovery import verifier  # noqa: PLC0415 — late import

    monkeypatch.setattr(verifier.subprocess, "run", _fake_run)
    return capture


def _write_fake_entity(tmp_path: Path, name: str = "myproj.jsonld") -> Path:
    """Drop a placeholder file so unlink() targets a real path."""
    p = tmp_path / name
    p.write_text('{"@id":"dna:project:01KFAKE000000000000000000A"}\n', encoding="utf-8")
    return p


# ─── Red tests ────────────────────────────────────────────────────────────


def test_drift_pass_returns_ok_True(tmp_path, monkeypatch):
    """A clean drift run returns DriftVerifyResult(ok=True, exit_code=0)."""
    from _discovery.verifier import run_drift_check_on_entity

    _install_fake_subprocess_run(monkeypatch, returncode=0, stdout="", stderr="")
    entity = _write_fake_entity(tmp_path)

    result = run_drift_check_on_entity(entity)

    assert result.ok is True
    assert result.exit_code == 0
    assert result.stderr == ""


def test_drift_fail_returns_ok_False_with_stderr(tmp_path, monkeypatch):
    """A failing drift run surfaces stderr and ok=False."""
    from _discovery.verifier import run_drift_check_on_entity

    _install_fake_subprocess_run(
        monkeypatch,
        returncode=1,
        stderr="DRIFT: release_workflow_ref points at unknown workflow ULID",
    )
    entity = _write_fake_entity(tmp_path)

    result = run_drift_check_on_entity(entity)

    assert result.ok is False
    assert result.exit_code == 1
    assert "release_workflow_ref" in result.stderr


def test_verify_and_roll_back_deletes_entity_on_failure(tmp_path, monkeypatch):
    """On drift failure, the entity file is unlinked and DriftVerifyFailed raised."""
    from _discovery.verifier import DriftVerifyFailed, verify_and_roll_back_on_failure

    _install_fake_subprocess_run(
        monkeypatch,
        returncode=1,
        stderr="DRIFT: unknown-workflow-ulid",
    )
    entity = _write_fake_entity(tmp_path)
    assert entity.exists()

    with pytest.raises(DriftVerifyFailed):
        verify_and_roll_back_on_failure(entity)

    assert entity.exists() is False, (
        "verify_and_roll_back_on_failure must delete entity on failure"
    )


def test_verify_and_roll_back_preserves_entity_on_success(tmp_path, monkeypatch):
    """On drift pass, the entity file remains on disk; no exception raised."""
    from _discovery.verifier import verify_and_roll_back_on_failure

    _install_fake_subprocess_run(monkeypatch, returncode=0)
    entity = _write_fake_entity(tmp_path)

    result = verify_and_roll_back_on_failure(entity)

    assert result.ok is True
    assert entity.exists() is True


def test_cross_tenant_flag_passed_to_detector(tmp_path, monkeypatch):
    """argv MUST include --cross-tenant-refs-allowed-for with the WP-007 default list."""
    from _discovery.verifier import run_drift_check_on_entity

    capture = _install_fake_subprocess_run(monkeypatch, returncode=0)
    entity = _write_fake_entity(tmp_path)

    run_drift_check_on_entity(entity)

    argv = capture["argv"]
    assert argv is not None
    # Flag should be passed; defaults match TDD §Armor §Cross-tenant drift semantics.
    flag_idx = argv.index("--cross-tenant-refs-allowed-for")
    assert argv[flag_idx + 1] == "release_workflow_ref,belongs_to_product_ref"


def test_scope_arg_passed_to_detector(tmp_path, monkeypatch):
    """argv MUST include --scope <entity_path>."""
    from _discovery.verifier import run_drift_check_on_entity

    capture = _install_fake_subprocess_run(monkeypatch, returncode=0)
    entity = _write_fake_entity(tmp_path)

    run_drift_check_on_entity(entity)

    argv = capture["argv"]
    assert argv is not None
    scope_idx = argv.index("--scope")
    assert argv[scope_idx + 1] == str(entity)


def test_DriftVerifyFailed_carries_rolled_back_path(tmp_path, monkeypatch):
    """DriftVerifyFailed exposes .rolled_back_path equal to the deleted entity."""
    from _discovery.verifier import DriftVerifyFailed, verify_and_roll_back_on_failure

    _install_fake_subprocess_run(monkeypatch, returncode=1, stderr="DRIFT: bad ref")
    entity = _write_fake_entity(tmp_path)

    with pytest.raises(DriftVerifyFailed) as exc_info:
        verify_and_roll_back_on_failure(entity)

    assert exc_info.value.rolled_back_path == entity


def test_DriftVerifyFailed_carries_stderr_for_operator_surface(tmp_path, monkeypatch):
    """The exception carries the detector's stderr so WP-008 can surface it verbatim."""
    from _discovery.verifier import DriftVerifyFailed, verify_and_roll_back_on_failure

    failure_msg = (
        "DRIFT: release_workflow_ref points at dna:workflow:01KBOGUS000000000000000000 "
        "which is not present in any tenant manifest (MUC-005)."
    )
    _install_fake_subprocess_run(monkeypatch, returncode=1, stderr=failure_msg)
    entity = _write_fake_entity(tmp_path)

    with pytest.raises(DriftVerifyFailed) as exc_info:
        verify_and_roll_back_on_failure(entity)

    assert failure_msg in exc_info.value.result.stderr


def test_detector_missing_raises_clear_error(tmp_path, monkeypatch):
    """If the detector exits 2 with an 'unknown flag' stderr (WP-009 not yet
    deployed), the verifier raises ``DriftDetectorExtensionMissingError`` with
    a hint pointing at WP-009 — NOT a silent pass.
    """
    from _discovery.verifier import (
        DriftDetectorExtensionMissingError,
        run_drift_check_on_entity,
    )

    _install_fake_subprocess_run(
        monkeypatch,
        returncode=2,
        stderr=(
            "check-canonical-drift.py: error: unrecognized arguments: "
            "--cross-tenant-refs-allowed-for release_workflow_ref,belongs_to_product_ref"
        ),
    )
    entity = _write_fake_entity(tmp_path)

    with pytest.raises(DriftDetectorExtensionMissingError) as exc_info:
        run_drift_check_on_entity(entity)

    # The hint must reference WP-009 so the operator knows where to look.
    assert "WP-009" in str(exc_info.value)
