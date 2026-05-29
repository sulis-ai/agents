"""Keystone unit tests for wpx-render-contract (WP-001, test-first).

Covers TDD §4.1 (Fixture A multi-area assertions 0–14; Fixture B minimal
single-area assertions 15–18) and §4.2 (OpenAPI fallback degradation,
tag-grouping, two-contracts precedence, no-contract raw + note).

The renderer is a CLI step that writes CONTRACT.html + a manifest into a
worktree. These tests seed a tmp worktree with a committed fixture, run the
step via subprocess, and assert on the rendered HTML.

The renderer marks the founder-legible default view and the technical-detail
region with `data-region="default"` / `data-region="technical"` wrappers so
the tests can assert *which* region a piece of content lands in (ADR-002:
form-fields/languages/background/retirement/permission code in the default
view; rateLimits/idempotent/bindings/raw-schemas/full JSON-LD behind the
toggle).
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_SCRIPTS_DIR = _HERE.parent.parent
_FIXTURES = _HERE.parent / "fixtures" / "render_contract"
_RENDERER = _SCRIPTS_DIR / "wpx-render-contract"


# ─── helpers ───────────────────────────────────────────────────────────────


def _run_renderer(worktree: Path, *extra: str) -> subprocess.CompletedProcess:
    cmd = [sys.executable, str(_RENDERER), "--worktree", str(worktree), *extra]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=60)


def _seed(tmp_path: Path, fixtures: dict[str, str]) -> Path:
    """Create a tmp worktree containing the given {dest_name: fixture_file}."""
    worktree = tmp_path / "worktree"
    worktree.mkdir(parents=True)
    for dest, src in fixtures.items():
        shutil.copy(_FIXTURES / src, worktree / dest)
    return worktree


def _render_html(tmp_path: Path, fixtures: dict[str, str]) -> tuple[str, dict]:
    worktree = _seed(tmp_path, fixtures)
    proc = _run_renderer(worktree)
    assert proc.returncode == 0, (
        f"renderer exited {proc.returncode}\n"
        f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
    )
    result = json.loads(proc.stdout)
    assert result["ok"] is True, result
    html_path = worktree / "CONTRACT.html"
    assert html_path.exists(), "renderer did not write CONTRACT.html"
    return html_path.read_text(encoding="utf-8"), result


# A region splitter: returns (default_view_html, technical_html). The renderer
# puts the founder-legible default view in <section data-region="default">
# blocks ABOVE the "show technical detail" toggle, and the technical render
# inside a single <details class="technical"> ... </details> element (its
# children carry data-region="technical"). The split keys on that toggle
# boundary — robust to arbitrary nested markup inside each region (a regex
# cannot balance nested tags, so we split on the boundary, not per-element).
_TOGGLE_OPEN = '<details class="technical">'


def _split_regions(html: str) -> tuple[str, str]:
    assert 'data-region="default"' in html, (
        'no data-region="default" block found in rendered HTML'
    )
    assert 'data-region="technical"' in html, (
        'no data-region="technical" block found in rendered HTML'
    )
    idx = html.find(_TOGGLE_OPEN)
    assert idx != -1, "no <details class=\"technical\"> toggle found"
    # The default *view* is the rendered body above the toggle — exclude the
    # <head>/<style> so CSS class names (.workflow, .entity, …) don't masquerade
    # as rendered content in the auto-trim assertions.
    body_start = html.find("<body")
    start = body_start if body_start != -1 else 0
    default = html[start:idx]
    technical = html[idx:]
    return default, technical


# ─── TDD §4.1 — Fixture A: rich, multi-area (assertions 0–14) ───────────────


@pytest.fixture
def fixtureA_html(tmp_path) -> tuple[str, str, str, dict]:
    html, result = _render_html(tmp_path, {"contract.jsonld": "fixtureA_catalog.jsonld"})
    default, technical = _split_regions(html)
    return html, default, technical, result


def test_fixtureA_multi_area_full_picture(fixtureA_html):
    html, default, technical, result = fixtureA_html

    # 0. groups the default view by area, in order, with an "areas covered"
    #    overview at the top naming both areas.
    assert "areas covered" in default.lower()
    pos_platforms = default.lower().find("platform")
    pos_notifications = default.lower().find("notification")
    assert pos_platforms != -1 and pos_notifications != -1
    # Both areas appear as headings (derived from the {service}/{op} key prefix).
    headings = re.findall(r"<h[12][^>]*>(.*?)</h[12]>", default, re.DOTALL | re.IGNORECASE)
    heading_text = " ".join(headings).lower()
    assert "platform" in heading_text
    assert "notification" in heading_text

    # 1. references each operation (the "What it does" list is complete across
    #    both areas) AND surfaces the actual operation identifier in the default
    #    view paired with the readable action description.
    assert "An admin can set up a new platform" in default  # readable description
    # actual operation identifier (the {service}/{operation} key and/or method)
    assert "platform/create-platform" in default or "create_platform" in default
    assert "send-legacy-digest" in default or "send_legacy_digest" in default

    # 2. per-operation default view: readable permission line + "Who can do
    #    this" + actual permission code, all in the default view.
    assert "lets you create platforms" in default          # readable meaning
    assert "Platform administrators" in default            # who can do this
    assert "platform.platforms:create" in default          # actual code in DEFAULT view (Rev 6)

    # 3. form fields rendered readably (label/placeholder/input type/group,
    #    validation rule, enum + human labels, show-when) for entity + op input.
    assert "Platform name" in default                      # label, not bare prop name
    assert "e.g. Acme Production" in default               # placeholder
    assert "Starter (single region)" in default            # x-enum-labels human option label
    assert "Enterprise (dedicated)" in default
    # show-when conditional logic surfaced
    assert re.search(r"(show[- ]?when|only.*when|visible)", default, re.IGNORECASE)
    # validation rule surfaced as a plain hint (not raw schema dump)
    assert re.search(r"(required|must)", default, re.IGNORECASE)

    # 4. entities + lifecycle state chain.
    assert "Platform" in default
    assert re.search(r"draft.*active.*suspended", default, re.DOTALL)

    # 5. constraints as plain business rules.
    assert "platform name must be unique" in default.lower()

    # 6. languages line in the DEFAULT view (not toggle), readable locale names.
    assert re.search(r"available in.*english.*spanish", default, re.IGNORECASE)
    assert "english" in default.lower() and "spanish" in default.lower()
    # languages must NOT be only in the technical region
    assert "spanish" not in technical.lower() or "spanish" in default.lower()

    # 7. workflows as readable journeys (steps + successCriteria).
    assert "Onboard a new customer" in default
    assert "Create the platform" in default
    assert "welcome notification" in default.lower()

    # 8. what each action changes — stateEffects naming entity + target state.
    assert re.search(r"Platform.*(active|suspended)", default, re.DOTALL)

    # 9. async op flagged "runs in the background" in the default view.
    assert re.search(r"runs in the background|background", default, re.IGNORECASE)

    # 10. synthesised worked walkthrough (hero scenario).
    assert re.search(r"(walkthrough|worked|scenario|for example)", default, re.IGNORECASE)

    # 11. concrete example request/response.
    assert re.search(r"(example|request|response)", default, re.IGNORECASE)
    assert "Acme Production" in default or "Acme Production" in html

    # 12. errors surfaced with user-facing messages.
    assert "That platform name is already in use." in default

    # 13. "being retired" badge enriched with sunset + replacement, default view.
    assert re.search(r"(being retired|retired|deprecated)", default, re.IGNORECASE)
    assert "2026-12-31" in default                          # sunset date
    assert "send-realtime-notification" in default          # replacement

    # 14. technical region holds the full ServiceSpec JSON-LD + rateLimits/
    #     idempotent/bindings/raw schemas; the default view does NOT carry the
    #     raw schema dump, but DOES carry the permission code + operation id.
    assert re.search(r'(json-?ld|"@type"|servicecatalog)', technical, re.IGNORECASE)
    # the actual permission code is in the default view (Rev 6 — superseding
    # Rev 5's toggle-only placement).
    assert "platform.platforms:create" in default


# ─── TDD §4.1 — Fixture B: minimal, single-area (assertions 15–18) ──────────


@pytest.fixture
def fixtureB_html(tmp_path) -> tuple[str, str, str, dict]:
    html, result = _render_html(tmp_path, {"contract.jsonld": "fixtureB_minimal.jsonld"})
    default, technical = _split_regions(html)
    return html, default, technical, result


def test_fixtureB_minimal_single_area_autohide(fixtureB_html):
    html, default, technical, result = fixtureB_html

    # 15. "What it does" + example are present.
    assert re.search(r"(what it does|ping|pong)", default, re.IGNORECASE)
    assert re.search(r"(example|request|response)", default, re.IGNORECASE)

    # 16. richer sections absent with NO empty heading: entities/lifecycle,
    #     business rules, journeys, what-each-action-changes, languages line,
    #     background flag, being-retired badge.
    low = default.lower()
    assert "business rules" not in low
    assert "lifecycle" not in low
    assert "journey" not in low and "workflow" not in low
    assert "what each action changes" not in low
    assert "available in" not in low          # single locale → no languages line
    assert "runs in the background" not in low  # synchronous → no background flag
    assert "being retired" not in low and "deprecated" not in low

    # 17. plain typed input still renders as basic fields (name + inferred type),
    #     no rich form-metadata chrome (no enum-option list, no show-when block).
    assert "message" in low                    # the field appears (label "Message")
    assert "show-when" not in low and "show when" not in low
    # no human-enum-label chrome (there is no enum in fixture B)
    assert "x-enum-labels" not in default

    # 18. single-area renders ungrouped: NO area heading, NO "areas covered".
    assert "areas covered" not in low


# ─── TDD §4.2 — OpenAPI fallback + degradation ──────────────────────────────


def test_openapi_fallback_degrades_gracefully(tmp_path):
    html, result = _render_html(tmp_path, {"openapi.json": "openapi_with_tags.json"})
    default, technical = _split_regions(html)
    low = default.lower()

    # operations + basic form fields + example + errors-from-responses present.
    assert "Create a widget" in default
    assert "name" in default
    assert re.search(r"(example|request|response)", default, re.IGNORECASE)
    assert "already exists" in low            # error derived from the 409 response

    # plain "this contract carries less guidance" note.
    assert re.search(r"(less guidance|carries less|raw contract|fewer)", low)

    # richer founder-legible sections ABSENT, no empty headings:
    assert "business rules" not in low
    assert "lifecycle" not in low
    assert "journey" not in low
    assert "what each action changes" not in low
    assert "available in" not in low          # OpenAPI carries no i18n block
    assert "runs in the background" not in low  # no async in OpenAPI
    assert "who can do this" not in low       # no permission defs in OpenAPI

    # form fields degrade: no human enum labels, no show-when logic.
    assert "show-when" not in low and "show when" not in low

    # technical region holds the Redoc / raw OpenAPI render.
    assert re.search(r"(openapi|redoc)", technical, re.IGNORECASE)


def test_openapi_tag_grouping_and_no_tag_single_block(tmp_path):
    # (a) tags present → group by tag, with the "areas covered" overview.
    html_t, _ = _render_html(tmp_path / "a", {"openapi.json": "openapi_with_tags.json"})
    default_t, _ = _split_regions(html_t)
    assert "areas covered" in default_t.lower()
    headings_t = " ".join(
        re.findall(r"<h[12][^>]*>(.*?)</h[12]>", default_t, re.DOTALL | re.IGNORECASE)
    ).lower()
    assert "widgets" in headings_t
    assert "gadgets" in headings_t
    # grouping never fabricates the richer per-area content OpenAPI can't carry.
    assert "who can do this" not in default_t.lower()
    assert "lifecycle" not in default_t.lower()

    # (b) no tags → single ungrouped block, no area heading, no overview.
    html_n, _ = _render_html(tmp_path / "b", {"openapi.json": "openapi_no_tags.json"})
    default_n, _ = _split_regions(html_n)
    assert "areas covered" not in default_n.lower()
    assert "Create a thing" in default_n


def test_two_contracts_precedence_order(tmp_path):
    # Both a ServiceSpec and an OpenAPI doc present → both render, ServiceSpec
    # ahead of OpenAPI (precedence order, ADR-005).
    html, result = _render_html(
        tmp_path,
        {"contract.jsonld": "fixtureB_minimal.jsonld", "openapi.json": "openapi_no_tags.json"},
    )
    # the ServiceSpec operation appears before the OpenAPI operation in the
    # default view (search the default region — the technical toggle also
    # contains "Ping" inside the JSON-LD dump, which must not fool the order).
    default, _ = _split_regions(html)
    # The ServiceSpec "ping" operation (its actual identifier) appears before
    # the OpenAPI "Create a thing" operation in the default view.
    pos_spec = default.find(">ping<")
    pos_openapi = default.find("Create a thing")
    assert pos_spec != -1, "ServiceSpec contract not rendered in default view"
    assert pos_openapi != -1, "OpenAPI contract not rendered in default view"
    assert pos_spec < pos_openapi, "ServiceSpec must render ahead of OpenAPI"


def test_no_contract_raw_plus_note(tmp_path):
    # No ServiceSpec, no OpenAPI — only a raw contract file. Renders the raw
    # contract + a plain note; must not throw.
    html, result = _render_html(tmp_path, {"data-contract.json": "raw_contract.json"})
    low = html.lower()
    assert re.search(r"(raw contract|no contract|this is the raw)", low)
    # the raw content is shown verbatim somewhere in the page.
    assert "legacy-thing" in html
