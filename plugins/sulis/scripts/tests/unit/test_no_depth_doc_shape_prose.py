"""WP-005 — sever the depth→document-shape branch (ADR-001, FR-01/02/03/05).

The load-bearing decoupling: **depth sizes only the interview, never which
document sections exist.** The machine path is already decoupled (WP-001's
`_drive_specify` harness always emits the comprehensive structure; WP-003's
`_assert_no_depth_doc_gate` proves no source-line branch gates section
existence on depth). What remained coupled was the *human-readable prose* in
`specify/SKILL.md` and the requirements-analyst path — the depth table
promised a "ten-line SPEC" at lite and a fuller document only at deep, which
is exactly the "small change ⇒ thin doc" coupling ADR-001 removes.

These tests read the real skill/agent files and assert the prose no longer
conditions document shape on depth:

  - `test_specify_prose_does_not_promise_depth_sized_document` — the depth
    table's outcome column must describe *interview size*, not a depth-sized
    document (no "ten-line SPEC.md", no "SPEC.md plus flow diagrams" reserved
    to deep). This FAILS against the pre-WP-005 prose and PASSES once the
    coupling is severed.
  - `test_specify_prose_states_document_is_always_comprehensive` — the prose
    affirmatively states the comprehensive document is produced regardless of
    depth (the FR-01/FR-02 invariant in founder-readable form).
  - `test_sc04_asserter_passes_on_the_three_contract_files` — the SC-04
    regression guard (FR-03): `_assert_no_depth_doc_gate` exits 0 against the
    three real files. This is the exact command from the WP's DoD.

Pure file reads + an in-process CLI call; stdlib only; no network, no fixtures.
Lives under tests/unit/ so branch-ci (`pytest tests/unit/`) gates it (lesson
#60: a test outside tests/unit/ is never run by branch-ci).
"""

from __future__ import annotations

import re
from pathlib import Path

import _assert_no_depth_doc_gate

# Repo root is four parents up from this file:
#   <root>/plugins/sulis/scripts/tests/unit/<thisfile>
_ROOT = Path(__file__).resolve().parents[5]
_SPECIFY_SKILL = _ROOT / "plugins" / "sulis" / "skills" / "specify" / "SKILL.md"
_ANALYST = _ROOT / "plugins" / "sulis" / "agents" / "requirements-analyst.md"
_DRAFT_ARCH = (
    _ROOT / "plugins" / "sulis" / "skills" / "draft-architecture" / "SKILL.md"
)

# Phrases that couple a depth to a *document shape* — the coupling ADR-001
# severs. Each is a promise that the produced document is thinner/fuller as a
# function of depth, rather than the interview being shorter/longer.
_DEPTH_DOC_SHAPE_PHRASES = (
    "ten-line `spec.md`",
    "10-line `spec.md`",
    "`spec.md` plus flow diagrams",
)


def _read(path: Path) -> str:
    assert path.exists(), f"expected file is missing: {path}"
    return path.read_text(encoding="utf-8")


def test_specify_prose_does_not_promise_depth_sized_document() -> None:
    """The specify prose must not promise a depth-sized *document*.

    FR-01/02/05: depth sizes the interview, not the document. The depth table's
    outcome column previously read "A ten-line SPEC.md" (lite) and "A SPEC.md
    plus flow diagrams" (deep-only) — promising the document gets thinner/fuller
    with depth. That coupling must be gone.
    """
    text = _read(_SPECIFY_SKILL).lower()
    offenders = [p for p in _DEPTH_DOC_SHAPE_PHRASES if p in text]
    assert not offenders, (
        "specify/SKILL.md still couples depth to document shape — found "
        f"{offenders!r}. Depth must size only the interview; the document is "
        "always the comprehensive structure (ADR-001, FR-01/02/05)."
    )


def test_specify_prose_states_document_is_always_comprehensive() -> None:
    """The prose affirmatively states the document is always comprehensive.

    FR-01: a complete document is produced for EVERY change regardless of depth.
    Severing the coupling is necessary but not sufficient — the founder-readable
    prose must positively say so (a reader must not infer that a small change
    still gets a thin document by omission).
    """
    text = _read(_SPECIFY_SKILL).lower()
    # An affirmative statement that depth sizes the interview, paired with the
    # word "document"/"sections" — the post-WP-005 invariant in prose.
    sizes_interview = re.search(
        r"depth[^.\n]{0,80}\b(interview|conversation|questions?|intake)\b",
        text,
    )
    assert sizes_interview, (
        "specify/SKILL.md does not state that depth sizes the interview — the "
        "FR-02 invariant must be stated in founder-readable prose, not left "
        "implicit."
    )
    assert (
        "regardless of depth" in text
        or "no matter the depth" in text
        or "whatever the depth" in text
        or "at every depth" in text
    ), (
        "specify/SKILL.md does not state the document is produced regardless "
        "of depth — the FR-01 always-comprehensive invariant must be explicit."
    )


def test_sc04_asserter_passes_on_the_three_contract_files() -> None:
    """SC-04 / FR-03 regression guard: no source-line branch gates emission.

    The exact command from the WP's Definition of Done — the static inspector
    over the three real files must exit 0 (no emission branch conditions
    document-section existence on depth).
    """
    rc = _assert_no_depth_doc_gate.main(
        [str(_SPECIFY_SKILL), str(_DRAFT_ARCH), str(_ANALYST)]
    )
    assert rc == 0, (
        "_assert_no_depth_doc_gate found a depth→doc-section emission branch in "
        "one of the three Contract files (SC-04 / FR-03 violation)."
    )
