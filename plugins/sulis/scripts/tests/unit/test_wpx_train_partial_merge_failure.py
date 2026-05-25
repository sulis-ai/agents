"""Characterisation test for HD-003 — partial-merge-failure handling.

Before HD-003: `cmd_run`'s sequential squash-merge loop had no per-merge
try/except. If `_merge_squash` raised on entry N after entries 1..N-1 had
already landed on dev, the RuntimeError propagated up to the outer
``except RuntimeError`` handler at the tail of `cmd_run`, which writes
``outcome=error`` and exits — without reverting the partial merges that
DID land. Dev was left in a half-state; the next train picked up the
unmerged WPs but the shipped ones had no INDEX flips, no train BLOCKER,
no revert.

After HD-003: each per-entry merge is wrapped in try/except; on
exception, control routes through `_handle_post_merge_failure` with the
partial bundle (entries 1..N-1 carry `merge_sha_on_dev`; entry N still
None). `_handle_post_merge_failure`'s existing internal filter
``merged = [e for e in bundle if e.get("merge_sha_on_dev")]`` selects
only the actually-landed merges for revert + restore.

Concrete trigger: 2026-05-23 autonomous founder session crashed mid-batch
after WP-AUTO-001 merged successfully; the next merge attempted on a
branch with drifted state, `_merge_squash` raised, the train state went
to `error`, and the maintainer had to reverse-engineer state from git
log.

These tests load `wpx-train` as a module via
``importlib.util.spec_from_file_location`` because the script lives at
``scripts/wpx-train`` (no .py extension; not on sys.path normally).
``cmd_run``'s heavy setup machinery (parse INDEX, eligibility, rebase,
CI) is monkeypatched on the loaded module so only the squash-merge loop's
new behaviour is exercised.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent


def _load_wpx_train_module():
    """Load scripts/wpx-train as a module, importable as wpx_train_module.

    The script has no .py extension and is invoked via shebang in
    production. For tests we load it explicitly so we can reach into
    `cmd_run` + the module-level imports.
    """
    if str(_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(_SCRIPTS_DIR))
    # The script has no .py extension, so spec_from_file_location can't
    # guess the loader. Pass SourceFileLoader explicitly.
    script_path = _SCRIPTS_DIR / "wpx-train"
    loader = importlib.machinery.SourceFileLoader(
        "wpx_train_module", str(script_path),
    )
    spec = importlib.util.spec_from_loader("wpx_train_module", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["wpx_train_module"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def wpx_train(monkeypatch):
    """Load wpx-train as a module + restore sys.modules on teardown."""
    module = _load_wpx_train_module()
    yield module
    sys.modules.pop("wpx_train_module", None)


@pytest.fixture
def tmp_project(tmp_path):
    """Minimal project layout for cmd_run to read.

    Creates .architecture/test-proj/work-packages/INDEX.md (empty;
    parse_index_md is monkeypatched so contents don't matter) and the
    train-runs/ dir that init_train_state writes into.
    """
    project = "test-proj"
    repo_root = tmp_path
    arch = repo_root / ".architecture" / project
    wp_dir = arch / "work-packages"
    train_runs = arch / "train-runs"
    wp_dir.mkdir(parents=True, exist_ok=True)
    train_runs.mkdir(parents=True, exist_ok=True)
    (wp_dir / "INDEX.md").write_text("# placeholder\n")
    return SimpleNamespace(
        repo_root=repo_root,
        project=project,
        wp_dir=wp_dir,
        train_runs=train_runs,
        index_md=wp_dir / "INDEX.md",
    )


def _make_args(tmp_project) -> SimpleNamespace:
    """Construct an argparse.Namespace-equivalent for cmd_run.

    Only attributes cmd_run actually reads are set. cmd_run uses
    `getattr(args, "...", default)` for optional fields, so unset
    attributes are fine.
    """
    return SimpleNamespace(
        project=tmp_project.project,
        repo_root=str(tmp_project.repo_root),
        repo="acme/test-repo",
        base_branch="dev",
        force=True,
        max_batch_size=10,
        deploy_workflow="deploy.yml",
        deploy_poll_interval=None,
        deploy_cap=None,
        staging_url=None,
        smoke_cmd="",
        ci_poll_interval=None,
        strict_ci=False,
    )


def _eligible_batch(wpx_train, *wp_ids: str) -> list:
    """Construct a list of EligibilityResult objects for the given WP IDs.

    `wpx-train` re-exports `EligibilityResult` via `from _wpxlib import ...`,
    so it's available as an attribute on the loaded module.
    """
    return [
        wpx_train.EligibilityResult(
            wp=wp_id,
            branch=f"feat/{wp_id.lower()}-x",
            eligible=True,
            reason="ready",
        )
        for wp_id in wp_ids
    ]


def _install_happy_path_mocks(wpx_train, monkeypatch, eligible_batch):
    """Monkeypatch all the helpers cmd_run calls BEFORE the merge loop.

    The merge loop itself (and its monkeypatches) is left to each test.
    Returns a dict the test can use to introspect calls, but most
    assertions in this suite are on the merge-loop monkeypatches.
    """
    # Discovery: parse INDEX, read overrides, eligibility
    monkeypatch.setattr(wpx_train, "parse_index_md",
                        lambda *a, **k: [SimpleNamespace(wp=e.wp) for e in eligible_batch])
    monkeypatch.setattr(wpx_train, "read_overrides",
                        lambda *a, **k: wpx_train.TrainOverrides(includes=[], holds=[]))
    monkeypatch.setattr(wpx_train, "find_eligible_branches",
                        lambda *a, **k: eligible_batch)
    monkeypatch.setattr(wpx_train, "check_train_trigger",
                        lambda *a, **k: (True, "force"))
    monkeypatch.setattr(wpx_train, "pack_batches",
                        lambda eligible, max_per_batch: [eligible])

    # Clone + rebase: skip the network / git work
    monkeypatch.setattr(wpx_train, "clone_repo_to_temp",
                        lambda *a, **k: None)
    monkeypatch.setattr(wpx_train, "_gh_ref_sha",
                        lambda repo, branch: "0" * 40)

    branch_to_sha = {
        e.branch: f"{i:040x}" for i, e in enumerate(eligible_batch, start=1)
    }
    monkeypatch.setattr(wpx_train, "_gh_branch_sha",
                        lambda repo, branch: branch_to_sha[branch])

    rebased_counter = {"n": 0}
    def _fake_rebase(clone_dir, branch, onto_sha, base_branch="dev"):
        rebased_counter["n"] += 1
        return f"reb{rebased_counter['n']:037x}"
    monkeypatch.setattr(wpx_train, "rebase_branch_in_clone", _fake_rebase)

    # Bundled-tip CI: green so cmd_run proceeds to the merge loop
    monkeypatch.setattr(wpx_train, "_poll_ci",
                        lambda *a, **k: "green")


# ─── Test 1: routing to _handle_post_merge_failure ──────────────────────


def test_merge_failure_mid_batch_routes_to_handle_post_merge_failure_with_partial_bundle(
    wpx_train, tmp_project, monkeypatch,
):
    """Failure on the 3rd merge after merges 1+2 land routes through the
    post-merge-failure path with the partial bundle intact.

    BEFORE HD-003: this test would fail because the RuntimeError from
    `_merge_squash` propagated past the merge loop, hit the outer
    `except RuntimeError`, and exited with `outcome=error` — without
    ever calling `_handle_post_merge_failure`.
    """
    batch = _eligible_batch(wpx_train, "WP-001", "WP-002", "WP-003")
    _install_happy_path_mocks(wpx_train, monkeypatch, batch)

    # Mock _merge_squash: succeed on WP-001, WP-002; raise on WP-003
    merge_calls: list[str] = []
    def _fake_merge(repo, branch, wp, base_branch="dev"):
        merge_calls.append(wp)
        if wp == "WP-003":
            raise RuntimeError("gh merge failed: 409 conflict")
        return f"merge-sha-{wp}"
    monkeypatch.setattr(wpx_train, "_merge_squash", _fake_merge)

    # Capture _handle_post_merge_failure call args; raise SystemExit to
    # mimic the real function's `emit_result -> sys.exit` behaviour.
    captured: dict[str, Any] = {}
    def _fake_handle(**kwargs):
        captured["kwargs"] = kwargs
        captured["bundle"] = kwargs["bundle"]
        captured["reason"] = kwargs["reason"]
        raise SystemExit(1)
    monkeypatch.setattr(wpx_train, "_handle_post_merge_failure", _fake_handle)

    args = _make_args(tmp_project)
    with pytest.raises(SystemExit) as excinfo:
        wpx_train.cmd_run(args)

    # The post-merge-failure path was reached (exit 1), NOT the outer
    # RuntimeError handler (which would exit 2).
    assert excinfo.value.code == 1, (
        "Expected exit 1 from _handle_post_merge_failure path; got "
        f"{excinfo.value.code}. A code of 2 would mean the merge "
        "exception propagated to the outer except RuntimeError handler "
        "— i.e. HD-003's per-merge try/except wasn't reached."
    )

    # _merge_squash was called for all 3 WPs in order (WP-003 raised)
    assert merge_calls == ["WP-001", "WP-002", "WP-003"]

    # _handle_post_merge_failure was called exactly once
    assert "bundle" in captured, "_handle_post_merge_failure was not called"

    # The partial bundle: entries 1+2 have merge_sha_on_dev populated;
    # entry 3 (the one that failed) does NOT.
    bundle = captured["bundle"]
    assert len(bundle) == 3
    assert bundle[0]["wp"] == "WP-001"
    assert bundle[0]["merge_sha_on_dev"] == "merge-sha-WP-001"
    assert bundle[1]["wp"] == "WP-002"
    assert bundle[1]["merge_sha_on_dev"] == "merge-sha-WP-002"
    assert bundle[2]["wp"] == "WP-003"
    assert bundle[2]["merge_sha_on_dev"] is None, (
        "WP-003 never landed; its merge_sha_on_dev must remain None so "
        "that _handle_post_merge_failure's internal filter "
        "`merged = [e for e in bundle if e.get('merge_sha_on_dev')]` "
        "excludes it from the revert + branch-restore loop."
    )

    # The reason string names the failing WP and the underlying exception
    assert "WP-003" in captured["reason"]
    assert "409 conflict" in captured["reason"]


# ─── Test 2: revert is called with the merged subset ────────────────────


def test_merge_failure_mid_batch_calls_revert_with_merged_subset(
    wpx_train, tmp_project, monkeypatch,
):
    """Allow the real `_handle_post_merge_failure` to run; mock
    `revert_train_on_dev` (and the index-flip / blocker side effects) so
    that only the bundle-handling behaviour is observed.

    The real function filters the bundle internally:
        merged = [e for e in bundle if e.get("merge_sha_on_dev")]
    and ALSO passes the full bundle to `revert_train_on_dev`, which
    re-applies the same filter. The assertion here is that the revert
    function receives the full bundle (its own filter will pick up
    entries 1+2 as the merged subset).
    """
    batch = _eligible_batch(wpx_train, "WP-001", "WP-002", "WP-003")
    _install_happy_path_mocks(wpx_train, monkeypatch, batch)

    def _fake_merge(repo, branch, wp, base_branch="dev"):
        if wp == "WP-003":
            raise RuntimeError("gh merge failed: 502 bad gateway")
        return f"merge-sha-{wp}"
    monkeypatch.setattr(wpx_train, "_merge_squash", _fake_merge)

    # Mock the side effects the real _handle_post_merge_failure performs.
    revert_calls: list[dict[str, Any]] = []
    def _fake_revert(repo, clone_dir, bundle, reason, train_id):
        revert_calls.append({
            "bundle": bundle,
            "reason": reason,
            "train_id": train_id,
        })
        return True, "reverted (mocked)"
    monkeypatch.setattr(wpx_train, "revert_train_on_dev", _fake_revert)

    # restore_branch_with_guard, flip_index_status_via_cli, write_train_blocker
    # are called by _handle_post_merge_failure too. Stub them out to no-op
    # so the test isolates the bundle-flow assertion.
    monkeypatch.setattr(wpx_train, "restore_branch_with_guard",
                        lambda *a, **k: (True, "restored (mocked)"))
    monkeypatch.setattr(wpx_train, "flip_index_status_via_cli",
                        lambda *a, **k: (True, ""))
    monkeypatch.setattr(wpx_train, "write_train_blocker",
                        lambda *a, **k: Path("/tmp/BLOCKER-mock.md"))
    monkeypatch.setattr(wpx_train, "compute_culprit_heuristic",
                        lambda *a, **k: None)
    monkeypatch.setattr(wpx_train, "write_train_run_record",
                        lambda *a, **k: None)
    monkeypatch.setattr(wpx_train, "cleanup_train_state",
                        lambda *a, **k: None)

    args = _make_args(tmp_project)
    with pytest.raises(SystemExit):
        wpx_train.cmd_run(args)

    assert len(revert_calls) == 1, (
        f"Expected revert_train_on_dev to be called exactly once; got "
        f"{len(revert_calls)} calls."
    )

    bundle_passed = revert_calls[0]["bundle"]

    # The full partial bundle is passed; revert_train_on_dev's own internal
    # filter selects the merged subset for the actual revert work.
    assert len(bundle_passed) == 3

    merged_subset = [e for e in bundle_passed if e.get("merge_sha_on_dev")]
    assert [e["wp"] for e in merged_subset] == ["WP-001", "WP-002"], (
        "revert_train_on_dev's internal filter must select exactly the "
        "two merges that actually landed (WP-001, WP-002). WP-003 raised "
        "before its merge_sha_on_dev could be set and must be excluded."
    )


# ─── Test 3: no underlying exception propagates ────────────────────────


def test_merge_failure_does_not_propagate_python_exception(
    wpx_train, tmp_project, monkeypatch,
):
    """The only exception escaping cmd_run for the partial-merge-failure
    path must be SystemExit (raised by _handle_post_merge_failure's
    emit_result). The underlying RuntimeError from _merge_squash must be
    caught inside the merge loop — otherwise it would propagate to the
    outer ``except RuntimeError`` handler and produce ``outcome=error``
    rather than the proper revert path.

    BEFORE HD-003: this test would fail with exit code 2 (the outer
    RuntimeError handler's exit code via emit_result) rather than
    SystemExit(1) from the proper revert path.
    """
    batch = _eligible_batch(wpx_train, "WP-001", "WP-002", "WP-003")
    _install_happy_path_mocks(wpx_train, monkeypatch, batch)

    def _fake_merge(repo, branch, wp, base_branch="dev"):
        if wp == "WP-003":
            raise RuntimeError("BOOM — this string must not leak out")
        return f"merge-sha-{wp}"
    monkeypatch.setattr(wpx_train, "_merge_squash", _fake_merge)

    # Stub _handle_post_merge_failure to a clean SystemExit so the test
    # focuses purely on what exception type escapes cmd_run.
    monkeypatch.setattr(wpx_train, "_handle_post_merge_failure",
                        lambda **kwargs: (_ for _ in ()).throw(SystemExit(1)))

    args = _make_args(tmp_project)
    with pytest.raises(BaseException) as excinfo:
        wpx_train.cmd_run(args)

    # The escaping exception must be SystemExit, NOT the underlying
    # RuntimeError. RuntimeError escape would indicate the merge-loop
    # try/except is missing or mis-scoped.
    assert isinstance(excinfo.value, SystemExit), (
        f"Expected SystemExit from the revert path; got "
        f"{type(excinfo.value).__name__}: {excinfo.value}. A RuntimeError "
        "escape would mean HD-003's per-merge try/except is missing — "
        "the merge failure would propagate to cmd_run's outer "
        "`except RuntimeError` and the partial bundle would never be "
        "reverted."
    )
    assert excinfo.value.code == 1
