"""
Dataclass schemas for probe inputs, outputs, and all phase payloads.

Every dataclass round-trips losslessly through:
    dataclasses.asdict → json.dumps → json.loads → from_dict

All file paths in payloads are REPO-RELATIVE for portability across machines.
"""

from __future__ import annotations

import dataclasses
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ─── Workspace + runner core ──────────────────────────────────────────────


@dataclass(frozen=True)
class Workspace:
    """A single workspace within a (possibly mono-)repo."""
    name: str                    # logical name ("packages/api" or ".")
    path: str                    # absolute path
    style: str                   # "pnpm" | "lerna" | "nx" | "turborepo" |
                                 # "cargo" | "maven" | "gradle" | "bazel" |
                                 # "rush" | "go-workspaces" | "single-repo"
    manifest_path: str | None    # absolute path to manifest, or None


@dataclass(frozen=True)
class RunnerInput:
    """Input passed to every runner."""
    workspace_path: str          # absolute
    workspace_name: str
    languages: tuple[str, ...]   # populated after Phase 1.1
    extra_excludes: tuple[str, ...]
    output_dir: str              # absolute path to probe-raw/{workspace}/
    run_tests: bool              # only honoured by test_runner
    git_lookback_days: int       # only honoured by git_history_runner


@dataclass(frozen=True)
class RunnerResult:
    """Output from a single runner."""
    phase: str                   # "1.1", "1.2", etc.
    tool: str                    # "scc", "ast-grep", "lizard", ...
    started_at: str              # ISO 8601
    duration_ms: int
    payload: dict[str, Any]      # phase-specific (see schemas below)
    raw_output_path: str | None  # absolute path to captured stdout, if kept
    warnings: tuple[str, ...]    # non-fatal issues


@dataclass(frozen=True)
class RepoInput:
    """Input passed to repo-wide runners (Phases 1.16 / 1.17).

    Distinct from RunnerInput because these phases operate on the whole repo,
    not a single workspace. Output lands in probe-raw/ (not per-workspace).
    """
    repo_root: str               # absolute path to repo root
    project: str                 # project slug
    extra_excludes: tuple[str, ...]
    output_dir: str              # absolute path to probe-raw/ (root, not per-ws)
    workspaces: tuple[Workspace, ...] = ()  # for cross-referencing


# ─── Phase 1.1: scc — stack inference ─────────────────────────────────────


@dataclass
class LanguageStats:
    files: int
    code: int
    blanks: int
    comments: int
    complexity_total: int


@dataclass
class FrameworkHint:
    name: str
    source: str                  # which manifest file mentioned it
    confidence: str              # "high" | "medium" | "low"


@dataclass
class StackPayload:
    languages: dict[str, LanguageStats]   # language name → stats
    primary_language: str | None
    total_files: int
    total_loc: int
    total_complexity: int
    frameworks: list[FrameworkHint]
    manifest_files_found: list[str]       # repo-relative paths


# ─── Phase 1.2: ast-grep — capability inventory ───────────────────────────


@dataclass
class Capability:
    kind: str                    # "class" | "function" | "interface" | ...
    name: str
    file: str                    # repo-relative
    line: int
    language: str
    signature: str | None        # raw matched span when captured
    visibility: str              # "exported" | "default" | "internal" (heuristic)


@dataclass
class CapabilityPayload:
    items: list[Capability]
    by_language: dict[str, int]
    by_kind: dict[str, int]


# ─── Phase 1.3: ast-grep — extension points ───────────────────────────────


@dataclass
class ExtensionPoint:
    kind: str                    # "abstract-class" | "interface" |
                                 # "registry" | "factory" | "di-marker" | "hook"
    name: str
    file: str
    line: int
    language: str
    contract: str | None         # abstract methods / interface members
    implementations: list[str]   # cross-referenced from capability inventory


@dataclass
class ExtensionPayload:
    items: list[ExtensionPoint]
    by_kind: dict[str, int]


# ─── Phase 1.4: reuse — consumer counts ───────────────────────────────────


@dataclass
class ReusableModule:
    module_path: str             # repo-relative
    language: str
    consumers: list[str]
    consumer_count: int
    is_kitchen_sink: bool        # heuristic


@dataclass
class ReusePayload:
    modules: list[ReusableModule]
    top_by_consumer_count: list[str]


# ─── Phase 1.5: coupling — fan-in/fan-out + cycles ────────────────────────


@dataclass
class ModuleCoupling:
    module: str
    fan_in: int
    fan_out: int
    imports_out: list[str]
    imports_in: list[str]


@dataclass
class CouplingPayload:
    modules: list[ModuleCoupling]
    cycles: list[list[str]]              # each cycle is a sequence of module paths
    high_fanin: list[str]                # > HIGH_FANIN threshold
    high_fanout: list[str]               # > HIGH_FANOUT threshold


# ─── Phase 1.6: lizard — complexity hotspots ──────────────────────────────


@dataclass
class ComplexFunction:
    file: str
    function: str
    line_start: int
    line_end: int
    ccn: int
    nloc: int
    tokens: int
    params: int


@dataclass
class FragileFile:
    file: str
    avg_ccn: float
    function_count: int


@dataclass
class ComplexityPayload:
    functions: list[ComplexFunction]     # only CCN > threshold
    fragile_files: list[FragileFile]     # avg CCN > MODULE_FRAGILITY_CCN
    threshold_ccn: int
    threshold_file_avg: int


# ─── Phase 1.7: wrapper-rot candidates ────────────────────────────────────


@dataclass
class WrapperCandidate:
    wrapper_class: str
    wrapper_file: str
    wrapper_line: int
    wrapped_target: str | None           # class name held by the wrapper
    wrapped_file: str | None
    suffix_match: str                    # which suffix triggered detection
    is_external_adapter_candidate: bool  # heuristic: wrapped target is in node_modules / @package


@dataclass
class WrappersPayload:
    candidates: list[WrapperCandidate]
    count_internal: int
    count_external_likely: int


# ─── Phase 1.8: conventions ───────────────────────────────────────────────


@dataclass
class NamingObservation:
    pattern: str                         # "PascalCase.ts" | "snake_case.py" | etc.
    confidence: float                    # 0..1
    samples: list[str]                   # representative file paths


@dataclass
class ConventionsPayload:
    file_naming: NamingObservation | None
    test_naming: NamingObservation | None
    module_layout: str                   # "per-feature" | "layered" | "mixed" | "flat"
    error_handling: str                  # "exceptions" | "result-types" | "error-returns" | "mixed"
    naming_for_roles: dict[str, str]     # {"repository": "*Repository", ...}


# ─── Phase 1.9: tests ─────────────────────────────────────────────────────


@dataclass
class TestPayload:
    framework: str                       # "pytest" | "vitest" | ... | "none-detected"
    test_files: int
    tests_enumerated: int
    executed: bool                       # only True if --run-tests
    passed: int | None
    failed: int | None
    skipped: int | None
    duration_sec: float | None
    coverage_tool_detected: str | None
    coverage_pct_overall: float | None
    coverage_pct_by_file: dict[str, float]


# ─── Phase 1.10: lints ────────────────────────────────────────────────────


@dataclass
class LintPayload:
    linters_configured: list[str]
    warnings_by_file: dict[str, int]
    errors_by_file: dict[str, int]
    typecheck_errors: int
    rule_violations: dict[str, int]      # top-10 rule-id → count


# ─── Phase 1.11: git history ──────────────────────────────────────────────


@dataclass
class FileChurn:
    file: str
    commits_in_lookback: int
    age_days: int
    distinct_authors: int
    last_commit_iso: str


@dataclass
class CoChangePair:
    file_a: str
    file_b: str
    pair_count: int


@dataclass
class HistoryPayload:
    lookback_days: int
    file_churn: list[FileChurn]
    high_churn_files: list[str]
    bus_factor_one: list[str]
    co_change_pairs: list[CoChangePair]
    repo_first_commit_iso: str | None
    repo_last_commit_iso: str | None


# ─── Phase 1.12: duplication ──────────────────────────────────────────────


@dataclass
class BlockInstance:
    file: str
    line_start: int
    line_end: int


@dataclass
class DuplicateBlock:
    instances: list[BlockInstance]
    tokens: int
    lines: int


@dataclass
class DuplicationPayload:
    blocks: list[DuplicateBlock]
    duplicated_lines: int
    duplicated_pct: float
    threshold_min_lines: int
    threshold_min_tokens: int


# ─── Phase 1.13: dead code ────────────────────────────────────────────────


@dataclass
class DeadSymbol:
    file: str
    line: int
    name: str
    kind: str                            # "export" | "function" | "class" | "variable"
    confidence: str                      # "high" | "medium" | "low"
    tool: str                            # "ts-prune" | "vulture" | "deadcode"


@dataclass
class DeadCodePayload:
    symbols: list[DeadSymbol]
    by_language: dict[str, int]
    by_tool: dict[str, int]


# ─── Phase 1.14: architecture rules ───────────────────────────────────────


@dataclass
class ArchViolation:
    rule_id: str
    source: str                          # importing module
    target: str                          # imported module
    file: str
    line: int
    severity: str                        # "error" | "warn"


@dataclass
class ArchitecturePayload:
    rules_config: str | None             # path to the config, or None if no config found
    violations: list[ArchViolation]
    rules_passed: int
    rules_failed: int


# ─── Phase 1.15: coverage ─────────────────────────────────────────────────


@dataclass
class CoveragePayload:
    overall_pct: float | None
    by_file: dict[str, float]
    low_coverage_files: list[str]
    source: str                          # "vitest" | "jest" | "coverage.py" | "go-cover"


# ─── Phase 1.16: deployment topology (repo-wide) ──────────────────────────


@dataclass
class DeploymentArtifact:
    """A single deployment-related file or directory.

    `extras` is a free-form dict for kind-specific fields (image, port,
    workload_type, etc.). `secret_references` captures secret NAMES only —
    never values.
    """
    kind: str                            # "dockerfile" | "docker-compose" |
                                         # "k8s-manifest" | "sulis-manifest" | ...
    sub_kind: str | None                 # for kind="k8s-manifest" → "Deployment"|"Service"|...
                                         # for kind="sulis-manifest" → "Workload"|"Application"|...
    name: str | None                     # metadata.name / image name / etc.
    path: str                            # repo-relative
    line: int | None                     # for multi-doc YAML, where the doc starts
    environment: str | None              # "dev"|"staging"|"prod"|"qa"|None
    target_platform: str | None          # "kubernetes" | "ecs" | "lambda" | ...
    secret_references: list[str]         # NAMES only — values never captured
    extras: dict[str, Any]               # kind-specific structured fields


@dataclass
class SulisWorkloadExtras:
    """Structured extras for kind=sulis-manifest, sub_kind=Workload."""
    image: str | None
    port: int | None
    replicas: int | None
    memory: str | None
    cpu: str | None
    health_check_path: str | None
    env_var_names: list[str]             # NAMES only


@dataclass
class DeploymentPayload:
    artifacts: list[DeploymentArtifact]
    by_kind: dict[str, int]              # "dockerfile" → 9, ...
    by_environment: dict[str, int]       # "prod" → 3, ...
    sulis_kinds_present: list[str]       # ["Workload", "Application", ...]
    target_platforms: list[str]
    files_scanned: int
    files_skipped_cap: int               # how many were skipped by MAX_FILES cap
    yaml_parser: str                     # "pyyaml" | "regex-fallback"


# ─── Phase 1.17: credential scanning (repo-wide, detect-secrets) ──────────


@dataclass
class CredentialFinding:
    """A single hardcoded-credential candidate.

    PRIVACY CONTRACT (MUST): `hashed_secret` is the SHA-1 hash produced by
    detect-secrets — never the plaintext value. Probe does not store secret
    values in any output (JSON, Markdown, HTML). Asserted by unit test
    `test_credential_finding_never_contains_value`.
    """
    file: str                            # repo-relative
    line: int
    secret_type: str                     # "AWS Access Key" | "Private Key" | ...
    hashed_secret: str                   # SHA-1 hash — NEVER the value
    is_verified: bool                    # detect-secrets verification status
    is_known: bool                       # in .secrets.baseline = previously triaged
    plugin_name: str                     # which detect-secrets plugin flagged it


@dataclass
class CredentialPayload:
    findings: list[CredentialFinding]
    by_type: dict[str, int]
    new_findings: list[CredentialFinding]    # not in baseline
    known_findings: list[CredentialFinding]  # in baseline
    baseline_present: bool
    baseline_path: str | None                # repo-relative, if found
    scanned_files: int
    skipped: bool                            # True if detect-secrets unavailable
    skip_reason: str | None


# ─── Per-workspace manifest ───────────────────────────────────────────────


@dataclass
class Manifest:
    workspace: Workspace
    tool_versions: dict[str, str]
    started_at: str
    finished_at: str
    runner_durations_ms: dict[str, int]
    runner_warnings: dict[str, list[str]]
    config_snapshot: dict[str, Any]      # selected config.py values for reproducibility


# ─── System manifest (for monorepos) ──────────────────────────────────────


@dataclass
class SystemManifest:
    project: str
    workspaces: list[Workspace]
    started_at: str
    finished_at: str
    tool_versions: dict[str, str]


# ─── LLM-authored synthesis payload ───────────────────────────────────────


@dataclass
class PatternFinding:
    pattern: str                         # e.g. "Ports & Adapters"
    confidence: str                      # "high" | "medium" | "low"
    evidence: list[str]                  # citing file paths / phase JSONs


@dataclass
class TriageItem:
    candidate: WrapperCandidate
    classification: str                  # "wrapper-rot" | "legitimate-adapter" |
                                         # "in-progress-strangle" | "branch-by-abstraction"
    recommendation: str                  # plain text


@dataclass
class Recommendation:
    priority: int                        # 1 = highest
    primitive: str                       # e.g. "REORGANISE-Decompose"
    target: str                          # file / symbol path
    evidence_phases: list[str]           # ["1.6", "1.11", "1.15"]
    rationale: str                       # plain text
    confidence: str                      # "high" | "medium" | "low"


@dataclass
class SynthesisPayload:
    summary: str
    pattern_recognition: list[PatternFinding]
    wrapper_rot_triage: list[TriageItem]
    recommendations: list[Recommendation]
    generated_at: str
    generated_by: str                    # "llm" | "manual" | "draft"


# ─── JSON serialisation helpers ───────────────────────────────────────────


class _DataclassJSONEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
            return dataclasses.asdict(obj)
        if isinstance(obj, Path):
            return str(obj)
        if isinstance(obj, tuple):
            return list(obj)
        return super().default(obj)


def to_json(obj: Any, *, indent: int = 2) -> str:
    """Serialise a dataclass (or any JSON-compatible object) to pretty JSON."""
    return json.dumps(obj, cls=_DataclassJSONEncoder, indent=indent, ensure_ascii=False)


def write_json(obj: Any, path: Path) -> None:
    """Serialise + write to a file, ensuring parent dirs exist."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(to_json(obj), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    """Read + parse a JSON file. Returns the raw dict."""
    return json.loads(path.read_text(encoding="utf-8"))
