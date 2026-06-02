"""Step dispatcher — execute ONE resolved Scenario step against a target.

v1 implements two concrete drivers — `http_call` (stdlib urllib) and `subprocess`
(shell) — and reports every other (agent-driven) kind as `deferred`
(not-yet-implemented). A step whose `input_artifacts` (needs / credentials)
are not in the available set defers with the missing need named — never a
silent pass. `mechanism: human` steps surface as `manual` checklist items.

Transports (`http`, `run`) are injected for unit-purity; the runner (WP-004)
wires the real httpx + subprocess. The driver-specific params live in the
step's `mechanism_detail` as a JSON blob:
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


@dataclass
class StepOutcome:
    status: str  # pass | fail | deferred | manual | unresolved
    detail: str = ""
    need: str | None = None  # set when status == deferred
    evidence: str = ""


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
        # Agent-driven + python_import + workflow_dispatch: real kinds, not yet
        # wired in v1. Deferred-with-need, never silent.
        return StepOutcome(status="deferred", need=f"driver:{step.driver}",
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
            return StepOutcome(status="fail",
                               detail=f"{method} {url} raised {exc!r}")
        got = getattr(resp, "status_code", None)
        if got == expect:
            return StepOutcome(status="pass", detail=f"{method} {url} → {got}")
        return StepOutcome(status="fail",
                           detail=f"{method} {url} → {got} (expected {expect})")

    # subprocess
    run = run or _default_run
    cmd = str(params.get("cmd", ""))
    expect_exit = int(params.get("expect_exit", 0))
    try:
        result = run(cmd)
    except Exception as exc:
        return StepOutcome(status="fail", detail=f"`{cmd}` raised {exc!r}")
    rc = getattr(result, "returncode", None)
    if rc == expect_exit:
        return StepOutcome(status="pass", detail=f"`{cmd}` → exit {rc}")
    return StepOutcome(status="fail",
                       detail=f"`{cmd}` → exit {rc} (expected {expect_exit})")
