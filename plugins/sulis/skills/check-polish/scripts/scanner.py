#!/usr/bin/env python3
"""Polish scanner — tier 7 (Polished).

Per-plugin documentation completeness + per-file tech-debt density +
per-file hygiene checks. Uses _lib/ shared helpers.

Scope is intentionally narrower than SEA's TDD tier-7 vision (perf /
a11y / UX deferred — need upstream design choice first).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path


# ─── _lib/ bootstrap ────────────────────────────────────────────────


sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _lib import allowlist, baseline, scope  # noqa: E402


# ─── Constants ──────────────────────────────────────────────────────


SCANNABLE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".rb"}

SKIP_PATH_PATTERNS = [
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)\.git/"),
    re.compile(r"(^|/)vendor/"),
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)build/"),
    re.compile(r"(^|/)\.checkup/"),
    re.compile(r"(^|/)fixtures?/"),
    re.compile(r"(^|/)testdata/"),
    re.compile(r"(^|/)mocks?/"),
]


def is_skipped_path(path: str) -> bool:
    return any(p.search(path) for p in SKIP_PATH_PATTERNS)


TECH_DEBT_MARKERS = ("TODO", "FIXME", "HACK", "XXX", "TEMPORARY", "WORKAROUND")
TECH_DEBT_RE = re.compile(r"\b(" + "|".join(TECH_DEBT_MARKERS) + r")\b")
COMMENT_LINE_RE = {
    ".py": re.compile(r"^\s*#"),
    ".rb": re.compile(r"^\s*#"),
    ".js": re.compile(r"^\s*(//|/\*|\*)"),
    ".jsx": re.compile(r"^\s*(//|/\*|\*)"),
    ".ts": re.compile(r"^\s*(//|/\*|\*)"),
    ".tsx": re.compile(r"^\s*(//|/\*|\*)"),
    ".go": re.compile(r"^\s*//"),
}


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class Finding:
    rule: str
    category: str  # docs-completeness | tech-debt-density | file-hygiene
    severity: str
    file: str  # path or plugin slug
    line: int  # 0 for plugin-level findings
    founder_message: str
    suggestion: str
    signature: str


@dataclass
class ScanReport:
    project: str
    scope: str
    plugins_audited: int
    files_scanned: int
    findings: list[Finding]
    baseline_loaded: bool
    newly_found: list[str]
    newly_resolved: list[str]
    allowlisted_count: int
    captured_baseline: bool
    errors: list[str]
    primitive_status: dict = field(default_factory=dict)


# ─── Documentation completeness (per plugin) ───────────────────────


def check_plugin_docs(repo_root: Path, plugin_slug: str) -> list[Finding]:
    findings: list[Finding] = []
    plugin_dir = repo_root / "plugins" / plugin_slug
    if not plugin_dir.is_dir():
        return findings

    # DC-001: README.md
    if not (plugin_dir / "README.md").is_file():
        findings.append(Finding(
            rule="DC-001", category="docs-completeness", severity="concern",
            file=f"plugins/{plugin_slug}/", line=0,
            founder_message=f"plugin `{plugin_slug}` has no README.md",
            suggestion="add a README.md describing what the plugin does + how to use it",
            signature=f"docs-completeness::{plugin_slug}::DC-001",
        ))

    # DC-002: CHANGELOG.md if plugin.json version > 0.x or shipped multiple
    plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
    if plugin_json.is_file():
        try:
            data = json.loads(plugin_json.read_text(encoding="utf-8"))
            version = data.get("version", "0.0.0")
            major, minor, *_ = (version.split(".") + ["0", "0"])[:2]
            if (int(major) > 0 or int(minor) >= 2) and not (plugin_dir / "CHANGELOG.md").is_file():
                findings.append(Finding(
                    rule="DC-002", category="docs-completeness", severity="advisory",
                    file=f"plugins/{plugin_slug}/", line=0,
                    founder_message=f"plugin `{plugin_slug}` v{version} has no CHANGELOG.md but has shipped multiple versions",
                    suggestion="add a CHANGELOG.md to track version history",
                    signature=f"docs-completeness::{plugin_slug}::DC-002",
                ))
        except (json.JSONDecodeError, OSError, ValueError):
            pass

    # DC-003: LICENSE
    if not any((plugin_dir / name).is_file() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")):
        # Marketplace-root LICENSE covers child plugins by convention
        if not any((repo_root / name).is_file() for name in ("LICENSE", "LICENSE.md", "LICENSE.txt")):
            findings.append(Finding(
                rule="DC-003", category="docs-completeness", severity="advisory",
                file=f"plugins/{plugin_slug}/", line=0,
                founder_message=f"plugin `{plugin_slug}` has no LICENSE file (and no marketplace-root LICENSE)",
                suggestion="add a LICENSE file (e.g., MIT, Apache-2.0)",
                signature=f"docs-completeness::{plugin_slug}::DC-003",
            ))

    # DC-004: plugin.json keywords ≥ 3
    if plugin_json.is_file():
        try:
            data = json.loads(plugin_json.read_text(encoding="utf-8"))
            keywords = data.get("keywords") or []
            if len(keywords) < 3:
                findings.append(Finding(
                    rule="DC-004", category="docs-completeness", severity="advisory",
                    file=f"plugins/{plugin_slug}/", line=0,
                    founder_message=f"plugin `{plugin_slug}` has {len(keywords)} keywords (recommended ≥3 for discoverability)",
                    suggestion="add keywords to plugin.json",
                    signature=f"docs-completeness::{plugin_slug}::DC-004",
                ))
        except (json.JSONDecodeError, OSError):
            pass

    # DC-005: README has ## headings
    readme = plugin_dir / "README.md"
    if readme.is_file():
        try:
            text = readme.read_text(encoding="utf-8")
            if not re.search(r"^##\s+", text, re.MULTILINE):
                findings.append(Finding(
                    rule="DC-005", category="docs-completeness", severity="advisory",
                    file=f"plugins/{plugin_slug}/README.md", line=0,
                    founder_message=f"plugin `{plugin_slug}`'s README has no `##` section headings — likely just a title",
                    suggestion="add section headings (## What it does, ## How to use, etc.)",
                    signature=f"docs-completeness::{plugin_slug}::DC-005",
                ))
        except OSError:
            pass

    return findings


# ─── Tech-debt density (per file) ──────────────────────────────────


def check_tech_debt(rel_path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []
    ext = Path(rel_path).suffix
    comment_re = COMMENT_LINE_RE.get(ext)
    if not comment_re:
        return findings

    comment_lines = [l for l in text.splitlines() if comment_re.match(l)]
    if not comment_lines:
        return findings

    debt_count = sum(1 for l in comment_lines if TECH_DEBT_RE.search(l))
    if debt_count == 0:
        return findings

    density = debt_count / len(comment_lines)

    # TD-001: density > 5%
    if density > 0.05 and debt_count >= 3:
        findings.append(Finding(
            rule="TD-001", category="tech-debt-density", severity="concern",
            file=rel_path, line=0,
            founder_message=f"{debt_count} tech-debt markers across {len(comment_lines)} comment lines ({density*100:.0f}% — high concentration)",
            suggestion="review the TODO/FIXME comments + either resolve or extract to a tracker",
            signature=f"tech-debt-density::{rel_path}::TD-001",
        ))

    # TD-002: >20 markers in single file
    if debt_count > 20:
        findings.append(Finding(
            rule="TD-002", category="tech-debt-density", severity="advisory",
            file=rel_path, line=0,
            founder_message=f"{debt_count} tech-debt markers in this file (above 20-marker threshold)",
            suggestion="extract a backlog item to track the work",
            signature=f"tech-debt-density::{rel_path}::TD-002",
        ))

    return findings


# ─── File hygiene (per file) ───────────────────────────────────────


def check_hygiene(rel_path: str, text: str) -> list[Finding]:
    findings: list[Finding] = []

    lines = text.splitlines()
    trailing_count = sum(1 for l in lines if l != l.rstrip() and l.rstrip())

    # FH-001: >5 trailing-whitespace lines
    if trailing_count > 5:
        findings.append(Finding(
            rule="FH-001", category="file-hygiene", severity="advisory",
            file=rel_path, line=0,
            founder_message=f"{trailing_count} lines have trailing whitespace",
            suggestion="run a formatter (or your editor's strip-trailing-whitespace setting)",
            signature=f"file-hygiene::{rel_path}::FH-001",
        ))

    # FH-002: mixed line endings
    has_crlf = "\r\n" in text
    has_lf = "\n" in text.replace("\r\n", "")
    if has_crlf and has_lf:
        findings.append(Finding(
            rule="FH-002", category="file-hygiene", severity="advisory",
            file=rel_path, line=0,
            founder_message="this file mixes CRLF and LF line endings",
            suggestion="configure .gitattributes (`* text=auto eol=lf`) and reformat",
            signature=f"file-hygiene::{rel_path}::FH-002",
        ))

    # FH-003: file doesn't end with newline
    if text and not text.endswith("\n"):
        findings.append(Finding(
            rule="FH-003", category="file-hygiene", severity="advisory",
            file=rel_path, line=0,
            founder_message="this file doesn't end with a newline (POSIX convention)",
            suggestion="add a trailing newline",
            signature=f"file-hygiene::{rel_path}::FH-003",
        ))

    return findings


# ─── Rendering ──────────────────────────────────────────────────────


def render_json(report: ScanReport) -> str:
    findings_out = [
        {
            "heuristic": f.category,
            "severity": f.severity,
            "file": f.file,
            "line": f.line,
            "identifier": f.rule,
            "message": f.founder_message,
            "suggestion": f.suggestion,
            "extras": {"signature": f.signature},
        }
        for f in report.findings
    ]
    return json.dumps({
        "project": report.project,
        "scope": report.scope,
        "plugins_audited": report.plugins_audited,
        "files_scanned": report.files_scanned,
        "findings_count": len(report.findings),
        "findings": findings_out,
        "newly_found": report.newly_found,
        "newly_resolved": report.newly_resolved,
        "allowlisted_count": report.allowlisted_count,
        "captured_baseline": report.captured_baseline,
        "errors": report.errors,
        "primitive_status": report.primitive_status,
    }, indent=2)


def render_markdown(report: ScanReport) -> str:
    out: list[str] = []
    out.append(f"# Polish check — {report.project}")
    out.append("")

    if report.captured_baseline:
        out.append(f"**First run.** Captured baseline ({len(report.findings)} pre-existing findings). Next run will detect newly-degraded polish.")
        out.append("")

    out.append(f"**Plugins audited:** {report.plugins_audited}")
    out.append(f"**Files scanned:** {report.files_scanned}")
    out.append(f"**Findings:** {len(report.findings)} (allowlisted: {report.allowlisted_count})")
    out.append("")

    if report.newly_found:
        verdict = f"⚠ Polish degraded — {len(report.newly_found)} new finding(s) since baseline"
    elif report.findings:
        concerns = sum(1 for f in report.findings if f.severity == "concern")
        if concerns:
            verdict = f"🟡 {concerns} polish concern(s) + {len(report.findings) - concerns} advisory finding(s)"
        else:
            verdict = f"ℹ {len(report.findings)} polish advisor(ies) — review when convenient"
    else:
        verdict = "✓ Clear — project feels polished"
    out.append(f"**Verdict:** {verdict}")
    out.append("")

    categories = {
        "docs-completeness": "📚 Documentation gaps",
        "tech-debt-density": "📝 Tech-debt density",
        "file-hygiene": "🧹 File hygiene",
    }
    by_cat: dict[str, list[Finding]] = {}
    for f in report.findings:
        by_cat.setdefault(f.category, []).append(f)
    for cat, label in categories.items():
        items = by_cat.get(cat, [])
        if not items:
            continue
        out.append(f"## {label} — {len(items)}")
        out.append("")
        for f in items[:15]:
            new_tag = " 🆕 NEW" if f.signature in report.newly_found else ""
            out.append(f"- `{f.file}` — {f.founder_message}{new_tag}")
            out.append(f"  - suggestion: {f.suggestion}")
        if len(items) > 15:
            out.append(f"- _…and {len(items) - 15} more — pass `--raw` for full list._")
        out.append("")

    out.append("---")
    out.append("_This skill is read-only. It identifies polish gaps; never modifies code._")
    out.append("_v1 scope: docs + tech-debt + hygiene. Performance / accessibility / UX deferred to a future version._")
    return "\n".join(out)


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Polish checker (tier 7).")
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

    resolved_scope, base_branch, files, scope_errors = scope.resolve_scope(
        repo_root, args.scope, args.base_branch, args.pr_number, SCANNABLE_EXTENSIONS,
    )
    files = [f for f in files if not is_skipped_path(f)]

    findings: list[Finding] = []

    # Per-plugin documentation completeness
    plugins_dir = repo_root / "plugins"
    plugins_audited = 0
    if plugins_dir.is_dir():
        for plugin_path in sorted(plugins_dir.iterdir()):
            if not plugin_path.is_dir():
                continue
            plugins_audited += 1
            findings.extend(check_plugin_docs(repo_root, plugin_path.name))

    # Per-file tech-debt + hygiene
    for rel_path in files:
        path = repo_root / rel_path
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        findings.extend(check_tech_debt(rel_path, text))
        findings.extend(check_hygiene(rel_path, text))

    # Allowlist
    project_allow = allowlist.project_allowlist_path(repo_root, args.project, "check-polish")
    allow_signatures = allowlist.load_allowlist(project_allow)
    pre = len(findings)
    findings = [f for f in findings if f.signature not in allow_signatures]
    allowlisted_count = pre - len(findings)

    # Baseline
    baseline_sigs = set(baseline.load_namespace(repo_root, args.project, "tier_7_findings", []))
    baseline_loaded = bool(baseline_sigs)
    current_sigs = {f.signature for f in findings}
    newly_found = sorted(current_sigs - baseline_sigs) if baseline_loaded else []
    newly_resolved = sorted(baseline_sigs - current_sigs) if baseline_loaded else []

    captured_baseline = False
    if (not baseline_loaded or args.update_baseline) and current_sigs:
        baseline.save_namespace(repo_root, args.project, "tier_7_findings", sorted(current_sigs))
        captured_baseline = True

    # CQ-04 primitive_status emission (v0.24.0+). check-polish is the
    # canonical CQ-04 owner per the v0.16.0 upsurge: TD-001 (density > 5%)
    # + TD-002 (>20 markers in single file) detect technical debt
    # accumulation. PASS = primitive was assessed (regardless of whether
    # any TD findings surfaced). Note: when files_scanned == 0 (no source
    # files in scope), CQ-04 is NOT_APPLICABLE.
    primitive_status: dict[str, str] = {}
    primitive_status["CQ-04"] = "PASS" if len(files) > 0 else "NOT_APPLICABLE"

    report = ScanReport(
        project=args.project, scope=resolved_scope,
        plugins_audited=plugins_audited, files_scanned=len(files),
        findings=findings, baseline_loaded=baseline_loaded,
        newly_found=newly_found, newly_resolved=newly_resolved,
        allowlisted_count=allowlisted_count,
        captured_baseline=captured_baseline, errors=scope_errors,
        primitive_status=primitive_status,
    )

    if args.raw:
        print(render_json(report))
    else:
        print(render_markdown(report))

    print(
        f"check-polish: plugins={plugins_audited}, files={len(files)}, "
        f"findings={len(findings)}, allowlisted={allowlisted_count}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
