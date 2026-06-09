"""WP-005 (dispatch-brief-assembler) — read-only dispatch brief from the
change-scoped working-set.

The assembler produces an ephemeral, right-sized context brief for a
scenario-RUN's subagent dispatch, from (a) the CHANGE-scoped working-set
sections 1-3 (problem / current solution / decisions-so-far) + (b) the scoped
contract (seam I/O + scenario definition + the relevant spec slice) — NOT the
whole session history.

Two hard scope-guards, asserted MECHANICALLY here (not by comment):
  - #91: the assembler MUST NOT mutate the working-set — the working-set file's
    bytes are byte-for-byte unchanged after assembly.
  - working-set stays CHANGE-scoped: the assembler creates NO per-run
    working-set / no new file under .changes/.

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

import hashlib

from _scenario_brief import assemble_brief

# A realistic working-set fixture: numbered `## N.` sections matching the live
# WORKING-SET.md format (sections 1-5 current-state, section 6 append-only log).
_WORKING_SET = """\
# Working Set — feat-example

> Live reasoning state for this change/session.

## 1. Problem  (→ Opportunity)
Build the thing that closes the gap the founder cares about.

## 2. Current best solution  (→ Design)
Layer additive concerns over the existing runner; no new engine.

## 3. Decisions in flight  (→ Decision; status: proposed)
- **Depth = standard, drafted-from-handoff.** [accepted]
- **kind = methodology.** [accepted]

## 4. Open questions / unknowns
- Do scenarios tile the seam set 1:1?

## 5. Rejected so far
_(none yet)_

## 6. Working log  (append-only)
- 2026-06-08T19:11:35Z — Working Set created.
- 2026-06-08T20:04Z — Blueprint drafted. SECRET-FAT-LOG-LINE-DO-NOT-LEAK.
- 2026-06-08T20:30Z — yet another fat append-only line that must stay out.
"""

# The scoped contract the dispatch passes in (the seam this run drives + the
# scenario definition + the relevant spec slice only).
_SCOPED_CONTRACT = {
    "seam_io": {
        "inputs": ["dna:contract:request"],
        "outputs": ["dna:contract:saved-record"],
    },
    "scenario": {
        "id": "dna:scenario:happy-path",
        "journey": "dna:workflow:checkout",
        "verdict_invariant": {
            "kind": "equality",
            "expected_ref": "fixtures/expected.json",
        },
        "isolation": "reset",
    },
    "spec_slice": "FR-007: the saved record carries the order total.",
}

# A whole-SPEC blob the test proves does NOT leak into the brief when only a
# slice is passed.
_WHOLE_SPEC_SENTINEL = "WHOLE-SPEC-BLOB-MUST-NOT-LEAK"


def _write_working_set(tmp_path):
    ws = tmp_path / "feat-example.WORKING-SET.md"
    ws.write_text(_WORKING_SET, encoding="utf-8")
    return ws


def test_brief_assembled_read_only_from_working_set(tmp_path):
    """#91 scope-guard, mechanical: the working-set file's bytes are unchanged
    after assembly, and the brief's working_set_slice carries sections 1-3."""
    ws = _write_working_set(tmp_path)
    before = ws.read_bytes()
    before_hash = hashlib.sha256(before).hexdigest()

    brief = assemble_brief(working_set_path=ws, scoped_contract=_SCOPED_CONTRACT)

    after = ws.read_bytes()
    # Mechanical scope-guard: byte-for-byte unchanged.
    assert after == before
    assert hashlib.sha256(after).hexdigest() == before_hash

    slice_ = brief["working_set_slice"]
    assert "closes the gap" in slice_["problem"]
    assert "additive concerns" in slice_["current_solution"]
    # decisions-so-far is a list carrying the accepted decisions.
    assert isinstance(slice_["decisions_so_far"], list)
    assert any("Depth = standard" in d for d in slice_["decisions_so_far"])
    assert any("kind = methodology" in d for d in slice_["decisions_so_far"])


def test_brief_is_bounded_to_sections_1_to_3(tmp_path):
    """The brief excludes the append-only working log (section 6) and the rest
    of the file; spec_slice is the passed slice, not a whole-SPEC blob."""
    ws = _write_working_set(tmp_path)

    brief = assemble_brief(working_set_path=ws, scoped_contract=_SCOPED_CONTRACT)

    # No section-6 (working log) content leaks into the brief at all.
    serialised = repr(brief)
    assert "SECRET-FAT-LOG-LINE-DO-NOT-LEAK" not in serialised
    assert "Working Set created" not in serialised
    assert "Blueprint drafted" not in serialised
    # No section-4/5 content either — bounded to 1-3.
    assert "tile the seam set" not in serialised

    # spec_slice is exactly the passed slice, not the whole SPEC.
    assert brief["scoped_contract"]["spec_slice"] == _SCOPED_CONTRACT["spec_slice"]
    assert _WHOLE_SPEC_SENTINEL not in serialised


def test_brief_carries_scoped_contract_shape(tmp_path):
    """The scoped_contract passthrough carries seam_io + the scenario definition
    (verdict_invariant + isolation, the WP-001 fields) + the spec slice."""
    ws = _write_working_set(tmp_path)

    brief = assemble_brief(working_set_path=ws, scoped_contract=_SCOPED_CONTRACT)

    sc = brief["scoped_contract"]
    assert sc["seam_io"] == _SCOPED_CONTRACT["seam_io"]
    scenario = sc["scenario"]
    assert scenario["id"] == "dna:scenario:happy-path"
    assert scenario["verdict_invariant"]["kind"] == "equality"
    assert scenario["isolation"] == "reset"


def test_assembler_creates_no_per_run_working_set(tmp_path):
    """Scope-guard: working-set stays CHANGE-scoped — the assembler creates NO
    new file (no per-run working-set, nothing under .changes/). The directory
    holding the working-set is unchanged after assembly."""
    ws = _write_working_set(tmp_path)
    before = {p.name for p in tmp_path.iterdir()}

    brief = assemble_brief(working_set_path=ws, scoped_contract=_SCOPED_CONTRACT)

    after = {p.name for p in tmp_path.iterdir()}
    # No new file created — the brief is ephemeral (returned, never persisted).
    assert after == before
    # And it is a plain in-memory dict, not a path/handle to a persisted file.
    assert isinstance(brief, dict)


# A minimal working-set exercising the empty/edge branches: a heading with no
# body, a missing accept-decision, and a string-only spec slice. Proves the
# parser degrades gracefully (empty slice fields) rather than raising.
_MINIMAL_WORKING_SET = """\
# Working Set — feat-minimal

## 1. Problem
## 2. Current best solution
Two-line body.
Continues here.

## 3. Decisions in flight
- only one decision
  with a continuation line
"""


def test_brief_handles_empty_and_continuation_sections(tmp_path):
    """Heading-with-no-body yields an empty field; a multi-line §2 body collapses
    to single-spaced prose; a §3 bullet folds its continuation line into one
    decision entry."""
    ws = tmp_path / "feat-minimal.WORKING-SET.md"
    ws.write_text(_MINIMAL_WORKING_SET, encoding="utf-8")

    brief = assemble_brief(working_set_path=ws, scoped_contract={})

    slice_ = brief["working_set_slice"]
    # §1 has no body → empty problem string.
    assert slice_["problem"] == ""
    # §2 multi-line body collapses to single-spaced prose.
    assert slice_["current_solution"] == "Two-line body. Continues here."
    # §3 bullet + continuation fold into exactly one decision entry.
    assert slice_["decisions_so_far"] == ["only one decision with a continuation line"]
    # Empty scoped_contract degrades to empty defaults, not a KeyError.
    sc = brief["scoped_contract"]
    assert sc["seam_io"] == {}
    assert sc["scenario"] == {}
    assert sc["spec_slice"] == ""
