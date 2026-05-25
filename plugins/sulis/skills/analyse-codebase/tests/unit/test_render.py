"""Unit tests for render.py — Markdown and HTML output assertions."""

from __future__ import annotations

import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

from probe.render import _md_to_html, _slug, render_html_doc, render_markdown


def test_slug_handles_special_chars():
    assert _slug("packages/api") == "packages-api"
    assert _slug(".") == "root"
    assert _slug("foo_bar-baz") == "foo_bar-baz"


def test_md_to_html_escapes_html():
    out = _md_to_html("<script>alert(1)</script>")
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_md_to_html_handles_inline_code_and_bold():
    out = _md_to_html("This has `code` and **bold** in it.")
    assert "<code>code</code>" in out
    assert "<strong>bold</strong>" in out


def test_md_to_html_preserves_newlines_as_br():
    out = _md_to_html("line one\nline two")
    assert "<br>" in out


class _TagCounter(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags: dict[str, int] = {}

    def handle_starttag(self, tag, attrs):
        self.tags[tag] = self.tags.get(tag, 0) + 1


def test_html_well_formed(tmp_path: Path, monkeypatch):
    """Smoke test: write a minimal system_manifest + 1.1 stack, render HTML."""
    raw = tmp_path / "raw"
    raw.mkdir()

    # System manifest
    (raw / "00_system_manifest.json").write_text(__import__("json").dumps({
        "project": "test",
        "workspaces": [{"name": ".", "path": str(tmp_path), "style": "single-repo", "manifest_path": None}],
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T00:00:01+00:00",
        "tool_versions": {"scc": "3.7.0"},
    }))

    # Phase 1.1
    (raw / "1_1_stack.json").write_text(__import__("json").dumps({
        "phase": "1.1", "tool": "scc",
        "started_at": "2026-01-01T00:00:00+00:00",
        "duration_ms": 50,
        "warnings": [],
        "payload": {
            "languages": {"Python": {"files": 10, "code": 100, "blanks": 5, "comments": 3, "complexity_total": 20}},
            "primary_language": "Python",
            "total_files": 10, "total_loc": 100, "total_complexity": 20,
            "frameworks": [], "manifest_files_found": [],
        },
    }))

    from probe.orchestrator import OrchestratorConfig
    cfg = OrchestratorConfig(
        root=tmp_path, project="test", output_dir=raw,
    )

    html_path = render_html_doc(cfg)
    assert html_path is not None
    content = html_path.read_text(encoding="utf-8")

    # Smoke checks
    assert "<!DOCTYPE html>" in content
    assert "<style>" in content
    assert "<script>" in content
    parser = _TagCounter()
    parser.feed(content)
    assert parser.tags.get("section", 0) >= 1
    assert parser.tags.get("nav", 0) >= 1
