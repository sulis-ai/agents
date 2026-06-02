"""n=1 dogfood acceptance for WP-008 (platform-contract-standard).

WP-007 checks the contract's *schema shape*. This file (WP-008) checks the
*grounding is genuine* — the UC-005 MUST (TDD lines 188-191):

    The GitHub Actions contract MUST NOT ship with any of the three rules
    uncited, nor with a load-bearing rule unprobed-and-not-justifiably-deferred.
    The three URLs and quotes MUST be re-retrieved at authoring — the handoff
    is not the source.

``test_no_rule_uncited`` is the mechanical form of that MUST. The per-rule
tests assert each of the three rules is cited / probed / deferred as the design
specified, and the meaning-check guards the bot-token "*new* workflow run"
qualifier (MUC-002 / A-3).

Network checks are best-effort (OAQ-2: authoring-time hard, CI soft).

Stdlib + pyyaml + pytest. Python 3.11-safe.
"""

from __future__ import annotations

import urllib.error
import urllib.request
from pathlib import Path

import pytest

from _platform_contract import parse_contract_claims, validate_claim_entry

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
    claims = parse_contract_claims(_CONTRACT)
    assert claims, "github-actions.md must carry a machine-readable claims block"
    return claims


def _rule(substr: str) -> dict:
    for c in _claims():
        if substr.lower() in str(c.get("claim", "")).lower():
            return c
    raise AssertionError(f"No claim matching {substr!r} in the contract.")


def _resolves(url: str) -> None:
    """Soft live-resolution check — skip on any network failure (OAQ-2)."""
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "sulis-ci"})
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            assert resp.status < 400, f"{url} returned {resp.status}"
    except (urllib.error.URLError, OSError, ValueError) as exc:
        pytest.skip(f"network unavailable for live URL check ({url}): {exc}")


def test_reusable_workflow_rule_cited_to_real_github_url() -> None:
    """The reusable-workflow rule is cited to a resolving docs.github.com URL,
    probe-confirmed with non-empty evidence."""
    rule = _rule("reusable workflows")
    assert rule.get("inferred") is False
    assert rule.get("source", "").startswith("https://docs.github.com/")
    assert rule.get("probe-result") == "confirmed"
    assert rule.get("probe-evidence"), "confirmed probe needs evidence"
    assert not validate_claim_entry(rule), validate_claim_entry(rule)
    _resolves(rule["source"])


def test_bot_token_rule_cited_and_probed() -> None:
    """The bot-token rule is cited + confirmed, AND the meaning-check holds:
    the verbatim quote preserves the '*new* workflow run' qualifier (MUC-002 /
    A-3) — not just any token-trigger statement."""
    rule = _rule("GITHUB_TOKEN")
    assert rule.get("inferred") is False
    assert rule.get("source", "").startswith("https://docs.github.com/")
    assert rule.get("probe-result") == "confirmed"
    assert rule.get("probe-evidence"), "confirmed probe needs evidence"
    # Meaning-check: the "new workflow run" semantics must be present in the
    # quote, guarding against an over-general "token can't trigger anything".
    quote = str(rule.get("quote", "")).lower()
    assert "new workflow run" in quote, (
        "The bot-token quote must preserve the '*new* workflow run' qualifier "
        "(MUC-002 / A-3) — without 'new' the claim over-generalises."
    )
    _resolves(rule["source"])


def test_branch_protection_rule_cited_and_deferred() -> None:
    """The branch-protection rule is an honest inference (no fabricated source)
    with its probe justifiably deferred to the canonical need id."""
    rule = _rule("branch protection")
    assert rule.get("inferred") is True, (
        "Branch-protection could not be re-grounded at authoring; it must be a "
        "flagged inference, not a source-bound fact."
    )
    assert not rule.get("source"), "An inference must not carry a source (A-4)."
    assert (
        rule.get("probe-result")
        == "deferred:paid-private-repo-for-branch-protection-probe"
    ), rule.get("probe-result")


def test_no_rule_uncited() -> None:
    """The UC-005 MUST, mechanically: every rule is either source-cited
    (inferred:false ⇒ source) or a flagged inference (inferred:true ⇒ no
    source), and no load-bearing rule is unprobed-and-not-deferred."""
    for claim in _claims():
        violations = validate_claim_entry(claim)
        assert not violations, (
            f"Rule {claim.get('claim')!r} violates the cite/probe MUST: "
            f"{violations}"
        )
