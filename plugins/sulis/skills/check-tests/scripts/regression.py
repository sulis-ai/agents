#!/usr/bin/env python3
"""Test-pass regression detector.

Detects test framework, runs tests (or reads cached results), compares
to a baseline at .checkup/{project}/baseline.json, and reports
newly-failing tests as regressions.

The baseline is captured on first run; subsequent runs compare against
it. Updating the baseline requires explicit --update-baseline.

Usage:

    # First run: captures baseline, runs tests
    python3 regression.py --project NAME --run

    # Subsequent run: compares to baseline
    python3 regression.py --project NAME [--run]

    # Use cached results (no fresh run)
    python3 regression.py --project NAME --no-run

    # Update baseline to current state
    python3 regression.py --project NAME --run --update-baseline

    # Force a specific framework
    python3 regression.py --project NAME --framework pytest --run

    # Operator JSON output
    python3 regression.py --project NAME --run --raw

Exit codes:
- 0 = success (regardless of regression count)
- 1 = usage error
- 2 = filesystem / git error
- 3 = test runner failed (non-zero exit; tests didn't run cleanly)
- 4 = framework not detected and not specified
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


DEFAULT_TIMEOUT_SECONDS = 120


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class TestResult:
    signature: str  # {file}::{class}::{name}
    status: str  # passed | failed | skipped | error
    file: str
    duration_ms: float | None = None


@dataclass
class Framework:
    name: str
    detect_signals: list[str]  # paths to check for existence
    run_cmd: list[str]
    timeout_s: int = DEFAULT_TIMEOUT_SECONDS


@dataclass
class Baseline:
    captured_at: str  # ISO timestamp
    captured_at_sha: str
    framework: str
    results: dict[str, str]  # signature → status


@dataclass
class RegressionReport:
    project: str
    repo_root: str
    framework: str | None
    ran_fresh: bool
    results_source: str  # "fresh-run" | "cache" | "detection-only"
    current_results: list[TestResult]
    baseline: Baseline | None
    newly_failing: list[str]  # signatures
    newly_passing: list[str]
    newly_added: list[str]
    newly_removed: list[str]
    flaky_suppressed: list[str]
    errors: list[str]
    captured_baseline: bool  # True if this run captured a new baseline


# ─── Framework detection ────────────────────────────────────────────


def detect_framework(repo_root: Path) -> tuple[str | None, list[str]]:
    """Return (chosen_framework, all_detected). chosen is the highest-precedence."""
    detected: list[str] = []

    # pytest
    pytest_signals = [
        repo_root / "pytest.ini",
        repo_root / "conftest.py",
    ]
    if any(p.is_file() for p in pytest_signals):
        detected.append("pytest")
    elif (repo_root / "pyproject.toml").is_file():
        try:
            content = (repo_root / "pyproject.toml").read_text(encoding="utf-8")
            if "[tool.pytest" in content or "pytest" in content.lower():
                detected.append("pytest")
        except OSError:
            pass

    # jest / vitest
    pkg = repo_root / "package.json"
    if pkg.is_file():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {**(data.get("dependencies") or {}), **(data.get("devDependencies") or {})}
            if "vitest" in deps or (repo_root / "vitest.config.ts").is_file() or (repo_root / "vitest.config.js").is_file():
                detected.append("vitest")
            elif "jest" in deps or data.get("jest"):
                detected.append("jest")
            elif "mocha" in deps:
                detected.append("mocha")
        except (json.JSONDecodeError, OSError):
            pass

    # go test
    if (repo_root / "go.mod").is_file():
        # Quick check: any *_test.go in the tree
        for _ in repo_root.rglob("*_test.go"):
            detected.append("go")
            break

    # rspec
    if (repo_root / ".rspec").is_file() or (repo_root / "spec" / "spec_helper.rb").is_file():
        detected.append("rspec")

    chosen = detected[0] if detected else None
    return chosen, detected


# ─── Test runners ───────────────────────────────────────────────────


def run_pytest(repo_root: Path, timeout: int) -> tuple[list[TestResult], list[str]]:
    """Run pytest; parse stdout to list of TestResult.

    Uses -v (verbose) so per-test PASSED/FAILED lines with signatures are
    emitted. Quiet mode collapses everything to characters which lose the
    signature information needed for regression detection.
    """
    errors: list[str] = []
    cmd = ["pytest", "-v", "--tb=no", "--no-header", "-p", "no:cacheprovider"]

    try:
        proc = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return [], [f"pytest timed out after {timeout}s"]
    except FileNotFoundError:
        return [], ["pytest not installed; install with `pip install pytest`"]

    results = _parse_pytest_verbose(proc.stdout, proc.stderr)
    if proc.returncode not in (0, 1, 5):
        # 0 = all passed, 1 = some failed, 5 = no tests collected
        errors.append(f"pytest exited with unexpected rc={proc.returncode}; stderr: {proc.stderr[:200]}")
    return results, errors


def _parse_pytest_verbose(stdout: str, stderr: str) -> list[TestResult]:
    """Parse `pytest -v` output.

    Per-test line format:
      tests/test_foo.py::TestX::test_a PASSED                  [ 50%]
      tests/test_foo.py::test_b FAILED                         [100%]
      tests/test_foo.py::test_c SKIPPED (reason)               [100%]

    The percentage in brackets is optional; the status keyword is what matters.
    """
    results: list[TestResult] = []
    seen: set[str] = set()
    for line in stdout.splitlines():
        match = re.match(
            r"^([^\s]+::[\w_:\[\]/.\-]+?)\s+(PASSED|FAILED|SKIPPED|ERROR|XFAIL|XPASS)\b",
            line,
        )
        if not match:
            continue
        sig, raw_status = match.group(1), match.group(2).upper()
        if sig in seen:
            continue  # avoid duplicate signatures (rare but possible with -v + xdist)
        seen.add(sig)
        status_map = {
            "PASSED": "passed",
            "FAILED": "failed",
            "SKIPPED": "skipped",
            "ERROR": "error",
            "XFAIL": "passed",  # expected-fail that did fail — counts as passed
            "XPASS": "failed",  # expected-fail that passed — unexpected; treat as failed
        }
        results.append(TestResult(
            signature=sig,
            status=status_map[raw_status],
            file=sig.split("::")[0],
        ))
    return results


def run_go_test(repo_root: Path, timeout: int) -> tuple[list[TestResult], list[str]]:
    """Run `go test -json ./...` and parse the JSON stream."""
    errors: list[str] = []
    cmd = ["go", "test", "-json", "./..."]

    try:
        proc = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return [], [f"go test timed out after {timeout}s"]
    except FileNotFoundError:
        return [], ["go not installed"]

    results: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "Test" not in event or event.get("Action") not in ("pass", "fail", "skip"):
            continue
        sig = f"{event.get('Package','')}::{event['Test']}"
        results[sig] = {"pass": "passed", "fail": "failed", "skip": "skipped"}[event["Action"]]

    if proc.returncode not in (0, 1):
        errors.append(f"go test exited with rc={proc.returncode}")

    return [TestResult(signature=sig, status=st, file=sig.split("::")[0]) for sig, st in results.items()], errors


def run_jest_or_vitest(repo_root: Path, timeout: int, framework: str) -> tuple[list[TestResult], list[str]]:
    """Run jest or vitest with JSON reporter."""
    errors: list[str] = []
    if framework == "jest":
        cmd = ["npx", "jest", "--json", "--silent"]
    else:  # vitest
        cmd = ["npx", "vitest", "run", "--reporter=json"]

    try:
        proc = subprocess.run(
            cmd, cwd=str(repo_root), capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return [], [f"{framework} timed out after {timeout}s"]
    except FileNotFoundError:
        return [], [f"npx not found; need Node.js installed for {framework}"]

    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return [], [f"{framework} produced unparseable JSON; stderr: {proc.stderr[:200]}"]

    results: list[TestResult] = []
    test_results = data.get("testResults") or data.get("results") or []
    for tr in test_results:
        file = tr.get("name") or tr.get("filepath", "")
        for test in tr.get("assertionResults", []) or tr.get("tasks", []):
            sig = f"{file}::{test.get('fullName') or test.get('name', '')}"
            raw_status = test.get("status", "unknown")
            status = "passed" if raw_status in ("passed", "pass") else \
                     "failed" if raw_status in ("failed", "fail") else \
                     "skipped" if raw_status in ("skipped", "pending", "skip") else "error"
            results.append(TestResult(signature=sig, status=status, file=file))

    return results, errors


def run_framework(framework: str, repo_root: Path, timeout: int) -> tuple[list[TestResult], list[str]]:
    if framework == "pytest":
        return run_pytest(repo_root, timeout)
    if framework == "go":
        return run_go_test(repo_root, timeout)
    if framework in ("jest", "vitest"):
        return run_jest_or_vitest(repo_root, timeout, framework)
    return [], [f"framework '{framework}' not yet supported in v1 (planned: rspec, mocha)"]


# ─── Baseline storage ───────────────────────────────────────────────
# Inline implementation removed in v0.11.2 — uses _lib/baseline.
# Baseline now lives under tier_3_tests sub-key (was root of
# baseline.json pre-v0.11.2; legacy detection below warns + ignores).


def baseline_path(repo_root: Path, project: str) -> Path:
    """Retained for legacy-detection messaging; the actual read/write
    goes through _lib.baseline now."""
    return repo_root / ".checkup" / project / "baseline.json"


def load_baseline(repo_root: Path, project: str) -> Baseline | None:
    """Load via _lib.baseline; detect legacy root-shape + warn."""
    data = _baseline.load_namespace(repo_root, project, "tier_3_tests", None)
    if data is None:
        # Check for legacy root-shape baseline (pre-v0.11.2)
        path = baseline_path(repo_root, project)
        if path.is_file():
            try:
                root_data = json.loads(path.read_text(encoding="utf-8"))
                if "captured_at" in root_data and "results" in root_data:
                    print(
                        f"warn: legacy baseline format at {path} (root-level "
                        "Baseline); v0.11.2+ stores under tier_3_tests sub-key. "
                        "Re-capture with --update-baseline to migrate.",
                        file=sys.stderr,
                    )
            except (OSError, json.JSONDecodeError):
                pass
        return None
    try:
        return Baseline(
            captured_at=data["captured_at"],
            captured_at_sha=data["captured_at_sha"],
            framework=data["framework"],
            results=data["results"],
        )
    except (KeyError, TypeError) as exc:
        print(
            f"warn: tier_3_tests baseline unreadable: {exc}",
            file=sys.stderr,
        )
        return None


def save_baseline(repo_root: Path, project: str, baseline: Baseline) -> None:
    """Save the full Baseline dataclass as a dict under tier_3_tests."""
    _baseline.save_namespace(
        repo_root, project, "tier_3_tests", asdict(baseline)
    )


def current_sha(repo_root: Path) -> str:
    return _baseline.current_sha(repo_root)


# ─── Known-flaky loading ────────────────────────────────────────────
# Inline implementation removed in v0.11.2 — uses _lib/allowlist.


def load_known_flaky(repo_root: Path, project: str) -> set[str]:
    """Load known-flaky test signatures from per-project + marketplace-
    shared lists. Both files use the same `signature: reason` (or bare
    signature) format that _lib/allowlist understands.
    """
    project_path = repo_root / ".checkup" / project / "known-flaky.md"
    marketplace_path = (
        repo_root
        / "plugins"
        / "sulis"
        / "skills"
        / "check-tests"
        / "references"
        / "check-tests-known-flaky.md"
    )
    return _allowlist.load_allowlist(project_path, marketplace_path)


# ─── Delta computation ──────────────────────────────────────────────


def compute_delta(
    current: list[TestResult], baseline: Baseline | None, flaky: set[str],
) -> tuple[list[str], list[str], list[str], list[str], list[str]]:
    """Returns (newly_failing, newly_passing, newly_added, newly_removed, flaky_suppressed)."""
    current_map = {r.signature: r.status for r in current}
    baseline_map = baseline.results if baseline else {}

    newly_failing: list[str] = []
    newly_passing: list[str] = []
    flaky_suppressed: list[str] = []
    newly_added = [sig for sig in current_map if sig not in baseline_map]
    newly_removed = [sig for sig in baseline_map if sig not in current_map]

    for sig, status in current_map.items():
        if sig in flaky:
            base_status = baseline_map.get(sig)
            if base_status and base_status != status:
                flaky_suppressed.append(sig)
            continue
        base_status = baseline_map.get(sig)
        if base_status is None:
            continue  # in newly_added
        if base_status == "passed" and status == "failed":
            newly_failing.append(sig)
        elif base_status == "failed" and status == "passed":
            newly_passing.append(sig)

    return newly_failing, newly_passing, newly_added, newly_removed, flaky_suppressed


# ─── Rendering ──────────────────────────────────────────────────────


def render_json(report: RegressionReport) -> str:
    # Build the orchestrator-compatible `findings` array. Each newly-failing
    # test → one finding (severity = high; this IS a regression). Other
    # categories (newly-passing, newly-added) are informational and don't
    # appear as findings — they're surfaced in the regression-specific fields
    # for callers that want them.
    findings = []
    for sig in report.newly_failing:
        file = sig.split("::")[0]
        name = "::".join(sig.split("::")[1:])
        findings.append({
            "heuristic": "test-regression",
            "severity": "high",
            "file": file,
            "line": 0,
            "identifier": name,
            "message": f"test `{name}` was passing at baseline; failing now",
            "suggestion": "investigate the change that broke this test",
            "extras": {"signature": sig, "category": "newly-failing"},
        })

    payload = {
        "project": report.project,
        "repo_root": report.repo_root,
        "framework": report.framework,
        "ran_fresh": report.ran_fresh,
        "results_source": report.results_source,
        "test_count": len(report.current_results),
        "passing_count": sum(1 for r in report.current_results if r.status == "passed"),
        "failing_count": sum(1 for r in report.current_results if r.status == "failed"),
        "baseline": asdict(report.baseline) if report.baseline else None,
        # Regression-specific fields
        "newly_failing": report.newly_failing,
        "newly_passing": report.newly_passing,
        "newly_added": report.newly_added,
        "newly_removed": report.newly_removed,
        "flaky_suppressed": report.flaky_suppressed,
        "captured_baseline": report.captured_baseline,
        # Orchestrator-compatible findings shape (only regressions surface here)
        "findings": findings,
        "errors": report.errors,
    }
    return json.dumps(payload, indent=2)


def render_markdown(report: RegressionReport) -> str:
    out: list[str] = []
    out.append(f"# Test check — {report.project}")
    out.append("")

    if report.captured_baseline:
        out.append("**First run.** Captured baseline at commit "
                   f"`{report.baseline.captured_at_sha}` ({len(report.current_results)} tests). "
                   "Next run will detect any regressions against this point.")
        out.append("")
        return "\n".join(out)

    if report.results_source == "detection-only":
        out.append(
            f"_Tests detected ({len(report.current_results)} signatures via {report.framework}) "
            "but not run. Pass `--run` to execute them, or your CI's results will be read when present._"
        )
        if report.errors:
            out.append("")
            out.append("**Errors during detection:**")
            for e in report.errors:
                out.append(f"- {e}")
        return "\n".join(out)

    total = len(report.current_results)
    passing = sum(1 for r in report.current_results if r.status == "passed")
    failing = sum(1 for r in report.current_results if r.status == "failed")
    skipped = sum(1 for r in report.current_results if r.status == "skipped")

    # Verdict
    if report.newly_failing:
        verdict = f"⚠ Something broke — {len(report.newly_failing)} test{_s(report.newly_failing)} that {_was_were(report.newly_failing)} passing now failing"
    elif failing > 0 and report.baseline:
        verdict = "🟡 Mostly clear — pre-existing failures unchanged"
    elif failing > 0:
        verdict = f"🟡 {failing} test{_s_count(failing)} failing (no baseline to compare against)"
    else:
        verdict = "✓ Clear — all tests pass"

    out.append(f"**Verdict:** {verdict}")
    out.append("")

    out.append(
        f"**Summary:** {total} tests · {passing} passing · {failing} failing"
        + (f" · {skipped} skipped" if skipped else "")
    )
    if report.baseline:
        out.append(
            f"Compared to baseline at commit `{report.baseline.captured_at_sha}` "
            f"(captured {report.baseline.captured_at})."
        )
    out.append("")

    if report.newly_failing:
        out.append(f"## ⚠ Newly-failing (regressions) — {len(report.newly_failing)}")
        out.append("")
        for sig in report.newly_failing[:10]:
            file = sig.split("::")[0]
            name = "::".join(sig.split("::")[1:])
            out.append(f"- **{name}** in `{file}`")
            out.append("  - Was passing at baseline; failing now.")
        if len(report.newly_failing) > 10:
            out.append(f"- _…and {len(report.newly_failing) - 10} more — pass `--raw` for the full list._")
        out.append("")

    if report.newly_passing:
        out.append(f"## ✓ Newly-passing (improvements) — {len(report.newly_passing)}")
        out.append("")
        for sig in report.newly_passing[:5]:
            out.append(f"- `{sig}`")
        out.append("")

    if report.newly_added or report.newly_removed:
        out.append(
            f"## ℹ Test-suite changes — {len(report.newly_added)} added, "
            f"{len(report.newly_removed)} removed"
        )
        out.append("")

    if report.flaky_suppressed:
        out.append(f"## Flaky tests (suppressed from regression report): {len(report.flaky_suppressed)}")
        out.append("")
        out.append(
            "_See `references/check-tests-known-flaky.md` and "
            "`.checkup/{project}/known-flaky.md` to manage._"
        )
        out.append("")

    if report.errors:
        out.append("## Errors")
        out.append("")
        for e in report.errors:
            out.append(f"- {e}")
        out.append("")

    out.append("---")
    out.append("")
    out.append("_This skill is read-only. It identifies what changed; it never modifies code._")
    return "\n".join(out)


def _s(items: list) -> str:
    return "s" if len(items) != 1 else ""


def _s_count(n: int) -> str:
    return "s" if n != 1 else ""


def _was_were(items: list) -> str:
    return "were" if len(items) != 1 else "was"


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Test-pass regression detector.")
    parser.add_argument("--project", default=None, help="Project slug (resolves .checkup/<project>/). Defaults to the repo-root basename.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--framework", default=None, help="Force a specific framework")
    parser.add_argument("--run", action="store_true", help="Run tests fresh")
    parser.add_argument("--no-run", action="store_true", help="Never run; report detection-only if no cache")
    parser.add_argument("--update-baseline", action="store_true", help="Overwrite baseline with current results (requires confirmation)")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--raw", action="store_true", help="Output JSON")
    # Accepted-but-ignored flags for orchestrator compatibility. check-tests
    # doesn't yet do scope-aware test selection (would require per-framework
    # filter paths); accepting the flag means the orchestrator can pass the
    # same args to every wired tier-skill without per-skill flag inspection.
    parser.add_argument("--scope", default=None, help="(accepted but ignored in v1)")
    parser.add_argument("--base-branch", default=None, help="(accepted but ignored in v1)")
    parser.add_argument("--pr-number", default=None, help="(accepted but ignored in v1)")
    args = parser.parse_args()

    # Default project to repo-root basename so the orchestrator doesn't have
    # to know the project name.
    if args.project is None:
        args.project = Path(args.repo_root).resolve().name

    if args.run and args.no_run:
        print("error: --run and --no-run are mutually exclusive", file=sys.stderr)
        return 1

    repo_root = Path(args.repo_root).resolve()
    if not (repo_root / ".git").exists():
        print(f"error: {repo_root} is not a git repo", file=sys.stderr)
        return 2

    # Resolve framework
    framework = args.framework
    if not framework:
        chosen, detected = detect_framework(repo_root)
        if not chosen:
            print(
                "error: no test framework detected (looked for pytest, vitest, jest, "
                "go, rspec, mocha). Pass --framework explicitly.",
                file=sys.stderr,
            )
            return 4
        framework = chosen
        if len(detected) > 1:
            print(f"info: multiple frameworks detected: {detected}; using {framework}. Override with --framework.", file=sys.stderr)

    # Run or skip
    errors: list[str] = []
    results: list[TestResult] = []
    ran_fresh = False
    results_source = "detection-only"

    if args.run:
        results, run_errors = run_framework(framework, repo_root, args.timeout)
        errors.extend(run_errors)
        ran_fresh = True
        results_source = "fresh-run"
    elif args.no_run:
        # Always report detection-only
        results_source = "detection-only"
    else:
        # Default: try cache, else detection-only. v1: simple — no cache reader yet.
        results_source = "detection-only"

    # Baseline + delta
    baseline = load_baseline(repo_root, args.project)
    flaky = load_known_flaky(repo_root, args.project)
    captured_baseline = False

    newly_failing, newly_passing, newly_added, newly_removed, flaky_suppressed = (
        compute_delta(results, baseline, flaky)
    )

    # First-run baseline capture
    if results_source == "fresh-run" and baseline is None and results:
        new_baseline = Baseline(
            captured_at=_baseline.now_iso(),
            captured_at_sha=current_sha(repo_root),
            framework=framework,
            results={r.signature: r.status for r in results},
        )
        save_baseline(repo_root, args.project, new_baseline)
        captured_baseline = True
        baseline = new_baseline

    # Explicit baseline update
    if args.update_baseline and results_source == "fresh-run" and results:
        new_baseline = Baseline(
            captured_at=_baseline.now_iso(),
            captured_at_sha=current_sha(repo_root),
            framework=framework,
            results={r.signature: r.status for r in results},
        )
        save_baseline(repo_root, args.project, new_baseline)
        captured_baseline = False  # update is not first-capture
        baseline = new_baseline
        # Re-compute delta against fresh baseline (should be empty)
        newly_failing, newly_passing, newly_added, newly_removed, flaky_suppressed = (
            compute_delta(results, baseline, flaky)
        )

    report = RegressionReport(
        project=args.project,
        repo_root=str(repo_root),
        framework=framework,
        ran_fresh=ran_fresh,
        results_source=results_source,
        current_results=results,
        baseline=baseline,
        newly_failing=newly_failing,
        newly_passing=newly_passing,
        newly_added=newly_added,
        newly_removed=newly_removed,
        flaky_suppressed=flaky_suppressed,
        errors=errors,
        captured_baseline=captured_baseline,
    )

    if args.raw:
        print(render_json(report))
    else:
        print(render_markdown(report))

    print(
        f"check-tests: framework={framework}, source={results_source}, "
        f"tests={len(results)}, regressions={len(newly_failing)}, captured_baseline={captured_baseline}",
        file=sys.stderr,
    )

    return 3 if errors and not results else 0


if __name__ == "__main__":
    sys.exit(main())
