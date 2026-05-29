"""Review-gate orchestrator test (WP-003, TDD §5 design-time half).

``wpx-render-review-gate`` is the thin orchestrator that renders a change's
CONTRACT.html + UI.html at the pre-dispatch review gate by composing the two
shipped renderers (WP-001 wpx-render-contract, WP-002 wpx-render-ui) against
one worktree. It does not re-implement rendering; it drives both with
subprocess discipline and emits the standard wpx JSON.

This drives the REAL orchestrator against a worktree carrying both a data
contract and a visual contract, and asserts: exit 0, ok:true, both artifacts
written, and the single shared manifest carries BOTH contract halves — i.e.
the gate leaves the worktree in exactly the state the cockpit (WP-003 routes)
then consumes.
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
_REVIEW_GATE = _SCRIPTS_DIR / "wpx-render-review-gate"

MANIFEST_NAME = "CONTRACT.manifest.json"


def _seed_dual_contract_worktree(root: Path) -> Path:
    wt = root / "review-gate-worktree"
    wt.mkdir()
    shutil.copy(_FIXTURES / "fixtureA_catalog.jsonld", wt / "contract.jsonld")
    design = wt / "design"
    design.mkdir()
    (design / "TOKEN_MAP.css").write_text(
        ":root {\n  --color-primary: #0ea5e9;\n}\n", encoding="utf-8"
    )
    (design / "DESIGN.md").write_text("# Sky design\n", encoding="utf-8")
    return wt


def test_review_gate_renders_both_artifacts_and_shared_manifest(tmp_path):
    wt = _seed_dual_contract_worktree(tmp_path)

    proc = subprocess.run(
        [sys.executable, str(_REVIEW_GATE), "--worktree", str(wt)],
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, (
        f"review-gate failed: stdout={proc.stdout}\nstderr={proc.stderr}"
    )
    result = json.loads(proc.stdout)
    assert result["ok"] is True, result

    # Both rendered artifacts exist.
    assert (wt / "CONTRACT.html").is_file(), "CONTRACT.html not rendered"
    assert (wt / "UI.html").is_file(), "UI.html not rendered (this fixture has a visual contract)"

    # The single shared manifest carries BOTH halves — the exact state the
    # cockpit's contract endpoints consume (WP-003).
    manifest = json.loads((wt / MANIFEST_NAME).read_text(encoding="utf-8"))
    assert "data_contract" in manifest, sorted(manifest)
    assert "ui_contract" in manifest, sorted(manifest)


def test_review_gate_errors_cleanly_on_missing_worktree(tmp_path):
    missing = tmp_path / "does-not-exist"
    proc = subprocess.run(
        [sys.executable, str(_REVIEW_GATE), "--worktree", str(missing)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode == 1, proc.stdout
    result = json.loads(proc.stdout)
    assert result["ok"] is False
