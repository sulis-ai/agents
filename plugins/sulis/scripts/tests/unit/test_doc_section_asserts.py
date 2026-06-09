"""Unit tests for the document-section assertion scripts (WP-003).

The P1 always-comprehensive scenarios (SC-01..SC-05) assert on the produced
design document's structure with five small, single-purpose assertion scripts.
Each is a CLI that exits 0 iff its check passes and non-zero with a
human-readable reason on failure (the reason is what the founder-facing gate
rollup surfaces in plain English). They share one markdown-section-parsing
helper (``_doc_section_parse``) — the single source of header detection.

These are the SC-01..SC-05 assertion halves:
  - SC-01 → _assert_doc_sections      (a required section is missing ⇒ fail)
  - SC-02 → _assert_same_section_set  (header sets differ across depths ⇒ fail)
  - SC-03 → _assert_section_na        (present-but-n/a vs silently-dropped)
  - SC-05 → _assert_measurable_nfr    (adjective-only NFR ⇒ fail)
  - SC-04 → _assert_no_depth_doc_gate (an emission branch on depth ⇒ fail)

Tests drive the CLI via ``main(argv) -> int`` (in-process — fast, deterministic)
so they assert the exit-code contract directly. The shared parser is unit-tested
through the four section-aware scripts.
"""

from __future__ import annotations

from pathlib import Path

import _assert_doc_sections
import _assert_measurable_nfr
import _assert_no_depth_doc_gate
import _assert_same_section_set
import _assert_section_na


# ─── fixtures (tiny in-memory docs written to tmp) ──────────────────────────


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body, encoding="utf-8")
    return p


_DOC_WITH_NFR = """\
# Design

## Overview
text

## NFR
- latency < 5 ms

## Verification Plan
text
"""

_DOC_WITHOUT_NFR = """\
# Design

## Overview
text

## Verification Plan
text
"""


# ─── SC-01 — _assert_doc_sections: a doc missing a required section fails ───


def test_assert_doc_sections_detects_missing_section(tmp_path, capsys):
    doc = _write(tmp_path, "DESIGN.md", _DOC_WITHOUT_NFR)
    rc = _assert_doc_sections.main(
        ["--require", "overview,nfr,verification plan", str(doc)]
    )
    assert rc != 0
    err = capsys.readouterr().err.lower()
    assert "nfr" in err  # the missing section is named in the human-readable reason


def test_assert_doc_sections_passes_when_all_present(tmp_path):
    doc = _write(tmp_path, "DESIGN.md", _DOC_WITH_NFR)
    rc = _assert_doc_sections.main(
        ["--require", "overview,nfr,verification plan", str(doc)]
    )
    assert rc == 0


# ─── SC-02 — _assert_same_section_set: differing header sets fails ──────────


def test_same_section_set_detects_drift(tmp_path, capsys):
    a = _write(tmp_path, "lite.md", _DOC_WITH_NFR)
    b = _write(tmp_path, "deep.md", _DOC_WITHOUT_NFR)  # missing ## NFR
    rc = _assert_same_section_set.main([str(a), str(b)])
    assert rc != 0
    err = capsys.readouterr().err.lower()
    assert "nfr" in err  # the drifting header is named


def test_same_section_set_passes_when_identical(tmp_path):
    a = _write(tmp_path, "lite.md", _DOC_WITH_NFR)
    b = _write(tmp_path, "deep.md", _DOC_WITH_NFR)
    rc = _assert_same_section_set.main([str(a), str(b)])
    assert rc == 0


# ─── SC-03 — _assert_section_na: present-but-n/a vs silently-dropped ────────


def test_section_na_requires_justification(tmp_path, capsys):
    # bare "n/a" (no reason) ⇒ fail
    bare = _write(
        tmp_path,
        "bare.md",
        "# D\n\n## Threat Model\nn/a\n\n## Verification Plan\nx\n",
    )
    rc_bare = _assert_section_na.main(["--section", "threat model", str(bare)])
    assert rc_bare != 0
    err = capsys.readouterr().err.lower()
    assert "threat model" in err or "reason" in err or "justification" in err

    # "n/a — <reason>" ⇒ pass
    justified = _write(
        tmp_path,
        "ok.md",
        "# D\n\n## Threat Model\nn/a — no untrusted input on this internal path\n\n## Verification Plan\nx\n",
    )
    rc_ok = _assert_section_na.main(["--section", "threat model", str(justified)])
    assert rc_ok == 0


def test_section_na_missing_heading_fails(tmp_path):
    # a missing heading is NOT a valid "n/a" — it must fail (NFR-R01: a dropped
    # section is distinguishable from a present-but-n/a one).
    missing = _write(tmp_path, "missing.md", "# D\n\n## Overview\nx\n")
    rc = _assert_section_na.main(["--section", "threat model", str(missing)])
    assert rc != 0


# ─── SC-05 — _assert_measurable_nfr: adjective-only NFR fails ───────────────


def test_measurable_nfr_rejects_adjective_only(tmp_path, capsys):
    # "fast" — no number/threshold ⇒ fail
    adjective = _write(
        tmp_path,
        "adj.md",
        "# D\n\n## Performance\nThe system is fast and responsive.\n",
    )
    rc_bad = _assert_measurable_nfr.main(["--categories", "performance", str(adjective)])
    assert rc_bad != 0
    err = capsys.readouterr().err.lower()
    assert "performance" in err

    # "< 5 ms" — a numeric threshold ⇒ pass
    measurable = _write(
        tmp_path,
        "meas.md",
        "# D\n\n## Performance\nclassify_depth returns < 5 ms; 1000 calls < 5 s.\n",
    )
    rc_ok = _assert_measurable_nfr.main(["--categories", "performance", str(measurable)])
    assert rc_ok == 0


# ─── SC-04 — _assert_no_depth_doc_gate: emission branch on depth fails ──────


def test_no_depth_doc_gate_flags_branch(tmp_path, capsys):
    # a fixture skill with `if depth == lite: skip nfr` ⇒ fail
    gated = _write(
        tmp_path,
        "skill.md",
        "Step 4. Emit the document.\n\n"
        "    if depth == 'lite':\n"
        "        skip the nfr section\n",
    )
    rc = _assert_no_depth_doc_gate.main([str(gated)])
    assert rc != 0
    err = capsys.readouterr().err.lower()
    assert "depth" in err


def test_no_depth_doc_gate_passes_when_no_branch(tmp_path):
    # depth sizes the interview, not the document — describing depth without
    # conditioning section emission on it is fine.
    clean = _write(
        tmp_path,
        "skill.md",
        "Step 4. Always emit the full document.\n"
        "Depth sizes only the interview, never which sections exist.\n",
    )
    rc = _assert_no_depth_doc_gate.main([str(clean)])
    assert rc == 0


# ─── CLI edge / error paths (exit code 2 = bad input) ───────────────────────


def test_doc_sections_empty_require_is_bad_input(tmp_path):
    doc = _write(tmp_path, "d.md", _DOC_WITH_NFR)
    assert _assert_doc_sections.main(["--require", " , ,", str(doc)]) == 2


def test_doc_sections_unreadable_file_is_bad_input(tmp_path):
    missing = tmp_path / "nope.md"
    assert _assert_doc_sections.main(["--require", "overview", str(missing)]) == 2


def test_same_section_set_single_doc_is_bad_input(tmp_path):
    doc = _write(tmp_path, "only.md", _DOC_WITH_NFR)
    assert _assert_same_section_set.main([str(doc)]) == 2


def test_same_section_set_unreadable_file_is_bad_input(tmp_path):
    a = _write(tmp_path, "a.md", _DOC_WITH_NFR)
    assert _assert_same_section_set.main([str(a), str(tmp_path / "gone.md")]) == 2


def test_section_na_populated_section_passes(tmp_path):
    # a section with real content (not an n/a marker at all) is populated ⇒ ok.
    doc = _write(
        tmp_path,
        "pop.md",
        "# D\n\n## Threat Model\nSTRIDE analysis with two trust boundaries.\n",
    )
    assert _assert_section_na.main(["--section", "threat model", str(doc)]) == 0


def test_section_na_empty_body_fails(tmp_path):
    # heading present but body blank ⇒ fail (neither populated nor justified n/a).
    doc = _write(tmp_path, "empty.md", "# D\n\n## Threat Model\n\n## Next\nx\n")
    assert _assert_section_na.main(["--section", "threat model", str(doc)]) == 1


def test_section_na_unreadable_file_is_bad_input(tmp_path):
    assert _assert_section_na.main(["--section", "x", str(tmp_path / "gone.md")]) == 2


def test_measurable_nfr_missing_category_is_bad_input(tmp_path):
    # the named category section is absent ⇒ exit 2 (can't assess; bad input).
    doc = _write(tmp_path, "d.md", "# D\n\n## Overview\nx\n")
    assert _assert_measurable_nfr.main(["--categories", "performance", str(doc)]) == 2


def test_measurable_nfr_empty_categories_is_bad_input(tmp_path):
    doc = _write(tmp_path, "d.md", _DOC_WITH_NFR)
    assert _assert_measurable_nfr.main(["--categories", " ,", str(doc)]) == 2


def test_measurable_nfr_unreadable_file_is_bad_input(tmp_path):
    assert _assert_measurable_nfr.main(["--categories", "performance", str(tmp_path / "gone.md")]) == 2


def test_no_depth_doc_gate_unreadable_file_is_bad_input(tmp_path):
    assert _assert_no_depth_doc_gate.main([str(tmp_path / "gone.md")]) == 2


def test_no_depth_doc_gate_single_line_branch_flags(tmp_path):
    # shape-1: conditional + depth + emission verb + noun all on one line.
    doc = _write(
        tmp_path,
        "skill.md",
        "Emit the nfr section only if depth is deep, else skip the section.\n",
    )
    assert _assert_no_depth_doc_gate.main([str(doc)]) == 1
