"""Step dispatcher — execute ONE resolved Scenario step against a target.

Concrete `scripted`-tier drivers: `http_call` (stdlib urllib), `subprocess`
(no-shell argv), and `browser` (a real browser, deterministic — the machine half
of journey-rigor #6). `agent-step`-tier drivers (`mcp_server` /
`claude_code_tool` / `skill_invocation`) are DECLARED but their EXECUTION is
deferred to #92 (canonical need `agent-step-execution-mcp`): such a step returns
`deferred` with the tier echoed, the driver named in the `need`, and a detail
naming #92 — never a silent pass (ADR-001). Other un-wired kinds (`python_import`
/ `workflow_dispatch`) defer generically. A step whose `input_artifacts` (needs /
credentials) are not in the available set defers with the missing need named.
`mechanism: human` steps surface as `manual` checklist items.

UI / browser flows — two ways to drive them, picked per step by `mechanism`
(the same deterministic-vs-agent fork the system uses everywhere):
  - **deterministic** → the `browser` driver here (Playwright/CDP): scripted
    actions + an observable assert, reproducible — a real regression gate. It is
    `scripted`-tier (see `SCRIPTED_KINDS`) and may produce a real saved record.
  - **probabilistic / human** → the agent-driven browser (a browser MCP) or the
    human-attest path (`sulis-attest-scenario`, journey-rigor #6), for the messy
    interactive bits (e.g. an interactive sign-in). The agent-driven driver is
    the NEXT slice; this one is the deterministic half.
A browser step a machine can't yet complete (e.g. it needs a real session)
DEFERS with the need named — never a faked green.

Two fields surface the verification substrate (ADR-001, ADR-003):
  `StepOutcome.tier`         — echoed from `ResolvedStep.tier` for the run report.
  `StepOutcome.saved_record` — the REAL produced artifact captured from the
                               step result (never a fabricated record), which
                               the runner's verdict-invariant (WP-004) evaluates.

Transports (`http`, `run`, `browser`) are injected for unit-purity; the real
ones are lazy defaults (the runner / executable wires them). **The marketplace
is stdlib-only by contract**, so the browser transport's Playwright import is
OPTIONAL + lazy: present → deterministic browser proving; absent → the step
DEFERS (need: playwright) to the agent / human-attest path, never a fake. A
transport return MAY carry a `saved_record` attribute (the real artifact the
step produced); when absent, `saved_record` stays `None` — never synthesised.
The driver-specific params live in the step's `mechanism_detail` as a JSON blob:
  http_call → {"method","path","expect_status"}
  subprocess → {"cmd","expect_exit"}
  browser   → {"url","actions":[{"fill":sel,"value":v}|{"click":sel}|
               {"wait_for":sel}],"assert":{"visible":text}|{"url_contains":s}}

Stdlib only at import time. Python 3.11-safe.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

from _scenario_runtime import HUMAN_DRIVER, UNRESOLVED_DRIVER, ResolvedStep

# Drivers actually run here. Everything else automatable is deferred.
_IMPLEMENTED = {"http_call", "subprocess", "browser"}


class BrowserUnavailable(RuntimeError):
    """The deterministic browser transport (Playwright) isn't installed. The step
    DEFERS with the need named — it never fakes a pass. Playwright is an optional
    extra (stdlib-only contract); absent, browser proving falls to the agent /
    human-attest path."""


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


def _default_browser(url: str, actions: list, assert_spec: dict):
    """Drive a real browser deterministically via Playwright (lazy, optional).

    Returns ``SimpleNamespace(ok: bool, detail: str)``. Raises
    ``BrowserUnavailable`` if Playwright isn't installed — so the dispatcher
    defers rather than crashing or faking. This function is the real-browser
    integration point; the dispatcher branch below is transport-agnostic and is
    what the unit tests exercise (via an injected fake).
    """
    try:
        from playwright.sync_api import sync_playwright  # lazy, optional extra
    except ImportError as exc:  # stdlib-only contract — Playwright is opt-in
        raise BrowserUnavailable("playwright not installed") from exc

    with sync_playwright() as p:
        chrome = p.chromium.launch()
        try:
            page = chrome.new_page()
            page.goto(url)
            for a in actions:
                if "fill" in a:
                    page.fill(a["fill"], a.get("value", ""))
                elif "click" in a:
                    page.click(a["click"])
                elif "wait_for" in a:
                    page.wait_for_selector(a["wait_for"])
            if "visible" in assert_spec:
                text = assert_spec["visible"]
                ok = page.get_by_text(text).count() > 0
                return SimpleNamespace(ok=ok, detail=f"visible({text!r})={ok}")
            if "url_contains" in assert_spec:
                frag = assert_spec["url_contains"]
                ok = frag in page.url
                return SimpleNamespace(ok=ok, detail=f"url={page.url} contains({frag!r})={ok}")
            # no assert declared → reaching here without error is the pass
            return SimpleNamespace(ok=True, detail="reached end of journey, no assert")
        finally:
            chrome.close()


def execute_step(
    step: ResolvedStep,
    *,
    base_url: str = "",
    available_artifacts=frozenset(),
    http=None,
    run=None,
    browser=None,
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

    if step.driver == "browser":
        browser = browser or _default_browser
        url = str(params.get("url", ""))
        if url and not url.startswith(("http://", "https://")):
            url = base_url.rstrip("/") + "/" + url.lstrip("/")
        actions = params.get("actions", []) or []
        assert_spec = params.get("assert", {}) or {}
        try:
            result = browser(url, actions, assert_spec)
        except BrowserUnavailable as exc:
            # never a fake pass — defer with the need so it routes to the agent /
            # human-attest path.
            return StepOutcome(status="deferred", tier=step.tier, need="playwright",
                               detail=f"browser driver unavailable: {exc}")
        except Exception as exc:  # a real drive/assert failure
            return StepOutcome(status="fail", tier=step.tier,
                               detail=f"browser {url} raised {exc!r}")
        # The REAL produced artifact, if the deterministic browser run carries one
        # (ADR-003) — the verdict-invariant evaluates it; never synthesised.
        record = getattr(result, "saved_record", None)
        if getattr(result, "ok", False):
            return StepOutcome(status="pass", tier=step.tier, saved_record=record,
                               detail=getattr(result, "detail", "") or f"browser {url} ok")
        return StepOutcome(status="fail", tier=step.tier, saved_record=record,
                           detail=getattr(result, "detail", "") or f"browser {url} assert failed")

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
