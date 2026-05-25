"""
Phase 1.8 — convention inventory.

Filesystem-driven heuristic detection of project conventions:
- File-naming style per language (PascalCase, kebab-case, snake_case)
- Test-file naming pattern
- Module layout (per-feature vs layered vs flat)
- Naming for roles (Repository, Service, etc.)
"""

from __future__ import annotations

import re
import time
from collections import Counter
from pathlib import Path

from ..filesystem import WalkConfig, walk_files
from ..models import ConventionsPayload, NamingObservation, RunnerInput, RunnerResult
from .base import make_result, now_iso


_CASE_PATTERNS = {
    "PascalCase": re.compile(r"^[A-Z][a-zA-Z0-9]*$"),
    "camelCase": re.compile(r"^[a-z][a-zA-Z0-9]*$"),
    "kebab-case": re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$"),
    "snake_case": re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$"),
    "lowercase": re.compile(r"^[a-z][a-z0-9]*$"),
}


class ConventionRunner:
    PHASE: str = "1.8"
    TOOL: str = "filesystem"

    def run(self, inp: RunnerInput) -> RunnerResult:
        started_at = now_iso()
        started_monotonic = time.monotonic()
        warnings: list[str] = []
        workspace_path = Path(inp.workspace_path)

        # Walk source files
        cfg = WalkConfig(root=workspace_path, max_depth=10)
        files = list(walk_files(cfg))

        # File-naming observation across all source files
        file_styles: Counter[str] = Counter()
        file_samples: dict[str, list[str]] = {style: [] for style in _CASE_PATTERNS}
        test_styles: Counter[str] = Counter()
        test_samples: dict[str, list[str]] = {style: [] for style in _CASE_PATTERNS}

        for p in files:
            ext = p.suffix.lower()
            if ext not in {".ts", ".tsx", ".js", ".py", ".go", ".rs", ".java", ".kt", ".rb"}:
                continue
            stem = p.stem
            rel = _to_rel(p, workspace_path)
            is_test = _is_test_file(rel, p.name)
            for style, pat in _CASE_PATTERNS.items():
                if pat.match(stem):
                    if is_test:
                        test_styles[style] += 1
                        if len(test_samples[style]) < 3:
                            test_samples[style].append(rel)
                    else:
                        file_styles[style] += 1
                        if len(file_samples[style]) < 3:
                            file_samples[style].append(rel)
                    break

        file_naming = _build_observation(file_styles, file_samples)
        test_naming = _build_observation(test_styles, test_samples)

        # Module layout heuristic
        layout = _infer_layout(files, workspace_path)

        # Error handling heuristic (Python only for now — most reliable signal)
        error_handling = _infer_error_handling(files, workspace_path, inp.languages)

        # Naming for roles
        role_patterns = _infer_role_patterns(files, workspace_path)

        payload = ConventionsPayload(
            file_naming=file_naming.__dict__ if file_naming else None,
            test_naming=test_naming.__dict__ if test_naming else None,
            module_layout=layout,
            error_handling=error_handling,
            naming_for_roles=role_patterns,
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


def _is_test_file(rel_path: str, name: str) -> bool:
    n = name.lower()
    if n.endswith((".test.ts", ".test.tsx", ".test.js", ".test.jsx")):
        return True
    if n.endswith(".spec.ts") or n.endswith(".spec.js"):
        return True
    if n.startswith("test_") and n.endswith(".py"):
        return True
    if n.endswith("_test.go") or n.endswith("_test.py"):
        return True
    if "/tests/" in rel_path.replace("\\", "/"):
        return True
    return False


def _build_observation(
    counts: Counter[str],
    samples: dict[str, list[str]],
) -> NamingObservation | None:
    if not counts:
        return None
    total = sum(counts.values())
    if total == 0:
        return None
    top_style, top_count = counts.most_common(1)[0]
    confidence = top_count / total
    return NamingObservation(
        pattern=top_style,
        confidence=round(confidence, 3),
        samples=samples.get(top_style, [])[:3],
    )


def _infer_layout(files: list[Path], workspace_path: Path) -> str:
    """
    Heuristic:
    - 'layered' if top-level dirs include domain/, application/, infrastructure/
    - 'per-feature' if top-level dirs are named after features
    - 'flat' if most code is at the top level
    - 'mixed' otherwise
    """
    top_dirs: set[str] = set()
    for p in files:
        try:
            rel = p.resolve().relative_to(workspace_path.resolve())
            parts = rel.parts
            if len(parts) > 1:
                top_dirs.add(parts[0])
        except ValueError:
            pass

    layered_markers = {"domain", "application", "infrastructure", "presentation", "interfaces"}
    if layered_markers & top_dirs:
        return "layered"
    if "src" in top_dirs and len(top_dirs) <= 3:
        # src/ + maybe tests/ + maybe docs/ = layered-style
        return "layered"
    if len(top_dirs) >= 5 and not layered_markers & top_dirs:
        return "per-feature"
    if len(top_dirs) <= 1:
        return "flat"
    return "mixed"


def _infer_error_handling(
    files: list[Path],
    workspace_path: Path,
    languages: tuple[str, ...],
) -> str:
    """
    Quick text scan for common patterns. Returns one of:
    - 'exceptions' — throw/raise dominant
    - 'result-types' — Result<T,E> / Either / Try imports observed
    - 'error-returns' — Go-style (err != nil)
    - 'mixed'
    """
    exceptions = 0
    result_types = 0
    error_returns = 0
    files_sampled = 0
    for p in files:
        ext = p.suffix.lower()
        if ext not in (".ts", ".tsx", ".js", ".py", ".go", ".rs"):
            continue
        try:
            text = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        files_sampled += 1
        if files_sampled > 200:
            break

        # exceptions
        if re.search(r"\bthrow\s+new\b|\braise\s+\w+\(", text):
            exceptions += 1
        # result types
        if re.search(r"\bResult<|\bEither<|\bResult\[\w+,\s*\w+\]", text):
            result_types += 1
        # go err returns
        if re.search(r"\bif\s+err\s*!=\s*nil\b", text):
            error_returns += 1

    candidates = {
        "exceptions": exceptions,
        "result-types": result_types,
        "error-returns": error_returns,
    }
    nonzero = [(k, v) for k, v in candidates.items() if v > 0]
    if not nonzero:
        return "unknown"
    if len(nonzero) == 1:
        return nonzero[0][0]
    top = max(nonzero, key=lambda kv: kv[1])
    top_count = top[1]
    second = sorted(nonzero, key=lambda kv: -kv[1])[1][1]
    # Dominant if 2x the runner-up
    if top_count >= 2 * second:
        return top[0]
    return "mixed"


_ROLE_SUFFIXES = ("Repository", "Service", "Adapter", "Handler", "Controller",
                  "Provider", "Factory", "Builder", "Manager", "Resolver",
                  "UseCase", "Command", "Query", "Event", "Listener")


def _infer_role_patterns(
    files: list[Path],
    workspace_path: Path,
) -> dict[str, str]:
    """Look for class-name suffixes that suggest standard roles."""
    role_counts: Counter[str] = Counter()
    for p in files:
        stem = p.stem
        for role in _ROLE_SUFFIXES:
            if stem.endswith(role):
                role_counts[role] += 1
                break

    out: dict[str, str] = {}
    for role, count in role_counts.most_common():
        if count >= 2:
            out[role.lower()] = f"*{role}"
    return out
