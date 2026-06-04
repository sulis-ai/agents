"""End-to-end CLI tests for `sulis-working-set` (the agent-triggered Working Set)."""

from __future__ import annotations

from pathlib import Path


class TestWorkingSetCli:
    def test_init_creates_then_is_idempotent(self, tmp_path: Path, run_tool) -> None:
        r = run_tool("sulis-working-set", "init", "--stem", "feat-add-login",
                     "--repo-root", str(tmp_path), "--intent", "users can sign in",
                     "--at", "2026-06-04T09:00:00Z")
        assert r.ok, r.stderr
        assert r.data["created"] is True
        ws = tmp_path / ".changes" / "feat-add-login.WORKING-SET.md"
        assert ws.exists()
        assert "users can sign in" in ws.read_text()

        # second init must NOT clobber (idempotent)
        ws.write_text(ws.read_text() + "\nHAND-EDIT\n")
        r2 = run_tool("sulis-working-set", "init", "--stem", "feat-add-login",
                      "--repo-root", str(tmp_path))
        assert r2.ok
        assert r2.data["created"] is False
        assert "HAND-EDIT" in ws.read_text()  # preserved

    def test_show_returns_content(self, tmp_path: Path, run_tool) -> None:
        run_tool("sulis-working-set", "init", "--stem", "feat-x",
                 "--repo-root", str(tmp_path), "--at", "2026-06-04T09:00:00Z")
        r = run_tool("sulis-working-set", "show", "--stem", "feat-x",
                     "--repo-root", str(tmp_path))
        assert r.ok
        assert "## 1. Problem" in r.data["content"]

    def test_show_missing_is_error(self, tmp_path: Path, run_tool) -> None:
        r = run_tool("sulis-working-set", "show", "--stem", "nope",
                     "--repo-root", str(tmp_path))
        assert r.returncode == 1
        assert "init" in (r.error or "")

    def test_log_appends(self, tmp_path: Path, run_tool) -> None:
        run_tool("sulis-working-set", "init", "--stem", "feat-x",
                 "--repo-root", str(tmp_path), "--at", "2026-06-04T09:00:00Z")
        r = run_tool("sulis-working-set", "log", "--stem", "feat-x",
                     "--repo-root", str(tmp_path), "--message", "locked the approach",
                     "--at", "2026-06-04T10:00:00Z")
        assert r.ok, r.stderr
        content = (tmp_path / ".changes" / "feat-x.WORKING-SET.md").read_text()
        assert "- 2026-06-04T10:00:00Z — locked the approach" in content
