"""SRD → Opportunity-entity transformation.

Fifth worked entity emission. The Opportunity is the headwater of the
product-development spine — the validated problem worth solving — and it
sits below Product (per the L13/JT-2 reframe).

Source format — a `Software Requirements Document` markdown file. The
emitter extracts:

  - **`job_statement`** from the first `## Summary` (or `## Introduction`,
    `## 1. Introduction`) section's prose. Cleaned, joined to a single line.
  - **`for_product`** from frontmatter `for_product: <product-slug>` if
    present; otherwise from a deterministic synthetic Product ID derived
    from the SRD path (replaceable when the SRD gets explicit product
    wiring).

ID strategy: deterministic from sha256("opportunity-from-srd:" + srd_path),
**matching the synthetic-Opportunity-source ULID** that
`_requirement_emission.py` produces for the same SRD. So:

  - Requirement emitter produces FRs that reference `dna:opportunity:X`
    (synthetic at first, real now).
  - Opportunity emitter produces the same `dna:opportunity:X` for the
    same SRD path.
  - The graph self-resolves — same SRD, same Opportunity, same id.

This closes the synthetic-placeholder loop CH-01KSWQ opened.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Final

from _entity_repository import EntityRepository
from _wpxlib import parse_frontmatter


_CROCKFORD_ALPHABET: Final[str] = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _deterministic_ulid_from(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    n = int.from_bytes(digest[:17], "big") & ((1 << 130) - 1)
    chars: list[str] = []
    for _ in range(26):
        chars.append(_CROCKFORD_ALPHABET[n & 0x1F])
        n >>= 5
    return "".join(reversed(chars))


def _opportunity_id_for_srd(srd_path: str) -> str:
    """Match the algorithm `_requirement_emission` uses for its synthetic
    Opportunity source — they MUST stay in lockstep.

    `_requirement_emission` derives it as:
      _deterministic_ulid_from(f"opportunity-from-srd:{srd_path}")
    """
    return f"dna:opportunity:{_deterministic_ulid_from(f'opportunity-from-srd:{srd_path}')}"


def _product_id_from_name(product_name: str, tenant_ref: str = "unbound") -> str:
    """Match the algorithm `_product_emission` uses — keep in lockstep."""
    return "dna:product:" + _deterministic_ulid_from(
        f"product-name:{product_name.strip()}:tenant:{tenant_ref}"
    )


# `## Summary`, `## Introduction`, `## 1. Introduction` — case-insensitive,
# trailing word boundaries.
_SUMMARY_HEADING_RE: Final = re.compile(
    r"^##\s+(?:\d+\.\s+)?(?:summary|introduction|overview|purpose)\s*$",
    re.MULTILINE | re.IGNORECASE,
)
_NEXT_HEADING_RE: Final = re.compile(r"^#{2,4}\s+\S", re.MULTILINE)


def _extract_summary(body: str) -> str | None:
    """Find the first `## Summary` (or synonym) section and return its
    flattened prose."""
    m = _SUMMARY_HEADING_RE.search(body)
    if m is None:
        return None
    start = m.end()
    # End at the next H2-H4 heading
    nxt = _NEXT_HEADING_RE.search(body, start)
    end = nxt.start() if nxt else len(body)
    section_body = body[start:end].strip()
    if not section_body:
        return None
    return re.sub(r"\s+", " ", section_body).strip()


def _opportunity_dict(
    *,
    opportunity_id: str,
    for_product: str,
    job_statement: str,
    state: str,
    evidence: list[str] | None = None,
    impact: str | None = None,
) -> dict:
    """Single home for the Opportunity field/default shape.

    Both compose paths (from-SRD, from-idea) assemble the same five required
    keys (`id`, `for_product`, `job_statement`, `state`, `sys_status`) plus
    the optional `evidence`/`impact`. Centralising the shape here keeps the
    two paths byte-identical for the same fields and keeps the
    `unevaluatedProperties:false` discipline (optionals omitted, never null)
    in one place. `job_statement` is flattened to a single line.
    """
    opportunity: dict = {
        "id": opportunity_id,
        "for_product": for_product,
        "job_statement": re.sub(r"\s+", " ", job_statement).strip(),
        "state": state,
        "sys_status": "active",
    }
    if evidence is not None:
        opportunity["evidence"] = evidence
    if impact is not None:
        opportunity["impact"] = impact
    return opportunity


def compose_opportunity_from_srd(
    srd_text: str,
    *,
    srd_path: str,
) -> list[dict]:
    """Pure transformation: SRD text → list of one Opportunity dict.

    Returns `[]` if the SRD has no detectable summary section (caller
    surfaces that — no headwater means no opportunity to emit).
    """
    frontmatter, body = parse_frontmatter(srd_text)
    summary = _extract_summary(body)
    if summary is None or not summary.strip():
        return []

    # for_product: explicit frontmatter wins; else synthetic from srd_path.
    product_slug = frontmatter.get("for_product")
    if isinstance(product_slug, str) and product_slug.strip():
        # Caller declared which Product this SRD targets. Use the same
        # algorithm `_product_emission` does. tenant_ref is unknown here
        # (could be looked up via sibling tenant.yaml), default to "unbound"
        # which is fine for cross-emitter ID coordination — emitted
        # alongside a real Product with the same tenant_ref, ids match.
        for_product = _product_id_from_name(product_slug.strip())
    else:
        # Synthetic — deterministic from srd_path. Replaceable when SRD
        # gains explicit `for_product` frontmatter.
        for_product = "dna:product:" + _deterministic_ulid_from(
            f"product-from-srd:{srd_path}"
        )

    # Optional: capture the SRD title as `impact` if frontmatter has it.
    title = frontmatter.get("title") if isinstance(frontmatter, dict) else None
    impact = title.strip() if isinstance(title, str) and title.strip() else None

    opportunity = _opportunity_dict(
        opportunity_id=_opportunity_id_for_srd(srd_path),
        for_product=for_product,
        job_statement=summary,
        state="hypothesis",
        impact=impact,
    )
    return [opportunity]


def compose_opportunity_from_idea(
    *,
    job_statement: str,
    for_product: str,
    seed: str,
    state: str = "hypothesis",
    evidence: str | None = None,
    impact: str | None = None,
) -> dict:
    """Pure transform: idea fields → Opportunity entity dict. No I/O.

    The single-idea capture sibling to `compose_opportunity_from_srd`
    (ADR-005): capture has no source document — just a why-string typed in
    conversation — so the SRD parser would have nothing to parse. This feeds
    the same ID-derivation and dict-shape discipline a different front end.

    ID = ``dna:opportunity:`` + ``_deterministic_ulid_from`` over the
    ``opportunity-from-idea:`` namespace, distinct from the from-SRD path's
    ``opportunity-from-srd:`` namespace so the two never collide on the same
    string (NFR-04: same seed ⇒ same id ⇒ overwrite-in-place, no duplicate).

    Optional fields are omitted from the dict when ``None`` (not set to
    ``null``), keeping ``unevaluatedProperties:false`` clean (ADR-005). The
    schema types ``evidence`` as an array of strings, so a provided string is
    wrapped to a single-element list; ``impact`` is a plain string.
    """
    return _opportunity_dict(
        opportunity_id="dna:opportunity:"
        + _deterministic_ulid_from(f"opportunity-from-idea:{seed}"),
        for_product=for_product,
        job_statement=job_statement,
        state=state,
        # Schema types `evidence` as an array of strings; wrap the single
        # captured string.
        evidence=[evidence] if evidence is not None else None,
        impact=impact,
    )


def emit_opportunity_from_srd(
    srd_path: Path,
    repo: EntityRepository,
) -> list[dict]:
    srd_text = Path(srd_path).read_text(encoding="utf-8")
    opportunities = compose_opportunity_from_srd(
        srd_text, srd_path=str(srd_path)
    )
    for opp in opportunities:
        repo.save("opportunity", opp)
    return opportunities
