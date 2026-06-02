"""WP-006 (testable-state-done) — Scenario↔implementation drift.

A Scenario is authored up front; the implementation can drift away from it (a
flow changes, an endpoint moves, a tool is removed). Drift detection flags a
Scenario whose journey-step referents no longer resolve against the
implementation — so the cases stay truthful, not silently stale. Same shape as
the Path-A canonical-drift detector: a finding per unresolved referent.

`referent_exists` is injected (the runner wires the real check — the http path
is declared in the ServiceSpec / the subprocess cmd resolves). Human steps have
no automatable referent and are skipped.

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

from _scenario_drift import detect_scenario_drift
from _scenario_runtime import ResolvedStep


def _step(name, driver, mechanism="deterministic"):
    return ResolvedStep(step_id=name, name=name, driver=driver, mechanism=mechanism)


def test_no_drift_when_all_referents_exist():
    steps = [_step("a", "http_call"), _step("b", "subprocess")]
    findings = detect_scenario_drift(steps, referent_exists=lambda s: True)
    assert findings == []


def test_unresolved_driver_is_drift():
    steps = [_step("gone", "unresolved")]
    findings = detect_scenario_drift(steps, referent_exists=lambda s: True)
    assert len(findings) == 1
    assert "gone" == findings[0].step_name
    assert "driver" in findings[0].reason.lower() or "unresolved" in findings[0].reason.lower()


def test_missing_referent_is_drift():
    steps = [_step("a", "http_call")]
    findings = detect_scenario_drift(steps, referent_exists=lambda s: False)
    assert len(findings) == 1
    assert "referent" in findings[0].reason.lower()


def test_human_step_skipped():
    steps = [_step("eyeball", "human", mechanism="human")]
    findings = detect_scenario_drift(steps, referent_exists=lambda s: False)
    assert findings == []  # no automatable referent to drift


def test_mixed_reports_only_the_drifted():
    steps = [_step("ok", "http_call"), _step("moved", "http_call"), _step("gone", "unresolved")]
    referent_exists = lambda s: s.name != "moved"
    findings = detect_scenario_drift(steps, referent_exists=referent_exists)
    assert {f.step_name for f in findings} == {"moved", "gone"}
