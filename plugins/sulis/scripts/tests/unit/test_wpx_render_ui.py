"""Unit tests for the wpx-render-ui step's pure functions (_render_ui.py).

WP-002: render a change's visual contract to UI.html by reusing the
design-system skill's VIEWER mechanism, or emit-nothing-with-a-note when the
change has no visual contract (TDD §2.4, ADR-001/003).

These are the RED tests: written first, against an unimplemented module, so
they fail for the right reason (ImportError / AttributeError), then drive the
GREEN implementation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# The module under test lives next to the other wpx-* helpers. conftest.py
# already puts the scripts dir on sys.path.
import _render_ui  # noqa: E402


# ─── Fixtures: worktrees with / without a visual contract ─────────────────


def _make_visual_worktree(root: Path) -> Path:
    """A worktree carrying a visual contract by convention (design tokens +
    a DESIGN.md). Mirrors what the design-system skill produces; discovery
    must find it generically, not by a change-specific filename."""
    wt = root / "change-with-ui"
    design_dir = wt / "design"
    design_dir.mkdir(parents=True)
    (design_dir / "TOKEN_MAP.css").write_text(
        ":root {\n"
        "  --color-primary: #2563eb;\n"
        "  --color-primary-foreground: #ffffff;\n"
        "  --color-surface-default: #ffffff;\n"
        "  --color-foreground: #111827;\n"
        "  --font-family-base: system-ui, sans-serif;\n"
        "  --radius-interactive: 8px;\n"
        "}\n",
        encoding="utf-8",
    )
    (design_dir / "DESIGN.md").write_text(
        "# Acme Design System\n\nPrimary blue, system font.\n",
        encoding="utf-8",
    )
    return wt


def _make_no_visual_worktree(root: Path) -> Path:
    """A non-user-facing change worktree: a data contract but no visual
    contract / tokens anywhere."""
    wt = root / "change-no-ui"
    src = wt / "src"
    src.mkdir(parents=True)
    (src / "service.openapi.json").write_text(
        json.dumps({"openapi": "3.0.0", "info": {"title": "x", "version": "1"}}),
        encoding="utf-8",
    )
    (wt / "README.md").write_text("# backend-only change\n", encoding="utf-8")
    return wt


# ─── locate_visual_contract — generic discovery (ADR-003) ─────────────────


def test_locate_finds_visual_contract_generically(tmp_path):
    wt = _make_visual_worktree(tmp_path)
    found = _render_ui.locate_visual_contract(wt)
    assert found is not None
    # It found something inside the worktree (the tokens or DESIGN source).
    assert wt in found.parents or found.parent == wt or wt in found.resolve().parents


def test_locate_returns_none_when_absent(tmp_path):
    wt = _make_no_visual_worktree(tmp_path)
    assert _render_ui.locate_visual_contract(wt) is None


def test_discovery_is_generic_not_hardwired(tmp_path):
    """ADR-003: discovery is by convention, never a fixed filename for ONE
    change. The same logic must find a contract under a different change's
    directory layout (different parent dir name, different nesting)."""
    wt = tmp_path / "some-other-change-slug"
    nested = wt / "ui" / "tokens"
    nested.mkdir(parents=True)
    (nested / "TOKEN_MAP.css").write_text(
        ":root { --color-primary: #ef4444; }\n", encoding="utf-8",
    )
    found = _render_ui.locate_visual_contract(wt)
    assert found is not None, "generic discovery must not depend on a fixed path"


# ─── render_ui — present case (reuses the VIEWER mechanism) ───────────────


def test_renders_viewer_when_visual_contract_present(tmp_path):
    wt = _make_visual_worktree(tmp_path)
    result = _render_ui.render_ui(wt)

    assert result["ui_contract"] == "present"
    ui_html = wt / "UI.html"
    assert ui_html.is_file(), "UI.html must be written when a contract is present"
    assert result["path"] == str(ui_html)

    html = ui_html.read_text(encoding="utf-8")
    # Self-contained VIEWER: a full HTML doc with the tokens inlined (no
    # external token fetch — opens from file://).
    assert "<!DOCTYPE html>" in html
    assert "--color-primary" in html, "design tokens must be inlined into the VIEWER"
    assert "#2563eb" in html, "the change's own token VALUES must be rendered"
    # Reuses the design-system VIEWER shape (sections / token showcase), not a
    # bespoke preview.
    assert "viewer" in html.lower()


def test_present_result_is_manifest_ready(tmp_path):
    wt = _make_visual_worktree(tmp_path)
    result = _render_ui.render_ui(wt)
    # The state dict carries exactly what the manifest records for the present
    # case: a state + the path, no note required.
    assert set(result) >= {"ui_contract", "path"}
    assert result["ui_contract"] == "present"


# ─── render_ui — absent case (emit nothing + a note, TDD §2.4) ────────────


def test_emits_none_with_note_when_no_visual_contract(tmp_path):
    wt = _make_no_visual_worktree(tmp_path)
    result = _render_ui.render_ui(wt)

    assert result["ui_contract"] == "none"
    # Emit NOTHING for UI.html — never a broken link.
    assert not (wt / "UI.html").exists(), "no UI.html when there is no visual contract"
    # A human-readable note is recorded so the cockpit shows "no UI contract
    # for this change" rather than a broken link.
    assert result.get("note"), "the none case must carry a plain human note"
    assert "no" in result["note"].lower() and "ui" in result["note"].lower()


def test_absent_case_raises_no_exception(tmp_path):
    """TDD §4.2 'no visual contract' case: never an exception, always a clean
    none-with-note result."""
    wt = _make_no_visual_worktree(tmp_path)
    # Must not raise.
    result = _render_ui.render_ui(wt)
    assert result["ui_contract"] == "none"


# ─── manifest helper — records ui state into the shared manifest ──────────


def test_write_manifest_records_present_state(tmp_path):
    wt = _make_visual_worktree(tmp_path)
    result = _render_ui.render_ui(wt)
    manifest_path = _render_ui.write_manifest(wt, result)

    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["ui_contract"] == "present"
    assert manifest["path"].endswith("UI.html")


def test_write_manifest_records_none_state_with_note(tmp_path):
    wt = _make_no_visual_worktree(tmp_path)
    result = _render_ui.render_ui(wt)
    manifest_path = _render_ui.write_manifest(wt, result)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["ui_contract"] == "none"
    assert manifest["note"]


def test_write_manifest_preserves_existing_keys(tmp_path):
    """The manifest is shared with WP-001 (data_contract). Writing the ui
    state must MERGE, not clobber a sibling renderer's data_contract entry."""
    wt = _make_visual_worktree(tmp_path)
    existing = wt / _render_ui.MANIFEST_NAME
    existing.write_text(
        json.dumps({"data_contract": "present", "data_path": "CONTRACT.html"}),
        encoding="utf-8",
    )
    result = _render_ui.render_ui(wt)
    _render_ui.write_manifest(wt, result)

    manifest = json.loads(existing.read_text(encoding="utf-8"))
    assert manifest["data_contract"] == "present", "must not clobber WP-001's key"
    assert manifest["ui_contract"] == "present"


# ─── path safety — writes stay inside the resolved worktree root ──────────


def test_writes_stay_inside_worktree_root(tmp_path):
    """Armor: artifact writes stay inside the resolved worktree root — UI.html
    and the shared manifest are written under the worktree, never outside it."""
    wt = _make_visual_worktree(tmp_path)
    result = _render_ui.render_ui(wt)
    manifest_path = _render_ui.write_manifest(wt, result)

    wt_resolved = wt.resolve()
    assert wt_resolved in (wt / "UI.html").resolve().parents
    assert wt_resolved in manifest_path.resolve().parents


def test_render_ui_rejects_missing_worktree(tmp_path):
    missing = tmp_path / "does-not-exist"
    with pytest.raises((FileNotFoundError, ValueError)):
        _render_ui.render_ui(missing)


def test_inlined_token_values_cannot_break_out_of_style_block(tmp_path):
    """Armor: a hostile/malformed token value containing a literal </style>
    must not escape the <style> element of the generated VIEWER."""
    wt = tmp_path / "hostile"
    d = wt / "design"
    d.mkdir(parents=True)
    # A value carrying a </style> breakout attempt (no ';' '}' or newline, so
    # the token regex would otherwise capture it whole).
    (d / "TOKEN_MAP.css").write_text(
        ":root { --color-primary: red</style><script>x </script> }\n",
        encoding="utf-8",
    )
    result = _render_ui.render_ui(wt)
    html = (wt / "UI.html").read_text(encoding="utf-8")
    assert result["ui_contract"] == "present"
    # The raw </style> must not survive into the output verbatim.
    assert "</style><script>" not in html

