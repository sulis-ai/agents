#!/usr/bin/env python3
"""Security pattern scanner.

Tier-2 regression detection: did the project add a credential leak or
dangerous code pattern? Pattern-based, designed for low false-positive
rate. For deep audit, use sulis-security:codebase-assess instead.

Baseline + signature-dedup at .checkup/{project}/baseline.json under
tier_2_findings sub-key (separate namespace from tier_1 + tier_3).

Usage:

    python3 scanner.py [--repo-root .] [--raw] [--update-baseline]

Exit codes:
- 0 = success
- 1 = usage error
- 2 = filesystem / git error
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# _lib/ shared helpers (canonical pattern per add-skill v0.6.0).
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _lib import allowlist as _allowlist  # noqa: E402
from _lib import baseline as _baseline  # noqa: E402


# ─── Source-file selection ──────────────────────────────────────────


SCANNABLE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".rb", ".go", ".rs", ".java",
    ".kt", ".swift", ".cs", ".scala", ".php", ".sh", ".yaml", ".yml",
    ".json", ".toml", ".ini", ".env", ".env.example", ".env.local",
    ".tf", ".hcl",
}

# Paths we never scan (intentional patterns live here)
SKIP_PATH_PATTERNS = [
    re.compile(r"(^|/)tests?/fixtures?/"),
    re.compile(r"(^|/)__tests__/fixtures?/"),
    re.compile(r"(^|/)testdata/"),
    re.compile(r"(^|/)mocks?/"),
    re.compile(r"(^|/)docs/examples?/"),
    re.compile(r"(^|/)\.checkup/"),
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)\.git/"),
    re.compile(r"(^|/)vendor/"),
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)build/"),
    # Skip the security-patterns reference doc (it documents patterns and
    # would self-match)
    re.compile(r"plugins/sulis/skills/check-security/references/security-patterns\.md$"),
]


def is_skipped_path(path: str) -> bool:
    return any(p.search(path) for p in SKIP_PATH_PATTERNS)


# ─── Pattern catalogue ──────────────────────────────────────────────


@dataclass
class Pattern:
    name: str  # human-readable name (e.g. "AWS Access Key ID")
    category: str  # "credential" | "dangerous-pattern"
    regex: str  # compiled at module load
    severity: str  # high | concern | advisory
    founder_message: str  # plain-English what-this-means

    def __post_init__(self):
        self.compiled = re.compile(self.regex)


CREDENTIAL_PATTERNS: list[Pattern] = [
    Pattern("AWS Access Key ID", "credential", r"\bAKIA[0-9A-Z]{16}\b", "high",
            "looks like an AWS access key"),
    Pattern("AWS Session Token", "credential", r"\bASIA[0-9A-Z]{16}\b", "high",
            "looks like an AWS session token"),
    Pattern("GitHub Personal Access Token", "credential", r"\bghp_[A-Za-z0-9]{36}\b", "high",
            "looks like a GitHub personal access token"),
    Pattern("GitHub OAuth Token", "credential", r"\bgho_[A-Za-z0-9]{36}\b", "high",
            "looks like a GitHub OAuth token"),
    Pattern("GitHub User-to-Server Token", "credential", r"\bghu_[A-Za-z0-9]{36}\b", "high",
            "looks like a GitHub user-to-server token"),
    Pattern("GitHub Server-to-Server Token", "credential", r"\bghs_[A-Za-z0-9]{36}\b", "high",
            "looks like a GitHub server-to-server token"),
    Pattern("GitHub Refresh Token", "credential", r"\bghr_[A-Za-z0-9]{36}\b", "high",
            "looks like a GitHub refresh token"),
    Pattern("GitHub Fine-Grained PAT", "credential", r"\bgithub_pat_[A-Za-z0-9_]{82}\b", "high",
            "looks like a GitHub fine-grained PAT"),
    Pattern("Stripe Secret Key", "credential", r"\bsk_(live|test)_[A-Za-z0-9]{24,}\b", "high",
            "looks like a Stripe secret key"),
    Pattern("Stripe Restricted Key", "credential", r"\brk_(live|test)_[A-Za-z0-9]{24,}\b", "high",
            "looks like a Stripe restricted key"),
    Pattern("Stripe Publishable Key", "credential", r"\bpk_(live|test)_[A-Za-z0-9]{24,}\b", "advisory",
            "looks like a Stripe publishable key (these ARE public, but worth confirming)"),
    Pattern("OpenAI API Key", "credential", r"\bsk-[A-Za-z0-9]{48}\b", "high",
            "looks like an OpenAI API key"),
    Pattern("Slack Bot Token", "credential", r"\bxox[bpoa]-\d+-\d+-\d+-[a-z0-9]+\b", "high",
            "looks like a Slack token"),
    Pattern("Slack Webhook", "credential", r"https://hooks\.slack\.com/services/[A-Z0-9/]+", "concern",
            "looks like a Slack webhook URL (these are private)"),
    Pattern("Anthropic API Key", "credential", r"\bsk-ant-(api|tok)\d+-[A-Za-z0-9_-]{32,}\b", "high",
            "looks like an Anthropic API key"),
    Pattern("Private Key Header", "credential", r"-----BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY-----", "high",
            "looks like an unencrypted private key"),
]


DANGEROUS_PATTERNS: list[Pattern] = [
    Pattern("Python eval on user input", "dangerous-pattern",
            r"eval\s*\(\s*(request\.|input\(|sys\.argv|os\.environ\[)", "high",
            "eval() on user input — code injection risk"),
    Pattern("Python exec on user input", "dangerous-pattern",
            r"exec\s*\(\s*(request\.|input\(|sys\.argv)", "high",
            "exec() on user input — code injection risk"),
    Pattern("Python pickle on untrusted", "dangerous-pattern",
            r"pickle\.loads?\s*\(\s*(request\.|payload|data\b)", "high",
            "pickle.loads on untrusted data — arbitrary code execution"),
    Pattern("Subprocess shell=True with format", "dangerous-pattern",
            r"subprocess\.(call|run|Popen)\s*\([^)]*shell\s*=\s*True[^)]*(%|f['\"])", "high",
            "subprocess with shell=True and formatted string — shell injection risk"),
    Pattern("os.system with format-string", "dangerous-pattern",
            r"os\.system\s*\(\s*(f['\"]|.*%.*['\"]|.*\.format\()", "high",
            "os.system with formatted string — shell injection risk"),
    Pattern("yaml.load unsafe", "dangerous-pattern",
            r"yaml\.load\s*\((?!.*Loader\s*=\s*yaml\.Safe)", "concern",
            "yaml.load without SafeLoader — arbitrary code execution"),
    Pattern("JS eval", "dangerous-pattern",
            r"\beval\s*\(\s*[a-zA-Z_$]", "high",
            "eval() on variable input — code injection risk"),
    Pattern("React dangerouslySetInnerHTML", "dangerous-pattern",
            r"dangerouslySetInnerHTML\s*=", "advisory",
            "dangerouslySetInnerHTML — XSS risk if input not trusted"),
    Pattern("innerHTML with variable", "dangerous-pattern",
            r"\.innerHTML\s*=\s*[a-zA-Z_$]\w*", "concern",
            "innerHTML = variable — potential XSS"),
    Pattern("SQL format-string execute (Python)", "dangerous-pattern",
            r"\.execute\s*\(\s*(f['\"]|.*%.*['\"]|.*\.format\()", "high",
            "SQL with formatted string — SQL injection risk; use parameterised queries"),
]


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class Finding:
    pattern_name: str
    category: str  # "credential" | "dangerous-pattern"
    severity: str
    file: str
    line: int
    matched_text: str  # short excerpt; not the full secret
    founder_message: str
    signature: str  # for dedup: {pattern_name}::{file}::{line}::{matched_excerpt}


@dataclass
class ScanReport:
    project: str
    repo_root: str
    files_scanned: int
    findings: list[Finding]
    baseline_loaded: bool
    newly_found: list[str]  # signatures
    newly_resolved: list[str]
    allowlisted_count: int
    captured_baseline: bool
    errors: list[str]
    primitive_status: dict[str, str] = field(default_factory=dict)
    deployed_url: str | None = None


# ─── Allowlist loading ──────────────────────────────────────────────
# (Inline implementation removed in v0.11.x — uses _lib/allowlist.
# Keep this comment as a pointer for future maintainers.)
# Pre-existing allowlist path: .checkup/{project}/security-allowlist.md


# ─── External tool integration (v0.20.0+) ─────────────────────────
# Wraps semgrep / gitleaks / trivy / testssl / curl_probe via
# plugins/sulis/_lib/tools/ wrappers. Each wrapper degrades to
# NOT_ASSESSED if neither Docker nor native binary is present —
# never silent regex fallback.


def _import_tool_wrappers():
    """Lazy import to avoid sys.path pollution at module load."""
    import sys as _sys
    lib_root = str(Path(__file__).resolve().parents[3])
    if lib_root not in _sys.path:
        _sys.path.insert(0, lib_root)
    from _lib.tools import semgrep, gitleaks, trivy, testssl, curl_probe
    return semgrep, gitleaks, trivy, testssl, curl_probe


def _tool_finding_to_finding(tool_finding: dict, category: str) -> Finding:
    """Map a tool-wrapper finding dict to the scanner's Finding dataclass."""
    rule_id = tool_finding.get("rule_id", "unknown")
    file_path = tool_finding.get("file", "")
    line = tool_finding.get("line", 1)
    message = tool_finding.get("message", "")
    severity = tool_finding.get("severity", "advisory")
    sig = f"{tool_finding.get('tool', 'tool')}::{rule_id}::{file_path}::{line}"
    return Finding(
        pattern_name=rule_id,
        category=category,
        severity=severity,
        file=file_path,
        line=line,
        matched_text=message[:80],
        founder_message=message,
        signature=sig,
    )


def run_external_tools(
    repo_root: Path,
    *,
    url: str | None = None,
    scan_git_history: bool = False,
    timeout_per_tool: int = 300,
) -> tuple[list[Finding], dict[str, str], list[str]]:
    """Invoke external tool wrappers and merge findings into Finding list.

    Args:
        repo_root: absolute repo path
        url: optional deployed URL — triggers testssl + curl_probe
        scan_git_history: if True, gitleaks scans git history (SEC-07)
        timeout_per_tool: per-wrapper subprocess timeout

    Returns:
        (findings, primitive_status, errors) — primitive_status maps
        primitive_id → PASS / NOT_ASSESSED based on tool availability.
    """
    semgrep, gitleaks, trivy, testssl, curl_probe = _import_tool_wrappers()
    findings: list[Finding] = []
    primitive_status: dict[str, str] = {}
    errors: list[str] = []
    repo_root_str = str(repo_root)

    # Semgrep — SEC-01/03/04/05/06 + DAT-03 + (via reliability) INF-04
    sg_mode = semgrep.is_available()
    if sg_mode.value != "not_available":
        try:
            result = semgrep.run(repo_root=repo_root_str, timeout=timeout_per_tool)
            for tf in semgrep.parse_findings(result, repo_root_str):
                findings.append(_tool_finding_to_finding(tf, "semgrep-security"))
            primitive_status.update({
                "SEC-01": "PASS", "SEC-03": "PASS", "SEC-04": "PASS",
                "SEC-05": "PASS", "SEC-06": "PASS", "DAT-03": "PASS",
            })
        except Exception as exc:  # noqa: BLE001 — boundary catch for tool wrapper
            errors.append(f"semgrep invocation failed: {exc}")
    else:
        for prim in ("SEC-01", "SEC-03", "SEC-04", "SEC-05", "SEC-06", "DAT-03"):
            primitive_status[prim] = "NOT_ASSESSED"

    # Gitleaks — SEC-07 + DAT-04
    gl_mode = gitleaks.is_available()
    if gl_mode.value != "not_available":
        try:
            result = gitleaks.run(
                repo_root=repo_root_str,
                scan_history=scan_git_history,
                timeout=timeout_per_tool,
            )
            for tf in gitleaks.parse_findings(result, repo_root_str):
                findings.append(_tool_finding_to_finding(tf, "credential"))
            primitive_status["SEC-07"] = "PASS"
            primitive_status["DAT-04"] = "PASS"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"gitleaks invocation failed: {exc}")
    else:
        primitive_status["SEC-07"] = "NOT_ASSESSED"
        primitive_status["DAT-04"] = "NOT_ASSESSED"

    # Trivy — SC-01..04
    tv_mode = trivy.is_available()
    if tv_mode.value != "not_available":
        try:
            result = trivy.run_fs_scan(repo_root=repo_root_str, timeout=timeout_per_tool * 2)
            for tf in trivy.parse_findings(result, repo_root_str):
                findings.append(_tool_finding_to_finding(tf, "supply-chain"))
            for prim in ("SC-01", "SC-02", "SC-03", "SC-04"):
                primitive_status[prim] = "PASS"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"trivy invocation failed: {exc}")
    else:
        for prim in ("SC-01", "SC-02", "SC-03", "SC-04"):
            primitive_status[prim] = "NOT_ASSESSED"

    # Deployed-URL checks: testssl (DAT-02) + curl_probe (INF-03)
    if url:
        ts_mode = testssl.is_available()
        if ts_mode.value != "not_available":
            try:
                result = testssl.run(url=url, timeout=timeout_per_tool * 2)
                for tf in testssl.parse_findings(result):
                    findings.append(_tool_finding_to_finding(tf, "tls"))
                primitive_status["DAT-02"] = "PASS"
            except Exception as exc:  # noqa: BLE001
                errors.append(f"testssl invocation failed: {exc}")
        else:
            primitive_status["DAT-02"] = "NOT_ASSESSED"

        cp_mode = curl_probe.is_available()
        if cp_mode.value != "not_available":
            try:
                result = curl_probe.run(url=url, timeout=30)
                for tf in curl_probe.parse_findings(result, url=url):
                    findings.append(_tool_finding_to_finding(tf, "http-header"))
                primitive_status["INF-03"] = "PASS"
            except Exception as exc:  # noqa: BLE001
                errors.append(f"curl_probe invocation failed: {exc}")
        else:
            primitive_status["INF-03"] = "NOT_ASSESSED"

    return findings, primitive_status, errors


# ─── Scanner ────────────────────────────────────────────────────────


def list_source_files(repo_root: Path) -> list[str]:
    """Get tracked files from git ls-files, filtered to scannable extensions."""
    try:
        proc = subprocess.run(
            ["git", "ls-files"], cwd=str(repo_root), capture_output=True, text=True, timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return []
    if proc.returncode != 0:
        return []
    files = []
    for line in proc.stdout.strip().splitlines():
        if not line:
            continue
        if is_skipped_path(line):
            continue
        ext = Path(line).suffix
        if ext in SCANNABLE_EXTENSIONS or Path(line).name.startswith(".env"):
            files.append(line)
    return files


def scan_file(rel_path: str, repo_root: Path, all_patterns: list[Pattern]) -> list[Finding]:
    findings: list[Finding] = []
    path = repo_root / rel_path
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return findings

    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern in all_patterns:
            match = pattern.compiled.search(line)
            if match:
                matched = match.group(0)
                # Truncate to first 8 chars + "..." for credentials (don't echo full secret)
                if pattern.category == "credential" and len(matched) > 12:
                    excerpt = matched[:8] + "…"
                else:
                    excerpt = matched[:60]
                sig = f"{pattern.name}::{rel_path}::{lineno}::{excerpt}"
                findings.append(Finding(
                    pattern_name=pattern.name,
                    category=pattern.category,
                    severity=pattern.severity,
                    file=rel_path,
                    line=lineno,
                    matched_text=excerpt,
                    founder_message=pattern.founder_message,
                    signature=sig,
                ))
    return findings


# ─── Baseline (tier_2 namespace) ───────────────────────────────────
# Inline implementation removed in v0.11.x — uses _lib/baseline.
# Wrappers below preserve the original call signatures so the rest of
# the file doesn't change.


def load_baseline_tier2(repo_root: Path, project: str) -> set[str]:
    return set(_baseline.load_namespace(repo_root, project, "tier_2_findings", []))


def save_baseline_tier2(repo_root: Path, project: str, signatures: set[str]) -> None:
    _baseline.save_namespace(
        repo_root, project, "tier_2_findings", sorted(signatures)
    )


# ─── Rendering ──────────────────────────────────────────────────────


def render_json(report: ScanReport) -> str:
    # Orchestrator-compatible findings array
    findings = []
    not_assessed = sorted(
        prim for prim, status in report.primitive_status.items() if status == "NOT_ASSESSED"
    )
    for f in report.findings:
        findings.append({
            "heuristic": f.category,
            "severity": f.severity,
            "file": f.file,
            "line": f.line,
            "identifier": f.pattern_name,
            "message": f.founder_message,
            "suggestion": "rotate the secret, then remove it from git history" if f.category == "credential" else "review and replace with a safer pattern",
            "extras": {"matched_text": f.matched_text, "signature": f.signature},
        })
    return json.dumps({
        "project": report.project,
        "files_scanned": report.files_scanned,
        "findings_count": len(report.findings),
        "findings": findings,
        "newly_found": report.newly_found,
        "newly_resolved": report.newly_resolved,
        "allowlisted_count": report.allowlisted_count,
        "captured_baseline": report.captured_baseline,
        "errors": report.errors,
        "primitive_status": report.primitive_status,
        "not_assessed": not_assessed,
        "deployed_url": report.deployed_url,
    }, indent=2)


def render_markdown(report: ScanReport) -> str:
    out: list[str] = []
    out.append(f"# Security check — {report.project}")
    out.append("")

    if report.captured_baseline:
        out.append(f"**First run.** Captured baseline ({len(report.findings)} pre-existing findings will not be re-flagged). Next run will detect any newly-leaked credentials or dangerous patterns.")
        out.append("")

    out.append(f"**Files scanned:** {report.files_scanned}")
    out.append(f"**Findings:** {len(report.findings)} (allowlisted: {report.allowlisted_count})")
    out.append("")

    if report.newly_found:
        verdict = f"⚠ Something new — {len(report.newly_found)} new security finding{'s' if len(report.newly_found) != 1 else ''} since baseline"
    elif report.findings:
        verdict = f"🟡 {len(report.findings)} pre-existing finding{'s' if len(report.findings) != 1 else ''} (no NEW issues vs baseline)"
    else:
        verdict = "✓ Clear — no security findings"
    out.append(f"**Verdict:** {verdict}")
    out.append("")

    creds = [f for f in report.findings if f.category == "credential"]
    dangers = [f for f in report.findings if f.category == "dangerous-pattern"]

    if creds:
        out.append(f"## ⚠ Likely-leaked credentials — {len(creds)}")
        out.append("")
        for f in creds[:10]:
            new_tag = " 🆕 NEW SINCE BASELINE" if f.signature in report.newly_found else ""
            out.append(f"- `{f.file}:{f.line}` — {f.founder_message}{new_tag}")
            out.append(f"  - matched: `{f.matched_text}`")
            out.append(f"  - to investigate: rotate the secret, then remove from git history")
        out.append("")

    if dangers:
        out.append(f"## ⚠ Dangerous code patterns — {len(dangers)}")
        out.append("")
        for f in dangers[:10]:
            new_tag = " 🆕 NEW SINCE BASELINE" if f.signature in report.newly_found else ""
            out.append(f"- `{f.file}:{f.line}` — {f.founder_message}{new_tag}")
            out.append(f"  - pattern: `{f.matched_text}`")
        out.append("")

    if report.errors:
        out.append("## Errors")
        for e in report.errors:
            out.append(f"- {e}")
        out.append("")

    # Primitive coverage status — surfaces NOT_ASSESSED honestly per
    # SPIRAL_TEMPLATES Codebase Referential Integrity policy.
    if report.primitive_status:
        passed = sorted(p for p, s in report.primitive_status.items() if s == "PASS")
        not_assessed_list = sorted(p for p, s in report.primitive_status.items() if s == "NOT_ASSESSED")
        out.append("## Primitive coverage")
        out.append("")
        if passed:
            out.append(f"**Assessed ({len(passed)}):** {', '.join(passed)}")
        if not_assessed_list:
            out.append(f"**⏳ NOT_ASSESSED ({len(not_assessed_list)}):** {', '.join(not_assessed_list)}")
            out.append("")
            out.append("> NOT_ASSESSED primitives have a known tool dependency that is")
            out.append("> not currently available (neither Docker daemon nor native binary).")
            out.append("> Install the relevant tool (semgrep / gitleaks / trivy / testssl.sh)")
            out.append("> or start Docker to assess these primitives.")
        out.append("")

    out.append("---")
    out.append("_This skill is read-only. It identifies what's risky; it never modifies code._")
    out.append("_For full 25-primitive depth audit until check-security parity reaches ≥ 95%, use `sulis-security:codebase-assess`._")
    return "\n".join(out)


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Security pattern scanner.")
    parser.add_argument("--project", default=None)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--raw", action="store_true")
    # Orchestrator-compat flags
    parser.add_argument("--scope", default=None)
    parser.add_argument("--base-branch", default=None)
    parser.add_argument("--pr-number", default=None)
    # External tool integration (v0.20.0+)
    parser.add_argument(
        "--url", default=None,
        help="deployed URL — triggers testssl (DAT-02) + curl_probe (INF-03)",
    )
    parser.add_argument(
        "--scan-git-history", action="store_true",
        help="gitleaks --no-git off; scans full git history (SEC-07)",
    )
    parser.add_argument(
        "--skip-tools", action="store_true",
        help="skip external tool wrappers (regex-only fast path; STRONGLY DISCOURAGED — produces NOT_ASSESSED for most primitives)",
    )
    parser.add_argument(
        "--tool-timeout", type=int, default=300,
        help="per-tool subprocess timeout in seconds",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not (repo_root / ".git").exists():
        print(f"error: {repo_root} is not a git repo", file=sys.stderr)
        return 2

    if args.project is None:
        args.project = repo_root.name

    files = list_source_files(repo_root)
    allowlist_path = repo_root / ".checkup" / args.project / "security-allowlist.md"
    allowlist = _allowlist.load_allowlist(allowlist_path)
    all_patterns = CREDENTIAL_PATTERNS + DANGEROUS_PATTERNS

    findings: list[Finding] = []
    allowlisted_count = 0
    for f in files:
        for finding in scan_file(f, repo_root, all_patterns):
            if finding.signature in allowlist or finding.matched_text in allowlist:
                allowlisted_count += 1
                continue
            findings.append(finding)

    # External tool integration — semgrep / gitleaks / trivy / testssl / curl_probe
    primitive_status: dict[str, str] = {}
    tool_errors: list[str] = []
    if not args.skip_tools:
        try:
            tool_findings, primitive_status, tool_errors = run_external_tools(
                repo_root,
                url=args.url,
                scan_git_history=args.scan_git_history,
                timeout_per_tool=args.tool_timeout,
            )
            for tf in tool_findings:
                if tf.signature in allowlist or tf.matched_text in allowlist:
                    allowlisted_count += 1
                    continue
                findings.append(tf)
        except Exception as exc:  # noqa: BLE001 — boundary catch
            tool_errors.append(f"external tool integration failed: {exc}")
    else:
        # All wrapper-covered primitives marked NOT_ASSESSED
        for prim in ("SEC-01", "SEC-03", "SEC-04", "SEC-05", "SEC-06", "SEC-07",
                     "DAT-03", "DAT-04", "SC-01", "SC-02", "SC-03", "SC-04"):
            primitive_status[prim] = "NOT_ASSESSED"
        if args.url:
            primitive_status["DAT-02"] = "NOT_ASSESSED"
            primitive_status["INF-03"] = "NOT_ASSESSED"

    # Baseline + delta
    baseline_sigs = load_baseline_tier2(repo_root, args.project)
    baseline_loaded = bool(baseline_sigs)
    current_sigs = {f.signature for f in findings}

    newly_found = sorted(current_sigs - baseline_sigs) if baseline_loaded else []
    newly_resolved = sorted(baseline_sigs - current_sigs) if baseline_loaded else []

    captured_baseline = False
    if (not baseline_loaded or args.update_baseline) and current_sigs:
        save_baseline_tier2(repo_root, args.project, current_sigs)
        captured_baseline = True

    report = ScanReport(
        project=args.project,
        repo_root=str(repo_root),
        files_scanned=len(files),
        findings=findings,
        baseline_loaded=baseline_loaded,
        newly_found=newly_found,
        newly_resolved=newly_resolved,
        allowlisted_count=allowlisted_count,
        captured_baseline=captured_baseline,
        errors=tool_errors,
        primitive_status=primitive_status,
        deployed_url=args.url,
    )

    if args.raw:
        print(render_json(report))
    else:
        print(render_markdown(report))

    print(
        f"check-security: scanned={len(files)}, findings={len(findings)}, "
        f"allowlisted={allowlisted_count}, new_since_baseline={len(newly_found)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
