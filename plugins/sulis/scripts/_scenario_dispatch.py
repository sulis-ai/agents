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
    import urllib.parse
    import urllib.request

    # Scheme guard: only real web requests. urllib would otherwise honour
    # file:// (read a local file), ftp://, etc. from an authored scenario URL.
    scheme = urllib.parse.urlsplit(url).scheme.lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"unsupported URL scheme {scheme!r} (http/https only): {url}")

    req = urllib.request.Request(url, method=method)
    try:
        # Mitigated: the scheme guard above rejects file://, ftp://, etc. — only
        # http/https reach urlopen, so no arbitrary-local-file read is possible.
        resp = urllib.request.urlopen(req, timeout=15)  # noqa: S310  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        return SimpleNamespace(status_code=getattr(resp, "status", resp.getcode()))
    except urllib.error.HTTPError as exc:
        return SimpleNamespace(status_code=exc.code)


def _default_run(cmd: str):
    # No shell. `cmd` is authored-scenario content (trusted, local test
    # tooling), but no scenario relies on shell features — pipes, redirects,
    # `&&`, globs — so shell=True would only add an injection surface for zero
    # benefit. shlex.split reproduces the one shell-like feature scenarios DO
    # use (POSIX quoting of args with spaces, e.g. --what 'a b c') as argv,
    # exactly as the shell would word-split it.
    import shlex
    import subprocess  # lazy

    return subprocess.run(shlex.split(cmd), capture_output=True, text=True)


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
