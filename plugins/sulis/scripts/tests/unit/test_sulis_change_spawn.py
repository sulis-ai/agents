"""Unit tests for WP-004 — `sulis-change start --spawn` composition.

Exercises cmd_start's recon + pre-prompt + launcher wiring and the
_build_change_pre_prompt helper. The launcher (_terminal_launcher) and
recon (_change_context) are mocked so no real terminal spawns and no git
worktree is created. cmd_start's own branch/worktree/metadata steps are
mocked too — this WP tests the composition, not the upstream mechanics.

sulis-change has no .py extension, so it's imported via importlib from its
file path.
"""

from __future__ import annotations

import argparse
import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
from unittest import mock

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2]
_SC_PATH = _SCRIPTS / "sulis-change"


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SC_PATH))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


sc = _load_sulis_change()

_GOOD_ULID = "01HYQC71000000000000000000"


def _args(spawn: bool, repo_root: Path) -> argparse.Namespace:
    return argparse.Namespace(
        repo_root=str(repo_root),
        slug="introduce-payments",
        primitive="create",
        intent="add subscription billing",
        base=None,
        spawn=spawn,
    )


class _ExitOK(Exception):
    """Raised by the emit_ok stub to halt cmd_start and capture the payload."""

    def __init__(self, data):
        self.data = data


def _patch_cmd_start_internals(repo_root: Path, worktree: Path):
    """Patch cmd_start's upstream mechanics + emit_ok; return a context stack.

    Returns (captured, patches) where captured is a dict the emit_ok stub
    fills with the JSON `data`, and patches is a list of mock context
    managers to enter.
    """
    captured: dict = {}

    def _emit_ok_stub(data=None, warnings=None, exit_code=0):
        captured["data"] = data
        raise _ExitOK(data)

    patches = [
        mock.patch.object(sc, "_resolve_repo_root", return_value=repo_root),
        mock.patch.object(sc, "compose_change_branch",
                          return_value="change/create-introduce-payments"),
        mock.patch.object(sc, "_run", return_value=(1, "", "")),  # branch absent
        mock.patch.object(sc, "change_worktree_path", return_value=worktree),
        mock.patch.object(sc, "git_worktree_add", return_value=(True, "ok")),
        mock.patch.object(sc, "generate_change_ulid", return_value=_GOOD_ULID),
        mock.patch.object(sc, "ulid_handle", return_value="CH-01HYQC"),
        mock.patch.object(sc, "write_change_metadata"),
        mock.patch.object(sc, "_log"),
        mock.patch.object(sc, "emit_ok", side_effect=_emit_ok_stub),
    ]
    return captured, patches


def _run_cmd_start(args, captured, patches, extra_patches):
    from contextlib import ExitStack
    with ExitStack() as stack:
        for p in patches + extra_patches:
            stack.enter_context(p)
        with pytest.raises(_ExitOK):
            sc.cmd_start(args)
    return captured["data"]


def test_cmd_start_always_writes_recon(tmp_path):
    repo_root = tmp_path
    worktree = tmp_path / "wt"
    worktree.mkdir()
    captured, patches = _patch_cmd_start_internals(repo_root, worktree)
    ctx_path = tmp_path / "CONTEXT.md"
    wcc = mock.patch.object(sc, "write_change_context", return_value=ctx_path)
    data = _run_cmd_start(_args(spawn=False, repo_root=repo_root), captured, patches, [wcc])
    assert data["context_md_path"] == str(ctx_path)


def test_cmd_start_default_no_spawn(tmp_path):
    repo_root = tmp_path
    worktree = tmp_path / "wt"
    worktree.mkdir()
    captured, patches = _patch_cmd_start_internals(repo_root, worktree)
    wcc = mock.patch.object(sc, "write_change_context", return_value=tmp_path / "C.md")
    lct = mock.patch.object(sc, "launch_change_terminal")
    data = _run_cmd_start(_args(spawn=False, repo_root=repo_root), captured, patches, [wcc, lct])
    assert data["spawn_result"] is None


def test_cmd_start_with_spawn_invokes_launcher(tmp_path):
    repo_root = tmp_path
    worktree = tmp_path / "wt"
    worktree.mkdir()
    captured, patches = _patch_cmd_start_internals(repo_root, worktree)
    spawned = {"status": "spawned", "pid": 1, "terminal_app_used": "Terminal.app",
               "script_path": "/x", "session_json_path": "/y", "error": None}
    wcc = mock.patch.object(sc, "write_change_context", return_value=tmp_path / "C.md")
    lct = mock.patch.object(sc, "launch_change_terminal", return_value=spawned)
    data = _run_cmd_start(_args(spawn=True, repo_root=repo_root), captured, patches, [wcc, lct])
    assert data["spawn_result"]["status"] == "spawned"


def test_cmd_start_with_spawn_passes_pre_prompt(tmp_path):
    repo_root = tmp_path
    worktree = tmp_path / "wt"
    worktree.mkdir()
    captured, patches = _patch_cmd_start_internals(repo_root, worktree)
    ctx_path = tmp_path / "C.md"
    spawned = {"status": "spawned", "pid": 1, "terminal_app_used": "Terminal.app",
               "script_path": "/x", "session_json_path": "/y", "error": None}
    wcc = mock.patch.object(sc, "write_change_context", return_value=ctx_path)
    lct = mock.patch.object(sc, "launch_change_terminal", return_value=spawned)
    from contextlib import ExitStack
    with ExitStack() as stack:
        for p in patches + [wcc, lct]:
            stack.enter_context(p)
        mock_launch = stack.enter_context(
            mock.patch.object(sc, "launch_change_terminal", return_value=spawned))
        with pytest.raises(_ExitOK):
            sc.cmd_start(_args(spawn=True, repo_root=repo_root))
    pre_prompt = mock_launch.call_args.kwargs["pre_prompt"]
    assert isinstance(pre_prompt, str) and pre_prompt
    assert "CH-01HYQC" in pre_prompt
    assert str(ctx_path) in pre_prompt


def test_cmd_start_recon_runs_before_spawn(tmp_path):
    repo_root = tmp_path
    worktree = tmp_path / "wt"
    worktree.mkdir()
    captured, patches = _patch_cmd_start_internals(repo_root, worktree)
    order: list[str] = []
    spawned = {"status": "spawned", "pid": 1, "terminal_app_used": "Terminal.app",
               "script_path": "/x", "session_json_path": "/y", "error": None}

    def _recon(*a, **k):
        order.append("recon")
        return tmp_path / "C.md"

    def _spawn(*a, **k):
        order.append("spawn")
        return spawned

    wcc = mock.patch.object(sc, "write_change_context", side_effect=_recon)
    lct = mock.patch.object(sc, "launch_change_terminal", side_effect=_spawn)
    _run_cmd_start(_args(spawn=True, repo_root=repo_root), captured, patches, [wcc, lct])
    assert order == ["recon", "spawn"]


def test_cmd_start_with_spawn_failure_still_emits_ok(tmp_path):
    repo_root = tmp_path
    worktree = tmp_path / "wt"
    worktree.mkdir()
    captured, patches = _patch_cmd_start_internals(repo_root, worktree)
    failed = {"status": "failed", "pid": None, "terminal_app_used": None,
              "script_path": "/x", "session_json_path": "", "error": "no terminal app"}
    wcc = mock.patch.object(sc, "write_change_context", return_value=tmp_path / "C.md")
    lct = mock.patch.object(sc, "launch_change_terminal", return_value=failed)
    # _ExitOK raised means emit_ok was reached (exit 0 path), not emit_error.
    data = _run_cmd_start(_args(spawn=True, repo_root=repo_root), captured, patches, [wcc, lct])
    assert data["spawn_result"]["status"] == "failed"


def test_cmd_start_stamps_initial_recon_stage(tmp_path):
    """cmd_start writes the initial 'recon' stage into state.json."""
    repo_root = tmp_path
    worktree = tmp_path / "wt"
    worktree.mkdir()
    captured, patches = _patch_cmd_start_internals(repo_root, worktree)
    wcc = mock.patch.object(sc, "write_change_context", return_value=tmp_path / "C.md")
    stamped: dict = {}

    def _stamp(change_id, stage):
        stamped["change_id"] = change_id
        stamped["stage"] = stage
        return tmp_path / "state.json"

    wcs = mock.patch.object(sc, "write_change_stage", side_effect=_stamp)
    _run_cmd_start(_args(spawn=False, repo_root=repo_root), captured, patches, [wcc, wcs])
    assert stamped["change_id"] == _GOOD_ULID
    assert stamped["stage"] == "recon"


def test_build_change_pre_prompt_includes_handle_and_intent():
    body = sc._build_change_pre_prompt(
        change_id=_GOOD_ULID, handle="CH-01HYQC", slug="introduce-payments",
        intent="add subscription billing", primitive="create",
        context_md_path=Path("/home/x/.sulis/changes/abc/CONTEXT.md"),
    )
    assert "CH-01HYQC" in body
    assert "add subscription billing" in body
    assert "/home/x/.sulis/changes/abc/CONTEXT.md" in body


def test_build_change_pre_prompt_does_not_contain_heredoc_tag():
    body = sc._build_change_pre_prompt(
        change_id=_GOOD_ULID, handle="CH-01HYQC", slug="x-y",
        intent="do a thing", primitive="create",
        context_md_path=Path("/tmp/CONTEXT.md"),
    )
    assert "SULIS_PROMPT_EOF" not in body
