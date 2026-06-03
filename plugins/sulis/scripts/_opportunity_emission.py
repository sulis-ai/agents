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

from _entity_evolve import evolve_entity
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

    opportunity: dict = {
        "id": _opportunity_id_for_srd(srd_path),
        "for_product": for_product,
        "job_statement": summary,
        "state": "hypothesis",
        "sys_status": "active",
    }
    # Optional: capture the SRD title as `evidence` if frontmatter has it.
    title = frontmatter.get("title") if isinstance(frontmatter, dict) else None
    if isinstance(title, str) and title.strip():
        opportunity["impact"] = title.strip()

    return [opportunity]


def emit_opportunity_from_srd(
    srd_path: Path,
    repo: EntityRepository,
    *,
    generated_by: str | None = None,
) -> list[dict]:
    """Emit the Opportunity composed from ``srd_path`` as a *living* entity.

    Opportunity is a ``prov:Entity`` living type (ADR-002/ADR-003): each emit
    delegates to the shared bitemporal ``evolve_entity`` helper (WP-009) rather
    than a plain ``repo.save`` — first emit opens a window, a changed re-emit
    closes the prior and opens a new one, a byte-identical re-emit is a no-op.
    The window logic is the helper's (EP-03), not re-implemented here.

    Args:
        generated_by: the producing LifecycleRun ref
            (``dna:lifecyclerun:<ulid>``) from the emit context. When supplied,
            the new window carries the conditional ``wasGeneratedBy`` PROV edge
            (Opportunity is ``prov:Entity`` — the edge is well-typed). ``None``
            moves the window without an edge.

    Emission stays best-effort: a fault at the persistence point is swallowed so
    the host operation never fails on an emit failure.
    """
    srd_text = Path(srd_path).read_text(encoding="utf-8")
    opportunities = compose_opportunity_from_srd(
        srd_text, srd_path=str(srd_path)
    )
    for opp in opportunities:
        try:
            evolve_entity(
                repo=repo,
                entity_type="opportunity",
                entity_id=opp["id"],
                new_fields=opp,
                generated_by=generated_by,
            )
        except Exception:
            # Best-effort emit — never raise into the host operation.
            continue
    return opportunities
