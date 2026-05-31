"""Regression: every `.github/workflows/*.yml` file must be YAML-parseable.

This test exists because of an incident on 2026-05-31:

  CH-01KSYE (PR #124, "wire entity emitters into existing substrate")
  added a brain-emit Release step to `.github/workflows/release-on-merge.yml`
  with a multi-line python3 -c expression embedded inside a `run: |` literal
  block. The Python source lines started at column 0 — below the block's
  indentation level — which terminates a YAML literal-block early. The
  parser then failed on the subsequent Python `:` and `try:` tokens.

  CI didn't catch it: `branch-ci` runs pytest + lint + checks, none of which
  parse the workflow files themselves. GitHub Actions only attempts to parse
  the YAML when the trigger fires — and when it fails, the workflow simply
  doesn't run, with no fail-loud at PR time.

  The release-on-merge robot fired on PR #130's merge to main and silently
  did NOTHING (no version bump, no CHANGELOG, no tag, no GitHub Release).

This test closes the gap structurally: at branch-ci time, every workflow
under `.github/workflows/` is parsed; a broken YAML fails the test.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def _workflows_dir() -> Path:
    """Find `.github/workflows/` from the test file's location."""
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        candidate = ancestor / ".github" / "workflows"
        if candidate.is_dir():
            return candidate
    pytest.skip("no .github/workflows/ directory found (not running in marketplace repo)")
    raise AssertionError("unreachable")  # for type checker


def _workflow_files() -> list[Path]:
    wf_dir = _workflows_dir()
    return sorted(
        p for p in wf_dir.iterdir()
        if p.is_file() and p.suffix in (".yml", ".yaml")
    )


class TestWorkflowsParse:
    @pytest.mark.parametrize(
        "workflow_path",
        _workflow_files(),
        ids=lambda p: p.name,
    )
    def test_workflow_yaml_parses(self, workflow_path: Path) -> None:
        """Every workflow file must be valid YAML.

        A failure here means GitHub Actions can't run the workflow at all
        (the runner skips workflows whose YAML doesn't parse — silently —
        which is how we shipped a broken release-on-merge.yml to main on
        2026-05-31 and missed the v1.131.0 release).

        The fix when this fails: open the workflow file, look for
        `run: |` blocks with content at column 0 (multi-line heredocs,
        embedded python -c, etc). Every line inside the block MUST stay
        at-or-beyond the block's indentation. Collapse multi-line
        embeds to one line, or use a sidecar script file.
        """
        with workflow_path.open() as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), f"{workflow_path.name}: not a dict at root"
        assert data.get("name"), f"{workflow_path.name}: missing 'name'"
        # GitHub Actions parses `on:` as the keyword `True` in PyYAML
        # (it's a YAML 1.1 boolean alias). Accept either form.
        assert "on" in data or True in data, f"{workflow_path.name}: missing 'on:' trigger"
        assert "jobs" in data, f"{workflow_path.name}: missing 'jobs:'"

    def test_at_least_one_workflow_exists(self) -> None:
        """Sanity: the marketplace has workflows."""
        files = _workflow_files()
        assert len(files) > 0, "no .yml files in .github/workflows/"

    def test_release_on_merge_is_present(self) -> None:
        """Specific check for the file the 2026-05-31 incident broke."""
        names = {p.name for p in _workflow_files()}
        assert "release-on-merge.yml" in names, (
            "release-on-merge.yml MUST be present — it's the bump authority "
            "(ADR-004). Removing it would silently disable releases."
        )
