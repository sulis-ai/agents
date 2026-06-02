"""Trunk-shape characterisation — WP-001 (CH-01KT4K, simplify-release-robot).

The release-train Workflow was re-modelled from the two-branch (dev->main
promotion) shape to a trunk-based (main-only) shape: the release stopped being
a *merge between branches* and became a *bump + tag on the trunk*. This test
pins the end-state so a future edit cannot silently re-introduce the promotion
machinery (the release-of-release loop #132 / the diverged-branch bugs).

End-state (per WP-001 Contract + AUDIT.md):

  * 10 Steps (was 15) — the 5 dev->main-PR Steps deleted:
    preflight-cross-branch-drift, draft-pr-body-and-changelog, open-release-pr,
    wait-for-checks-and-mergeability, squash-merge.
  * 4 FailureModes (was 8) — the 4 orphaned-by-deletion FMs removed:
    pr-checks-fail, release-pr-conflicts-with-target-at-merge,
    pr-open-but-mergeability-stuck, probabilistic-step-token-budget-exceeded.
    The loop-guard + bot-tag FMs are KEPT (load-bearing on a trunk).
  * excluded_from_yaml shrinks to the 2 real-but-unannotated Steps:
    gate-founder-confirmation, publish-github-release.
  * The drift gate (check-canonical-drift.py mirror<->template) exits 0.

Deterministic + offline. The drift-exit-0 assertion shells out to the real
detector against the real template, which is the load-bearing structural proof
that the imperative template matches the re-modelled canonical.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# tests/unit/ -> tests/ -> scripts/ -> sulis/ -> plugins/ -> repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_INSTANCE_DIR = _REPO_ROOT / "plugins" / "sulis" / "instances" / "release-train"
_STEPS = _INSTANCE_DIR / "steps.jsonld"
_WORKFLOW = _INSTANCE_DIR / "workflow.jsonld"
_FAILUREMODES = _INSTANCE_DIR / "failuremodes.jsonld"
_TRIGGERS = _INSTANCE_DIR / "triggers.jsonld"
_TEMPLATE = (
    _REPO_ROOT / "plugins" / "sulis" / "templates" / "workflows" / "release-on-merge.yml"
)
_DRIFT_SCRIPT = _REPO_ROOT / "plugins" / "sulis" / "scripts" / "check-canonical-drift.py"

# The 10 kept Steps in canonical (linear) order.
_KEPT_STEP_NAMES = [
    "detect-pending-changesets",
    "preflight-version-drift",
    "compute-next-version",
    "gate-founder-confirmation",
    "bump-version-files",
    "write-changelog-entry",
    "commit-bump-on-main",
    "tag-and-push",
    "publish-github-release",
    "emit-release-entity",
]

_DELETED_STEP_NAMES = {
    "preflight-cross-branch-drift",
    "draft-pr-body-and-changelog",
    "open-release-pr",
    "wait-for-checks-and-mergeability",
    "squash-merge",
}

# The 4 kept FailureModes (still real on a trunk).
_KEPT_FAILUREMODE_NAMES = {
    "version-drift-detected-pre-flight",
    "loop-guard-matches-founder-pr",
    "bot-tag-doesnt-trigger-release-prod",
    "workflow-yaml-fails-to-parse",
}

_DELETED_FAILUREMODE_NAMES = {
    "pr-checks-fail",
    "release-pr-conflicts-with-target-at-merge",
    "pr-open-but-mergeability-stuck",
    "probabilistic-step-token-budget-exceeded",
}

_EXPECTED_EXCLUDED_FROM_YAML = {
    "gate-founder-confirmation",
    "publish-github-release",
}


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


# ----- Steps -----


def test_steps_are_the_ten_kept_in_order() -> None:
    """steps.jsonld declares exactly the 10 kept Steps, in canonical order."""
    names = [s["name"] for s in _load(_STEPS)["steps"]]
    assert names == _KEPT_STEP_NAMES, (
        f"steps.jsonld step order/shape drifted.\n"
        f"got:      {names}\n"
        f"expected: {_KEPT_STEP_NAMES}"
    )


def test_deleted_steps_are_gone() -> None:
    """None of the 5 dev->main-PR Steps survive."""
    names = {s["name"] for s in _load(_STEPS)["steps"]}
    leaked = names & _DELETED_STEP_NAMES
    assert not leaked, f"deleted Steps still present in steps.jsonld: {sorted(leaked)}"


def test_commit_step_renamed_to_on_main() -> None:
    """The bot-commit Step is conceptually commit-bump-on-main (commits
    directly to main, no promotion PR). The bot author identity stays in
    the prose (load-bearing for the loop-guard)."""
    by_name = {s["name"]: s for s in _load(_STEPS)["steps"]}
    assert "commit-bump-on-main" in by_name, (
        "expected commit-bump-on-main Step (was commit-bump-as-bot)"
    )
    assert "commit-bump-as-bot" not in by_name
    instr = by_name["commit-bump-on-main"].get("agent_instructions", "")
    assert "github-actions[bot]" in instr, (
        "commit step must retain the github-actions[bot] author identity "
        "(load-bearing for the loop-guard)"
    )


def test_excluded_from_yaml_is_the_two() -> None:
    """excluded_from_yaml shrinks to the 2 real-but-unannotated Steps."""
    excluded = set(_load(_STEPS).get("excluded_from_yaml", []))
    assert excluded == _EXPECTED_EXCLUDED_FROM_YAML, (
        f"excluded_from_yaml mismatch — got {sorted(excluded)}, "
        f"expected {sorted(_EXPECTED_EXCLUDED_FROM_YAML)}"
    )


def test_no_surviving_step_handles_a_deleted_failuremode() -> None:
    """No kept Step's handles_failures points at a deleted FailureMode id."""
    fm_ids_by_name = {fm["name"]: fm["id"] for fm in _load(_FAILUREMODES)["failuremodes"]}
    # The deleted FM ids are not in failuremodes.jsonld anymore — so any
    # surviving handles_failures entry that DOESN'T resolve is the failure.
    valid_ids = set(fm_ids_by_name.values())
    dangling: list[str] = []
    for s in _load(_STEPS)["steps"]:
        for fm_id in s.get("handles_failures", []):
            if fm_id not in valid_ids:
                dangling.append(f"{s['name']}: {fm_id}")
    assert not dangling, f"surviving Steps reference deleted FailureModes: {dangling}"


# ----- Workflow -----


def test_workflow_steps_list_is_the_ten() -> None:
    wf = _load(_WORKFLOW)["workflows"][0]
    assert wf["steps"] == _KEPT_STEP_NAMES, (
        f"workflow.steps[] drifted.\ngot:      {wf['steps']}\n"
        f"expected: {_KEPT_STEP_NAMES}"
    )


def test_workflow_has_no_back_edge_or_promotion_edges() -> None:
    """The JT-7 back-edge and all promotion/PR transitions are gone — the
    path is strictly linear over the 10 kept Steps (plus terminals)."""
    wf = _load(_WORKFLOW)["workflows"][0]
    joined = "\n".join(wf["transitions"])
    for deleted in _DELETED_STEP_NAMES:
        assert deleted not in joined, (
            f"transition still references deleted step {deleted!r}:\n{joined}"
        )


def test_workflow_transitions_only_reference_kept_steps() -> None:
    wf = _load(_WORKFLOW)["workflows"][0]
    kept = set(_KEPT_STEP_NAMES)
    for t in wf["transitions"]:
        lhs = t.split("->", 1)[0].strip()
        assert lhs in kept, f"transition LHS {lhs!r} is not a kept Step: {t!r}"


# ----- FailureModes -----


def test_failuremodes_are_the_four_kept() -> None:
    names = {fm["name"] for fm in _load(_FAILUREMODES)["failuremodes"]}
    assert names == _KEPT_FAILUREMODE_NAMES, (
        f"failuremodes drifted.\ngot:      {sorted(names)}\n"
        f"expected: {sorted(_KEPT_FAILUREMODE_NAMES)}"
    )


def test_deleted_failuremodes_are_gone() -> None:
    names = {fm["name"] for fm in _load(_FAILUREMODES)["failuremodes"]}
    leaked = names & _DELETED_FAILUREMODE_NAMES
    assert not leaked, f"deleted FailureModes still present: {sorted(leaked)}"


def test_loadbearing_failuremodes_kept() -> None:
    """The loop-guard + bot-tag FMs MUST survive — deleting them
    re-introduces the release-of-release loop (#132)."""
    names = {fm["name"] for fm in _load(_FAILUREMODES)["failuremodes"]}
    assert "loop-guard-matches-founder-pr" in names
    assert "bot-tag-doesnt-trigger-release-prod" in names


# ----- Trigger -----


def test_event_trigger_is_push_to_main_not_dev_promotion() -> None:
    """The event Trigger condition is the push-to-main / cadence shape — no
    dev->main PR promotion language."""
    triggers = _load(_TRIGGERS)["triggers"]
    by_name = {t["name"]: t for t in triggers}
    # The event Trigger keeps its canonical id/ulid; its condition is rewritten.
    event = next(t for t in triggers if t["kind"] == "event")
    cond = event.get("condition", "").lower()
    desc = event.get("description", "").lower()
    blob = cond + " " + desc
    assert "dev" not in cond, (
        f"event Trigger condition still references dev->main promotion: "
        f"{event.get('condition')!r}"
    )
    assert "push" in blob and "main" in blob, (
        f"event Trigger condition must describe push-to-main/cadence; got "
        f"{event.get('condition')!r}"
    )
    # The manual Trigger remains.
    assert any(t["kind"] == "manual" for t in triggers)
    assert by_name  # silence unused in case of single trigger


# ----- The blocking gate: drift exit 0 -----


def test_drift_check_exits_zero_against_template() -> None:
    """check-canonical-drift.py (mirror<->template) exits 0 — the
    load-bearing structural proof. This is the WP's blocking gate."""
    if not _DRIFT_SCRIPT.is_file():
        pytest.skip("drift script not present")
    proc = subprocess.run(
        [
            sys.executable,
            str(_DRIFT_SCRIPT),
            "--instance-dir",
            str(_INSTANCE_DIR),
            "--yaml-path",
            str(_TEMPLATE),
            "--validate-schemas",
        ],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, (
        f"drift check did not exit 0 (got {proc.returncode}).\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    envelope = json.loads(proc.stdout)
    assert envelope.get("ok") is True, f"drift envelope not clean: {envelope}"
