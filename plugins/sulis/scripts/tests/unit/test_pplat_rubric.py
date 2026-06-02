"""Structural verification for WP-004 (platform-contract-standard change).

WP-004 appends **Phase 10 — P-PLAT (Platform Contract)** to
``plugins/sulis/references/decompose-validation-rubric.md``, immediately after
P-VER (Phase 9). P-PLAT is the mechanical enforcement leg of the
defence-in-depth gate (WP-003's prose is the friendly front leg): a gated
write/deploy third-party touch with no referenced Platform Contract fails
P-PLAT regardless of prose edits (MUC-004).

The rubric is prose, so the RED cycle pins the documented phase contract as
structural assertions over the live rubric text (mirrors the P-VER tests).

Per the WP Contract (`Definition of Done > Red`):

  1. ``## Phase 10 — P-PLAT (Platform Contract)`` header present.
  2. Seven check rows (``10.01`` .. ``10.07``).
  3. Front matter carries ``platform_contract_required_from:``.
  4. The grandfather sub-phase cites ADR-006.
  5. The self-attestation block carries a P10 row.

Stdlib + pytest only, Python 3.11-safe.
"""

from __future__ import annotations

import re
from pathlib import Path

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_RUBRIC = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "references"
    / "decompose-validation-rubric.md"
)

# The seven P-PLAT check IDs (one per contract-integrity control A-1..A-8;
# 10.07 is the SHOULD freshness check).
_CHECK_IDS = tuple(f"10.0{n}" for n in range(1, 8))


def _rubric_text() -> str:
    assert _RUBRIC.is_file(), f"missing rubric {_RUBRIC}"
    return _RUBRIC.read_text(encoding="utf-8")


def test_phase_pplat_present_and_complete() -> None:
    """WP-004: the rubric carries a complete Phase 10 — P-PLAT (ADR-006)."""
    text = _rubric_text()

    # 1. The phase header.
    assert "## Phase 10 — P-PLAT (Platform Contract)" in text, (
        "Expected a '## Phase 10 — P-PLAT (Platform Contract)' header "
        "appended after Phase 9 (ADR-006)."
    )

    # 2. Seven check rows (10.01..10.07).
    missing = [cid for cid in _CHECK_IDS if cid not in text]
    assert not missing, f"P-PLAT missing check row(s): {missing}."

    # 3. Front-matter constant.
    assert "platform_contract_required_from:" in text, (
        "Expected the front-matter constant 'platform_contract_required_from:' "
        "(the merge-date grandfather constant; ADR-006)."
    )

    # 4. Grandfather sub-phase cites ADR-006.
    assert "ADR-006" in text, (
        "P-PLAT must cite ADR-006 (placement + grandfather + verdict "
        "semantics)."
    )

    # 5. Self-attestation P10 row.
    assert re.search(r"P10\b.*P-PLAT", text), (
        "Expected a self-attestation row for 'P10 P-PLAT (Platform Contract)'."
    )


def test_pplat_detects_via_frontmatter_field() -> None:
    """P-PLAT detects a gated touch via the explicit `platform:` /
    `touch-class:` WP-frontmatter field, not brittle prose scanning
    (OAQ-4 / MUC-004)."""
    text = _rubric_text()
    assert "touch-class:" in text, (
        "P-PLAT must name the `touch-class:` detection field (OAQ-4)."
    )
    assert "platform:" in text, (
        "P-PLAT must name the `platform:` detection field (OAQ-4)."
    )


def test_pplat_phase10_follows_phase9() -> None:
    """Ordering preserved: Phase 10 sits after Phase 9 (P-VER), before the
    anti-patterns section (ADR-006)."""
    text = _rubric_text()
    p9 = text.find("## Phase 9 — P-VER")
    p10 = text.find("## Phase 10 — P-PLAT")
    assert p9 != -1 and p10 != -1, "Both Phase 9 and Phase 10 headers required."
    assert p9 < p10, "Phase 10 — P-PLAT must follow Phase 9 — P-VER."


# ---------------------------------------------------------------------------
# WP-007 — the deterministic P-PLAT enforcement leg (check 10.01 + grandfather)
# ---------------------------------------------------------------------------
from _platform_contract import pplat_scan_wp_set  # noqa: E402


def test_pplat_fails_no_contract(tmp_path) -> None:
    """A WP set naming a gated write/deploy platform with no contract reference
    triggers P-PLAT FAIL → GAPS_FOUND (FR-015 / check 10.01). The keystone:
    a weakened prose gate cannot let this pass."""
    contracts_dir = tmp_path / "platform-contracts"
    contracts_dir.mkdir()
    # Only stripe.md exists; the WP set touches github-actions with a write.
    (contracts_dir / "stripe.md").write_text("# stripe", encoding="utf-8")

    wp_set = [
        {"id": "WP-001", "platform": "github-actions", "touch-class": "write"},
        {"id": "WP-002"},  # no third-party touch
    ]
    result = pplat_scan_wp_set(wp_set, contracts_dir)
    assert result["verdict"] == "GAPS_FOUND", result
    assert "github-actions" in result["missing"], result


def test_pplat_passes_when_contract_present(tmp_path) -> None:
    """A gated touch WITH the referenced contract present passes (10.01)."""
    contracts_dir = tmp_path / "platform-contracts"
    contracts_dir.mkdir()
    (contracts_dir / "github-actions.md").write_text("# gha", encoding="utf-8")

    wp_set = [{"id": "WP-001", "platform": "github-actions", "touch-class": "deploy"}]
    result = pplat_scan_wp_set(wp_set, contracts_dir)
    assert result["verdict"] == "PASS", result


def test_pplat_read_only_is_soft(tmp_path) -> None:
    """A read-only touch does not fail P-PLAT even with no contract (ADR-001
    soft-recommend)."""
    contracts_dir = tmp_path / "platform-contracts"
    contracts_dir.mkdir()
    wp_set = [{"id": "WP-001", "platform": "github-actions", "touch-class": "read-only"}]
    result = pplat_scan_wp_set(wp_set, contracts_dir)
    assert result["verdict"] == "PASS", result


def test_pplat_grandfathers(tmp_path) -> None:
    """A change whose started_at predates the merge constant passes P-PLAT
    without a contract (NFR-005, mirrors P-VER's grandfather)."""
    contracts_dir = tmp_path / "platform-contracts"
    contracts_dir.mkdir()  # empty — no contract anywhere
    wp_set = [{"id": "WP-001", "platform": "github-actions", "touch-class": "write"}]
    result = pplat_scan_wp_set(
        wp_set,
        contracts_dir,
        started_at="2026-01-01",
        required_from="2026-06-02",
    )
    assert result["verdict"] == "PASS — grandfathered", result
