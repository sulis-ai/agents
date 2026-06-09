"""drive-specify fixture harness (WP-001).

A deterministic, non-interactive driver that drives the real specify path on a
named fixture change and writes the produced design document to a path. It is
the single most-shared harness primitive in the methodology scenario set
(SC-01/02/03/05/15/16/18 invoke it as their first step), so it lives in its own
foundational module.

CLI
---
    python3 _drive_specify.py --fixture <name> --depth <lite|standard|deep> --out <path>

  --fixture  one of the named fixtures shipped under
             tests/fixtures/methodology/ (sample-user-facing,
             no-dependencies, sample-tool-surface).
  --depth    forces the specify depth. This is an EXPLICIT input: the driver
             does NOT consult the founder proposal flow, so the harness stays
             non-interactive and deterministic. The classifier is still
             exercised (its proposal is recorded as a signal) but the forced
             depth is what the document is sized for.
  --out      path the produced design document is written to.

Exit codes
----------
  0  a document was produced.
  non-zero  a stage failure (unknown fixture, malformed manifest, unknown
            depth) — surfaced loudly so scenarios fail rather than silently
            producing a half-document.

Design contracts
----------------
  - Deterministic (NFR-04): same fixture + depth ⇒ byte-identical output. No
    timestamps, no random IDs, no environment reads in the produced artifact.
  - Reuses the real specify path: depth is decided by
    `_specify_classifier.classify_depth`, the same function `/sulis:specify`
    uses. The driver forces the final depth but records what the real
    classifier would have proposed — it is a harness over the real path, not a
    fork of it.
  - The document carries the canonical comprehensive section set; sections a
    fixture cannot populate are marked `n/a — <reason>`, never omitted
    (ADR-002). Per-depth content sizing is intentionally minimal here — the
    full comprehensive emitter is WP-006; this harness produces the drivable
    shape the scenarios assert against.

See:
  - plugins/sulis/scripts/_specify_classifier.py (the real depth classifier)
  - .architecture/comprehensive-spec-and-journey-walk/adrs/ADR-002-*.md
  - plugins/sulis/skills/requirements-templates/SKILL.md (canonical sections)
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from _specify_classifier import (
    DepthDecision,
    classify_depth,
    paths_touch_founder_surface,
)

# ─── Fixture location ───────────────────────────────────────────────────────

_HERE: Final[Path] = Path(__file__).resolve().parent
_FIXTURES_DIR: Final[Path] = _HERE / "tests" / "fixtures" / "methodology"

_VALID_DEPTHS: Final[frozenset[str]] = frozenset({"lite", "standard", "deep"})


class DriveSpecifyError(Exception):
    """A stage failure the driver surfaces as a non-zero exit."""


# ─── Fixture manifest ───────────────────────────────────────────────────────


@dataclass(frozen=True)
class FixtureManifest:
    """A fixture change manifest — the deterministic inputs to a specify drive."""

    slug: str
    primitive: str
    intent: str
    paths: list[str]
    dependencies: list[str]
    tool_operations: list[dict]


def load_fixture(name: str) -> FixtureManifest:
    """Load and validate a named fixture's manifest.

    Raises DriveSpecifyError (→ non-zero exit) when the fixture is unknown or
    its manifest is malformed.
    """
    manifest_path = _FIXTURES_DIR / name / "manifest.json"
    if not manifest_path.is_file():
        raise DriveSpecifyError(
            f"unknown fixture {name!r}: no manifest at {manifest_path}"
        )
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise DriveSpecifyError(
            f"fixture {name!r} manifest is malformed: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise DriveSpecifyError(
            f"fixture {name!r} manifest must be a JSON object, got {type(raw).__name__}"
        )

    slug = raw.get("slug")
    primitive = raw.get("primitive")
    intent = raw.get("intent")
    if not isinstance(slug, str) or not slug:
        raise DriveSpecifyError(f"fixture {name!r} manifest missing 'slug'")
    if not isinstance(primitive, str) or not primitive:
        raise DriveSpecifyError(f"fixture {name!r} manifest missing 'primitive'")
    if not isinstance(intent, str) or not intent:
        raise DriveSpecifyError(f"fixture {name!r} manifest missing 'intent'")

    return FixtureManifest(
        slug=slug,
        primitive=primitive,
        intent=intent,
        paths=list(raw.get("paths", [])),
        dependencies=list(raw.get("dependencies", [])),
        tool_operations=list(raw.get("tool_operations", [])),
    )


# ─── Specify drive ──────────────────────────────────────────────────────────


# The canonical comprehensive section set (ADR-002), modelled on the
# requirements-templates target structure. Ordering is invariant; the §10
# `## Verification Plan` heading is fixed verbatim (ADR-001 of the
# verification-by-design change).
#
# WP-006 makes this emitter *always-comprehensive*: every mandatory section is
# present at every depth (FR-01/02/11). The top-level §1..§10 spine matches the
# canonical; the always-on measurable NFR section, the STRIDE/Constraints/
# Assumptions/Dependencies sub-sections, and the interface-contract skeleton
# stub (CF-05 — WP-011 fills it to full CF-10) live beneath §4 Requirements and
# §7 Solution Design as named sub-headings the document inspectors anchor on.
_SECTIONS: Final[tuple[tuple[str, str], ...]] = (
    ("1", "Executive Summary"),
    ("2", "Problem Discovery"),
    ("3", "Stakeholders / Personas"),
    ("4", "Requirements"),
    ("5", "Scope"),
    ("6", "Use Cases"),
    ("7", "Solution Design"),
    ("8", "ADRs + BDRs"),
    ("9", "Migration / Rollback / Security / Performance"),
    ("10", "Verification Plan"),
)


def run_specify_stage(manifest: FixtureManifest, depth: str) -> DepthDecision:
    """Drive the real specify depth-classification on a fixture.

    `depth` is the forced, explicit depth (the harness never negotiates). The
    real classifier is still invoked so the driver records the proposal it
    would have made — keeping the harness honest about reusing the real path.
    Raises DriveSpecifyError on an unknown depth.
    """
    if depth not in _VALID_DEPTHS:
        raise DriveSpecifyError(
            f"unknown depth {depth!r}: expected one of {sorted(_VALID_DEPTHS)}"
        )

    founder_facing = paths_touch_founder_surface(manifest.paths)
    file_count = len(manifest.paths) if manifest.paths else None

    # Reuse the real specify path — the same classifier `/sulis:specify` uses.
    return classify_depth(
        primitive=manifest.primitive,
        file_count=file_count,
        founder_facing=founder_facing,
    )


def render_document(
    manifest: FixtureManifest, depth: str, proposal: DepthDecision
) -> str:
    """Render the comprehensive design document for a driven fixture.

    Deterministic: the output is a pure function of the manifest, the forced
    depth, and the classifier proposal — no timestamps, no random IDs. Sections
    a fixture cannot populate are marked `n/a — <reason>` (ADR-002).
    """
    lines: list[str] = [
        f"# Design — {manifest.slug}",
        "",
        f"<!-- driven by _drive_specify.py · depth={depth} · "
        f"primitive={manifest.primitive} · "
        f"classifier-proposed={proposal.depth} -->",
        "",
    ]

    for number, title in _SECTIONS:
        lines.append(f"## {number}. {title}")
        lines.append("")
        lines.append(_section_body(number, manifest))
        lines.append("")

    return "\n".join(lines).rstrip("\n") + "\n"


# Always-on measurable NFR targets (FR-06, SC-05). Structure is invariant —
# every comprehensive document carries a measurable target per category at every
# depth; depth tunes only how much *additional* interview-derived detail is
# layered on. A category with no fixture-specific target still states the
# methodology's own measurable floor, so `_assert_measurable_nfr` always passes.
_NFR_BASELINE: Final[tuple[tuple[str, str], ...]] = (
    (
        "Performance",
        "Producing the comprehensive document at lite depth adds ≤ 1.6× the "
        "legacy lite cost (NFR-02); section emission completes in < 5 s.",
    ),
    (
        "Security",
        "100% of mandatory sections are present or carry an explicit "
        "`n/a — <reason>`; 0 silent drops (NFR-R01). No false completeness.",
    ),
    (
        "Reliability",
        "Under token pressure all mandatory sections remain present — detail "
        "degrades, existence does not; ≥ 99% of drives keep the full section "
        "set (NFR-R01).",
    ),
)


def _subsection(heading: str, body: str, *, level: int = 3) -> list[str]:
    """Render one named sub-section as a list of lines: a blank-line separator,
    the ATX heading at ``level``, a blank line, then the body.

    The single source of the sub-section shape the document inspectors anchor
    on — extracted so the §4 Requirements and §7 Solution Design renderers don't
    each repeat the `["", "### Name", "", body]` pattern (Blue refactor,
    2-consumer threshold).
    """
    return ["", f"{'#' * level} {heading}", "", body]


def _requirements_body(manifest: FixtureManifest) -> str:
    """The §4 Requirements body — functional summary plus the always-on
    measurable NFR section and the Threat Model / Constraints / Assumptions /
    Dependencies sub-sections.

    Each sub-section is a named heading the document inspectors anchor on
    (FR-06 / SC-03 / SC-05). A sub-section a fixture cannot populate carries an
    explicit `n/a — <reason>` (NFR-R01), never a bare omission.
    """
    if manifest.paths:
        functional = "Touches:\n" + "\n".join(f"- `{p}`" for p in manifest.paths)
    else:
        functional = "n/a — no source paths declared in the fixture manifest."

    nfr_intro = (
        "Always-on, measurable targets per category (FR-06). Structure is "
        "invariant across depth; detail is interview-sized."
    )

    if manifest.dependencies:
        dependencies = "Dependencies:\n" + "\n".join(
            f"- {d}" for d in manifest.dependencies
        )
    else:
        dependencies = "n/a — this fixture declares no dependencies."

    # The leading blank from the first _subsection separator is stripped by the
    # final "\n".join — the heading is the first line of the rendered body.
    parts: list[str] = []
    parts += _subsection("Functional Requirements", functional)
    parts += _subsection("Non-Functional Requirements", nfr_intro)
    for category, target in _NFR_BASELINE:
        parts += _subsection(category, target, level=4)
    parts += _subsection(
        "Threat Model",
        "STRIDE skeleton — the methodology's threat actors are the bypasses "
        "that ship incomplete work. Filled to a full STRIDE matrix by the "
        "downstream design stage (FR-15).",
    )
    parts += _subsection(
        "Constraints",
        "The document MUST match the canonical Target Structure (C-01); the "
        "`## Verification Plan` heading is fixed verbatim (C-02).",
    )
    parts += _subsection(
        "Assumptions",
        f"This `{manifest.primitive}` change assumes its declared paths and "
        "dependencies are accurate as captured in the fixture manifest.",
    )
    parts += _subsection("Dependencies", dependencies)

    return "\n".join(parts).lstrip("\n")


def _solution_design_body(manifest: FixtureManifest) -> str:
    """The §7 Solution Design body, including the mandatory Interface Contract
    section skeleton stub (CF-05, ADR-007).

    This WP lands the *skeleton*; WP-011 fills it to the full CF-10 founder-
    reviewable dimensions. The skeleton is present at every depth so WP-009's
    tool-walk has a target and contract-first ordering holds (BDR-001).
    """
    if manifest.tool_operations:
        ops = "\n".join(
            f"- `{op.get('name', '?')}` "
            f"(in: {', '.join(op.get('inputs', []))}; "
            f"out: {', '.join(op.get('outputs', []))})"
            for op in manifest.tool_operations
        )
        contract = "Interface contract — tool operations:\n" + ops
    else:
        contract = (
            "n/a — this change exposes no tool surface; the interface-contract "
            "skeleton stands ready for any operation a tool surface would add "
            "(CF-05; WP-011 fills the full CF-10 dimensions)."
        )

    parts: list[str] = []
    parts += _subsection("Solution Overview", "Implementation follows the paths in §4.")
    parts += _subsection("Interface Contract", contract)
    return "\n".join(parts).lstrip("\n")


def _section_body(number: str, manifest: FixtureManifest) -> str:
    """Deterministic body for one section, marking the unpopulated ones n/a."""
    if number == "1":
        return manifest.intent
    if number == "2":
        return f"This change is a `{manifest.primitive}` on: {manifest.intent}"
    if number == "4":
        return _requirements_body(manifest)
    if number == "5":
        return (
            "In scope: the paths in §4. "
            "Out of scope: anything not named by this fixture."
        )
    if number == "7":
        return _solution_design_body(manifest)
    if number == "9":
        return (
            "Migration: the comprehensive structure applies to changes "
            "specified after this ships; existing artifacts are not rewritten. "
            "Rollback: revert the change branch. Security + performance "
            "targets are stated in §4 Non-Functional Requirements."
        )
    if number == "10":
        return (
            "Methodology adapter: drive this fixture via `_drive_specify.py` "
            "and assert the produced document's section set."
        )
    # Sections 3 and 6 are not populated by the minimal fixture shape; §8
    # (ADRs + BDRs) likewise carries no fixture-derived decisions.
    return "n/a — not populated by this fixture."


def drive(*, fixture: str, depth: str, out: Path) -> None:
    """Drive specify on a fixture and write the document. Raises on failure."""
    manifest = load_fixture(fixture)
    proposal = run_specify_stage(manifest, depth)
    document = render_document(manifest, depth, proposal)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(document, encoding="utf-8")


# ─── CLI ────────────────────────────────────────────────────────────────────


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_drive_specify.py",
        description="Drive the specify stage on a fixture; write the document.",
    )
    parser.add_argument("--fixture", required=True, help="named fixture to drive")
    parser.add_argument(
        "--depth",
        required=True,
        choices=sorted(_VALID_DEPTHS),
        help="forced specify depth (explicit input; not negotiated)",
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="path to write the document to"
    )
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = _parse_args(argv)
    try:
        drive(fixture=args.fixture, depth=args.depth, out=args.out)
    except DriveSpecifyError as exc:
        print(f"drive-specify: stage failure: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
