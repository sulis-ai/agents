"""Unit tests for _specify_classifier.py (Phase 6b — /sulis:specify depth classifier).

classify_depth() proposes one of three depth modes — "lite" / "standard" /
"deep" — from three deterministic signals: file count, primitive, and a
founder-facing flag. Per the change-as-primitive design (§ "Depth modes for
Specify"): on uncertainty, default to standard. The founder always confirms
or overrides downstream — the classifier only *proposes*.

Pure function: no I/O, no git, no env. Signals are gathered by the caller
and handed in. These tests pin the proposal table exactly.
"""

from __future__ import annotations

import _specify_classifier as sc


# ─── Shape ──────────────────────────────────────────────────────────────────


def test_returns_decision_dataclass_with_required_fields():
    d = sc.classify_depth(primitive="fix", file_count=1, founder_facing=False)
    assert d.depth in ("lite", "standard", "deep")
    assert isinstance(d.reason, str) and d.reason
    assert isinstance(d.signals, dict)
    assert d.signals["primitive"] == "fix"
    assert d.signals["file_count"] == 1
    assert d.signals["founder_facing"] is False


def test_depth_is_one_of_three_modes_for_every_known_primitive():
    for prim in sc.LITE_PRIMITIVES | sc.DEEP_PRIMITIVES | {"refactor", "move", "wrap"}:
        d = sc.classify_depth(primitive=prim, file_count=2, founder_facing=False)
        assert d.depth in ("lite", "standard", "deep"), prim


# ─── Lite proposals ───────────────────────────────────────────────────────────


def test_single_file_mechanical_fix_proposes_lite():
    d = sc.classify_depth(primitive="fix", file_count=1, founder_facing=False)
    assert d.depth == "lite"


def test_typo_chore_single_file_proposes_lite():
    d = sc.classify_depth(primitive="chore", file_count=1, founder_facing=False)
    assert d.depth == "lite"


def test_delete_single_file_proposes_lite():
    d = sc.classify_depth(primitive="delete", file_count=1, founder_facing=False)
    assert d.depth == "lite"


def test_lite_primitive_with_many_files_escalates_to_standard():
    # A "lite" primitive that sprawls across many files is no longer trivial.
    d = sc.classify_depth(primitive="fix", file_count=9, founder_facing=False)
    assert d.depth == "standard"


def test_lite_primitive_that_is_founder_facing_escalates_to_standard():
    # Touching a user-visible surface is never a silent lite change.
    d = sc.classify_depth(primitive="fix", file_count=1, founder_facing=True)
    assert d.depth == "standard"


# ─── Deep proposals ───────────────────────────────────────────────────────────


def test_create_feature_proposes_deep():
    d = sc.classify_depth(primitive="create", file_count=4, founder_facing=False)
    assert d.depth == "deep"


def test_compose_new_system_proposes_deep():
    d = sc.classify_depth(primitive="compose", file_count=3, founder_facing=False)
    assert d.depth == "deep"


def test_any_primitive_that_is_founder_facing_and_large_proposes_deep():
    # User-facing + multi-file → full SRD territory.
    d = sc.classify_depth(primitive="extend", file_count=8, founder_facing=True)
    assert d.depth == "deep"


def test_deep_primitive_single_file_still_at_least_standard():
    # A "create" touching one file is unusual but should not collapse to lite.
    d = sc.classify_depth(primitive="create", file_count=1, founder_facing=False)
    assert d.depth in ("standard", "deep")
    assert d.depth != "lite"


# ─── Standard (the default / uncertainty fallback) ───────────────────────────


def test_mid_size_refactor_proposes_standard():
    d = sc.classify_depth(primitive="refactor", file_count=4, founder_facing=False)
    assert d.depth == "standard"


def test_unknown_primitive_defaults_to_standard():
    d = sc.classify_depth(primitive="banana", file_count=3, founder_facing=False)
    assert d.depth == "standard"
    assert "default" in d.reason.lower() or "uncertain" in d.reason.lower()


def test_unknown_primitive_none_defaults_to_standard():
    d = sc.classify_depth(primitive=None, file_count=None, founder_facing=False)
    assert d.depth == "standard"


def test_missing_file_count_does_not_crash():
    # At specify time there may be zero commits — file_count is unknown.
    d = sc.classify_depth(primitive="fix", file_count=None, founder_facing=False)
    assert d.depth in ("lite", "standard", "deep")


# ─── founder_facing path heuristic ────────────────────────────────────────────


def test_paths_with_ui_surface_flag_founder_facing():
    assert sc.paths_touch_founder_surface(["src/components/Login.tsx"]) is True
    assert sc.paths_touch_founder_surface(["app/routes/checkout.py"]) is True
    assert sc.paths_touch_founder_surface(["templates/email/welcome.html"]) is True


def test_internal_only_paths_not_founder_facing():
    assert sc.paths_touch_founder_surface(["src/lib/_utils.py"]) is False
    assert sc.paths_touch_founder_surface(["tests/unit/test_foo.py"]) is False
    assert sc.paths_touch_founder_surface([]) is False


def test_mixed_paths_are_founder_facing_if_any_surface_touched():
    assert sc.paths_touch_founder_surface(
        ["src/lib/_utils.py", "src/components/Nav.tsx"]
    ) is True


# ─── Plain-English proposal sentence ──────────────────────────────────────────


def test_proposal_sentence_is_founder_english_for_lite():
    d = sc.classify_depth(primitive="fix", file_count=1, founder_facing=False)
    sentence = sc.proposal_sentence(d)
    # Plain English, names the depth, invites override. No internal IDs.
    assert "lite" in sentence.lower() or "quick" in sentence.lower()
    assert "?" in sentence
    for jargon in ("primitive", "founder_facing", "file_count", "SPEC-", "WP-"):
        assert jargon not in sentence


def test_proposal_sentence_for_deep_offers_override():
    d = sc.classify_depth(primitive="create", file_count=5, founder_facing=True)
    sentence = sc.proposal_sentence(d)
    assert "?" in sentence


# ─── FR-04: depth phrases describe interview size, not document shape ──────────
#
# WP-004 (REORGANISE/Refactor). _DEPTH_PHRASE / _DEPTH_ALT are the founder-facing
# strings proposal_sentence() renders. FR-04 requires them to describe the
# *interview* size (how many questions), never *document* completeness ("three
# lines", "the flows drawn out"). Per EP-07 the characterisation test pins the
# current strings (it is UPDATED, not deleted, after the reword); the second
# test asserts the post-reword shape and fails until the strings are reworded.


def test_proposal_sentence_current_wording():
    """Characterisation pin for the depth phrases this WP rewords.

    Pins the exact `_DEPTH_PHRASE` / `_DEPTH_ALT` strings proposal_sentence()
    composes, so the reword is a deliberate, reviewed diff (REORGANISE
    doctrine). Updated to the new wording in the same WP's Green step.
    """
    # The phrase rendered per depth (the part this WP rewords). Updated to the
    # post-FR-04 wording: interview size only, no document-shape language.
    assert sc._DEPTH_PHRASE["lite"] == (
        "a few quick questions (about thirty seconds)"
    )
    assert sc._DEPTH_PHRASE["standard"] == (
        "a few questions (a couple of minutes)"
    )
    assert sc._DEPTH_PHRASE["deep"] == (
        "a fuller set of questions (a longer conversation)"
    )
    # The alternate-depth nudge.
    assert sc._DEPTH_ALT["lite"] == "answer a few more questions"
    assert sc._DEPTH_ALT["standard"] == "fewer questions or a fuller conversation"
    assert sc._DEPTH_ALT["deep"] == "a shorter set of questions"


def test_depth_phrase_describes_interview_not_doc_shape():
    """Every depth phrase + alt talks about the interview, not the document.

    FR-04: the founder-facing proposal must describe interview size — questions
    asked — and must NOT describe document completeness (lines, sections, the
    document itself, "drawn out" flows).
    """
    interview_words = ("question", "questions", "conversation", "ask")
    doc_shape_words = (
        "line",
        "lines",
        "section",
        "sections",
        "document",
        "doc ",
        "drawn out",
        "three lines",
    )
    for depth in ("lite", "standard", "deep"):
        phrase = sc._DEPTH_PHRASE[depth].lower()
        alt = sc._DEPTH_ALT[depth].lower()
        # Mentions the interview.
        assert any(w in phrase for w in interview_words), (
            depth,
            "phrase",
            phrase,
        )
        # Never mentions document shape.
        for bad in doc_shape_words:
            assert bad not in phrase, (depth, "phrase", bad, phrase)
            assert bad not in alt, (depth, "alt", bad, alt)
