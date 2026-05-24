#!/usr/bin/env python3
"""Dead-code detector (tier 6 — Evolves).

Builds a static reference graph of Python symbols; flags any defined
symbol with zero references in other files. ALL findings ship at
advisory severity per the FP-philosophy lock (dead-code detection has
inherent FP from dynamic dispatch, framework discovery, plugin loading).

Uses _lib/ shared helpers (canonical pattern per add-skill v0.6.0).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


# ─── _lib/ bootstrap ────────────────────────────────────────────────


sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _lib import allowlist, baseline, scope  # noqa: E402


# ─── Constants ──────────────────────────────────────────────────────


SCANNABLE_EXTENSIONS = {".py"}

# Skip these paths entirely (test infrastructure + tooling that uses
# convention-based discovery).
SKIP_PATH_PATTERNS = [
    re.compile(r"(^|/)tests?/"),
    re.compile(r"(^|/)__tests__/"),
    re.compile(r"_test\.py$"),
    re.compile(r"(^|/)conftest\.py$"),
    re.compile(r"(^|/)fixtures?/"),
    re.compile(r"(^|/)mocks?/"),
    re.compile(r"(^|/)\.checkup/"),
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)\.git/"),
    re.compile(r"(^|/)vendor/"),
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)build/"),
    # _lib/ directories are libraries — their public functions are
    # intended to be called from elsewhere; an unused library function
    # is "not yet adopted" not "dead." Skip from dead-code scanning.
    re.compile(r"(^|/)_lib/"),
]


def is_skipped_path(path: str) -> bool:
    return any(p.search(path) for p in SKIP_PATH_PATTERNS)


# Symbol-definition patterns (Python).
DEF_FUNCTION_RE = re.compile(r"^def\s+(\w+)\s*\(")
DEF_CLASS_RE = re.compile(r"^class\s+(\w+)[\s(:]")
DEF_CONSTANT_RE = re.compile(r"^([A-Z_][A-Z0-9_]+)\s*[:=]")
IMPORT_MODULE_RE = re.compile(r"^import\s+(\w+)(?:\s+as\s+(\w+))?")
IMPORT_FROM_RE = re.compile(r"^from\s+[\w.]+\s+import\s+(.+?)(?:\s+#.*)?$")
ALL_LIST_RE = re.compile(r"^__all__\s*=\s*\[([^\]]+)\]", re.MULTILINE)

# Exempt-from-flagging name patterns.
DUNDER_RE = re.compile(r"^__\w+__$")
TEST_PREFIX_RE = re.compile(r"^test_")
FIXTURE_DECORATOR_RE = re.compile(r"^\s*@(pytest\.)?fixture\b")


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class SymbolDef:
    name: str
    kind: str  # function | class | constant | import
    file: str
    line: int


@dataclass
class Finding:
    symbol_name: str
    symbol_kind: str
    file: str
    line: int
    founder_message: str
    suggestion: str
    signature: str


@dataclass
class ScanReport:
    project: str
    scope: str
    files_scanned: int
    symbols_defined: int
    findings: list[Finding]
    baseline_loaded: bool
    newly_found: list[str]
    newly_resolved: list[str]
    allowlisted_count: int
    captured_baseline: bool
    errors: list[str]
    primitive_status: dict = None  # type: ignore[assignment]
    hypotheses: list = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.primitive_status is None:
            self.primitive_status = {}
        if self.hypotheses is None:
            self.hypotheses = []


# ─── CQ-05 review-practices analysis (v0.22.0+) ───────────────────


def _run_review_practices_check(repo_root: Path) -> tuple[list, dict[str, str], list[str]]:
    """Analyse recent git history for review-practice signals.

    Heuristics (per codebase-assess CQ-05 hypothesis):
    - Direct-to-main commits: count of commits to main/master in the last
      90 days that DON'T have a merge-commit parent (single-parent commits
      authored directly without a PR merge).
    - Average reviewer count: parsed from `Reviewed-by:` trailers in
      commit messages (last 100 commits).
    - PR template presence: `.github/pull_request_template.md` or
      `.github/PULL_REQUEST_TEMPLATE.md`.

    Returns:
        (hypotheses, primitive_status, errors)
    """
    import subprocess

    sys_path_old = sys.path.copy()
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
    try:
        from _lib.hypothesis import Confidence, Hypothesis
    finally:
        sys.path[:] = sys_path_old

    hypotheses: list = []
    primitive_status: dict[str, str] = {}
    errors: list[str] = []

    # PR template detection (always check)
    template_paths = [
        repo_root / ".github" / "pull_request_template.md",
        repo_root / ".github" / "PULL_REQUEST_TEMPLATE.md",
        repo_root / ".github" / "PULL_REQUEST_TEMPLATE" / "default.md",
    ]
    has_template = any(p.exists() for p in template_paths)

    # Git log analysis
    try:
        # Count commits in last 90 days
        proc = subprocess.run(
            ["git", "log", "--since=90.days", "--pretty=format:%H %P"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=30, check=False,
        )
        if proc.returncode != 0:
            errors.append(f"git log failed: {proc.stderr[:200]}")
            primitive_status["CQ-05"] = "NOT_ASSESSED"
            return hypotheses, primitive_status, errors

        commits = [line.strip().split(" ", 1) for line in proc.stdout.splitlines() if line.strip()]
        total = len(commits)
        merge_commits = sum(1 for c in commits if len(c) > 1 and len(c[1].split()) > 1)
        direct_commits = total - merge_commits
        direct_pct = (direct_commits / total * 100) if total else 0

        # Reviewer-trailer scan (last 100 commits)
        proc2 = subprocess.run(
            ["git", "log", "-100", "--pretty=format:%b"],
            cwd=str(repo_root), capture_output=True, text=True, timeout=30, check=False,
        )
        body = proc2.stdout if proc2.returncode == 0 else ""
        reviewer_lines = sum(1 for line in body.splitlines() if line.lower().startswith("reviewed-by:"))
        reviewer_per_100 = reviewer_lines  # rough proxy

        # Form hypothesis
        signals = []
        signals.append(f"{direct_pct:.0f}% direct-to-main commits (last 90 days; {direct_commits} of {total})")
        signals.append(f"PR template: {'present' if has_template else 'absent'}")
        signals.append(f"Reviewed-by trailers in last 100 commits: {reviewer_per_100}")

        # Confidence calibration
        if total < 10:
            confidence = Confidence.UNVALIDATED
            statement = "Not enough commit history (last 90 days) to assess review practices"
        elif direct_pct > 50 and not has_template:
            confidence = Confidence.SUPPORTED
            statement = "Review practices likely informal: high direct-to-main ratio + no PR template"
        elif direct_pct < 10 and has_template and reviewer_per_100 > 20:
            confidence = Confidence.SUPPORTED
            statement = "Review practices appear formal: low direct-to-main + PR template + reviewer trailers"
        elif direct_pct < 30:
            confidence = Confidence.EMERGING
            statement = f"Review practices likely moderate: {direct_pct:.0f}% direct-to-main commits"
        else:
            confidence = Confidence.EMERGING
            statement = f"Review practices unclear: {direct_pct:.0f}% direct-to-main commits, template={'yes' if has_template else 'no'}"

        hypotheses.append(Hypothesis(
            primitive_id="CQ-05",
            statement=statement,
            evidence=signals,
            confidence=confidence,
            verification_question="Does the team have a documented review process? How are direct-to-main commits authorised?",
        ))
        primitive_status["CQ-05"] = "HYPOTHESIS"
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
        errors.append(f"CQ-05 git log analysis failed: {exc}")
        primitive_status["CQ-05"] = "NOT_ASSESSED"

    return hypotheses, primitive_status, errors


# ─── Symbol extraction ──────────────────────────────────────────────


def extract_definitions(rel_path: str, text: str) -> tuple[list[SymbolDef], set[str]]:
    """Return (defined symbols, names in __all__).

    Skip: indented defs (methods, nested), dunder names, names matching
    test convention. __all__ exports are tracked separately to mark
    public-API.
    """
    defs: list[SymbolDef] = []
    all_names: set[str] = set()

    # __all__ scan (find anywhere in the file)
    all_match = ALL_LIST_RE.search(text)
    if all_match:
        for entry in all_match.group(1).split(","):
            cleaned = entry.strip().strip("'\"")
            if cleaned:
                all_names.add(cleaned)

    fixture_decorated = False
    for lineno, line in enumerate(text.splitlines(), start=1):
        # Track fixture decorator (affects next def)
        if FIXTURE_DECORATOR_RE.match(line):
            fixture_decorated = True
            continue

        # Top-level only (no leading indent)
        if line and line[0].isspace():
            fixture_decorated = False
            continue
        if line.strip().startswith(("#", '"', "'")):
            continue

        m = DEF_FUNCTION_RE.match(line)
        if m:
            name = m.group(1)
            if DUNDER_RE.match(name):
                fixture_decorated = False
                continue
            if TEST_PREFIX_RE.match(name):
                fixture_decorated = False
                continue
            if fixture_decorated:
                fixture_decorated = False
                continue
            # Skip private names with length > 4 (founder knows they're internal)
            if name.startswith("_") and len(name) > 4:
                continue
            defs.append(SymbolDef(name, "function", rel_path, lineno))
            fixture_decorated = False
            continue

        m = DEF_CLASS_RE.match(line)
        if m:
            name = m.group(1)
            if DUNDER_RE.match(name):
                continue
            if name.startswith("_") and len(name) > 4:
                continue
            defs.append(SymbolDef(name, "class", rel_path, lineno))
            continue

        m = DEF_CONSTANT_RE.match(line)
        if m:
            name = m.group(1)
            # ALL_CAPS constants only (single-char is over-broad)
            if len(name) < 3:
                continue
            defs.append(SymbolDef(name, "constant", rel_path, lineno))
            continue

        m = IMPORT_MODULE_RE.match(line)
        if m:
            alias = m.group(2) or m.group(1)
            defs.append(SymbolDef(alias, "import", rel_path, lineno))
            continue

        m = IMPORT_FROM_RE.match(line)
        if m:
            names = m.group(1).strip()
            # Handle (a, b, c) parenthesised AND `a, b, c` forms
            names = names.strip("()")
            for raw in names.split(","):
                bits = raw.strip().split()
                if not bits:
                    continue
                # `name as alias` → alias is what's defined
                if len(bits) >= 3 and bits[1] == "as":
                    name = bits[2]
                else:
                    name = bits[0]
                if name and name != "*":
                    defs.append(SymbolDef(name, "import", rel_path, lineno))

    return defs, all_names


# ─── Reference counting ─────────────────────────────────────────────


def build_reference_index(repo_root: Path, files: list[str]) -> dict[str, int]:
    """For each unique symbol name, count whole-word matches across all
    files except where it's defined. Returns name → count (excluding
    self-references).

    Comment-stripping is approximate (strip everything after `#` on a
    line). Docstring contents NOT stripped (heuristic too noisy).
    """
    # First pass: load all file contents (small marketplace ~hundreds of files)
    file_contents: dict[str, str] = {}
    for f in files:
        path = repo_root / f
        if not path.is_file():
            continue
        try:
            file_contents[f] = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

    # Build ref-counts per name (across all files; we'll subtract
    # self-file count later when checking each definition).
    ref_counts: dict[str, dict[str, int]] = {}  # name → {file: count}

    # We need all candidate names first. Build set of "names of interest"
    # from all definitions across all files. (Cheap two-pass.)
    names_of_interest: set[str] = set()
    for rel_path, text in file_contents.items():
        if is_skipped_path(rel_path):
            continue
        defs, _ = extract_definitions(rel_path, text)
        for d in defs:
            names_of_interest.add(d.name)

    # Walk each file once; tokenise into identifier-like substrings and
    # count occurrences against the names-of-interest set. This is O(text
    # length) per file, NOT O(names × lines). Critical for large
    # marketplaces — the per-line per-name regex.search version is too
    # slow.
    names_long_enough = {n for n in names_of_interest if len(n) >= 3}
    identifier_re = re.compile(r"\b[A-Za-z_]\w+\b")

    for rel_path, text in file_contents.items():
        # Strip line comments cheaply (works for # and // style)
        lines_clean = []
        for line in text.splitlines():
            idx = line.find("#")
            if idx >= 0:
                line = line[:idx]
            lines_clean.append(line)
        joined = "\n".join(lines_clean)
        # Find every identifier-token in the file; intersect with names set
        per_file: dict[str, int] = {}
        for token in identifier_re.findall(joined):
            if token in names_long_enough:
                per_file[token] = per_file.get(token, 0) + 1
        for name, count in per_file.items():
            ref_counts.setdefault(name, {})
            ref_counts[name][rel_path] = count

    # Flatten: total references per name
    flat: dict[str, int] = {n: sum(per.values()) for n, per in ref_counts.items()}
    return flat, ref_counts


# ─── Scanner ────────────────────────────────────────────────────────


def scan(repo_root: Path, files: list[str], all_symbols: dict[str, list[SymbolDef]],
         all_names_per_file: dict[str, set[str]], ref_counts: dict[str, int],
         ref_counts_per_file: dict[str, dict[str, int]]) -> list[Finding]:
    findings: list[Finding] = []
    for rel_path in files:
        if is_skipped_path(rel_path):
            continue
        defs = all_symbols.get(rel_path, [])
        all_exports = all_names_per_file.get(rel_path, set())

        for sym in defs:
            # Skip if in __all__
            if sym.name in all_exports:
                continue
            # Skip if name is "main" or matches the filename stem (CLI entry)
            stem = Path(rel_path).stem.lower()
            if sym.name == "main" or sym.name.lower() == stem:
                continue
            # Skip if very short (FP-prone)
            if len(sym.name) < 3:
                continue
            # Count refs across ALL files INCLUDING the self-file (a
            # module-level constant USED in the same file is referenced).
            # The token-scan counts the definition line itself as 1 hit,
            # so the test is "more than 1 reference total" — anything ≤1
            # means only the def line matched (no uses).
            per_file = ref_counts_per_file.get(sym.name, {})
            total_refs = sum(per_file.values())
            if total_refs > 1:
                continue
            # Dead
            kind_msg = {
                "function": "function",
                "class": "class",
                "constant": "constant",
                "import": "import",
            }[sym.kind]
            sig = f"dead-{sym.kind}::{rel_path}::{sym.line}::{sym.name}"
            findings.append(Finding(
                symbol_name=sym.name,
                symbol_kind=sym.kind,
                file=rel_path,
                line=sym.line,
                founder_message=(
                    f"{kind_msg} `{sym.name}` has no detected references "
                    "elsewhere — possibly dead code"
                ),
                suggestion=(
                    "consider removing if confirmed unused; review for "
                    "dynamic-dispatch (getattr, plugin registries) first"
                ),
                signature=sig,
            ))
    return findings


# ─── Rendering ──────────────────────────────────────────────────────


def render_json(report: ScanReport) -> str:
    findings_out = [
        {
            "heuristic": f"dead-{f.symbol_kind}",
            "severity": "advisory",
            "file": f.file,
            "line": f.line,
            "identifier": f.symbol_name,
            "message": f.founder_message,
            "suggestion": f.suggestion,
            "extras": {"signature": f.signature, "kind": f.symbol_kind},
        }
        for f in report.findings
    ]
    return json.dumps({
        "project": report.project,
        "scope": report.scope,
        "files_scanned": report.files_scanned,
        "symbols_defined": report.symbols_defined,
        "findings_count": len(report.findings),
        "findings": findings_out,
        "newly_found": report.newly_found,
        "newly_resolved": report.newly_resolved,
        "allowlisted_count": report.allowlisted_count,
        "captured_baseline": report.captured_baseline,
        "errors": report.errors,
        "primitive_status": report.primitive_status,
        "hypotheses": [h.to_dict() if hasattr(h, "to_dict") else h for h in report.hypotheses],
    }, indent=2)


def render_markdown(report: ScanReport) -> str:
    out: list[str] = []
    out.append(f"# Maintainability check — {report.project}")
    out.append("")

    if report.captured_baseline:
        out.append(
            f"**First run.** Captured baseline ({len(report.findings)} pre-existing advisory findings will not be re-flagged). Next run will detect any newly-dead code."
        )
        out.append("")

    out.append(f"**Files scanned:** {report.files_scanned}")
    out.append(f"**Symbols analysed:** {report.symbols_defined}")
    out.append(f"**Findings:** {len(report.findings)} (advisory, allowlisted: {report.allowlisted_count})")
    out.append("")

    if report.newly_found:
        verdict = f"ℹ {len(report.newly_found)} newly-dead symbol(s) since baseline"
    elif report.findings:
        verdict = f"ℹ {len(report.findings)} pre-existing advisory finding(s) — review before deleting"
    else:
        verdict = "✓ Clear — no detected dead code"
    out.append(f"**Verdict:** {verdict}")
    out.append("")

    if report.findings:
        by_kind: dict[str, list[Finding]] = {}
        for f in report.findings:
            by_kind.setdefault(f.symbol_kind, []).append(f)
        for kind in ("function", "class", "constant", "import"):
            items = by_kind.get(kind, [])
            if not items:
                continue
            out.append(f"## ℹ Possibly-dead {kind}{'s' if len(items) != 1 else ''} — {len(items)}")
            out.append("")
            for f in items[:15]:
                new_tag = " 🆕 NEW" if f.signature in report.newly_found else ""
                out.append(f"- `{f.file}:{f.line}` — `{f.symbol_name}`{new_tag}")
                out.append(f"  - {f.founder_message}")
            if len(items) > 15:
                out.append(f"- _…and {len(items) - 15} more — pass `--raw` for full list._")
            out.append("")

    out.append("---")
    out.append("_This skill is read-only. It identifies possibly-dead code; never modifies._")
    out.append("_All findings are ADVISORY — static dead-code detection has false positives from dynamic dispatch / plugin systems / external API consumers. Review each before deleting._")
    return "\n".join(out)


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Dead-code detector.")
    parser.add_argument("--project", default=None)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--scope", default="auto", choices=("auto", "pr", "codebase"))
    parser.add_argument("--base-branch", default=None)
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--raw", action="store_true")
    parser.add_argument("--skip-cq05", action="store_true",
        help="skip CQ-05 review-practices git-log analysis")
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

    # Read everything once
    file_texts: dict[str, str] = {}
    for f in files:
        path = repo_root / f
        if not path.is_file():
            continue
        try:
            file_texts[f] = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

    # Extract symbols + __all__ per file
    all_symbols: dict[str, list[SymbolDef]] = {}
    all_names_per_file: dict[str, set[str]] = {}
    symbol_total = 0
    for rel_path, text in file_texts.items():
        defs, exports = extract_definitions(rel_path, text)
        all_symbols[rel_path] = defs
        all_names_per_file[rel_path] = exports
        symbol_total += len(defs)

    # Build reference graph across ALL files (including tests — they
    # reference production code, which counts).
    # ALSO include extensionless Python scripts (detected by shebang).
    # Without this, _wpxlib.py symbols like cli_main / add_common_args /
    # PlanResult / find_change_branches appear "dead" because they're
    # used in scripts/wpx-pipeline, scripts/wpx-worktree, scripts/sulis-
    # change — files with no .py extension that won't match
    # SCANNABLE_EXTENSIONS. Real bug; surfaced during cleanup-iteration
    # round 3.
    full_files = scope.list_codebase_files(repo_root, SCANNABLE_EXTENSIONS) if resolved_scope == "codebase" else files
    # Add extensionless scripts that look Python (shebang-detected)
    all_tracked = scope.list_codebase_files(repo_root, None)
    for candidate in all_tracked:
        if candidate in full_files or is_skipped_path(candidate):
            continue
        if Path(candidate).suffix:
            continue  # has an extension; if not .py, not relevant
        # Extensionless: check shebang
        candidate_path = repo_root / candidate
        if not candidate_path.is_file():
            continue
        try:
            first_line = candidate_path.read_text(encoding="utf-8", errors="ignore")[:200]
        except OSError:
            continue
        if first_line.startswith("#!") and "python" in first_line.split("\n", 1)[0]:
            full_files.append(candidate)
    for f in full_files:
        if f not in file_texts:
            path = repo_root / f
            if path.is_file():
                try:
                    file_texts[f] = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue

    ref_counts, ref_counts_per_file = build_reference_index(repo_root, list(file_texts.keys()))

    # Allowlist
    project_allow = allowlist.project_allowlist_path(repo_root, args.project, "check-maintainability")
    allow_signatures = allowlist.load_allowlist(project_allow)

    findings = scan(
        repo_root, files, all_symbols, all_names_per_file,
        ref_counts, ref_counts_per_file,
    )

    # Apply allowlist
    pre_allow = len(findings)
    findings = [f for f in findings if f.signature not in allow_signatures]
    allowlisted_count = pre_allow - len(findings)

    # Baseline
    baseline_sigs = set(baseline.load_namespace(repo_root, args.project, "tier_6_findings", []))
    baseline_loaded = bool(baseline_sigs)
    current_sigs = {f.signature for f in findings}
    newly_found = sorted(current_sigs - baseline_sigs) if baseline_loaded else []
    newly_resolved = sorted(baseline_sigs - current_sigs) if baseline_loaded else []

    captured_baseline = False
    if (not baseline_loaded or args.update_baseline) and current_sigs:
        baseline.save_namespace(repo_root, args.project, "tier_6_findings", sorted(current_sigs))
        captured_baseline = True

    # CQ-05 review-practices hypothesis (v0.22.0+)
    hypotheses: list = []
    primitive_status: dict[str, str] = {}
    if not args.skip_cq05:
        try:
            hypotheses, primitive_status, cq05_errors = _run_review_practices_check(repo_root)
            scope_errors.extend(cq05_errors)
        except Exception as exc:  # noqa: BLE001
            scope_errors.append(f"CQ-05 review-practices check failed: {exc}")
            primitive_status["CQ-05"] = "NOT_ASSESSED"
    else:
        primitive_status["CQ-05"] = "NOT_ASSESSED"

    report = ScanReport(
        project=args.project,
        scope=resolved_scope,
        files_scanned=len(files),
        symbols_defined=symbol_total,
        findings=findings,
        baseline_loaded=baseline_loaded,
        newly_found=newly_found,
        newly_resolved=newly_resolved,
        allowlisted_count=allowlisted_count,
        captured_baseline=captured_baseline,
        errors=scope_errors,
        primitive_status=primitive_status,
        hypotheses=hypotheses,
    )

    if args.raw:
        print(render_json(report))
    else:
        print(render_markdown(report))

    print(
        f"check-maintainability: files={len(files)}, symbols={symbol_total}, "
        f"findings={len(findings)}, allowlisted={allowlisted_count}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
