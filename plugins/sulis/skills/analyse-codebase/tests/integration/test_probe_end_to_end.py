"""End-to-end integration tests — real binaries against real fixtures."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from probe.orchestrator import OrchestratorConfig, run as run_orchestrator
from probe.render import render_all


pytestmark = pytest.mark.integration


def _run_probe(workspace: Path, output_dir: Path, project: str) -> dict:
    cfg = OrchestratorConfig(
        root=workspace, project=project, output_dir=output_dir,
    )
    result = run_orchestrator(cfg)
    render_all(cfg, render_html=True)
    return {
        "workspaces": [w.name for w in result.workspaces],
        "errors": result.errors,
    }


def test_ts_simple_full_run(make_workspace, tmp_path, integration_tools):
    """ts_simple fixture: 3 classes, 1 hotspot, 1 wrapper. node_modules excluded."""
    workspace = make_workspace("ts_simple")
    output_dir = tmp_path / "out"

    result = _run_probe(workspace, output_dir, "ts_simple")
    assert not result["errors"]

    # All phase JSONs produced
    for phase_file in ("1_1_stack.json", "1_2_capabilities.json",
                       "1_5_coupling.json", "1_6_complexity.json",
                       "1_7_wrappers.json"):
        assert (output_dir / phase_file).exists(), f"{phase_file} missing"

    # Capabilities found
    caps = json.loads((output_dir / "1_2_capabilities.json").read_text())
    items = caps["payload"]["items"]
    assert len(items) >= 3
    class_names = {i["name"] for i in items if i["kind"] == "class"}
    assert "UserService" in class_names
    assert "PaymentProcessor" in class_names

    # node_modules excluded
    for item in items:
        assert "node_modules" not in item["file"], (
            f"node_modules leaked into capabilities: {item['file']}"
        )


def test_ts_simple_wrapper_rot_detected(make_workspace, tmp_path, integration_tools):
    """PaymentProcessorV2 should be flagged as candidate wrapper rot."""
    workspace = make_workspace("ts_simple")
    output_dir = tmp_path / "out"
    _run_probe(workspace, output_dir, "ts_simple")

    wrappers = json.loads((output_dir / "1_7_wrappers.json").read_text())
    candidates = wrappers["payload"]["candidates"]
    names = [c["wrapper_class"] for c in candidates]
    assert "PaymentProcessorV2" in names

    # Should be flagged as internal (NOT external-adapter)
    v2 = next(c for c in candidates if c["wrapper_class"] == "PaymentProcessorV2")
    assert v2["wrapped_target"] == "PaymentProcessor"
    assert v2["is_external_adapter_candidate"] is False


def test_py_simple_excludes_venv(make_workspace, tmp_path, integration_tools):
    """v0.7.2 regression test: .venv/ must NOT appear in capability/complexity outputs."""
    workspace = make_workspace("py_simple")
    output_dir = tmp_path / "out"
    _run_probe(workspace, output_dir, "py_simple")

    # Phase-output JSONs (not the manifest, which persists config containing the
    # word ".venv" as an exclusion glob).
    phase_files = [
        "1_2_capabilities.json", "1_6_complexity.json",
        "1_5_coupling.json", "1_7_wrappers.json",
    ]
    for fname in phase_files:
        path = output_dir / fname
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        assert ".venv/" not in text, f"v0.7.2 regression: .venv/ leaked into {fname}"
        assert "ShouldNotAppear" not in text, (
            f"Excluded class ShouldNotAppear leaked into {fname}"
        )


def test_py_simple_bare_keyword_patterns(make_workspace, tmp_path, integration_tools):
    """v0.7.2 regression test: bare-keyword Python patterns produce results."""
    workspace = make_workspace("py_simple")
    output_dir = tmp_path / "out"
    _run_probe(workspace, output_dir, "py_simple")

    caps = json.loads((output_dir / "1_2_capabilities.json").read_text())
    items = caps["payload"]["items"]
    assert any(i["kind"] == "class" and i["name"] == "Order" for i in items)
    assert any(i["kind"] == "function" and i["name"] == "place_order" for i in items)


def test_monorepo_pnpm_three_workspaces(make_workspace, tmp_path, integration_tools):
    """pnpm-workspace fixture should yield 3 workspaces."""
    workspace = make_workspace("monorepo_pnpm")
    output_dir = tmp_path / "out"
    result = _run_probe(workspace, output_dir, "monorepo")

    workspaces = sorted(result["workspaces"])
    assert workspaces == ["packages/api", "packages/shared", "packages/web"]

    # System manifest reflects all 3
    sm = json.loads((output_dir / "00_system_manifest.json").read_text())
    assert len(sm["workspaces"]) == 3


def test_empty_fixture_runs_without_error(make_workspace, tmp_path, integration_tools):
    """Empty repo: probe runs successfully with mostly-empty outputs."""
    workspace = make_workspace("empty")
    output_dir = tmp_path / "out"
    result = _run_probe(workspace, output_dir, "empty")

    assert not result["errors"]
    # 1.1 stack should exist with zeros
    stack = json.loads((output_dir / "1_1_stack.json").read_text())
    assert stack["payload"]["total_files"] == 0


def test_end_to_end_produces_both_md_and_html(make_workspace, tmp_path, integration_tools):
    """The pipeline writes both .md and .html in .architecture/{project}/."""
    workspace = make_workspace("ts_simple")
    output_dir = tmp_path / "out"

    cfg = OrchestratorConfig(
        root=workspace, project="ts_simple", output_dir=output_dir,
    )
    run_orchestrator(cfg)
    rendered = render_all(cfg, render_html=True)

    assert rendered.markdown_path is not None
    assert rendered.markdown_path.exists()
    assert rendered.html_path is not None
    assert rendered.html_path.exists()

    html_content = rendered.html_path.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html_content
    assert "Code Intelligence" in html_content
    assert "<nav" in html_content
    assert "<style>" in html_content
    assert "<script>" in html_content
