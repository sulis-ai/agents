"""WP-004 (testable-state-done) — the runner core.

`run_scenario` composes the runtime (WP-001) + dispatcher (WP-002): resolve the
journey, execute each step against a target, aggregate into a per-Scenario
verdict. `format_founder_summary` renders plain green/red a non-technical
founder reads. Verdict precedence (worst-wins): fail > unresolved > deferred >
manual-pending > pass — so the DoD gate (WP-005) treats only `pass` as
done-qualifying and surfaces `deferred` needs rather than faking green.

Transports injected → unit-pure (the executable wraps graph-I/O + standup).

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from _scenario_runner import format_founder_summary, run_scenario

_TOOLS = {"dna:tool:http": {"@id": "dna:tool:http", "implementation_kind": "http_call"}}


def _journey(*step_ids):
    return {"@id": "dna:workflow:j", "steps": list(step_ids)}


def _http_step(sid, path, expect, **kw):
    return {
        "@id": sid, "name": f"GET {path}", "mechanism": "deterministic",
        "tool_ref": "dna:tool:http",
        "mechanism_detail": json.dumps({"method": "GET", "path": path, "expect_status": expect}),
        **kw,
    }


_SCENARIO = {"@id": "dna:scenario:login", "name": "A new user can sign up and log in",
             "journey": "dna:workflow:j"}


def _run(steps, *, http, **kw):
    steps_by_id = {s["@id"]: s for s in steps}
    wf = _journey(*[s["@id"] for s in steps])
    return run_scenario(_SCENARIO, wf, steps_by_id, _TOOLS,
                        target_base_url="http://local", http=http, **kw)


def test_all_pass_verdict_pass():
    steps = [_http_step("a", "/signup", 200), _http_step("b", "/dashboard", 200)]
    res = _run(steps, http=lambda m, u: SimpleNamespace(status_code=200))
    assert res.verdict == "pass"
    assert all(s["status"] == "pass" for s in res.steps)


def test_one_fail_verdict_fail():
    steps = [_http_step("a", "/signup", 200), _http_step("b", "/dashboard", 200)]
    # /dashboard returns 500
    http = lambda m, u: SimpleNamespace(status_code=200 if "signup" in u else 500)
    res = _run(steps, http=http)
    assert res.verdict == "fail"


def test_missing_need_verdict_deferred_and_surfaces_need():
    steps = [_http_step("a", "/charge", 200, input_artifacts=["secret:stripe-test-key"])]
    res = _run(steps, http=lambda m, u: SimpleNamespace(status_code=200),
               available_artifacts=frozenset())
    assert res.verdict == "deferred"
    assert any("stripe-test-key" in (s.get("need") or "") for s in res.steps)


def test_human_step_verdict_manual_pending():
    steps = [_http_step("a", "/signup", 200),
             {"@id": "h", "name": "eyeball welcome email", "mechanism": "human"}]
    res = _run(steps, http=lambda m, u: SimpleNamespace(status_code=200))
    assert res.verdict == "manual-pending"


def test_fail_beats_deferred():
    steps = [_http_step("a", "/charge", 200, input_artifacts=["secret:x"]),
             _http_step("b", "/dashboard", 200)]
    http = lambda m, u: SimpleNamespace(status_code=500)
    res = _run(steps, http=http, available_artifacts=frozenset())
    assert res.verdict == "fail"  # the /dashboard fail wins over the deferred /charge


def test_founder_summary_is_plain():
    steps = [_http_step("a", "/signup", 200)]
    res = _run(steps, http=lambda m, u: SimpleNamespace(status_code=200))
    summary = format_founder_summary(res)
    assert "A new user can sign up and log in" in summary
    assert "✓" in summary or "pass" in summary.lower()
