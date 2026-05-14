"""
Phase 1.10 — linter dry-run signal.

Detects configured linters (eslint, ruff, mypy, clippy, golangci-lint) and
runs them in check-only mode with JSON output. Captures warning/error
counts per file plus top rule violations.

Graceful degradation: if no linter configured or binary missing, returns
empty LintPayload with appropriate warning.
"""

from __future__ import annotations

import json
import time
from collections import Counter
from pathlib import Path

from ..config import LINTER_SIGNALS
from ..models import LintPayload, RunnerInput, RunnerResult
from .base import is_tool_available, make_result, now_iso, run_tool


class LintRunner:
    PHASE: str = "1.10"
    TOOL: str = "linters"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings_list: list[str] = []
        workspace_path = Path(inp.workspace_path)

        linters_configured: list[str] = []
        warnings_by_file: Counter[str] = Counter()
        errors_by_file: Counter[str] = Counter()
        typecheck_errors = 0
        rule_violations: Counter[str] = Counter()

        for linter, info in LINTER_SIGNALS.items():
            if not _is_configured(linter, info, workspace_path):
                continue
            linters_configured.append(linter)

            binary = info["binary"]
            if not is_tool_available(binary[0]):
                warnings_list.append(
                    f"{linter} configured but {binary[0]} not on PATH; skipped"
                )
                continue

            stats = _run_linter(linter, info, workspace_path)
            if stats is None:
                warnings_list.append(f"{linter} execution failed")
                continue

            for f, count in stats.get("warnings_by_file", {}).items():
                warnings_by_file[f] += count
            for f, count in stats.get("errors_by_file", {}).items():
                errors_by_file[f] += count
            for rule, count in stats.get("rules", {}).items():
                rule_violations[rule] += count
            typecheck_errors += stats.get("typecheck_errors", 0)

        # Top 10 rule violations
        top_rules = dict(rule_violations.most_common(10))

        payload = LintPayload(
            linters_configured=linters_configured,
            warnings_by_file=dict(warnings_by_file),
            errors_by_file=dict(errors_by_file),
            typecheck_errors=typecheck_errors,
            rule_violations=top_rules,
        )

        return make_result(
            phase=self.PHASE, tool=self.TOOL,
            started_at=started_at, started_monotonic=started_monotonic,
            payload=payload.__dict__, warnings=warnings_list,
        )


def _is_configured(linter: str, info: dict, workspace_path: Path) -> bool:
    for manifest in info["manifests"]:
        mpath = workspace_path / manifest
        if not mpath.exists():
            continue
        # Special: pyproject.toml for ruff/mypy needs the corresponding section
        if manifest == "pyproject.toml":
            try:
                text = mpath.read_text(encoding="utf-8")
                if linter == "ruff" and "[tool.ruff" in text:
                    return True
                if linter == "mypy" and "[tool.mypy" in text:
                    return True
                if linter not in ("ruff", "mypy"):
                    return True
            except OSError:
                continue
        else:
            return True
    return False


def _run_linter(linter: str, info: dict, workspace_path: Path) -> dict | None:
    """Returns dict with warnings_by_file, errors_by_file, rules, typecheck_errors."""
    cmd = info["binary"] + info["check_args"]
    try:
        result = run_tool(
            cmd, cwd=workspace_path, tool=linter, phase="1.10",
        )
    except Exception:
        return None

    return _parse_lint_output(linter, result.stdout, workspace_path)


def _parse_lint_output(linter: str, stdout: str, workspace_path: Path) -> dict:
    out = {
        "warnings_by_file": {},
        "errors_by_file": {},
        "rules": {},
        "typecheck_errors": 0,
    }
    if not stdout.strip():
        return out

    if linter == "eslint":
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return out
        for entry in data:
            f = _to_rel(entry.get("filePath", ""), workspace_path)
            w = entry.get("warningCount", 0)
            e = entry.get("errorCount", 0)
            if w:
                out["warnings_by_file"][f] = w
            if e:
                out["errors_by_file"][f] = e
            for msg in entry.get("messages", []):
                rid = msg.get("ruleId") or "(no-rule)"
                out["rules"][rid] = out["rules"].get(rid, 0) + 1

    elif linter == "ruff":
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return out
        for finding in data:
            f = _to_rel(finding.get("filename", ""), workspace_path)
            code = finding.get("code") or "(no-code)"
            out["warnings_by_file"][f] = out["warnings_by_file"].get(f, 0) + 1
            out["rules"][code] = out["rules"].get(code, 0) + 1

    elif linter == "mypy":
        # mypy text output: <file>:<line>: error: ...
        for line in stdout.splitlines():
            if ": error:" in line:
                f = line.split(":", 1)[0]
                f_rel = _to_rel(f, workspace_path)
                out["errors_by_file"][f_rel] = out["errors_by_file"].get(f_rel, 0) + 1
                out["typecheck_errors"] += 1

    elif linter == "clippy":
        # cargo clippy --message-format=json — each line is a compiler message
        for line in stdout.splitlines():
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("reason") != "compiler-message":
                continue
            m = msg.get("message") or {}
            level = m.get("level")
            spans = m.get("spans") or []
            for span in spans:
                f = _to_rel(span.get("file_name", ""), workspace_path)
                if level == "warning":
                    out["warnings_by_file"][f] = out["warnings_by_file"].get(f, 0) + 1
                elif level == "error":
                    out["errors_by_file"][f] = out["errors_by_file"].get(f, 0) + 1
                code_obj = m.get("code") or {}
                code = code_obj.get("code") or "(unknown)"
                out["rules"][code] = out["rules"].get(code, 0) + 1

    elif linter == "golangci-lint":
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            return out
        for issue in data.get("Issues") or []:
            f = _to_rel((issue.get("Pos") or {}).get("Filename", ""), workspace_path)
            severity = (issue.get("Severity") or "warning").lower()
            if severity == "error":
                out["errors_by_file"][f] = out["errors_by_file"].get(f, 0) + 1
            else:
                out["warnings_by_file"][f] = out["warnings_by_file"].get(f, 0) + 1
            rule = issue.get("FromLinter") or "(unknown)"
            out["rules"][rule] = out["rules"].get(rule, 0) + 1

    return out


def _to_rel(path: str, workspace_path: Path) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve().relative_to(workspace_path.resolve()))
    except ValueError:
        return path
