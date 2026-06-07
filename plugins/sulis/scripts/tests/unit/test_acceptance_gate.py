"""WP-005 (testable-state-done) — the DoD gate decision.

"Done" requires every in-scope Scenario to PASS or be DEFERRED-WITH-NEED. A
`fail` (broken) or `manual-pending` (a human step not yet confirmed) BLOCKS
done; a `deferred` is an acknowledged, recorded gap (a credential/infra not
available) and does NOT block — but its need is surfaced. This is the real,
honest "done": grounded in the gate that matters (the app is testable), not in
"merged".

Pure decision over a list of AcceptanceResult (WP-004).

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

from _acceptance_gate import gate_decision, format_gate_message
from _scenario_runner import AcceptanceResult


def _res(name, verdict, needs=None):
    steps = [{"name": "s", "status": "deferred", "detail": "", "need": n} for n in (needs or [])]
    return AcceptanceResult(scenario_id=name, scenario_name=name, verdict=verdict, steps=steps)


def test_all_pass_gate_passes():
    d = gate_decision([_res("login", "pass"), _res("billing", "pass")])
    assert d.verdict == "pass"
    assert d.blocking == []


def test_fail_blocks():
    d = gate_decision([_res("login", "pass"), _res("billing", "fail")])
    assert d.verdict == "blocked"
    assert "billing" in [b["scenario"] for b in d.blocking]


def test_manual_pending_blocks():
    d = gate_decision([_res("login", "manual-pending")])
    assert d.verdict == "blocked"


def test_deferred_blocks_by_default_observed_or_blocked():
    # The #83 fix: a deferred (never-driven) outcome is NOT done. Default strict.
    d = gate_decision([_res("login", "pass"),
                       _res("billing", "deferred", needs=["secret:stripe-test-key"])])
    assert d.verdict == "blocked"
    assert "billing" in [b["scenario"] for b in d.blocking]
    # the need is still surfaced (both in the blocking why and deferred_needs)
    assert "secret:stripe-test-key" in d.deferred_needs


def test_deferred_records_without_blocking_only_with_allow_deferred():
    # The conscious opt-out: require_observed=False restores legacy behaviour.
    d = gate_decision([_res("login", "pass"),
                       _res("billing", "deferred", needs=["secret:stripe-test-key"])],
                      require_observed=False)
    assert d.verdict == "pass"
    assert "secret:stripe-test-key" in d.deferred_needs


def test_fail_beats_deferred():
    d = gate_decision([_res("a", "deferred", needs=["x"]), _res("b", "fail")])
    assert d.verdict == "blocked"


def test_gate_message_is_founder_english():
    d = gate_decision([_res("billing", "fail")])
    msg = format_gate_message(d)
    assert "billing" in msg
    assert "done" in msg.lower() or "can't" in msg.lower() or "not" in msg.lower()
