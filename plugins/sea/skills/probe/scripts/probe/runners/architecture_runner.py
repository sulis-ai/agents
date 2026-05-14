"""
Phase 1.14 — architecture-rule violations.

Tools:
- TS/JS: dependency-cruiser (requires .dependency-cruiser.cjs config)
- Python: import-linter (`lint-imports` CLI; requires config in pyproject.toml or .importlinter)

Graceful skip when no config file detected.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import ARCH_RULE_CONFIGS_BY_LANG
from ..models import ArchitecturePayload, ArchViolation, RunnerInput, RunnerResult
from .base import is_tool_available, make_result, now_iso, run_tool


class ArchitectureRunner:
    PHASE: str = "1.14"
    TOOL: str = "arch-rules"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []
        workspace_path = Path(inp.workspace_path)

        violations: list[ArchViolation] = []
        rules_passed = rules_failed = 0
        rules_config: str | None = None

        # Try TS / dependency-cruiser
        if any(l in inp.languages for l in ("ts", "tsx", "javascript")):
            for cfg_name in ARCH_RULE_CONFIGS_BY_LANG.get("ts", []):
                cfg_path = workspace_path / cfg_name
                if cfg_path.exists():
                    rules_config = str(cfg_path.relative_to(workspace_path))
                    if is_tool_available("dependency-cruiser"):
                        result = _run_dep_cruiser(workspace_path, cfg_path)
                        if result is not None:
                            violations.extend(result["violations"])
                            rules_passed += result.get("passed", 0)
                            rules_failed += result.get("failed", 0)
                    else:
                        warnings.append(
                            "dependency-cruiser config found but binary not on PATH; skipped"
                        )
                    break

        # Try Python / import-linter
        if "python" in inp.languages and rules_config is None:
            for cfg_name in ARCH_RULE_CONFIGS_BY_LANG.get("python", []):
                cfg_path = workspace_path / cfg_name
                if cfg_path.exists():
                    # pyproject.toml only counts if it has the importlinter section
                    if cfg_name == "pyproject.toml":
                        try:
                            if "[tool.importlinter]" not in cfg_path.read_text(encoding="utf-8"):
                                continue
                        except OSError:
                            continue
                    rules_config = str(cfg_path.relative_to(workspace_path))
                    if is_tool_available("lint-imports"):
                        result = _run_import_linter(workspace_path)
                        if result is not None:
                            violations.extend(result["violations"])
                            rules_passed += result.get("passed", 0)
                            rules_failed += result.get("failed", 0)
                    else:
                        warnings.append(
                            "import-linter config found but lint-imports not on PATH; skipped"
                        )
                    break

        if rules_config is None:
            warnings.append("No architecture-rule config found; phase skipped")

        payload = ArchitecturePayload(
            rules_config=rules_config,
            violations=[v.__dict__ for v in violations],
            rules_passed=rules_passed,
            rules_failed=rules_failed,
        )

        return make_result(
            phase=self.PHASE, tool=self.TOOL,
            started_at=started_at, started_monotonic=started_monotonic,
            payload=payload.__dict__, warnings=warnings,
        )


def _run_dep_cruiser(workspace_path: Path, cfg_path: Path) -> dict | None:
    """Run dependency-cruiser --validate."""
    cmd = ["dependency-cruiser", "--validate", str(cfg_path), "--output-type", "json", "."]
    try:
        result = run_tool(cmd, cwd=workspace_path, tool="dependency-cruiser", phase="1.14")
    except Exception:
        return None
    if not result.stdout.strip():
        return {"violations": [], "passed": 0, "failed": 0}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    violations: list[ArchViolation] = []
    summary = data.get("summary") or {}
    for module in data.get("modules") or []:
        for dep in module.get("dependencies") or []:
            for rule in dep.get("rules") or []:
                violations.append(ArchViolation(
                    rule_id=rule.get("name", "unknown"),
                    source=_to_rel(module.get("source", ""), workspace_path),
                    target=_to_rel(dep.get("resolved", ""), workspace_path),
                    file=_to_rel(module.get("source", ""), workspace_path),
                    line=0,
                    severity=rule.get("severity", "warn"),
                ))
    return {
        "violations": violations,
        "passed": summary.get("totalCruised", 0) - len(violations),
        "failed": len(violations),
    }


def _run_import_linter(workspace_path: Path) -> dict | None:
    """Run lint-imports and parse text output."""
    try:
        result = run_tool(
            ["lint-imports"], cwd=workspace_path, tool="lint-imports", phase="1.14",
        )
    except Exception:
        return None

    violations: list[ArchViolation] = []
    passed = failed = 0

    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("Contract "):
            # "Contract X passes." / "Contract X fails." — best-effort tally
            if "passes" in line:
                passed += 1
            elif "fails" in line:
                failed += 1
        # Violation lines often look like "  - some.module -> other.module"
        if line.startswith("-") and "->" in line:
            try:
                _, body = line.split("-", 1)
                src, tgt = body.split("->")
                violations.append(ArchViolation(
                    rule_id="import-linter-violation",
                    source=src.strip(),
                    target=tgt.strip(),
                    file="",
                    line=0,
                    severity="error",
                ))
            except ValueError:
                continue

    return {"violations": violations, "passed": passed, "failed": failed}


def _to_rel(path: str, workspace_path: Path) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve().relative_to(workspace_path.resolve()))
    except ValueError:
        return path
