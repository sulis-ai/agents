"""
Phase 1.13 — dead code detection.

Per-language tools:
- ts/tsx/javascript: ts-prune
- python: vulture
- go: deadcode (golang.org/x/tools/cmd/deadcode)

Graceful skip if tool not on PATH for a language. Records confidence per
finding so downstream Recommendations can prioritise.
"""

from __future__ import annotations

import re
import time
from collections import Counter
from pathlib import Path

from ..config import DEADCODE_TOOLS_BY_LANG, VULTURE_MIN_CONFIDENCE
from ..models import DeadCodePayload, DeadSymbol, RunnerInput, RunnerResult
from .base import is_tool_available, make_result, now_iso, run_tool


class DeadCodeRunner:
    PHASE: str = "1.13"
    TOOL: str = "deadcode-detectors"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []
        workspace_path = Path(inp.workspace_path)

        symbols: list[DeadSymbol] = []

        for lang in inp.languages:
            tools = DEADCODE_TOOLS_BY_LANG.get(lang, [])
            for tool in tools:
                if not is_tool_available(tool):
                    warnings.append(f"{tool} (for {lang}) not installed; skipped")
                    continue
                parsed = _run_deadcode_tool(tool, lang, workspace_path)
                symbols.extend(parsed)

        by_language: Counter[str] = Counter()
        by_tool: Counter[str] = Counter()
        for s in symbols:
            by_language[_lang_of(s.file)] += 1
            by_tool[s.tool] += 1

        payload = DeadCodePayload(
            symbols=[s.__dict__ for s in symbols],
            by_language=dict(by_language),
            by_tool=dict(by_tool),
        )

        return make_result(
            phase=self.PHASE, tool=self.TOOL,
            started_at=started_at, started_monotonic=started_monotonic,
            payload=payload.__dict__, warnings=warnings,
        )


def _run_deadcode_tool(tool: str, language: str, workspace_path: Path) -> list[DeadSymbol]:
    """Dispatch to the right parser per tool."""
    if tool == "ts-prune":
        try:
            result = run_tool(
                [tool], cwd=workspace_path, tool=tool, phase="1.13",
            )
        except Exception:
            return []
        return _parse_ts_prune(result.stdout, workspace_path)

    if tool == "vulture":
        try:
            result = run_tool(
                [tool, str(workspace_path), "--min-confidence", str(VULTURE_MIN_CONFIDENCE)],
                tool=tool, phase="1.13",
            )
        except Exception:
            return []
        return _parse_vulture(result.stdout, workspace_path)

    if tool == "deadcode":
        try:
            result = run_tool(
                [tool, "./..."], cwd=workspace_path, tool=tool, phase="1.13",
            )
        except Exception:
            return []
        return _parse_go_deadcode(result.stdout, workspace_path)

    return []


def _parse_ts_prune(stdout: str, workspace_path: Path) -> list[DeadSymbol]:
    """
    ts-prune output: <file>:<line> - <name>[ (used in module)]

    `(used in module)` means it's used within the file but not exported —
    low confidence. Bare entries are high confidence.
    """
    symbols: list[DeadSymbol] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line or " - " not in line:
            continue
        loc_part, name_part = line.split(" - ", 1)
        m = re.match(r"^(?P<file>.+):(?P<line>\d+)$", loc_part)
        if not m:
            continue
        used_in_module = "(used in module)" in name_part
        name = name_part.replace("(used in module)", "").strip()
        file_rel = _to_rel(m.group("file"), workspace_path)
        symbols.append(DeadSymbol(
            file=file_rel,
            line=int(m.group("line")),
            name=name,
            kind="export",
            confidence="low" if used_in_module else "high",
            tool="ts-prune",
        ))
    return symbols


def _parse_vulture(stdout: str, workspace_path: Path) -> list[DeadSymbol]:
    """
    vulture output:
        path/to/file.py:NN: unused function 'name' (XX% confidence)
    """
    symbols: list[DeadSymbol] = []
    pattern = re.compile(
        r"^(?P<file>.+):(?P<line>\d+):\s+unused\s+(?P<kind>\w+)\s+"
        r"'(?P<name>[^']+)'\s+\((?P<conf>\d+)%\s+confidence\)"
    )
    for line in stdout.splitlines():
        m = pattern.match(line.strip())
        if not m:
            continue
        conf_int = int(m.group("conf"))
        confidence = "high" if conf_int >= 80 else "medium" if conf_int >= 60 else "low"
        symbols.append(DeadSymbol(
            file=_to_rel(m.group("file"), workspace_path),
            line=int(m.group("line")),
            name=m.group("name"),
            kind=m.group("kind"),
            confidence=confidence,
            tool="vulture",
        ))
    return symbols


def _parse_go_deadcode(stdout: str, workspace_path: Path) -> list[DeadSymbol]:
    """
    deadcode output:
        path/to/file.go:NN:NN: unreachable func name
    """
    symbols: list[DeadSymbol] = []
    pattern = re.compile(
        r"^(?P<file>[^:]+):(?P<line>\d+):\d+:\s+unreachable\s+(?P<kind>\w+)\s+(?P<name>\S+)"
    )
    for line in stdout.splitlines():
        m = pattern.match(line.strip())
        if not m:
            continue
        symbols.append(DeadSymbol(
            file=_to_rel(m.group("file"), workspace_path),
            line=int(m.group("line")),
            name=m.group("name"),
            kind=m.group("kind"),
            confidence="high",
            tool="deadcode",
        ))
    return symbols


def _to_rel(path: str, workspace_path: Path) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve().relative_to(workspace_path.resolve()))
    except ValueError:
        return path


def _lang_of(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return {
        ".ts": "ts", ".tsx": "tsx", ".js": "javascript", ".mjs": "javascript",
        ".py": "python", ".go": "go", ".rs": "rust",
    }.get(ext, "unknown")
