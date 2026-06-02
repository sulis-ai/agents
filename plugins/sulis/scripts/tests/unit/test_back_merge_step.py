"""WP-003 unit test — static assertions on the back-merge step block of
the reusable workflow (`plugins/sulis/templates/workflows/release-on-merge.yml`).

WP-003 appends three net-new steps to the reusable workflow's `release`
job: **pin-read**, **decide+act**, and **post-condition**. These steps
are the load-bearing piece that makes every release auto-back-merge to
dev (TDD §4.2, §5.2, §5.3, §5.6, §5.7). The behaviour is exercised
end-to-end by WP-008's integration suite (against scripted local git
remotes) and by the sandbox CI run (TDD §9.5); this file is the local,
fast, static guardrail that runs at branch-ci time and pins the
invariants the YAML must always satisfy.

Six invariant classes, mirroring the WP's Definition-of-Done Red set:

1. **The back-merge block exists and is gated.** A `pin` step, a
   `backmerge` step, and a post-condition step all appear; the
   pin-read and decide+act steps are gated on the same
   `steps.detect.outputs.skip != 'true'` condition every other
   release step uses (so a no-changeset push never back-merges).

2. **Pin-read regex round-trips.** The exact regex the workflow uses
   (`dev-sha-at-open: ([a-f0-9]{40})`, ADR-006) matches a valid 40-hex
   pin and rejects malformed ones (39 hex, non-hex, uppercase). This
   keeps the read side byte-for-byte aligned with ADR-005's write side.

3. **Fast-forward path is fast-forward only.** The clean-path push is
   the plain `git push origin main:dev` refspec — git refuses a
   non-fast-forward by default. No `--force` retry.

4. **Raced path uses the canonical strings.** The raced-path PR is
   created with `--base dev`, `--head main`, `--label back-integrate`,
   and a title carrying the `chore: back-integrate main → dev` prefix.
   Each of those four strings is asserted to match the constants
   exported by `drift_check.sh` (LABEL, TITLE_PREFIX, BASE_BRANCH,
   HEAD_BRANCH) character-for-character — the P8 canonical-identifier
   discipline. WP-009 carries the cross-component parity assertion;
   this is the executor's local check that the workflow side holds up
   its end.

5. **No force push anywhere in the back-merge block** — symmetric to
   `test_no_force_push_static.sh`, scoped to the new steps: none of
   `--force`, `--force-with-lease`, or the `+main:dev` refspec form
   appears (TDD §5.2 static layer, NFR-002).

6. **Post-condition step is present and asserts atomicity.** A final
   step runs with `if: always()`, references the `back-integrate`
   label and `--base dev`, and can exit non-zero (NFR-006 / TDD §5.3).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest
import yaml


# ─── Path helpers ──────────────────────────────────────────────────────


def _repo_root() -> Path:
    """Walk up to the marketplace repo root.

    Anchored on the reusable workflow this WP modifies — that file is
    the thing under test, so its presence is the correct root signal.
    """
    here = Path(__file__).resolve()
    rel = Path("plugins/sulis/templates/workflows/release-on-merge.yml")
    for ancestor in here.parents:
        if (ancestor / rel).is_file():
            return ancestor
    pytest.skip("reusable release-on-merge.yml not found (not in marketplace repo)")
    raise AssertionError("unreachable")  # for the type checker


def _reusable_workflow() -> Path:
    return (
        _repo_root()
        / "plugins"
        / "sulis"
        / "templates"
        / "workflows"
        / "release-on-merge.yml"
    )


def _drift_check_sh() -> Path:
    return _repo_root() / "plugins" / "sulis" / "scripts" / "drift_check.sh"


def _workflow_text() -> str:
    return _reusable_workflow().read_text()


# ─── Canonical-string sourcing (P8 — single source of truth) ───────────


def _canonical_constants() -> dict[str, str]:
    """Source LABEL / TITLE_PREFIX / BASE_BRANCH / HEAD_BRANCH from
    drift_check.sh by executing it in sourced-constants-only mode.

    This is exactly how the workflow's consumers (release-train, change)
    read the constants — we assert the workflow's literals against the
    same authority rather than re-hardcoding them in the test.
    """
    sh = _drift_check_sh()
    if not sh.is_file():
        pytest.skip("drift_check.sh not present (WP-001 not yet merged onto base)")
    script = (
        f'DRIFT_CHECK_SOURCED_ONLY=1 source "{sh}" && '
        'printf "LABEL=%s\\n" "$LABEL" && '
        'printf "TITLE_PREFIX=%s\\n" "$TITLE_PREFIX" && '
        'printf "BASE_BRANCH=%s\\n" "$BASE_BRANCH" && '
        'printf "HEAD_BRANCH=%s\\n" "$HEAD_BRANCH"'
    )
    out = subprocess.run(
        ["bash", "-c", script],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    consts: dict[str, str] = {}
    for line in out.splitlines():
        if "=" in line:
            k, _, v = line.partition("=")
            consts[k] = v
    return consts


# ─── Step-extraction helper ────────────────────────────────────────────


def _release_steps() -> list[dict]:
    data = yaml.safe_load(_workflow_text())
    return data["jobs"]["release"]["steps"]


def _step_by_id(step_id: str) -> dict | None:
    for step in _release_steps():
        if step.get("id") == step_id:
            return step
    return None


# ─── 1. Block exists and is gated ──────────────────────────────────────


class TestBackMergeBlockPresentAndGated:
    def test_pin_read_step_present(self) -> None:
        assert _step_by_id("pin") is not None, (
            "release-on-merge.yml has no step with id `pin`. WP-003 must "
            "append a pin-read step that recovers dev-sha-at-open from the "
            "merged release PR body (ADR-006)."
        )

    def test_decide_act_step_present(self) -> None:
        assert _step_by_id("backmerge") is not None, (
            "release-on-merge.yml has no step with id `backmerge`. WP-003 "
            "must append the decide+act step (fast-forward or raced-path PR)."
        )

    def test_pin_and_backmerge_gated_on_skip(self) -> None:
        """Both substantive steps gate on the existing skip output, so a
        no-changeset push never attempts a back-merge."""
        for sid in ("pin", "backmerge"):
            step = _step_by_id(sid)
            assert step is not None
            cond = str(step.get("if", ""))
            assert "steps.detect.outputs.skip != 'true'" in cond, (
                f"step `{sid}` must be gated on "
                f"`steps.detect.outputs.skip != 'true'` like every other "
                f"release step; found if: {cond!r}"
            )


# ─── 2. Pin-read regex round-trips (ADR-006) ───────────────────────────


# The canonical pin regex per ADR-006 / TDD §3. The workflow YAML must
# contain this pattern; the test also exercises it directly to prove it
# matches valid pins and rejects malformed ones.
_PIN_REGEX = r"dev-sha-at-open: ([a-f0-9]{40})"


class TestPinReadRegex:
    def test_workflow_contains_canonical_pin_regex(self) -> None:
        assert _PIN_REGEX in _workflow_text(), (
            "release-on-merge.yml must extract the pin with the canonical "
            f"regex {_PIN_REGEX!r} (ADR-006 / TDD §3). A different pattern "
            "would drift from ADR-005's write side."
        )

    def test_regex_matches_valid_40_hex_pin(self) -> None:
        body = "release notes\n<!-- dev-sha-at-open: " + "a" * 40 + " -->\n"
        m = re.search(_PIN_REGEX, body)
        assert m is not None
        assert m.group(1) == "a" * 40

    def test_regex_matches_realistic_sha(self) -> None:
        sha = "3a0b3175f0ff4bf5afc00569fac24bdf77f4bc9d"
        m = re.search(_PIN_REGEX, f"<!-- dev-sha-at-open: {sha} -->")
        assert m is not None and m.group(1) == sha

    @pytest.mark.parametrize(
        "bad",
        [
            "dev-sha-at-open: " + "a" * 39,  # 39 hex — too short
            "dev-sha-at-open: " + "g" * 40,  # non-hex char
            "dev-sha-at-open: " + "A" * 40,  # uppercase — wrong class
            "dev-sha-at-open:" + "a" * 40,  # missing the space separator
        ],
    )
    def test_regex_rejects_malformed_pin(self, bad: str) -> None:
        """A malformed pin must not yield a 40-hex capture — the workflow
        safe-defaults to the raced path on a failed extraction (TDD §5.6)."""
        m = re.search(_PIN_REGEX, bad)
        assert m is None, f"regex should not extract a pin from {bad!r}"


# ─── 3. Fast-forward path is fast-forward only ─────────────────────────


class TestFastForwardPath:
    def test_clean_path_uses_plain_main_to_dev_push(self) -> None:
        """The only push targeting dev is the bare `git push origin
        main:dev` refspec — git refuses a non-fast-forward by default
        (TDD §5.2 runtime layer)."""
        assert "git push origin main:dev" in _workflow_text(), (
            "the clean (fast-forward) path must push with the bare "
            "`git push origin main:dev` refspec; this is the no-force "
            "fast-forward (TDD §5.2)."
        )


# ─── 4. Raced path uses the canonical strings (P8 parity) ──────────────


class TestRacedPathCanonicalStrings:
    def test_pr_create_base_and_head(self) -> None:
        consts = _canonical_constants()
        text = _workflow_text()
        assert f"--base {consts['BASE_BRANCH']}" in text, (
            f"raced-path PR must be created with --base {consts['BASE_BRANCH']} "
            "(sourced from drift_check.sh BASE_BRANCH)."
        )
        assert f"--head {consts['HEAD_BRANCH']}" in text, (
            f"raced-path PR must be created with --head {consts['HEAD_BRANCH']} "
            "(sourced from drift_check.sh HEAD_BRANCH)."
        )

    def test_pr_create_label_matches_drift_check_constant(self) -> None:
        consts = _canonical_constants()
        assert f"--label {consts['LABEL']}" in _workflow_text(), (
            f"raced-path PR must be labelled {consts['LABEL']!r}, "
            "character-for-character matching drift_check.sh's LABEL "
            "constant (P8 canonical-identifier discipline; WP-009 parity)."
        )

    def test_pr_title_carries_canonical_prefix(self) -> None:
        consts = _canonical_constants()
        assert consts["TITLE_PREFIX"] in _workflow_text(), (
            f"raced-path PR title must carry the prefix "
            f"{consts['TITLE_PREFIX']!r}, matching drift_check.sh's "
            "TITLE_PREFIX constant byte-for-byte (TDD §3)."
        )

    def test_auto_merge_enabled_on_raced_pr(self) -> None:
        """ADR-002 — the raced back-merge PR auto-merges after CI green."""
        assert "gh pr merge" in _workflow_text() and "--auto" in _workflow_text(), (
            "raced-path PR must enable auto-merge (`gh pr merge --auto`) "
            "per ADR-002."
        )


# ─── 5. No force push anywhere in the back-merge block ─────────────────


class TestNoForcePush:
    def test_no_force_flags_in_workflow(self) -> None:
        """Symmetric to test_no_force_push_static.sh, re-asserted here so
        WP-003's new steps can never introduce a force flag (NFR-002)."""
        text = _workflow_text()
        for forbidden in ("--force", "--force-with-lease", "+main:dev"):
            assert forbidden not in text, (
                f"forbidden force-push token {forbidden!r} found in the "
                "reusable workflow. The back-merge step must only "
                "fast-forward or open a PR (TDD §5.2, NFR-002)."
            )


# ─── 6. Post-condition step (NFR-006 / TDD §5.3) ───────────────────────


class TestPostConditionStep:
    def _post_condition_step(self) -> dict:
        """The post-condition step has no id (nothing references it) and
        runs with `if: always()`. Identify it by that conjunction plus a
        back-integrate reference."""
        for step in _release_steps():
            cond = str(step.get("if", ""))
            run = str(step.get("run", ""))
            if "always()" in cond and "back-integrate" in run:
                return step
        pytest.fail(
            "no post-condition step found: expected a step with "
            "`if: always()` whose run body references `back-integrate`."
        )
        raise AssertionError("unreachable")

    def test_post_condition_runs_always(self) -> None:
        step = self._post_condition_step()
        assert "always()" in str(step.get("if", "")), (
            "the post-condition step must run with `if: always()` so it "
            "verifies the end-state even when an upstream step failed "
            "(TDD §5.3)."
        )

    def test_post_condition_references_label_and_base(self) -> None:
        run = str(self._post_condition_step().get("run", ""))
        assert "back-integrate" in run, (
            "post-condition must look for a back-integrate-labelled PR."
        )
        assert "--base dev" in run, (
            "post-condition must scope its PR lookup to --base dev."
        )

    def test_post_condition_can_exit_nonzero(self) -> None:
        """Atomicity (NFR-006): the step fails the workflow when neither
        dev==main nor a back-integrate PR exists."""
        run = str(self._post_condition_step().get("run", ""))
        assert "exit 1" in run, (
            "post-condition must `exit 1` when the atomicity invariant is "
            "violated (NFR-006 / TDD §5.3)."
        )
