"""Unit tests for the list-ready round-trip gate folded into `wpx-index lint`
(WP-001 / #60/#218/#222/#233, meta-diagnosis #97).

Today's `cmd_lint` only checks the WP table HEADER shape
(`validate_wp_index_header`, keyed off `_WP_TABLE_HEADER_RE`). That is a
*proxy* for "the builder can read the to-do list": it is structurally blind
to a canonical-header INDEX whose Status cells are all `ready`/`blocked`
(never `pending`). The real builder consumer (`list-ready` →
`_collect_status_across_tables` + `_resolve_deps`) then returns an empty
ready/pending set and the break surfaces mid-build, not at decompose time.

These tests pin the round-trip: after the header check passes, `cmd_lint`
runs the SAME parse `list-ready` runs and asserts every authored `pending`
WP is accounted for (the consumer SEES it — ready ∪ dependency-blocked). A
0-WP / parse-fail result while WPs exist is a non-zero exit.

Cases 1–3 MUST be red against today's gate (the bug); cases 4–5 MUST be
green throughout (no false-positive). The wiring test pins the exit-code
contract Step 9.5 reads.

Fixture/helper shape reused from `test_wpx_index_multitable.py` (EP-03 — the
established pattern in this dir).
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import json
from contextlib import redirect_stdout
from importlib.machinery import SourceFileLoader
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]
_WPX_INDEX = _SCRIPTS / "wpx-index"


def _load_wpx_index():
    loader = SourceFileLoader("wpx_index_mod_rt", str(_WPX_INDEX))
    spec = importlib.util.spec_from_loader("wpx_index_mod_rt", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


wpx = _load_wpx_index()


# ─── fixtures ────────────────────────────────────────────────────────────────

# (1) No WP table at all — "readable layout" prose only. The consumer can
# parse nothing; the break would surface mid-build.
_NO_WP_TABLE_INDEX = """# Work Package Index

## Orchestrator Config
max_parallel: 3

## Plan

We will decompose into a readable layout of work, addressed in order. No
machine-readable table is emitted here.
"""

# (2) Canonical-shaped rows under a NON-canonical header (`| WP |` + a
# duplicate `kind` column) — the #60/#218/#233 drift. Invisible to
# `_WP_TABLE_HEADER_RE`.
_NONCANONICAL_HEADER_INDEX = """# Work Package Index

## WP table

| WP | Title | kind | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|---|
| WP-001 | Foundation | backend | create | pending | — | WP-002 |
| WP-002 | Builds on it | backend | create | pending | WP-001 | — |
"""

# (3) Canonical header, but every Status cell is `ready`/`blocked` — none
# `pending`. The load-bearing #222 case: the header lint passes, yet the
# consumer's pending set is empty (decompose NOT actually done).
_ALL_NONPENDING_INDEX = """# Work Package Index

## WP table

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | Foundation | create | ready | — | WP-002 |
| WP-002 | Builds on it | create | blocked | WP-001 | — |
"""

# (4) Canonical header, ≥1 `pending` WP — a mix of immediately-ready
# (no deps) and dependency-blocked (dep on a pending WP). Healthy INDEX.
_CANONICAL_PENDING_INDEX = """# Work Package Index

## WP table

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | Foundation | create | pending | — | WP-002 |
| WP-002 | Builds on it | create | pending | WP-001 | — |
"""

# (5) Canonical header, every WP `pending` but every WP depends on another
# pending WP → 0 immediately ready. The consumer still SEES all of them
# (dependency-blocked), so the round-trip property "accounted for" holds.
# (A pathological cycle is fine for this property test — it proves the gate
# does not require ready ≥ 1.)
_FULLY_DEPCHAINED_INDEX = """# Work Package Index

## WP table

| ID | Title | Primitive | Status | Depends On | Blocks |
|---|---|---|---|---|---|
| WP-001 | A | create | pending | WP-002 | — |
| WP-002 | B | create | pending | WP-001 | — |
"""


def _write_index(tmp_path: Path, index_text: str) -> Path:
    """Create .architecture/proj/work-packages/INDEX.md (no WP files →
    deps resolve from the table dep column, the single-table fallback path)."""
    wp_dir = tmp_path / ".architecture" / "proj" / "work-packages"
    wp_dir.mkdir(parents=True)
    (wp_dir / "INDEX.md").write_text(index_text, encoding="utf-8")
    return tmp_path


def _ns(tmp_path: Path, **kw) -> argparse.Namespace:
    base = {"repo_root": str(tmp_path), "project": "proj"}
    base.update(kw)
    return argparse.Namespace(**base)


def _run(fn, ns) -> dict:
    """Invoke a cmd_* function; capture the emit JSON + SystemExit code."""
    buf = io.StringIO()
    code = None
    with redirect_stdout(buf):
        try:
            fn(ns)
        except SystemExit as exc:
            code = exc.code
    out = buf.getvalue().strip()
    data = json.loads(out) if out else {}
    data["_exit"] = code
    return data


# ─── case 1: no WP table → gate FAILS (#97) ──────────────────────────────────


def test_missing_wp_table_fails_gate(tmp_path):
    """An INDEX with no WP table (prose only) must fail the gate. The
    consumer can parse nothing — a non-zero exit at decompose time, not a
    silent mid-build break."""
    _write_index(tmp_path, _NO_WP_TABLE_INDEX)
    result = _run(wpx.cmd_lint, _ns(tmp_path))
    assert result["ok"] is False
    assert result["_exit"] != 0


# ─── case 2: non-canonical header → gate FAILS (#218/#233) ────────────────────


def test_noncanonical_header_fails_gate(tmp_path):
    """Canonical-shaped rows under a `| WP |` / duplicate-`kind` header are
    invisible to the consumer. The gate must fail."""
    _write_index(tmp_path, _NONCANONICAL_HEADER_INDEX)
    result = _run(wpx.cmd_lint, _ns(tmp_path))
    assert result["ok"] is False
    assert result["_exit"] != 0


# ─── case 3: all-non-pending statuses → gate FAILS (#222, LOAD-BEARING) ───────


def test_status_vocab_all_nonpending_fails_gate(tmp_path):
    """The case the header lint CANNOT catch: canonical header passes, but
    every Status cell is `ready`/`blocked` (none `pending`). The consumer's
    pending set is empty → decompose NOT done. MUST be red against today's
    gate (which only checks the header) and green after this WP's change."""
    _write_index(tmp_path, _ALL_NONPENDING_INDEX)
    result = _run(wpx.cmd_lint, _ns(tmp_path))
    assert result["ok"] is False, (
        "all-non-pending INDEX passed the gate — the header lint is blind to "
        "this (#222); the round-trip must catch it"
    )
    assert result["_exit"] != 0


# ─── case 4: canonical + ≥1 pending → gate PASSES (no false-positive) ─────────


def test_canonical_with_pending_passes_gate(tmp_path):
    """A healthy INDEX (canonical header, ≥1 pending WP, mix of ready and
    dependency-blocked) must pass and report round_trip ok."""
    _write_index(tmp_path, _CANONICAL_PENDING_INDEX)
    result = _run(wpx.cmd_lint, _ns(tmp_path))
    assert result["ok"] is True, f"healthy INDEX wrongly failed: {result}"
    assert result["_exit"] == 0
    assert result["data"]["round_trip"] == "ok"


# ─── case 5: fully dep-chained, 0 ready, all accounted → PASSES ───────────────


def test_fully_depchained_zero_ready_still_passes(tmp_path):
    """Every WP `pending` but each depends on another pending WP → 0
    immediately ready, yet the consumer SEES every WP (dependency-blocked).
    The property is "accounted for", not "ready ≥ 1" (Contract invariant 2),
    so the gate must pass."""
    _write_index(tmp_path, _FULLY_DEPCHAINED_INDEX)
    result = _run(wpx.cmd_lint, _ns(tmp_path))
    assert result["ok"] is True, (
        f"fully dep-chained INDEX wrongly failed — gate is requiring ready>=1 "
        f"instead of accounted-for: {result}"
    )
    assert result["_exit"] == 0


# ─── wiring: Step 9.5 exit-code contract ("non-zero = not done") ──────────────


def test_step95_treats_variants_as_done_state(tmp_path):
    """The SPEC "Wiring check" as a test over `cmd_lint`'s exit code — which
    is exactly what plan-work Step 9.5 reads: cases 1–3 non-zero (decompose
    NOT done), cases 4–5 zero (done)."""
    # cases 1-3 → non-zero
    for index_text in (_NO_WP_TABLE_INDEX, _NONCANONICAL_HEADER_INDEX,
                       _ALL_NONPENDING_INDEX):
        sub = tmp_path / f"p{abs(hash(index_text))}"
        _write_index(sub, index_text)
        result = _run(wpx.cmd_lint, _ns(sub))
        assert result["_exit"] != 0, (
            f"expected non-zero (not-done) exit for fixture, got "
            f"{result['_exit']}: {result}"
        )

    # cases 4-5 → zero
    for index_text in (_CANONICAL_PENDING_INDEX, _FULLY_DEPCHAINED_INDEX):
        sub = tmp_path / f"q{abs(hash(index_text))}"
        _write_index(sub, index_text)
        result = _run(wpx.cmd_lint, _ns(sub))
        assert result["_exit"] == 0, (
            f"expected zero (done) exit for healthy fixture, got "
            f"{result['_exit']}: {result}"
        )
