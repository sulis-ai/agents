#!/usr/bin/env python3
"""_assert_flow_scenario_map.py — assert every use-case flow maps to a covering
scenario (WP-009, SC-10 / FR-10).

A use case has main / alternate / exception flows; each must be the source of at
least one verifiable scenario, or be explicitly recorded out-of-scope. This
inspector reads a flow-map fixture and exits 0 iff every enumerated flow is
covered (by a scenario or an out-of-scope record), naming the uncovered flows
otherwise. Fail-closed (NFR-S04): an absent mapping is a gap, never silently
passed.

Fixture shape (JSON)::

    {
      "flows": ["UC-01:main", "UC-01:2a", "UC-01:5a"],
      "scenarios": [
        {"id": "SC-01", "covers": ["UC-01:main"]},
        {"id": "SC-02", "covers": ["UC-01:2a"]}
      ],
      "out_of_scope": ["UC-01:5a"]        # optional — recorded exemptions
    }

Usage:
    _assert_flow_scenario_map.py <flow-map.json>

Exit codes:
  0 — every flow has a covering scenario or a recorded out-of-scope entry
  1 — at least one flow is uncovered (named on stderr)
  2 — bad input (file unreadable / malformed)

Pure inspector — reads one JSON file, no other I/O. Stdlib only. 3.11-safe.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def uncovered_flows(spec: dict) -> list[str]:
    """Return the flows with neither a covering scenario nor an out-of-scope record.

    Order-preserving over the declared ``flows`` list so the report is
    deterministic for an unchanged fixture (NFR-04).
    """
    flows = list(spec.get("flows", []))
    out_of_scope = set(spec.get("out_of_scope", []))
    covered: set[str] = set()
    for scenario in spec.get("scenarios", []):
        for flow in scenario.get("covers", []):
            covered.add(flow)
    return [f for f in flows if f not in covered and f not in out_of_scope]


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_assert_flow_scenario_map.py",
        description="Exit 0 iff every UC flow maps to >=1 scenario (or is out-of-scope).",
    )
    parser.add_argument("flow_map", help="path to the flow-map JSON")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        spec = json.loads(Path(args.flow_map).read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"error: cannot read {args.flow_map}: {exc}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"error: {args.flow_map} is not valid JSON: {exc}", file=sys.stderr)
        return 2

    missing = uncovered_flows(spec)
    if missing:
        print(
            f"{args.flow_map}: uncovered flow(s) — no scenario and no out-of-scope "
            f"record: {', '.join(missing)}",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
