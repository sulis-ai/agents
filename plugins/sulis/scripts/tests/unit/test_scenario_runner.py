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

from _scenario_runner import (
    _POLL_ATTEMPTS_MAX,
    evaluate_invariant,
    format_founder_summary,
    run_scenario,
)

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


def test_journey_internal_dataflow_is_available_not_deferred():
    """An input_artifact produced by an earlier step in the same journey is
    available to a later step — the journey's own data-flow chain, not an
    external need. Without this, every multi-step authored journey defers on
    its own chaining (the authoring assembler links step N+1's input to step
    N's output). The ``test-target`` entry seed is available to the first step.
    """
    first = _http_step("a", "/signup", 200,
                       input_artifacts=["test-target"],
                       output_artifacts=["session"])
    second = _http_step("b", "/dashboard", 200,
                        input_artifacts=["session"],  # produced by `first`
                        output_artifacts=["dash-result"])
    res = _run([first, second],
               http=lambda m, u: SimpleNamespace(status_code=200),
               available_artifacts=frozenset())  # nothing supplied externally
    assert res.verdict == "pass", res.steps
    assert all(s["status"] == "pass" for s in res.steps)


def test_external_need_still_defers_even_with_dataflow():
    """A genuinely-external need (never produced by any step) still defers —
    the data-flow shortcut doesn't fake green for real missing credentials."""
    step = _http_step("a", "/charge", 200,
                      input_artifacts=["test-target", "secret:stripe-key"],
                      output_artifacts=["charge-result"])
    res = _run([step], http=lambda m, u: SimpleNamespace(status_code=200),
               available_artifacts=frozenset())
    assert res.verdict == "deferred"
    assert any("stripe-key" in (s.get("need") or "") for s in res.steps)


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


# --- WP-004: isolation rung + verdict-invariant evaluator -------------------

def _http_step_with_record(sid, path, expect, record, **kw):
    """An http step whose transport carries a REAL saved_record (the artifact
    the dispatcher captures off the step result — never fabricated)."""
    return _http_step(sid, path, expect, **kw), record


def test_isolation_rung_default_and_recorded():
    """No `isolation` field → the cheapest-sufficient default `reset` is
    recorded; a Scenario declaring `isolation: env` → `env` recorded. The pure
    core records INTENT only — no process/env EXECUTION here (ADR-002)."""
    steps = [_http_step("a", "/signup", 200)]
    http = lambda m, u: SimpleNamespace(status_code=200)

    # default (field absent)
    res_default = _run(steps, http=http)
    assert res_default.isolation_rung == "reset"

    # explicit env
    scenario_env = dict(_SCENARIO, isolation="env")
    steps_by_id = {s["@id"]: s for s in steps}
    wf = _journey(*[s["@id"] for s in steps])
    res_env = run_scenario(scenario_env, wf, steps_by_id, _TOOLS,
                           target_base_url="http://local", http=http)
    assert res_env.isolation_rung == "env"


def test_verdict_invariant_equality():
    """kind=equality: saved_record == expected → observed; mismatch → blocked.
    Evaluated over the REAL saved record (never a mock)."""
    expected = {"user": "ada", "status": "active"}
    invariant = {"kind": "equality", "expected": expected}

    assert evaluate_invariant(invariant, {"user": "ada", "status": "active"}) == "observed"
    assert evaluate_invariant(invariant, {"user": "ada", "status": "pending"}) == "blocked"
    # absent saved record can never equal a declared expected shape → blocked
    assert evaluate_invariant(invariant, None) == "blocked"


def test_verdict_invariant_property_bounded_poll():
    """kind=property: a record matching shape X appeared → observed; bounded
    poll exhausted → blocked. Poll is BOUNDED — `sleep` injected so the test
    never waits; the hard-max ceiling clamps an over-large `attempts`."""
    slept: list = []

    def sleep(_secs):
        slept.append(_secs)

    # The shape predicate: a record carrying status == "saved".
    invariant_appears = {
        "kind": "property",
        "expected": {"status": "saved"},
        "poll": {"attempts": 3, "interval_ms": 10},
    }

    # A fetcher (callable saved_record) that only matches on the 2nd read.
    calls = {"n": 0}

    def fetch_on_second():
        calls["n"] += 1
        return {"status": "saved"} if calls["n"] >= 2 else {"status": "pending"}

    assert evaluate_invariant(invariant_appears, fetch_on_second, sleep=sleep) == "observed"
    assert calls["n"] == 2            # stopped as soon as it matched
    assert len(slept) == 1            # slept once between attempt 1 and 2

    # Never matches → poll exhausted → blocked (honest, never a fake pass).
    never = {"kind": "property", "expected": {"status": "saved"},
             "poll": {"attempts": 3, "interval_ms": 10}}
    assert evaluate_invariant(never, lambda: {"status": "pending"}) == "blocked"

    # Hard-max ceiling: an over-large `attempts` is clamped so a misauthored
    # scenario cannot spin. Count the reads against a never-matching fetcher.
    reads = {"n": 0}

    def count_reads():
        reads["n"] += 1
        return {"status": "pending"}

    over = {"kind": "property", "expected": {"status": "saved"},
            "poll": {"attempts": _POLL_ATTEMPTS_MAX + 1000, "interval_ms": 0}}
    assert evaluate_invariant(over, count_reads, sleep=lambda _s: None) == "blocked"
    assert reads["n"] == _POLL_ATTEMPTS_MAX   # clamped, not the over-large value


def test_invariant_result_empty_when_absent():
    """A Scenario with no `verdict_invariant` → invariant_result == ""."""
    steps = [_http_step("a", "/signup", 200)]
    res = _run(steps, http=lambda m, u: SimpleNamespace(status_code=200))
    assert res.invariant_result == ""
    # And the pure evaluator agrees: None/absent invariant → "".
    assert evaluate_invariant(None, {"any": "record"}) == ""
    assert evaluate_invariant({}, {"any": "record"}) == ""


def test_verdict_invariant_malformed_poll_fails_closed_blocked():
    """A verification engine FAILS CLOSED HONESTLY — it never crashes. The pure
    `evaluate_invariant` can be called directly with a hand-built bundle that
    bypassed schema validation, so a `property` poll may carry a non-numeric
    `attempts`/`interval_ms` (e.g. `"abc"`). Such a malformed poll value must
    yield `"blocked"` (the honest "couldn't confirm"), NEVER a raised
    ValueError/TypeError that takes the whole run down."""
    expected = {"status": "saved"}

    # Non-numeric `attempts` → blocked, no exception.
    bad_attempts = {"kind": "property", "expected": expected,
                    "poll": {"attempts": "abc", "interval_ms": 0}}
    assert evaluate_invariant(bad_attempts, {"status": "saved"}) == "blocked"

    # Non-numeric `interval_ms` → blocked, no exception.
    bad_interval = {"kind": "property", "expected": expected,
                    "poll": {"attempts": 3, "interval_ms": "soon"}}
    assert evaluate_invariant(bad_interval, {"status": "saved"}) == "blocked"

    # Both malformed → blocked.
    both_bad = {"kind": "property", "expected": expected,
                "poll": {"attempts": None, "interval_ms": []}}
    assert evaluate_invariant(both_bad, {"status": "saved"}) == "blocked"

    # A malformed poll must not even invoke the saved-record fetcher down a
    # path that would otherwise observe — fail-closed precedes the poll.
    reads = {"n": 0}

    def count_reads():
        reads["n"] += 1
        return {"status": "saved"}

    assert evaluate_invariant(bad_attempts, count_reads) == "blocked"
    assert reads["n"] == 0  # never polled — bailed before the loop


def test_disposition_precedence_unchanged():
    """Characterisation: the worst-wins fold (fail > unresolved > deferred >
    manual > pass) produces the SAME `verdict` as today. The additive
    isolation/invariant fields must not perturb the disposition."""
    def http_ok(m, u):
        return SimpleNamespace(status_code=200)

    # all pass → pass
    assert _run([_http_step("a", "/x", 200)], http=http_ok).verdict == "pass"

    # a fail wins over everything
    def fail_http(m, u):
        return SimpleNamespace(status_code=500)

    assert _run([_http_step("a", "/x", 200)], http=fail_http).verdict == "fail"

    # fail beats a deferred (external missing need)
    mixed = [_http_step("a", "/charge", 200, input_artifacts=["secret:x"]),
             _http_step("b", "/dash", 200)]
    assert _run(mixed, http=fail_http, available_artifacts=frozenset()).verdict == "fail"

    # a human step with otherwise-passing steps → manual-pending
    human = [_http_step("a", "/x", 200),
             {"@id": "h", "name": "eyeball", "mechanism": "human"}]
    assert _run(human, http=http_ok).verdict == "manual-pending"

    # a deferred-only run → deferred (not faked green)
    deferred_only = [_http_step("a", "/charge", 200, input_artifacts=["secret:x"])]
    assert _run(deferred_only, http=http_ok,
                available_artifacts=frozenset()).verdict == "deferred"
