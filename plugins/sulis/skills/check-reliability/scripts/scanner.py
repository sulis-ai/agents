#!/usr/bin/env python3
"""Reliability pattern scanner.

Tier-4 regression detection: did the project introduce a missing
timeout, silent-except, or broad-except? Pattern-based; low FP rate.

First skill to USE the new _lib/ shared helpers (baseline, allowlist,
scope). Future skills should adopt the same import pattern.

Usage:

    python3 scanner.py [--repo-root .] [--raw] [--update-baseline]

Exit codes:
- 0 = success
- 2 = filesystem / git error
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# ─── _lib/ helper bootstrap (canonical pattern per add-skill v0.6.0) ─


sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _lib import allowlist, baseline, scope  # noqa: E402


# ─── Source-file selection ──────────────────────────────────────────


SCANNABLE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".go"}

SKIP_PATH_PATTERNS = [
    re.compile(r"(^|/)tests?/"),
    re.compile(r"(^|/)__tests__/"),
    re.compile(r"_test\.go$"),
    re.compile(r"\.test\.(js|ts|jsx|tsx)$"),
    re.compile(r"\.spec\.(js|ts|jsx|tsx)$"),
    re.compile(r"(^|/)fixtures?/"),
    re.compile(r"(^|/)testdata/"),
    re.compile(r"(^|/)mocks?/"),
    re.compile(r"(^|/)docs/examples?/"),
    re.compile(r"(^|/)\.checkup/"),
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)\.git/"),
    re.compile(r"(^|/)vendor/"),
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)build/"),
]


def is_skipped_path(path: str) -> bool:
    return any(p.search(path) for p in SKIP_PATH_PATTERNS)


# ─── Pattern catalogue ──────────────────────────────────────────────


@dataclass
class Finding:
    pattern_name: str
    category: str  # "missing-timeout" | "silent-except" | "broad-except"
    severity: str
    file: str
    line: int
    excerpt: str
    founder_message: str
    suggestion: str
    signature: str


# Missing-timeout patterns. Each one matches a call WITHOUT a `timeout=`
# kwarg present on the same line. (Multi-line call detection would need
# AST parsing; v1 sticks to single-line regex for low complexity.)

MISSING_TIMEOUT_PATTERNS = [
    # Python requests library
    (
        re.compile(r"\brequests\.(get|post|put|patch|delete|head|options|request)\s*\("),
        re.compile(r"timeout\s*="),
        "Python requests call",
        "this HTTP call has no time limit — could hang the process if the upstream stalls",
        "add `timeout=N` (e.g. `requests.get(url, timeout=30)`)",
    ),
    # Python httpx library
    (
        re.compile(r"\bhttpx\.(get|post|put|patch|delete|head|options|request)\s*\("),
        re.compile(r"timeout\s*="),
        "Python httpx call",
        "this HTTP call has no time limit — could hang the process if the upstream stalls",
        "add `timeout=N` (e.g. `httpx.get(url, timeout=30)`)",
    ),
    # Python subprocess
    (
        re.compile(r"\bsubprocess\.(run|call|check_call|check_output|Popen)\s*\("),
        re.compile(r"timeout\s*="),
        "Python subprocess call",
        "this subprocess has no time limit — could hang indefinitely",
        "add `timeout=N` (note: Popen needs special handling — use `.wait(timeout=N)`)",
    ),
    # Python urllib
    (
        re.compile(r"\burllib\.request\.urlopen\s*\("),
        re.compile(r"timeout\s*="),
        "Python urlopen call",
        "this HTTP call has no time limit",
        "add `timeout=N` to `urlopen(...)`",
    ),
    # Python socket
    (
        re.compile(r"\bsocket\.create_connection\s*\("),
        re.compile(r"timeout\s*="),
        "Python socket connection",
        "this socket connection has no time limit",
        "add `timeout=N` to `socket.create_connection(...)`",
    ),
]


# Silent-except patterns: `try: ... except: pass` or `except Exception: pass`
SILENT_EXCEPT_PATTERN = re.compile(
    r"^\s*except\s*(?:Exception\s*)?(?:as\s+\w+\s*)?:\s*$"
)
PASS_AFTER_EXCEPT_PATTERN = re.compile(r"^\s*pass\s*(?:#.*)?$")


# Broad-except patterns: `except Exception:` or `except:` without re-raise.
# v1 detects the except line; absence of `raise` / `raise X` / `reraise(` in
# the except body (next ~10 lines until dedent) is the "without re-raise"
# signal.
BROAD_EXCEPT_PATTERN = re.compile(
    r"^(\s*)except\s+(?:Exception|BaseException)\s*(?:as\s+\w+\s*)?:\s*(?:#.*)?$"
)
NAKED_EXCEPT_PATTERN = re.compile(r"^(\s*)except\s*:\s*(?:#.*)?$")


# ─── Scanner ────────────────────────────────────────────────────────


def _find_closing_paren_line(lines: list[str], start_line: int, start_col: int, max_lookahead: int = 12) -> int:
    """Find the line containing the matching `)` for the call starting at
    (start_line, start_col). Returns start_line if same-line; otherwise the
    line index of the closing paren, capped at start_line + max_lookahead.
    """
    depth = 0
    for i in range(start_line, min(start_line + max_lookahead + 1, len(lines))):
        line = lines[i]
        # On the starting line, skip until the actual `(`
        scan_from = start_col if i == start_line else 0
        for ch in line[scan_from:]:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth == 0:
                    return i
    return min(start_line + max_lookahead, len(lines) - 1)


def scan_file_python(rel_path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()

    for lineno, line in enumerate(lines, start=1):
        # Skip comment lines + docstrings (rough heuristic)
        stripped = line.strip()
        if stripped.startswith("#"):
            continue

        # Missing-timeout patterns
        for call_re, timeout_re, name, msg, suggestion in MISSING_TIMEOUT_PATTERNS:
            call_match = call_re.search(line)
            if not call_match:
                continue
            # Extend window until the matching close-paren OR 12 lines.
            # Multi-line calls (subprocess.run with many kwargs) often span
            # 5-8 lines; tighter window produces false positives on real
            # timeouts (this bug surfaced during Gate 4 P3 — caught my own
            # _lib/baseline.py and check-readability/audit.py which DO have
            # timeout=N but on line N+5).
            window_end = _find_closing_paren_line(lines, lineno - 1, call_match.start())
            window = "\n".join(lines[lineno - 1:window_end + 1])
            if timeout_re.search(window):
                continue
            # Also check for asyncio.wait_for wrapping (multi-line)
            preceding = "\n".join(lines[max(0, lineno - 3):lineno - 1])
            if "asyncio.wait_for" in preceding or "wait_for" in preceding:
                continue
            excerpt = stripped[:120]
            sig = f"missing-timeout::{rel_path}::{lineno}::{name}"
            findings.append(Finding(
                pattern_name=name, category="missing-timeout",
                severity="high",
                file=rel_path, line=lineno, excerpt=excerpt,
                founder_message=msg, suggestion=suggestion, signature=sig,
            ))

        # Silent-except detection: `except[ Exception]:` followed by `pass`
        if SILENT_EXCEPT_PATTERN.match(line):
            # Look at next non-blank, non-comment line
            for next_line in lines[lineno:lineno + 3]:
                next_stripped = next_line.strip()
                if not next_stripped or next_stripped.startswith("#"):
                    continue
                if PASS_AFTER_EXCEPT_PATTERN.match(next_line):
                    sig = f"silent-except::{rel_path}::{lineno}"
                    findings.append(Finding(
                        pattern_name="silent-except", category="silent-except",
                        severity="high",
                        file=rel_path, line=lineno, excerpt=stripped[:120],
                        founder_message="errors here are silently swallowed — the founder will never see what went wrong",
                        suggestion="log the exception (`log.error(...)`) before deciding to ignore it",
                        signature=sig,
                    ))
                break

        # Broad-except detection: except Exception or naked except, without re-raise
        broad_match = BROAD_EXCEPT_PATTERN.match(line) or NAKED_EXCEPT_PATTERN.match(line)
        if broad_match:
            indent = broad_match.group(1)
            # Skip if already flagged as silent-except (would double-flag)
            already_silent = any(
                f.line == lineno and f.category == "silent-except" for f in findings
            )
            if already_silent:
                continue
            # Look at except-body until dedent or 12 lines
            body_lines = []
            for j, next_line in enumerate(lines[lineno:lineno + 12]):
                if not next_line.strip():
                    continue
                # Detect dedent
                next_indent = len(next_line) - len(next_line.lstrip())
                if next_indent <= len(indent) and next_line.strip():
                    break
                body_lines.append(next_line.strip())
            body_text = " ".join(body_lines)
            # Does the body re-raise?
            if re.search(r"\b(raise(\s+\w+)?|reraise\s*\()", body_text):
                continue
            is_naked = NAKED_EXCEPT_PATTERN.match(line) is not None
            sig = f"broad-except::{rel_path}::{lineno}"
            findings.append(Finding(
                pattern_name="naked-except" if is_naked else "broad-except",
                category="broad-except",
                severity="concern",
                file=rel_path, line=lineno, excerpt=stripped[:120],
                founder_message=(
                    "this catches every kind of error including system signals — even Ctrl+C"
                    if is_naked
                    else "this catches all exceptions and doesn't re-raise — hides bugs"
                ),
                suggestion=(
                    "catch only the specific exception types you can handle, or re-raise"
                    if not is_naked
                    else "use `except Exception:` (or specific types) instead of bare `except:`"
                ),
                signature=sig,
            ))

    return findings


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class ScanReport:
    project: str
    repo_root: str
    scope: str
    base_branch: str
    files_scanned: int
    findings: list[Finding]
    baseline_loaded: bool
    newly_found: list[str]
    newly_resolved: list[str]
    allowlisted_count: int
    captured_baseline: bool
    errors: list[str]


# ─── Rendering ──────────────────────────────────────────────────────


def render_json(report: ScanReport) -> str:
    findings = [
        {
            "heuristic": f.category,
            "severity": f.severity,
            "file": f.file,
            "line": f.line,
            "identifier": f.pattern_name,
            "message": f.founder_message,
            "suggestion": f.suggestion,
            "extras": {"excerpt": f.excerpt, "signature": f.signature},
        }
        for f in report.findings
    ]
    return json.dumps({
        "project": report.project,
        "scope": report.scope,
        "files_scanned": report.files_scanned,
        "findings_count": len(report.findings),
        "findings": findings,
        "newly_found": report.newly_found,
        "newly_resolved": report.newly_resolved,
        "allowlisted_count": report.allowlisted_count,
        "captured_baseline": report.captured_baseline,
        "errors": report.errors,
    }, indent=2)


def render_markdown(report: ScanReport) -> str:
    out: list[str] = []
    out.append(f"# Reliability check — {report.project}")
    out.append("")

    if report.captured_baseline:
        out.append(
            f"**First run.** Captured baseline ({len(report.findings)} pre-existing findings will not be re-flagged). Next run will detect any newly-introduced reliability issues."
        )
        out.append("")

    out.append(f"**Files scanned:** {report.files_scanned}")
    out.append(f"**Findings:** {len(report.findings)} (allowlisted: {report.allowlisted_count})")
    out.append("")

    if report.newly_found:
        verdict = f"⚠ Something new — {len(report.newly_found)} new reliability issue{'s' if len(report.newly_found) != 1 else ''} since baseline"
    elif report.findings:
        verdict = f"🟡 {len(report.findings)} pre-existing finding{'s' if len(report.findings) != 1 else ''} (no NEW issues vs baseline)"
    else:
        verdict = "✓ Clear — no reliability findings"
    out.append(f"**Verdict:** {verdict}")
    out.append("")

    cats = {"missing-timeout": [], "silent-except": [], "broad-except": []}
    for f in report.findings:
        cats[f.category].append(f)

    category_labels = {
        "missing-timeout": "⚠ External calls without time limits",
        "silent-except": "⚠ Silent error swallowing",
        "broad-except": "🟡 Broad exception handling",
    }

    for cat_key, label in category_labels.items():
        items = cats[cat_key]
        if not items:
            continue
        out.append(f"## {label} — {len(items)}")
        out.append("")
        for f in items[:10]:
            new_tag = " 🆕 NEW SINCE BASELINE" if f.signature in report.newly_found else ""
            out.append(f"- `{f.file}:{f.line}` — {f.founder_message}{new_tag}")
            out.append(f"  - suggestion: {f.suggestion}")
        if len(items) > 10:
            out.append(f"- _…and {len(items) - 10} more — pass `--raw` for the full list._")
        out.append("")

    if report.errors:
        out.append("## Errors")
        for e in report.errors:
            out.append(f"- {e}")
        out.append("")

    out.append("---")
    out.append("_This skill is read-only. It identifies what's risky; it never modifies code._")
    out.append("_For deeper analysis (Armor pillar — 25 primitives), use `sulis-security:codebase-assess`._")
    return "\n".join(out)


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Reliability pattern scanner.")
    parser.add_argument("--project", default=None)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--scope", default="auto", choices=("auto", "pr", "codebase"))
    parser.add_argument("--base-branch", default=None)
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--raw", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not (repo_root / ".git").exists():
        print(f"error: {repo_root} is not a git repo", file=sys.stderr)
        return 2

    if args.project is None:
        args.project = repo_root.name

    # Use _lib/scope helper
    resolved_scope, base_branch, files, scope_errors = scope.resolve_scope(
        repo_root, args.scope, args.base_branch, args.pr_number, SCANNABLE_EXTENSIONS,
    )
    files = [f for f in files if not is_skipped_path(f)]

    # Use _lib/allowlist helper
    project_allow = allowlist.project_allowlist_path(
        repo_root, args.project, "check-reliability"
    )
    allow_signatures = allowlist.load_allowlist(project_allow)

    # Scan
    findings: list[Finding] = []
    allowlisted_count = 0
    for f in files:
        path = repo_root / f
        if not path.is_file():
            continue
        if path.suffix != ".py":
            # v1: only Python scanning. JS/TS/Go patterns deferred to v1.1
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for finding in scan_file_python(f, text):
            if finding.signature in allow_signatures:
                allowlisted_count += 1
                continue
            findings.append(finding)

    # Use _lib/baseline helper
    baseline_sigs = set(baseline.load_namespace(
        repo_root, args.project, "tier_4_findings", []
    ))
    baseline_loaded = bool(baseline_sigs)
    current_sigs = {f.signature for f in findings}

    newly_found = sorted(current_sigs - baseline_sigs) if baseline_loaded else []
    newly_resolved = sorted(baseline_sigs - current_sigs) if baseline_loaded else []

    captured_baseline = False
    if (not baseline_loaded or args.update_baseline) and current_sigs:
        baseline.save_namespace(
            repo_root, args.project, "tier_4_findings", sorted(current_sigs)
        )
        captured_baseline = True

    report = ScanReport(
        project=args.project,
        repo_root=str(repo_root),
        scope=resolved_scope,
        base_branch=base_branch,
        files_scanned=len(files),
        findings=findings,
        baseline_loaded=baseline_loaded,
        newly_found=newly_found,
        newly_resolved=newly_resolved,
        allowlisted_count=allowlisted_count,
        captured_baseline=captured_baseline,
        errors=scope_errors,
    )

    if args.raw:
        print(render_json(report))
    else:
        print(render_markdown(report))

    print(
        f"check-reliability: scanned={len(files)}, findings={len(findings)}, "
        f"allowlisted={allowlisted_count}, new_since_baseline={len(newly_found)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
