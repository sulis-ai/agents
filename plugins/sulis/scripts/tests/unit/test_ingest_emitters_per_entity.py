"""Per-entity integration smoke for the ingest emitters (the Scenario-graph chain).

The generic ingest behaviour is covered by `test_instance_ingest.py`. This file
proves each entity's CLI binding end-to-end: that `sulis-emit-{entity}` ingests
the REAL authored instance (tool/step/workflow) — validating against that
entity's compiled schema in the correct domain — and persists files where
expected. Scenario has no authored instance yet, so it's exercised with a valid
hand-built fixture.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def _instances_dir(scripts_dir: Path) -> Path:
    # scripts_dir = plugins/sulis/scripts ; instances = plugins/sulis/instances
    return scripts_dir.parent / "instances" / "discover-project"


@pytest.mark.parametrize(
    "tool, src_file, domain, entity_type, min_count",
    [
        ("sulis-emit-tool", "tools.jsonld", "foundation", "tool", 6),
        ("sulis-emit-step", "steps.jsonld", "foundation", "step", 9),
        ("sulis-emit-workflow", "workflow.jsonld", "foundation", "workflow", 1),
    ],
)
def test_emits_real_authored_instance(
    tmp_path, run_tool, scripts_dir, tool, src_file, domain, entity_type, min_count
) -> None:
    src = _instances_dir(scripts_dir) / src_file
    assert src.exists(), f"authored instance missing: {src}"
    result = run_tool(
        tool, "--from-instances", str(src),
        "--base-dir", str(tmp_path / ".brain" / "instances"),
        "--repo-root", str(tmp_path),
    )
    assert result.ok, f"stderr: {result.stderr!r}"
    assert result.data["count"] == min_count
    # files land under the right domain + entity_type
    first = Path(result.data["entities"][0]["path"])
    rel = first.relative_to(tmp_path)
    assert rel.parts[:4] == (".brain", "instances", domain, entity_type)
    assert first.exists()


_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"  # no I/L/O/U


def _ulid(seed: str) -> str:
    import hashlib
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def _valid_scenario() -> dict:
    # Refs are pattern-matched (^dna:<type>:[26 Crockford]$); generate valid ULIDs.
    return {
        "id": f"dna:scenario:{_ulid('sc-pay')}",
        "name": "A signed-in user can pay with a saved card",
        "verifies": [f"dna:requirement:{_ulid('req-pay')}"],
        "exercises": f"dna:design:{_ulid('des-checkout')}",
        "journey": f"dna:workflow:{_ulid('wf-pay-journey')}",
        "state": "draft",
        "sys_status": "active",
    }


def test_emits_scenario_fixture_under_product_development(
    tmp_path, run_tool
) -> None:
    src = tmp_path / "scenarios.jsonld"
    src.write_text(json.dumps({"scenarios": [_valid_scenario()]}))
    result = run_tool(
        "sulis-emit-scenario", "--from-instances", str(src),
        "--base-dir", str(tmp_path / ".brain" / "instances"),
        "--repo-root", str(tmp_path),
    )
    assert result.ok, f"stderr: {result.stderr!r}"
    assert result.data["count"] == 1
    first = Path(result.data["entities"][0]["path"])
    rel = first.relative_to(tmp_path)
    assert rel.parts[:4] == (".brain", "instances", "product-development", "scenario")
    assert first.exists()


# --- brand-identity emitters (DR-030; phase-1b — vendored Brand + DesignSystem) ---

_BRAND_ID = f"dna:brand:{_ulid('brand-acme')}"


def _valid_brand() -> dict:
    # Brand is a thin anchor: id + name + discovery-lifecycle state + soft elements.
    return {
        "id": _BRAND_ID,
        "sys_status": "active",
        "name": "Acme",
        "state": "Articulated",
        "voice": {
            "what_it_is": "warm, precise, plain",
            "what_its_not": [{"not": "hype", "example_not": "'revolutionary, world-class'"}],
        },
    }


def _valid_design_system() -> dict:
    # DesignSystem realizes the Brand; tokens are W3C-DTCG; tiers use the DTCG enum
    # (global|alias|component — NOT the UXD-04 primitive/semantic names).
    return {
        "id": f"dna:design-system:{_ulid('ds-acme')}",
        "sys_status": "active",
        "name": "Acme DS",
        "state": "draft",
        "realizes_identity": [_BRAND_ID],
        "tokens": {"color": {"brand": {"$value": "#3366FF", "$type": "color"}}},
        "token_tiers": ["global", "alias", "component"],
        "accessibility_target": "AA",
    }


def test_emits_brand_fixture_under_brand_identity(tmp_path, run_tool) -> None:
    src = tmp_path / "brands.jsonld"
    src.write_text(json.dumps({"brands": [_valid_brand()]}))
    result = run_tool(
        "sulis-emit-brand", "--from-instances", str(src),
        "--base-dir", str(tmp_path / ".brain" / "instances"),
        "--repo-root", str(tmp_path),
    )
    assert result.ok, f"stderr: {result.stderr!r}"
    assert result.data["count"] == 1
    first = Path(result.data["entities"][0]["path"])
    rel = first.relative_to(tmp_path)
    assert rel.parts[:4] == (".brain", "instances", "brand-identity", "brand")
    assert first.exists()


def test_emits_design_system_fixture_realizing_a_brand(tmp_path, run_tool) -> None:
    src = tmp_path / "design-systems.jsonld"
    src.write_text(json.dumps({"design-systems": [_valid_design_system()]}))
    result = run_tool(
        "sulis-emit-design-system", "--from-instances", str(src),
        "--base-dir", str(tmp_path / ".brain" / "instances"),
        "--repo-root", str(tmp_path),
    )
    assert result.ok, f"stderr: {result.stderr!r}"
    assert result.data["count"] == 1
    first = Path(result.data["entities"][0]["path"])
    rel = first.relative_to(tmp_path)
    assert rel.parts[:4] == (".brain", "instances", "brand-identity", "design-system")
    assert first.exists()


def test_design_system_without_realizes_identity_is_rejected(tmp_path, run_tool) -> None:
    """The load-bearing edge: a DesignSystem with no Brand to realize must NOT persist."""
    bad = _valid_design_system()
    del bad["realizes_identity"]
    src = tmp_path / "design-systems-bad.jsonld"
    src.write_text(json.dumps({"design-systems": [bad]}))
    result = run_tool(
        "sulis-emit-design-system", "--from-instances", str(src),
        "--base-dir", str(tmp_path / ".brain" / "instances"),
        "--repo-root", str(tmp_path),
    )
    assert not result.ok, "schema must reject a DesignSystem missing realizes_identity"
    assert "realizes_identity" in (result.stdout + result.stderr)
