#!/usr/bin/env python3
"""Stranger-reader legibility audit.

Three heuristic families: naming clarity (per identifier), module cohesion
(per file), jargon density (per module). Read-only — never modifies code.

Scope auto-detects PR-diff vs whole-codebase from local git state; can be
overridden via --scope, --base-branch, or --pr-number.

Usage:

    # auto-detect scope
    python3 audit.py [--raw] [--kitchen-sink-threshold 1500]

    # explicit PR scope (local diff)
    python3 audit.py --scope pr --base-branch main

    # explicit codebase scope
    python3 audit.py --scope codebase

    # remote PR (via gh CLI)
    python3 audit.py --pr-number 142

Output:
- JSON envelope to stdout when --raw is set
- Markdown structured report otherwise (intended for SKILL.md consumption)

Exit codes:
- 0 = success (regardless of finding count)
- 1 = usage error
- 2 = filesystem / git error
- 3 = no files in scope (e.g. PR diff returned 0 source files)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# _lib/ shared helpers (canonical pattern per add-skill v0.6.0).
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from _lib import allowlist as _allowlist  # noqa: E402
from _lib import scope as _scope  # noqa: E402


# ─── Constants ───────────────────────────────────────────────────────


DEFAULT_KITCHEN_SINK_LOC = 1500
DEFAULT_KITCHEN_SINK_CONCERNS = 4
DEFAULT_JARGON_DENSITY_THRESHOLD = 0.15

SOURCE_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".rb", ".go", ".rs", ".java",
    ".kt", ".swift", ".cs", ".scala", ".php", ".sh",
}

# Names that almost certainly mean "do nothing meaningful at all".
# Note: protocol-method names (run, execute, handle, get, set, add, find, save, load)
# are deliberately EXCLUDED here — they're conventional in Runner/Command/Handler
# /Strategy patterns. We only flag them if they're module-level (not class methods).
MAGIC_METHOD_PATTERNS = {
    "process", "do_it", "doit", "go",
    "process_data", "do_thing", "do_stuff", "do_work",
    "main_proc", "the_thing", "do_x", "process_x", "handle_request",
}

# Protocol-method names — legitimate when on a class, magic when standalone
PROTOCOL_METHOD_NAMES = {
    "run", "execute", "handle", "get", "set", "add", "remove", "find",
    "save", "load", "create", "update", "delete", "fetch", "send",
    "open", "close", "start", "stop", "init", "build", "compile",
    "render", "parse", "format", "serialize", "deserialize",
}

# Common loop-variable / index names that SHOULD be short.
# Includes Node.js stdlib aliases (`fs` / `os` / `vm`) and common
# language-keyword adjacents that aren't abbreviations.
ACCEPTABLE_SHORT_NAMES = {
    "i", "j", "k", "n", "x", "y", "z", "_", "id", "ok", "fn", "fd",
    "to", "of", "in", "on", "at", "as", "is", "or", "by", "up", "no",
    "fs", "os", "vm", "io", "db", "ws", "rx", "tx",
}

# Path patterns that exempt files from specific heuristics
TEST_FILE_PATTERNS = (
    re.compile(r"(^|/)tests?/"),
    re.compile(r"(^|/)__tests__/"),
    re.compile(r"(^|/)spec/"),
    re.compile(r"\.test\."),
    re.compile(r"\.spec\."),
    re.compile(r"^test_"),
    re.compile(r"_test\."),
)
FIXTURE_PATH_PATTERNS = (
    re.compile(r"(^|/)fixtures?/"),
    re.compile(r"(^|/)testdata/"),
    re.compile(r"(^|/)mocks?/"),
)


def is_test_file(path: str) -> bool:
    return any(p.search(path) for p in TEST_FILE_PATTERNS)


def is_fixture_file(path: str) -> bool:
    return any(p.search(path) for p in FIXTURE_PATH_PATTERNS)


# ─── Data structures ────────────────────────────────────────────────


@dataclass
class Finding:
    heuristic: str  # naming-clarity | kitchen-sink-file | jargon-density | etc.
    severity: str   # high | concern | advisory | info
    file: str       # path relative to repo root
    line: int       # 0 if file-level
    identifier: str  # the offending symbol/name (empty for file-level)
    message: str    # operator-vocab message
    suggestion: str  # optional rename or restructure suggestion
    extras: dict = field(default_factory=dict)


@dataclass
class AuditEnvelope:
    scope: str  # "pr" | "codebase"
    base_branch: str  # detected/used base
    pr_number: int | None
    files_audited: int
    findings: list[Finding]
    vocabulary_sources: list[str]
    kitchen_sink_threshold_loc: int
    kitchen_sink_threshold_concerns: int
    errors: list[str]
    primitive_status: dict[str, str] = field(default_factory=dict)


# ─── External tool integration (v0.20.0+) ─────────────────────────


def _run_readability_tools(
    repo_root: Path,
    *,
    timeout: int = 300,
) -> tuple[list[Finding], dict[str, str], list[str]]:
    """Invoke lizard (CQ-01) + jscpd (CQ-03) wrappers and convert findings."""
    from _lib.tools import lizard, jscpd

    findings: list[Finding] = []
    primitive_status: dict[str, str] = {}
    errors: list[str] = []
    repo_root_str = str(repo_root)

    # lizard — CQ-01 cyclomatic complexity
    if lizard.is_available().value != "not_available":
        try:
            result = lizard.run(repo_root=repo_root_str, timeout=timeout)
            for tf in lizard.parse_findings(result, repo_root_str):
                findings.append(Finding(
                    heuristic="cyclomatic-complexity",
                    severity=tf["severity"],
                    file=tf["file"],
                    line=tf["line"],
                    identifier=tf["extras"]["function_name"],
                    message=tf["message"],
                    suggestion=f"refactor — extract sub-functions; target CCN ≤ {lizard.DEFAULT_CCN_THRESHOLD}",
                    extras=tf["extras"],
                ))
            primitive_status["CQ-01"] = "PASS"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"lizard invocation failed: {exc}")
    else:
        primitive_status["CQ-01"] = "NOT_ASSESSED"

    # jscpd — CQ-03 code duplication
    if jscpd.is_available().value != "not_available":
        try:
            result = jscpd.run(repo_root=repo_root_str, timeout=timeout)
            for tf in jscpd.parse_findings(result, repo_root_str):
                findings.append(Finding(
                    heuristic="code-duplication",
                    severity=tf["severity"],
                    file=tf["file"],
                    line=tf["line"],
                    identifier="duplicate-block",
                    message=tf["message"],
                    suggestion="extract shared module / function",
                    extras=tf["extras"],
                ))
            primitive_status["CQ-03"] = "PASS"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"jscpd invocation failed: {exc}")
    else:
        primitive_status["CQ-03"] = "NOT_ASSESSED"

    return findings, primitive_status, errors


# ─── Scope detection ────────────────────────────────────────────────
# Inline implementation removed in v0.11.x — uses _lib/scope.
# Wrappers below preserve the original call signatures so the rest of
# the file doesn't need to change.


def detect_base_branch(repo_root: Path) -> str:
    return _scope.detect_base_branch(repo_root)


def detect_scope(repo_root: Path, base_branch: str) -> tuple[str, list[str]]:
    return _scope.detect_scope(repo_root, base_branch)


def fetch_pr_files(pr_number: int, repo_root: Path) -> tuple[list[str], list[str]]:
    return _scope.fetch_pr_files(pr_number, repo_root)


def list_codebase_files(repo_root: Path) -> list[str]:
    return _scope.list_codebase_files(repo_root, SOURCE_EXTENSIONS)


def filter_source_files(files: list[str]) -> list[str]:
    return [f for f in files if Path(f).suffix in SOURCE_EXTENSIONS]


# ─── Vocabulary loading ─────────────────────────────────────────────


def load_vocabulary(repo_root: Path) -> tuple[set[str], list[str]]:
    """Load known-vocabulary terms from project + marketplace standards.

    Returns (vocab_set, sources_loaded).
    """
    vocab: set[str] = set()
    sources: list[str] = []

    candidates = [
        repo_root / "plugins" / "sea" / "references" / "boring-code.md",
        repo_root / "plugins" / "srd" / "references" / "founder-english.md",
        repo_root / "GLOSSARY.md",
        repo_root / "plugins" / "sulis" / "skills" / "check-readability"
            / "references" / "check-readability-vocabulary.md",
    ]
    # Also any .specifications/*/GLOSSARY.md
    specs_dir = repo_root / ".specifications"
    if specs_dir.is_dir():
        candidates.extend(specs_dir.glob("*/GLOSSARY.md"))

    for path in candidates:
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        sources.append(str(path.relative_to(repo_root)))
        # Heuristic: extract code-like identifiers (`backtick` or **bold-term**)
        # and bullet-list items that look like vocab entries
        for match in re.finditer(r"`([a-zA-Z_][a-zA-Z0-9_-]+)`", text):
            vocab.add(match.group(1).lower())
        for match in re.finditer(r"\*\*([a-zA-Z][a-zA-Z0-9_ -]+?)\*\*", text):
            term = match.group(1).strip().lower().replace(" ", "")
            if 2 < len(term) < 30:
                vocab.add(term)
        # Bullet items: "- term — definition" or "- **term** — definition"
        for match in re.finditer(r"^[-*]\s+(?:\*\*)?([a-zA-Z][a-zA-Z0-9_-]+)", text, re.MULTILINE):
            vocab.add(match.group(1).lower())

    return vocab, sources


# ─── Heuristics ─────────────────────────────────────────────────────


def extract_identifiers(text: str, file_path: str) -> list[tuple[int, str, str, bool]]:
    """Return list of (line_no, identifier_kind, identifier_name, is_class_method).

    Kinds: function, class, variable. Light heuristic — supports common
    languages but not exhaustively. The `is_class_method` flag is True for
    Python methods (functions defined inside a class). Used to suppress
    false-positives on protocol-method names like `run`/`execute`.
    """
    out: list[tuple[int, str, str, bool]] = []
    ext = Path(file_path).suffix

    patterns = {
        ".py": [
            (r"^(\s*)def\s+(\w+)", "function"),
            (r"^\s*class\s+(\w+)", "class"),
            (r"^([A-Z_][A-Z0-9_]+)\s*=", "constant"),
        ],
        ".js": [
            (r"function\s+(\w+)", "function"),
            (r"class\s+(\w+)", "class"),
            (r"const\s+(\w+)\s*=", "variable"),
        ],
        ".ts": [
            (r"function\s+(\w+)", "function"),
            (r"class\s+(\w+)", "class"),
            (r"const\s+(\w+)\s*=", "variable"),
            (r"interface\s+(\w+)", "type"),
        ],
        ".rb": [
            (r"^\s*def\s+(\w+)", "function"),
            (r"^\s*class\s+(\w+)", "class"),
        ],
        ".go": [
            (r"^func\s+(?:\([^)]+\)\s+)?(\w+)", "function"),
            (r"^type\s+(\w+)\s+struct", "class"),
        ],
    }
    patterns[".jsx"] = patterns[".js"]
    patterns[".tsx"] = patterns[".ts"]

    rules = patterns.get(ext)
    if not rules:
        return out

    # For Python, track whether a `def` is indented (class method) or top-level
    is_python = ext == ".py"

    for lineno, line in enumerate(text.splitlines(), start=1):
        for pattern, kind in rules:
            match = re.search(pattern, line)
            if not match:
                continue
            is_method = False
            if is_python and kind == "function":
                indent = match.group(1)
                identifier = match.group(2)
                is_method = len(indent) > 0
            elif kind == "constant":
                identifier = match.group(1)
            else:
                # group(1) is the name for non-Python or class-pattern
                identifier = match.group(2) if (is_python and kind == "function") else match.group(1)
            out.append((lineno, kind, identifier, is_method))
    return out


def is_magic_name(name: str, is_class_method: bool = False, file_path: str = "") -> bool:
    """Detect magic / placeholder names.

    Protocol-method names (run, execute, handle, get, set, add, find, save,
    load, etc.) are legitimate when on a class but suspicious as standalone
    functions — `is_class_method` discriminates.

    Filename-disambiguation: if the function's name is a prefix of the
    filename stem, it's NOT magic (e.g., `def build()` in `build_pptx.py`
    is meaningfully named — the file says what's being built).
    """
    lower = name.lower()
    if lower in MAGIC_METHOD_PATTERNS:
        return True
    if lower in PROTOCOL_METHOD_NAMES and not is_class_method:
        # File-context disambiguation: if filename stem starts with the
        # function name + non-alpha boundary (e.g. `build_X`, `run-Y`),
        # the file says what's being run/built/etc. Not magic.
        if file_path:
            stem = Path(file_path).stem.lower()
            if stem == lower or re.match(rf"^{re.escape(lower)}[_\-.]", stem):
                return False
        return True
    # do_X / process_X with single-token suffix
    if re.match(r"^(do|process|handle)_[a-z]{1,3}$", lower):
        return True
    return False


def is_over_abbreviated(name: str) -> bool:
    """A name is over-abbreviated if it's ≤3 chars and not in the acceptable
    short-name list, OR if it's a vowel-stripped guess like 'prcs', 'mgr', 'cfg'.

    Real English words (run, get, add, set, new, ...) are NOT abbreviations even
    though they're short — they live in PROTOCOL_METHOD_NAMES.
    """
    lower = name.lower()
    if lower in ACCEPTABLE_SHORT_NAMES:
        return False
    if lower in PROTOCOL_METHOD_NAMES:
        return False  # real English verbs, not abbreviations
    if len(name) <= 3:
        return True
    # Vowel-stripped detection: ratio of consonants > 0.85 AND length 4-6
    if 4 <= len(name) <= 6:
        consonants = sum(1 for c in lower if c.isalpha() and c not in "aeiou")
        total_alpha = sum(1 for c in lower if c.isalpha())
        if total_alpha > 0 and consonants / total_alpha > 0.85:
            return True
    return False


def is_over_long(name: str) -> bool:
    return len(name) > 40


def jargon_density(text: str, vocab: set[str]) -> tuple[float, list[str]]:
    """Return (density, top-jargon-terms).

    Density = (unique unknown UPPERCASE-ish or abbreviated terms) / (unique identifiers).
    Lower-cased single English words and snake_case longer than 6 chars are NOT jargon.
    """
    identifiers = set()
    for match in re.finditer(r"\b[a-zA-Z_][a-zA-Z0-9_]{2,}\b", text):
        identifiers.add(match.group(0))
    if not identifiers:
        return 0.0, []

    jargon: set[str] = set()
    for ident in identifiers:
        lower = ident.lower()
        # Skip Python/JS keywords and common stdlib names
        if lower in {
            "self", "true", "false", "none", "null", "undefined",
            "return", "import", "from", "class", "def", "let", "const",
            "function", "this", "super", "static", "async", "await",
            "for", "while", "if", "else", "elif", "try", "except", "finally",
        }:
            continue
        # In vocab → not jargon
        if lower in vocab:
            continue
        # Short ALL-CAPS or mixedCAP abbreviations → jargon
        if re.match(r"^[A-Z][A-Z0-9_]+$", ident) and len(ident) <= 8:
            jargon.add(ident)
        # CamelCase abbreviations like WpxClient, GHClient → jargon
        elif re.match(r"^[A-Z][a-z]?[A-Z]", ident):
            jargon.add(ident)
        # snake_case starting with abbreviated prefix
        elif "_" in ident:
            first = ident.split("_")[0]
            if len(first) <= 3 and first not in ACCEPTABLE_SHORT_NAMES and first.isalpha():
                jargon.add(ident)

    density = len(jargon) / len(identifiers) if identifiers else 0.0
    top = sorted(jargon, key=lambda s: -text.count(s))[:5]
    return density, top


def count_concerns(text: str) -> int:
    """Heuristic concern count: number of distinct "areas" the file touches.

    Signals: imports from different top-level packages, distinct class clusters,
    section headers in comments. Imperfect but useful at scale.
    """
    concerns = set()
    # Distinct top-level imports
    for match in re.finditer(r"^(?:import|from)\s+(\w+)", text, re.MULTILINE):
        concerns.add(("import", match.group(1)))
    # Section-header comment lines (--- or === or ###)
    for match in re.finditer(r"^#\s*[─=#]{3,}\s*(\w[\w \-]*?)\s*[─=#]*$", text, re.MULTILINE):
        concerns.add(("section", match.group(1).strip().lower()))
    # Class clusters (each class is potentially a concern)
    for match in re.finditer(r"^class\s+(\w+)", text, re.MULTILINE):
        concerns.add(("class", match.group(1)))
    return len(concerns)


# ─── Main audit driver ──────────────────────────────────────────────


def audit_file(
    repo_root: Path,
    rel_path: str,
    vocab: set[str],
    kitchen_sink_loc: int,
    kitchen_sink_concerns: int,
    jargon_threshold: float,
) -> list[Finding]:
    """Run all three heuristic families on one file."""
    findings: list[Finding] = []
    path = repo_root / rel_path
    if not path.is_file():
        return findings
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return findings

    loc = len(text.splitlines())

    # ── Kitchen-sink heuristic ──
    concerns = count_concerns(text)
    if loc > kitchen_sink_loc and concerns > kitchen_sink_concerns:
        findings.append(Finding(
            heuristic="kitchen-sink-file",
            severity="concern" if loc > kitchen_sink_loc * 2 else "advisory",
            file=rel_path,
            line=0,
            identifier="",
            message=f"file is {loc} LOC covering {concerns} distinct concerns",
            suggestion="consider splitting into focused files",
            extras={"loc": loc, "concerns": concerns},
        ))

    # ── Jargon-density heuristic ──
    # Fixture files are intentionally noise — skip.
    if is_fixture_file(rel_path):
        density, top_terms = 0.0, []
    else:
        density, top_terms = jargon_density(text, vocab)
    if density > jargon_threshold:
        findings.append(Finding(
            heuristic="jargon-density",
            severity="advisory" if density < jargon_threshold * 1.5 else "concern",
            file=rel_path,
            line=0,
            identifier="",
            message=f"jargon density {density:.0%} (threshold {jargon_threshold:.0%}); top unknown terms: {', '.join(top_terms)}",
            suggestion="add a glossary or rename for self-explanation",
            extras={"density": round(density, 3), "top_terms": top_terms},
        ))

    # ── Naming-clarity heuristic (per identifier) ──
    # Fixture files contain code patterns for tests; naming quality is irrelevant.
    if is_fixture_file(rel_path):
        return findings
    test_file = is_test_file(rel_path)
    for lineno, kind, name, is_method in extract_identifiers(text, rel_path):
        # Skip dunder methods
        if name.startswith("__") and name.endswith("__"):
            continue
        # Skip private convention (underscore prefix says "internal")
        if name.startswith("_"):
            continue
        # Skip test_ functions from over-long check — descriptive test names
        # are GOOD practice, not a finding.
        if test_file and name.startswith("test_"):
            continue

        if is_magic_name(name, is_class_method=is_method, file_path=rel_path):
            findings.append(Finding(
                heuristic="naming-clarity",
                severity="advisory",
                file=rel_path,
                line=lineno,
                identifier=name,
                message=f"{kind} name `{name}` doesn't say what it does",
                suggestion=f"rename to a verb-noun pair (e.g., process_payment, validate_email)",
                extras={"reason": "magic-method-name", "kind": kind},
            ))
        elif is_over_abbreviated(name):
            findings.append(Finding(
                heuristic="naming-clarity",
                severity="advisory",
                file=rel_path,
                line=lineno,
                identifier=name,
                message=f"{kind} name `{name}` is too short to be clear",
                suggestion=f"expand the abbreviation (e.g., proc → process; mgr → manager)",
                extras={"reason": "over-abbreviated", "kind": kind},
            ))
        elif is_over_long(name):
            findings.append(Finding(
                heuristic="naming-clarity",
                severity="advisory",
                file=rel_path,
                line=lineno,
                identifier=name,
                message=f"{kind} name `{name}` is awkwardly long ({len(name)} chars)",
                suggestion="shorten while preserving meaning",
                extras={"reason": "over-long", "kind": kind, "length": len(name)},
            ))

    return findings


# ─── Output renderers ───────────────────────────────────────────────


def render_json(env: AuditEnvelope) -> str:
    not_assessed = sorted(
        prim for prim, status in env.primitive_status.items() if status == "NOT_ASSESSED"
    )
    return json.dumps({
        "scope": env.scope,
        "base_branch": env.base_branch,
        "pr_number": env.pr_number,
        "files_audited": env.files_audited,
        "findings": [asdict(f) for f in env.findings],
        "vocabulary_sources": env.vocabulary_sources,
        "thresholds": {
            "kitchen_sink_loc": env.kitchen_sink_threshold_loc,
            "kitchen_sink_concerns": env.kitchen_sink_threshold_concerns,
        },
        "errors": env.errors,
        "primitive_status": env.primitive_status,
        "not_assessed": not_assessed,
    }, indent=2)


def render_markdown(env: AuditEnvelope) -> str:
    out: list[str] = []
    scope_label = (
        f"PR #{env.pr_number}" if env.pr_number
        else f"current branch vs {env.base_branch}" if env.scope == "pr"
        else "whole codebase"
    )
    out.append(f"# Readability audit — {scope_label}")
    out.append("")
    out.append(f"Files audited: **{env.files_audited}**")
    out.append(f"Findings: **{len(env.findings)}**")
    out.append(f"Base branch used for diff: `{env.base_branch}`")
    out.append("")

    if not env.findings:
        out.append("_No legibility findings. The audit didn't find anything that would trip a stranger reader._")
        out.extend(_render_vocab_footer(env))
        return "\n".join(out)

    # Group by heuristic
    by_heuristic: dict[str, list[Finding]] = {}
    for f in env.findings:
        by_heuristic.setdefault(f.heuristic, []).append(f)

    severity_rank = {"high": 0, "concern": 1, "advisory": 2, "info": 3}

    for heuristic in ("naming-clarity", "kitchen-sink-file", "jargon-density"):
        items = by_heuristic.get(heuristic, [])
        if not items:
            continue
        items.sort(key=lambda f: (severity_rank.get(f.severity, 9), f.file, f.line))
        out.append(f"## {heuristic} ({len(items)})")
        out.append("")
        for f in items:
            location = f"{f.file}" + (f":{f.line}" if f.line else "")
            ident = f" `{f.identifier}`" if f.identifier else ""
            out.append(f"- [{f.severity}]{ident} — {f.message}")
            out.append(f"  - file: `{location}`")
            if f.suggestion:
                out.append(f"  - suggestion: {f.suggestion}")
        out.append("")

    out.extend(_render_vocab_footer(env))

    if env.errors:
        out.append("## Errors during audit")
        out.append("")
        for e in env.errors:
            out.append(f"- {e}")
    return "\n".join(out)


def _render_vocab_footer(env: AuditEnvelope) -> list[str]:
    out = []
    out.append("## Resolved vocabulary")
    out.append("")
    if env.vocabulary_sources:
        out.append("Terms in the following sources were treated as established (not jargon):")
        for s in env.vocabulary_sources:
            out.append(f"- `{s}`")
    else:
        out.append("_No project vocabulary sources found. Every unknown term was treated as potentially-jargon._")
    out.append("")
    out.append(
        f"Thresholds used: kitchen-sink-LOC={env.kitchen_sink_threshold_loc}, "
        f"kitchen-sink-concerns={env.kitchen_sink_threshold_concerns}"
    )
    return out


# ─── Main ────────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="Stranger-reader legibility audit.")
    parser.add_argument(
        "--scope",
        choices=("auto", "pr", "codebase"),
        default="auto",
        help="Audit scope. Default: auto-detect from git state.",
    )
    parser.add_argument(
        "--base-branch",
        default=None,
        help="Base branch for PR-scope diff. Default: auto-detect (main/master/trunk).",
    )
    parser.add_argument(
        "--pr-number",
        type=int,
        default=None,
        help="Audit a remote PR via gh CLI. Sets --scope=pr implicitly.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Output operator-grade JSON instead of founder-readable markdown.",
    )
    parser.add_argument(
        "--kitchen-sink-threshold",
        type=int,
        default=DEFAULT_KITCHEN_SINK_LOC,
        help=f"LOC threshold for kitchen-sink heuristic. Default: {DEFAULT_KITCHEN_SINK_LOC}",
    )
    parser.add_argument(
        "--kitchen-sink-concerns-threshold",
        type=int,
        default=DEFAULT_KITCHEN_SINK_CONCERNS,
        help=f"Concern-count threshold for kitchen-sink. Default: {DEFAULT_KITCHEN_SINK_CONCERNS}",
    )
    parser.add_argument(
        "--jargon-threshold",
        type=float,
        default=DEFAULT_JARGON_DENSITY_THRESHOLD,
        help=f"Jargon-density threshold (0.0-1.0). Default: {DEFAULT_JARGON_DENSITY_THRESHOLD}",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="Repo root (defaults to cwd).",
    )
    parser.add_argument(
        "--project",
        default=None,
        help="Project slug for the per-project allowlist (defaults to repo-root basename).",
    )
    # External tool integration
    parser.add_argument(
        "--skip-tools", action="store_true",
        help="skip lizard + jscpd integration; CQ-01 + CQ-03 will be NOT_ASSESSED",
    )
    parser.add_argument(
        "--tool-timeout", type=int, default=300,
        help="per-tool subprocess timeout in seconds",
    )
    args = parser.parse_args()
    if args.project is None:
        args.project = Path(args.repo_root).resolve().name

    repo_root = Path(args.repo_root).resolve()
    if not (repo_root / ".git").exists():
        print(f"error: {repo_root} is not a git repo", file=sys.stderr)
        return 2

    errors: list[str] = []
    base_branch = args.base_branch or detect_base_branch(repo_root)

    # Resolve scope + file list
    if args.pr_number is not None:
        scope = "pr"
        files, pr_errors = fetch_pr_files(args.pr_number, repo_root)
        errors.extend(pr_errors)
    elif args.scope == "pr":
        scope = "pr"
        _, files = detect_scope(repo_root, base_branch)
        if not files:
            print(f"warning: --scope=pr but no diff against {base_branch}; nothing to audit", file=sys.stderr)
    elif args.scope == "codebase":
        scope = "codebase"
        files = list_codebase_files(repo_root)
    else:  # auto
        scope, files = detect_scope(repo_root, base_branch)
        if scope == "codebase":
            files = list_codebase_files(repo_root)

    files = filter_source_files(files)
    if not files:
        print("warning: no source files in scope", file=sys.stderr)
        return 3

    # Load vocabulary
    vocab, sources = load_vocabulary(repo_root)

    # External tool integration (v0.20.0+): lizard CQ-01 + jscpd CQ-03
    primitive_status: dict[str, str] = {}
    tool_findings: list[Finding] = []
    if not args.skip_tools:
        tool_findings, primitive_status, tool_errors = _run_readability_tools(
            repo_root, timeout=args.tool_timeout
        )
        errors.extend(tool_errors)
    else:
        primitive_status["CQ-01"] = "NOT_ASSESSED"
        primitive_status["CQ-03"] = "NOT_ASSESSED"

    # Run heuristics on each file
    findings: list[Finding] = []
    findings.extend(tool_findings)
    for f in files:
        findings.extend(audit_file(
            repo_root, f, vocab,
            args.kitchen_sink_threshold,
            args.kitchen_sink_concerns_threshold,
            args.jargon_threshold,
        ))

    # Apply per-project allowlist. Signature shape:
    # `{heuristic}::{file}::{line}` — matches the convention used by
    # other check-* skills' allowlists.
    allowlist_path = (
        repo_root / ".checkup" / args.project / "check-readability-allowlist.md"
    )
    allow_signatures = _allowlist.load_allowlist(allowlist_path)
    if allow_signatures:
        pre = len(findings)
        findings = [
            f for f in findings
            if f"{f.heuristic}::{f.file}::{f.line}" not in allow_signatures
        ]
        allowlisted = pre - len(findings)
        if allowlisted:
            print(f"audit: allowlisted {allowlisted} finding(s)", file=sys.stderr)

    env = AuditEnvelope(
        scope=scope,
        base_branch=base_branch,
        pr_number=args.pr_number,
        files_audited=len(files),
        findings=findings,
        vocabulary_sources=sources,
        kitchen_sink_threshold_loc=args.kitchen_sink_threshold,
        kitchen_sink_threshold_concerns=args.kitchen_sink_concerns_threshold,
        errors=errors,
        primitive_status=primitive_status,
    )

    if args.raw:
        print(render_json(env))
    else:
        print(render_markdown(env))

    print(
        f"audit: scope={scope}, base={base_branch}, files={len(files)}, "
        f"findings={len(findings)}, vocab_sources={len(sources)}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
