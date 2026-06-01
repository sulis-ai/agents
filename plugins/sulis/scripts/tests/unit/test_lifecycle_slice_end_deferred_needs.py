"""Structural verification for CH-01KT2B (verification-by-design) WP-005.

The change extends the slice-end review (hosted in
`plugins/sulis/references/lifecycle.md` per Pre-Work Prior-Art
resolution) with a deferred-needs scan: at slice-end, every WP's
`verification:` frontmatter `deferred-to-follow-on:` value plus every
SRD's "Infrastructure needs surfaced (deferred)" entry are tallied
by canonical need identifier (FR-011); identifiers flagged by 2+
designs auto-draft a follow-on change (FR-012); singletons are
surfaced to the founder for explicit defer-or-draft disposition.
The scan is idempotent (ADR-005).

This module pins the new slice-end prose in place so a future heading
or content drift surfaces as a failing test rather than a silent
methodology regression. Stdlib + pytest only, Python 3.11-safe.
Resolves paths relative to this test file so the suite is location-
stable inside any worktree.

Four assertions:

  1. lifecycle.md contains a deferred-needs scan section.
  2. The section cites FR-011 (canonical identifier) + FR-012
     (auto-draft trigger) + ADR-005 (timing).
  3. The section names the 2+ threshold for auto-draft AND the
     singleton-surface behaviour.
  4. The section references the FR-015 behavioural test ledger as
     an input the scan reads.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# tests/unit/ → tests/ → scripts/ → sulis/ → plugins/sulis/ → plugins/
_PLUGINS_SULIS = Path(__file__).resolve().parents[3]
_LIFECYCLE = _PLUGINS_SULIS / "references" / "lifecycle.md"


@pytest.fixture(scope="module")
def lifecycle_text() -> str:
    """The live lifecycle.md content as a single string."""
    assert _LIFECYCLE.is_file(), f"missing lifecycle.md at {_LIFECYCLE}"
    return _LIFECYCLE.read_text(encoding="utf-8")


def test_slice_end_scan_section_present(lifecycle_text: str) -> None:
    """lifecycle.md contains a deferred-needs scan section.

    Without a discoverable heading naming the scan, the new
    behaviour lives as ambient prose and a future reader has to
    grep to find it. The section heading also pins the seam the
    scan owns: deferred-needs aggregation across the slice.
    """
    # Match a heading or bold lead-in that includes BOTH the
    # "deferred" cue AND the "slice-end" or "scan" cue.
    pattern = re.compile(
        r"(?:slice-end.{0,80}deferred|deferred.{0,80}(?:scan|slice-end)|"
        r"deferred-needs\s+scan)",
        re.IGNORECASE | re.DOTALL,
    )
    assert pattern.search(lifecycle_text), (
        "lifecycle.md is missing a slice-end deferred-needs scan "
        "section. Expected a heading like 'Slice-end deferred-needs "
        "scan' so the scan behaviour is discoverable. Without the "
        "section, ADR-005's auto-draft trigger has no implementation "
        "anchor in the lifecycle reference."
    )


def test_slice_end_section_cites_canonical_anchors(lifecycle_text: str) -> None:
    """The slice-end scan section cites FR-011, FR-012, and ADR-005.

    Each anchor pins a piece of the contract:
      - FR-011 — canonical need identifier (what the scan tallies on).
      - FR-012 — auto-draft trigger (the 2+ threshold rule).
      - ADR-005 — timing decision (fire at slice-end, not real-time).
    The section MUST cite all three so a reader following the trail
    finds the authoritative source for each rule.
    """
    missing: list[str] = []
    for anchor in ("FR-011", "FR-012", "ADR-005"):
        if not re.search(anchor, lifecycle_text):
            missing.append(anchor)
    assert not missing, (
        "lifecycle.md slice-end deferred-needs section is missing "
        f"required citations: {missing}. FR-011 defines the canonical "
        "need identifier the scan tallies on; FR-012 defines the "
        "auto-draft trigger; ADR-005 defines the slice-end (not "
        "real-time) timing. All three MUST be cited."
    )


def test_slice_end_section_names_threshold_and_singleton(
    lifecycle_text: str,
) -> None:
    """The scan section names the 2+ threshold AND singleton-surface.

    ADR-005 defines two behaviours:
      - ≥2 designs flag the same identifier → auto-draft a follow-on.
      - Exactly 1 design flags an identifier → surface to founder
        for defer-or-draft disposition.
    Both MUST appear in the lifecycle prose so executors don't
    silently drop singletons.
    """
    has_threshold = re.search(
        r"(?:2\+|two\s+or\s+more|≥\s*2|>=\s*2|at\s+least\s+2)",
        lifecycle_text,
        re.IGNORECASE,
    )
    assert has_threshold, (
        "lifecycle.md slice-end deferred-needs section is missing the "
        "2+ threshold for auto-draft. Expected wording like '2+ "
        "designs', '≥ 2 designs', or 'at least two designs'. Without "
        "the explicit threshold, the auto-draft trigger is "
        "underspecified."
    )

    has_singleton = re.search(
        r"singleton|exactly\s+one\s+design|flagged\s+by\s+exactly\s+one|"
        r"one-line.{0,80}defer",
        lifecycle_text,
        re.IGNORECASE,
    )
    assert has_singleton, (
        "lifecycle.md slice-end deferred-needs section is missing the "
        "singleton-surface behaviour. Expected wording like "
        "'singletons' or 'flagged by exactly one design'. Without "
        "the singleton clause, founder-disposition for one-off "
        "deferrals is undefined."
    )


def test_slice_end_section_references_behavioural_ledger(
    lifecycle_text: str,
) -> None:
    """The scan section references the FR-015 behavioural test ledger.

    The ledger (per FR-015, default location
    `.specifications/{change}/verification-ledger.md`) is the
    machine-readable cross-check input the slice-end scan reads to
    flag orphan rows (a claimed test artifact with neither artifact
    nor deferred-to-follow-on). The reference MUST appear so the
    cross-check is discoverable.
    """
    pattern = re.compile(
        r"(?:FR-015|verification-ledger|behavioural\s+test\s+ledger)",
        re.IGNORECASE,
    )
    assert pattern.search(lifecycle_text), (
        "lifecycle.md slice-end deferred-needs section is missing a "
        "reference to the FR-015 behavioural test ledger. The scan "
        "MUST cite the ledger (by FR-015 anchor, by filename, or by "
        "'behavioural test ledger') as the cross-check input. "
        "Without the reference, orphan-row detection is undocumented."
    )
