#!/usr/bin/env python3
"""Build-and-manifest-hygiene checker.

Tier-1 regression detection: did the project's build stop working?
Are the manifest files semantically correct?

Same baseline + signature-dedup pattern as check-tests; uses the same
.checkup/{project}/baseline.json file under tier_1_* keys (separate
namespace from tier_3 to avoid collision).

Usage:

    python3 builder.py [--run] [--system NAME] [--no-side-effects-check] [--raw]

Exit codes:
- 0 = success
- 1 = usage error
- 2 = filesystem / git error
- 3 = build runner failed (when --run)
- 4 = no build system detected
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
from _lib import baseline as _baseline  # noqa: E402


DEFAULT_TIMEOUT_SECONDS = 180


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class BuildSystem:
    name: str  # pip | npm | go | cargo | docker | make
    detected_at: str  # path that triggered detection
    confidence: str  # high | medium | low


@dataclass
class BuildResult:
    system: str
    status: str  # passed | failed | skipped | not_run
    exit_code: int | None
    error_summary: str  # short, founder-readable
    raw_stderr_excerpt: str  # operator-grade


@dataclass
class HygieneFinding:
    rule: str  # MH-001, PH-101, MM-103, etc.
    severity: str  # high | concern | advisory
    file: str
    message: str  # founder-readable
    raw_value: str = ""  # operator-grade


@dataclass
class BuilderReport:
    project: str
    repo_root: str
    detected_systems: list[BuildSystem]
    build_results: list[BuildResult]
    hygiene_findings: list[HygieneFinding]
    baseline_loaded: bool
    newly_broken_systems: list[str]
    newly_fixed_systems: list[str]
    captured_baseline: bool
    errors: list[str]


# ─── Side-effect blocklist ──────────────────────────────────────────


DANGEROUS_TARGET_PATTERNS = [
    re.compile(r"^(publish|deploy|release|push|upload)(:[\w-]+)?$"),
    re.compile(r"^[\w-]+:(publish|deploy|release|push|upload)$"),
    re.compile(r"^notify:[\w-]+$"),
]


def is_dangerous_target(target: str) -> bool:
    return any(p.match(target) for p in DANGEROUS_TARGET_PATTERNS)


# ─── Detection ──────────────────────────────────────────────────────


def detect_systems(repo_root: Path) -> list[BuildSystem]:
    out: list[BuildSystem] = []

    # pip
    if (repo_root / "pyproject.toml").is_file():
        try:
            text = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
            if "[project]" in text or "[tool.poetry]" in text:
                out.append(BuildSystem("pip", "pyproject.toml", "high"))
        except OSError:
            pass
    elif (repo_root / "setup.py").is_file():
        out.append(BuildSystem("pip", "setup.py", "high"))
    elif (repo_root / "requirements.txt").is_file():
        out.append(BuildSystem("pip", "requirements.txt", "medium"))

    # npm/yarn/pnpm
    if (repo_root / "package.json").is_file():
        try:
            pkg = json.loads((repo_root / "package.json").read_text(encoding="utf-8"))
            if (pkg.get("scripts") or {}).get("build"):
                if (repo_root / "pnpm-lock.yaml").is_file():
                    out.append(BuildSystem("pnpm", "package.json", "high"))
                elif (repo_root / "yarn.lock").is_file():
                    out.append(BuildSystem("yarn", "package.json", "high"))
                else:
                    out.append(BuildSystem("npm", "package.json", "high"))
        except (json.JSONDecodeError, OSError):
            pass

    # go
    if (repo_root / "go.mod").is_file():
        out.append(BuildSystem("go", "go.mod", "high"))

    # cargo
    if (repo_root / "Cargo.toml").is_file():
        out.append(BuildSystem("cargo", "Cargo.toml", "high"))

    # docker
    if (repo_root / "Dockerfile").is_file():
        out.append(BuildSystem("docker", "Dockerfile", "medium"))

    # make
    makefile = next((p for p in [repo_root / "Makefile", repo_root / "makefile"] if p.is_file()), None)
    if makefile:
        try:
            text = makefile.read_text(encoding="utf-8")
            if re.search(r"^(build|all):", text, re.MULTILINE):
                out.append(BuildSystem("make", str(makefile.relative_to(repo_root)), "low"))
        except OSError:
            pass

    return out


# ─── Build runners ──────────────────────────────────────────────────


def run_build(system: BuildSystem, repo_root: Path, timeout: int,
              check_side_effects: bool) -> BuildResult:
    cmd = _build_cmd(system, repo_root, check_side_effects)
    if cmd is None:
        return BuildResult(
            system=system.name, status="skipped", exit_code=None,
            error_summary="skipped — only dangerous targets available (use --allow-side-effects)",
            raw_stderr_excerpt="",
        )
    try:
        proc = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return BuildResult(
            system=system.name, status="failed", exit_code=None,
            error_summary=f"build timed out after {timeout}s",
            raw_stderr_excerpt="",
        )
    except FileNotFoundError as exc:
        return BuildResult(
            system=system.name, status="failed", exit_code=None,
            error_summary=f"{system.name} tool not installed",
            raw_stderr_excerpt=str(exc),
        )

    if proc.returncode == 0:
        return BuildResult(
            system=system.name, status="passed", exit_code=0,
            error_summary="build succeeded",
            raw_stderr_excerpt=proc.stderr[:500],
        )

    return BuildResult(
        system=system.name, status="failed", exit_code=proc.returncode,
        error_summary=_translate_error(system.name, proc.stderr + proc.stdout),
        raw_stderr_excerpt=(proc.stderr or proc.stdout)[:1000],
    )


def _build_cmd(system: BuildSystem, repo_root: Path, check_side_effects: bool) -> list[str] | None:
    if system.name == "pip":
        # Prefer python -m build (modern) but fall back to pip install -e .
        return ["python3", "-m", "pip", "install", "--dry-run", "-e", str(repo_root)]
    if system.name in ("npm", "yarn", "pnpm"):
        return [system.name, "run", "build"]
    if system.name == "go":
        return ["go", "build", "./..."]
    if system.name == "cargo":
        return ["cargo", "build"]
    if system.name == "docker":
        return ["docker", "build", "-t", f"{repo_root.name}:check", "."]
    if system.name == "make":
        target = "build" if _make_has_target(repo_root, "build") else "all"
        if check_side_effects and is_dangerous_target(target):
            return None
        return ["make", target]
    return None


def _make_has_target(repo_root: Path, target: str) -> bool:
    makefile = next((p for p in [repo_root / "Makefile", repo_root / "makefile"] if p.is_file()), None)
    if not makefile:
        return False
    try:
        text = makefile.read_text(encoding="utf-8")
        return bool(re.search(rf"^{re.escape(target)}:", text, re.MULTILINE))
    except OSError:
        return False


def _translate_error(system: str, output: str) -> str:
    """Translate common error patterns to founder-readable strings."""
    translations = {
        "pip": [
            (r"ResolutionImpossible", "couldn't figure out which package versions to install — there's a conflict between dependencies"),
            (r"ModuleNotFoundError: No module named ['\"](\w+)", lambda m: f"build tried to import `{m.group(1)}` but couldn't find it — likely a missing dependency"),
            (r"subprocess-exited-with-error", "a package's installer crashed while trying to build itself"),
            (r"Permission denied", "build doesn't have permission to write somewhere it needs to — often fixed with a virtualenv"),
        ],
        "npm": [
            (r"ENOENT.*?'(.+?)'", lambda m: f"build can't find file `{m.group(1)}`"),
            (r"E(TIMEDOUT|CONNREFUSED)", "build couldn't reach the npm registry — check network or registry config"),
            (r"npm ERR! missing script: (\w+)", lambda m: f"package.json doesn't have the `{m.group(1)}` script the build is trying to run"),
            (r"E(ACCES|PERM)", "permission issue — typically a permissions problem on node_modules/"),
        ],
        "go": [
            (r"cannot find module providing package (.+)", lambda m: f"couldn't find module {m.group(1).strip()} — check `go.mod`"),
            (r"undefined: (\w+)", lambda m: f"code uses `{m.group(1)}` but it's not defined — likely a missing import or typo"),
        ],
        "docker": [
            (r"Cannot connect to the Docker daemon", "Docker isn't running — start Docker Desktop or the daemon"),
            (r"pull access denied", "Docker can't pull a base image — check registry auth or image name"),
        ],
    }
    rules = translations.get(system, [])
    for pattern, replacement in rules:
        match = re.search(pattern, output)
        if match:
            if callable(replacement):
                return replacement(match)
            return replacement
    # Fallback: first non-blank stderr line
    for line in output.splitlines():
        line = line.strip()
        if line and not line.startswith("Warning"):
            return line[:200]
    return f"{system} build failed (no specific error pattern matched)"


# ─── Manifest hygiene ───────────────────────────────────────────────


SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+(-[\w.]+)?(\+[\w.]+)?$")
KEBAB_CASE_RE = re.compile(r"^[a-z][a-z0-9-]*$")


def check_manifest_hygiene(repo_root: Path) -> list[HygieneFinding]:
    findings: list[HygieneFinding] = []

    # Common: every .claude-plugin/plugin.json
    for plugin_json in repo_root.rglob(".claude-plugin/plugin.json"):
        rel = str(plugin_json.relative_to(repo_root))
        findings.extend(_check_plugin_json(plugin_json, rel))

    # marketplace.json at root
    mp = repo_root / ".claude-plugin" / "marketplace.json"
    if mp.is_file():
        findings.extend(_check_marketplace_json(mp, str(mp.relative_to(repo_root))))

    # package.json files (not in node_modules)
    for pkg in repo_root.rglob("package.json"):
        if "node_modules" in pkg.parts:
            continue
        rel = str(pkg.relative_to(repo_root))
        findings.extend(_check_package_json(pkg, rel))

    return findings


def _check_plugin_json(path: Path, rel: str) -> list[HygieneFinding]:
    findings: list[HygieneFinding] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [HygieneFinding(
            rule="MH-001", severity="high", file=rel,
            message=f"plugin.json doesn't parse as JSON: {exc.msg} at line {exc.lineno}",
            raw_value=str(exc),
        )]
    except OSError as exc:
        return [HygieneFinding(
            rule="MH-001", severity="high", file=rel,
            message=f"can't read: {exc}",
            raw_value=str(exc),
        )]

    name = data.get("name", "")
    if not name:
        findings.append(HygieneFinding("PH-101", "high", rel, "plugin.json is missing the `name` field"))
    elif not KEBAB_CASE_RE.match(name) or len(name) > 50:
        findings.append(HygieneFinding("PH-101", "high", rel, f"plugin name `{name}` must be kebab-case and ≤50 chars"))

    version = data.get("version", "")
    if not version:
        findings.append(HygieneFinding("PH-102", "high", rel, "plugin.json is missing the `version` field"))
    elif not SEMVER_RE.match(version):
        findings.append(HygieneFinding("PH-102", "high", rel, f"version `{version}` is not valid semver (X.Y.Z)"))

    desc = data.get("description", "")
    if not desc:
        findings.append(HygieneFinding("PH-103", "high", rel, "plugin.json is missing the `description` field"))
    elif len(desc) > 500:
        findings.append(HygieneFinding(
            "PH-103", "concern", rel,
            f"description is {len(desc)} chars (recommended max 500 per HD-004 — move cumulative history to CHANGELOG.md)",
            raw_value=f"len={len(desc)}",
        ))

    if not data.get("repository"):
        findings.append(HygieneFinding("PH-104", "concern", rel, "plugin.json is missing the `repository` field (recommended if shipping to a marketplace)"))

    if not data.get("keywords") or len(data.get("keywords") or []) < 3:
        findings.append(HygieneFinding("PH-105", "advisory", rel, "plugin.json should have ≥3 keywords for discoverability"))

    return findings


def _check_marketplace_json(path: Path, rel: str) -> list[HygieneFinding]:
    findings: list[HygieneFinding] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [HygieneFinding("MH-001", "high", rel, f"marketplace.json doesn't parse: {exc}")]

    metadata = data.get("metadata", {})
    version = metadata.get("version", "")
    if not version:
        findings.append(HygieneFinding("MM-101", "high", rel, "marketplace.json is missing `metadata.version`"))
    elif not SEMVER_RE.match(version):
        findings.append(HygieneFinding("MM-101", "high", rel, f"marketplace version `{version}` is not valid semver"))

    plugins = data.get("plugins", [])
    if not plugins:
        findings.append(HygieneFinding("MM-102", "high", rel, "marketplace.json has no `plugins` array entries"))

    for i, p in enumerate(plugins):
        prefix = f"plugin[{i}]"
        if not p.get("name"):
            findings.append(HygieneFinding("MM-103", "high", rel, f"{prefix} is missing `name`"))
        if not p.get("source"):
            findings.append(HygieneFinding("MM-103", "high", rel, f"{prefix} is missing `source`"))
        if not p.get("version"):
            findings.append(HygieneFinding("MM-103", "high", rel, f"{prefix} is missing `version`"))
        desc = p.get("description", "")
        if not desc:
            findings.append(HygieneFinding("MM-103", "high", rel, f"{prefix} is missing `description`"))
        elif len(desc) > 500:
            findings.append(HygieneFinding(
                "MM-104", "concern", rel,
                f"{prefix} (`{p.get('name', '?')}`) description is {len(desc)} chars (recommended max 500)",
                raw_value=f"len={len(desc)}",
            ))
        # MM-105: source path exists
        src = p.get("source", "")
        if src.startswith("./") and not (path.parent.parent / src[2:]).exists():
            findings.append(HygieneFinding("MM-105", "advisory", rel, f"{prefix} source path `{src}` doesn't exist"))

    return findings


def _check_package_json(path: Path, rel: str) -> list[HygieneFinding]:
    findings: list[HygieneFinding] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return [HygieneFinding("MH-001", "high", rel, f"package.json doesn't parse: {exc}")]

    if not data.get("name"):
        findings.append(HygieneFinding("PJ-101", "high", rel, "package.json is missing `name`"))

    version = data.get("version", "")
    if not version:
        findings.append(HygieneFinding("PJ-102", "high", rel, "package.json is missing `version`"))
    elif not SEMVER_RE.match(version):
        findings.append(HygieneFinding("PJ-102", "high", rel, f"version `{version}` is not valid semver"))

    return findings


# ─── Baseline (tier_1 namespace; uses _lib/baseline since v0.11.x) ─


def load_baseline_tier1(repo_root: Path, project: str) -> dict[str, str]:
    return _baseline.load_namespace(repo_root, project, "tier_1_systems", {})


def save_baseline_tier1(repo_root: Path, project: str, systems: dict[str, str]) -> None:
    _baseline.save_namespace(repo_root, project, "tier_1_systems", systems)


# ─── Rendering ──────────────────────────────────────────────────────


def render_json(report: BuilderReport) -> str:
    # Orchestrator-compatible findings: each failed build + each high/concern hygiene finding
    findings = []
    for b in report.build_results:
        if b.status == "failed":
            findings.append({
                "heuristic": "build-failure",
                "severity": "high",
                "file": "(build)",
                "line": 0,
                "identifier": b.system,
                "message": f"{b.system} build failed: {b.error_summary}",
                "suggestion": "investigate the build error in the system's tooling",
                "extras": {"exit_code": b.exit_code, "raw": b.raw_stderr_excerpt[:300]},
            })
    for h in report.hygiene_findings:
        if h.severity in ("high", "concern"):
            findings.append({
                "heuristic": "manifest-hygiene",
                "severity": h.severity,
                "file": h.file,
                "line": 0,
                "identifier": h.rule,
                "message": h.message,
                "suggestion": "",
                "extras": {"rule": h.rule, "raw": h.raw_value},
            })

    return json.dumps({
        "project": report.project,
        "detected_systems": [asdict(s) for s in report.detected_systems],
        "build_results": [asdict(b) for b in report.build_results],
        "hygiene_findings": [asdict(h) for h in report.hygiene_findings],
        "newly_broken_systems": report.newly_broken_systems,
        "newly_fixed_systems": report.newly_fixed_systems,
        "captured_baseline": report.captured_baseline,
        "findings": findings,
        "errors": report.errors,
    }, indent=2)


def render_markdown(report: BuilderReport) -> str:
    out: list[str] = []
    out.append(f"# Build check — {report.project}")
    out.append("")

    if report.captured_baseline and not report.baseline_loaded:
        out.append(f"**First run.** Captured build baseline ({len(report.build_results)} systems). Next run will detect any newly-broken builds.")
        out.append("")

    if report.detected_systems:
        out.append(f"**Build systems detected:** {', '.join(s.name for s in report.detected_systems)}")
        out.append("")
    else:
        out.append("_No build systems detected (looked for pip, npm, go, cargo, docker, make). Manifest hygiene still ran._")
        out.append("")

    # Verdict
    failures = [b for b in report.build_results if b.status == "failed"]
    high_hygiene = [h for h in report.hygiene_findings if h.severity == "high"]
    concern_hygiene = [h for h in report.hygiene_findings if h.severity == "concern"]

    if report.newly_broken_systems:
        verdict = f"⚠ Something broke — {len(report.newly_broken_systems)} build that was passing now failing"
    elif failures:
        verdict = f"🟡 {len(failures)} build failing (no baseline to compare against)"
    elif high_hygiene:
        verdict = f"⚠ {len(high_hygiene)} manifest issue need{'s' if len(high_hygiene)==1 else ''} attention"
    elif concern_hygiene:
        verdict = f"🟡 {len(concern_hygiene)} manifest concern{'s' if len(concern_hygiene)!=1 else ''} worth fixing"
    elif report.build_results:
        verdict = "✓ Builds — all good"
    else:
        verdict = "✓ Detection-only — pass `--run` to verify"

    out.append(f"**Verdict:** {verdict}")
    out.append("")

    # Per-system build result
    if report.build_results:
        out.append("## Builds")
        out.append("")
        for b in report.build_results:
            icon = {"passed": "✓", "failed": "❌", "skipped": "⏭", "not_run": "○"}[b.status]
            out.append(f"- {icon} **{b.system}**: {b.error_summary}")
        out.append("")

    # Hygiene findings
    if report.hygiene_findings:
        out.append("## Manifest hygiene")
        out.append("")
        for h in sorted(report.hygiene_findings, key=lambda x: (x.severity != "high", x.severity != "concern")):
            icon = {"high": "❌", "concern": "🟡", "advisory": "ℹ"}.get(h.severity, "•")
            out.append(f"- {icon} `{h.file}` — {h.message}")
        out.append("")

    if report.errors:
        out.append("## Errors")
        for e in report.errors:
            out.append(f"- {e}")
        out.append("")

    out.append("---")
    out.append("_This skill is read-only. It identifies what's broken; it never modifies code._")
    return "\n".join(out)


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Build + manifest-hygiene checker.")
    parser.add_argument("--project", default=None)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--system", default=None, help="Force a specific build system")
    parser.add_argument("--run", action="store_true", help="Actually run the build")
    parser.add_argument("--no-run", action="store_true", help="Detection + hygiene only")
    parser.add_argument("--allow-side-effects", action="store_true", help="Allow dangerous Make targets (publish, deploy, release)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--raw", action="store_true")
    # Orchestrator-compatibility flags (accepted but unused in v1)
    parser.add_argument("--scope", default=None)
    parser.add_argument("--base-branch", default=None)
    parser.add_argument("--pr-number", default=None)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    if not (repo_root / ".git").exists():
        print(f"error: {repo_root} is not a git repo", file=sys.stderr)
        return 2

    if args.project is None:
        args.project = repo_root.name

    errors: list[str] = []

    # Always run hygiene (cheap, no side effects)
    hygiene = check_manifest_hygiene(repo_root)

    # Detect systems
    systems = detect_systems(repo_root)
    if args.system:
        systems = [s for s in systems if s.name == args.system]
        if not systems:
            print(f"error: build system '{args.system}' not detected", file=sys.stderr)
            return 4

    # NB: empty (systems + hygiene) is a PASSABLE state when there are
    # genuinely no manifests + no build systems in the project. Tier
    # wrappers (code-health) need this to register as "passed" not
    # "error". Standalone users see the markdown output which still
    # explains "No build systems detected" cleanly.

    # Build runs (if --run)
    build_results: list[BuildResult] = []
    if args.run and not args.no_run:
        for system in systems:
            result = run_build(system, repo_root, args.timeout, check_side_effects=not args.allow_side_effects)
            build_results.append(result)

    # Baseline + delta
    baseline = load_baseline_tier1(repo_root, args.project)
    baseline_loaded = bool(baseline)
    current = {b.system: b.status for b in build_results}

    newly_broken = [s for s, st in current.items() if baseline.get(s) == "passed" and st == "failed"]
    newly_fixed = [s for s, st in current.items() if baseline.get(s) == "failed" and st == "passed"]

    captured_baseline = False
    if build_results and (not baseline_loaded or args.update_baseline):
        save_baseline_tier1(repo_root, args.project, current)
        captured_baseline = True

    report = BuilderReport(
        project=args.project,
        repo_root=str(repo_root),
        detected_systems=systems,
        build_results=build_results,
        hygiene_findings=hygiene,
        baseline_loaded=baseline_loaded,
        newly_broken_systems=newly_broken,
        newly_fixed_systems=newly_fixed,
        captured_baseline=captured_baseline,
        errors=errors,
    )

    if args.raw:
        print(render_json(report))
    else:
        print(render_markdown(report))

    print(
        f"check-build: systems={len(systems)}, hygiene={len(hygiene)}, "
        f"newly_broken={len(newly_broken)}, captured_baseline={captured_baseline}",
        file=sys.stderr,
    )

    return 0


if __name__ == "__main__":
    sys.exit(main())
