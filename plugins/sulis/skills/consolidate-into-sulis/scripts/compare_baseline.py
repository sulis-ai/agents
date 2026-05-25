#!/usr/bin/env python3
"""Compare two /sulis:code-health --raw JSON outputs (baseline vs final).

Classifies each finding in the final report as NEW, PRE-EXISTING, or RESOLVED
relative to the baseline. Emits a Markdown comparison report to stdout.

Usage:
  python3 plugins/sulis/skills/consolidate-into-sulis/scripts/compare_baseline.py \\
    --baseline runs/{source}-{date}/code-health-baseline.json \\
    --final    runs/{source}-{date}/code-health-final.json

Finding signatures are derived from {file, line (or rule), severity} when those
fields are present, falling back to a stable JSON representation of the finding
when not. This is best-effort — the exact /sulis:code-health JSON shape may
evolve, so future versions may need to update the signature function.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any


def finding_signature(finding: dict) -> str:
    """Produce a stable signature for a single finding.

    Priority order:
    - file + line + rule (most stable)
    - file + rule
    - hash of stable JSON dump
    """
    file = finding.get("file") or finding.get("path") or ""
    line = finding.get("line") or finding.get("lineno") or ""
    rule = finding.get("rule") or finding.get("rule_id") or finding.get("check") or ""

    if file and rule:
        return f"{file}::{line}::{rule}"

    # Fall back to a hash of stable JSON
    blob = json.dumps(finding, sort_keys=True, default=str)
    return "hash::" + hashlib.sha1(blob.encode()).hexdigest()[:12]


def extract_findings(report: dict) -> list[dict]:
    """Pull a flat list of findings from a code-health JSON report.

    Handles the common shapes:
    - report["findings"] — flat list
    - report["tiers"][N]["findings"] — per-tier
    - report["tiers"][N]["primitives"][M]["findings"] — per-primitive
    """
    findings: list[dict] = []

    if isinstance(report.get("findings"), list):
        findings.extend(report["findings"])

    tiers = report.get("tiers") or []
    if isinstance(tiers, list):
        for tier in tiers:
            if isinstance(tier, dict):
                if isinstance(tier.get("findings"), list):
                    findings.extend(tier["findings"])
                prims = tier.get("primitives") or []
                if isinstance(prims, list):
                    for prim in prims:
                        if isinstance(prim, dict) and isinstance(prim.get("findings"), list):
                            findings.extend(prim["findings"])
    elif isinstance(tiers, dict):
        for _, tier in tiers.items():
            if isinstance(tier, dict) and isinstance(tier.get("findings"), list):
                findings.extend(tier["findings"])

    return findings


def classify(baseline: list[dict], final: list[dict]) -> dict[str, list[dict]]:
    """Return dict with NEW / PRE-EXISTING / RESOLVED lists."""
    baseline_sigs = {finding_signature(f): f for f in baseline}
    final_sigs = {finding_signature(f): f for f in final}

    new_keys = set(final_sigs) - set(baseline_sigs)
    resolved_keys = set(baseline_sigs) - set(final_sigs)
    preexisting_keys = set(final_sigs) & set(baseline_sigs)

    return {
        "new": [final_sigs[k] for k in sorted(new_keys)],
        "pre_existing": [final_sigs[k] for k in sorted(preexisting_keys)],
        "resolved": [baseline_sigs[k] for k in sorted(resolved_keys)],
    }


def finding_brief(f: dict) -> str:
    """One-line summary of a finding for the Markdown table."""
    file = f.get("file") or f.get("path") or "?"
    line = f.get("line") or f.get("lineno") or ""
    rule = f.get("rule") or f.get("rule_id") or f.get("check") or "?"
    severity = f.get("severity") or f.get("level") or ""
    suffix = f":{line}" if line else ""
    sev = f" [{severity}]" if severity else ""
    return f"`{file}{suffix}` — `{rule}`{sev}"


def emit_markdown(classified: dict[str, list[dict]], baseline_path: str, final_path: str) -> str:
    out: list[str] = []
    out.append("# Code-health comparison — baseline vs final")
    out.append("")
    out.append(f"**Baseline:** `{baseline_path}`")
    out.append(f"**Final:** `{final_path}`")
    out.append("")
    out.append("## Verdict")
    out.append("")
    new_count = len(classified["new"])
    if new_count == 0:
        out.append("**PASS** — no NEW findings introduced by the consolidation.")
    else:
        out.append(f"**REGRESSION** — {new_count} NEW finding(s) introduced. Investigate and fix forward.")
    out.append("")

    out.append("## Counts")
    out.append("")
    out.append(f"- NEW (introduced by consolidation): **{len(classified['new'])}**")
    out.append(f"- PRE-EXISTING (also in baseline): **{len(classified['pre_existing'])}**")
    out.append(f"- RESOLVED (in baseline, gone in final): **{len(classified['resolved'])}**")
    out.append("")

    # NEW findings — the load-bearing list
    out.append("## NEW findings (consolidation-attributed)")
    out.append("")
    if not classified["new"]:
        out.append("None.")
        out.append("")
    else:
        out.append("Investigate each. Classify as **regression-grade** (fix forward in Commit 6)")
        out.append("or **pre-existing in disguise** (document, don't gate). See")
        out.append("`references/code-health-gating.md` for the rubric.")
        out.append("")
        for f in classified["new"]:
            out.append(f"- {finding_brief(f)}")
        out.append("")

    # RESOLVED
    out.append("## RESOLVED findings (improvement from consolidation)")
    out.append("")
    if not classified["resolved"]:
        out.append("None.")
        out.append("")
    else:
        for f in classified["resolved"]:
            out.append(f"- {finding_brief(f)}")
        out.append("")

    # PRE-EXISTING (collapsed)
    out.append("## PRE-EXISTING findings (carried over)")
    out.append("")
    out.append(f"{len(classified['pre_existing'])} pre-existing finding(s) carried over from baseline.")
    out.append("These are unrelated to the consolidation; not gating.")
    out.append("")

    return "\n".join(out)


def load_report(path: Path) -> list[dict]:
    if not path.is_file():
        print(f"Error: file not found: {path}", file=sys.stderr)
        return []
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {path}: {e}", file=sys.stderr)
        return []
    return extract_findings(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--final", required=True, type=Path)
    args = parser.parse_args()

    baseline = load_report(args.baseline)
    final = load_report(args.final)

    classified = classify(baseline, final)
    sys.stdout.write(emit_markdown(classified, str(args.baseline), str(args.final)))
    sys.stdout.write("\n")

    return 0 if not classified["new"] else 2


if __name__ == "__main__":
    sys.exit(main())
