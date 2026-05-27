"""Unit tests for the data-contract structural check (#48, CF-05 / WP-08.5).

The symmetric partner to the visual-contract gate (#45). Where the visual gate
is per-WP (every frontend WP needs a contract — checkable from one frontmatter),
the data-contract wiring is a property of the whole WP GRAPH: "is this a
producer/consumer seam, and if so does a data contract sit between the kinds?"
So `validate_cross_kind_contract_wiring` operates on the full WP set.

Rules (only when the set spans ≥2 implementation kinds among
backend/frontend/async):
  1. A data-contract WP must exist (kind: contract, contract_type != visual).
  2. No direct dependency edge between two different implementation kinds —
     cross-kind deps route through the contract WP (CF-05 parallel-not-
     sequential). frontend dependsOn backend is the canonical violation.
"""

from __future__ import annotations

from _wpxlib import validate_cross_kind_contract_wiring


def _wp(wp_id, kind, dependsOn=None, contract_type=None, prototype=False):
    d = {"id": wp_id, "kind": kind, "dependsOn": dependsOn or []}
    if contract_type is not None:
        d["contract_type"] = contract_type
    if prototype:
        d["prototype"] = True
    return d


# ─── not a cross-kind seam → no check ───────────────────────────────────────


def test_single_kind_set_is_not_checked():
    wps = [_wp("WP-001", "backend"), _wp("WP-002", "backend", ["WP-001"])]
    assert validate_cross_kind_contract_wiring(wps) == []


def test_empty_set_passes():
    assert validate_cross_kind_contract_wiring([]) == []


def test_backend_plus_docs_is_not_a_seam():
    # docs/infra aren't implementation kinds — no producer/consumer seam.
    wps = [_wp("WP-001", "backend"), _wp("WP-002", "docs", ["WP-001"])]
    assert validate_cross_kind_contract_wiring(wps) == []


# ─── cross-kind seam: rule 1 (a data contract must exist) ───────────────────


def test_cross_kind_without_data_contract_is_flagged():
    wps = [
        _wp("WP-001", "backend"),
        _wp("WP-002", "frontend", ["WP-001"]),
    ]
    errs = validate_cross_kind_contract_wiring(wps)
    assert any("no data-contract WP" in e for e in errs)


def test_cross_kind_with_data_contract_and_clean_wiring_passes():
    wps = [
        _wp("WP-000", "contract", contract_type="data"),
        _wp("WP-001", "backend", ["WP-000"]),
        _wp("WP-002", "frontend", ["WP-000"]),
    ]
    assert validate_cross_kind_contract_wiring(wps) == []


def test_visual_contract_does_not_satisfy_the_data_contract_requirement():
    # A visual contract is not a data contract — a cross-kind data seam still
    # needs its own kind: contract (contract_type: data) WP.
    wps = [
        _wp("WP-000", "contract", contract_type="visual"),
        _wp("WP-001", "backend", ["WP-000"]),
        _wp("WP-002", "frontend", ["WP-000"]),
    ]
    errs = validate_cross_kind_contract_wiring(wps)
    assert any("no data-contract WP" in e for e in errs)


def test_contract_with_unset_type_counts_as_data_contract():
    wps = [
        _wp("WP-000", "contract"),  # no contract_type → data contract
        _wp("WP-001", "backend", ["WP-000"]),
        _wp("WP-002", "frontend", ["WP-000"]),
    ]
    assert validate_cross_kind_contract_wiring(wps) == []


# ─── cross-kind seam: rule 2 (no direct cross-impl-kind edge) ───────────────


def test_frontend_depends_directly_on_backend_is_flagged():
    wps = [
        _wp("WP-000", "contract", contract_type="data"),
        _wp("WP-001", "backend", ["WP-000"]),
        _wp("WP-002", "frontend", ["WP-000", "WP-001"]),  # direct edge to backend
    ]
    errs = validate_cross_kind_contract_wiring(wps)
    assert any("WP-002" in e and "WP-001" in e and "CF-05" in e for e in errs)


def test_async_to_backend_direct_edge_is_flagged():
    wps = [
        _wp("WP-000", "contract", contract_type="data"),
        _wp("WP-001", "backend", ["WP-000"]),
        _wp("WP-003", "async", ["WP-001"]),  # async → backend direct
    ]
    errs = validate_cross_kind_contract_wiring(wps)
    assert any("WP-003" in e and "WP-001" in e for e in errs)


def test_same_kind_edge_is_fine():
    # backend → backend is not a cross-kind edge.
    wps = [
        _wp("WP-000", "contract", contract_type="data"),
        _wp("WP-001", "backend", ["WP-000"]),
        _wp("WP-001b", "backend", ["WP-000", "WP-001"]),
        _wp("WP-002", "frontend", ["WP-000"]),
    ]
    assert validate_cross_kind_contract_wiring(wps) == []


# ─── prototype exemption ────────────────────────────────────────────────────


def test_prototype_wps_do_not_trigger_the_seam():
    wps = [
        _wp("WP-001", "backend", prototype=True),
        _wp("WP-002", "frontend", ["WP-001"], prototype=True),
    ]
    assert validate_cross_kind_contract_wiring(wps) == []


def test_depends_as_comma_string_is_handled():
    wps = [
        _wp("WP-000", "contract", contract_type="data"),
        _wp("WP-001", "backend", "WP-000"),
        _wp("WP-002", "frontend", "WP-000, WP-001"),
    ]
    errs = validate_cross_kind_contract_wiring(wps)
    assert any("WP-002" in e and "WP-001" in e for e in errs)
