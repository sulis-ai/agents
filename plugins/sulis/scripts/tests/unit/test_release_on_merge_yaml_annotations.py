"""Regression: the reusable `release-on-merge.yml` carries
`# canonical:step:<name>` annotations binding each implementing block to a
canonical Step per ADR-002.

Subject relocation (WP-005, SUBSTITUTE-Replace): the canonical-step
annotations and the loop-guard `if:` originally lived in the marketplace's
`.github/workflows/release-on-merge.yml`. WP-002 moved that 280-line body
into the plugin-distributed reusable workflow at
`plugins/sulis/templates/workflows/release-on-merge.yml`; WP-003 extended
it; WP-005 then replaced the marketplace file with a thin shim that calls
the reusable workflow. The annotations + loop-guard now live in the
reusable workflow, so these invariants are asserted there. (The shim
itself carries no step bodies and no inline guard — the guard fires through
the workflow_call indirection from the reusable workflow's job-level `if:`.)

Symmetric to the broader drift detector (WP-007); these are the executor's
local invariants — fast feedback at PR time, parsed against
`plugins/sulis/instances/release-train/steps.jsonld`.

Three classes of invariant tested here:

1. **YAML still parses.** A regression test for CH-01KSYZ
   (workflow-yaml-fails-to-parse) — adding annotations as bash comments
   above `- name:` is inert, but a missing space, stray dash, or column-0
   line inside a `run: |` block would break the parser. This test catches
   that within the same WP rather than waiting for GitHub Actions' silent
   no-op.

2. **Every annotation references a canonical Step.** No orphan
   annotations. The drift detector (WP-007) will also catch this against
   the broader Workflow envelope; here we provide a local check that runs
   inside the marketplace's pytest suite at branch-ci time.

3. **Loop-guard conjunction is intact.** Per FailureMode
   `loop-guard-matches-founder-pr` (CH-01KSZ1), the job-level `if:` MUST
   require BOTH (a) `actor != 'github-actions[bot]'` AND (b) the head-
   commit author check. The previous single-condition match silently
   skipped PR #132. This test greps the YAML for the conjunction.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml


_REUSABLE_REL = Path("plugins/sulis/templates/workflows/release-on-merge.yml")


def _repo_root() -> Path:
    """Find the marketplace repo root from the test file's location.

    The anchor is the reusable workflow (the post-WP-005 home of the
    canonical-step annotations + loop-guard), not the marketplace shim.
    """
    here = Path(__file__).resolve()
    for ancestor in here.parents:
        if (ancestor / _REUSABLE_REL).is_file():
            return ancestor
    pytest.skip(
        "reusable release-on-merge.yml not found (not running in marketplace repo)"
    )
    raise AssertionError("unreachable")  # for type checker


def _release_on_merge_yaml() -> Path:
    """The reusable workflow — annotations + loop-guard live here post-WP-005."""
    return _repo_root() / _REUSABLE_REL


def _steps_jsonld() -> Path:
    return (
        _repo_root()
        / "plugins"
        / "sulis"
        / "instances"
        / "release-train"
        / "steps.jsonld"
    )


def _failuremodes_jsonld() -> Path:
    return (
        _repo_root()
        / "plugins"
        / "sulis"
        / "instances"
        / "release-train"
        / "failuremodes.jsonld"
    )


def _canonical_step_names() -> set[str]:
    """The 15 canonical Step names from WP-002's steps.jsonld."""
    with _steps_jsonld().open() as f:
        data = json.load(f)
    return {step["name"] for step in data["steps"]}


def _canonical_failuremode_names() -> set[str]:
    """The 8 canonical FailureMode names from WP-004's failuremodes.jsonld."""
    with _failuremodes_jsonld().open() as f:
        data = json.load(f)
    return {fm["name"] for fm in data["failuremodes"]}


_ANNOTATION_RE = re.compile(r"^\s*#\s*canonical:(step|failuremode):([a-z0-9-]+)\s*$")


def _extracted_annotations() -> list[tuple[str, str]]:
    """Return [(kind, name), ...] for every canonical:* annotation in the YAML.

    `kind` is one of {"step", "failuremode"}; `name` is the kebab-case
    canonical entity name.
    """
    out: list[tuple[str, str]] = []
    with _release_on_merge_yaml().open() as f:
        for line in f:
            m = _ANNOTATION_RE.match(line)
            if m:
                out.append((m.group(1), m.group(2)))
    return out


class TestReleaseOnMergeYamlParses:
    """Regression for CH-01KSYZ — adding comments must not break parsing."""

    def test_yaml_safe_loads(self) -> None:
        """`pyyaml.safe_load` must succeed on the annotated YAML."""
        with _release_on_merge_yaml().open() as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict), "release-on-merge.yml: not a dict at root"
        # The reusable variant carries " (reusable)" in its name (WP-002).
        assert str(data.get("name", "")).startswith("release-on-merge")
        # The reusable workflow's trigger is `workflow_call:` (WP-002), which
        # PyYAML keys under "on" (not the boolean True alias that the bare
        # `on:`-with-mapping form produces for the marketplace shim).
        assert "on" in data or True in data
        assert "jobs" in data


class TestCanonicalStepAnnotations:
    """Every `# canonical:step:<name>` references a real Step name."""

    def test_at_least_one_step_annotation_present(self) -> None:
        """Sanity: the YAML carries at least one canonical:step annotation.

        Without this, WP-009's whole point evaporates. The drift detector
        would catch it eventually, but this local test catches it at edit
        time.
        """
        step_annotations = [
            name for kind, name in _extracted_annotations() if kind == "step"
        ]
        assert len(step_annotations) >= 1, (
            "release-on-merge.yml has no `# canonical:step:<name>` annotations. "
            "Per ADR-002, every implementing step block needs an inline "
            "annotation binding it to a canonical Step."
        )

    def test_all_step_annotations_reference_real_steps(self) -> None:
        """No orphan annotations — every annotation references a known Step."""
        canonical = _canonical_step_names()
        step_annotations = [
            name for kind, name in _extracted_annotations() if kind == "step"
        ]
        orphans = [name for name in step_annotations if name not in canonical]
        assert not orphans, (
            f"release-on-merge.yml has orphan `# canonical:step:<name>` "
            f"annotations referencing Steps that don't exist in "
            f"steps.jsonld: {orphans}. "
            f"Either rename the annotation to match a real Step, or "
            f"add the Step to plugins/sulis/instances/release-train/steps.jsonld."
        )


class TestCanonicalFailureModeAnnotations:
    """Every `# canonical:failuremode:<name>` references a real FailureMode."""

    def test_all_failuremode_annotations_reference_real_failuremodes(
        self,
    ) -> None:
        canonical = _canonical_failuremode_names()
        fm_annotations = [
            name for kind, name in _extracted_annotations() if kind == "failuremode"
        ]
        orphans = [name for name in fm_annotations if name not in canonical]
        assert not orphans, (
            f"release-on-merge.yml has orphan `# canonical:failuremode:<name>` "
            f"annotations referencing FailureModes that don't exist in "
            f"failuremodes.jsonld: {orphans}. "
            f"Either rename the annotation to match a real FailureMode, or "
            f"add the FailureMode to "
            f"plugins/sulis/instances/release-train/failuremodes.jsonld."
        )


class TestLoopGuardConjunction:
    """Per FailureMode loop-guard-matches-founder-pr (CH-01KSZ1).

    The job-level `if:` MUST require BOTH:
      (a) head_commit.author.username != 'github-actions[bot]', AND
      (b) github.actor != 'github-actions[bot]'

    The single-condition title-prefix match silently skipped a founder PR
    on 2026-05-31 (PR #132). This test pins the conjunction so a future
    refactor can't quietly drop one half.
    """

    def test_loop_guard_uses_both_actor_checks(self) -> None:
        content = _release_on_merge_yaml().read_text()
        # Both conditions must appear in the same `if:` expression, joined
        # by `&&`. We grep for both substrings rather than parsing the
        # GH-Actions expression syntax (which YAML doesn't model).
        assert (
            "github.event.head_commit.author.username != 'github-actions[bot]'"
            in content
        ), (
            "release-on-merge.yml loop-guard is missing the head_commit author "
            "check. Per FailureMode `loop-guard-matches-founder-pr`, the guard "
            "MUST require BOTH head_commit.author.username AND github.actor "
            "checks — single-condition matches silently skipped a founder PR "
            "on 2026-05-31."
        )
        assert "github.actor != 'github-actions[bot]'" in content, (
            "release-on-merge.yml loop-guard is missing the github.actor check. "
            "See FailureMode `loop-guard-matches-founder-pr` for the regression."
        )
        # And the `&&` conjunction — not two separate `if:` expressions.
        assert "&& github.actor != 'github-actions[bot]'" in content or (
            "github.actor != 'github-actions[bot]' &&" in content
        ), (
            "release-on-merge.yml loop-guard uses both actor checks but not "
            "joined by `&&`. The single-condition match (either check alone) "
            "is what skipped PR #132."
        )
