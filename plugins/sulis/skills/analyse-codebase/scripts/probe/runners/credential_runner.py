"""
Phase 1.17 — Credential Scanning (repo-wide).

Invokes Yelp's detect-secrets to find hardcoded credentials. Privacy contract:
the runner stores only the SHA-1 hash that detect-secrets itself produces —
NEVER the plaintext value. Asserted by unit tests.

Graceful skip: if `detect-secrets` is not on PATH, the phase returns a
payload with `skipped=True` and a `skip_reason`. The probe never fails for
a missing optional tool.

Baseline awareness: if `.secrets.baseline` exists at the repo root (or the
caller-provided path), findings present in the baseline are categorised as
`known` rather than `new` — supporting the standard detect-secrets
acknowledged-finding workflow.
"""

from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ..config import (
    DETECT_SECRETS_BASELINE_NAME,
    DETECT_SECRETS_EXCLUDE_DIRS,
    DETECT_SECRETS_EXCLUDE_FILES,
    DETECT_SECRETS_EXCLUDE_LINES_RE,
    DETECT_SECRETS_DEFAULT_PLUGINS,
)
from ..models import (
    CredentialFinding,
    CredentialPayload,
    RepoInput,
    RunnerResult,
)
from .base import (
    ToolTimeoutError,
    make_result,
    now_iso,
    run_tool,
)


_TOOL = "detect-secrets"


def _is_tool_available() -> bool:
    return shutil.which(_TOOL) is not None


def _build_exclude_files_regex() -> str:
    """Regex matching files we never want to scan (lockfiles + skip-dirs).

    detect-secrets accepts a single regex via `--exclude-files`.
    """
    parts: list[str] = []
    for d in DETECT_SECRETS_EXCLUDE_DIRS:
        parts.append(rf"(?:^|/){d}(?:/|$)")
    for f in DETECT_SECRETS_EXCLUDE_FILES:
        parts.append(rf"(?:^|/){f}$")
    return "|".join(parts) if parts else r"^$"


def _load_baseline(baseline_path: Path) -> set[tuple[str, str]]:
    """Read a .secrets.baseline file and return a set of (file, hash) tuples.

    The baseline structure is the standard detect-secrets format:
        {"results": {"path/to/file": [{"hashed_secret": "...", ...}, ...]}}
    """
    try:
        data = json.loads(baseline_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    out: set[tuple[str, str]] = set()
    results = data.get("results", {})
    if not isinstance(results, dict):
        return out
    for path, findings in results.items():
        if not isinstance(findings, list):
            continue
        for f in findings:
            if isinstance(f, dict):
                h = f.get("hashed_secret")
                if isinstance(h, str):
                    out.add((path, h))
    return out


def _parse_scan_output(
    raw: str,
    baseline_hashes: set[tuple[str, str]],
) -> list[CredentialFinding]:
    """Parse `detect-secrets scan` JSON output into CredentialFinding list.

    detect-secrets emits a single JSON object on stdout with the same
    structure as a baseline file. The `secret` value is NEVER stored;
    only `hashed_secret`.
    """
    findings: list[CredentialFinding] = []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return findings
    results = data.get("results", {})
    if not isinstance(results, dict):
        return findings
    for path, entries in results.items():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if not isinstance(e, dict):
                continue
            hashed = e.get("hashed_secret") or ""
            findings.append(CredentialFinding(
                file=str(path),
                line=int(e.get("line_number", 0) or 0),
                secret_type=str(e.get("type", "unknown")),
                hashed_secret=str(hashed),
                is_verified=bool(e.get("is_verified", False)),
                is_known=(path, hashed) in baseline_hashes,
                plugin_name=str(e.get("type", "unknown")),
            ))
    return findings


# ─── Runner ────────────────────────────────────────────────────────────────


class CredentialRunner:
    PHASE: str = "1.17"
    TOOL: str = _TOOL

    def run_repo(
        self,
        inp: RepoInput,
        *,
        baseline_path_override: Path | None = None,
    ) -> RunnerResult:
        started_iso = now_iso()
        started_mono = time.monotonic()
        warnings: list[str] = []

        root = Path(inp.repo_root).resolve()

        # Tool availability — graceful skip.
        if not _is_tool_available():
            payload = CredentialPayload(
                findings=[],
                by_type={},
                new_findings=[],
                known_findings=[],
                baseline_present=False,
                baseline_path=None,
                scanned_files=0,
                skipped=True,
                skip_reason=(
                    "detect-secrets not on PATH. Install via "
                    "`pipx install detect-secrets` or run the bundled "
                    "install-probe-tools.sh."
                ),
            )
            return make_result(
                phase=self.PHASE,
                tool=self.TOOL,
                started_at=started_iso,
                started_monotonic=started_mono,
                payload=asdict(payload),
                warnings=warnings,
            )

        # Baseline lookup.
        baseline_path: Path | None = baseline_path_override
        if baseline_path is None:
            default = root / DETECT_SECRETS_BASELINE_NAME
            baseline_path = default if default.is_file() else None
        baseline_hashes: set[tuple[str, str]] = (
            _load_baseline(baseline_path) if baseline_path else set()
        )

        # Run detect-secrets. All built-in plugins are enabled by default;
        # `-p` is for *external* plugin files, not built-in detector names.
        #
        # We deliberately DO NOT pass `--baseline` here: detect-secrets'
        # `--baseline` mode filters known findings from its output, which
        # makes it impossible to distinguish "new" from "known" downstream.
        # Instead, we load the baseline ourselves and tag each finding's
        # `is_known` flag from `baseline_hashes`. This preserves both
        # categories in the payload for cross-reference reporting.
        cmd: list[str] = [_TOOL, "scan"]
        cmd.extend(["--exclude-files", _build_exclude_files_regex()])
        cmd.extend(["--exclude-lines", DETECT_SECRETS_EXCLUDE_LINES_RE])

        try:
            result = run_tool(
                cmd, cwd=root, tool=_TOOL, phase=self.PHASE,
            )
        except ToolTimeoutError:
            payload = CredentialPayload(
                findings=[],
                by_type={},
                new_findings=[],
                known_findings=[],
                baseline_present=baseline_path is not None,
                baseline_path=(
                    str(baseline_path.relative_to(root))
                    if baseline_path else None
                ),
                scanned_files=0,
                skipped=True,
                skip_reason="detect-secrets timed out",
            )
            return make_result(
                phase=self.PHASE, tool=self.TOOL,
                started_at=started_iso, started_monotonic=started_mono,
                payload=asdict(payload), warnings=warnings,
            )

        if result.returncode != 0 and not result.stdout.strip():
            warnings.append(
                f"detect-secrets exited {result.returncode}; stderr: "
                f"{result.stderr[:500]}"
            )
            payload = CredentialPayload(
                findings=[], by_type={},
                new_findings=[], known_findings=[],
                baseline_present=baseline_path is not None,
                baseline_path=(
                    str(baseline_path.relative_to(root))
                    if baseline_path else None
                ),
                scanned_files=0,
                skipped=True,
                skip_reason=(
                    f"detect-secrets returned exit {result.returncode}"
                ),
            )
            return make_result(
                phase=self.PHASE, tool=self.TOOL,
                started_at=started_iso, started_monotonic=started_mono,
                payload=asdict(payload), warnings=warnings,
            )

        findings = _parse_scan_output(result.stdout, baseline_hashes)
        new_findings = [f for f in findings if not f.is_known]
        known_findings = [f for f in findings if f.is_known]
        by_type: dict[str, int] = {}
        for f in findings:
            by_type[f.secret_type] = by_type.get(f.secret_type, 0) + 1

        # Count distinct files scanned (best-effort: distinct files in results
        # plus an unknown count of clean files. Use distinct findings files).
        scanned_files = len({f.file for f in findings})

        payload = CredentialPayload(
            findings=findings,
            by_type=dict(sorted(by_type.items())),
            new_findings=new_findings,
            known_findings=known_findings,
            baseline_present=baseline_path is not None,
            baseline_path=(
                str(baseline_path.relative_to(root))
                if baseline_path else None
            ),
            scanned_files=scanned_files,
            skipped=False,
            skip_reason=None,
        )

        return make_result(
            phase=self.PHASE,
            tool=self.TOOL,
            started_at=started_iso,
            started_monotonic=started_mono,
            payload=asdict(payload),
            warnings=warnings,
        )
