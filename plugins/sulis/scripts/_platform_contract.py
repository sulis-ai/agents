"""Shared helpers for Platform Contract conformance + P-PLAT detection.

This is the mechanical core of the platform-contract methodology:

  * ``parse_contract_claims`` — pull the machine-readable claim-entry block out
    of a Platform Contract markdown file.
  * ``validate_claim_entry`` — assert one claim against the claim-entry schema
    defined in ``PLATFORM_CONTRACT_STANDARD.md`` (the A-1 / A-4 / A-6 invariants
    that the rubric's P-PLAT checks 10.03..10.06 enforce).
  * ``pplat_scan_wp_set`` — the deterministic P-PLAT check 10.01 + the
    grandfather sub-phase: a WP set with a gated write/deploy third-party touch
    must reference a stored Platform Contract, unless the change predates the
    merge constant.

Keeping the enforcement deterministic (not prose-only) is what makes P-PLAT a
real gate rather than a convention. The decompose-validation rubric documents
the phase for a human/agent reader; this module is the executable leg the
fixture tests exercise.

Stdlib + pyyaml. Python 3.11-safe.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

_YAML_BLOCK = re.compile(r"```yaml\n(.*?)```", re.DOTALL)


def parse_contract_claims(contract_path: str | Path) -> list[dict]:
    """Return the list of claim entries from a Platform Contract's first
    machine-readable ```yaml``` block. Empty list if none present."""
    text = Path(contract_path).read_text(encoding="utf-8")
    m = _YAML_BLOCK.search(text)
    if not m:
        return []
    data = yaml.safe_load(m.group(1))
    return data if isinstance(data, list) else []


def validate_claim_entry(claim: dict) -> list[str]:
    """Return the list of claim-entry-schema violations for one claim.

    An empty list means the claim is conformant. Mirrors the rubric's P-PLAT
    MUST checks 10.03..10.06:

      * 10.03 / A-1 — ``inferred: false`` ⇒ source + quote + retrieval-date.
      * 10.04 / A-4 — ``inferred: true`` ⇒ NO ``source`` (an inference is ours,
        not the platform's; it must not masquerade as source-backed).
      * 10.05 / A-6 — ``load_bearing: true`` ⇒ probe + probe-result (or a
        justified ``deferred:<id>`` probe-result).
      * 10.06 — ``probe-result: confirmed`` ⇒ non-empty probe-evidence.
    """
    v: list[str] = []
    inferred = claim.get("inferred")
    if inferred is None:
        v.append("missing required key `inferred`")

    if inferred is False:
        for key in ("source", "quote", "retrieval-date"):
            if not claim.get(key):
                v.append(f"inferred:false claim missing `{key}` (A-1)")

    if inferred is True:
        if claim.get("source"):
            v.append("inferred:true claim must not carry a `source` (A-4)")

    probe_result = claim.get("probe-result", "")
    if claim.get("load_bearing") is True:
        if not claim.get("probe") or not probe_result:
            v.append("load_bearing:true claim needs `probe` + `probe-result` (A-6)")

    if probe_result == "confirmed" and not claim.get("probe-evidence"):
        v.append("probe-result:confirmed requires non-empty `probe-evidence`")

    return v


def pplat_scan_wp_set(
    wp_frontmatters,
    contracts_dir: str | Path,
    started_at: str | None = None,
    required_from: str = "",
) -> dict:
    """Deterministic P-PLAT check 10.01 + grandfather sub-phase.

    ``wp_frontmatters`` — iterable of WP-frontmatter dicts (each may carry
    ``platform:`` / ``touch-class:``). ``contracts_dir`` — the
    ``platform-contracts/`` directory. ``started_at`` / ``required_from`` —
    ISO-8601 strings for the grandfather comparison (mirrors P-VER).

    Returns ``{"verdict": ..., "missing": [...]}`` where verdict is one of
    ``"PASS"``, ``"PASS — grandfathered"``, ``"GAPS_FOUND"``. A gated
    write/deploy touch (``touch-class`` in {write, deploy} with a ``platform``
    slug) whose ``platform-contracts/<slug>.md`` does not exist collapses the
    verdict to GAPS_FOUND.
    """
    contracts = Path(contracts_dir)

    # Grandfather: a change started before the merge constant passes without a
    # contract (NFR-005). An empty constant runs all checks (the dogfood window).
    if required_from and started_at and started_at < required_from:
        return {"verdict": "PASS — grandfathered", "missing": []}

    missing: list[str] = []
    for fm in wp_frontmatters:
        touch_class = str(fm.get("touch-class") or "").strip().lower()
        platform = str(fm.get("platform") or "").strip().lower()
        if touch_class in ("write", "deploy") and platform:
            if not (contracts / f"{platform}.md").is_file():
                missing.append(platform)

    return {
        "verdict": "GAPS_FOUND" if missing else "PASS",
        "missing": sorted(set(missing)),
    }
