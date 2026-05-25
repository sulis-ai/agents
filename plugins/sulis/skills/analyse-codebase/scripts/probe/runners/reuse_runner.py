"""
Phase 1.4 — reuse / consumer counts.

For each source file (per language), count how many other files import it.
High-consumer-count modules are candidates for Reuse recommendations;
kitchen-sink modules (many exports, heterogeneous consumers) get flagged
for Decompose.

Uses simple text-based import scanning rather than ast-grep — fast and
captures most patterns:
- TS/JS:  `from '...path...'`, `require('...')`, `import('...')`
- Python: `from path import ...`, `import path`
- Go:     `import "path"`
- Rust:   `use path::...`
"""

from __future__ import annotations

import re
import time
from collections import defaultdict
from pathlib import Path

from ..config import REUSE_CONSUMER_THRESHOLD
from ..filesystem import WalkConfig, walk_files
from ..models import ReusableModule, ReusePayload, RunnerInput, RunnerResult
from .base import make_result, now_iso


# Per-language import regex (compiled once)
_IMPORT_PATTERNS: dict[str, list[re.Pattern]] = {
    "ts": [
        re.compile(r"""from\s+['"]([^'"]+)['"]"""),
        re.compile(r"""import\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
        re.compile(r"""require\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
    ],
    "tsx": None,         # filled below from ts
    "javascript": None,  # filled below from ts
    "python": [
        re.compile(r"""^\s*from\s+([\w.]+)\s+import""", re.MULTILINE),
        re.compile(r"""^\s*import\s+([\w.]+)""", re.MULTILINE),
    ],
    "go": [
        re.compile(r"""^\s*import\s+(?:\(\s*)?["']([^"']+)["']""", re.MULTILINE),
        re.compile(r"""^\s+["']([^"']+)["']""", re.MULTILINE),  # multi-line import block
    ],
    "rust": [
        re.compile(r"""^\s*use\s+([\w:]+)""", re.MULTILINE),
    ],
}
_IMPORT_PATTERNS["tsx"] = _IMPORT_PATTERNS["ts"]
_IMPORT_PATTERNS["javascript"] = _IMPORT_PATTERNS["ts"]


_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "ts": (".ts",), "tsx": (".tsx",),
    "javascript": (".js", ".mjs", ".cjs"),
    "python": (".py",), "go": (".go",), "rust": (".rs",),
}


class ReuseRunner:
    PHASE: str = "1.4"
    TOOL: str = "grep"   # logical name; we use Python regex

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []

        workspace_path = Path(inp.workspace_path)

        # Collect all source files for active languages
        all_files: dict[str, list[Path]] = {}  # lang → files
        for lang in inp.languages:
            exts = _EXTENSIONS.get(lang)
            if not exts:
                continue
            cfg = WalkConfig(
                root=workspace_path,
                include_patterns=tuple(f"*{e}" for e in exts),
            )
            all_files[lang] = list(walk_files(cfg))

        # For each language, count how many files import each module path
        consumer_counts: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: defaultdict(set)
        )
        # consumer_counts[lang][module_target] = set of importing files

        for lang, files in all_files.items():
            patterns = _IMPORT_PATTERNS.get(lang) or []
            for src_file in files:
                try:
                    text = src_file.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                src_rel = _to_rel(src_file, workspace_path)
                for pat in patterns:
                    for match in pat.finditer(text):
                        target = match.group(1)
                        # Filter: only count internal targets
                        if not _is_internal_target(target, lang):
                            continue
                        consumer_counts[lang][target].add(src_rel)

        # Build ReusableModule list
        modules: list[ReusableModule] = []
        for lang, targets in consumer_counts.items():
            for target, consumers in targets.items():
                if len(consumers) < REUSE_CONSUMER_THRESHOLD:
                    continue
                modules.append(
                    ReusableModule(
                        module_path=target,
                        language=lang,
                        consumers=sorted(consumers),
                        consumer_count=len(consumers),
                        is_kitchen_sink=_is_kitchen_sink(target),
                    )
                )
        modules.sort(key=lambda m: -m.consumer_count)

        top = [m.module_path for m in modules[:20]]
        payload = ReusePayload(
            modules=[m.__dict__ for m in modules],
            top_by_consumer_count=top,
        )

        return make_result(
            phase=self.PHASE, tool=self.TOOL,
            started_at=started_at, started_monotonic=started_monotonic,
            payload=payload.__dict__, warnings=warnings,
        )


def _to_rel(path: Path, workspace_path: Path) -> str:
    try:
        return str(path.resolve().relative_to(workspace_path.resolve()))
    except ValueError:
        return str(path)


def _is_internal_target(target: str, lang: str) -> bool:
    """
    Heuristic: filter out external packages.

    - TS/JS: paths starting with `.` or `/` are internal; otherwise external
    - Python: anything not in stdlib + not starting with capital
              (heuristic — capital-letter imports are often classes)
    - Go: paths containing `/` and starting with project domain are tricky;
          we accept anything containing `/` (cross-module) as internal candidate
    - Rust: any `use` is in-crate (good enough)
    """
    if lang in ("ts", "tsx", "javascript"):
        return target.startswith(".") or target.startswith("/")
    if lang == "python":
        # Exclude common stdlib + popular packages
        top = target.split(".")[0]
        STDLIB = {
            "os", "sys", "re", "json", "typing", "pathlib", "subprocess",
            "datetime", "time", "collections", "dataclasses", "functools",
            "itertools", "math", "random", "string", "io", "logging",
            "argparse", "abc", "asyncio", "contextlib", "copy", "enum",
            "hashlib", "html", "http", "tempfile", "threading", "traceback",
            "unittest", "urllib", "uuid", "warnings", "xml",
        }
        EXTERNAL_HINTS = {
            "pytest", "numpy", "pandas", "django", "flask", "fastapi",
            "requests", "httpx", "aiohttp", "sqlalchemy", "pydantic",
            "click", "rich", "loguru", "structlog", "tenacity", "pyyaml",
        }
        if top in STDLIB or top in EXTERNAL_HINTS:
            return False
        return True
    if lang == "go":
        # Internal targets typically contain at least one slash AND don't
        # start with a known external domain
        if "/" not in target:
            return False
        first = target.split("/")[0]
        return first not in ("github.com", "golang.org", "google.golang.org", "gopkg.in")
    if lang == "rust":
        # Filter out std and common crates
        top = target.split(":")[0].strip()
        return top not in ("std", "core", "alloc", "serde", "tokio", "anyhow", "thiserror")
    return True


def _is_kitchen_sink(module_path: str) -> bool:
    """Heuristic: utility/helper modules are kitchen-sink candidates."""
    p = module_path.lower()
    return any(s in p for s in ("util", "helper", "common", "misc", "lib/", "legacy"))
