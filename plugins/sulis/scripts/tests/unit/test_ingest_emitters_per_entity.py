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
