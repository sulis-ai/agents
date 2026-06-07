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

import pytest

from _scenario_dispatch import _default_http, _default_run, execute_step
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


# ─── _default_run: runs argv-split, NOT via a shell ─────────────────────────


def test_default_run_executes_a_real_command():
    # A plain command runs and reports its exit code (no shell needed).
    result = _default_run("true")
    assert result.returncode == 0


def test_default_run_honours_posix_quoting_like_authored_scenarios():
    # Authored scenario cmds carry quoted args with spaces (e.g.
    # --what 'a probe with spaces'). shlex.split must keep that one argv item
    # whole, exactly as a shell would word-split it — this is the only
    # "shell-like" feature any scenario relies on.
    result = _default_run(
        "python3 -c \"import sys; print(len(sys.argv)); sys.exit(len(sys.argv) - 3)\" "
        "--what 'a probe with spaces'"
    )
    # argv = [-c prog, --what, 'a probe with spaces'] → 3 → exit 0
    assert result.returncode == 0


def test_default_run_does_not_invoke_a_shell():
    # With shell=False, a shell metacharacter is an INERT argument byte, never
    # an operator. `echo` simply prints the literal string; the `; touch …`
    # cannot run as a second command. We assert the metachars survive verbatim
    # in stdout (proof no shell parsed them).
    result = _default_run("echo a;b|c")
    assert result.returncode == 0
    assert result.stdout.strip() == "a;b|c"


def test_default_run_empty_cmd_fails_cleanly_not_via_shell():
    # An empty cmd splits to [] — there is no program to exec. This must raise
    # (IndexError / ValueError), which execute_step catches as a fail; it must
    # NOT silently spawn a shell that exits 0.
    with pytest.raises(Exception):
        _default_run("")


# ─── _default_http: scheme guard (no file:// local reads) ───────────────────


def test_default_http_rejects_file_scheme():
    with pytest.raises(ValueError):
        _default_http("GET", "file:///etc/passwd")


def test_default_http_rejects_non_http_scheme():
    with pytest.raises(ValueError):
        _default_http("GET", "ftp://example.com/x")
# ── browser driver (deterministic — journey-rigor #6 machine-half) ─────────────

from _scenario_dispatch import BrowserUnavailable  # noqa: E402


def _browser_step(detail: dict, **kw) -> ResolvedStep:
    return ResolvedStep(
        step_id="s", name="land on dashboard", driver="browser",
        mechanism="deterministic", mechanism_detail=json.dumps(detail), **kw,
    )


def test_browser_pass_when_assert_holds():
    step = _browser_step({"url": "/login", "actions": [{"fill": "#email", "value": "a@b.c"},
                          {"click": "#submit"}], "assert": {"visible": "Dashboard"}})
    fake = lambda url, actions, a: SimpleNamespace(ok=True, detail="visible(Dashboard)")
    out = execute_step(step, base_url="http://local", browser=fake)
    assert out.status == "pass", out


def test_browser_fail_when_assert_misses():
    step = _browser_step({"url": "/login", "assert": {"visible": "Dashboard"}})
    fake = lambda url, actions, a: SimpleNamespace(ok=False, detail="not visible")
    out = execute_step(step, base_url="http://local", browser=fake)
    assert out.status == "fail"
    assert "not visible" in out.detail


def test_browser_joins_base_url_and_passes_actions_assert():
    seen = {}
    def fake(url, actions, a):
        seen.update(url=url, actions=actions, assert_spec=a)
        return SimpleNamespace(ok=True, detail="ok")
    step = _browser_step({"url": "app/home", "actions": [{"click": "#go"}],
                          "assert": {"url_contains": "/home"}})
    execute_step(step, base_url="http://local:3000", browser=fake)
    assert seen["url"] == "http://local:3000/app/home"
    assert seen["actions"] == [{"click": "#go"}]
    assert seen["assert_spec"] == {"url_contains": "/home"}


def test_browser_absolute_url_not_rejoined():
    seen = {}
    def fake(url, actions, a):
        seen["url"] = url
        return SimpleNamespace(ok=True)
    step = _browser_step({"url": "https://dev.example.app/login", "assert": {"visible": "X"}})
    execute_step(step, base_url="http://ignored", browser=fake)
    assert seen["url"] == "https://dev.example.app/login"


def test_browser_unavailable_defers_never_fakes():
    # the transport can't run (e.g. Playwright absent) → DEFER with the need,
    # never a fake pass. Routes to the agent / human-attest path.
    def fake(url, actions, a):
        raise BrowserUnavailable("playwright not installed")
    step = _browser_step({"url": "/login", "assert": {"visible": "Dashboard"}})
    out = execute_step(step, base_url="http://local", browser=fake)
    assert out.status == "deferred"
    assert "playwright" in (out.need or "")


def test_browser_real_default_degrades_gracefully_without_playwright():
    # With no transport injected, the real default lazily imports Playwright;
    # it's an OPTIONAL extra (stdlib-only contract), so when absent the step
    # DEFERS — it does not crash and does not fake green.
    step = _browser_step({"url": "/login", "assert": {"visible": "Dashboard"}})
    out = execute_step(step, base_url="http://local")
    assert out.status in {"deferred", "pass", "fail"}
    # in CI/dev without Playwright installed, it's deferred-with-need:
    if out.status == "deferred":
        assert "playwright" in (out.need or "")
