"""WP-001 — consumer-repo regression: the headline acceptance evidence.

Before this WP, ``/sulis:discover-project`` rolled back EVERY mint in any repo
other than the marketplace repo itself. Three bugs combined on the post-mint
verify path:

1. The verifier invoked ``check-canonical-drift.py --scope <entity> ...`` but
   the detector had no ``--scope`` flag → exit 2 → read as drift → rollback.
2. ``_DEFAULT_DRIFT_DETECTOR`` was cwd-relative
   (``Path("plugins/sulis/scripts/check-canonical-drift.py")``) so it didn't
   resolve from a consumer repo's cwd → python exited before the checker ran.
3. ``inspector.read_root`` recorded the *checked-out* branch via
   ``git branch --show-current`` instead of the repo default — so a mint run
   from a feature branch recorded e.g. ``feat/x`` as ``primary_branch``.

This suite is the first test to drive the **real** verifier end-to-end against
the **real** detector from OUTSIDE the marketplace repo — exactly the
condition that was failing in the wild (``Capsule-Insurance/platform``). It
goes green only when all three fixes land:

- mint must PERSIST (no rollback) — fixes 1 + 2 make the real detector runnable
  and findable from any cwd;
- ``primary_branch == "main"`` (the repo default), NOT the checked-out feature
  branch — fix 3.

The real verifier shells out to the real ``check-canonical-drift.py`` via
``subprocess.run``; ``_DEFAULT_DRIFT_DETECTOR`` (resolved via ``__file__``)
must point at the installed script regardless of the test's cwd.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from _discovery import DiscoveryResult, run_discovery_headless
from _discovery.inferrer import NullConfigurationInferrer
from _discovery.verifier import verify_and_roll_back_on_failure


# ---------------------------------------------------------------------------
# Consumer-repo construction helpers
# ---------------------------------------------------------------------------


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True, timeout=15
    )


def _make_consumer_repo(
    path: Path,
    *,
    default_branch: str = "main",
    set_origin_head: bool = True,
    checkout_feature_branch: str | None = "feat/azure-terraform-foundation",
) -> None:
    """Build a tmp git repo that is NOT the marketplace repo.

    Mirrors the in-the-wild condition: a remote origin whose default branch is
    ``main`` (recorded via ``origin/HEAD``), with a feature branch checked out.

    When ``set_origin_head`` is True, ``refs/remotes/origin/HEAD`` is pointed at
    ``origin/<default_branch>`` (what ``git remote set-head`` / a fresh clone
    establishes). When False, ``origin/HEAD`` is left unset (the fallback path).
    """
    path.mkdir(parents=True, exist_ok=True)

    # Build a bare "remote" so origin/<default_branch> exists to point HEAD at.
    remote = path.parent / f"{path.name}-remote.git"
    _git(["init", "-q", "--bare", "-b", default_branch, str(remote)], cwd=path.parent)

    _git(["init", "-q", "-b", default_branch], cwd=path)
    _git(["config", "user.email", "test@example.com"], cwd=path)
    _git(["config", "user.name", "Test Runner"], cwd=path)
    (path / "README.md").write_text("# consumer fixture repo\n")
    _git(["add", "-A"], cwd=path)
    _git(["commit", "-q", "-m", "init"], cwd=path)
    _git(["remote", "add", "origin", str(remote)], cwd=path)
    _git(["push", "-q", "origin", default_branch], cwd=path)
    # Establish the remote tracking refs.
    _git(["fetch", "-q", "origin"], cwd=path)

    if set_origin_head:
        # Point refs/remotes/origin/HEAD at origin/<default_branch> — the
        # standard "what is the repo default branch" record a fresh clone has.
        _git(["remote", "set-head", "origin", default_branch], cwd=path)

    if checkout_feature_branch is not None:
        _git(["checkout", "-q", "-b", checkout_feature_branch], cwd=path)


def _patch_consuming_repo_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    from _discovery import minter as minter_module

    monkeypatch.setattr(minter_module, "consuming_repo_root", lambda: root.resolve())


def _answers() -> dict:
    return {
        "name": "consumer-app",
        "type": "library",
        "version_files": ["README.md"],
        "description": "A consumer repo adopting Sulis for the regression test.",
        "belongs_to_product_ref": "consumer-product",
        "branch_policy": "trunk",
    }


# ---------------------------------------------------------------------------
# Regression tests
# ---------------------------------------------------------------------------


def test_consumer_repo_mint_persists_and_records_default_branch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Discovery from a consumer repo (NOT the marketplace repo), on a feature
    branch, with cwd OUTSIDE the marketplace repo, drives the REAL verifier.

    Asserts:
      (a) the minted entity file PERSISTS on disk — no rollback;
      (b) the recorded ``primary_branch == "main"`` (the repo default), NOT the
          checked-out ``feat/...`` branch.

    Fails today on all three bug surfaces.
    """
    repo = tmp_path / "consumer"
    _make_consumer_repo(
        repo,
        default_branch="main",
        set_origin_head=True,
        checkout_feature_branch="feat/azure-terraform-foundation",
    )
    _patch_consuming_repo_root(monkeypatch, repo)

    # Run with cwd OUTSIDE the marketplace repo — proves the detector path
    # resolves via __file__, not the process cwd (fix 2). tmp_path is a system
    # temp dir, never inside the marketplace checkout.
    prior_cwd = Path.cwd()
    os.chdir(tmp_path)
    try:
        result = run_discovery_headless(
            repo_path=repo,
            inferrer=NullConfigurationInferrer(),
            answers=_answers(),
            verifier_fn=verify_and_roll_back_on_failure,  # the REAL verifier
        )
    finally:
        os.chdir(prior_cwd)

    assert isinstance(result, DiscoveryResult)
    assert result.ok is True
    assert result.entity_path is not None

    # (a) The mint PERSISTS — the real verify gate did not roll it back.
    assert result.entity_path.exists(), (
        "minted entity was rolled back — the real verify gate failed in a "
        "consumer repo (the in-the-wild bug)"
    )

    # (b) primary_branch is the repo DEFAULT (main), not the checked-out branch.
    proj = json.loads(result.entity_path.read_text())["projects"][0]
    source = json.loads(proj["source"])
    assert source["primary_branch"] == "main", (
        f"primary_branch should be the repo default 'main', not the checked-out "
        f"feature branch; got {source['primary_branch']!r}"
    )
    assert source["primary_branch"] != "feat/azure-terraform-foundation"


def test_consumer_repo_default_branch_falls_back_to_main(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A consumer repo with no ``origin/HEAD`` set records
    ``primary_branch == "main"`` via the fallback.

    Fails today: records the checked-out branch instead of falling back.
    """
    repo = tmp_path / "consumer-no-head"
    _make_consumer_repo(
        repo,
        default_branch="main",
        set_origin_head=False,  # origin/HEAD deliberately unset
        checkout_feature_branch="feat/some-work",
    )
    _patch_consuming_repo_root(monkeypatch, repo)

    result = run_discovery_headless(
        repo_path=repo,
        inferrer=NullConfigurationInferrer(),
        answers={**_answers(), "name": "consumer-app-2"},
        verifier_fn=verify_and_roll_back_on_failure,
    )

    assert result.ok is True
    proj = json.loads(result.entity_path.read_text())["projects"][0]
    source = json.loads(proj["source"])
    assert source["primary_branch"] == "main", (
        f"with origin/HEAD unset, primary_branch must fall back to 'main'; "
        f"got {source['primary_branch']!r}"
    )
