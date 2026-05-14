"""
Phase 1.15 — coverage signal.

Reads Phase 1.9's TestPayload (already in probe-raw/1_9_tests.json) and
re-parses the standard coverage output formats produced by common
test runners (vitest, jest, coverage.py, go cover).

For v0.8.0 this is mostly pass-through: if 1.9 captured `coverage_pct_overall`
and `coverage_pct_by_file`, we surface them in a dedicated CoveragePayload
so downstream skills can read coverage independent of test execution data.

Future enhancement: parse `coverage.xml`, `coverage.json`, `lcov.info`
files directly from disk.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import LOW_COVERAGE_THRESHOLD_PCT, PHASE_FILES
from ..models import CoveragePayload, RunnerInput, RunnerResult
from .base import make_result, now_iso


class CoverageRunner:
    PHASE: str = "1.15"
    TOOL: str = "coverage"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []
        workspace_path = Path(inp.workspace_path)

        # Try to load Phase 1.9 results
        tests_path = Path(inp.output_dir) / PHASE_FILES["1.9"]
        overall_pct: float | None = None
        by_file: dict[str, float] = {}
        source = "none"

        if tests_path.exists():
            try:
                data = json.loads(tests_path.read_text(encoding="utf-8"))
                test_payload = data.get("payload") or {}
                overall_pct = test_payload.get("coverage_pct_overall")
                by_file = test_payload.get("coverage_pct_by_file") or {}
                source = test_payload.get("coverage_tool_detected") or "none"
            except (OSError, json.JSONDecodeError) as exc:
                warnings.append(f"Failed to read Phase 1.9 coverage data: {exc!r}")
        else:
            warnings.append("Phase 1.9 not run; no coverage data available")

        # Fallback: scan for common coverage report files
        if not by_file:
            extra_by_file = _parse_coverage_files(workspace_path)
            if extra_by_file:
                by_file = extra_by_file
                if overall_pct is None and extra_by_file:
                    overall_pct = sum(extra_by_file.values()) / len(extra_by_file)

        low_coverage = [
            f for f, pct in by_file.items()
            if pct < LOW_COVERAGE_THRESHOLD_PCT
        ]

        payload = CoveragePayload(
            overall_pct=overall_pct,
            by_file=by_file,
            low_coverage_files=low_coverage,
            source=source,
        )

        return make_result(
            phase=self.PHASE, tool=self.TOOL,
            started_at=started_at, started_monotonic=started_monotonic,
            payload=payload.__dict__, warnings=warnings,
        )


def _parse_coverage_files(workspace_path: Path) -> dict[str, float]:
    """Best-effort scan for coverage report files."""
    candidates = [
        workspace_path / "coverage" / "coverage-summary.json",  # vitest/jest
        workspace_path / "coverage" / "coverage-final.json",     # jest
        workspace_path / ".coverage" / "coverage.json",
        workspace_path / "coverage.json",
    ]
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue

        # Format detection
        if isinstance(data, dict):
            # vitest/jest coverage-summary.json: per-file path → {lines: {pct: N}, ...}
            by_file: dict[str, float] = {}
            for file_path, file_summary in data.items():
                if file_path == "total":
                    continue
                if isinstance(file_summary, dict):
                    lines = file_summary.get("lines") or {}
                    pct = lines.get("pct")
                    if isinstance(pct, (int, float)):
                        try:
                            rel = str(Path(file_path).resolve().relative_to(workspace_path.resolve()))
                        except ValueError:
                            rel = file_path
                        by_file[rel] = float(pct)
            if by_file:
                return by_file

    return {}
