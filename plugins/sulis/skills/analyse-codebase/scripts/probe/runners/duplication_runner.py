"""
Phase 1.12 — code duplication via jscpd.

Graceful skip if jscpd not on PATH.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import DUPLICATION_HIGH_THRESHOLD_PCT, JSCPD_MIN_LINES, JSCPD_MIN_TOKENS
from ..models import BlockInstance, DuplicateBlock, DuplicationPayload, RunnerInput, RunnerResult
from .base import is_tool_available, make_result, now_iso, run_tool


class DuplicationRunner:
    PHASE: str = "1.12"
    TOOL: str = "jscpd"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []
        workspace_path = Path(inp.workspace_path)

        if not is_tool_available("jscpd"):
            warnings.append("jscpd not installed; duplication detection skipped")
            payload = DuplicationPayload(
                blocks=[], duplicated_lines=0, duplicated_pct=0.0,
                threshold_min_lines=JSCPD_MIN_LINES,
                threshold_min_tokens=JSCPD_MIN_TOKENS,
            )
            return make_result(
                phase=self.PHASE, tool=self.TOOL,
                started_at=started_at, started_monotonic=started_monotonic,
                payload=payload.__dict__, warnings=warnings,
            )

        out_dir = Path(inp.output_dir) / "_jscpd"
        out_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "jscpd",
            "--min-lines", str(JSCPD_MIN_LINES),
            "--min-tokens", str(JSCPD_MIN_TOKENS),
            "--reporters", "json",
            "--output", str(out_dir),
            "--silent",
            inp.workspace_path,
        ]
        try:
            run_tool(cmd, tool=self.TOOL, phase=self.PHASE)
        except Exception as exc:
            warnings.append(f"jscpd failed: {exc!r}")

        # jscpd writes jscpd-report.json
        report_path = out_dir / "jscpd-report.json"
        blocks: list[DuplicateBlock] = []
        duplicated_lines = 0
        duplicated_pct = 0.0

        if report_path.exists():
            try:
                data = json.loads(report_path.read_text(encoding="utf-8"))
                stats = (data.get("statistics") or {}).get("total") or {}
                duplicated_lines = int(stats.get("duplicatedLines", 0))
                duplicated_pct = float(stats.get("percentage", 0.0))

                duplicates = data.get("duplicates") or []
                for dup in duplicates:
                    first = dup.get("firstFile") or {}
                    second = dup.get("secondFile") or {}
                    instances = []
                    for f in (first, second):
                        instances.append(
                            BlockInstance(
                                file=_to_rel(f.get("name", ""), workspace_path),
                                line_start=int(f.get("start", 0)),
                                line_end=int(f.get("end", 0)),
                            )
                        )
                    blocks.append(
                        DuplicateBlock(
                            instances=[i.__dict__ for i in instances],
                            tokens=int(dup.get("tokens", 0)),
                            lines=int(dup.get("lines", 0)),
                        )
                    )
            except (OSError, json.JSONDecodeError, ValueError) as exc:
                warnings.append(f"jscpd report parse failed: {exc!r}")

        payload = DuplicationPayload(
            blocks=[b.__dict__ for b in blocks],
            duplicated_lines=duplicated_lines,
            duplicated_pct=duplicated_pct,
            threshold_min_lines=JSCPD_MIN_LINES,
            threshold_min_tokens=JSCPD_MIN_TOKENS,
        )
        return make_result(
            phase=self.PHASE, tool=self.TOOL,
            started_at=started_at, started_monotonic=started_monotonic,
            payload=payload.__dict__, warnings=warnings,
        )


def _to_rel(path: str, workspace_path: Path) -> str:
    if not path:
        return ""
    try:
        return str(Path(path).resolve().relative_to(workspace_path.resolve()))
    except ValueError:
        return path
