"""
Phase 1.3 — extension point catalogue.

Identifies abstract classes, interfaces with implementations, factories,
registries, and DI markers. Cross-references the capability inventory
(Phase 1.2) to find which classes implement each interface.

Sparse by design — we want strong-signal extension points, not all interfaces.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import ASTGREP_BASE_FLAGS, ASTGREP_EXTENSION_PATTERNS, PHASE_FILES
from ..models import ExtensionPayload, ExtensionPoint, RunnerInput, RunnerResult
from .base import make_result, now_iso, run_tool
from .astgrep_capability import _parse_astgrep_stream


class AstGrepExtensionRunner:
    PHASE: str = "1.3"
    TOOL: str = "ast-grep"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []
        extension_points: list[ExtensionPoint] = []

        # 1. Run extension-specific patterns (abstract classes, etc.)
        for lang in inp.languages:
            patterns = ASTGREP_EXTENSION_PATTERNS.get(lang, [])
            for kind, pattern in patterns:
                cmd = [
                    "ast-grep", *ASTGREP_BASE_FLAGS,
                    "-p", pattern, "-l", lang, inp.workspace_path,
                ]
                result = run_tool(cmd, tool="ast-grep", phase=self.PHASE)
                caps = _parse_astgrep_stream(
                    result.stdout,
                    workspace_path=Path(inp.workspace_path),
                    language=lang,
                    kind=kind,
                )
                for c in caps:
                    extension_points.append(
                        ExtensionPoint(
                            kind=c.kind,
                            name=c.name,
                            file=c.file,
                            line=c.line,
                            language=c.language,
                            contract=c.signature,
                            implementations=[],
                        )
                    )

        # 2. From capability inventory, treat interfaces as extension points
        #    Cross-reference 'implements' for TS (best-effort via signature scan)
        caps_path = Path(inp.output_dir) / PHASE_FILES["1.2"]
        if caps_path.exists():
            try:
                caps_data = json.loads(caps_path.read_text(encoding="utf-8"))
                items = (caps_data.get("payload") or {}).get("items") or []
                interfaces = [c for c in items if c.get("kind") == "interface"]
                for iface in interfaces:
                    extension_points.append(
                        ExtensionPoint(
                            kind="interface",
                            name=iface.get("name", ""),
                            file=iface.get("file", ""),
                            line=iface.get("line", 0),
                            language=iface.get("language", ""),
                            contract=iface.get("signature"),
                            implementations=[],  # populated below
                        )
                    )

                # Best-effort implementation detection via signature substring
                # (matches 'class Foo implements Bar' or 'class Foo extends Bar')
                interface_names = {iface.get("name") for iface in interfaces if iface.get("name")}
                for c in items:
                    if c.get("kind") != "class":
                        continue
                    sig = (c.get("signature") or "")
                    for iname in interface_names:
                        if f"implements {iname}" in sig or f"extends {iname}" in sig:
                            for ep in extension_points:
                                if ep.name == iname:
                                    ep.implementations.append(c.get("name", ""))
            except (OSError, json.JSONDecodeError) as exc:
                warnings.append(f"Failed to cross-reference capabilities: {exc!r}")

        by_kind: dict[str, int] = {}
        for ep in extension_points:
            by_kind[ep.kind] = by_kind.get(ep.kind, 0) + 1

        payload = ExtensionPayload(
            items=[ep.__dict__ for ep in extension_points],
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
