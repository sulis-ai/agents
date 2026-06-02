"""Structural verification for WP-003 (platform-contract-standard change).

WP-003 wires the **design-phase gate** (the friendly front leg of the
defence-in-depth pair) and the **harness-invocation glue** into the two
design-phase skills:

  * ``plugins/sulis/skills/specify/SKILL.md`` — gate-detection prose only
    (detect a gated third-party touch, ask for a Platform Contract). It does
    NOT run the harness.
  * ``plugins/sulis/skills/draft-architecture/SKILL.md`` — gate-detection
    prose AND the harness-invocation step (run the faithful-generation-harness
    via ``/sulis-brain:execute-workflow``, land the bound-claim table as the
    contract body, BLOCKER on an unresolvable sibling repo).

The skills are prose, not code, so the RED cycle pins the documented gate
contract as structural assertions over the live SKILL.md text (mirrors
``test_platform_contract_standard.py``).

Per the WP Contract (`Definition of Done > Red`):

  1. Both skills reference the standard (``PLATFORM_CONTRACT_STANDARD.md``) or
     the storage dir (``platform-contracts/``).
  2. Both carry the write/deploy hard-gate vs read-only soft-recommend
     distinction (FR-002 / ADR-001).
  3. ``draft-architecture`` references ``/sulis-brain:execute-workflow`` (the
     harness dispatch) AND the BLOCKER-on-unresolvable path (FR-003 / ADR-004).

Stdlib + pytest only, Python 3.11-safe.
"""

from __future__ import annotations

import re
from pathlib import Path

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_SKILLS = _REPO_ROOT / "plugins" / "sulis" / "skills"
_SPECIFY = _SKILLS / "specify" / "SKILL.md"
_DRAFT_ARCH = _SKILLS / "draft-architecture" / "SKILL.md"


def _read(path: Path) -> str:
    assert path.is_file(), f"missing skill file {path}"
    return path.read_text(encoding="utf-8")


def test_skills_reference_platform_contract() -> None:
    """Both design skills reference the Platform Contract standard or its
    storage directory (FR-002)."""
    for path in (_SPECIFY, _DRAFT_ARCH):
        text = _read(path)
        assert (
            "PLATFORM_CONTRACT_STANDARD.md" in text
            or "platform-contracts/" in text
        ), (
            f"{path.parent.name}/SKILL.md must reference the Platform "
            "Contract standard or its storage directory (FR-002)."
        )


def test_both_skills_carry_gate_distinction() -> None:
    """Both skills carry the write/deploy hard-gate vs read-only
    soft-recommend distinction (FR-002 / ADR-001)."""
    for path in (_SPECIFY, _DRAFT_ARCH):
        text = _read(path).lower()
        # The three load-bearing touch-classes must all appear in the gate
        # prose so the distinction is documented, not implied.
        for token in ("write", "deploy", "read-only"):
            assert token in text, (
                f"{path.parent.name}/SKILL.md gate prose must name the "
                f"'{token}' touch-class (write/deploy hard-gate vs read-only "
                "soft-recommend; ADR-001)."
            )
        # The hard-gate vs soft-recommend asymmetry must be expressed.
        assert re.search(r"hard[- ]gate", text) or "hard gate" in text, (
            f"{path.parent.name}/SKILL.md must name the hard-gate for "
            "write/deploy touches (ADR-001)."
        )
        assert "soft" in text or "recommend" in text, (
            f"{path.parent.name}/SKILL.md must name the soft-recommend for "
            "read-only touches (ADR-001)."
        )


def test_draft_architecture_runs_harness_with_blocker_path() -> None:
    """draft-architecture wires the harness dispatch AND the
    BLOCKER-on-unresolvable path (FR-003 / ADR-004 / OAQ-1)."""
    text = _read(_DRAFT_ARCH)
    assert "/sulis-brain:execute-workflow" in text, (
        "draft-architecture/SKILL.md must dispatch the faithful-generation-"
        "harness via /sulis-brain:execute-workflow (FR-003 / ADR-004)."
    )
    assert "faithful-generation-harness" in text, (
        "draft-architecture/SKILL.md must name the faithful-generation-harness "
        "as the contract-production mechanism (FR-003)."
    )
    assert "BLOCKER" in text, (
        "draft-architecture/SKILL.md must record the BLOCKER-on-unresolvable-"
        "sibling-repo path — no hand-authored fallback (OAQ-1 / ADR-004)."
    )


def test_specify_does_not_run_harness() -> None:
    """specify only detects-and-asks; the harness run lives in
    draft-architecture (ADR-004). Guards against the glue leaking into the
    wrong skill."""
    text = _read(_SPECIFY)
    assert "/sulis-brain:execute-workflow" not in text, (
        "specify/SKILL.md must NOT run the harness — it detects-and-asks "
        "only; the harness-invocation step lives in draft-architecture "
        "(ADR-004)."
    )
