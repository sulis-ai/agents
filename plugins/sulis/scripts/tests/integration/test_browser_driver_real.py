"""Integration: the deterministic browser driver drives a REAL browser.

This is the proof the unit tests can't give — they inject a fake transport. Here
`_default_browser` opens an actual (headless) page and asserts against real DOM,
closing the `/sulis:prove` "blocked: real browser drive never exercised" gap.

Playwright is an OPTIONAL extra (stdlib-only contract): this test SKIPS when it's
absent, so CI stays stdlib-only — but it runs (and proves the real path) wherever
`uv sync --extra browser && playwright install chromium` has been done. No
network, no auth — it drives a local file:// page.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("playwright")  # skip cleanly when the optional extra is absent

from _scenario_dispatch import _default_browser  # noqa: E402


def _page(tmp_path: Path) -> str:
    html = tmp_path / "page.html"
    html.write_text(
        "<html><body><h1>Dashboard</h1>"
        "<input id='email'/><button id='go'>Go</button></body></html>",
        encoding="utf-8",
    )
    return html.as_uri()


def test_visible_assert_holds_against_real_dom(tmp_path: Path) -> None:
    r = _default_browser(_page(tmp_path), [], {"visible": "Dashboard"})
    assert r.ok, r.detail


def test_visible_assert_misses_against_real_dom(tmp_path: Path) -> None:
    r = _default_browser(_page(tmp_path), [], {"visible": "No Such Text Anywhere"})
    assert not r.ok, r.detail


def test_url_contains_assert_against_real_page(tmp_path: Path) -> None:
    r = _default_browser(_page(tmp_path), [], {"url_contains": "page.html"})
    assert r.ok, r.detail


def test_actions_run_against_real_dom(tmp_path: Path) -> None:
    # fill + click against real selectors, then assert — proves actions execute,
    # not just navigation.
    r = _default_browser(
        _page(tmp_path),
        [{"fill": "#email", "value": "a@b.c"}, {"click": "#go"}],
        {"visible": "Dashboard"},
    )
    assert r.ok, r.detail
