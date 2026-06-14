"""Unit tests for the wpx-wp CLI.

Covers the WP-005 `branch-name` emitter (the single source of truth for the
MINTED WP branch — ADR-001) plus a characterisation test pinning that the
existing `read-frontmatter` subcommand is unaffected by the addition.
"""
from __future__ import annotations

import importlib.util
import io
import json
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
_WPX_WP = _SCRIPTS / "wpx-wp"


def _load_wpx_wp():
    loader = SourceFileLoader("wpx_wp_mod", str(_WPX_WP))
    spec = importlib.util.spec_from_loader("wpx_wp_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


wpx = _load_wpx_wp()


def _run(subcommand_argv: list[str]) -> dict:
    """Parse argv through build_parser, dispatch the handler, capture JSON."""
    args = wpx.build_parser().parse_args(subcommand_argv)
    fn = wpx.HANDLERS[args.subcommand]
    buf = io.StringIO()
    code = None
    with redirect_stdout(buf):
        try:
            fn(args)
        except SystemExit as exc:
            code = exc.code
    out = buf.getvalue().strip()
    data = json.loads(out) if out else {}
    data["_exit"] = code
    return data


def _seed_wp(wp_dir: Path, wp_id: str, slug: str) -> None:
    wp_dir.mkdir(parents=True, exist_ok=True)
    (wp_dir / f"{wp_id}-{slug}.md").write_text(f"# {wp_id}\n", encoding="utf-8")


# ─── WP-005: branch-name emitter ──────────────────────────────────────────


def test_branch_name_subcommand_emits_scoped_then_legacy(tmp_path, monkeypatch):
    """branch-name emits the scoped wp/{scope}/ shape when in a change, and the
    legacy feat/... shape when no change scope resolves."""
    wp_dir = tmp_path / ".architecture" / "p" / "work-packages"
    _seed_wp(wp_dir, "WP-001", "foo")
    argv = ["branch-name", "--wp", "WP-001", "--project", "p",
            "--repo-root", str(tmp_path)]

    # Scoped — change identity resolves.
    monkeypatch.setattr(wpx, "current_change_scope", lambda repo_root: "fix-x")
    res = _run(argv)
    assert res.get("ok") is True
    assert res["data"]["branch"] == "wp/fix-x/wp-001-foo"

    # Legacy — no change scope.
    monkeypatch.setattr(wpx, "current_change_scope", lambda repo_root: None)
    res = _run(argv)
    assert res["data"]["branch"] == "feat/wp-001-foo"


def test_branch_name_subcommand_prefixed_id_clean_tail(tmp_path, monkeypatch):
    """WP-001 (CH-5DMB1N): branch-name emits a CLEAN tail for a prefixed id.

    A prefixed `CH-…-WP-NNN` WP file resolves to `wp/{scope}/wp-NNN-{slug}`,
    NOT the doubled `wp/{scope}/wp-ch-5dmb1n-wp-001-{slug}` — the shared
    `wp_nnn_suffix` strips the change-handle prefix. Retained alongside the
    legacy bare-id `test_branch_name_subcommand_emits_scoped_then_legacy`.
    """
    wp_dir = tmp_path / ".architecture" / "p" / "work-packages"
    _seed_wp(wp_dir, "CH-5DMB1N-WP-001", "foo")
    argv = ["branch-name", "--wp", "CH-5DMB1N-WP-001", "--project", "p",
            "--repo-root", str(tmp_path)]

    monkeypatch.setattr(wpx, "current_change_scope", lambda repo_root: "fix-x")
    res = _run(argv)
    assert res.get("ok") is True
    assert res["data"]["branch"] == "wp/fix-x/wp-001-foo"

    monkeypatch.setattr(wpx, "current_change_scope", lambda repo_root: None)
    res = _run(argv)
    assert res["data"]["branch"] == "feat/wp-001-foo"


def test_branch_name_subcommand_missing_wp_file_errors(tmp_path, monkeypatch):
    """No WP file → structured error, non-zero exit."""
    monkeypatch.setattr(wpx, "current_change_scope", lambda repo_root: None)
    res = _run(["branch-name", "--wp", "WP-404", "--project", "p",
                "--repo-root", str(tmp_path)])
    assert res.get("ok") is False
    assert res["_exit"] not in (0, None)


# ─── Regression oracle — existing subcommand unaffected ───────────────────


def test_read_frontmatter_unaffected(tmp_path):
    """The pre-existing read-frontmatter subcommand still works after the
    branch-name addition (characterisation)."""
    wp_dir = tmp_path / ".architecture" / "p" / "work-packages"
    wp_dir.mkdir(parents=True, exist_ok=True)
    (wp_dir / "WP-001-foo.md").write_text(
        "---\nid: WP-001\ntitle: Demo\n---\nbody\n", encoding="utf-8",
    )
    res = _run(["read-frontmatter", "--wp", "WP-001", "--field", "title",
                "--project", "p", "--repo-root", str(tmp_path)])
    assert res.get("ok") is True
    assert res["data"]["value"] == "Demo"
