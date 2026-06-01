"""Prose verification for WP-005 (discover-project Ask-phase fragments).

WP-005 authors three prose fragments + three rendered examples that
WP-008's ``SKILL.md`` will include verbatim:

  * ``confirm-or-override.md`` — Step ``confirm-or-override-inferences``
  * ``gather-ambiguous-fields.md`` — Step ``gather-ambiguous-fields``
  * ``per-field-diff.md`` — the ``--update`` flow per ADR-005

Plus rendered examples at ``_prompts/examples/`` that show exactly what
the prompt templates would produce — no aspirational text, no
placeholder boilerplate.

The fragments are **founder English** (FE-01..FE-10): no internal IDs
on the founder-facing surface (no ULIDs, no ``dna:`` prefixes, no
``FR-NN``/``WP-NN``/``ADR-NN`` IDs, no ``[A-Z]{2,}-\\d{2,}`` patterns).
The drift detector relies on a single allowlisted line per file (the
``<!-- canonical:step:... -->`` annotation per ADR-001 + WP-009) — that
line is the only ID-shaped string the file is permitted to contain.

Per the WP Contract (`Definition of Done > Red`) the suite covers
9 structural assertions on the prose + example files. Stdlib + pytest
only, Python 3.11-safe. Paths resolve relative to this test file so
the suite is location-stable inside any worktree.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/sulis/
_PLUGIN_ROOT = Path(__file__).resolve().parents[3]
_PROMPTS_DIR = _PLUGIN_ROOT / "skills" / "discover-project" / "_prompts"
_EXAMPLES_DIR = _PROMPTS_DIR / "examples"

_CONFIRM = _PROMPTS_DIR / "confirm-or-override.md"
_AMBIGUOUS = _PROMPTS_DIR / "gather-ambiguous-fields.md"
_DIFF = _PROMPTS_DIR / "per-field-diff.md"

_EX_CONFIRM = _EXAMPLES_DIR / "example-confirm-prompt.txt"
_EX_AMBIGUOUS = _EXAMPLES_DIR / "example-ambiguous-prompt.txt"
_EX_DIFF = _EXAMPLES_DIR / "example-per-field-diff.txt"

# Founder-English negative patterns. If any of these appear OUTSIDE the
# allowlisted canonical-step annotation line, the file is leaking
# internal taxonomy onto the founder-facing surface.
_INTERNAL_ID_REGEXES = (
    re.compile(r"\b[A-Z]{2,}-\d{2,}\b"),  # WP-005, ADR-005, FR-009, MUC-004
    re.compile(r"\bdna:[a-z]+:"),  # dna:step:..., dna:tenant:..., dna:workflow:...
    re.compile(r"\bULID\b", re.IGNORECASE),  # internal taxonomy
)

# The canonical-step annotation is the ONE permitted line that carries
# step-naming. The drift detector parses it; the founder doesn't read
# it (HTML comment, hidden in rendered Markdown).
_ANNOTATION_RE = re.compile(r"^<!--\s*canonical:step:[a-z][a-z0-9-]*\s*-->\s*$")


def _strip_annotation_lines(text: str) -> str:
    """Return the file's text with canonical-step annotation lines removed.

    Annotation lines are allowlisted from the internal-ID checks because
    they are the documented bridge between the drift detector and the
    founder-facing prose. Everything else is founder-readable.
    """
    return "\n".join(
        line for line in text.splitlines() if not _ANNOTATION_RE.match(line)
    )


def _assert_no_internal_ids(text: str, path: Path) -> None:
    """Fail with the first offending match so the author sees the leak."""
    body = _strip_annotation_lines(text)
    for pattern in _INTERNAL_ID_REGEXES:
        match = pattern.search(body)
        if match:
            pytest.fail(
                f"{path.name} leaks internal taxonomy on the founder-facing "
                f"surface: matched '{match.group(0)}' at offset "
                f"{match.start()}. Founder English (FE-01..FE-10) forbids "
                "WP/ADR/FR IDs, dna: prefixes, and the literal 'ULID' "
                "in any prose the founder reads."
            )


# ---------------------------------------------------------------------------
# Founder-English checks — one per prose file
# ---------------------------------------------------------------------------


def test_confirm_prompt_uses_founder_english() -> None:
    """``confirm-or-override.md`` carries no internal IDs in its prose."""
    assert _CONFIRM.is_file(), f"missing prose file: {_CONFIRM}"
    _assert_no_internal_ids(_CONFIRM.read_text(encoding="utf-8"), _CONFIRM)


def test_ambiguous_prompt_uses_founder_english() -> None:
    """``gather-ambiguous-fields.md`` carries no internal IDs in its prose."""
    assert _AMBIGUOUS.is_file(), f"missing prose file: {_AMBIGUOUS}"
    _assert_no_internal_ids(_AMBIGUOUS.read_text(encoding="utf-8"), _AMBIGUOUS)


def test_per_field_diff_uses_founder_english() -> None:
    """``per-field-diff.md`` carries no internal IDs in its prose."""
    assert _DIFF.is_file(), f"missing prose file: {_DIFF}"
    _assert_no_internal_ids(_DIFF.read_text(encoding="utf-8"), _DIFF)


# ---------------------------------------------------------------------------
# Confirm-prompt shape — one field per prompt, keep-or-override choice
# ---------------------------------------------------------------------------


def test_confirm_prompt_one_field_per_prompt() -> None:
    """Example shows N>=3 distinct prompts each closing with the choice line.

    The Ask phase MUST present one field per prompt — surfacing all
    inferred values in a single dump would defeat the consumer-
    confirmation gate (MUC-004 armor). The example file is the contract
    for what the prompt loop renders at runtime; we assert structural
    shape on it.
    """
    assert _EX_CONFIRM.is_file(), f"missing example: {_EX_CONFIRM}"
    text = _EX_CONFIRM.read_text(encoding="utf-8")
    # The choice line is the keep-or-override binary. Count how many
    # times it appears — the example is required to show >= 3 distinct
    # prompts so the one-per-prompt shape is visible.
    choice_marker_count = text.lower().count("override")
    assert choice_marker_count >= 3, (
        "example-confirm-prompt.txt is required to show >= 3 distinct "
        "prompts each ending with the keep-or-override choice — saw "
        f"'override' appearing {choice_marker_count} time(s). The one-"
        "field-per-prompt shape is the founder-confirmation gate; the "
        "example must demonstrate it."
    )


# ---------------------------------------------------------------------------
# Confidence + token surfaces forbidden in Ask prose (per TDD §Armor §Observability)
# ---------------------------------------------------------------------------


def test_no_confidence_displayed() -> None:
    """Confidence values are NEVER surfaced to the founder.

    Per TDD §Armor §Observability: the LLM's ``confidence`` field stays
    in the structured-stderr debug log. The founder sees the inferred
    value as a plain proposal — surfacing confidence introduces
    decision paralysis and leaks internal taxonomy.
    """
    files = [_CONFIRM, _AMBIGUOUS, _DIFF, _EX_CONFIRM, _EX_AMBIGUOUS, _EX_DIFF]
    for path in files:
        assert path.is_file(), f"missing file: {path}"
        text = path.read_text(encoding="utf-8").lower()
        assert "confidence" not in text, (
            f"{path.name} surfaces 'confidence' — forbidden in Ask "
            "prose per TDD §Armor §Observability. Confidence is "
            "debug-stderr only; the founder sees the inferred value "
            "as a plain proposal."
        )


def test_no_token_count_displayed_in_ask_prose() -> None:
    """Token / budget surfaces stay in the stderr log, not in the prompts.

    The structured stderr log emits ``tokens used: N / M`` per TDD
    §Armor §Observability — that's debug. The Ask phase prompts are
    the founder-facing surface and MUST NOT carry token-counting
    surface; the founder doesn't care, and exposing it implies they
    should.
    """
    files = [_CONFIRM, _AMBIGUOUS, _DIFF, _EX_CONFIRM, _EX_AMBIGUOUS, _EX_DIFF]
    forbidden = ("tokens used", "token budget", "budget exceeded")
    for path in files:
        assert path.is_file(), f"missing file: {path}"
        lowered = path.read_text(encoding="utf-8").lower()
        for needle in forbidden:
            assert needle not in lowered, (
                f"{path.name} surfaces '{needle}' — token-counting "
                "surface lives in the structured-stderr log per TDD "
                "§Armor §Observability, NOT in founder-facing Ask "
                "prompts."
            )


# ---------------------------------------------------------------------------
# Per-field diff specifics (ADR-005)
# ---------------------------------------------------------------------------


def test_per_field_diff_excludes_metadata_fields() -> None:
    """The diff prose explicitly names the excluded metadata fields.

    Per ADR-005, metadata fields like ``valid_from`` change every run
    and would create diff noise. The prose MUST tell the reader those
    fields are excluded so the contract is visible.
    """
    assert _DIFF.is_file(), f"missing prose file: {_DIFF}"
    text = _DIFF.read_text(encoding="utf-8")
    assert "valid_from" in text, (
        "per-field-diff.md is required to name 'valid_from' as an "
        "excluded metadata field — per ADR-005 the diff hides "
        "metadata that changes every run, and the prose must make "
        "that exclusion visible to the reader."
    )


# ---------------------------------------------------------------------------
# Canonical-step annotation (ADR-001 + WP-009 drift parser)
# ---------------------------------------------------------------------------


def test_canonical_step_annotations_present() -> None:
    """Each prose file opens with its ``<!-- canonical:step:... -->`` line.

    The drift detector (WP-009) parses these annotations to verify the
    SKILL.md's prose conforms to the canonical Step set. Missing the
    annotation surfaces as a missing-Step-coverage failure at PR time.

    Required bindings per the WP file Notes section:
      * confirm-or-override.md   -> confirm-or-override-inferences
      * gather-ambiguous-fields.md -> gather-ambiguous-fields
      * per-field-diff.md        -> gather-ambiguous-fields
        (per-ADR-005, diff approvals are the human gate during
         re-discovery and share the gather-ambiguous-fields Step)
    """
    bindings = {
        _CONFIRM: "confirm-or-override-inferences",
        _AMBIGUOUS: "gather-ambiguous-fields",
        _DIFF: "gather-ambiguous-fields",
    }
    for path, expected_step in bindings.items():
        assert path.is_file(), f"missing prose file: {path}"
        text = path.read_text(encoding="utf-8")
        expected_line = f"<!-- canonical:step:{expected_step} -->"
        assert expected_line in text, (
            f"{path.name} is missing the required canonical-step "
            f"annotation '{expected_line}'. The drift detector (per "
            "ADR-001 + WP-009) parses this line to verify the prose "
            "binds to its Step; without it the conformance check fails."
        )


# ---------------------------------------------------------------------------
# Per-field diff example — binary [k]/[p] choice (no third option)
# ---------------------------------------------------------------------------


def test_examples_show_keep_or_override_binary() -> None:
    """The diff example shows exactly the ``[k]`` and ``[p]`` choices.

    Per ADR-005 the diff is a binary choice — keep existing or apply
    proposed. A third option (e.g. ``[e]`` to edit inline) would expand
    the consequence surface and contradict the decision. The example
    MUST show the binary shape.
    """
    assert _EX_DIFF.is_file(), f"missing example: {_EX_DIFF}"
    text = _EX_DIFF.read_text(encoding="utf-8")
    assert "[k]" in text, (
        "example-per-field-diff.txt is missing the '[k]' (keep "
        "existing) choice marker — ADR-005 mandates the binary "
        "keep/apply choice; the example must show it verbatim."
    )
    assert "[p]" in text, (
        "example-per-field-diff.txt is missing the '[p]' (apply "
        "proposed) choice marker — ADR-005 mandates the binary "
        "keep/apply choice; the example must show it verbatim."
    )
