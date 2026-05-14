"""
Single source of truth for /sea:probe tool flags, exclusions, version pins,
and per-language patterns.

Every bug fix from v0.7.0 → v0.7.2 lives here. If a downstream behaviour
changes, this is the file to inspect first.

Bug-fix lineage:
  v0.7.1 (Bug 1): macOS lizard install path → use pipx, not brew. See
                  LIZARD_HELP_MARKER below.
  v0.7.1 (Bug 2): ast-grep over-specific patterns miss return-type variants.
                  See ASTGREP_CAPABILITY_PATTERNS — TS uses partial patterns.
  v0.7.1 (Bug 3): lizard `-E sloc -E maxcc` flags don't exist. See
                  LIZARD_BASE_FLAGS — only --CCN and -L.
  v0.7.2 (Bug 4): ast-grep default ignore rules skip dotfile-prefixed dirs.
                  See ASTGREP_BASE_FLAGS — always pass --no-ignore hidden
                  --no-ignore dot.
  v0.7.2 (Bug 5): Python `class $NAME:` and `def $NAME($$$):` patterns
                  produce ERROR nodes. See ASTGREP_CAPABILITY_PATTERNS —
                  Python uses BARE keywords.
  v0.7.2 (Bug 6): lizard walks .venv and site-packages by default. See
                  LIZARD_EXCLUDE_GLOBS — explicit exclusion globs required.
"""

from __future__ import annotations

# ─── Tool versions ────────────────────────────────────────────────────────

# Minimum (major, minor) required for each tool. Verified by detection.py
# parsing the tool's --version output.
TOOL_VERSION_MIN: dict[str, tuple[int, int]] = {
    "ast-grep": (0, 30),
    "lizard": (1, 17),
    "scc": (3, 1),
    "git": (2, 25),
}

TOOL_REQUIRED: tuple[str, ...] = ("ast-grep", "lizard", "scc", "git")

# Optional tools — graceful skip with manifest warning if missing.
TOOL_OPTIONAL: tuple[str, ...] = (
    "repomix",
    "jscpd",
    "ts-prune",
    "vulture",
    "deadcode",          # Go: golang.org/x/tools/cmd/deadcode
    "dependency-cruiser",
    "lint-imports",      # Python: import-linter CLI name
    "pytest",
    "npx",               # vitest, jest, eslint
    "ruff",
    "mypy",
    "golangci-lint",
    "go",
    "cargo",
)

# Lizard sanity check: must be Terry Yin's McCabe analyser, not the
# compression utility of the same name from brew. The detection.py post-
# install check greps this marker in `lizard --help` output.
LIZARD_HELP_MARKER: str = "Cyclomatic Complexity Analyzer"

# Per-tool subprocess timeout (seconds). Long enough for large codebases.
TOOL_TIMEOUTS_SEC: dict[str, int] = {
    "ast-grep": 120,
    "lizard": 180,
    "scc": 60,
    "git": 60,
    "jscpd": 180,
    "ts-prune": 120,
    "vulture": 120,
    "deadcode": 120,
    "dependency-cruiser": 180,
    "lint-imports": 120,
    "pytest": 300,
    "npx": 300,
    "ruff": 60,
    "mypy": 180,
    "golangci-lint": 180,
}

# Truncate runaway stdout to keep memory bounded.
SUBPROCESS_MAX_OUTPUT_BYTES: int = 50 * 1024 * 1024  # 50 MiB

# ─── ast-grep ─────────────────────────────────────────────────────────────

# Mandatory flags — apply on EVERY ast-grep invocation. See v0.7.2 Bug 4.
#
# --no-ignore hidden: include hidden files (e.g. .eslintrc.json)
# --no-ignore dot:    enter dotfile-prefixed dirs (.claude/, .config/, etc.)
# (We deliberately KEEP --no-ignore vcs OFF — .gitignore should still
#  exclude .venv, node_modules, etc.)
ASTGREP_BASE_FLAGS: tuple[str, ...] = (
    "run",
    "--no-ignore", "hidden",
    "--no-ignore", "dot",
    "--json=stream",
)

# Per-language capability patterns. List of (kind, pattern) tuples.
#
# IMPORTANT — Python uses BARE keywords (no $NAME, no body). v0.7.2 Bug 5:
# `class $NAME:` and `def $NAME($$$):` produce ERROR nodes because Python's
# AST requires a body block. The bare-keyword partial pattern matches all
# class/def variants reliably.
#
# IMPORTANT — TS/Go/Rust use partial patterns without function body.
# v0.7.1 Bug 2: over-specific patterns like `function $NAME($$$) { $$$ }`
# don't match functions with return-type annotations.
ASTGREP_CAPABILITY_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "ts": [
        ("class", "class $NAME"),
        ("function", "function $NAME"),
        ("interface", "interface $NAME"),
        ("type-alias", "type $NAME"),
    ],
    "tsx": [
        ("class", "class $NAME"),
        ("function", "function $NAME"),
        ("interface", "interface $NAME"),
        ("type-alias", "type $NAME"),
    ],
    "javascript": [
        ("class", "class $NAME"),
        ("function", "function $NAME"),
    ],
    "python": [
        # BARE keywords — see Bug 5 note above
        ("class", "class"),
        ("function", "def"),
    ],
    "go": [
        ("type", "type $NAME"),
        ("function", "func $NAME"),
    ],
    "rust": [
        ("struct", "struct $NAME"),
        ("enum", "enum $NAME"),
        ("trait", "trait $NAME"),
        ("function", "fn $NAME"),
    ],
    "java": [
        ("class", "class $NAME"),
        ("interface", "interface $NAME"),
    ],
}

# Extension-point patterns: abstracts, interfaces, factories, registries,
# DI markers, hooks. Sparser than capability patterns — we want strong
# signal, not noise.
ASTGREP_EXTENSION_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "ts": [
        ("abstract-class", "abstract class $NAME"),
    ],
    "python": [
        # Abstract classes detected via ABC / ABCMeta inheritance (heuristic
        # in runner). Bare keyword scan handled by capability runner.
    ],
    "java": [
        ("abstract-class", "abstract class $NAME"),
    ],
}

# Wrapper-rot heuristic: class names containing these suffixes are
# candidates for further inspection (does the wrapper hold a reference
# to an internal class with a similar name minus the suffix?).
ASTGREP_WRAPPER_SUFFIXES: tuple[str, ...] = (
    "V2", "V3", "V4",
    "Facade", "Wrapper", "Proxy", "Compat",
    "New", "Old", "Legacy",
    # Note: NOT "Adapter" — that would catch legitimate hexagonal-
    # architecture adapters for ports. The wrapper_runner uses other
    # heuristics for Adapter-class triage (delegating-call patterns).
)

# ─── lizard ───────────────────────────────────────────────────────────────

# Base flags. v0.7.1 Bug 3: -E was for plugins not formats.
# --CCN: complexity warning threshold
# -L:    max function length warning threshold
# -w:    warnings-only output
LIZARD_BASE_FLAGS: tuple[str, ...] = (
    "--CCN", "15",
    "-L", "80",
    "-w",
)

# v0.7.2 Bug 6: lizard walks all subdirs by default; explicit excludes
# required or hotspot list is polluted with third-party code.
LIZARD_EXCLUDE_GLOBS: tuple[str, ...] = (
    "*.venv*",
    "*venv*",
    "*site-packages*",
    "*node_modules*",
    "*vendor*",
    "*dist*",
    "*build*",
    "*.next*",
    "*__pycache__*",
    "*target*",          # Rust/Java
    "*.git*",
    "*coverage*",
    "*.turbo*",
    "*.nx*",
)

# Map ast-grep language name → lizard `-l` value. Lizard accepts these
# language names per its --help.
LIZARD_LANG_MAP: dict[str, str] = {
    "ts": "typescript",
    "tsx": "tsx",
    "javascript": "javascript",
    "python": "python",
    "go": "go",
    "rust": "rust",
    "java": "java",
    "csharp": "csharp",
    "ruby": "ruby",
    "php": "php",
    "swift": "swift",
    "kotlin": "kotlin",
}

# ─── scc ──────────────────────────────────────────────────────────────────

SCC_BASE_FLAGS: tuple[str, ...] = (
    "--format", "json",
    "--no-cocomo",
)

SCC_EXCLUDE_DIRS: tuple[str, ...] = (
    "node_modules", ".next", "dist", "build", ".git", ".vercel",
    ".venv", "venv", "site-packages", "__pycache__",
    "target", "vendor", "third_party", "coverage",
    ".turbo", ".nx", ".cache",
)

# ─── Filesystem walk ──────────────────────────────────────────────────────

DEFAULT_MAX_DEPTH: int = 8

# Extra directories the orchestrator always excludes from its own walks
# (in addition to .gitignore via `git check-ignore`).
EXTRA_EXCLUDE_DIRS: tuple[str, ...] = (
    ".venv", "venv", "node_modules", "__pycache__",
    "dist", "build", ".next", "target", "vendor", "third_party",
    "coverage", ".turbo", ".nx", ".cache", ".pytest_cache",
    ".mypy_cache", ".ruff_cache", ".tox",
)

# ─── Monorepo detection ───────────────────────────────────────────────────

# (manifest filename, style) — order matters: first match wins per dir.
MONOREPO_MANIFESTS: tuple[tuple[str, str], ...] = (
    ("pnpm-workspace.yaml", "pnpm"),
    ("pnpm-workspace.yml", "pnpm"),
    ("lerna.json", "lerna"),
    ("nx.json", "nx"),
    ("turbo.json", "turborepo"),
    ("rush.json", "rush"),
    ("Cargo.toml", "cargo"),            # parsed for [workspace]
    ("pom.xml", "maven"),               # parsed for <modules>
    ("settings.gradle", "gradle"),
    ("settings.gradle.kts", "gradle"),
    ("WORKSPACE", "bazel"),
    ("WORKSPACE.bazel", "bazel"),
    ("MODULE.bazel", "bazel"),
    ("go.work", "go-workspaces"),
)

# Files marking a leaf project (when no monorepo manifest).
WORKSPACE_PROJECT_MANIFESTS: tuple[str, ...] = (
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "setup.py",
    "Gemfile",
    "composer.json",
)

# ─── Test framework signals (Phase 1.9) ───────────────────────────────────

TEST_FRAMEWORK_SIGNALS: dict[str, dict[str, list[str]]] = {
    "pytest": {
        "manifests": ["pytest.ini", "pyproject.toml"],
        "binary": ["pytest"],
        "list_args": ["--collect-only", "-q", "--no-header"],
        "run_args": ["-v", "--tb=short"],
    },
    "vitest": {
        "manifests": ["vitest.config.ts", "vitest.config.js", "vitest.config.mjs"],
        "binary": ["npx", "vitest"],
        "list_args": ["list", "--reporter=json"],
        "run_args": ["run", "--reporter=json"],
    },
    "jest": {
        "manifests": ["jest.config.js", "jest.config.ts", "jest.config.json"],
        "binary": ["npx", "jest"],
        "list_args": ["--listTests"],
        "run_args": ["--json"],
    },
    "go-test": {
        "manifests": ["go.mod"],
        "binary": ["go"],
        "list_args": ["test", "-list", ".*", "./..."],
        "run_args": ["test", "-json", "./..."],
    },
    "cargo-test": {
        "manifests": ["Cargo.toml"],
        "binary": ["cargo"],
        "list_args": ["test", "--", "--list"],
        "run_args": ["test", "--", "--format=json"],
    },
}

# Coverage tool signals — detection only, not execution.
COVERAGE_SIGNALS: dict[str, dict[str, list[str]]] = {
    "vitest-coverage": {
        "manifest_hints": ["vitest.config.ts"],
        "package_json_scripts": ["test:cov", "coverage"],
    },
    "jest-coverage": {
        "manifest_hints": ["jest.config.js"],
        "package_json_scripts": ["test:cov", "coverage"],
    },
    "coverage.py": {
        "manifests": [".coveragerc", "pyproject.toml"],
    },
    "go-cover": {
        "manifests": ["go.mod"],
    },
}

# ─── Linter signals (Phase 1.10) ──────────────────────────────────────────

LINTER_SIGNALS: dict[str, dict[str, list[str]]] = {
    "eslint": {
        "manifests": [".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yaml",
                      ".eslintrc.yml", "eslint.config.js", "eslint.config.mjs"],
        "binary": ["npx", "eslint"],
        "check_args": ["--format", "json", "--no-error-on-unmatched-pattern", "."],
    },
    "ruff": {
        "manifests": ["ruff.toml", ".ruff.toml", "pyproject.toml"],
        "binary": ["ruff"],
        "check_args": ["check", "--output-format=json", "."],
    },
    "mypy": {
        "manifests": ["mypy.ini", ".mypy.ini", "pyproject.toml"],
        "binary": ["mypy"],
        "check_args": ["--no-incremental", "--show-error-codes",
                       "--no-error-summary", "."],
    },
    "clippy": {
        "manifests": ["Cargo.toml"],
        "binary": ["cargo"],
        "check_args": ["clippy", "--message-format=json", "--", "-D", "warnings"],
    },
    "golangci-lint": {
        "manifests": [".golangci.yml", ".golangci.yaml"],
        "binary": ["golangci-lint"],
        "check_args": ["run", "--out-format", "json"],
    },
}

# ─── Git history config (Phase 1.11) ──────────────────────────────────────

GIT_HISTORY_LOOKBACK_DAYS_DEFAULT: int = 365
GIT_CHURN_HIGH_THRESHOLD: int = 20            # commits in lookback window
GIT_BUS_FACTOR_LOW: int = 1                   # single-author = concentration risk
GIT_COCHANGE_MIN_PAIRS: int = 5               # files co-changing N+ times

# ─── Duplication config (Phase 1.12) ──────────────────────────────────────

JSCPD_MIN_TOKENS: int = 50
JSCPD_MIN_LINES: int = 5
DUPLICATION_HIGH_THRESHOLD_PCT: float = 5.0

# ─── Dead code config (Phase 1.13) ────────────────────────────────────────

DEADCODE_TOOLS_BY_LANG: dict[str, list[str]] = {
    "ts": ["ts-prune"],
    "tsx": ["ts-prune"],
    "javascript": ["ts-prune"],
    "python": ["vulture"],
    "go": ["deadcode"],
}

VULTURE_MIN_CONFIDENCE: int = 60      # default vulture threshold

# ─── Architecture-rules config (Phase 1.14) ───────────────────────────────

ARCH_RULE_CONFIGS_BY_LANG: dict[str, list[str]] = {
    "ts": [".dependency-cruiser.cjs", ".dependency-cruiser.js",
           ".dependency-cruiser.json", "dependency-cruiser.config.js"],
    "tsx": [".dependency-cruiser.cjs"],
    "javascript": [".dependency-cruiser.cjs"],
    "python": [".importlinter", "pyproject.toml"],   # importlinter section in pyproject
}

# ─── Cross-reference thresholds (Phase 2 LLM synthesis) ───────────────────

HIGH_CCN_THRESHOLD: int = 15
MODULE_FRAGILITY_CCN: int = 10
HIGH_FANIN: int = 10
HIGH_FANOUT: int = 15
REUSE_CONSUMER_THRESHOLD: int = 3
HIGH_LINT_WARNINGS_PER_FILE: int = 20
LOW_COVERAGE_THRESHOLD_PCT: float = 50.0
HIGH_CHURN_THRESHOLD: int = 20

# ─── Stable JSON file names ───────────────────────────────────────────────

# Downstream consumers (blueprint, decompose, harden, verify, future tools)
# depend on these exact filenames. Don't rename without a major version
# bump.
PHASE_FILES: dict[str, str] = {
    "1.1": "1_1_stack.json",
    "1.2": "1_2_capabilities.json",
    "1.3": "1_3_extensions.json",
    "1.4": "1_4_reuse.json",
    "1.5": "1_5_coupling.json",
    "1.6": "1_6_complexity.json",
    "1.7": "1_7_wrappers.json",
    "1.8": "1_8_conventions.json",
    "1.9": "1_9_tests.json",
    "1.10": "1_10_lints.json",
    "1.11": "1_11_history.json",
    "1.12": "1_12_duplication.json",
    "1.13": "1_13_deadcode.json",
    "1.14": "1_14_architecture.json",
    "1.15": "1_15_coverage.json",
}

MANIFEST_FILE: str = "00_manifest.json"
SYSTEM_MANIFEST_FILE: str = "00_system_manifest.json"
SYNTHESIS_FILE: str = "synthesis.json"

# Output filenames in .architecture/{project}/
FINAL_MARKDOWN: str = "CODE_INTELLIGENCE.md"
FINAL_HTML: str = "CODE_INTELLIGENCE.html"
RAW_SUBDIR: str = "probe-raw"
