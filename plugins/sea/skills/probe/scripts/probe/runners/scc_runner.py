"""
Phase 1.1 — scc: language inventory + LOC + complexity averages.

Output: StackPayload (see models.py).
Source of truth: `scc --format json --by-file <root>`
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import SCC_BASE_FLAGS, SCC_EXCLUDE_DIRS
from ..models import FrameworkHint, LanguageStats, RunnerInput, RunnerResult, StackPayload
from .base import (
    Runner,
    ToolParseError,
    make_result,
    now_iso,
    run_tool,
)


# Map scc language names → internal language codes
_SCC_LANGUAGE_MAP = {
    "TypeScript": "ts",
    "TSX": "tsx",
    "JavaScript": "javascript",
    "Python": "python",
    "Go": "go",
    "Rust": "rust",
    "Java": "java",
}


class SccRunner:
    PHASE: str = "1.1"
    TOOL: str = "scc"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()

        exclude_arg = ",".join(SCC_EXCLUDE_DIRS)
        cmd = [
            "scc",
            *SCC_BASE_FLAGS,
            "--exclude-dir", exclude_arg,
            inp.workspace_path,
        ]

        result = run_tool(cmd, tool=self.TOOL, phase=self.PHASE)

        if result.returncode != 0 and not result.stdout.strip():
            raise ToolParseError(
                tool=self.TOOL,
                phase=self.PHASE,
                reason=f"scc exited {result.returncode} with no output",
                stderr=result.stderr,
            )

        payload = _parse_scc_output(
            result.stdout,
            workspace_path=Path(inp.workspace_path),
        )

        return make_result(
            phase=self.PHASE,
            tool=self.TOOL,
            started_at=started_at,
            started_monotonic=started_monotonic,
            payload=payload.__dict__ if hasattr(payload, "__dict__") else payload,
        )


def _parse_scc_output(stdout: str, *, workspace_path: Path) -> dict:
    """
    Parse scc's JSON output and produce StackPayload as a dict.

    scc --format json emits a list of language records:
        [{"Name": "TypeScript", "Files": [...], "Code": N, ...}, ...]
    """
    if not stdout.strip():
        return StackPayload(
            languages={},
            primary_language=None,
            total_files=0,
            total_loc=0,
            total_complexity=0,
            frameworks=[],
            manifest_files_found=[],
        ).__dict__

    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ToolParseError(
            tool="scc",
            phase="1.1",
            reason=f"scc JSON parse failed: {exc.msg}",
        ) from exc

    languages: dict[str, dict] = {}
    total_files = 0
    total_loc = 0
    total_complexity = 0

    for record in data:
        name = record.get("Name") or "Unknown"
        files = record.get("Count", 0) or len(record.get("Files") or [])
        code = record.get("Code", 0)
        blanks = record.get("Blank", 0)
        comments = record.get("Comment", 0)
        complexity = record.get("Complexity", 0)

        languages[name] = LanguageStats(
            files=files,
            code=code,
            blanks=blanks,
            comments=comments,
            complexity_total=complexity,
        ).__dict__

        total_files += files
        total_loc += code
        total_complexity += complexity

    primary_language = None
    if languages:
        primary_language = max(languages.items(), key=lambda kv: kv[1]["code"])[0]

    frameworks = _detect_frameworks(workspace_path)
    manifest_files = _detect_manifests(workspace_path)

    return StackPayload(
        languages=languages,
        primary_language=primary_language,
        total_files=total_files,
        total_loc=total_loc,
        total_complexity=total_complexity,
        frameworks=[fh.__dict__ for fh in frameworks],
        manifest_files_found=manifest_files,
    ).__dict__


_MANIFEST_NAMES = (
    "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "pom.xml", "build.gradle", "build.gradle.kts",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    "requirements.txt", "Pipfile", "setup.py",
    "Gemfile", "composer.json",
)


def _detect_manifests(workspace_path: Path) -> list[str]:
    """Find common manifest files in the workspace root."""
    found: list[str] = []
    for name in _MANIFEST_NAMES:
        p = workspace_path / name
        if p.exists() and p.is_file():
            found.append(name)
    return found


def _detect_frameworks(workspace_path: Path) -> list[FrameworkHint]:
    """
    Best-effort framework detection from package.json / pyproject.toml.

    We don't aim for completeness — just enough to anchor the LLM's stack
    inference. Confidence is "high" when a manifest mentions the package
    by name, "low" otherwise.
    """
    hints: list[FrameworkHint] = []

    # package.json
    pkg = workspace_path / "package.json"
    if pkg.exists():
        try:
            data = json.loads(pkg.read_text(encoding="utf-8"))
            deps = {
                **(data.get("dependencies") or {}),
                **(data.get("devDependencies") or {}),
            }
            for known in (
                "express", "fastify", "koa", "next", "react", "vue", "svelte",
                "nestjs", "@nestjs/core", "vitest", "jest", "mocha",
            ):
                if known in deps:
                    hints.append(FrameworkHint(name=known, source="package.json", confidence="high"))
        except (OSError, json.JSONDecodeError):
            pass

    # pyproject.toml
    pyproject = workspace_path / "pyproject.toml"
    if pyproject.exists():
        try:
            text = pyproject.read_text(encoding="utf-8")
            for known in ("django", "flask", "fastapi", "starlette", "sqlalchemy", "pydantic"):
                if known in text.lower():
                    hints.append(FrameworkHint(name=known, source="pyproject.toml", confidence="medium"))
        except OSError:
            pass

    return hints
