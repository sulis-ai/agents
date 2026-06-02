"""Verify phase of the discover-project skill.

Implements the post-mint drift verification + roll-back contract per:

- TDD §Canonical Identifiers: Step ULID
  ``01KT1WDSST09RUNDRIFTDET`` ("run-drift-detector-on-mint").
- TDD §Armor §Cross-tenant drift semantics: the verifier MUST allow
  ``release_workflow_ref`` (and the forward-compatibility hook
  ``belongs_to_product_ref``) to cross from the consumer tenant to
  the marketplace tenant; without that allowance every consumer mint
  would falsely FAIL drift.
- FR-008 (post-mint drift verification).
- MUC-005 (unknown-workflow-ulid) → roll-back-and-surface system response.

The verifier delegates to the existing blocking drift detector at
``plugins/sulis/scripts/check-canonical-drift.py`` (commit ``7d666df``
extended by WP-009 with the new ``--scope`` + flag plumbing). One
entity per run; non-zero exit → roll back the mint by deleting the
just-written entity file; surface the structured failure message
to the operator verbatim.

The drift detector is invoked via ``subprocess.run``. Callers can
swap the detector path (test harnesses, alternate vendor checks) via
the ``drift_detector_path`` kwarg; the default points at the canonical
script under ``plugins/sulis/scripts``.

MUC-005 system response (quote-verbatim for operator surfaces):

    The Project entity at ``<entity_path>`` was minted but failed
    post-mint drift verification. The mint has been rolled back. The
    drift detector reported:

        <stderr>

    This typically means a ``release_workflow_ref`` pointed at a
    Workflow ULID that isn't present in any tenant manifest. Re-run
    once the release-train Workflow is published, or correct the
    consumer's Project descriptor.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

# Default cross-tenant allowances per TDD §Armor §Cross-tenant drift semantics.
# These are the ref types known to cross from the consumer tenant to the
# marketplace tenant. ``belongs_to_product_ref`` is a forward-compatibility
# hook for the foundation Project schema (post-v1).
_DEFAULT_CROSS_TENANT_REFS_ALLOWED: tuple[str, ...] = (
    "release_workflow_ref",
    "belongs_to_product_ref",
)

# Default location of the drift detector — resolved relative to THIS module's
# file, not the current working directory. verifier.py lives at
# ``plugins/sulis/scripts/_discovery/verifier.py``; the detector is its
# sibling-one-up at ``plugins/sulis/scripts/check-canonical-drift.py``.
# Resolving via ``__file__`` makes the path point at the installed plugin
# location regardless of cwd — a cwd-relative path only resolved from inside
# the marketplace repo, so every consumer-repo mint failed (the bug this WP
# fixes). Callers can override via ``drift_detector_path`` for test harnesses.
_DEFAULT_DRIFT_DETECTOR = (
    Path(__file__).resolve().parent.parent / "check-canonical-drift.py"
)

# Exit code emitted by argparse on unrecognised flags.
_UNRECOGNISED_FLAG_EXIT_CODE = 2


@dataclass(frozen=True)
class DriftVerifyResult:
    """Outcome of one drift-detector invocation, scoped to one entity.

    Attributes:
        ok: True iff the detector exited 0.
        exit_code: The detector's exit code (0 = clean, 1 = drift, 2 = invocation error).
        stderr: The detector's structured failure message; founder-readable. Empty on success.
    """

    ok: bool
    exit_code: int
    stderr: str


class DriftVerifyFailed(Exception):
    """Raised when the drift detector exits non-zero AFTER roll-back has executed.

    Carries the drift detector's stderr so the skill prose (WP-008)
    can surface the structured failure message verbatim per MUC-005.
    """

    def __init__(self, result: DriftVerifyResult, rolled_back_path: Path) -> None:
        self.result = result
        self.rolled_back_path = rolled_back_path
        super().__init__(
            f"Drift verification failed (exit {result.exit_code}). "
            f"Mint at {rolled_back_path} has been rolled back."
        )


class DriftDetectorExtensionMissingError(Exception):
    """Raised when the drift detector doesn't recognise the WP-007 flag set.

    Distinct from ``DriftVerifyFailed`` because this is an *infrastructure*
    problem, not a content problem. The operator-visible diagnostic
    points at WP-009 (the drift-detector-extensions WP) so the right
    person knows where to look.
    """

    def __init__(self, stderr: str) -> None:
        self.stderr = stderr
        super().__init__(
            "The drift detector at "
            f"{_DEFAULT_DRIFT_DETECTOR} does not recognise the "
            "--cross-tenant-refs-allowed-for flag yet. "
            "This means WP-009 (drift-detector-extensions) has not "
            "been deployed. Without the flag, every consumer mint "
            "would falsely FAIL drift on release_workflow_ref. "
            f"Detector stderr was:\n{stderr}"
        )


def _invoke_drift_detector(
    entity_path: Path,
    *,
    cross_tenant_refs_allowed: list[str] | tuple[str, ...] | None,
    drift_detector_path: Path,
) -> DriftVerifyResult:
    """Build the argv + run subprocess.run; classify the outcome.

    Internal helper composed by both public entry points. Centralises:
    - argv assembly (so the flag order is consistent + easily asserted in tests)
    - the "unrecognised flag" diagnostic (WP-009 race detection)
    """
    refs = (
        list(cross_tenant_refs_allowed)
        if cross_tenant_refs_allowed is not None
        else list(_DEFAULT_CROSS_TENANT_REFS_ALLOWED)
    )
    argv = [
        "python3",
        str(drift_detector_path),
        "--scope",
        str(entity_path),
        "--cross-tenant-refs-allowed-for",
        ",".join(refs),
    ]

    completed = subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
    )
    stderr = completed.stderr or ""

    # WP-009 race: detector ran but argparse rejected our flag because
    # the extension isn't deployed yet. Surface as a typed error rather
    # than silently passing OR pretending it's a content failure.
    if (
        completed.returncode == _UNRECOGNISED_FLAG_EXIT_CODE
        and "unrecognized arguments" in stderr
        and "--cross-tenant-refs-allowed-for" in stderr
    ):
        raise DriftDetectorExtensionMissingError(stderr)

    return DriftVerifyResult(
        ok=completed.returncode == 0,
        exit_code=completed.returncode,
        stderr=stderr,
    )


def run_drift_check_on_entity(
    entity_path: Path,
    *,
    cross_tenant_refs_allowed: list[str] | None = None,
    drift_detector_path: Path = _DEFAULT_DRIFT_DETECTOR,
) -> DriftVerifyResult:
    """Invoke the drift detector scoped to ONE just-minted entity.

    Defaults ``cross_tenant_refs_allowed`` to
    ``['release_workflow_ref', 'belongs_to_product_ref']`` per TDD
    §Armor §Cross-tenant drift semantics — the only legitimate
    consumer→marketplace cross-tenant references in v1 (plus one
    forward-compatibility hook).

    Does NOT roll back on failure; that decision belongs to the
    caller (the composition root of the Verify phase). Use
    ``verify_and_roll_back_on_failure`` for the standard "mint + verify
    + roll-back" composition.

    Raises:
        DriftDetectorExtensionMissingError: If the detector doesn't
            recognise the ``--cross-tenant-refs-allowed-for`` flag
            (WP-009 not yet deployed).
    """
    return _invoke_drift_detector(
        entity_path,
        cross_tenant_refs_allowed=cross_tenant_refs_allowed,
        drift_detector_path=drift_detector_path,
    )


def verify_and_roll_back_on_failure(
    entity_path: Path,
    *,
    cross_tenant_refs_allowed: list[str] | None = None,
    drift_detector_path: Path = _DEFAULT_DRIFT_DETECTOR,
) -> DriftVerifyResult:
    """Run the drift check; on failure, delete the entity and raise.

    Composition of ``run_drift_check_on_entity`` + ``unlink`` rooted
    in MUC-005's system response: drift failure = roll-back-and-surface.

    On success: returns the ``DriftVerifyResult`` (``ok=True``); the
    entity file remains on disk.

    On failure: the entity is unlinked via
    ``entity_path.unlink(missing_ok=False)`` — explicit; if the file
    is already gone, that's a more-serious problem than the drift
    failure and we want to raise loudly. Then raises
    ``DriftVerifyFailed`` carrying the drift detector's stderr so the
    operator-facing surface (WP-008's skill prose) can quote the
    structured failure verbatim.

    Raises:
        DriftVerifyFailed: Drift detected; entity rolled back.
        DriftDetectorExtensionMissingError: WP-009 not yet deployed
            (entity is NOT rolled back in this case — the mint itself
            is fine, the verifier infrastructure isn't).
        FileNotFoundError: Entity file already missing when we tried to roll back.
    """
    result = _invoke_drift_detector(
        entity_path,
        cross_tenant_refs_allowed=cross_tenant_refs_allowed,
        drift_detector_path=drift_detector_path,
    )

    if result.ok:
        return result

    # Drift detected — roll back the mint, then raise with stderr attached.
    entity_path.unlink(missing_ok=False)
    raise DriftVerifyFailed(result, rolled_back_path=entity_path)
