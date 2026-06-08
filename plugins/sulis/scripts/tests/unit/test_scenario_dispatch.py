"""WP-002 (testable-state-done) — the Step dispatcher + drivers.

Executes ONE resolved step against a target, returning a StepOutcome
(pass | fail | deferred | manual | unresolved). v1 implements the two concrete
drivers `http_call` (httpx) + `subprocess` (shell); agent-driven kinds
(mcp_server / claude_code_tool / skill_invocation / workflow_dispatch /
python_import) are reported `deferred` (not-yet-implemented). A step whose
`input_artifacts` (needs/credentials) aren't available → `deferred:<need>` —
never silently passed.

Transports (http / run) are injected so this is unit-pure (no network, no
shell). The runner (WP-004) wires the real httpx + subprocess.

Stdlib + pytest. Python 3.11-safe.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

from _scenario_dispatch import execute_step
from _scenario_runtime import ResolvedStep


def _http_step(detail: dict, **kw) -> ResolvedStep:
    return ResolvedStep(
        step_id="s", name="POST /x", driver="http_call", mechanism="deterministic",
        mechanism_detail=json.dumps(detail), **kw,
    )


def test_http_call_pass():
    step = _http_step({"method": "GET", "path": "/dashboard", "expect_status": 200})
    http = lambda method, url: SimpleNamespace(status_code=200)
    out = execute_step(step, base_url="http://local", http=http)
    assert out.status == "pass", out


def test_http_call_fail_on_wrong_status():
    step = _http_step({"method": "GET", "path": "/dashboard", "expect_status": 200})
    http = lambda method, url: SimpleNamespace(status_code=500)
    out = execute_step(step, base_url="http://local", http=http)
    assert out.status == "fail"
    assert "500" in out.detail


def test_http_call_hits_base_url_plus_path():
    seen = {}
    def http(method, url):
        seen["url"] = url; seen["method"] = method
        return SimpleNamespace(status_code=200)
    step = _http_step({"method": "POST", "path": "/signup", "expect_status": 200})
    execute_step(step, base_url="http://local:5173", http=http)
    assert seen == {"url": "http://local:5173/signup", "method": "POST"}


def test_subprocess_pass():
    step = ResolvedStep(step_id="s", name="run spec", driver="subprocess",
                        mechanism="deterministic",
                        mechanism_detail=json.dumps({"cmd": "true", "expect_exit": 0}))
    run = lambda cmd: SimpleNamespace(returncode=0)
    out = execute_step(step, run=run)
    assert out.status == "pass", out


def test_subprocess_fail():
    step = ResolvedStep(step_id="s", name="run spec", driver="subprocess",
                        mechanism="deterministic",
                        mechanism_detail=json.dumps({"cmd": "false", "expect_exit": 0}))
    run = lambda cmd: SimpleNamespace(returncode=1)
    out = execute_step(step, run=run)
    assert out.status == "fail"


def test_missing_input_artifact_defers_with_need():
    step = _http_step({"method": "GET", "path": "/x", "expect_status": 200},
                      input_artifacts=["secret:stripe-test-key"])
    out = execute_step(step, base_url="http://local", available_artifacts=frozenset(),
                       http=lambda m, u: SimpleNamespace(status_code=200))
    assert out.status == "deferred"
    assert "secret:stripe-test-key" in (out.need or "")


def test_available_artifact_proceeds():
    step = _http_step({"method": "GET", "path": "/x", "expect_status": 200},
                      input_artifacts=["secret:stripe-test-key"])
    out = execute_step(step, base_url="http://local",
                       available_artifacts=frozenset({"secret:stripe-test-key"}),
                       http=lambda m, u: SimpleNamespace(status_code=200))
    assert out.status == "pass"


def test_human_step_is_manual():
    step = ResolvedStep(step_id="s", name="eyeball email", driver="human", mechanism="human")
    out = execute_step(step)
    assert out.status == "manual"


def test_unresolved_step():
    step = ResolvedStep(step_id="s", name="?", driver="unresolved", mechanism="deterministic")
    out = execute_step(step)
    assert out.status == "unresolved"


def test_agent_driven_kind_is_deferred_not_yet_implemented():
    step = ResolvedStep(step_id="s", name="login via agent", driver="mcp_server",
                        mechanism="mixed")
    out = execute_step(step, base_url="http://local")
    assert out.status == "deferred"
    assert "mcp_server" in (out.need or "")


# --- WP-003: tier echo + saved_record capture + named agent-step deferral ---


def test_agent_step_defers_to_92():
    """An agent-step-tier step (mcp_server) defers with the tier echoed, the
    driver named in the need, AND a detail naming #92 as the execution owner —
    never silent (ADR-001 sharpening of today's never-silent contract)."""
    step = ResolvedStep(step_id="s", name="login via agent", driver="mcp_server",
                        mechanism="mixed", tier="agent-step")
    out = execute_step(step, base_url="http://local")
    assert out.status == "deferred", out
    assert out.tier == "agent-step", out
    assert out.need == "driver:mcp_server", out
    assert "#92" in out.detail, out


def test_dispatch_captures_saved_record():
    """The dispatcher captures the REAL saved record from the step result onto
    StepOutcome.saved_record (ADR-003 real-data-not-mock guard) — and leaves it
    None when the step result carries none."""
    record = {"user_id": "u_123", "email": "a@b.test"}

    def http_with_record(method, url):
        # Real-shaped transport return carrying the produced artifact.
        return SimpleNamespace(status_code=200, saved_record=record)

    step = _http_step({"method": "POST", "path": "/signup", "expect_status": 200})
    out = execute_step(step, base_url="http://local", http=http_with_record)
    assert out.status == "pass", out
    assert out.saved_record == record, out

    # No record on the result → saved_record stays None (not fabricated).
    step2 = _http_step({"method": "GET", "path": "/dashboard", "expect_status": 200})
    out2 = execute_step(step2, base_url="http://local",
                        http=lambda m, u: SimpleNamespace(status_code=200))
    assert out2.status == "pass", out2
    assert out2.saved_record is None, out2


def test_scripted_step_still_executes():
    """Characterisation (EP-07): an http_call scripted step against an injected
    transport still passes, now additionally echoing tier == 'scripted'. Proves
    the additive edit preserves existing behaviour."""
    step = _http_step({"method": "GET", "path": "/dashboard", "expect_status": 200},
                      tier="scripted")
    out = execute_step(step, base_url="http://local",
                       http=lambda m, u: SimpleNamespace(status_code=200))
    assert out.status == "pass", out
    assert out.tier == "scripted", out
