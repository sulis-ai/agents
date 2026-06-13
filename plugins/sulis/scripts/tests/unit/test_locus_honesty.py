"""WP-005 — locus-honesty (SC-E6): the embedded rules carry their enforcement
locus + threat-scope, and no rule claims a locus it does not hold.

The honesty primitive of this whole change (D1/D8) is: *every embedded rule is
adjudicated at exactly one enforcement-locus* — (i) model judgment (prose,
advisory), (ii) the Claude Code harness (permission rules + the PreToolUse
hook), or (iii) the OS sandbox — and is labelled by its **threat-scope**
(GAP-alpha accidental-over-reach, closed now; GAP-beta adversarial TLS-exfil,
deferred). An honest "not enforced here" beats a false "enforced".

These tests are the SC-E6 gate. They read the FOUR shipped surfaces that carry
locus claims and assert two things:

  * ``test_every_rule_labelled`` — the standard (WP-005), the PreToolUse hook
    (WP-003), the permission config (WP-003), and the sandbox recipe (WP-004)
    each carry the enforcement-locus + threat-scope vocabulary. A rule with no
    locus is an unlabelled rule — the failure mode this gate exists to catch.

  * ``test_no_overclaim`` — no surface over-claims:
      - the prose / locus-i nudge must NOT claim harness (ii) or OS (iii)
        enforcement (a quality nudge is not a safety control);
      - the MCP-identity argument must be labelled necessary-NOT-sufficient
        (a denyable identity makes "allow-safe/deny-raw" expressible; it is not
        itself the wall);
      - the sandbox recipe must own the adversarial-subprocess case (locus iii)
        and label GAP-beta DEFERRED, never claimed-closed.

  * ``test_standard_has_two_axis_shape`` — the standard documents the D8 2-axis
    criterion (invocation-substrate x governance), the narrow MCP criterion,
    the worked classification, and the spiral chain; it is a real standard, not
    a stub.

The assertions read the actual shipped text, so they fail if a future edit
drops a label or introduces an over-claim — not a tautology.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# plugins/sulis/scripts/tests/unit/<this> → parents[3] == plugins/sulis
_SULIS = Path(__file__).resolve().parents[3]

_STANDARD = _SULIS / "references" / "standards" / "GOVERNED_ACTION_SURFACE_STANDARD.md"
_HOOK = _SULIS / "scripts" / "_safe_tools_hook.py"
_SETTINGS = _SULIS / "settings.json"
_RECIPE = _SULIS / "references" / "sandbox-enable-recipe.md"
_AGENT = _SULIS / "agents" / "sulis.md"

# The three loci, named the way every surface in this change names them.
_LOCUS_TOKENS = ("locus i", "locus ii", "locus iii")
# The two threat-scopes (rendered with either the greek letter or its ascii name
# so the gate survives both spellings used across the surfaces).
_GAP_ALPHA = ("gap-α", "gap-alpha")
_GAP_BETA = ("gap-β", "gap-beta")


def _read(p: Path) -> str:
    assert p.is_file(), f"expected surface missing at {p}"
    return p.read_text(encoding="utf-8")


def _lower(p: Path) -> str:
    return _read(p).lower()


def _has_any(haystack: str, needles) -> bool:
    return any(n in haystack for n in needles)


# --------------------------------------------------------------------------- #
# test_every_rule_labelled — SC-E6 (a): every locus-bearing surface is labelled
# --------------------------------------------------------------------------- #
def test_every_rule_labelled():
    """The standard + hook + permission config + recipe each carry the
    enforcement-locus + threat-scope vocabulary. An unlabelled rule is the
    failure this gate exists to catch."""
    surfaces = {
        "standard": _lower(_STANDARD),
        "hook": _lower(_HOOK),
        "recipe": _lower(_RECIPE),
    }
    for name, text in surfaces.items():
        # at least one explicit enforcement-locus label
        present = [tok for tok in _LOCUS_TOKENS if tok in text]
        assert present, (
            f"{name}: no enforcement-locus label (expected one of {_LOCUS_TOKENS})"
        )
        # threat-scope vocabulary present (either gap label, or both threat words)
        scoped = (
            _has_any(text, _GAP_ALPHA)
            or _has_any(text, _GAP_BETA)
            or ("threat-scope" in text)
            or ("accidental" in text and "adversarial" in text)
        )
        assert scoped, (
            f"{name}: no threat-scope label (gap-alpha/beta / accidental+adversarial)"
        )

    # The permission config is JSON, not prose — its honesty contract is that it
    # denies the raw web tools and allows ONLY the safe MCP identities. That IS
    # its locus-ii claim; assert the shape rather than a prose label.
    cfg = json.loads(_read(_SETTINGS))
    deny = cfg["permissions"]["deny"]
    allow = cfg["permissions"]["allow"]
    assert "WebFetch" in deny, "permission config: WebFetch must be denied (locus ii)"
    assert any("curl" in d for d in deny), "permission config: raw curl must be denied"
    assert any(a.startswith("mcp__sulis-safe-tools__") for a in allow), (
        "permission config: the safe MCP identities must be the allowed path"
    )


# --------------------------------------------------------------------------- #
# test_no_overclaim — SC-E6 (b): no surface claims a locus it does not hold
# --------------------------------------------------------------------------- #
def test_no_overclaim():
    """No rule claims more safety than its locus delivers."""
    standard = _lower(_STANDARD)
    recipe = _lower(_RECIPE)
    agent = _lower(_AGENT)

    # (1) The prose / quality nudge in the agent is locus-i ONLY. It must read as
    # a quality preference, and must NOT claim it enforces safety. We assert the
    # nudge sentence(s) mention quality/clean/token and disclaim enforcement.
    # Find the nudge region by its anchor phrase.
    assert "safe_fetch" in agent or "safe-fetch" in agent, (
        "agent: expected a safe-fetch quality nudge"
    )
    # The nudge must explicitly disclaim that the prose is the safety control.
    assert ("not the safety" in agent) or (
        "safety" in agent and "hook" in agent and "sandbox" in agent
    ), (
        "agent: the quality nudge must disclaim that prose is the safety control "
        "(safety = the hook + sandbox, not this line)"
    )
    # And it must NOT assert that the prose itself blocks/enforces/denies.
    # Look at the lines around the nudge for a forbidden enforcement verb tied to
    # the prose. We scan the whole agent file for an over-claim pattern that ties
    # a prose preference to enforcement.
    overclaim = re.search(r"prose[^.\n]*(enforc|block|deny|prevent|guarantee)", agent)
    assert overclaim is None, (
        f"agent: prose nudge over-claims enforcement: {overclaim.group(0)!r}"
    )

    # (2) The MCP-identity argument is necessary-NOT-sufficient. The standard must
    # say so in those terms (so no future reader treats MCP exposure as the wall).
    assert "necessary" in standard and "sufficient" in standard, (
        "standard: the MCP-identity claim must be labelled necessary-not-sufficient"
    )

    # (3) The sandbox recipe owns the adversarial-subprocess case (locus iii) and
    # labels GAP-beta deferred — never claimed closed.
    assert "locus iii" in recipe, "recipe: must claim locus iii (OS backstop)"
    assert _has_any(recipe, _GAP_BETA), "recipe: must name GAP-beta"
    assert "deferred" in recipe, (
        "recipe: GAP-beta must be labelled DEFERRED, not closed"
    )
    # The standard must also defer GAP-beta, not claim it closed.
    assert _has_any(standard, _GAP_BETA) and "deferred" in standard, (
        "standard: GAP-beta must be carried as deferred"
    )

    # (4) The standard must not claim the prose layer (locus i) enforces anything.
    li_overclaim = re.search(
        r"locus i\b[^.\n]*(enforc|block|deny|prevent|guarantee)", standard
    )
    assert li_overclaim is None, (
        f"standard: locus-i (prose) over-claims enforcement: {li_overclaim.group(0)!r}"
    )


# --------------------------------------------------------------------------- #
# test_standard_has_two_axis_shape — the standard is real, not a stub
# --------------------------------------------------------------------------- #
def test_standard_has_two_axis_shape():
    """The standard documents the D8 2-axis criterion, the narrow MCP criterion,
    the worked classification, and the spiral chain — a genuine standard."""
    text = _lower(_STANDARD)

    # The TWO axes — invocation-substrate x governance, explicitly NOT "what it
    # touches".
    assert "invocation-substrate" in text or "invocation substrate" in text, (
        "standard: missing the invocation-substrate axis"
    )
    assert "governance" in text, "standard: missing the governance axis"
    for substrate in ("raw-bash", "cli", "mcp"):
        assert substrate in text, f"standard: substrate axis must name {substrate!r}"
    for gov in ("ungoverned", "hook-governed", "permission-denied"):
        assert gov in text, f"standard: governance axis must name {gov!r}"

    # The narrow MCP criterion: typed/structured contract OR denyable identity at
    # a trust boundary, AND no selection-surface bloat; default = CLI.
    assert "typed" in text and (
        "trust boundary" in text or "denyable identity" in text
    ), "standard: missing the MCP criterion (typed contract / denyable identity)"
    assert "selection" in text, (
        "standard: the binding constraint (selection accuracy, ~30-50-tool cliff) must appear"
    )
    assert "default" in text and "cli" in text, (
        "standard: default-to-CLI must be stated"
    )

    # Governance != MCP — a free-standing hook layer.
    assert "governance" in text and "hook" in text, (
        "standard: governance-is-a-free-standing-hook-layer must be stated"
    )

    # Worked classification: MCP now = safe-fetch + scoped-file; ~55 CLIs stay
    # CLI; one hook; never 1:1 the emit-* family.
    assert "safe_fetch" in text or "safe-fetch" in text, (
        "standard: classification must name safe-fetch"
    )
    assert "scoped_file" in text or "scoped-file" in text, (
        "standard: classification must name scoped-file"
    )
    assert "emit" in text, (
        "standard: classification must address the emit-* family (never 1:1)"
    )

    # The chain of critical-thinking spirals must be cited (the criterion's
    # provenance). Assert at least three distinct spiral ULIDs appear.
    ulids = set(re.findall(r"01k[0-9a-z]{7,}", text))
    assert len(ulids) >= 3, (
        f"standard: must cite the spiral chain (>=3 spiral ULIDs); found {sorted(ulids)}"
    )
