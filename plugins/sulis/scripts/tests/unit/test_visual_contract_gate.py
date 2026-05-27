"""Unit tests for the mandatory visual-contract gate (#45, UXD-14).

The gate makes the visual contract unskippable for user-facing surfaces. Its
write-time half lives in `validate_frontend_wp_visual_contract`: a
`kind: frontend` WP MUST declare a `visual_contract:` naming the visual-
contract WP it depends on (and that id MUST also be in `dependsOn`, so the
existing list-ready done-oracle won't dispatch the frontend WP before the
contract WP is signed off). The only bypass is an explicit logged exemption
(`visual_contract: exempt — <reason>`) or a `prototype` WP.

This is the deterministic, hardest-to-bypass layer — it fires at the single
chokepoint every WP passes through to reach the INDEX (`_cells_from_
frontmatter`), exactly like the L-03 status validator.
"""

from __future__ import annotations

from _wpxlib import validate_frontend_wp_visual_contract


def _fe(**overrides) -> dict:
    base = {
        "id": "WP-010",
        "kind": "frontend",
        "visual_contract": "WP-009",
        "dependsOn": ["WP-009"],
    }
    base.update(overrides)
    return base


# ─── non-frontend WPs are never gated ───────────────────────────────────────


def test_backend_wp_is_not_gated():
    assert validate_frontend_wp_visual_contract({"kind": "backend"}) is None


def test_contract_wp_itself_is_not_gated():
    # The visual-contract WP is kind: contract, not frontend — it must not
    # require a visual contract of its own (no infinite regress).
    assert validate_frontend_wp_visual_contract({"kind": "contract"}) is None


def test_missing_kind_is_not_gated():
    assert validate_frontend_wp_visual_contract({}) is None


# ─── frontend WPs: the gate ─────────────────────────────────────────────────


def test_frontend_with_contract_in_deps_passes():
    assert validate_frontend_wp_visual_contract(_fe()) is None


def test_frontend_without_visual_contract_is_rejected():
    msg = validate_frontend_wp_visual_contract(_fe(visual_contract=""))
    assert msg is not None
    assert "visual_contract" in msg
    assert "UXD-14" in msg


def test_frontend_with_contract_not_in_deps_is_rejected():
    # Declares a contract but doesn't depend on it → list-ready would dispatch
    # it before the contract is signed off. Rejected.
    msg = validate_frontend_wp_visual_contract(
        _fe(visual_contract="WP-009", dependsOn=["WP-001"])
    )
    assert msg is not None
    assert "dependsOn" in msg


def test_frontend_kind_is_case_insensitive():
    assert validate_frontend_wp_visual_contract(_fe(kind="Frontend")) is None
    assert validate_frontend_wp_visual_contract(
        _fe(kind="FRONTEND", visual_contract="", dependsOn=[])
    ) is not None


# ─── the only bypasses: explicit logged exemption + prototype ───────────────


def test_explicit_exemption_passes():
    fm = _fe(visual_contract="exempt — pure data-table change, no visual delta",
             dependsOn=[])
    assert validate_frontend_wp_visual_contract(fm) is None


def test_prototype_flag_bypasses():
    assert validate_frontend_wp_visual_contract(
        _fe(prototype=True, visual_contract="", dependsOn=[])
    ) is None


# ─── dependsOn spellings the parser must tolerate ───────────────────────────


def test_depends_as_comma_string_is_accepted():
    assert validate_frontend_wp_visual_contract(
        _fe(dependsOn="WP-009, WP-001")
    ) is None


def test_depends_absent_with_contract_is_rejected():
    msg = validate_frontend_wp_visual_contract(
        _fe(visual_contract="WP-009", dependsOn=None)
    )
    assert msg is not None
    assert "dependsOn" in msg
