#!/usr/bin/env python3
"""_drive_scenario.py — drive a single authored scenario, recording an undrivable
tool scenario as DEFERRED rather than skipping it (WP-009, SC-11 / NFR-R02).

The two-surface walk derives a scenario per UC flow on both surfaces. A tool
scenario may be undrivable in the current environment (no dev-tier endpoint /
credential — the ``tool-drive-sandbox`` deferred infrastructure need, §10 of the
design). The discipline this script enforces: an undrivable scenario is
**recorded deferred** — a visible deferred record with a distinct exit code —
never a silent skip and never a fake green. This keeps "deferred" telling apart
from "observed" (passed) and "failed".

Scenario fixture shape (JSON)::

    {
      "id": "SC-NN",
      "surface": "ui" | "tool",
      "drivable": true | false,
      "deferred_need": "tool-drive-sandbox: dev-tier endpoint + credential"
    }

Usage:
    _drive_scenario.py --scenario <scenario.json> --out <record.json>

Exit codes:
  0 — the scenario was drivable; an ``observed`` record is written
  3 — the scenario was undrivable; a ``deferred`` record is written (NFR-R02)
  2 — bad input (file unreadable / malformed / missing required field)

The output record is a single JSON object with a ``disposition`` of ``observed``
or ``deferred`` — the brain/coverage layer reads it; a deferred disposition is
never countable as a passing TestResult.

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RC_OBSERVED = 0
RC_BAD_INPUT = 2
RC_DEFERRED = 3


def disposition_for(scenario: dict) -> dict:
    """Return the result record for a scenario.

    A scenario with ``drivable`` falsey is recorded ``deferred`` with its stated
    ``deferred_need``; otherwise it is ``observed``. The record always names the
    scenario so a deferred entry is traceable, never anonymous (NFR-R02).
    """
    sid = scenario.get("id", "(unidentified scenario)")
    surface = scenario.get("surface", "tool")
    if scenario.get("drivable"):
        return {"scenario": sid, "surface": surface, "disposition": "observed"}
    return {
        "scenario": sid,
        "surface": surface,
        "disposition": "deferred",
        "deferred_need": scenario.get(
            "deferred_need", "undrivable in this environment (no driver/sandbox)"
        ),
    }


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="_drive_scenario.py",
        description="Drive one scenario; record an undrivable tool scenario deferred.",
    )
    parser.add_argument("--scenario", required=True, help="path to the scenario JSON")
    parser.add_argument("--out", required=True, help="path the result record lands")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(sys.argv[1:] if argv is None else argv)
    try:
        scenario = json.loads(Path(args.scenario).read_text(encoding="utf-8"))
    except OSError as exc:
        print(f"error: cannot read {args.scenario}: {exc}", file=sys.stderr)
        return RC_BAD_INPUT
    except json.JSONDecodeError as exc:
        print(f"error: {args.scenario} is not valid JSON: {exc}", file=sys.stderr)
        return RC_BAD_INPUT

    record = disposition_for(scenario)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    if record["disposition"] == "deferred":
        print(
            f"{record['scenario']}: DEFERRED — {record['deferred_need']} "
            "(recorded, not skipped; NFR-R02)",
            file=sys.stderr,
        )
        return RC_DEFERRED
    return RC_OBSERVED


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
