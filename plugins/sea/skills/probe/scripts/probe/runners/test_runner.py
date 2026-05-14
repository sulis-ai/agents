"""
Phase 1.9 — test framework discovery + enumeration + optional execution.

Three tiers (per config.TEST_FRAMEWORK_SIGNALS):
1. Discovery: detect configured framework via manifest files.
2. Enumeration: invoke `--collect-only` / `--listTests` / `-list` to count tests.
3. Execution (--run-tests only): run the suite, capture pass/fail counts and
   coverage if available.

Gracefully skips when no framework detected. Never installs dependencies.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from ..config import COVERAGE_SIGNALS, TEST_FRAMEWORK_SIGNALS
from ..models import RunnerInput, RunnerResult, TestPayload
from .base import make_result, now_iso, run_tool


class TestRunner:
    PHASE: str = "1.9"
    TOOL: str = "test-framework"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []
        workspace_path = Path(inp.workspace_path)

        # Detect framework
        framework = _detect_framework(workspace_path)
        if framework is None:
            payload = TestPayload(
                framework="none-detected",
                test_files=0,
                tests_enumerated=0,
                executed=False,
                passed=None, failed=None, skipped=None,
                duration_sec=None,
                coverage_tool_detected=None,
                coverage_pct_overall=None,
                coverage_pct_by_file={},
            )
            return make_result(
                phase=self.PHASE, tool=self.TOOL,
                started_at=started_at, started_monotonic=started_monotonic,
                payload=payload.__dict__, warnings=warnings,
            )

        info = TEST_FRAMEWORK_SIGNALS[framework]
        coverage_tool = _detect_coverage_tool(workspace_path)

        # Enumerate tests
        test_files, tests_enumerated, enum_warn = _enumerate_tests(
            framework, info, workspace_path
        )
        if enum_warn:
            warnings.append(enum_warn)

        # Optionally execute
        executed = False
        passed = failed = skipped = None
        duration = None
        coverage_overall = None
        coverage_by_file: dict[str, float] = {}

        if inp.run_tests:
            exec_result = _execute_tests(framework, info, workspace_path)
            if exec_result:
                executed = True
                passed, failed, skipped, duration = exec_result
                # Coverage capture is best-effort and framework-specific —
                # left as a future enhancement; for v0.8.0 we just detect.
            else:
                warnings.append(f"Test execution failed for {framework}")

        payload = TestPayload(
            framework=framework,
            test_files=test_files,
            tests_enumerated=tests_enumerated,
            executed=executed,
            passed=passed, failed=failed, skipped=skipped,
            duration_sec=duration,
            coverage_tool_detected=coverage_tool,
            coverage_pct_overall=coverage_overall,
            coverage_pct_by_file=coverage_by_file,
        )

        return make_result(
            phase=self.PHASE, tool=self.TOOL,
            started_at=started_at, started_monotonic=started_monotonic,
            payload=payload.__dict__, warnings=warnings,
        )


def _detect_framework(workspace_path: Path) -> str | None:
    """Find first matching framework. Order: pytest, vitest, jest, go-test, cargo-test."""
    for name, info in TEST_FRAMEWORK_SIGNALS.items():
        for manifest in info["manifests"]:
            mpath = workspace_path / manifest
            if mpath.exists():
                # Special case: pyproject.toml only counts if it has [tool.pytest]
                if manifest == "pyproject.toml":
                    try:
                        if "[tool.pytest" in mpath.read_text(encoding="utf-8"):
                            return name
                    except OSError:
                        continue
                else:
                    return name
    # Heuristic fallback: scan for test files
    if list(workspace_path.glob("tests/test_*.py")) or list(workspace_path.glob("test_*.py")):
        return "pytest"
    if list(workspace_path.glob("**/*.test.ts"))[:1] or list(workspace_path.glob("**/*.test.tsx"))[:1]:
        return "vitest"  # default TS test runner; user may use jest
    return None


def _detect_coverage_tool(workspace_path: Path) -> str | None:
    for name, info in COVERAGE_SIGNALS.items():
        manifests = info.get("manifests", [])
        for manifest in manifests:
            if (workspace_path / manifest).exists():
                return name
    # Check package.json for vitest/jest --coverage scripts
    pkg = workspace_path / "package.json"
    if pkg.exists():
        try:
            text = pkg.read_text(encoding="utf-8")
            if "vitest --coverage" in text or "vitest run --coverage" in text:
                return "vitest-coverage"
            if "jest --coverage" in text:
                return "jest-coverage"
        except OSError:
            pass
    return None


def _enumerate_tests(
    framework: str,
    info: dict,
    workspace_path: Path,
) -> tuple[int, int, str | None]:
    """Returns (test_files, tests_enumerated, warning)."""
    binary = info["binary"]
    list_args = info["list_args"]

    cmd = binary + list_args
    try:
        result = run_tool(
            cmd, cwd=workspace_path, tool=framework, phase="1.9",
        )
    except Exception as exc:
        return 0, 0, f"{framework} enumeration failed: {exc!r}"

    if result.returncode not in (0, 5):  # pytest exits 5 on "no tests collected"
        return 0, 0, f"{framework} returned exit code {result.returncode}"

    return _parse_enum_output(framework, result.stdout)


def _parse_enum_output(framework: str, output: str) -> tuple[int, int, str | None]:
    """Parse enumeration output per framework."""
    if framework == "pytest":
        # pytest --collect-only -q outputs:
        #   tests/test_foo.py::TestA::test_one
        #   tests/test_foo.py::TestA::test_two
        #   <blank>
        #   5 tests collected in 0.05s
        lines = [l for l in output.splitlines() if l.strip()]
        # Last line usually has the count
        count_match = re.search(r"(\d+)\s+tests?\s+collected", output)
        tests = int(count_match.group(1)) if count_match else 0
        files = {l.split("::")[0] for l in lines if "::" in l}
        return len(files), tests, None
    if framework in ("vitest", "jest"):
        # vitest list / jest --listTests output one file path per line
        files = [l.strip() for l in output.splitlines() if l.strip()]
        return len(files), len(files), None  # rough — file count == test count
    if framework == "go-test":
        # `go test -list` outputs test function names; one per line
        funcs = [l for l in output.splitlines() if l.startswith("Test")]
        return 0, len(funcs), None  # file count unavailable here
    if framework == "cargo-test":
        # Format: "<path>::<name>: test"
        tests = [l for l in output.splitlines() if "test" in l]
        return 0, len(tests), None
    return 0, 0, f"Unknown framework parser: {framework}"


def _execute_tests(
    framework: str,
    info: dict,
    workspace_path: Path,
) -> tuple[int, int, int, float] | None:
    """Run tests; return (passed, failed, skipped, duration_sec) or None."""
    binary = info["binary"]
    run_args = info["run_args"]
    cmd = binary + run_args

    start = time.monotonic()
    try:
        result = run_tool(
            cmd, cwd=workspace_path, tool=framework, phase="1.9", timeout=600,
        )
    except Exception:
        return None
    duration = time.monotonic() - start

    return _parse_exec_output(framework, result.stdout, result.stderr, duration)


def _parse_exec_output(
    framework: str,
    stdout: str,
    stderr: str,
    duration: float,
) -> tuple[int, int, int, float] | None:
    if framework == "pytest":
        # pytest summary: "5 passed, 2 failed, 1 skipped in 0.10s"
        m = re.search(
            r"(?:(\d+)\s+passed)?(?:,\s+)?(?:(\d+)\s+failed)?(?:,\s+)?(?:(\d+)\s+skipped)?",
            stdout + stderr,
        )
        if m:
            p = int(m.group(1) or 0)
            f = int(m.group(2) or 0)
            s = int(m.group(3) or 0)
            return p, f, s, round(duration, 2)
    elif framework in ("vitest", "jest"):
        # Best-effort JSON parsing; vitest reporter JSON has numTotalTestSuites etc.
        try:
            data = json.loads(stdout)
            return (
                int(data.get("numPassedTests", 0)),
                int(data.get("numFailedTests", 0)),
                int(data.get("numPendingTests", 0)),
                round(duration, 2),
            )
        except (json.JSONDecodeError, ValueError):
            pass
    elif framework == "go-test":
        passed = stdout.count("--- PASS:")
        failed = stdout.count("--- FAIL:")
        return passed, failed, 0, round(duration, 2)
    return None
