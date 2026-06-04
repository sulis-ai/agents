"""Tests for `_brand_from_design.translate_design_to_brand` — the discover-brand
translator (generator TOKEN_MAP → Brand + DesignSystem records).

The load-bearing test is the **E2E**: the translator's output, written as
`brands.jsonld` / `design-systems.jsonld`, must pass the real emitters
(`sulis-emit-brand`, `sulis-emit-design-system`) and land validated in the
brain. If the translator emits something the schemas reject, that test fails —
the translator is only useful if its output is emit-valid.
"""

from __future__ import annotations

import json
import re

import pytest

from _brain_query import iter_entities
from _brand_from_design import (
    JUDGED_ELEMENTS,
    translate_design_to_brand,
)

# A generator-shaped flat TOKEN_MAP.json (the `{group: {name: value}}` form).
_FLAT_TOKENS = {
    "color": {"brand-500": "#3366FF", "ink-900": "#0A100F"},
    "font": {"sans": "Inter, system-ui, sans-serif"},
    "space": {"sm": "8px", "md": "16px"},
}


class TestTranslateShape:
    def test_produces_both_list_keys_the_emitters_expect(self) -> None:
        out = translate_design_to_brand(token_map=_FLAT_TOKENS, name="Acme")
        assert list(out) == ["brands", "design-systems"]
        assert len(out["brands"]) == 1 and len(out["design-systems"]) == 1

    def test_brand_is_partial_research_state_no_invented_identity(self) -> None:
        brand = translate_design_to_brand(token_map=_FLAT_TOKENS, name="Acme")["brands"][0]
        assert re.fullmatch(r"dna:brand:[0-9A-HJKMNP-TV-Z]{26}", brand["id"])
        assert brand["name"] == "Acme"
        assert brand["state"] == "Researched"          # discovered, not Articulated
        assert "palette" in brand["visual_identity"]    # the visual layer IS known
        # the judged identity layers are NEVER invented from a scrape
        for el in JUDGED_ELEMENTS:
            assert el not in brand, f"{el} must be left for the founder, not invented"

    def test_design_system_is_dtcg_and_links_to_the_brand(self) -> None:
        out = translate_design_to_brand(token_map=_FLAT_TOKENS, name="Acme")
        brand_id = out["brands"][0]["id"]
        ds = out["design-systems"][0]
        assert ds["state"] == "draft"
        assert ds["realizes_identity"] == [brand_id]
        # flat token wrapped into DTCG {$value,$type}
        assert ds["tokens"]["color"]["brand-500"] == {"$value": "#3366FF", "$type": "color"}
        assert ds["tokens"]["font"]["sans"]["$type"] == "fontFamily"

    def test_already_dtcg_tokens_pass_through(self) -> None:
        dtcg = {"color": {"brand": {"$value": "#3366FF", "$type": "color"}}}
        ds = translate_design_to_brand(token_map=dtcg, name="X")["design-systems"][0]
        assert ds["tokens"]["color"]["brand"] == {"$value": "#3366FF", "$type": "color"}

    def test_deterministic_ids_same_name(self) -> None:
        a = translate_design_to_brand(token_map=_FLAT_TOKENS, name="Acme")
        b = translate_design_to_brand(token_map=_FLAT_TOKENS, name="Acme")
        assert a["brands"][0]["id"] == b["brands"][0]["id"]
        assert a["design-systems"][0]["id"] == b["design-systems"][0]["id"]

    def test_tenant_threads_through_when_given(self) -> None:
        t = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"
        out = translate_design_to_brand(token_map=_FLAT_TOKENS, name="Acme", tenant=t)
        assert out["brands"][0]["belongs_to_tenant"] == t
        assert out["design-systems"][0]["belongs_to_tenant"] == t


class TestEmitValidEndToEnd:
    """The proof: translator output passes the REAL emitters into the brain."""

    def test_translator_output_emits_into_the_brain(self, tmp_path, run_tool) -> None:
        out = translate_design_to_brand(token_map=_FLAT_TOKENS, name="Acme")
        base = tmp_path / ".brain" / "instances"

        brands_src = tmp_path / "brands.jsonld"
        brands_src.write_text(json.dumps({"brands": out["brands"]}))
        ds_src = tmp_path / "design-systems.jsonld"
        ds_src.write_text(json.dumps({"design-systems": out["design-systems"]}))

        r1 = run_tool("sulis-emit-brand", "--from-instances", str(brands_src),
                      "--base-dir", str(base))
        assert r1.ok, f"brand emit rejected the translator output: {r1.stderr}"
        r2 = run_tool("sulis-emit-design-system", "--from-instances", str(ds_src),
                      "--base-dir", str(base))
        assert r2.ok, f"design-system emit rejected the translator output: {r2.stderr}"

        brands = list(iter_entities(base, domain="brand-identity", entity_type="brand"))
        dss = list(iter_entities(base, domain="brand-identity", entity_type="design-system"))
        assert len(brands) == 1 and len(dss) == 1
        # the link survives the round-trip: the filed DS realizes the filed Brand
        assert dss[0]["realizes_identity"] == [brands[0]["id"]]
