"""Tests for `_prune_cache` — defence-in-depth cache pruner (#49).

Keeps the newest N (default 3) cached `sulis-ai-agents/sulis/<version>`
directories and removes older ones, using the SAME portable numeric
version comparison as `_version_pick` (never lexical, never `sort -V`).

Dry-run by default; deletion only under `--force`. These tests operate
ENTIRELY on a fake cache built under `tmp_path` — they MUST never touch
the real `~/.claude/plugins/cache`.
"""

from __future__ import annotations

from pathlib import Path

import _prune_cache as pc


def _fake_cache(tmp_path: Path, versions: list[str]) -> Path:
    """Build ~/.claude/plugins/cache/sulis-ai-agents/sulis/<v>/ dirs."""
    base = tmp_path / "cache" / "sulis-ai-agents" / "sulis"
    for v in versions:
        d = base / v / "scripts"
        d.mkdir(parents=True)
        (d / "marker.txt").write_text(v)
    return tmp_path / "cache"


class TestPlanPrune:
    def test_keeps_newest_n_by_numeric_order(self, tmp_path):
        # Lexical sort would keep 0.98.0/0.99.0 over 0.126.0 — numeric must not.
        cache = _fake_cache(
            tmp_path, ["0.98.0", "0.99.0", "0.100.0", "0.126.0", "0.45.0"]
        )
        plan = pc.plan_prune(cache, keep=3)
        assert plan.keep == ["0.126.0", "0.100.0", "0.99.0"]
        assert sorted(plan.remove) == ["0.45.0", "0.98.0"]

    def test_nothing_removed_when_under_limit(self, tmp_path):
        cache = _fake_cache(tmp_path, ["0.126.0", "0.100.0"])
        plan = pc.plan_prune(cache, keep=3)
        assert plan.remove == []
        assert set(plan.keep) == {"0.126.0", "0.100.0"}

    def test_single_version_kept(self, tmp_path):
        cache = _fake_cache(tmp_path, ["0.126.0"])
        plan = pc.plan_prune(cache, keep=3)
        assert plan.remove == []
        assert plan.keep == ["0.126.0"]

    def test_missing_cache_yields_empty_plan(self, tmp_path):
        plan = pc.plan_prune(tmp_path / "does-not-exist", keep=3)
        assert plan.keep == []
        assert plan.remove == []

    def test_non_version_dirs_ignored(self, tmp_path):
        cache = _fake_cache(tmp_path, ["0.126.0", "0.98.0"])
        # stray non-version dir alongside real versions
        (cache / "sulis-ai-agents" / "sulis" / "scratch").mkdir()
        plan = pc.plan_prune(cache, keep=1)
        assert plan.keep == ["0.126.0"]
        assert plan.remove == ["0.98.0"]


class TestApplyPrune:
    def test_dry_run_deletes_nothing(self, tmp_path):
        cache = _fake_cache(tmp_path, ["0.98.0", "0.100.0", "0.126.0", "0.45.0"])
        plan = pc.plan_prune(cache, keep=2)
        removed = pc.apply_prune(plan, force=False)
        # Dry-run returns what WOULD be removed but leaves disk intact.
        assert sorted(removed) == ["0.45.0", "0.98.0"]
        sulis = cache / "sulis-ai-agents" / "sulis"
        assert (sulis / "0.98.0").exists()
        assert (sulis / "0.45.0").exists()
        assert (sulis / "0.126.0").exists()

    def test_force_deletes_old_keeps_new(self, tmp_path):
        cache = _fake_cache(tmp_path, ["0.98.0", "0.100.0", "0.126.0", "0.45.0"])
        plan = pc.plan_prune(cache, keep=2)
        removed = pc.apply_prune(plan, force=True)
        assert sorted(removed) == ["0.45.0", "0.98.0"]
        sulis = cache / "sulis-ai-agents" / "sulis"
        assert not (sulis / "0.98.0").exists()
        assert not (sulis / "0.45.0").exists()
        assert (sulis / "0.126.0").exists()
        assert (sulis / "0.100.0").exists()

    def test_force_under_limit_is_noop(self, tmp_path):
        cache = _fake_cache(tmp_path, ["0.126.0", "0.100.0"])
        plan = pc.plan_prune(cache, keep=3)
        removed = pc.apply_prune(plan, force=True)
        assert removed == []
        sulis = cache / "sulis-ai-agents" / "sulis"
        assert (sulis / "0.126.0").exists()
        assert (sulis / "0.100.0").exists()
