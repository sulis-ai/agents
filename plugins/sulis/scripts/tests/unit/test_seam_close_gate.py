"""WP-001 — failing decision-unit tests for the seam-close gate.

Test-first (MUST). These tests pin the public contract of
``_seam_close_gate.evaluate(...)`` — the pure decision the seam-close gate
makes at the WP done-transition — **before** the module exists (WP-002
implements it). At Red they fail at import (``ModuleNotFoundError:
_seam_close_gate``); WP-002 turns them green. Authoring the failing tests as
their own WP makes the Red gate observable in the dependency graph.

The gate is a pure decision over fixture inputs (TDD §Form: it depends only on
``_acceptance_gate``, ``_brain_query`` read seams, and the ``_wpxlib`` INDEX
reader — all sideways/inward). So every test here drives ``evaluate`` over:

  * a fixture INDEX.md (written by ``_write_index``) giving the seam graph
    (``kind: contract`` + the ``dependsOn`` fan-out + per-WP ``status``),
  * a monkeypatched ``_brain_query`` (``_seed_brain``) resolving requirements →
    covering Scenarios and the already-driven brain evidence, and
  * an injected ``run_scenario`` callable (``FakeRunner``) returning the same
    JSON envelope shape ``sulis-verify-acceptance --json`` emits
    (``{"scenario", "verdict", "gate", "steps", "deferred_needs",
    "blocking", "evidence"}``),

and asserts the resulting ``SeamCloseResult`` verdict + founder-English message.

Mirrors ``test_ship_acceptance_gate_wiring.py`` in spirit; reuses the **real**
``_acceptance_gate.gate_decision`` for the behaviour-parity test (no mock of the
unit we assert reuse of — MEA-09).

Stdlib + pytest. Python 3.11-safe. No subprocess (the runner is injected).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

# The seam-close gate lives in plugins/sulis/scripts/ alongside this test
# package's parents. Put the scripts dir on the path so the bare-module import
# (`_seam_close_gate`, `_acceptance_gate`) resolves the same way the runtime
# (wpx-step12) imports them.
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))


# ─── Fixture identifiers (test-local; not minted brain constants) ───────────
# These are well-formed `dna:<type>:<ulid>` literals used ONLY as fixture
# inputs the monkeypatched _brain_query echoes back. They are not registered
# entities and never leak into a founder-facing assertion.
_REQ = "dna:requirement:0000000000000000000000REQ1"
_JOURNEY = "dna:workflow:0000000000000000000JOURNEY1"
_SCEN = "dna:scenario:000000000000000000000SCEN1"


# ─── In-file fixture helpers (Blue: no copy-paste across the 12 tests) ──────


def _write_index(tmp_path: Path, rows: list[dict]) -> Path:
    """Write a minimal INDEX.md whose WP table ``_wpxlib.parse_index_md`` reads.

    Each row dict carries: id, title, kind, status, depends_on (list), blocks
    (list). The Kind column is non-standard, so ``_wpxlib`` stashes it under
    ``WPRow.extras["Kind"]`` — which is exactly where the gate reads
    ``kind: contract`` / ``kind: composite`` from.
    """
    header = (
        "| ID | Title | Primitive | Kind | Status | Depends On | Blocks |\n"
        "|---|---|---|---|---|---|---|\n"
    )
    lines = []
    for r in rows:
        deps = ", ".join(r.get("depends_on", [])) or "—"
        blocks = ", ".join(r.get("blocks", [])) or "—"
        lines.append(
            f"| {r['id']} | {r['title']} | create | {r.get('kind', 'methodology')} "
            f"| {r['status']} | {deps} | {blocks} |"
        )
    text = "# Work Package Index — fixture\n\n## WP Table\n\n" + header + "\n".join(lines) + "\n"
    path = tmp_path / "INDEX.md"
    path.write_text(text, encoding="utf-8")
    return path


def _seed_brain(
    monkeypatch: pytest.MonkeyPatch,
    *,
    implements: dict[str, list[str]] | None = None,
    scenarios_for_req: dict[str, list[dict]] | None = None,
    scenarios_for_journey: dict[str, list[dict]] | None = None,
    passing_testresults: dict[str, list[dict]] | None = None,
) -> None:
    """Monkeypatch the ``_brain_query`` read seam the gate resolves through.

    The gate is expected to import these names from ``_brain_query``; patching
    them on that module patches the gate's view regardless of how it binds them
    (the gate calls ``_brain_query.find_scenarios_verifying(...)`` etc., the
    same indirection ``_verify_scenario_coverage`` uses).
    """
    import _brain_query

    scenarios_for_req = scenarios_for_req or {}
    scenarios_for_journey = scenarios_for_journey or {}
    passing_testresults = passing_testresults or {}

    monkeypatch.setattr(
        _brain_query,
        "find_scenarios_verifying",
        lambda base_dir, req_id, **kw: list(scenarios_for_req.get(req_id, [])),
        raising=False,
    )
    monkeypatch.setattr(
        _brain_query,
        "find_scenarios_for_journey",
        lambda base_dir, journey_id, **kw: list(scenarios_for_journey.get(journey_id, [])),
        raising=False,
    )
    monkeypatch.setattr(
        _brain_query,
        "find_passing_testresults_for_scenario",
        lambda base_dir, scenario_id, **kw: list(passing_testresults.get(scenario_id, [])),
        raising=False,
    )


def _scenario(scenario_id: str = _SCEN, *, name: str = "Real data crosses the seam") -> dict:
    """A fixture Scenario entity in the shape ``_brain_query`` returns."""
    return {"id": scenario_id, "name": name, "verifies": [_REQ], "journey": _JOURNEY}


class FakeRunner:
    """Injected ``run_scenario`` stub returning the runner's JSON envelope.

    Records every scenario id it was asked to drive so a test can assert the
    gate did (or did NOT, for the fires-once case) invoke the runner. The
    envelope matches ``sulis-verify-acceptance --json``:
    ``{"scenario", "verdict", "gate", "steps", "deferred_needs",
    "blocking", "evidence"}``.
    """

    def __init__(self, envelopes: dict[str, dict] | None = None, default: dict | None = None):
        self._envelopes = envelopes or {}
        self._default = default
        self.calls: list[str] = []

    def __call__(self, scenario_id: str, **kwargs) -> dict:
        self.calls.append(scenario_id)
        if scenario_id in self._envelopes:
            return self._envelopes[scenario_id]
        if self._default is not None:
            return dict(self._default, scenario=scenario_id)
        raise AssertionError(f"FakeRunner had no envelope for {scenario_id!r}")


def _envelope(
    *,
    verdict: str,
    gate: str,
    scenario: str = _SCEN,
    deferred_needs: list[str] | None = None,
    blocking: list[dict] | None = None,
    invariant_kind: str = "equality",
) -> dict:
    """Build a runner JSON envelope. ``invariant_kind`` records whether the
    real-record check was equality or property (AC-2 vs AC-3) — both fold to
    ``observed`` at the gate; the marker rides in a step for the assertion."""
    return {
        "scenario": scenario,
        "verdict": verdict,
        "gate": gate,
        "steps": [{"name": "drive", "status": "pass", "invariant_kind": invariant_kind}],
        "deferred_needs": deferred_needs or [],
        "blocking": blocking or [],
        "evidence": {"emitted": True},
    }


# A reusable closing seam: a contract WP + a consumer that dependsOn it, both
# done, so the seam is closed at the consumer's done-transition.
def _closed_seam_rows() -> list[dict]:
    return [
        {"id": "WP-C", "title": "Order export contract", "kind": "contract",
         "status": "done", "depends_on": [], "blocks": ["WP-X"]},
        {"id": "WP-X", "title": "Consumer of the export", "kind": "methodology",
         "status": "done", "depends_on": ["WP-C"], "blocks": []},
    ]


# ─── The six SPEC acceptance-criteria tests ─────────────────────────────────


def test_seam_undriven_scenario_blocks(tmp_path, monkeypatch):
    """AC-1: seam closes, a covering Scenario exists but was never driven green
    → ``blocked``. (Today it passes silently until ship — the bug being fixed.)
    """
    from _seam_close_gate import evaluate

    index = _write_index(tmp_path, _closed_seam_rows())
    _seed_brain(
        monkeypatch,
        scenarios_for_req={_REQ: [_scenario()]},
        passing_testresults={_SCEN: []},  # never driven green
    )
    # The runner, when driven, reports the real outcome was not observed.
    runner = FakeRunner(default=_envelope(verdict="deferred", gate="blocked",
                                          deferred_needs=["the real data was never driven"]))

    result = evaluate(
        "WP-X",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
        implements={"WP-C": [_REQ]},
    )

    assert result.verdict == "blocked"


def test_seam_equality_verdict_passes(tmp_path, monkeypatch):
    """AC-2: covering Scenario drove green with an **equality** verdict over the
    real record → ``observed``."""
    from _seam_close_gate import evaluate

    index = _write_index(tmp_path, _closed_seam_rows())
    _seed_brain(monkeypatch, scenarios_for_req={_REQ: [_scenario()]})
    runner = FakeRunner(default=_envelope(verdict="pass", gate="pass",
                                          invariant_kind="equality"))

    result = evaluate(
        "WP-X",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
        implements={"WP-C": [_REQ]},
    )

    assert result.verdict == "observed"


def test_seam_property_verdict_passes(tmp_path, monkeypatch):
    """AC-3: covering Scenario drove green with a **property** verdict (a record
    matching shape X appeared) → ``observed``. Same pass outcome as equality —
    both are observed-green at the gate."""
    from _seam_close_gate import evaluate

    index = _write_index(tmp_path, _closed_seam_rows())
    _seed_brain(monkeypatch, scenarios_for_req={_REQ: [_scenario()]})
    runner = FakeRunner(default=_envelope(verdict="pass", gate="pass",
                                          invariant_kind="property"))

    result = evaluate(
        "WP-X",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
        implements={"WP-C": [_REQ]},
    )

    assert result.verdict == "observed"


def test_seam_deferred_blocks(tmp_path, monkeypatch):
    """AC-4: a deferred/blocked Scenario → ``blocked``; ``reason`` names the seam
    by the contract WP **title** and what wasn't driven; **no** ``dna:`` / ``WP-``
    operator ids leak into ``reason`` (asserted via regex)."""
    from _seam_close_gate import evaluate

    index = _write_index(tmp_path, _closed_seam_rows())
    _seed_brain(monkeypatch, scenarios_for_req={_REQ: [_scenario()]})
    runner = FakeRunner(default=_envelope(
        verdict="deferred", gate="blocked",
        deferred_needs=["a credential the real run needs"],
        blocking=[{"scenario": "Real data crosses the seam",
                   "why": "the real outcome wasn't driven"}],
    ))

    result = evaluate(
        "WP-X",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
        implements={"WP-C": [_REQ]},
    )

    assert result.verdict == "blocked"
    # Founder-English: names the seam by its human title…
    assert "Order export contract" in result.reason
    # …and never leaks operator vocabulary.
    assert not re.search(r"\bdna:", result.reason), result.reason
    assert not re.search(r"\bWP-\w+", result.reason), result.reason
    assert "dna:scenario:" not in result.reason


def test_seam_no_covering_scenario_blocks(tmp_path, monkeypatch):
    """AC-5: closing seam with **no** covering Scenario → ``blocked``; the reason
    distinguishes "no end-to-end check" from "couldn't run" (ADR-005 distinct
    wording). The runner must NOT be invoked — there is nothing to drive."""
    from _seam_close_gate import evaluate

    index = _write_index(tmp_path, _closed_seam_rows())
    _seed_brain(
        monkeypatch,
        scenarios_for_req={_REQ: []},        # no covering scenario for the requirement
        scenarios_for_journey={_JOURNEY: []},  # nor via the journey fallback
    )
    runner = FakeRunner(default=_envelope(verdict="pass", gate="pass"))

    result = evaluate(
        "WP-X",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
        implements={"WP-C": [_REQ]},
    )

    assert result.verdict == "blocked"
    assert runner.calls == [], "no-coverage must short-circuit before driving"
    # Distinct-from-deferred wording: "no end-to-end check / nothing drove".
    low = result.reason.lower()
    assert "no end-to-end check" in low or "nothing drove" in low, result.reason
    # And it must NOT read as the deferred "couldn't run" message.
    assert "couldn't run" not in low and "could not run" not in low, result.reason


def test_seam_allow_deferred_escape_records(tmp_path, monkeypatch):
    """AC-6: ``allow_deferred=True`` on a knowingly-deferred seam → ``observed``
    (proceeds) **and** the deferral is recorded (``deferred_needs`` non-empty /
    a recorded note present)."""
    from _seam_close_gate import evaluate

    index = _write_index(tmp_path, _closed_seam_rows())
    _seed_brain(monkeypatch, scenarios_for_req={_REQ: [_scenario()]})
    runner = FakeRunner(default=_envelope(
        verdict="deferred", gate="pass",
        deferred_needs=["agent-step-execution-tier"],
    ))

    result = evaluate(
        "WP-X",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        allow_deferred=True,
        run_scenario=runner,
        implements={"WP-C": [_REQ]},
    )

    assert result.verdict == "observed"
    assert result.deferred_needs, "the conscious deferral must be recorded"


# ─── Supporting correctness tests (not numbered ACs) ────────────────────────


def test_unrelated_wp_done_is_noop(tmp_path, monkeypatch):
    """A just-``done`` WP in no seam → ``not-closed``, ``reason == ""`` (silent).
    The common single-kind case — this change's OWN WPs hit this path (CF
    exemption). The runner must never be invoked."""
    from _seam_close_gate import evaluate

    rows = [
        {"id": "WP-SOLO", "title": "Standalone methodology WP", "kind": "methodology",
         "status": "done", "depends_on": [], "blocks": []},
    ]
    index = _write_index(tmp_path, rows)
    _seed_brain(monkeypatch)
    runner = FakeRunner(default=_envelope(verdict="pass", gate="pass"))

    result = evaluate(
        "WP-SOLO",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
    )

    assert result.verdict == "not-closed"
    assert result.reason == ""
    assert runner.calls == []


def test_integration_wp_completion_detects_seam_close(tmp_path, monkeypatch):
    """Detection signal (1): an integration / ``kind: composite`` WP reaching
    ``done`` closes its rooted seam, so the gate evaluates (here: observed)."""
    from _seam_close_gate import evaluate

    rows = [
        {"id": "WP-C", "title": "Payments contract", "kind": "contract",
         "status": "done", "depends_on": [], "blocks": ["WP-INT"]},
        {"id": "WP-INT", "title": "Integration: swap mock to real", "kind": "composite",
         "status": "done", "depends_on": ["WP-C"], "blocks": []},
    ]
    index = _write_index(tmp_path, rows)
    _seed_brain(monkeypatch, scenarios_for_req={_REQ: [_scenario()]})
    runner = FakeRunner(default=_envelope(verdict="pass", gate="pass"))

    result = evaluate(
        "WP-INT",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
        implements={"WP-C": [_REQ]},
    )

    assert result.verdict == "observed"
    assert runner.calls == [_SCEN], "the integration close must drive the covering scenario"


def test_contract_fanout_all_done_detects_seam_close(tmp_path, monkeypatch):
    """Detection signal (2): a contract WP + all its ``dependsOn``-children
    ``done``, with no explicit integration WP, closes the seam."""
    from _seam_close_gate import evaluate

    rows = [
        {"id": "WP-C", "title": "Inventory contract", "kind": "contract",
         "status": "done", "depends_on": [], "blocks": ["WP-P", "WP-Q"]},
        {"id": "WP-P", "title": "Producer side", "kind": "methodology",
         "status": "done", "depends_on": ["WP-C"], "blocks": []},
        {"id": "WP-Q", "title": "Consumer side", "kind": "methodology",
         "status": "done", "depends_on": ["WP-C"], "blocks": []},
    ]
    index = _write_index(tmp_path, rows)
    _seed_brain(monkeypatch, scenarios_for_req={_REQ: [_scenario()]})
    runner = FakeRunner(default=_envelope(verdict="pass", gate="pass"))

    # The last child to flip done (WP-Q) closes the seam.
    result = evaluate(
        "WP-Q",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
        implements={"WP-C": [_REQ]},
    )

    assert result.verdict == "observed"


def test_seam_close_fires_once(tmp_path, monkeypatch):
    """A settled seam (its covering Scenarios already have passing TestResults
    in the fixture brain) is **not** re-driven by a later unrelated WP ``done``.
    Once-only via brain evidence (Open Question 2). Asserts ``run_scenario`` is
    NOT called when evidence already present."""
    from _seam_close_gate import evaluate

    index = _write_index(tmp_path, _closed_seam_rows())
    _seed_brain(
        monkeypatch,
        scenarios_for_req={_REQ: [_scenario()]},
        passing_testresults={_SCEN: [{"outcome": "pass", "scenario": _SCEN}]},
    )
    runner = FakeRunner(default=_envelope(verdict="pass", gate="pass"))

    result = evaluate(
        "WP-X",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
        implements={"WP-C": [_REQ]},
    )

    # The seam is already observed-green by brain evidence — no re-drive.
    assert runner.calls == [], "a settled seam must not be re-driven"
    assert result.verdict in ("observed", "not-closed")


def test_malformed_index_does_not_fabricate_green(tmp_path, monkeypatch):
    """Armor: an undeterminable detection (malformed INDEX / missing WP row) →
    ``not-closed`` with a "couldn't evaluate" reason; **never** fabricates
    ``observed``."""
    from _seam_close_gate import evaluate

    # INDEX with no WP table at all — the just-done WP's row is absent.
    index = tmp_path / "INDEX.md"
    index.write_text("# Broken INDEX\n\nNo table here.\n", encoding="utf-8")
    _seed_brain(monkeypatch)
    runner = FakeRunner(default=_envelope(verdict="pass", gate="pass"))

    result = evaluate(
        "WP-MISSING",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
    )

    assert result.verdict != "observed", "must never fabricate green on a bad INDEX"
    assert result.verdict == "not-closed"
    assert "couldn't evaluate" in result.reason.lower() or "could not evaluate" in result.reason.lower()
    assert runner.calls == []


def test_gate_decision_is_reused_not_reimplemented(tmp_path, monkeypatch):
    """Behaviour-parity: fold the same fixture verdicts through both the **real**
    ``_acceptance_gate.gate_decision`` directly and through ``evaluate``; assert
    identical blocked/pass outcome (so the two gates can't drift on
    observed-or-blocked). No mock of ``gate_decision`` — MEA-09."""
    from _acceptance_gate import gate_decision
    from _scenario_runner import AcceptanceResult
    from _seam_close_gate import evaluate

    # A deferred scenario: gate_decision (observed-or-blocked default) → blocked.
    direct = gate_decision(
        [AcceptanceResult(scenario_id=_SCEN, scenario_name="Real data crosses the seam",
                          verdict="deferred",
                          steps=[{"name": "drive", "status": "deferred", "need": "x"}])],
        require_observed=True,
    )
    assert direct.verdict == "blocked"  # anchors the real gate_decision behaviour

    index = _write_index(tmp_path, _closed_seam_rows())
    _seed_brain(monkeypatch, scenarios_for_req={_REQ: [_scenario()]})
    runner = FakeRunner(default=_envelope(
        verdict="deferred", gate="blocked",
        deferred_needs=["x"],
        blocking=[{"scenario": "Real data crosses the seam", "why": "the real outcome wasn't driven"}],
    ))

    via_gate = evaluate(
        "WP-X",
        index_path=index,
        brain_base_dir=tmp_path,
        repo_root=tmp_path,
        run_scenario=runner,
        implements={"WP-C": [_REQ]},
    )

    # Same observed-or-blocked outcome through both paths: blocked maps to blocked.
    assert via_gate.verdict == "blocked"
    assert (direct.verdict == "blocked") == (via_gate.verdict == "blocked")
