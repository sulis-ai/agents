#!/usr/bin/env python3
"""Aggregator — merges per-tier Agent responses into a single CHECKUP.md.

Invoked by Claude (in the /sulis:code-health session) after deep / audited
mode dispatches its 7 per-tier Agent calls. Each Agent returns a markdown
response per `agent_prompts/_shared-contract.md`; this aggregator merges
them into the founder-mode CHECKUP.

Usage:

    python3 plugins/sulis/skills/code-health/scripts/aggregator.py \\
        --tier-response 1:/path/to/check-build-response.md \\
        --tier-response 2:/path/to/check-security-response.md \\
        ... (one per tier 1..7)
        [--independence-check /path/to/independence-response.md]
        [--scope codebase|pr|auto]
        [--project NAME]
        [--raw]  # emit JSON envelope instead of founder markdown
        [--output CHECKUP.md]

Per-tier responses are markdown files written by Claude after each Agent
call completes. The aggregator parses them per the shared contract format
and produces the final CHECKUP.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


VERDICT_ICONS = {
    "PASS": "✅ Clear",
    "NEEDS_ATTENTION": "🟡 needs attention",
    "FAILED": "❌ failed",
    "NOT_YET_CHECKED": "⏳ not yet checked",
}

TIER_NAMES = {
    1: "Exists",
    2: "Safe",
    3: "Works",
    4: "Survives",
    5: "Understandable",
    6: "Evolves",
    7: "Polished",
}


@dataclass
class TierResponse:
    """Parsed structure from one Agent's markdown response."""
    number: int
    verdict: str  # PASS / NEEDS_ATTENTION / FAILED / NOT_YET_CHECKED
    primitive_coverage: dict[str, str] = field(default_factory=dict)
    findings: list[str] = field(default_factory=list)  # raw lines
    hypotheses: list[str] = field(default_factory=list)  # raw lines
    summary: str = ""


@dataclass
class IndependenceCheckResponse:
    """Parsed structure from the audited-mode Independence Check agent."""
    verdict: str  # CONFIRMED / DIVERGENT / INCONCLUSIVE
    divergence_rows: list[str] = field(default_factory=list)
    missed_findings: list[str] = field(default_factory=list)
    disputed_findings: list[str] = field(default_factory=list)
    score: int = 0
    confidence: str = ""
    recommendation: str = ""


def parse_tier_response(tier_number: int, text: str) -> TierResponse:
    """Parse a per-tier agent response per `_shared-contract.md`."""
    response = TierResponse(number=tier_number, verdict="NOT_YET_CHECKED")

    # Section parser
    sections = _split_h2_sections(text)

    if "Per-tier verdict" in sections:
        verdict_body = sections["Per-tier verdict"].strip()
        first_token = verdict_body.split()[0] if verdict_body.split() else "NOT_YET_CHECKED"
        if first_token in VERDICT_ICONS:
            response.verdict = first_token

    if "Primitive coverage" in sections:
        for row in _parse_table_rows(sections["Primitive coverage"]):
            if len(row) >= 2:
                primitive_id = row[0].strip()
                status = row[1].strip()
                response.primitive_coverage[primitive_id] = status

    if "Findings (capped per MUC-F4)" in sections:
        for line in sections["Findings (capped per MUC-F4)"].splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                response.findings.append(stripped[2:])

    if "Hypotheses (if any)" in sections:
        body = sections["Hypotheses (if any)"].strip()
        if body and "none" not in body.lower():
            response.hypotheses = [line.strip() for line in body.splitlines() if line.strip()]

    if "Founder-mode summary" in sections:
        response.summary = sections["Founder-mode summary"].strip()

    return response


def parse_independence_check(text: str) -> IndependenceCheckResponse:
    """Parse independence-check.md output format."""
    response = IndependenceCheckResponse(verdict="INCONCLUSIVE")
    sections = _split_h2_sections(text)

    if "Independence Check verdict" in sections:
        verdict_body = sections["Independence Check verdict"].strip()
        if verdict_body:
            response.verdict = verdict_body.split()[0]

    if "Per-primitive divergence" in sections:
        for row in _parse_table_rows(sections["Per-primitive divergence"]):
            if any(cell.strip() for cell in row):
                response.divergence_rows.append(" | ".join(row))

    if "Findings the prior agent missed" in sections:
        for line in sections["Findings the prior agent missed"].splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                response.missed_findings.append(stripped[2:])

    if "Findings the prior agent surfaced but Independence Check disagrees with" in sections:
        for line in sections["Findings the prior agent surfaced but Independence Check disagrees with"].splitlines():
            stripped = line.strip()
            if stripped.startswith("- "):
                response.disputed_findings.append(stripped[2:])

    if "Score (per SPIRAL_TEMPLATES.md HEAVY)" in sections:
        body = sections["Score (per SPIRAL_TEMPLATES.md HEAVY)"]
        for line in body.splitlines():
            line = line.strip()
            if line.startswith("- Independence dimension:"):
                match = re.search(r"(\d+)", line)
                if match:
                    response.score = int(match.group(1))
            elif line.startswith("- Confidence:"):
                response.confidence = line.split(":", 1)[1].strip()
            elif line.startswith("- Recommendation:"):
                response.recommendation = line.split(":", 1)[1].strip()

    return response


def _split_h2_sections(text: str) -> dict[str, str]:
    """Split markdown into {h2-heading: body} dict."""
    sections: dict[str, str] = {}
    current_heading: str | None = None
    current_lines: list[str] = []
    for line in text.splitlines():
        h2_match = re.match(r"^##\s+(.+?)\s*$", line)
        if h2_match:
            if current_heading is not None:
                sections[current_heading] = "\n".join(current_lines).strip()
            current_heading = h2_match.group(1).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_heading is not None:
        sections[current_heading] = "\n".join(current_lines).strip()
    return sections


def _parse_table_rows(text: str) -> list[list[str]]:
    """Parse a markdown table; return rows as list of cell-lists (header + separator skipped)."""
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        # Skip separator row (only `-` and `|` and `:`)
        if re.fullmatch(r"[\s\-:|]+", stripped):
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        rows.append(cells)
    # First row is header; drop it
    return rows[1:] if rows else []


def render_founder_markdown(
    tiers: dict[int, TierResponse],
    mode: str,
    scope_desc: str,
    independence: IndependenceCheckResponse | None,
) -> str:
    """Render the CHECKUP per the founder-mode template."""
    lines: list[str] = []
    lines.append(f"🩺 Code Health — {scope_desc}")
    lines.append(f"Mode: {mode}")
    lines.append("")
    lines.append("At a glance:")
    for n in range(1, 8):
        name = TIER_NAMES[n]
        tier = tiers.get(n)
        if tier is None:
            verdict_icon = "⏳ not yet checked"
        else:
            verdict_icon = VERDICT_ICONS.get(tier.verdict, tier.verdict)
            if tier.verdict in {"NEEDS_ATTENTION", "FAILED"}:
                count = len(tier.findings)
                verdict_icon += f" ({count} finding{'s' if count != 1 else ''})"
        lines.append(f"  Tier {n} — {name:18s} {verdict_icon}")
    lines.append("")

    attention = [t for t in tiers.values() if t.verdict in {"NEEDS_ATTENTION", "FAILED"}]
    if attention:
        lines.append("What needs your attention:")
        lines.append("")
        for tier in sorted(attention, key=lambda t: t.number):
            lines.append(f"{VERDICT_ICONS[tier.verdict]} Tier {tier.number} — {TIER_NAMES[tier.number]}")
            if tier.summary:
                lines.append(f"  {tier.summary}")
            for finding in tier.findings[:5]:
                lines.append(f"  - {finding}")
            if len(tier.findings) > 5:
                lines.append(f"  - … and {len(tier.findings) - 5} more")
            lines.append("")

    hypotheses_present = [t for t in tiers.values() if t.hypotheses]
    if hypotheses_present:
        lines.append("Things to verify with the team:")
        lines.append("")
        for tier in sorted(hypotheses_present, key=lambda t: t.number):
            for h in tier.hypotheses:
                lines.append(f"  {h}")
        lines.append("")

    not_yet_checked = [t for t in tiers.values() if t.verdict == "NOT_YET_CHECKED"]
    if not_yet_checked:
        lines.append("What's not yet checked:")
        lines.append("")
        for tier in sorted(not_yet_checked, key=lambda t: t.number):
            reason = tier.summary or "scanner did not run"
            lines.append(f"  Tier {tier.number} — {TIER_NAMES[tier.number]}: {reason}")
        lines.append("")

    if independence:
        lines.append("---")
        lines.append("")
        lines.append("## Independence Check (audited mode)")
        lines.append("")
        lines.append(f"**Verdict:** {independence.verdict}")
        lines.append(f"**Independence dimension score:** {independence.score}/5 ({independence.confidence})")
        lines.append(f"**Recommendation:** {independence.recommendation}")
        lines.append("")
        if independence.divergence_rows:
            lines.append("**Per-primitive divergence:**")
            for row in independence.divergence_rows:
                lines.append(f"- {row}")
            lines.append("")
        if independence.missed_findings:
            lines.append("**Findings the prior agent missed:**")
            for f in independence.missed_findings:
                lines.append(f"- {f}")
            lines.append("")
        if independence.disputed_findings:
            lines.append("**Findings the prior agent surfaced but Independence Check disagrees with:**")
            for f in independence.disputed_findings:
                lines.append(f"- {f}")
            lines.append("")

    return "\n".join(lines)


def render_raw_json(
    tiers: dict[int, TierResponse],
    mode: str,
    scope_desc: str,
    independence: IndependenceCheckResponse | None,
) -> str:
    """Render the operator-mode JSON envelope."""
    payload = {
        "mode": mode,
        "scope": scope_desc,
        "tiers": {},
    }
    for n in range(1, 8):
        tier = tiers.get(n)
        if tier is None:
            payload["tiers"][str(n)] = {"verdict": "NOT_YET_CHECKED", "tier_name": TIER_NAMES[n]}
        else:
            payload["tiers"][str(n)] = {
                "tier_name": TIER_NAMES[n],
                "verdict": tier.verdict,
                "primitive_coverage": tier.primitive_coverage,
                "findings": tier.findings,
                "hypotheses": tier.hypotheses,
                "summary": tier.summary,
            }
    if independence:
        payload["independence_check"] = {
            "verdict": independence.verdict,
            "score": independence.score,
            "confidence": independence.confidence,
            "recommendation": independence.recommendation,
            "divergence_rows": independence.divergence_rows,
            "missed_findings": independence.missed_findings,
            "disputed_findings": independence.disputed_findings,
        }
    return json.dumps(payload, indent=2)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tier-response", action="append", default=[],
        help="N:path — tier number colon path to that tier's agent response markdown. Repeat per tier.",
    )
    parser.add_argument("--independence-check", default=None,
        help="path to independence-check response markdown (audited mode only)")
    parser.add_argument("--scope", default="codebase")
    parser.add_argument("--project", default=None)
    parser.add_argument("--raw", action="store_true", help="JSON envelope output instead of founder markdown")
    parser.add_argument("--output", default=None, help="Write output to this path (defaults to stdout)")
    parser.add_argument("--mode", default="deep", choices=("deep", "audited"),
        help="Invocation mode the aggregator is summarising (cosmetic — affects header only)")

    args = parser.parse_args()

    tiers: dict[int, TierResponse] = {}
    for entry in args.tier_response:
        if ":" not in entry:
            print(f"error: --tier-response expects N:path; got {entry}", file=sys.stderr)
            return 1
        n_str, path = entry.split(":", 1)
        try:
            n = int(n_str)
        except ValueError:
            print(f"error: tier number must be integer; got {n_str}", file=sys.stderr)
            return 1
        try:
            text = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            print(f"error: could not read {path}: {exc}", file=sys.stderr)
            return 1
        tiers[n] = parse_tier_response(n, text)

    independence: IndependenceCheckResponse | None = None
    if args.independence_check:
        try:
            ind_text = Path(args.independence_check).read_text(encoding="utf-8")
            independence = parse_independence_check(ind_text)
        except OSError as exc:
            print(f"error: could not read {args.independence_check}: {exc}", file=sys.stderr)
            return 1

    scope_desc = args.scope
    if args.project:
        scope_desc = f"{args.project} — {scope_desc}"

    if args.raw:
        output = render_raw_json(tiers, args.mode, scope_desc, independence)
    else:
        output = render_founder_markdown(tiers, args.mode, scope_desc, independence)

    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
