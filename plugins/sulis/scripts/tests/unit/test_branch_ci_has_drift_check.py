"""Structural assertion: branch-ci.yml wires the canonical drift-detector (WP-008).

Per FR-015 + ADR-001/002 the drift detector (`check-canonical-drift.py`,
built in WP-007) is wired into `.github/workflows/branch-ci.yml` as a
**separate top-level job** (not a step inside the existing `branch-ci`
job). The new job must:

  * exist, named "canonical-drift-check";
  * run on `ubuntu-latest`;
  * invoke `check-canonical-drift.py` with the contracted
    `--instance-dir plugins/sulis/instances/release-train` and
    `--yaml-path .github/workflows/release-on-merge.yml` arguments;
  * run in **advisory mode** for v1 (`continue-on-error: true`) — the
    wave-5b dogfood found 11 pre-existing reconciliation items
    (6 `missing_in_yaml` + 5 `missing_failuremode_handling`) that are
    mostly by-design absences (Steps 1-8 live in skill prose per
    MUC-007). Advisory mode surfaces drift in the run logs without
    blocking PR merges. Future-toggle to blocking is a one-line YAML
    change in a follow-on change once the 11 items are reconciled.

CI YAML is not unit-testable the way Python is, so this is a
structural assertion over the workflow text (read as YAML). PyYAML is
listed in `plugins/sulis/scripts/pyproject.toml` so we can parse the
file directly rather than relying on a brittle line-scan.

This test FAILS RED against the pre-edit tree (the job does not yet
exist) and PASSES once the job is added to branch-ci.yml.

Stdlib + pyyaml + pytest, Python 3.11-safe.
"""

from __future__ import annotations

from pathlib import Path

import yaml

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_WORKFLOW = _REPO_ROOT / ".github" / "workflows" / "branch-ci.yml"

_JOB_KEY = "canonical-drift-check"
_INSTANCE_ARG = "--instance-dir plugins/sulis/instances/release-train"
_YAML_ARG = "--yaml-path .github/workflows/release-on-merge.yml"
_SCRIPT_INVOCATION = "check-canonical-drift.py"


def _load_workflow() -> dict:
    """Parse branch-ci.yml. Reused by every assertion below."""
    return yaml.safe_load(_WORKFLOW.read_text(encoding="utf-8"))


def test_workflow_exists():
    """Guard: branch-ci.yml resolves to a real file in the live tree."""
    assert _WORKFLOW.is_file(), f"missing workflow {_WORKFLOW}"


def test_workflow_parses_as_yaml():
    """branch-ci.yml is valid YAML.

    This is the structural smoke check that the addition we make in
    Green doesn't break the file. Existing structural tests over the
    file rely on this too.
    """
    doc = _load_workflow()
    assert isinstance(doc, dict), "branch-ci.yml did not parse to a mapping"
    assert "jobs" in doc, "branch-ci.yml missing top-level 'jobs' key"


def test_drift_check_job_present():
    """A `canonical-drift-check` job exists at the top-level of `jobs`.

    Fails RED before the edit (the job is absent).
    """
    doc = _load_workflow()
    jobs = doc.get("jobs", {})
    assert _JOB_KEY in jobs, (
        f"job '{_JOB_KEY}' missing from branch-ci.yml jobs: {sorted(jobs)}"
    )


def test_drift_check_job_runs_on_ubuntu():
    """The drift-check job declares `runs-on: ubuntu-latest`.

    Matches the existing `branch-ci` job's runner. Pinning to a
    specific runner family keeps the canonical+yaml read deterministic.
    """
    doc = _load_workflow()
    job = doc.get("jobs", {}).get(_JOB_KEY)
    assert job is not None, f"job '{_JOB_KEY}' missing"
    assert job.get("runs-on") == "ubuntu-latest", (
        f"job '{_JOB_KEY}' runs-on must be ubuntu-latest; got {job.get('runs-on')!r}"
    )


def test_drift_check_job_is_advisory_for_v1():
    """The job sets `continue-on-error: true` (advisory mode for v1).

    The wave-5b dogfood found 11 pre-existing reconciliation items that
    the canonical now makes visible. Advisory mode surfaces drift in
    the run logs without blocking PR merges; flipping to blocking is a
    one-line YAML change once those items are reconciled in a follow-on.

    This assertion is deliberately load-bearing: removing the toggle
    silently (i.e. flipping to blocking without removing the 11 items
    first) would block every PR build, which is the failure this WP
    explicitly defends against.
    """
    doc = _load_workflow()
    job = doc.get("jobs", {}).get(_JOB_KEY)
    assert job is not None, f"job '{_JOB_KEY}' missing"
    assert job.get("continue-on-error") is True, (
        f"job '{_JOB_KEY}' must set continue-on-error: true for v1 "
        f"(advisory mode); got {job.get('continue-on-error')!r}"
    )


def test_drift_check_job_invokes_script_with_contracted_args():
    """At least one step in the drift-check job runs `check-canonical-drift.py`
    with the contracted `--instance-dir` and `--yaml-path` arguments.

    The exit-1-on-drift contract of the script is what surfaces gaps in
    the CI run logs (advisory mode keeps the build green but the
    failed-step indicator is visible). Fails RED before the edit.
    """
    doc = _load_workflow()
    job = doc.get("jobs", {}).get(_JOB_KEY)
    assert job is not None, f"job '{_JOB_KEY}' missing"
    steps = job.get("steps", [])
    assert isinstance(steps, list) and steps, (
        f"job '{_JOB_KEY}' must declare at least one step"
    )

    # Look at every step's `run:` field; the script invocation may live
    # inside a multi-line block.
    run_text = "\n".join(
        step.get("run", "") for step in steps if isinstance(step, dict)
    )
    assert _SCRIPT_INVOCATION in run_text, (
        f"job '{_JOB_KEY}' does not invoke '{_SCRIPT_INVOCATION}'"
    )
    assert _INSTANCE_ARG in run_text, (
        f"job '{_JOB_KEY}' missing required arg: {_INSTANCE_ARG}"
    )
    assert _YAML_ARG in run_text, (
        f"job '{_JOB_KEY}' missing required arg: {_YAML_ARG}"
    )


def test_drift_check_job_has_checkout_step():
    """The drift-check job checks out the repo before invoking the script.

    The script reads files from the working tree; without checkout the
    job would fail with "file not found" rather than reporting drift.
    """
    doc = _load_workflow()
    job = doc.get("jobs", {}).get(_JOB_KEY)
    assert job is not None, f"job '{_JOB_KEY}' missing"
    steps = job.get("steps", [])
    uses_values = [step.get("uses", "") for step in steps if isinstance(step, dict)]
    assert any(u.startswith("actions/checkout@") for u in uses_values), (
        f"job '{_JOB_KEY}' must use actions/checkout; uses values: {uses_values}"
    )


def test_existing_branch_ci_job_still_present():
    """Regression: adding the new job does not remove or rename the
    existing `branch-ci` job — that's the required-check the merge
    queue gates on.
    """
    doc = _load_workflow()
    jobs = doc.get("jobs", {})
    assert "branch-ci" in jobs, (
        f"existing 'branch-ci' job must still be present; got jobs: {sorted(jobs)}"
    )
