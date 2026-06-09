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


def _section_body(number: str, manifest: FixtureManifest) -> str:
    """Deterministic body for one section, marking the unpopulated ones n/a."""
    if number == "1":
        return manifest.intent
    if number == "2":
        return f"This change is a `{manifest.primitive}` on: {manifest.intent}"
    if number == "4":
        if manifest.paths:
            return "Touches:\n" + "\n".join(f"- `{p}`" for p in manifest.paths)
        return "n/a — no source paths declared in the fixture manifest."
    if number == "5":
        return (
            "In scope: the paths in §4. "
            "Out of scope: anything not named by this fixture."
        )
    if number == "7":
        if manifest.tool_operations:
            ops = "\n".join(
                f"- `{op.get('name', '?')}` "
                f"(in: {', '.join(op.get('inputs', []))}; "
                f"out: {', '.join(op.get('outputs', []))})"
                for op in manifest.tool_operations
            )
            return "Interface contract — tool operations:\n" + ops
        return "Implementation follows the paths in §4."
    if number == "9":
        if manifest.dependencies:
            return "Dependencies:\n" + "\n".join(
                f"- {d}" for d in manifest.dependencies
            )
        return "n/a — this fixture declares no dependencies."
    if number == "10":
        return (
            "Methodology adapter: drive this fixture via `_drive_specify.py` "
            "and assert the produced document's section set."
        )
    # Sections 3, 6, 8 are not populated by the minimal fixture shape.
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
