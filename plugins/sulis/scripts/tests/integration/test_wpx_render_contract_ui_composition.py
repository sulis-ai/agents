"""Cross-renderer composition test for the shared contract manifest.

WP-AUTO-MANIFEST (Step 10.5 remediation): wpx-render-contract and
wpx-render-ui were designed to share ONE manifest file so the cockpit-wiring
WP (WP-003) can read both contracts from a single source — but they wrote to
DIFFERENT filenames (CONTRACT.manifest.json vs manifest.json) AND the
data-contract renderer clobbered rather than merged. Result: the
``data_contract`` and ``ui_contract`` keys ended up in two separate files, so
neither renderer saw the other's keys.

This drives BOTH real CLIs against a single worktree carrying BOTH a data
contract (a *.jsonld ServiceSpec) AND a visual contract (design/TOKEN_MAP.css),
in BOTH run orders, and asserts the SINGLE resulting manifest carries BOTH the
``data_contract`` and ``ui_contract`` keys. It is the regression guard for the
shared-manifest contract WP-003 consumes.
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
_RENDER_CONTRACT = _SCRIPTS_DIR / "wpx-render-contract"
_RENDER_UI = _SCRIPTS_DIR / "wpx-render-ui"

# The single canonical manifest both renderers share. WP-003 (the cockpit)
# consumes exactly this filename.
MANIFEST_NAME = "CONTRACT.manifest.json"


def _seed_dual_contract_worktree(root: Path) -> Path:
    """A worktree carrying BOTH a data contract AND a visual contract."""
    wt = root / "dual-worktree"
    wt.mkdir()
    # Data contract — a structured ServiceSpec the data renderer recognises.
    shutil.copy(_FIXTURES / "fixtureA_catalog.jsonld", wt / "contract.jsonld")
    # Visual contract — design tokens the UI renderer recognises (ADR-003).
    design = wt / "design"
    design.mkdir()
    (design / "TOKEN_MAP.css").write_text(
        ":root {\n  --color-primary: #0ea5e9;\n}\n", encoding="utf-8"
    )
    (design / "DESIGN.md").write_text("# Sky design\n", encoding="utf-8")
    return wt


def _run(renderer: Path, *extra: str, worktree: Path) -> dict:
    # wpx-render-contract takes --worktree directly; wpx-render-ui needs the
    # "render" subcommand. The caller passes any leading subcommand via *extra.
    argv = [sys.executable, str(renderer), *extra, "--worktree", str(worktree)]
    proc = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, (
        f"{renderer.name} failed: stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    return json.loads(proc.stdout)


def _assert_single_shared_manifest(wt: Path) -> None:
    """Exactly one manifest file, carrying BOTH contract keys."""
    # The legacy split-brain filename must NOT exist alongside the canonical one.
    assert not (wt / "manifest.json").exists(), (
        "split-brain: a second manifest.json was written; both renderers must "
        "share the single canonical CONTRACT.manifest.json"
    )
    manifest_path = wt / MANIFEST_NAME
    assert manifest_path.is_file(), f"missing shared manifest {MANIFEST_NAME}"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "data_contract" in manifest, (
        f"data_contract key lost from shared manifest: {sorted(manifest)}"
    )
    assert "ui_contract" in manifest, (
        f"ui_contract key lost from shared manifest: {sorted(manifest)}"
    )


def test_both_renderers_share_one_manifest_contract_then_ui(tmp_path):
    wt = _seed_dual_contract_worktree(tmp_path)
    _run(_RENDER_CONTRACT, worktree=wt)
    _run(_RENDER_UI, "render", worktree=wt)
    _assert_single_shared_manifest(wt)


def test_both_renderers_share_one_manifest_ui_then_contract(tmp_path):
    wt = _seed_dual_contract_worktree(tmp_path)
    _run(_RENDER_UI, "render", worktree=wt)
    _run(_RENDER_CONTRACT, worktree=wt)
    _assert_single_shared_manifest(wt)
