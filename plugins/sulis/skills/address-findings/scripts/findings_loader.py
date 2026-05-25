#!/usr/bin/env python3
"""Findings loader for /sulis:address-findings.

Validates input shape, checks staleness, deduplicates against existing WP
files. The skill body uses the JSON envelope this script emits as the
authoritative "what's left to characterise" list.

Three input shapes supported:
- Deep-mode CHECKUP.md path (markdown; parses findings from per-tier sections)
- Single check-* --raw JSON file
- Multiple check-* --raw JSON files (merged into one envelope)

Output: JSON envelope to stdout (default) or --output path:

    {
      "input_paths": [...],
      "input_mtime_max": "2026-05-25T14:30:00Z",
      "stale": false,
      "stale_reason": null,
      "findings": [
        {"signature": "...", "file": "...", "line": N, "severity": "...",
         "rule_id": "...", "message": "...", "source": "code-health::tier-2", "tool": "semgrep"}
      ],
      "duplicate_signatures": [...],   # already in an existing WP's addresses_findings
      "new_signatures": [...],         # NEW since last address-findings run
      "existing_wp_signatures": [...], # full set across all WP files (for context)
      "errors": [...]
    }

Usage:

    python3 plugins/sulis/skills/address-findings/scripts/findings_loader.py \\
        --input <path-or-glob> [--input ...]
        [--project NAME]
        [--repo-root .]
        [--max-age-hours 24]
        [--force-stale]
        [--output PATH]
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class Finding:
    signature: str
    file: str
    line: int
    severity: str
    rule_id: str
    message: str
    source: str  # e.g., "code-health::tier-2::semgrep"
    tool: str = ""


@dataclass
class LoaderEnvelope:
    input_paths: list[str] = field(default_factory=list)
    input_mtime_max: str = ""
    stale: bool = False
    stale_reason: Optional[str] = None
    findings: list[dict] = field(default_factory=list)
    duplicate_signatures: list[str] = field(default_factory=list)
    new_signatures: list[str] = field(default_factory=list)
    existing_wp_signatures: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


# ─── Input loading ───────────────────────────────────────────────────


def load_input_files(input_args: list[str]) -> tuple[list[Path], list[str]]:
    """Resolve --input args (paths or globs) to a sorted unique list."""
    errors: list[str] = []
    paths: set[Path] = set()
    for arg in input_args:
        if any(c in arg for c in ("*", "?", "[")):
            matches = glob.glob(arg, recursive=True)
            if not matches:
                errors.append(f"glob matched no files: {arg}")
                continue
            for m in matches:
                paths.add(Path(m).resolve())
        else:
            p = Path(arg).resolve()
            if not p.is_file():
                errors.append(f"file not found: {arg}")
                continue
            paths.add(p)
    return sorted(paths), errors


def newest_mtime(paths: list[Path]) -> float:
    """Return the most recent mtime across the given paths (0.0 if empty)."""
    return max((p.stat().st_mtime for p in paths), default=0.0)


def check_staleness(mtime: float, max_age_hours: int) -> tuple[bool, Optional[str]]:
    """Return (stale, reason)."""
    if mtime == 0.0:
        return True, "no input files"
    age_hours = (time.time() - mtime) / 3600.0
    if age_hours > max_age_hours:
        return True, f"newest input is {age_hours:.1f}h old (max {max_age_hours}h)"
    return False, None


# ─── Finding extraction ──────────────────────────────────────────────


_FINDING_FIELDS = ("file", "line", "severity", "message")


def extract_findings_from_json(path: Path) -> tuple[list[Finding], list[str]]:
    """Parse a check-* --raw envelope; extract findings."""
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [], [f"could not parse {path}: {exc}"]

    findings: list[Finding] = []
    raw_findings = data.get("findings") or []
    if not isinstance(raw_findings, list):
        return [], [f"{path}: 'findings' is not a list"]

    # Source tag — derived from the envelope's project + path hint
    project = data.get("project", "")
    source_prefix = _infer_source_from_path(path)

    for item in raw_findings:
        if not isinstance(item, dict):
            continue
        sig = _signature_from_item(item, source_prefix)
        if not sig:
            continue
        findings.append(Finding(
            signature=sig,
            file=str(item.get("file", "")),
            line=int(item.get("line", 0) or 0),
            severity=str(item.get("severity", "advisory")),
            rule_id=str(item.get("identifier", item.get("rule_id", ""))),
            message=str(item.get("message", "")),
            source=source_prefix,
            tool=str(item.get("extras", {}).get("tool", "") if isinstance(item.get("extras"), dict) else ""),
        ))
    return findings, errors


def extract_findings_from_checkup(path: Path) -> tuple[list[Finding], list[str]]:
    """Parse a deep-mode CHECKUP.md; extract findings from per-tier bullet lists.

    Best-effort. The deep-mode aggregator's CHECKUP.md format is:

        ## ⚠️ {tier name}
          - {file:line} — {severity} — {message}
          - ...
    """
    errors: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return [], [f"could not read {path}: {exc}"]

    findings: list[Finding] = []
    current_tier = ""
    for line in text.splitlines():
        h2 = re.match(r"^##\s+.*?Tier\s+(\d+)", line)
        if h2:
            current_tier = f"tier-{h2.group(1)}"
            continue
        bullet = re.match(r"^\s*-\s+(.+?):(\d+)\s+—\s+(\S+)\s+—\s+(.+)$", line)
        if bullet and current_tier:
            file, line_no, severity, message = bullet.groups()
            sig = f"code-health::{current_tier}::checkup::{file}::{line_no}"
            findings.append(Finding(
                signature=sig,
                file=file.strip(),
                line=int(line_no),
                severity=severity.strip().lower(),
                rule_id="",
                message=message.strip(),
                source=f"code-health::{current_tier}",
            ))
    return findings, errors


def _signature_from_item(item: dict, source_prefix: str) -> str:
    """Return the stable finding signature (from extras.signature if present)."""
    extras = item.get("extras")
    if isinstance(extras, dict):
        sig = extras.get("signature")
        if sig:
            return str(sig)
    # Synthesise a signature if none present
    rule = item.get("identifier") or item.get("rule_id") or "unknown"
    file = item.get("file", "")
    line = item.get("line", 0)
    return f"{source_prefix}::{rule}::{file}::{line}"


def _infer_source_from_path(path: Path) -> str:
    """Derive a source tag from the JSON envelope's file path."""
    parts = path.parts
    if "check-security" in parts:
        return "code-health::tier-2::semgrep-or-gitleaks-or-trivy"
    if "check-readability" in parts:
        return "code-health::tier-5"
    if "check-reliability" in parts:
        return "code-health::tier-4"
    if "check-maintainability" in parts:
        return "code-health::tier-6"
    if "check-build" in parts:
        return "code-health::tier-1"
    if "check-tests" in parts:
        return "code-health::tier-3"
    if "check-polish" in parts:
        return "code-health::tier-7"
    return "scanner"


# ─── Deduplication against existing WPs ──────────────────────────────


def collect_existing_wp_signatures(repo_root: Path, project: str) -> list[str]:
    """Read every WP file under .architecture/{project}/work-packages/ and
    collect the union of their addresses_findings arrays."""
    wp_dir = repo_root / ".architecture" / project / "work-packages"
    if not wp_dir.is_dir():
        return []

    signatures: set[str] = set()
    for wp_path in wp_dir.glob("WP-*.md"):
        try:
            text = wp_path.read_text(encoding="utf-8")
        except OSError:
            continue
        addresses = _extract_addresses_findings(text)
        signatures.update(addresses)
    return sorted(signatures)


def _extract_addresses_findings(text: str) -> list[str]:
    """Extract addresses_findings list from a WP markdown's frontmatter."""
    fm_match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not fm_match:
        return []
    block = fm_match.group(1)
    out: list[str] = []
    in_addresses = False
    for line in block.splitlines():
        if re.match(r"^addresses_findings:\s*$", line):
            in_addresses = True
            continue
        if in_addresses:
            if line.startswith("  - "):
                out.append(line[4:].strip().strip("'\""))
            elif line and not line.startswith(" "):
                # next top-level key — addresses_findings list ended
                in_addresses = False
        # inline list form: `addresses_findings: [sig1, sig2]`
        inline = re.match(r"^addresses_findings:\s*\[(.+)\]\s*$", line)
        if inline:
            inner = inline.group(1)
            out.extend(s.strip().strip("'\"") for s in inner.split(","))
    return out


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", action="append", default=[],
        help="Path or glob to scanner --raw JSON or deep-mode CHECKUP.md. Repeat for multiple.")
    parser.add_argument("--project", default=None,
        help="Project slug (for dedup against existing WPs). Defaults to repo-root basename.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--max-age-hours", type=int, default=24,
        help="Warn if newest input is older than this. Default 24.")
    parser.add_argument("--force-stale", action="store_true",
        help="Proceed even if inputs are stale.")
    parser.add_argument("--output", default=None,
        help="Write JSON envelope to this path (default: stdout).")
    args = parser.parse_args()

    if not args.input:
        print("error: at least one --input required", file=sys.stderr)
        return 1

    repo_root = Path(args.repo_root).resolve()
    project = args.project or repo_root.name

    envelope = LoaderEnvelope()

    # Resolve input paths
    paths, path_errors = load_input_files(args.input)
    envelope.errors.extend(path_errors)
    envelope.input_paths = [str(p) for p in paths]

    if not paths:
        envelope.errors.append("no input files resolved")
        _emit(envelope, args.output)
        return 1

    # Staleness check
    newest = newest_mtime(paths)
    envelope.input_mtime_max = datetime.fromtimestamp(newest, tz=timezone.utc).isoformat()
    is_stale, reason = check_staleness(newest, args.max_age_hours)
    envelope.stale = is_stale
    envelope.stale_reason = reason
    if is_stale and not args.force_stale:
        envelope.errors.append(
            f"stale input ({reason}); pass --force-stale to proceed or re-run the scanner"
        )
        _emit(envelope, args.output)
        return 2

    # Extract findings from each input
    all_findings: list[Finding] = []
    for p in paths:
        if p.suffix == ".json":
            findings, errors = extract_findings_from_json(p)
        elif p.suffix == ".md":
            findings, errors = extract_findings_from_checkup(p)
        else:
            envelope.errors.append(f"unsupported input format: {p.suffix} ({p})")
            continue
        all_findings.extend(findings)
        envelope.errors.extend(errors)

    # Dedup against existing WPs
    existing_sigs = set(collect_existing_wp_signatures(repo_root, project))
    envelope.existing_wp_signatures = sorted(existing_sigs)

    for f in all_findings:
        if f.signature in existing_sigs:
            envelope.duplicate_signatures.append(f.signature)
        else:
            envelope.new_signatures.append(f.signature)

    envelope.findings = [asdict(f) for f in all_findings]

    _emit(envelope, args.output)
    print(
        f"findings_loader: inputs={len(paths)} findings={len(all_findings)} "
        f"new={len(envelope.new_signatures)} duplicate={len(envelope.duplicate_signatures)} "
        f"stale={envelope.stale}",
        file=sys.stderr,
    )
    return 0


def _emit(envelope: LoaderEnvelope, output: Optional[str]) -> None:
    payload = json.dumps(asdict(envelope), indent=2)
    if output:
        Path(output).write_text(payload, encoding="utf-8")
    else:
        print(payload)


if __name__ == "__main__":
    sys.exit(main())
