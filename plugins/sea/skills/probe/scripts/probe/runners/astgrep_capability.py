"""
Phase 1.2 — ast-grep: capability inventory (classes, functions, types).

For each language detected in Phase 1.1, run ast-grep with the patterns
from config.ASTGREP_CAPABILITY_PATTERNS. Aggregates results into one
CapabilityPayload.

Critical gotchas (from config.py comments):
- ASTGREP_BASE_FLAGS includes --no-ignore hidden --no-ignore dot (v0.7.2)
- Python uses BARE keywords; TS/Go/Rust use partial $NAME patterns (v0.7.1/2)
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from ..config import ASTGREP_BASE_FLAGS, ASTGREP_CAPABILITY_PATTERNS
from ..models import Capability, CapabilityPayload, RunnerInput, RunnerResult
from .base import (
    ToolParseError,
    make_result,
    now_iso,
    run_tool,
)


class AstGrepCapabilityRunner:
    PHASE: str = "1.2"
    TOOL: str = "ast-grep"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()

        all_capabilities: list[Capability] = []
        warnings: list[str] = []

        languages = inp.languages or tuple(ASTGREP_CAPABILITY_PATTERNS.keys())

        for lang in languages:
            patterns = ASTGREP_CAPABILITY_PATTERNS.get(lang)
            if not patterns:
                continue

            for kind, pattern in patterns:
                caps, warn = _run_pattern(
                    workspace_path=inp.workspace_path,
                    language=lang,
                    pattern=pattern,
                    kind=kind,
                )
                all_capabilities.extend(caps)
                if warn:
                    warnings.append(warn)

        # Deduplicate (same file+line+kind+name)
        unique: dict[tuple, Capability] = {}
        for c in all_capabilities:
            key = (c.file, c.line, c.kind, c.name)
            unique.setdefault(key, c)
        all_capabilities = sorted(
            unique.values(),
            key=lambda c: (c.file, c.line, c.kind, c.name),
        )

        by_language: dict[str, int] = {}
        by_kind: dict[str, int] = {}
        for c in all_capabilities:
            by_language[c.language] = by_language.get(c.language, 0) + 1
            by_kind[c.kind] = by_kind.get(c.kind, 0) + 1

        payload = CapabilityPayload(
            items=[c.__dict__ for c in all_capabilities],
            by_language=by_language,
            by_kind=by_kind,
        )

        return make_result(
            phase=self.PHASE,
            tool=self.TOOL,
            started_at=started_at,
            started_monotonic=started_monotonic,
            payload=payload.__dict__,
            warnings=warnings,
        )


def _run_pattern(
    *,
    workspace_path: str,
    language: str,
    pattern: str,
    kind: str,
) -> tuple[list[Capability], str | None]:
    """Run one ast-grep query and parse the JSON-stream output."""
    cmd = [
        "ast-grep",
        *ASTGREP_BASE_FLAGS,
        "-p", pattern,
        "-l", language,
        workspace_path,
    ]

    result = run_tool(cmd, tool="ast-grep", phase="1.2")

    if result.returncode != 0 and not result.stdout.strip():
        return [], f"ast-grep `{pattern}` ({language}) returned non-zero with empty stdout"

    return _parse_astgrep_stream(
        result.stdout,
        workspace_path=Path(workspace_path),
        language=language,
        kind=kind,
    ), None


def _parse_astgrep_stream(
    stdout: str,
    *,
    workspace_path: Path,
    language: str,
    kind: str,
) -> list[Capability]:
    """
    Parse ast-grep `--json=stream` output.

    Each line is a JSON object with at least:
        {"file": "...", "range": {"start": {"line": N, ...}, ...}, "text": "..."}
    """
    caps: list[Capability] = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue

        file_path = obj.get("file") or obj.get("path") or ""
        if not file_path:
            continue

        # Convert to repo-relative
        try:
            rel = str(Path(file_path).resolve().relative_to(workspace_path.resolve()))
        except ValueError:
            rel = file_path

        # Extract line
        line_no = 0
        rng = obj.get("range") or {}
        start = rng.get("start") or {}
        line_no = int(start.get("line") or start.get("row") or 0)
        if line_no == 0:
            # Try alternative key
            line_no = int(obj.get("line") or 0)

        # Extract name from metaVariables or text
        name = _extract_name(obj, kind=kind)
        text = (obj.get("text") or "").strip()

        # Visibility heuristic
        visibility = "exported" if text.startswith(("export ", "pub ")) else "internal"

        caps.append(
            Capability(
                kind=kind,
                name=name,
                file=rel,
                line=line_no,
                language=language,
                signature=text[:200] if text else None,
                visibility=visibility,
            )
        )
    return caps


_IDENT_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_KEYWORDS = {"class", "def", "function", "interface", "type", "struct",
             "enum", "trait", "fn", "func", "abstract", "export", "pub",
             "async", "public", "private", "protected", "static"}


def _extract_name(obj: dict, *, kind: str) -> str:
    """
    Pull the $NAME metavariable if present (TS/Go/Rust patterns include it);
    otherwise parse the name from the matched line text (Python's bare-keyword
    patterns return only the keyword as `text`).
    """
    # Path 1: $NAME metavariable (from patterns like 'class $NAME')
    metavars = obj.get("metaVariables") or {}
    single = metavars.get("single") or {}
    name_node = single.get("NAME")
    if isinstance(name_node, dict):
        name_text = name_node.get("text")
        if name_text:
            return name_text.strip()

    # Path 2: parse from `lines` (full line context, available for bare-keyword
    # Python patterns like 'class' or 'def').
    lines_text = obj.get("lines") or obj.get("text") or ""
    # First line only (multi-line matches are rare here)
    first_line = lines_text.splitlines()[0] if lines_text else ""

    # Skip leading keywords and find first identifier-like token
    for token in _IDENT_RE.findall(first_line):
        if token not in _KEYWORDS:
            return token

    return "<unknown>"
