"""Step dispatcher — execute ONE resolved Scenario step against a target.

v1 implements two concrete `scripted`-tier drivers — `http_call` (stdlib
urllib) and `subprocess` (shell). `agent-step`-tier drivers (`mcp_server` /
`claude_code_tool` / `skill_invocation`) are DECLARED but their EXECUTION is
deferred to #92 (canonical need `agent-step-execution-mcp`): such a step
returns `deferred` with the tier echoed, the driver named in the `need`, and a
detail naming #92 — never a silent pass (ADR-001). Other un-wired kinds
(`python_import` / `workflow_dispatch`) defer generically. A step whose
`input_artifacts` (needs / credentials) are not in the available set defers
with the missing need named. `mechanism: human` steps surface as `manual`
checklist items.

Two fields surface the verification substrate (ADR-001, ADR-003):
  `StepOutcome.tier`         — echoed from `ResolvedStep.tier` for the run report.
  `StepOutcome.saved_record` — the REAL produced artifact captured from the
                               step result (never a fabricated record), which
                               the runner's verdict-invariant (WP-004) evaluates.

Transports (`http`, `run`) are injected for unit-purity; the runner (WP-004)
wires the real httpx + subprocess. A transport return MAY carry a
`saved_record` attribute (the real artifact the step produced); when absent,
`saved_record` stays `None` — it is never synthesised. The driver-specific
params live in the step's `mechanism_detail` as a JSON blob:
  http_call → {"method","path","expect_status"}
  subprocess → {"cmd","expect_exit"}

Stdlib only. Python 3.11-safe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

from _scenario_runtime import HUMAN_DRIVER, UNRESOLVED_DRIVER, ResolvedStep

# Drivers WP-002 actually runs. Everything else automatable is deferred.
_IMPLEMENTED = {"http_call", "subprocess"}

# The agent-step tier's EXECUTION is owned by #92; the canonical need
# identifier the deferral names. Declared here, executed there (ADR-001).
_AGENT_STEP_NEED = "agent-step-execution-mcp"
_AGENT_STEP_OWNER = "#92"


@dataclass
class StepOutcome:
    status: str  # pass | fail | deferred | manual | unresolved
    detail: str = ""
    need: str | None = None  # set when status == deferred
    evidence: str = ""
    tier: str = ""  # echoed from ResolvedStep.tier, for the run report (ADR-001)
    # The REAL produced artifact captured from the step result — what the
    # runner's verdict-invariant evaluates (ADR-003). Never a fabricated record;
    # None when the step result carries none.
    saved_record: dict | None = None


def _default_http(method: str, url: str):
    # Stdlib only (the marketplace tooling is stdlib-only by contract — no
    # httpx dependency). A 4xx/5xx surfaces as a status_code, NOT an exception,
    # so the dispatcher compares it to expect_status; a real connection error
    # propagates and the caller marks the step failed.
    import urllib.error
    import urllib.request

    req = urllib.request.Request(url, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return SimpleNamespace(status_code=getattr(resp, "status", resp.getcode()))
    except urllib.error.HTTPError as exc:
        return SimpleNamespace(status_code=exc.code)


def _default_run(cmd: str):
    import subprocess  # lazy

    return subprocess.run(cmd, shell=True, capture_output=True, text=True)


def execute_step(
    step: ResolvedStep,
    *,
    base_url: str = "",
    available_artifacts=frozenset(),
    http=None,
    run=None,
) -> StepOutcome:
    """Execute one resolved step; return a StepOutcome."""
    if step.driver == HUMAN_DRIVER:
        return StepOutcome(status="manual",
                           detail=step.agent_instructions or step.name)
    if step.driver == UNRESOLVED_DRIVER:
        return StepOutcome(status="unresolved",
                           detail=f"step '{step.name}' resolves to no driver")

    # Precondition: every declared need must be available, else defer (don't fake).
    missing = [a for a in step.input_artifacts if a not in available_artifacts]
    if missing:
        return StepOutcome(status="deferred", need=", ".join(missing),
                           detail=f"missing needs: {', '.join(missing)}")

    if step.driver not in _IMPLEMENTED:
        if step.tier == "agent-step":
            # agent-step tier is DECLARED here; its EXECUTION (browser-MCP /
            # LLM-judged step running) folds into #92. Defer with the tier
            # echoed and the owner named — never silent (ADR-001).
            return StepOutcome(
                status="deferred",
                tier=step.tier,
                need=f"driver:{step.driver}",
                detail=(f"agent-step tier — execution deferred to "
                        f"{_AGENT_STEP_OWNER} (need: {_AGENT_STEP_NEED})"),
            )
        # python_import / workflow_dispatch (tier ""): real kinds, not yet
        # wired in v1. Deferred-with-need, never silent.
        return StepOutcome(status="deferred", tier=step.tier,
                           need=f"driver:{step.driver}",
                           detail=f"driver '{step.driver}' not yet implemented")

    try:
        params = json.loads(step.mechanism_detail) if step.mechanism_detail else {}
    except (json.JSONDecodeError, TypeError) as exc:
        return StepOutcome(status="fail",
                           detail=f"bad mechanism_detail for '{step.name}': {exc}")

    if step.driver == "http_call":
        http = http or _default_http
        method = str(params.get("method", "GET")).upper()
        url = base_url.rstrip("/") + "/" + str(params.get("path", "")).lstrip("/")
        expect = int(params.get("expect_status", 200))
        try:
            resp = http(method, url)
        except Exception as exc:  # transport/network failure is a real fail
            return StepOutcome(status="fail", tier=step.tier,
                               detail=f"{method} {url} raised {exc!r}")
        got = getattr(resp, "status_code", None)
        # The REAL produced artifact, if the transport carries one (ADR-003):
        record = getattr(resp, "saved_record", None)
        if got == expect:
            return StepOutcome(status="pass", tier=step.tier,
                               saved_record=record,
                               detail=f"{method} {url} → {got}")
        return StepOutcome(status="fail", tier=step.tier, saved_record=record,
                           detail=f"{method} {url} → {got} (expected {expect})")

    # subprocess
    run = run or _default_run
    cmd = str(params.get("cmd", ""))
    expect_exit = int(params.get("expect_exit", 0))
    try:
        result = run(cmd)
    except Exception as exc:
        return StepOutcome(status="fail", tier=step.tier,
                           detail=f"`{cmd}` raised {exc!r}")
    rc = getattr(result, "returncode", None)
    record = getattr(result, "saved_record", None)
    if rc == expect_exit:
        return StepOutcome(status="pass", tier=step.tier, saved_record=record,
                           detail=f"`{cmd}` → exit {rc}")
    return StepOutcome(status="fail", tier=step.tier, saved_record=record,
                       detail=f"`{cmd}` → exit {rc} (expected {expect_exit})")
