"""
Phase orchestrator — sequences runners per workspace, handles errors,
writes JSON files to disk, and assembles workspace manifests.

The orchestrator is intentionally dumb: it knows the phase order and the
error policy. Per-phase intelligence lives in the runners.
"""

from __future__ import annotations

import dataclasses
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from . import config as cfg_module
from .config import MANIFEST_FILE, PHASE_FILES, RAW_SUBDIR, SYSTEM_MANIFEST_FILE
from .detection import DetectionReport, detect_tools, format_report
from .models import (
    Manifest,
    RepoInput,
    RunnerInput,
    RunnerResult,
    SystemManifest,
    Workspace,
    write_json,
)
from .runners.base import Runner, RunnerError, now_iso
from .workspace import detect_and_enumerate


# ─── Orchestration config ─────────────────────────────────────────────────


@dataclass(frozen=True)
class OrchestratorConfig:
    root: Path
    project: str
    output_dir: Path                     # absolute, .architecture/{project}/probe-raw/
    languages: tuple[str, ...] = ()      # filter; empty = all
    run_tests: bool = False
    test_timeout_sec: int = 300
    git_lookback_days: int = 365
    workspace_filter: str | None = None  # only run this workspace by name
    skip_phases: frozenset[str] = frozenset()
    continue_on_error: bool = False
    extra_excludes: tuple[str, ...] = ()


@dataclass
class OrchestratorResult:
    project: str
    workspaces: list[Workspace]
    raw_dir: Path
    manifests: dict[str, Manifest]       # workspace name → manifest
    system_manifest: SystemManifest
    errors: list[str]                    # accumulated when continue_on_error=True


# ─── Phase registry ───────────────────────────────────────────────────────


def _build_runners() -> list[Runner]:
    """
    Construct all phase runners in execution order.

    Importing runners lazily so a partial install (e.g. missing a runner
    file during development) doesn't break the whole orchestrator. The
    minimal-slice (Stage 2) starts with just scc and astgrep_capability.
    """
    runners: list[Runner] = []

    try:
        from .runners.scc_runner import SccRunner
        runners.append(SccRunner())
    except ImportError:
        pass

    try:
        from .runners.astgrep_capability import AstGrepCapabilityRunner
        runners.append(AstGrepCapabilityRunner())
    except ImportError:
        pass

    # Stage 3 runners — added as they're implemented
    for module_path, class_name in [
        ("astgrep_extension", "AstGrepExtensionRunner"),
        ("reuse_runner", "ReuseRunner"),
        ("coupling_runner", "CouplingRunner"),
        ("lizard_runner", "LizardRunner"),
        ("wrapper_runner", "WrapperRunner"),
        ("convention_runner", "ConventionRunner"),
        ("test_runner", "TestRunner"),
        ("lint_runner", "LintRunner"),
        ("git_history_runner", "GitHistoryRunner"),
        ("duplication_runner", "DuplicationRunner"),
        ("deadcode_runner", "DeadCodeRunner"),
        ("architecture_runner", "ArchitectureRunner"),
        ("coverage_runner", "CoverageRunner"),
    ]:
        try:
            mod = __import__(f"probe.runners.{module_path}", fromlist=[class_name])
            cls = getattr(mod, class_name)
            runners.append(cls())
        except (ImportError, AttributeError):
            # Runner not yet implemented — skip silently in early stages.
            # The orchestrator will record this in manifest warnings.
            pass

    return runners


# ─── Per-workspace execution ──────────────────────────────────────────────


def _run_workspace(
    workspace: Workspace,
    cfg: OrchestratorConfig,
    detected_versions: dict[str, str],
) -> tuple[Manifest, list[str]]:
    """Run all phases for a single workspace. Returns (manifest, error-messages)."""
    workspace_dir = cfg.output_dir / workspace.name
    workspace_dir.mkdir(parents=True, exist_ok=True)

    runner_durations: dict[str, int] = {}
    runner_warnings: dict[str, list[str]] = {}
    errors: list[str] = []
    languages: tuple[str, ...] = cfg.languages   # may be updated after Phase 1.1

    started_at = now_iso()
    started_monotonic = time.monotonic()

    runners = _build_runners()
    if not runners:
        errors.append("No runners available — implementation incomplete.")

    for runner in runners:
        if runner.PHASE in cfg.skip_phases:
            continue

        inp = RunnerInput(
            workspace_path=workspace.path,
            workspace_name=workspace.name,
            languages=languages,
            extra_excludes=cfg.extra_excludes,
            output_dir=str(workspace_dir),
            run_tests=cfg.run_tests,
            git_lookback_days=cfg.git_lookback_days,
        )

        try:
            result = runner.run(inp)
        except RunnerError as exc:
            msg = f"[{exc.phase}/{exc.tool}] {exc.reason}"
            errors.append(msg)
            runner_warnings.setdefault(runner.PHASE, []).append(msg)
            if not cfg.continue_on_error:
                # Write a stub manifest and re-raise
                _write_manifest_stub(
                    workspace, cfg, started_at, runner_durations, runner_warnings,
                    detected_versions, workspace_dir,
                )
                raise
            continue
        except Exception as exc:
            msg = f"[{runner.PHASE}/{runner.TOOL}] unexpected error: {exc!r}"
            errors.append(msg)
            runner_warnings.setdefault(runner.PHASE, []).append(msg)
            if not cfg.continue_on_error:
                _write_manifest_stub(
                    workspace, cfg, started_at, runner_durations, runner_warnings,
                    detected_versions, workspace_dir,
                )
                raise
            continue

        # Persist per-phase JSON
        out_file = PHASE_FILES.get(result.phase)
        if out_file:
            write_json(
                {
                    "phase": result.phase,
                    "tool": result.tool,
                    "started_at": result.started_at,
                    "duration_ms": result.duration_ms,
                    "warnings": list(result.warnings),
                    "payload": result.payload,
                },
                workspace_dir / out_file,
            )

        runner_durations[result.phase] = result.duration_ms
        if result.warnings:
            runner_warnings.setdefault(result.phase, []).extend(result.warnings)

        # If Phase 1.1 succeeded, extract detected languages for downstream
        if result.phase == "1.1":
            stack = result.payload
            detected_langs = list((stack.get("languages") or {}).keys())
            if detected_langs and not cfg.languages:
                languages = tuple(_normalise_languages(detected_langs))

    manifest = Manifest(
        workspace=workspace,
        tool_versions=detected_versions,
        started_at=started_at,
        finished_at=now_iso(),
        runner_durations_ms=runner_durations,
        runner_warnings=runner_warnings,
        config_snapshot=_snapshot_config(),
    )
    write_json(manifest, workspace_dir / MANIFEST_FILE)
    return manifest, errors


def _write_manifest_stub(
    workspace: Workspace,
    cfg: OrchestratorConfig,
    started_at: str,
    runner_durations: dict[str, int],
    runner_warnings: dict[str, list[str]],
    detected_versions: dict[str, str],
    workspace_dir: Path,
) -> None:
    """Write a manifest even when a runner errored, so debugging is possible."""
    manifest = Manifest(
        workspace=workspace,
        tool_versions=detected_versions,
        started_at=started_at,
        finished_at=now_iso(),
        runner_durations_ms=runner_durations,
        runner_warnings=runner_warnings,
        config_snapshot=_snapshot_config(),
    )
    write_json(manifest, workspace_dir / MANIFEST_FILE)


def _normalise_languages(langs: list[str]) -> list[str]:
    """Map scc language names to our internal language codes."""
    mapping = {
        "TypeScript": "ts",
        "TSX": "tsx",
        "JavaScript": "javascript",
        "Python": "python",
        "Go": "go",
        "Rust": "rust",
        "Java": "java",
        "C#": "csharp",
        "Ruby": "ruby",
        "PHP": "php",
        "Swift": "swift",
        "Kotlin": "kotlin",
    }
    out: list[str] = []
    for lang in langs:
        code = mapping.get(lang)
        if code and code not in out:
            out.append(code)
    return out


def _snapshot_config() -> dict:
    """Snapshot key config values for reproducibility in the manifest."""
    return {
        "TOOL_VERSION_MIN": cfg_module.TOOL_VERSION_MIN,
        "HIGH_CCN_THRESHOLD": cfg_module.HIGH_CCN_THRESHOLD,
        "HIGH_CHURN_THRESHOLD": cfg_module.HIGH_CHURN_THRESHOLD,
        "LOW_COVERAGE_THRESHOLD_PCT": cfg_module.LOW_COVERAGE_THRESHOLD_PCT,
        "REUSE_CONSUMER_THRESHOLD": cfg_module.REUSE_CONSUMER_THRESHOLD,
        "ASTGREP_BASE_FLAGS": list(cfg_module.ASTGREP_BASE_FLAGS),
        "LIZARD_BASE_FLAGS": list(cfg_module.LIZARD_BASE_FLAGS),
        "LIZARD_EXCLUDE_GLOBS": list(cfg_module.LIZARD_EXCLUDE_GLOBS),
    }


# ─── Repo-wide phases (1.16, 1.17) ────────────────────────────────────────


def _run_repo_phases(
    repo_input: RepoInput,
    cfg: OrchestratorConfig,
    errors: list[str],
) -> None:
    """Run Phases 1.16 (deployment) and 1.17 (credentials) at repo level."""
    # Phase 1.16 — Deployment topology.
    if "1.16" not in cfg.skip_phases:
        try:
            from .runners.deployment_runner import DeploymentRunner
            result = DeploymentRunner().run_repo(repo_input)
            _persist_repo_phase(result, cfg)
        except Exception as exc:
            msg = f"[1.16/deployment-scan] unexpected error: {exc!r}"
            errors.append(msg)
            if not cfg.continue_on_error:
                raise

    # Phase 1.17 — Credential scanning.
    if "1.17" not in cfg.skip_phases:
        try:
            from .runners.credential_runner import CredentialRunner
            result = CredentialRunner().run_repo(repo_input)
            _persist_repo_phase(result, cfg)
        except Exception as exc:
            msg = f"[1.17/detect-secrets] unexpected error: {exc!r}"
            errors.append(msg)
            if not cfg.continue_on_error:
                raise


def _persist_repo_phase(result: RunnerResult, cfg: OrchestratorConfig) -> None:
    """Write a repo-wide phase JSON to probe-raw/ (not per-workspace)."""
    out_file = PHASE_FILES.get(result.phase)
    if not out_file:
        return
    write_json(
        {
            "phase": result.phase,
            "tool": result.tool,
            "started_at": result.started_at,
            "duration_ms": result.duration_ms,
            "warnings": list(result.warnings),
            "payload": result.payload,
        },
        cfg.output_dir / out_file,
    )


# ─── Public entry ─────────────────────────────────────────────────────────


def run(cfg: OrchestratorConfig) -> OrchestratorResult:
    """
    Execute the full probe: detect tools, enumerate workspaces, run each
    phase per workspace, write all JSON files + manifests.

    Raises RunnerError on first failure unless cfg.continue_on_error.
    """
    # Tool detection short-circuits
    report = detect_tools()
    if not report.all_required_present or report.failed_sanity:
        # Format and write a system-level error report; raise via stderr
        sys.stderr.write(format_report(report) + "\n")
        raise SystemExit(2)

    detected_versions = {s.name: (s.version or "unknown") for s in report.tools if s.available}

    # Enumerate workspaces
    workspaces = detect_and_enumerate(cfg.root)
    if cfg.workspace_filter:
        workspaces = [w for w in workspaces if w.name == cfg.workspace_filter]
        if not workspaces:
            sys.stderr.write(f"No workspace matches --workspace {cfg.workspace_filter}\n")
            raise SystemExit(4)

    if not workspaces:
        sys.stderr.write("No workspaces detected.\n")
        raise SystemExit(4)

    system_started = now_iso()
    cfg.output_dir.mkdir(parents=True, exist_ok=True)

    manifests: dict[str, Manifest] = {}
    all_errors: list[str] = []

    for workspace in workspaces:
        try:
            manifest, errors = _run_workspace(workspace, cfg, detected_versions)
        except RunnerError as exc:
            # Already wrote stub manifest in _run_workspace
            all_errors.append(str(exc))
            if not cfg.continue_on_error:
                raise
            continue
        manifests[workspace.name] = manifest
        all_errors.extend(errors)

    # ─── Repo-wide phases (1.16, 1.17) ──────────────────────────────────
    # Run once after per-workspace loop; output lands in probe-raw/, not
    # in a per-workspace subdir.
    repo_input = RepoInput(
        repo_root=str(cfg.root.resolve()),
        project=cfg.project,
        extra_excludes=cfg.extra_excludes,
        output_dir=str(cfg.output_dir),
        workspaces=tuple(workspaces),
    )
    _run_repo_phases(repo_input, cfg, all_errors)

    system_manifest = SystemManifest(
        project=cfg.project,
        workspaces=workspaces,
        started_at=system_started,
        finished_at=now_iso(),
        tool_versions=detected_versions,
    )
    write_json(system_manifest, cfg.output_dir / SYSTEM_MANIFEST_FILE)

    return OrchestratorResult(
        project=cfg.project,
        workspaces=workspaces,
        raw_dir=cfg.output_dir,
        manifests=manifests,
        system_manifest=system_manifest,
        errors=all_errors,
    )
