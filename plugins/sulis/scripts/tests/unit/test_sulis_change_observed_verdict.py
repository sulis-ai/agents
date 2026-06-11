"""Unit tests for the #118 ship-time observed-verdict gate.

The root cause this closes: the Definition-of-Done verdict (every touched
Requirement has a passing TestResult) was enforced ONLY as prose in
`change/SKILL.md` gate 4.9 — the `sulis-change` ship script ran it zero times.
So a change could be marked *shipped* without an observed verdict, by an agent
skipping the prose step or a hand-merge bypassing the skill entirely. This gate
moves the check from prose into the ship mechanism: `mark-shipped` refuses
unless every touched SRD's DoD verdict is `pass` — escapable only by a
conscious, logged `--force` (mirrors the #111 ship-integrity guard).

`evaluate_observed_verdict` is the PURE decision (touched SRDs + a verdict
function → ok/blocked); the script wires git-diff + `verify_requirements` into
it. The decision is the load-bearing, fixture-able part — tested here.
"""

from __future__ import annotations

import importlib.util
import json
from importlib.machinery import SourceFileLoader
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]


def _load_sulis_change():
    loader = SourceFileLoader("sulis_change_mod", str(_SCRIPTS / "sulis-change"))
    spec = importlib.util.spec_from_loader("sulis_change_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_mod = _load_sulis_change()
evaluate_observed_verdict = _mod.evaluate_observed_verdict
evaluate_scenario_verdict = _mod.evaluate_scenario_verdict
_scenario_ids_for_change = _mod._scenario_ids_for_change


# ─── no SRD touched → out of scope, never blocks ───────────────────────────


def test_no_srd_touched_is_ok():
    ok, reason = evaluate_observed_verdict([], verify_fn=lambda srd: "pass")
    assert ok is True
    assert "no srd" in reason.lower() or "not applicable" in reason.lower()


# ─── all touched SRDs PASS → observed, ship proceeds ───────────────────────


def test_all_srds_pass_is_ok():
    srds = [".specifications/payments/SRD.md", ".specifications/auth/SRD.md"]
    ok, reason = evaluate_observed_verdict(srds, verify_fn=lambda srd: "pass")
    assert ok is True


# ─── any touched SRD not-PASS → BLOCKED (observed-or-blocked) ──────────────


def test_a_failing_srd_blocks():
    srds = [".specifications/payments/SRD.md"]
    ok, reason = evaluate_observed_verdict(srds, verify_fn=lambda srd: "fail")
    assert ok is False
    assert "payments" in reason
    assert "fail" in reason.lower()


def test_a_partial_srd_blocks():
    # partial = some FRs unverified — an unobserved requirement is blocked, not
    # a quiet pass. The conscious escape is --force at the call site.
    srds = [".specifications/auth/SRD.md"]
    ok, reason = evaluate_observed_verdict(srds, verify_fn=lambda srd: "partial")
    assert ok is False
    assert "auth" in reason


def test_one_pass_one_fail_blocks_and_names_the_failing_one():
    srds = [".specifications/ok/SRD.md", ".specifications/bad/SRD.md"]
    verdicts = {".specifications/ok/SRD.md": "pass",
                ".specifications/bad/SRD.md": "fail"}
    ok, reason = evaluate_observed_verdict(srds, verify_fn=lambda srd: verdicts[srd])
    assert ok is False
    assert "bad" in reason
    assert "ok/SRD.md" not in reason  # only the unverified one is named


# ─── Phase 2: the scenario route (founder-facing changes with scenarios, no ─
#     SRD). A change's emitted scenarios must each have a passing TestResult
#     (observed) before it ships. The authored .scenarios.jsonld records each
#     scenario's emitted dna:scenario id directly — no seed/journey resolution.


def test_scenario_verdict_no_emitted_scenarios_is_ok():
    ok, reason = evaluate_scenario_verdict([], observed_fn=lambda sid: True)
    assert ok is True
    assert "not applicable" in reason.lower() or "no emitted" in reason.lower()


def test_scenario_verdict_all_observed_is_ok():
    ids = ["dna:scenario:AAA", "dna:scenario:BBB"]
    ok, reason = evaluate_scenario_verdict(ids, observed_fn=lambda sid: True)
    assert ok is True


def test_scenario_verdict_unobserved_blocks_and_names_it():
    ids = ["dna:scenario:AAA", "dna:scenario:BBB"]
    observed = {"dna:scenario:AAA": True, "dna:scenario:BBB": False}
    ok, reason = evaluate_scenario_verdict(ids, observed_fn=lambda sid: observed[sid])
    assert ok is False
    assert "dna:scenario:BBB" in reason
    assert "dna:scenario:AAA" not in reason  # only the unobserved one is named


def test_scenario_verdict_none_observed_blocks():
    ids = ["dna:scenario:AAA"]
    ok, reason = evaluate_scenario_verdict(ids, observed_fn=lambda sid: False)
    assert ok is False


# ─── _scenario_ids_for_change — read the emitted dna:scenario ids ──────────


def _write_scen(tmp_path, stem, payload):
    d = tmp_path / ".changes"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{stem}.scenarios.jsonld").write_text(json.dumps(payload), encoding="utf-8")


def test_scenario_ids_reads_emitted_dna_ids(tmp_path):
    _write_scen(tmp_path, "feat-x", {"scenarios": [
        {"id": "dna:scenario:Y6Z1", "name": "a"},
        {"id": "dna:scenario:Q33B", "name": "b"},
    ]})
    assert _scenario_ids_for_change(tmp_path, "feat-x") == [
        "dna:scenario:Y6Z1", "dna:scenario:Q33B"]


def test_scenario_ids_ignores_pre_emit_sc_ids(tmp_path):
    # An authored-but-not-emitted file (SC-NN ids) has no emitted scenarios to
    # gate on — returns [] (scenario route N/A; the #301 presence gate + SRD
    # route cover those cases). Authored-not-emitted is a separate state.
    _write_scen(tmp_path, "feat-x", {"scenarios": [{"id": "SC-01", "name": "a"}]})
    assert _scenario_ids_for_change(tmp_path, "feat-x") == []


def test_scenario_ids_missing_file_is_empty(tmp_path):
    assert _scenario_ids_for_change(tmp_path, "feat-x") == []


def test_scenario_ids_malformed_is_empty(tmp_path):
    d = tmp_path / ".changes"
    d.mkdir(parents=True, exist_ok=True)
    (d / "feat-x.scenarios.jsonld").write_text("{not json", encoding="utf-8")
    assert _scenario_ids_for_change(tmp_path, "feat-x") == []
