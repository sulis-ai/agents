"""Integration tests for the wpx-render-ui CLI step.

WP-002: the step shares the wpx shape with WP-001 — argv, emit_ok/emit_error
JSON, worktree-only inputs, generic per-change resolution (ADR-001/003). These
tests invoke the real CLI via the run_tool subprocess fixture (the canonical
wpx-* integration pattern), asserting on the emitted JSON and the artifacts +
manifest written into the worktree.
"""

from __future__ import annotations

import json
from pathlib import Path


def _seed_visual_worktree(root: Path) -> Path:
    wt = root / "wt-with-ui"
    d = wt / "design"
    d.mkdir(parents=True)
    (d / "TOKEN_MAP.css").write_text(
        ":root {\n  --color-primary: #0ea5e9;\n  --color-foreground: #0f172a;\n}\n",
        encoding="utf-8",
    )
    (d / "DESIGN.md").write_text("# Sky design\n", encoding="utf-8")
    return wt


def _seed_no_visual_worktree(root: Path) -> Path:
    wt = root / "wt-no-ui"
    s = wt / "api"
    s.mkdir(parents=True)
    (s / "openapi.json").write_text('{"openapi": "3.0.0"}', encoding="utf-8")
    return wt


def test_cli_emits_ok_and_manifest_records_ui_state(run_tool, tmp_path):
    wt = _seed_visual_worktree(tmp_path)
    result = run_tool(
        "wpx-render-ui", "render", "--worktree", str(wt),
    )
    assert result.ok, f"expected ok JSON, got: {result.stdout}\n{result.stderr}"
    assert result.data["ui_contract"] == "present"

    # UI.html produced, self-contained.
    ui_html = wt / "UI.html"
    assert ui_html.is_file()
    assert "<!DOCTYPE html>" in ui_html.read_text(encoding="utf-8")

    # Manifest records the ui state generically.
    manifest = json.loads(
        (wt / "CONTRACT.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["ui_contract"] == "present"
    assert manifest["path"].endswith("UI.html")


def test_cli_no_visual_contract_records_none_no_html(run_tool, tmp_path):
    wt = _seed_no_visual_worktree(tmp_path)
    result = run_tool(
        "wpx-render-ui", "render", "--worktree", str(wt),
    )
    # Never an error / exception for the non-user-facing case (TDD §2.4).
    assert result.ok, f"none case must still emit ok JSON, got: {result.stderr}"
    assert result.data["ui_contract"] == "none"
    assert result.data.get("note")

    # No UI.html — never a broken link.
    assert not (wt / "UI.html").exists()

    # Manifest records none + the note.
    manifest = json.loads(
        (wt / "CONTRACT.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["ui_contract"] == "none"
    assert manifest["note"]


def test_cli_errors_on_missing_worktree(run_tool, tmp_path):
    missing = tmp_path / "nope"
    result = run_tool("wpx-render-ui", "render", "--worktree", str(missing))
    assert result.json is not None, "must emit structured JSON even on error"
    assert result.ok is False
    assert result.returncode == 1  # expected user/data error, not a crash
