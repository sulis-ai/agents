"""
Phase 1.5 — coupling map.

Builds the import graph (per language) using the same regex patterns as
Phase 1.4. Computes:
- fan_in:  how many other modules import this one
- fan_out: how many other modules this one imports
- cycles:  Tarjan's strongly-connected-components algorithm

Cycles are structural smells — flagged for REORGANISE-Decompose.
"""

from __future__ import annotations

import time
from collections import defaultdict
from pathlib import Path

from ..config import HIGH_FANIN, HIGH_FANOUT
from ..filesystem import WalkConfig, walk_files
from ..models import CouplingPayload, ModuleCoupling, RunnerInput, RunnerResult
from .base import make_result, now_iso
from .reuse_runner import (
    _EXTENSIONS,
    _IMPORT_PATTERNS,
    _is_internal_target,
    _to_rel,
)


class CouplingRunner:
    PHASE: str = "1.5"
    TOOL: str = "ast-grep"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []
        workspace_path = Path(inp.workspace_path)

        # Build the import graph: source_file → {target_module, ...}
        edges_out: dict[str, set[str]] = defaultdict(set)

        for lang in inp.languages:
            exts = _EXTENSIONS.get(lang)
            patterns = _IMPORT_PATTERNS.get(lang)
            if not exts or not patterns:
                continue

            cfg = WalkConfig(
                root=workspace_path,
                include_patterns=tuple(f"*{e}" for e in exts),
            )
            for src_file in walk_files(cfg):
                try:
                    text = src_file.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                src_rel = _to_rel(src_file, workspace_path)
                for pat in patterns:
                    for match in pat.finditer(text):
                        target = match.group(1)
                        if not _is_internal_target(target, lang):
                            continue
                        edges_out[src_rel].add(target)

        # Build fan-in
        edges_in: dict[str, set[str]] = defaultdict(set)
        for src, targets in edges_out.items():
            for t in targets:
                edges_in[t].add(src)

        all_modules = set(edges_out.keys()) | set(edges_in.keys())

        # Detect cycles via Tarjan SCC on the directed graph
        cycles = _find_cycles(edges_out)

        # Build per-module records
        modules: list[ModuleCoupling] = []
        for mod in sorted(all_modules):
            out = sorted(edges_out.get(mod, set()))
            in_ = sorted(edges_in.get(mod, set()))
            modules.append(
                ModuleCoupling(
                    module=mod,
                    fan_in=len(in_),
                    fan_out=len(out),
                    imports_out=out,
                    imports_in=in_,
                )
            )

        high_fanin = [m.module for m in modules if m.fan_in > HIGH_FANIN]
        high_fanout = [m.module for m in modules if m.fan_out > HIGH_FANOUT]

        payload = CouplingPayload(
            modules=[m.__dict__ for m in modules],
            cycles=cycles,
            high_fanin=high_fanin,
            high_fanout=high_fanout,
        )

        return make_result(
            phase=self.PHASE, tool=self.TOOL,
            started_at=started_at, started_monotonic=started_monotonic,
            payload=payload.__dict__, warnings=warnings,
        )


def _find_cycles(edges: dict[str, set[str]]) -> list[list[str]]:
    """
    Tarjan's strongly-connected-components algorithm.

    Returns SCCs of size > 1 as lists of node names (= cycles). Self-loops
    (a → a) are also returned as single-node cycles.
    """
    index_counter = [0]
    stack: list[str] = []
    on_stack: set[str] = set()
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    result: list[list[str]] = []

    def strongconnect(v: str) -> None:
        indices[v] = index_counter[0]
        lowlinks[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)

        for w in edges.get(v, set()):
            if w not in indices:
                strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif w in on_stack:
                lowlinks[v] = min(lowlinks[v], indices[w])

        if lowlinks[v] == indices[v]:
            scc: list[str] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                scc.append(w)
                if w == v:
                    break
            if len(scc) > 1 or (len(scc) == 1 and scc[0] in edges.get(scc[0], set())):
                result.append(sorted(scc))

    all_nodes = set(edges.keys())
    for values in edges.values():
        all_nodes.update(values)

    # Use an iterative DFS in case of deep recursion (stdlib recursion limit)
    import sys as _sys
    old_limit = _sys.getrecursionlimit()
    _sys.setrecursionlimit(max(old_limit, 10000))
    try:
        for v in all_nodes:
            if v not in indices:
                strongconnect(v)
    finally:
        _sys.setrecursionlimit(old_limit)

    return result
