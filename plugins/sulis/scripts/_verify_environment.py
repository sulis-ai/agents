"""Production-like environment harness — stand up a clean repo + drive the
full emit-and-verify pipeline + report the resulting brain graph state.

What this is FOR (the user story):

  Before the DoD gate (Phase C) can be trusted to block ships on
  unverified Requirements, we need to prove the whole pipeline works
  end-to-end in conditions that look like production:

    1. A fresh repo (no leftover .brain/ state)
    2. The marketplace surface present (scripts + schemas) as a
       downstream consumer would receive it
    3. A realistic SRD with FR/NFR blocks
    4. Tests that claim Requirements via `@pytest.mark.verifies`
    5. Pytest runs the brain-emit plugin, producing TestRun + TestResults
    6. A brain-query confirms the graph self-connects:
       TestResult.verifies → Requirement.id

  This module is the automation pass that exercises all of that, end
  to end, with structured output. CI can call it directly; the founder
  can call it locally before changing anything DoD-related.

What this is NOT:

  - Not a unit test (we already have those for each emitter + the plugin)
  - Not the DoD gate (that's `sulis-verify-requirements`, Phase C — this
    module gives that CLI the proven foundation it builds on)
  - Not a doc / runbook (per the founder's direction: automation first,
    explanation second)

Operating model:

  `run_environment_check(workspace, srd_text, tests_text)` returns a
  `EnvironmentCheckResult` dataclass with:

    - `status`: "pass" | "partial" | "fail"
    - `requirements_emitted`: count
    - `testrun_id`: the dna:testrun:<ulid> from the pytest run
    - `testresults_emitted`: count
    - `requirements_verified`: list of Requirement IDs with ≥1 passing
      TestResult
    - `requirements_unverified`: list of Requirement IDs with NO
      passing TestResult (the DoD-gate-blocking set)
    - `pytest_outcome`: the pytest exit code
    - `errors`: any stage-specific error messages

  The status is computed from the verified/unverified split:
    - all verified → "pass"
    - some verified → "partial"
    - none verified → "fail"

  Callers compose: the harness CLI writes the workspace + invokes this
  function; the verifier CLI (sulis-verify-requirements) skips the
  setup and runs the same check against an existing .brain/.

The workspace is a temporary directory by default; the caller can pass
a persistent one for inspection. The marketplace surface (scripts +
schemas) is COPIED into the workspace at a known path, so the pytest
sub-run sees them on sys.path as a downstream consumer would.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ─── Public result type ─────────────────────────────────────────────────


@dataclass
class EnvironmentCheckResult:
    """Structured output of one end-to-end pipeline run."""

    status: str  # "pass" | "partial" | "fail"
    requirements_emitted: int = 0
    testrun_id: str | None = None
    testresults_emitted: int = 0
    requirements_verified: list[str] = field(default_factory=list)
    requirements_unverified: list[str] = field(default_factory=list)
    pytest_outcome: int | None = None
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "status": self.status,
            "requirements_emitted": self.requirements_emitted,
            "testrun_id": self.testrun_id,
            "testresults_emitted": self.testresults_emitted,
            "requirements_verified": list(self.requirements_verified),
            "requirements_unverified": list(self.requirements_unverified),
            "pytest_outcome": self.pytest_outcome,
            "errors": list(self.errors),
        }


# ─── Stage helpers ─────────────────────────────────────────────────────


def _copy_marketplace_surface(scripts_src: Path, dest: Path) -> Path:
    """Copy the marketplace scripts + schemas into the workspace.

    Mirrors what a downstream consumer receives via `claude plugin install`:
    a `plugins/sulis/scripts/` tree with the emitter CLIs, the
    `_brain_*` libraries, the `_pytest_brain_emit` plugin, and the
    vendored `plugins/sulis/brain/compiled/` schemas.

    Returns the destination scripts path.
    """
    dest_scripts = dest / "plugins" / "sulis" / "scripts"
    dest_scripts.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(scripts_src, dest_scripts, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(
                        "__pycache__", "*.pyc", ".pytest_cache", ".venv",
                        "tests",  # don't copy our own test suite into the workspace
                        "node_modules",
                    ))

    # Schemas live next to scripts in the source tree; copy too.
    brain_src = scripts_src.parent / "brain"
    if brain_src.exists():
        shutil.copytree(brain_src, dest / "plugins" / "sulis" / "brain",
                        dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("__pycache__"))

    return dest_scripts


def _write_srd(workspace: Path, srd_text: str) -> Path:
    """Write the SRD to the canonical `.specifications/<project>/SRD.md`
    location so the brain-emit plugin can auto-infer the base dir."""
    srd_dir = workspace / ".specifications" / "demo"
    srd_dir.mkdir(parents=True, exist_ok=True)
    srd = srd_dir / "SRD.md"
    srd.write_text(srd_text)
    return srd


def _write_tests(workspace: Path, tests_text: str) -> Path:
    """Write a test module that pytest can collect from the workspace.

    The tests directory sits at the workspace root (alongside .brain/);
    the pytest invocation runs from there.
    """
    tests_dir = workspace / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    test_file = tests_dir / "test_demo.py"
    test_file.write_text(tests_text)
    return test_file


def _emit_requirements(
    workspace: Path, srd: Path, scripts_dir: Path
) -> tuple[int, list[str]]:
    """Run sulis-emit-requirements; return (count, error-messages)."""
    errors: list[str] = []
    cmd = [
        sys.executable, str(scripts_dir / "sulis-emit-requirements"),
        "--from-srd", str(srd),
        "--base-dir", str(workspace / ".brain" / "instances"),
        "--repo-root", str(workspace),
    ]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(scripts_dir) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=60)
    if proc.returncode != 0:
        errors.append(
            f"sulis-emit-requirements failed (rc={proc.returncode}): "
            f"{proc.stderr.strip() or proc.stdout.strip()}"
        )

    # Count emitted requirements by listing the directory rather than
    # parsing CLI output (the CLI's JSON output isn't load-bearing here).
    req_dir = workspace / ".brain" / "instances" / "product-development" / "requirement"
    count = len(list(req_dir.glob("*.jsonld"))) if req_dir.exists() else 0
    return count, errors


def _run_pytest_with_brain_emit(
    workspace: Path, srd: Path, scripts_dir: Path
) -> tuple[int, list[str]]:
    """Run pytest in the workspace with the brain-emit plugin active.

    Returns (pytest_exit_code, error-messages). A non-zero exit from
    pytest (test failures) is NOT an error from the harness's
    perspective — the goal is to observe what landed in the brain, not
    to demand a green test suite.
    """
    errors: list[str] = []
    env = os.environ.copy()
    env["PYTHONPATH"] = str(scripts_dir) + os.pathsep + env.get("PYTHONPATH", "")

    cmd = [
        sys.executable, "-m", "pytest",
        "-p", "_pytest_brain_emit",
        "-p", "no:cacheprovider",
        "--rootdir", str(workspace),
        "--brain-emit",
        "--brain-srd", str(srd),
        "--brain-base-dir", str(workspace / ".brain" / "instances"),
        "-q",
        str(workspace / "tests"),
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=120,
            cwd=workspace,
        )
        return proc.returncode, errors
    except subprocess.TimeoutExpired:
        errors.append("pytest run timed out (>120s)")
        return -1, errors
    except FileNotFoundError as exc:
        errors.append(f"pytest invocation failed: {exc}")
        return -1, errors


def _query_brain_graph(
    workspace: Path, scripts_dir: Path,
) -> tuple[list[str], list[str], str | None, int]:
    """Walk the brain graph and split Requirements into verified vs unverified.

    Returns (verified_ids, unverified_ids, testrun_id_or_None,
    testresults_count).

    A Requirement is VERIFIED if there exists at least one TestResult
    whose `verifies[]` array contains its id AND whose outcome is `pass`.
    Everything else is UNVERIFIED — including "no TestResult at all".
    """
    sys.path.insert(0, str(scripts_dir))
    try:
        from _brain_query import (
            find_requirements,
            find_passing_testresults_verifying,
            iter_entities,
        )
    finally:
        # Don't permanently pollute sys.path; pop our entry on exit.
        # (Best-effort — if the import succeeded we leave it since
        # the imported references hold the modules.)
        pass

    base = workspace / ".brain" / "instances"
    reqs = find_requirements(base)
    verified: list[str] = []
    unverified: list[str] = []
    for r in reqs:
        passing = find_passing_testresults_verifying(base, r["id"])
        if passing:
            verified.append(r["id"])
        else:
            unverified.append(r["id"])

    # Find the most-recent TestRun (there should be exactly one per
    # harness invocation, but if a prior session left one it's stable
    # to sort by `ran_at`).
    runs = list(iter_entities(base, entity_type="testrun"))
    testrun_id = None
    if runs:
        runs.sort(key=lambda r: str(r.get("ran_at", "")), reverse=True)
        testrun_id = runs[0].get("id")

    results = list(iter_entities(base, entity_type="testresult"))
    return verified, unverified, testrun_id, len(results)


# ─── Top-level entry ────────────────────────────────────────────────────


def run_environment_check(
    workspace: Path,
    *,
    scripts_src: Path,
    srd_text: str,
    tests_text: str,
) -> EnvironmentCheckResult:
    """End-to-end harness: set up workspace, drive pipeline, query graph.

    Args:
        workspace: directory to use as the production-like root. Must be
            writable and (ideally) empty.
        scripts_src: source `plugins/sulis/scripts/` directory to copy
            into the workspace. In normal use this is the marketplace's
            own scripts directory.
        srd_text: SRD.md content. Should contain `**FR-NN: ...**` blocks
            for the harness to emit Requirements.
        tests_text: a pytest test module's source. Should use
            `@pytest.mark.verifies("FR-NN")` markers to claim
            Requirements.

    Returns:
        EnvironmentCheckResult — see dataclass for the shape.
    """
    workspace = Path(workspace).resolve()
    workspace.mkdir(parents=True, exist_ok=True)

    result = EnvironmentCheckResult(status="fail")

    # Stage 1: drop the marketplace surface into the workspace
    try:
        dest_scripts = _copy_marketplace_surface(Path(scripts_src), workspace)
    except Exception as exc:
        result.errors.append(f"copy marketplace surface failed: {exc}")
        return result

    # Stage 2: write the SRD + tests
    srd = _write_srd(workspace, srd_text)
    _write_tests(workspace, tests_text)

    # Stage 3: emit Requirements
    req_count, errs = _emit_requirements(workspace, srd, dest_scripts)
    result.errors.extend(errs)
    result.requirements_emitted = req_count
    if req_count == 0:
        result.errors.append("no Requirements emitted from the SRD — pipeline can't proceed")
        return result

    # Stage 4: run pytest with brain-emit enabled
    pytest_rc, errs = _run_pytest_with_brain_emit(workspace, srd, dest_scripts)
    result.errors.extend(errs)
    result.pytest_outcome = pytest_rc

    # Stage 5: query the brain graph and compute the verdict
    verified, unverified, testrun_id, tr_count = _query_brain_graph(
        workspace, dest_scripts,
    )
    result.requirements_verified = verified
    result.requirements_unverified = unverified
    result.testrun_id = testrun_id
    result.testresults_emitted = tr_count

    # Compute status
    if not verified and not unverified:
        result.status = "fail"
        result.errors.append("no Requirements in brain — emission stage didn't run")
    elif unverified and not verified:
        result.status = "fail"
    elif unverified and verified:
        result.status = "partial"
    else:
        result.status = "pass"

    return result
