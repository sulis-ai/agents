"""Integration test for the wpx-render-contract CLI step (WP-001).

Drives the real CLI against a tmp worktree and asserts the standard wpx
emit_ok JSON on stdout (exit 0) plus the written artifacts (CONTRACT.html +
manifest) — the CLI contract WP-003 (the cockpit) consumes.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent
_FIXTURES = _HERE.parent / "fixtures" / "render_contract"
_RENDERER = _SCRIPTS_DIR / "wpx-render-contract"


def test_cli_emits_ok_and_writes_artifacts(tmp_path):
    worktree = tmp_path / "worktree"
    worktree.mkdir()
    shutil.copy(_FIXTURES / "fixtureA_catalog.jsonld", worktree / "contract.jsonld")

    proc = subprocess.run(
        [sys.executable, str(_RENDERER), "--worktree", str(worktree)],
        capture_output=True,
        text=True,
        timeout=60,
    )

    # exit 0 + standard emit_ok JSON on stdout.
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    result = json.loads(proc.stdout)
    assert result["ok"] is True
    data = result["data"]

    # the result names what was produced.
    contract_html = Path(data["contract_html"])
    manifest_path = Path(data["manifest"])
    assert contract_html.exists()
    assert manifest_path.exists()

    # artifacts written inside the worktree (path-safety invariant).
    assert worktree in contract_html.parents
    assert worktree in manifest_path.parents

    # manifest is well-formed JSON carrying the data-contract format.
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["data_contract"]["format"] == "servicespec"

    # the rendered HTML is self-contained (no external stylesheet/script refs).
    html = contract_html.read_text(encoding="utf-8")
    assert "<html" in html.lower()
    assert "src=\"http" not in html and "href=\"http" not in html


def test_cli_rejects_missing_worktree(tmp_path):
    proc = subprocess.run(
        [sys.executable, str(_RENDERER), "--worktree", str(tmp_path / "nope")],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 1
    result = json.loads(proc.stdout)
    assert result["ok"] is False
