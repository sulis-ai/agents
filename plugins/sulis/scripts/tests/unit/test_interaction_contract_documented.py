"""Structural verification for WP-003 (interaction-flow-gate change).

WP-003 is a **documentation-only, SHOULD-strength** amendment (ADR-002,
Phase 1). It gives ``contract_type: interaction`` a defined home in the
cross-kind decomposition doctrine — sibling to the existing visual contract —
across two standards files:

  * ``plugins/sulis/references/standards/WORK_PACKAGE_STANDARD.md`` (WP-08.5,
    the "User-facing seams" callout region), and
  * ``plugins/sulis/references/standards/CONTRACT_FIRST_STANDARD.md`` (near the
    CF-05/CF-07 cross-kind requirements).

The amendment is **prose, not code**, so the failing-first (RED) cycle pins the
documented invariants on the live files as structural assertions — exactly as
the sibling ``test_platform_contract_standard.py`` does for its standard.

Per the WP Contract (`Definition of Done > Red`), the amended files MUST:

  1. ``WORK_PACKAGE_STANDARD.md`` — within the WP-08.5 region — contain
     ``contract_type: interaction`` together with the strings ``exercised`` and
     ``SHOULD`` (the SHOULD-strength exercised-flow done-gate guidance).
  2. ``WORK_PACKAGE_STANDARD.md`` — make the Phase-1-SHOULD / Phase-2-MUST
     boundary explicit (so a reader cannot mistake this for the Phase-2 flip).
  3. ``CONTRACT_FIRST_STANDARD.md`` — reference the ``interaction`` contract
     type (the third contract flavour, alongside data + visual).
  4. **Neither** file state the interaction contract as ``MUST`` for
     founder-facing work — the guard against accidentally landing Phase 2.

Stdlib + pytest only, Python 3.11-safe. Resolves paths relative to this test
file so the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo-root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_STANDARDS_DIR = _REPO_ROOT / "plugins" / "sulis" / "references" / "standards"
_WP_STANDARD = _STANDARDS_DIR / "WORK_PACKAGE_STANDARD.md"
_CF_STANDARD = _STANDARDS_DIR / "CONTRACT_FIRST_STANDARD.md"


def _read(path: Path) -> str:
    if not path.exists():
        pytest.fail(
            f"{path.name} missing at {path}. WP-003 amends this file; the "
            "structural assertions cannot run until it exists."
        )
    return path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def wp_standard_text() -> str:
    return _read(_WP_STANDARD)


@pytest.fixture(scope="module")
def cf_standard_text() -> str:
    return _read(_CF_STANDARD)


@pytest.fixture(scope="module")
def wp_0805_region(wp_standard_text: str) -> str:
    """The WP-08.5 region — from the ``### WP-08.5`` heading up to the next
    ``### WP-`` sibling heading. The interaction-contract guidance is a sibling
    of the visual-contract callout, so it MUST live inside this region (not
    merely somewhere in the file)."""
    match = re.search(
        r"###\s+WP-08\.5\b.*?(?=\n###\s+WP-\d|\Z)",
        wp_standard_text,
        re.DOTALL,
    )
    assert match, (
        "Could not locate the `### WP-08.5` region in WORK_PACKAGE_STANDARD.md "
        "— the interaction-contract guidance must live there, sibling to the "
        "visual-contract callout."
    )
    return match.group(0)


def test_wp0805_documents_interaction_contract_type(wp_0805_region: str) -> None:
    """The WP-08.5 region names the ``contract_type: interaction`` child — the
    defined home for the interaction contract, sibling to the visual one."""
    assert "contract_type: interaction" in wp_0805_region, (
        "Expected `contract_type: interaction` inside the WP-08.5 region "
        "(the interaction contract's defined home, sibling to the visual "
        "contract callout)."
    )


def test_wp0805_states_exercised_flow_done_gate(wp_0805_region: str) -> None:
    """The done-gate is the exercised-flow predicate — the region must say the
    flow is ``exercised`` (end-to-end over stubs)."""
    assert re.search(r"\bexercised\b", wp_0805_region, re.IGNORECASE), (
        "Expected the WP-08.5 region to describe the exercised-flow done-gate "
        "(the string `exercised`)."
    )


def test_wp0805_interaction_strength_is_should(wp_0805_region: str) -> None:
    """Phase 1 states the interaction-contract guidance at SHOULD strength."""
    assert "SHOULD" in wp_0805_region, (
        "Expected `SHOULD` in the WP-08.5 region — Phase 1 interaction-contract "
        "guidance is SHOULD strength, not MUST."
    )


def test_wp0805_states_phase_boundary(wp_0805_region: str) -> None:
    """The Phase-1-SHOULD / Phase-2-MUST boundary is made explicit so a reader
    cannot mistake this for the Phase-2 flip."""
    assert re.search(r"Phase\s*2", wp_0805_region, re.IGNORECASE), (
        "Expected the WP-08.5 region to name `Phase 2` — the MUST flip "
        "(mandatory for all founder-facing work) is explicitly deferred."
    )


def test_cf_standard_references_interaction_contract(cf_standard_text: str) -> None:
    """CONTRACT_FIRST_STANDARD.md references the `interaction` contract type as
    a third contract flavour alongside data + visual."""
    assert "contract_type: interaction" in cf_standard_text or re.search(
        r"\binteraction\b\s+contract", cf_standard_text, re.IGNORECASE
    ), (
        "Expected CONTRACT_FIRST_STANDARD.md to reference the `interaction` "
        "contract type (the third contract flavour, alongside data + visual)."
    )


def test_cf_standard_interaction_is_exercised_over_stubs(
    cf_standard_text: str,
) -> None:
    """The interaction contract's conformance is 'the flow was exercised
    end-to-end over stubs', gated at done."""
    # Find the sentence/region mentioning the interaction contract, then assert
    # the exercised-over-stubs conformance idea is present nearby in the file.
    assert re.search(r"\bexercised\b", cf_standard_text, re.IGNORECASE), (
        "Expected CONTRACT_FIRST_STANDARD.md to describe the interaction "
        "contract's conformance as the flow being `exercised` over stubs."
    )


# --- Phase-2 guard: neither file may land the MUST flip in Phase 1 ----------

# The Phase-2 flip is: the interaction contract becomes MANDATORY for *all*
# founder-facing work, enforced at write-time. We detect an *affirmative* flip
# — an assertion that the interaction contract is mandatory / required for
# founder-facing work — while deliberately NOT tripping on the explicit
# negations Phase 1 needs to state ("the interaction contract is SHOULD, not
# MUST"; "is the Phase 2 flip … out of scope"). The discriminator is the
# affirmative-mandate vocabulary tied to *founder-facing* / *all* work.
_MUST_FLIP_PATTERNS = (
    # "interaction contract … MUST … founder-facing" — but not "… not MUST …"
    re.compile(
        r"interaction\s+contract(?![^.\n]*\bnot\s+MUST\b)"
        r"[^.\n]{0,120}\bMUST\b[^.\n]{0,120}founder-facing",
        re.IGNORECASE,
    ),
    # "MUST … emit … interaction contract … for … founder-facing"
    re.compile(
        r"\bMUST\b[^.\n]{0,120}contract_type:\s*interaction"
        r"[^.\n]{0,120}founder-facing",
        re.IGNORECASE,
    ),
    # "mandatory … interaction contract … founder-facing" (the Phase-2 prose)
    re.compile(
        r"mandatory[^.\n]{0,120}interaction\s+contract"
        r"[^.\n]{0,120}founder-facing",
        re.IGNORECASE,
    ),
)


@pytest.mark.parametrize(
    "name,text_fixture",
    [
        ("WORK_PACKAGE_STANDARD.md", "wp_standard_text"),
        ("CONTRACT_FIRST_STANDARD.md", "cf_standard_text"),
    ],
)
def test_no_must_flip_for_interaction_contract(
    name: str, text_fixture: str, request: pytest.FixtureRequest
) -> None:
    """Neither file states the interaction contract as MANDATORY for all
    founder-facing work — guards against accidentally landing the Phase-2 flip.

    The negations Phase 1 *must* state ("SHOULD, not MUST"; "MUST flip … is
    Phase 2 … out of scope") are intentionally not flagged — only an
    affirmative mandate tied to founder-facing work is.
    """
    text = request.getfixturevalue(text_fixture)
    for pattern in _MUST_FLIP_PATTERNS:
        match = pattern.search(text)
        assert match is None, (
            f"{name} appears to make the interaction contract MANDATORY "
            f"(matched: {match.group(0)!r}). That is the Phase-2 MUST flip — "
            "out of scope for WP-003 (Phase 1 is SHOULD strength, ADR-002)."
        )
