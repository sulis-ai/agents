"""
Phase 1.6 — lizard: cyclomatic complexity hotspots.

Output: ComplexityPayload with high-CCN functions + fragile files.
v0.7.1 fix: correct flags (--CCN, -L, -w; not -E).
v0.7.2 fix: explicit excludes for .venv, site-packages, etc.
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from pathlib import Path

from ..config import (
    HIGH_CCN_THRESHOLD,
    LIZARD_BASE_FLAGS,
    LIZARD_EXCLUDE_GLOBS,
    LIZARD_LANG_MAP,
    MODULE_FRAGILITY_CCN,
)
from ..models import ComplexFunction, ComplexityPayload, FragileFile, RunnerInput, RunnerResult
from .base import make_result, now_iso, run_tool


# lizard warning line format:
#   path/to/file.py:NN: warning: name has NLOC, CCN, token, PARAM, length, ND
_WARNING_RE = re.compile(
    r"^(?P<file>[^:]+):(?P<line>\d+):\s*warning:\s+"
    r"(?P<func>\S+)\s+has\s+"
    r"(?P<nloc>\d+)\s*NLOC,\s+"
    r"(?P<ccn>\d+)\s*CCN,\s+"
    r"(?P<tokens>\d+)\s*token,\s+"
    r"(?P<params>\d+)\s*PARAM,\s+"
    r"(?P<length>\d+)\s*length"
)


class LizardRunner:
    PHASE: str = "1.6"
    TOOL: str = "lizard"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()

        cmd = ["lizard", *LIZARD_BASE_FLAGS]
        # Add language filters
        for lang in inp.languages:
            lizard_lang = LIZARD_LANG_MAP.get(lang)
            if lizard_lang:
                cmd.extend(["-l", lizard_lang])
        # Add exclude globs
        for glob in LIZARD_EXCLUDE_GLOBS:
            cmd.extend(["-x", glob])
        cmd.append(inp.workspace_path)

        result = run_tool(cmd, tool=self.TOOL, phase=self.PHASE)

        payload = _parse_lizard_warnings(
            result.stdout,
            workspace_path=Path(inp.workspace_path),
        )

        return make_result(
            phase=self.PHASE,
            tool=self.TOOL,
            started_at=started_at,
            started_monotonic=started_monotonic,
            payload=payload.__dict__,
        )


def _parse_lizard_warnings(stdout: str, *, workspace_path: Path) -> ComplexityPayload:
    """Parse lizard's -w output (warning-only mode)."""
    functions: list[ComplexFunction] = []
    file_ccns: dict[str, list[int]] = defaultdict(list)

    for line in stdout.splitlines():
        m = _WARNING_RE.match(line.strip())
        if not m:
            continue

        file_abs = m.group("file")
        try:
            rel = str(Path(file_abs).resolve().relative_to(workspace_path.resolve()))
        except ValueError:
            rel = file_abs

        line_start = int(m.group("line"))
        nloc = int(m.group("nloc"))
        # length is the function body length in lines
        length = int(m.group("length"))
        line_end = line_start + length - 1

        ccn = int(m.group("ccn"))
        tokens = int(m.group("tokens"))
        params = int(m.group("params"))

        functions.append(
            ComplexFunction(
                file=rel,
                function=m.group("func"),
                line_start=line_start,
                line_end=line_end,
                ccn=ccn,
                nloc=nloc,
                tokens=tokens,
                params=params,
            )
        )
        file_ccns[rel].append(ccn)

    # Sort hotspots by CCN descending
    functions.sort(key=lambda f: -f.ccn)

    fragile: list[FragileFile] = []
    for fpath, ccns in file_ccns.items():
        if not ccns:
            continue
        avg = sum(ccns) / len(ccns)
        if avg > MODULE_FRAGILITY_CCN:
            fragile.append(
                FragileFile(file=fpath, avg_ccn=round(avg, 2), function_count=len(ccns))
            )
    fragile.sort(key=lambda f: -f.avg_ccn)

    return ComplexityPayload(
        functions=[f.__dict__ for f in functions],
        fragile_files=[f.__dict__ for f in fragile],
        threshold_ccn=HIGH_CCN_THRESHOLD,
        threshold_file_avg=MODULE_FRAGILITY_CCN,
    )
