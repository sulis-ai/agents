"""
Phase 1.7 — wrapper rot detection.

Scan capability inventory (Phase 1.2) for classes whose names contain
suffixes suggesting they wrap another internal class (V2, V3, Facade,
Wrapper, Proxy, Compat, etc. — but NOT Adapter, since that's the legitimate
hexagonal-architecture pattern).

For each suspect, check if there's a sibling class with the suffix removed
(e.g. `OrderServiceV2` → look for `OrderService`). If found in the same
codebase, flag as candidate wrapper rot.

Reads the previously-written 1_2_capabilities.json rather than re-running
ast-grep.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from ..config import ASTGREP_WRAPPER_SUFFIXES, PHASE_FILES
from ..models import RunnerInput, RunnerResult, WrapperCandidate, WrappersPayload
from .base import make_result, now_iso


class WrapperRunner:
    PHASE: str = "1.7"
    TOOL: str = "ast-grep"   # via capability inventory

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []

        # Load 1.2 capabilities JSON
        caps_path = Path(inp.output_dir) / PHASE_FILES["1.2"]
        if not caps_path.exists():
            warnings.append("Phase 1.2 capabilities not found; wrapper detection skipped")
            payload = WrappersPayload(
                candidates=[], count_internal=0, count_external_likely=0
            )
            return make_result(
                phase=self.PHASE,
                tool=self.TOOL,
                started_at=started_at,
                started_monotonic=started_monotonic,
                payload=payload.__dict__,
                warnings=warnings,
            )

        try:
            data = json.loads(caps_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            warnings.append(f"Failed to read capabilities: {exc!r}")
            payload = WrappersPayload(candidates=[], count_internal=0, count_external_likely=0)
            return make_result(
                phase=self.PHASE, tool=self.TOOL,
                started_at=started_at, started_monotonic=started_monotonic,
                payload=payload.__dict__, warnings=warnings,
            )

        items = (data.get("payload") or {}).get("items") or []
        classes = [c for c in items if c.get("kind") == "class"]
        class_names = {c["name"]: c for c in classes if c.get("name")}

        candidates: list[WrapperCandidate] = []
        for cls in classes:
            name = cls.get("name") or ""
            for suffix in ASTGREP_WRAPPER_SUFFIXES:
                if name.endswith(suffix) and len(name) > len(suffix):
                    base = name[: -len(suffix)]
                    target = class_names.get(base)
                    is_external = False
                    if target:
                        # Internal: target class found in same codebase
                        candidates.append(
                            WrapperCandidate(
                                wrapper_class=name,
                                wrapper_file=cls.get("file", ""),
                                wrapper_line=cls.get("line", 0),
                                wrapped_target=base,
                                wrapped_file=target.get("file"),
                                suffix_match=suffix,
                                is_external_adapter_candidate=False,
                            )
                        )
                    else:
                        # No internal target — likely external SDK or false positive
                        is_external = True
                        candidates.append(
                            WrapperCandidate(
                                wrapper_class=name,
                                wrapper_file=cls.get("file", ""),
                                wrapper_line=cls.get("line", 0),
                                wrapped_target=None,
                                wrapped_file=None,
                                suffix_match=suffix,
                                is_external_adapter_candidate=True,
                            )
                        )
                    break  # one suffix match is enough

        count_internal = sum(1 for c in candidates if not c.is_external_adapter_candidate)
        count_external = sum(1 for c in candidates if c.is_external_adapter_candidate)

        payload = WrappersPayload(
            candidates=[c.__dict__ for c in candidates],
            count_internal=count_internal,
            count_external_likely=count_external,
        )

        return make_result(
            phase=self.PHASE,
            tool=self.TOOL,
            started_at=started_at,
            started_monotonic=started_monotonic,
            payload=payload.__dict__,
            warnings=warnings,
        )
