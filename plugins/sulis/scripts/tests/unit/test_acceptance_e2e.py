"""WP-008 (testable-state-done) — end-to-end dogfood of the testable-state gate.

Proves the WHOLE mechanism against a REAL standing app (a stdlib HTTP server),
using the REAL httpx transport — no injection. Reproduces the agent-journey
failure (shipped, but you can't log in → /dashboard 401) and asserts the gate
**blocks "done"**; then a fixed server (200) → the gate passes.

This is the marketplace-side proof. The live dogfood against the actual
agent-journey app (platform repo) is the same Scenario pointed at that app's
standup + URL — the only remaining dependency is that app standing, not code.

Stdlib http.server + httpx + pytest. Python 3.11-safe.
"""

from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from _acceptance_gate import gate_decision
from _scenario_runner import run_scenario

# A login journey: POST /signup → 200, GET /dashboard → 200.
_TOOLS = {"dna:tool:http": {"@id": "dna:tool:http", "implementation_kind": "http_call"}}
_STEPS = {
    "s1": {"@id": "s1", "name": "sign up", "mechanism": "deterministic",
           "tool_ref": "dna:tool:http",
           "mechanism_detail": json.dumps({"method": "POST", "path": "/signup", "expect_status": 200})},
    "s2": {"@id": "s2", "name": "load dashboard (logged in)", "mechanism": "deterministic",
           "tool_ref": "dna:tool:http",
           "mechanism_detail": json.dumps({"method": "GET", "path": "/dashboard", "expect_status": 200})},
}
_WF = {"@id": "wf", "steps": ["s1", "s2"]}
_SCENARIO = {"@id": "dna:scenario:login", "name": "A new user can sign up and log in",
             "journey": "wf"}


def _make_handler(dashboard_status: int):
    class H(BaseHTTPRequestHandler):
        def _respond(self, code):
            self.send_response(code); self.end_headers()
        def do_POST(self):
            self._respond(200 if self.path == "/signup" else 404)
        def do_GET(self):
            self._respond(dashboard_status if self.path == "/dashboard" else 404)
        def log_message(self, *a):  # silence
            pass
    return H


def _serve(dashboard_status: int):
    srv = HTTPServer(("127.0.0.1", 0), _make_handler(dashboard_status))
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def test_blocked_on_login_is_caught_by_the_gate():
    """The agent-journey failure: app is up but you can't log in (/dashboard
    401). The gate must BLOCK done — the exact slip this change exists to fix."""
    srv, base = _serve(dashboard_status=401)
    try:
        result = run_scenario(_SCENARIO, _WF, _STEPS, _TOOLS, target_base_url=base)
    finally:
        srv.shutdown()
    assert result.verdict == "fail", result.steps
    decision = gate_decision([result])
    assert decision.verdict == "blocked"
    assert "log in" in decision.blocking[0]["scenario"]


def test_working_login_passes_the_gate():
    """A fixed app (/dashboard 200) → the Scenario passes → gate passes."""
    srv, base = _serve(dashboard_status=200)
    try:
        result = run_scenario(_SCENARIO, _WF, _STEPS, _TOOLS, target_base_url=base)
    finally:
        srv.shutdown()
    assert result.verdict == "pass", result.steps
    assert gate_decision([result]).verdict == "pass"
