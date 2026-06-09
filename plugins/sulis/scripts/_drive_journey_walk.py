#!/usr/bin/env python3
"""Drive the design-stage journey walk (draft-architecture step 8.5) on a fixture.

This is the methodology harness the journey-walk scenarios (SC-06..SC-09, SC-19)
drive. It does NOT re-implement classification policy that the step-8.5 procedure
already owns in prose — it mechanises the same outside-in, hop-by-hop existence
check so the scenarios can assert it deterministically:

  - Walk each Scenario's journey hop-by-hop, in order.
  - Classify every hop EXISTS / planned-WP / GAP.
      * UI / host hop: EXISTS when a component is cited.
      * Tool hop (ADR-003 / FR-09): EXISTS only when BOTH the handler AND its
        ServiceSpec binding are cited. A handler that merely serves — no binding —
        is a GAP (the generalised "looks-built-but-isn't-wired" bar, MUC-02).
      * A hop with a planned WP but no component/binding is planned-WP.
      * A hop with neither is a bare GAP.
  - Write the result to ``--out`` as a ``## Journey Walk`` section: one hop table
    per scenario plus a classification summary.
  - Exit 0 when the walk completes with no bare GAP; exit 1 when a bare GAP blocks
    design completion (fail-closed at the walk level, NFR-S04).

Fixture shape (JSON)::

    {
      "journey": "<human label>",
      "scenarios": [
        {
          "id": "SC-NN",
          "surface": "ui" | "tool",
          "hops": [
            {"name": "...", "component": "path#fn"},          # ui EXISTS
            {"name": "...", "handler": "path#fn",              # tool EXISTS needs
                            "binding": "spec.yaml#op"},        #   handler + binding
            {"name": "...", "planned_wp": "WP-NNN"},           # planned-WP
            {"name": "..."}                                    # bare GAP
          ]
        }
      ]
    }

Stdlib only (boring-code.md): argparse + json + pathlib.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

EXISTS = "exists"
PLANNED = "planned-WP"
GAP = "GAP"


def classify_hop(hop: dict, surface: str) -> tuple[str, str]:
    """Return ``(status, detail)`` for one hop on the given surface.

    ``detail`` is the cited component / handler+binding / planned WP, or empty
    for a bare GAP — it is what the walk table shows in its evidence column.
    """
    if surface == "tool":
        handler = hop.get("handler")
        binding = hop.get("binding")
        if handler and binding:
            return EXISTS, f"{handler} + {binding}"
        if hop.get("planned_wp"):
            return PLANNED, hop["planned_wp"]
        # A handler without a binding serves but is not wired — GAP (FR-09).
        if handler:
            return GAP, f"{handler} (no ServiceSpec binding)"
        return GAP, ""

    # ui / host-rendered surface
    component = hop.get("component")
    if component:
        return EXISTS, component
    if hop.get("planned_wp"):
        return PLANNED, hop["planned_wp"]
    return GAP, ""


def _md_escape(text: str) -> str:
    """Escape the pipe so an evidence string never breaks the Markdown table."""
    return text.replace("|", "\\|")


def walk(fixture: dict, surface: str) -> tuple[str, bool]:
    """Walk every scenario in the fixture for ``surface``.

    Returns ``(section_markdown, has_bare_gap)``. Output is deterministic for an
    unchanged fixture: scenarios and hops are emitted in their declared order and
    no timestamps or environment values leak in (NFR-04).
    """
    journey = fixture.get("journey", "(unnamed journey)")
    scenarios = [s for s in fixture.get("scenarios", []) if s.get("surface") == surface]

    lines: list[str] = [
        "## Journey Walk",
        "",
        f"Journey: {journey}",
        f"Surface: {surface}",
        "",
    ]
    has_bare_gap = False

    if not scenarios:
        lines.append(f"_No `{surface}`-surface scenarios in this journey._")
        return "\n".join(lines) + "\n", has_bare_gap

    for scenario in scenarios:
        sid = scenario.get("id", "(unidentified scenario)")
        lines.append(f"### {sid}")
        lines.append("")
        lines.append("| hop | evidence | status |")
        lines.append("| --- | --- | --- |")
        for hop in scenario.get("hops", []):
            status, detail = classify_hop(hop, surface)
            if status == GAP and not hop.get("planned_wp"):
                has_bare_gap = True
            name = _md_escape(hop.get("name", "(unnamed hop)"))
            lines.append(f"| {name} | {_md_escape(detail) or '—'} | {status} |")
        lines.append("")

    summary = (
        "bare GAP present — design BLOCKED"
        if has_bare_gap
        else "no bare GAP — walk complete"
    )
    lines.append(f"**Classification:** {summary}.")
    return "\n".join(lines) + "\n", has_bare_gap


def load_fixture(path: Path) -> dict:
    """Load a walk fixture. Accepts a file or a directory containing one JSON file."""
    if path.is_dir():
        candidates = sorted(path.glob("*.json"))
        if not candidates:
            raise FileNotFoundError(f"no fixture JSON in directory {path}")
        path = candidates[0]
    elif not path.exists() and path.suffix == "":
        # Allow ``--fixture <name>`` to resolve ``<name>.json``.
        sibling = path.with_suffix(".json")
        if sibling.is_file():
            path = sibling
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Drive the design-stage journey walk on a fixture."
    )
    parser.add_argument(
        "--fixture", required=True, help="path to the walk fixture JSON (or dir / name)"
    )
    parser.add_argument(
        "--surface",
        required=True,
        choices=["ui", "tool"],
        help="which surface walk to drive",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="path the produced design doc (with the walk) lands",
    )
    args = parser.parse_args(argv)

    fixture = load_fixture(Path(args.fixture))
    section, has_bare_gap = walk(fixture, args.surface)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(section, encoding="utf-8")

    # Fail-closed: a bare GAP blocks design completion (NFR-S04).
    return 1 if has_bare_gap else 0


if __name__ == "__main__":
    sys.exit(main())
