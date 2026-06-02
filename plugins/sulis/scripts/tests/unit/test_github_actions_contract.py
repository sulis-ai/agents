"""Conformance verification for WP-006 / WP-007 (platform-contract-standard).

WP-006 produced the n=1 dogfood instance — the GitHub Actions Platform Contract
at ``plugins/sulis/references/platform-contracts/github-actions.md``. These
tests assert it conforms to the **claim-entry schema** (the A-1 / A-4 / A-6
invariants), using the shared validator in ``_platform_contract.py`` (so the
rubric's P-PLAT phase and these tests share one definition — EP-02 REFACTOR).

WP-007 conformance ≠ WP-008 grounding: this file checks the *schema shape*
(fields present, inferred-vs-source rules). WP-008 (``test_github_actions_
dogfood.py``) checks the *grounding is genuine* (URLs resolve, the "new"
qualifier is preserved, probes ran or are justifiably deferred).

Stdlib + pyyaml + pytest. Network checks are best-effort (OAQ-2: authoring-time
hard, CI soft) — a network failure skips, never reds the build.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

import pytest

from _platform_contract import parse_contract_claims, validate_claim_entry

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_CONTRACT = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "references"
    / "platform-contracts"
    / "github-actions.md"
)


def _claims() -> list[dict]:
    assert _CONTRACT.is_file(), f"missing contract {_CONTRACT}"
    claims = parse_contract_claims(_CONTRACT)
    assert claims, "github-actions.md must carry a machine-readable claims block"
    return claims


def test_contract_has_three_rules() -> None:
    """The dogfood contract carries the three grounded rules (Proof leg 3)."""
    assert len(_claims()) == 3, "Expected three claim entries in the contract."


def test_contract_conformance() -> None:
    """Every claim entry satisfies the claim-entry schema invariants
    (A-1 / A-4 / A-6 — the WP-006 Red assertion)."""
    violations: dict[int, list[str]] = {}
    for i, claim in enumerate(_claims()):
        v = validate_claim_entry(claim)
        if v:
            violations[i] = v
    assert not violations, f"Claim-entry schema violations: {violations}"


def test_harness_run_recorded() -> None:
    """The contract front matter carries a non-empty harness-run reference
    (A-8 / NFR-007 — provenance P-PLAT check 10.02)."""
    text = _CONTRACT.read_text(encoding="utf-8")
    assert "harness-run:" in text, "Contract front matter must carry `harness-run:`."
    # The run id must be a non-placeholder value (a ULID-shaped token).
    import re

    m = re.search(r"harness-run:\s*([0-9A-HJKMNP-TV-Z]{26})", text)
    assert m, "harness-run: must be a non-empty ULID-shaped run reference."


def test_source_urls_resolve() -> None:
    """Every source URL on a non-inferred claim is a docs.github.com HTTPS URL
    (hard) and resolves live (soft — skipped on network failure, OAQ-2)."""
    sourced = [c for c in _claims() if c.get("inferred") is False]
    assert sourced, "Expected at least one source-bound claim."

    for claim in sourced:
        url = claim.get("source", "")
        # Structural assertion — hard.
        assert url.startswith("https://docs.github.com/"), (
            f"source URL must be an HTTPS docs.github.com URL; got {url!r}"
        )

    # Live resolution — soft. A network failure must not red the build.
    for claim in sourced:
        url = claim["source"]
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "sulis-ci"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                assert resp.status < 400, f"{url} returned {resp.status}"
        except (urllib.error.URLError, OSError, ValueError) as exc:
            pytest.skip(f"network unavailable for live URL check ({url}): {exc}")
