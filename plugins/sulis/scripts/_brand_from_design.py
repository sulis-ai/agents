"""Translate a design-system generator's output into authored Brand +
DesignSystem records — the load-bearing bridge of `discover-brand`.

The URL→design generator (the `design-system` skill) extracts the *visual*
layer of a brand: a flat `TOKEN_MAP.json` (colours, type, spacing) + a
`DESIGN.md`. This module turns that into the two brain records the emitters
(`sulis-emit-brand`, `sulis-emit-design-system`) ingest:

  - a **DesignSystem** — the full W3C-DTCG token set + `realizes_identity →`
    the Brand (state ``draft``: a scrape is a starting point, not accepted).
  - a **Brand** — its `visual_identity` populated from the tokens, at state
    ``Researched`` (discovered, not yet Articulated).

The honesty line (matches the founder-owned-identity carve-out): a URL scrape
can know the *visual* identity, but NOT the *judged* identity — voice, values,
positioning. Those soft elements are **left absent**, never invented, for the
founder (or the ux-designer's establish-the-language step) to articulate. So
`discover-brand` produces a complete design system + a deliberately-partial
brand, with the judged layer flagged as the founder's to fill.
"""

from __future__ import annotations

import hashlib
from typing import Any, Final

_CROCKFORD: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Top-level token-group name → DTCG `$type`. The generator's TOKEN_MAP.json
# groups leaves under a coarse category; map each to its DTCG type so the
# emitted tokens validate as real DTCG. Unknown groups fall through to None
# (a bare `$value`, still valid DTCG).
_GROUP_TO_DTCG_TYPE: Final[dict[str, str]] = {
    "color": "color",
    "colour": "color",
    "colors": "color",
    "font": "fontFamily",
    "fontFamily": "fontFamily",
    "fontFamilies": "fontFamily",
    "typography": "fontFamily",
    "fontSize": "dimension",
    "fontSizes": "dimension",
    "space": "dimension",
    "spacing": "dimension",
    "size": "dimension",
    "sizes": "dimension",
    "radius": "dimension",
    "radii": "dimension",
    "borderRadius": "dimension",
    "shadow": "shadow",
    "shadows": "shadow",
    "duration": "duration",
    "fontWeight": "fontWeight",
    "fontWeights": "fontWeight",
}


def _ulid(seed: str) -> str:
    """Deterministic Crockford-base32 ULID body from a seed (same scheme the
    emitters use). Same seed → same id, so re-running discover-brand on the
    same brand is idempotent rather than duplicating."""
    n = int.from_bytes(hashlib.sha256(seed.encode()).digest()[:17], "big") & ((1 << 130) - 1)
    out: list[str] = []
    for _ in range(26):
        out.append(_CROCKFORD[n & 0x1F])
        n >>= 5
    return "".join(reversed(out))


def _is_dtcg_leaf(v: Any) -> bool:
    return isinstance(v, dict) and "$value" in v


def _to_dtcg(token_map: dict, *, _group: str | None = None) -> dict:
    """Convert a generator TOKEN_MAP.json into W3C-DTCG tokens.

    The generator emits a flat-ish `{group: {name: value}}` map (e.g.
    `{"color": {"brand-500": "#3366FF"}}`). DTCG wants each leaf as
    `{"$value": ..., "$type": ...}`. Already-DTCG leaves pass through. The
    `$type` is inferred from the *top-level* group name; nested groups inherit
    it. Non-dict, non-leaf values (a bare string at the group root) are wrapped
    using the current group's type.
    """
    out: dict = {}
    for key, val in token_map.items():
        group = _group if _group is not None else key
        if _is_dtcg_leaf(val):
            out[key] = val  # already DTCG — pass through untouched
        elif isinstance(val, dict):
            out[key] = _to_dtcg(val, _group=group)
        else:
            leaf: dict = {"$value": val}
            dtcg_type = _GROUP_TO_DTCG_TYPE.get(group)
            if dtcg_type:
                leaf["$type"] = dtcg_type
            out[key] = leaf
    return out


def _flatten_values(token_map: dict, group: str) -> list:
    """Collect the leaf values under a top-level group (for the brand's
    visual_identity summary). Handles both flat and DTCG-wrapped leaves."""
    grp = token_map.get(group)
    if not isinstance(grp, dict):
        return []
    vals: list = []
    for v in grp.values():
        if _is_dtcg_leaf(v):
            vals.append(v["$value"])
        elif isinstance(v, dict):
            vals.extend(x["$value"] if _is_dtcg_leaf(x) else x for x in v.values())
        else:
            vals.append(v)
    return vals


def _visual_identity_from_tokens(token_map: dict) -> dict:
    """Summarise the scraped tokens into the Brand's visual_identity — the one
    brand layer a scrape can legitimately know. Empty groups are omitted."""
    vi: dict = {}
    palette = []
    for g in ("color", "colour", "colors"):
        palette.extend(_flatten_values(token_map, g))
    if palette:
        vi["palette"] = palette
    type_families = []
    for g in ("font", "fontFamily", "fontFamilies", "typography"):
        type_families.extend(_flatten_values(token_map, g))
    if type_families:
        vi["typography"] = type_families
    vi["source"] = "discover-brand (extracted from the generator's token map)"
    return vi


# The judged identity layers a URL scrape MUST NOT invent — left absent on the
# Brand for the founder / ux-designer to articulate (state stays Researched
# until then).
JUDGED_ELEMENTS: Final[tuple[str, ...]] = (
    "voice", "values", "positioning", "audience", "offering", "lexicon", "claims",
)


def translate_design_to_brand(
    *,
    token_map: dict,
    name: str,
    design_md: str = "",
    tenant: str = "",
    seed: str = "",
) -> dict:
    """Build the `{brands, design-systems}` payload the emitters ingest.

    Returns a dict with two list keys (``brands`` and ``design-systems``) — the
    exact shape `sulis-emit-brand --from-instances` / `sulis-emit-design-system`
    expect. The Brand is deliberately partial (visual only, judged layers
    absent); the DesignSystem is complete and links back to the Brand.
    """
    seed = seed or name
    brand_id = f"dna:brand:{_ulid('brand:' + seed)}"
    ds_id = f"dna:design-system:{_ulid('design-system:' + seed)}"

    brand: dict = {
        "id": brand_id,
        "sys_status": "active",
        "name": name,
        "state": "Researched",  # discovered from a scrape; not yet Articulated
        "visual_identity": _visual_identity_from_tokens(token_map),
    }
    if tenant:
        brand["belongs_to_tenant"] = tenant
    # JUDGED_ELEMENTS deliberately omitted — never invented from a scrape.

    design_system: dict = {
        "id": ds_id,
        "sys_status": "active",
        "name": f"{name} Design System",
        "state": "draft",
        "realizes_identity": [brand_id],
        "tokens": _to_dtcg(token_map),
        "token_tiers": ["global", "alias", "component"],
    }
    if tenant:
        design_system["belongs_to_tenant"] = tenant

    return {"brands": [brand], "design-systems": [design_system]}
