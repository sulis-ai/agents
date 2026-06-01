"""TrainTestbed — end-to-end fixture for wpx-train cmd_run failure-path tests.

Provisions a real local bare git repo as ``origin``, a FakeGHClient that
implements the HD-005 ``GHClient`` Protocol against the bare repo, and
named failure-injection methods covering the six paths cmd_run must
tolerate (rebase conflict, CI red/timeout, mid-batch merge fail,
deploy timeout/fail, health/smoke fail).

Consumed by `test_train_failure_paths.py`. Imports the wpx-train script
via `importlib.machinery.SourceFileLoader` (the script has no .py
extension; see test_wpx_train_partial_merge_failure.py for the same
pattern).

This file is HD-002. The injection seam it consumes comes from HD-005.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent

# Make _wpxlib importable.
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ───────────────────────────────────────────────────────────────────────
# Module loading — wpx-train and _wpxlib are loaded once per session.
# ───────────────────────────────────────────────────────────────────────


def _load_wpx_train_module():
    """Load scripts/wpx-train as a Python module under name 'wpx_train_module'.

    The script has no .py extension; SourceFileLoader is needed.
    Idempotent — re-importing returns the cached module.
    """
    if "wpx_train_module" in sys.modules:
        return sys.modules["wpx_train_module"]
    script_path = _SCRIPTS_DIR / "wpx-train"
    loader = importlib.machinery.SourceFileLoader(
        "wpx_train_module", str(script_path),
    )
    spec = importlib.util.spec_from_loader("wpx_train_module", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["wpx_train_module"] = module
    spec.loader.exec_module(module)
    return module


# ───────────────────────────────────────────────────────────────────────
# FakeGHClient — implements the HD-005 GHClient Protocol.
# ───────────────────────────────────────────────────────────────────────


@dataclass
class _CIConfig:
    """Simulated CI verdict + how many polls must elapse before it resolves."""

    verdict: str = "green"  # "green" | "failed" | "timeout"
    poll_count_before_resolve: int = 0


@dataclass
class _DeployConfig:
    """Simulated deploy-workflow verdict + URL + poll behaviour."""

    verdict: str = "green"  # "green" | "failed" | "timeout"
    url: str = "https://example.invalid/deploy/123"


class FakeGHClient:
    """GHClient implementation backed by a local bare git repo.

    Read methods (branch_sha, ref_sha, compare, branch_exists) query the
    bare repo via git plumbing — so production-shaped data flows through
    them. Mutation methods (merge, delete_branch) update the bare repo's
    refs directly, simulating GitHub's `POST /merges` and `DELETE
    /git/refs/heads/{branch}` behaviour.

    Pure-simulation methods (check_runs, deploy_runs) return whatever the
    test configured via `set_ci_verdict` / `set_deploy_verdict`.

    Failure injection: each method consults a `fail_next` dict keyed by
    operation name; when populated, the next call raises the recorded
    exception (then the entry is consumed). The `force_fail` dict
    persists for every subsequent call until cleared. Tests use named
    helpers on `TrainTestbed` rather than poking these directly.
    """

    def __init__(self, bare_repo: Path) -> None:
        self.bare_repo = bare_repo
        # Per-operation transient failures (consumed on next call):
        self.fail_next: dict[str, Exception] = {}
        # Per-operation persistent failures (until cleared):
        self.force_fail: dict[str, Exception] = {}
        # WP branches the test wants to fail at merge time, keyed by branch name:
        self.fail_merge_for: set[str] = set()
        # CI simulation
        self.ci = _CIConfig()
        # Deploy simulation
        self.deploy = _DeployConfig()
        # Call log for assertions
        self.calls: list[tuple[str, tuple, dict]] = []

    # ── helpers ──────────────────────────────────────────────────────

    def _git(self, *args: str, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command in the bare repo. Bare-repo invocations use
        `--git-dir` form (the bare repo IS the git dir).
        """
        return subprocess.run(  # noqa: S603
            ["git", "--git-dir", str(self.bare_repo), *args],
            capture_output=True, text=True, check=check,
        )

    def _maybe_raise(self, op: str) -> None:
        """Raise injected failure for ``op`` if configured."""
        if op in self.fail_next:
            exc = self.fail_next.pop(op)
            raise exc
        if op in self.force_fail:
            raise self.force_fail[op]

    def _record(self, op: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append((op, args, kwargs))

    # ── GHClient Protocol methods ────────────────────────────────────

    def check_runs(self, repo: str, branch: str) -> dict:
        self._record("check_runs", repo, branch)
        self._maybe_raise("check_runs")
        # Eligibility uses this to decide strict-ci; in strict=False mode
        # the value isn't gating. Return a green check-run by default.
        return {
            "check_runs": [
                {"status": "completed", "conclusion": "success",
                 "name": "ci", "html_url": "https://example.invalid/run/1"},
            ],
        }

    def branch_sha(self, repo: str, branch: str) -> str:
        self._record("branch_sha", repo, branch)
        self._maybe_raise("branch_sha")
        try:
            proc = self._git("rev-parse", branch)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"gh branch-sha failed for {branch}: {exc.stderr}",
            ) from None
        return proc.stdout.strip()

    def ref_sha(self, repo: str, ref: str) -> str:
        self._record("ref_sha", repo, ref)
        self._maybe_raise("ref_sha")
        try:
            proc = self._git("rev-parse", ref)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"gh ref-sha failed for {ref}: {exc.stderr}",
            ) from None
        return proc.stdout.strip()

    def compare(self, repo: str, base: str, head: str) -> dict:
        self._record("compare", repo, base, head)
        self._maybe_raise("compare")
        # Use git merge-base to determine ancestry; map to GitHub
        # compare API status field semantics.
        try:
            base_sha = self._git("rev-parse", base).stdout.strip()
            head_sha = self._git("rev-parse", head).stdout.strip()
        except subprocess.CalledProcessError:
            return {}
        if base_sha == head_sha:
            return {"status": "identical"}
        # base..head: commits in head not in base (head is ahead)
        ahead = self._git(
            "rev-list", "--count", f"{base}..{head}", check=False,
        ).stdout.strip()
        behind = self._git(
            "rev-list", "--count", f"{head}..{base}", check=False,
        ).stdout.strip()
        a = int(ahead or "0")
        b = int(behind or "0")
        if a > 0 and b == 0:
            return {"status": "ahead"}
        if a == 0 and b > 0:
            return {"status": "behind"}
        if a > 0 and b > 0:
            return {"status": "diverged"}
        return {"status": "identical"}

    def merge(self, repo: str, base: str, head: str, commit_message: str) -> str:
        self._record("merge", repo, base, head, commit_message)
        self._maybe_raise("merge")
        # Test-specific per-branch failure (used by fail_merge_for(wp)).
        if head in self.fail_merge_for:
            raise RuntimeError(
                f"gh merges failed: 409 simulated conflict on {head}",
            )
        # Simulate squash-merge by updating base's ref to point at head.
        # This is a fast-forward in the bare repo, which is the
        # post-rebase state the train hands us (head's history sits on
        # top of the most recent base). A "real" squash-merge would
        # produce one synthetic commit per merge; for our test purposes
        # the ref movement is what downstream assertions care about.
        try:
            head_sha = self._git("rev-parse", head).stdout.strip()
        except subprocess.CalledProcessError as exc:
            raise RuntimeError(
                f"gh merges failed: head ref unknown: {exc.stderr}",
            ) from None
        self._git("update-ref", f"refs/heads/{base}", head_sha)
        return head_sha

    def deploy_runs(self, repo: str, workflow: str, commit: str) -> list[dict]:
        self._record("deploy_runs", repo, workflow, commit)
        self._maybe_raise("deploy_runs")
        # Map the configured deploy verdict onto the gh-run-list shape.
        if self.deploy.verdict == "timeout":
            # No runs found → _poll_deploy interprets this as "still
            # spinning up" and loops until cap. Tests configure a short
            # cap to trigger the timeout path quickly.
            return []
        conclusion = (
            "success" if self.deploy.verdict == "green" else self.deploy.verdict
        )
        return [{
            "databaseId": 999,
            "status": "completed",
            "conclusion": conclusion,
            "createdAt": "2026-05-23T00:00:00Z",
            "url": self.deploy.url,
        }]

    def delete_branch(self, repo: str, branch: str) -> None:
        self._record("delete_branch", repo, branch)
        # Best-effort — match the production helper's swallow-errors shape.
        self._git("update-ref", "-d", f"refs/heads/{branch}", check=False)

    def branch_exists(self, repo: str, branch: str) -> bool:
        self._record("branch_exists", repo, branch)
        if "branch_exists" in self.force_fail:
            return False  # treat forced failure as "branch missing"
        proc = self._git("rev-parse", "--verify", f"refs/heads/{branch}",
                         check=False)
        return proc.returncode == 0 and bool(proc.stdout.strip())

    def list_matching_branches(self, repo: str, pattern: str) -> list[dict]:
        """Real-git-backed implementation of the GHClient method.

        Uses ``git for-each-ref`` against the bare repo so existing integration
        tests (which build out branches via the real-git fixture) see the same
        shape RealGHClient would produce against origin.
        """
        self._record("list_matching_branches", repo, pattern)
        if "list_matching_branches" in self.force_fail:
            return []
        # Pattern is like ``feat/wp-008-*`` → for-each-ref takes
        # ``refs/heads/feat/wp-008-*`` and emits one line per match.
        ref_pattern = f"refs/heads/{pattern}"
        proc = self._git(
            "for-each-ref",
            "--format=%(refname:short)%09%(committerdate:iso8601-strict)",
            ref_pattern,
            check=False,
        )
        if proc.returncode != 0 or not proc.stdout.strip():
            return []
        results: list[dict] = []
        for line in proc.stdout.strip().splitlines():
            parts = line.split("\t", 1)
            if not parts:
                continue
            name = parts[0]
            committerdate = parts[1] if len(parts) > 1 else ""
            results.append({"name": name, "committerdate": committerdate})
        return results

    def clone(self, repo: str, dest: Path) -> tuple[int, str]:
        self._record("clone", repo, dest)
        self._maybe_raise("clone")
        # Real git clone against the bare repo so the train's
        # subsequent `git fetch origin <branch>` calls find real refs.
        proc = subprocess.run(  # noqa: S603
            ["git", "clone", "--depth", "100", str(self.bare_repo), str(dest)],
            capture_output=True, text=True,
        )
        return proc.returncode, proc.stderr


# ───────────────────────────────────────────────────────────────────────
# TrainTestbed — the public fixture surface.
# ───────────────────────────────────────────────────────────────────────


@dataclass
class TrainTestbed:
    """End-to-end harness for wpx-train cmd_run failure-path tests.

    Construct via the `train_testbed` pytest fixture; the fixture wires
    up:

      - A real local bare git repo (origin) at `tmp/origin.git`.
      - A working clone at `tmp/workspace` (the "founder's repo root").
      - An empty `.architecture/<project>/work-packages/INDEX.md` skeleton.
      - A `FakeGHClient` swapped into `_wpxlib._default_gh_client`.
      - Side-effect helpers (flip_index_status_via_cli, write_train_blocker,
        revert_train_on_dev, restore_branch_with_guard) monkeypatched
        to record-and-no-op so assertions can read the recorded calls
        without subprocess-spawning the side-effect tools.

    Tests use the seed_* helpers to provision branches/WP files/INDEX
    rows, the fail_*/timeout_* helpers to inject failures, then call
    `run_train()` which returns the cmd_run result + exit code.

    All module-level monkeypatches (failure injection on _poll_ci /
    _poll_deploy / _poll_health / _run_smoke) are routed through the
    pytest ``monkeypatch`` fixture so they auto-restore between tests —
    critical because the wpx_train module is module-cached and would
    otherwise leak patched callables across tests in the same session.
    """

    tmp_path: Path
    bare_repo: Path
    workspace: Path
    project: str
    arch_dir: Path
    wp_dir: Path
    train_runs_dir: Path
    index_md: Path
    gh: FakeGHClient
    monkeypatch: pytest.MonkeyPatch
    # Records of calls to side-effect helpers (monkeypatched in fixture)
    index_flips: list[dict] = field(default_factory=list)
    blocker_files: list[Path] = field(default_factory=list)
    revert_calls: list[dict] = field(default_factory=list)
    restore_calls: list[dict] = field(default_factory=list)
    smoke_result: tuple[str, str] = ("PASS", "")
    health_result: str = "healthy"
    # Per-WP slug map (set by seed_wp_branch)
    slugs: dict[str, str] = field(default_factory=dict)

    # ── seeding ──────────────────────────────────────────────────────

    def _git_bare(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(  # noqa: S603
            ["git", "--git-dir", str(self.bare_repo), *args],
            capture_output=True, text=True, check=True,
        )

    def _git(self, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(  # noqa: S603
            ["git", *args],
            cwd=cwd or self.workspace,
            capture_output=True, text=True, check=True,
        )

    def seed_wp_branch(
        self,
        wp_id: str,
        slug: str,
        *,
        files: dict[str, str] | None = None,
    ) -> str:
        """Create a feature branch for ``wp_id`` with one commit.

        The branch name follows the production convention from
        `_branch_name`: ``feat/wp-{id-lower-no-WP-prefix}-{slug}``.

        Files default to a single touch on ``wp/<wp_id>.txt`` with
        unique contents (so the branch genuinely diverges from dev).

        Returns the branch name.
        """
        files = files or {f"wp/{wp_id}.txt": f"{wp_id} content\n"}
        branch = f"feat/wp-{wp_id.lower().removeprefix('wp-')}-{slug}"
        # Work in a worktree off the bare repo so we don't disturb the
        # main workspace clone.
        scratch = self.tmp_path / f"_scratch-{wp_id}"
        subprocess.run(  # noqa: S603
            ["git", "clone", str(self.bare_repo), str(scratch)],
            capture_output=True, text=True, check=True,
        )
        self._git("config", "user.email", "test@example.com", cwd=scratch)
        self._git("config", "user.name", "Test", cwd=scratch)
        self._git("checkout", "-b", branch, cwd=scratch)
        for rel_path, contents in files.items():
            target = scratch / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(contents)
            self._git("add", rel_path, cwd=scratch)
        self._git("commit", "-m", f"feat({wp_id.lower()}): seed", cwd=scratch)
        self._git("push", "origin", branch, cwd=scratch)
        shutil.rmtree(scratch, ignore_errors=True)
        self.slugs[wp_id] = slug
        # Seed the WP file (used by _wp_slug_from_file)
        wp_file = self.wp_dir / f"{wp_id}-{slug}.md"
        wp_file.write_text(f"# {wp_id}\n")
        return branch

    def seed_index_with_wps(
        self,
        wp_specs: list[tuple[str, str]],
        status: str = "step-7-complete",
    ) -> None:
        """Write INDEX.md with one WP row per (wp_id, title) tuple.

        Default status is ``step-7-complete`` — eligible for the train.
        Tests that want non-eligible WPs pass a different status.
        """
        lines = [
            "# Work Package Index",
            "",
            "## Orchestrator Config",
            "",
            "max_parallel: 3",
            "",
            "## Work Packages",
            "",
            "| ID | Title | Primitive | Status | Depends | Blocks | Token | TDD § |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for wp_id, title in wp_specs:
            lines.append(
                f"| {wp_id} | {title} | create | {status} | — | — | 3k | 2.1 |",
            )
        self.index_md.write_text("\n".join(lines) + "\n")

    # ── failure injection ───────────────────────────────────────────

    def fail_rebase(self, wp_id: str) -> None:
        """Inject a rebase conflict for ``wp_id``.

        Adds a conflicting commit to dev that the WP's branch can't
        cleanly rebase onto. Concretely: writes a different content to
        the same file the WP branch modified, commits it to dev, pushes.
        Subsequent rebase of ``wp_id``'s branch will conflict on that file.
        """
        # The branch name itself isn't needed here — we're modifying dev,
        # not the WP branch. Conflict surfaces when wpx-train rebases the
        # WP branch onto the new dev head.
        scratch = self.tmp_path / "_dev-scratch"
        subprocess.run(  # noqa: S603
            ["git", "clone", str(self.bare_repo), str(scratch)],
            capture_output=True, text=True, check=True,
        )
        self._git("config", "user.email", "test@example.com", cwd=scratch)
        self._git("config", "user.name", "Test", cwd=scratch)
        self._git("checkout", "dev", cwd=scratch)
        target = scratch / "wp" / f"{wp_id}.txt"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("competing content from dev\n")
        self._git("add", str(target.relative_to(scratch)), cwd=scratch)
        self._git("commit", "-m", f"chore: competing change for {wp_id}",
                  cwd=scratch)
        self._git("push", "origin", "dev", cwd=scratch)
        shutil.rmtree(scratch, ignore_errors=True)

    def fail_ci(self) -> None:
        """Configure check-runs to return failed.

        Patches ``_poll_ci`` on the wpx_train module via pytest's
        monkeypatch so the override is auto-restored on test teardown
        (the wpx_train module is session-cached; direct setattrs would
        leak across tests).
        """
        self.gh.ci.verdict = "failed"
        wpx = _load_wpx_train_module()
        self.monkeypatch.setattr(
            wpx, "_poll_ci",
            lambda repo, branch, interval, cap: "failed",
        )

    def timeout_ci(self) -> None:
        """Configure CI poll to time out."""
        self.gh.ci.verdict = "timeout"
        wpx = _load_wpx_train_module()
        self.monkeypatch.setattr(
            wpx, "_poll_ci",
            lambda repo, branch, interval, cap: "timeout",
        )

    def fail_merge(self, wp_id: str) -> None:
        """Inject a merge failure on ``wp_id``'s branch."""
        slug = self.slugs[wp_id]
        branch = f"feat/wp-{wp_id.lower().removeprefix('wp-')}-{slug}"
        # rebase rewrites the branch name; the rebased branch keeps the
        # original name (force-pushed) so we still key on the original.
        self.gh.fail_merge_for.add(branch)

    def fail_deploy(self) -> None:
        """Configure deploy verdict to be 'failed'."""
        self.gh.deploy.verdict = "failed"
        wpx = _load_wpx_train_module()
        self.monkeypatch.setattr(
            wpx, "_poll_deploy",
            lambda *a, **k: ("failed", self.gh.deploy.url),
        )

    def timeout_deploy(self) -> None:
        """Configure deploy verdict to be 'timeout' (paused path)."""
        self.gh.deploy.verdict = "timeout"
        wpx = _load_wpx_train_module()
        self.monkeypatch.setattr(
            wpx, "_poll_deploy",
            lambda *a, **k: ("timeout", self.gh.deploy.url),
        )

    def fail_health(self) -> None:
        """Configure health poll to return 'unhealthy'."""
        self.health_result = "unhealthy"

    def fail_smoke(self) -> None:
        """Configure smoke command to FAIL."""
        self.smoke_result = ("FAIL — exit 1", "smoke failed")

    # ── run + assertions ────────────────────────────────────────────

    def make_args(self, **overrides: Any) -> SimpleNamespace:
        """Construct an args Namespace for ``cmd_run`` with defaults.

        Tests pass ``staging_url``, ``smoke_cmd``, deploy caps, etc.
        via overrides.
        """
        base = {
            "project": self.project,
            "repo_root": str(self.workspace),
            "repo": "acme/test-repo",
            "base_branch": "dev",
            "force": True,
            "max_batch_size": 10,
            "deploy_workflow": "deploy.yml",
            "deploy_poll_interval": 1,
            "deploy_cap": 1,
            "staging_url": None,
            "smoke_cmd": "",
            "ci_poll_interval": 1,
            "strict_ci": False,
            "health_path": "/",
        }
        base.update(overrides)
        return SimpleNamespace(**base)

    def run_train(self, args: SimpleNamespace) -> tuple[dict, int]:
        """Run cmd_run and capture its emitted result + exit code.

        cmd_run calls emit_result(...) which raises SystemExit. The
        result dict is written to wpx-train's stdout as JSON via
        emit_ok. For test introspection we don't need to parse the
        JSON; we read the train-runs YAML record on disk instead.

        Returns (parsed_record, exit_code). If no record was written
        (eligibility produced no batch, etc.), returns ({}, exit_code).
        """
        wpx = _load_wpx_train_module()
        try:
            wpx.cmd_run(args)
            exit_code = 0
        except SystemExit as exc:
            exit_code = int(exc.code or 0)
        record = self.read_latest_train_record()
        return record, exit_code

    def read_latest_train_record(self) -> dict:
        """Return the most recent train YAML record as a dict.

        Trivial YAML parser sufficient for the fields ``write_train_run_record``
        emits (string + null + numeric scalars; a single ``bundle`` list).
        """
        yamls = sorted(self.train_runs_dir.glob("train-*.yaml"),
                       key=lambda p: p.stat().st_mtime, reverse=True)
        if not yamls:
            return {}
        text = yamls[0].read_text()
        out: dict[str, Any] = {}
        bundle: list[dict] = []
        cur_item: dict | None = None
        in_bundle = False
        for raw in text.splitlines():
            if raw.startswith("bundle:"):
                in_bundle = True
                continue
            if in_bundle and raw.startswith("  - wp:"):
                if cur_item is not None:
                    bundle.append(cur_item)
                cur_item = {"wp": raw.split(":", 1)[1].strip()}
                continue
            if in_bundle and raw.startswith("    ") and cur_item is not None:
                k, _, v = raw.strip().partition(":")
                v = v.strip()
                cur_item[k.strip()] = None if v == "null" else v
                continue
            if not in_bundle and ":" in raw:
                k, _, v = raw.partition(":")
                v = v.strip().strip('"')
                out[k.strip()] = None if v == "null" else v
        if cur_item is not None:
            bundle.append(cur_item)
        if bundle:
            out["bundle"] = bundle
        return out

    def _branch_for(self, wp_id: str) -> str:
        slug = self.slugs[wp_id]
        return f"feat/wp-{wp_id.lower().removeprefix('wp-')}-{slug}"

    def _merge_sha_for(self, wp_id: str) -> str | None:
        """Return the SHA dev was updated to when wp_id was merged.

        Looks through FakeGHClient.calls for the merge() invocation whose
        ``head`` matches wp_id's branch; if found, looks up what SHA
        FakeGHClient.merge() returned (which is also what dev was set to,
        because the fake fast-forwards dev to head's SHA).
        """
        branch = self._branch_for(wp_id)
        for op, args, _kwargs in self.gh.calls:
            if op != "merge":
                continue
            # merge(repo, base, head, commit_message) — match by head
            if len(args) >= 3 and args[2] == branch:
                # The SHA the merge mapped to: we re-derive by checking
                # the bare repo at the time of recording. Since dev now
                # has the merged head's content, walk through the dev
                # history looking for a commit whose tree mirrors what
                # the test would expect. Simpler: dev's history contains
                # the WP's commit by content; check it's reachable from
                # dev via `git log` searching for the seed commit message.
                return self._find_commit_with_msg(
                    f"feat({wp_id.lower()}): seed",
                )
        return None

    def _find_commit_with_msg(self, needle: str) -> str | None:
        """Find a commit on dev whose message contains ``needle``."""
        proc = subprocess.run(  # noqa: S603
            ["git", "--git-dir", str(self.bare_repo),
             "log", "dev", "--format=%H %s"],
            capture_output=True, text=True, check=False,
        )
        if proc.returncode != 0:
            return None
        for line in proc.stdout.splitlines():
            sha, _, msg = line.partition(" ")
            if needle in msg:
                return sha
        return None

    def assert_merged_on_dev(self, wp_id: str) -> None:
        """Assert that ``wp_id``'s seed commit is reachable from dev.

        The feature branch ref is deleted post-merge (matching the real
        ``DELETE /git/refs/heads/{branch}`` call), so we can't check
        ancestry via the branch name. Instead, search dev's log for the
        WP's seed commit message (produced by seed_wp_branch).
        """
        sha = self._find_commit_with_msg(f"feat({wp_id.lower()}): seed")
        assert sha is not None, (
            f"{wp_id}'s seed commit not found in dev log — merge did not land. "
            f"dev SHA: "
            f"{subprocess.run(['git', '--git-dir', str(self.bare_repo), 'rev-parse', 'dev'], capture_output=True, text=True).stdout.strip()}"
        )

    def assert_not_merged_on_dev(self, wp_id: str) -> None:
        sha = self._find_commit_with_msg(f"feat({wp_id.lower()}): seed")
        assert sha is None, (
            f"{wp_id}'s seed commit IS in dev log (SHA {sha}) but should not be"
        )

    def assert_index_flip(self, wp_id: str, to_status: str) -> None:
        """Assert that flip_index_status_via_cli was called for wp_id."""
        matching = [
            f for f in self.index_flips
            if f["wp"] == wp_id and f["to_status"] == to_status
        ]
        assert matching, (
            f"Expected INDEX flip for {wp_id} → {to_status}; recorded flips: "
            f"{self.index_flips}"
        )


# ───────────────────────────────────────────────────────────────────────
# pytest fixture
# ───────────────────────────────────────────────────────────────────────


@pytest.fixture
def train_testbed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TrainTestbed:
    """End-to-end TrainTestbed bound to ``tmp_path``.

    Sets up the bare repo + workspace + GHClient swap + side-effect
    monkeypatches; tears everything down via the fixture scope.
    """
    project = "test-train-project"
    workspace = tmp_path / "workspace"
    bare_repo = tmp_path / "origin.git"
    arch_dir = workspace / ".architecture" / project
    wp_dir = arch_dir / "work-packages"
    train_runs_dir = arch_dir / "train-runs"
    index_md = wp_dir / "INDEX.md"

    # Provision the bare origin + a working clone with a baseline commit
    workspace.mkdir(parents=True)
    wp_dir.mkdir(parents=True)
    train_runs_dir.mkdir(parents=True)

    seed_dir = tmp_path / "_seed"
    subprocess.run(["git", "init", "-q", "-b", "dev", str(seed_dir)],  # noqa: S603,S607
                  capture_output=True, text=True, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"],  # noqa: S603,S607
                  cwd=seed_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"],  # noqa: S603,S607
                  cwd=seed_dir, check=True)
    (seed_dir / "README.md").write_text("# test\n")
    subprocess.run(["git", "add", "."], cwd=seed_dir, check=True)  # noqa: S603,S607
    subprocess.run(["git", "commit", "-q", "-m", "initial"],  # noqa: S603,S607
                  cwd=seed_dir, check=True)
    subprocess.run(["git", "clone", "-q", "--bare", str(seed_dir), str(bare_repo)],  # noqa: S603,S607
                  check=True)
    shutil.rmtree(seed_dir, ignore_errors=True)

    # Make a working clone (the "founder's repo root"). Tests don't need
    # it for git operations — cmd_run clones into a temp dir itself —
    # but having one keeps `paths.repo_root` realistic if any helper
    # inspects it.
    subprocess.run(["git", "clone", "-q", str(bare_repo), str(workspace / ".git-clone")],  # noqa: S603,S607
                  capture_output=True, text=True, check=True)

    # Construct the fake GH client + swap into _wpxlib's default.
    import _wpxlib
    fake = FakeGHClient(bare_repo=bare_repo)
    monkeypatch.setattr(_wpxlib, "_default_gh_client", fake)

    # Load the wpx_train module + monkeypatch side-effect helpers to
    # record-and-no-op. The recorded calls drive testbed.* assertions.
    wpx = _load_wpx_train_module()

    testbed = TrainTestbed(
        tmp_path=tmp_path,
        bare_repo=bare_repo,
        workspace=workspace,
        project=project,
        arch_dir=arch_dir,
        wp_dir=wp_dir,
        train_runs_dir=train_runs_dir,
        index_md=index_md,
        gh=fake,
        monkeypatch=monkeypatch,
    )

    # Side-effect monkeypatches: instead of shelling out to wpx-index /
    # wpx-blocker, record the intent on the testbed so tests can
    # assert on it directly.
    def _record_flip(scripts_dir, paths, wp_id, to_status, expected=None):
        testbed.index_flips.append({
            "wp": wp_id, "to_status": to_status, "expected": expected,
        })
        return True, ""

    def _record_wp_blocker(*args, **kwargs):
        testbed.blocker_files.append(testbed.wp_dir / f"BLOCKER-{kwargs.get('wp_id', 'unknown')}.md")
        return True, ""

    def _record_train_blocker(paths, train_id, reason, bundle,
                              suspected_wp_id=None, evidence=""):
        path = testbed.wp_dir / f"BLOCKER-{train_id}.md"
        # Actually write a stub file so the test can read it
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"# BLOCKER-{train_id}\n\n{reason}\n")
        testbed.blocker_files.append(path)
        return path

    def _record_revert(repo, clone_dir, bundle, reason, train_id):
        testbed.revert_calls.append({
            "bundle": bundle, "reason": reason, "train_id": train_id,
        })
        return True, "reverted (testbed)"

    def _record_restore(repo, clone_dir, branch, pre_sha, expected_sha):
        testbed.restore_calls.append({
            "branch": branch, "pre_sha": pre_sha, "expected_sha": expected_sha,
        })
        return True, "restored (testbed)"

    monkeypatch.setattr(wpx, "flip_index_status_via_cli", _record_flip)
    monkeypatch.setattr(wpx, "write_wp_blocker_via_cli", _record_wp_blocker)
    monkeypatch.setattr(wpx, "write_train_blocker", _record_train_blocker)
    monkeypatch.setattr(wpx, "revert_train_on_dev", _record_revert)
    monkeypatch.setattr(wpx, "restore_branch_with_guard", _record_restore)
    # Smoke / health helpers go through wpx-train module-level imports
    monkeypatch.setattr(wpx, "_run_smoke",
                        lambda cmd, cwd: testbed.smoke_result)
    monkeypatch.setattr(wpx, "_poll_health",
                        lambda url, cap: testbed.health_result)

    yield testbed
    # tmp_path teardown is handled by pytest automatically.
