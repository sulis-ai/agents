"""WP-004/008 — `sulis-verify-acceptance` CLI integration.

Invokes the real executable via subprocess against a live stdlib fixture
server, through the repo-contract target resolution — the founder's actual
`sulis-verify-acceptance --bundle ... --target local` path. Proves exit codes
(0 pass / 1 blocked / 2 invocation) + the JSON envelope end-to-end.

Stdlib (http.server + subprocess) + pytest. Python 3.11-safe.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[2] / "sulis-verify-acceptance"

_BUNDLE = {
    "scenario": {"@id": "dna:scenario:login", "name": "log in", "journey": "wf"},
    "workflow": {"@id": "wf", "steps": ["s1", "s2"]},
    "tools": [{"@id": "dna:tool:http", "implementation_kind": "http_call"}],
    "steps": [
        {"@id": "s1", "name": "sign up", "mechanism": "deterministic",
         "tool_ref": "dna:tool:http",
         "mechanism_detail": json.dumps({"method": "POST", "path": "/signup", "expect_status": 200})},
        {"@id": "s2", "name": "dashboard", "mechanism": "deterministic",
         "tool_ref": "dna:tool:http",
         "mechanism_detail": json.dumps({"method": "GET", "path": "/dashboard", "expect_status": 200})},
    ],
}


def _serve(dashboard_status: int):
    class H(BaseHTTPRequestHandler):
        def _r(self, c): self.send_response(c); self.end_headers()
        def do_POST(self): self._r(200 if self.path == "/signup" else 404)
        def do_GET(self): self._r(dashboard_status if self.path == "/dashboard" else 404)
        def log_message(self, *a): pass
    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def _setup(tmp_path, dashboard_status):
    srv, base = _serve(dashboard_status)
    (tmp_path / ".sulis").mkdir()
    (tmp_path / ".sulis" / "repo-contract.yml").write_text(
        f"targets:\n  local: {base}\n", encoding="utf-8")
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(_BUNDLE), encoding="utf-8")
    return srv, bundle


def _run_cli(tmp_path, bundle):
    return subprocess.run(
        [sys.executable, str(_SCRIPT), "--bundle", str(bundle),
         "--target", "local", "--repo-root", str(tmp_path), "--json"],
        capture_output=True, text=True,
    )


def test_cli_passes_on_working_app(tmp_path):
    srv, bundle = _setup(tmp_path, 200)
    try:
        r = _run_cli(tmp_path, bundle)
    finally:
        srv.shutdown()
    assert r.returncode == 0, r.stderr
    env = json.loads(r.stdout)
    assert env["verdict"] == "pass" and env["gate"] == "pass"


def test_cli_blocks_on_broken_login(tmp_path):
    srv, bundle = _setup(tmp_path, 401)
    try:
        r = _run_cli(tmp_path, bundle)
    finally:
        srv.shutdown()
    assert r.returncode == 1
    env = json.loads(r.stdout)
    assert env["verdict"] == "fail" and env["gate"] == "blocked"


def test_cli_errors_on_missing_target(tmp_path):
    bundle = tmp_path / "bundle.json"
    bundle.write_text(json.dumps(_BUNDLE), encoding="utf-8")
    (tmp_path / ".sulis").mkdir()
    (tmp_path / ".sulis" / "repo-contract.yml").write_text("profile: x\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(_SCRIPT), "--bundle", str(bundle),
         "--target", "local", "--repo-root", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 2
    assert "target" in r.stderr.lower()


# #171 — subprocess-only scenarios on a no-app repo
_SUBPROCESS_BUNDLE = {
    "scenario": {"@id": "dna:scenario:cli", "name": "cli check", "journey": "wf"},
    "workflow": {"@id": "wf", "steps": ["s1", "s2"]},
    "tools": [{"@id": "dna:tool:sub", "implementation_kind": "subprocess"}],
    "steps": [
        {"@id": "s1", "name": "true cmd", "mechanism": "deterministic",
         "tool_ref": "dna:tool:sub",
         "mechanism_detail": json.dumps({"cmd": "true", "expect_exit": 0})},
        {"@id": "s2", "name": "echo ok", "mechanism": "deterministic",
         "tool_ref": "dna:tool:sub",
         "mechanism_detail": json.dumps({"cmd": "echo ok", "expect_exit": 0})},
    ],
}


def test_cli_passes_on_subprocess_only_scenario_without_local_target(tmp_path):
    """#171 — a scenario whose every step is a subprocess-mechanism step
    needs no HTTP target URL. The gate must run on a no-app repo (no
    `targets.local`) instead of refusing with the misleading 'No local
    target URL' error."""
    bundle = tmp_path / "subprocess-bundle.json"
    bundle.write_text(json.dumps(_SUBPROCESS_BUNDLE), encoding="utf-8")
    # No `targets.local` — only `profile: x` (a no-app repo: published-artifact,
    # plugin, library, etc.).
    (tmp_path / ".sulis").mkdir()
    (tmp_path / ".sulis" / "repo-contract.yml").write_text(
        "profile: published-artifact\n", encoding="utf-8")

    r = subprocess.run(
        [sys.executable, str(_SCRIPT), "--bundle", str(bundle),
         "--target", "local", "--repo-root", str(tmp_path), "--json"],
        capture_output=True, text=True,
    )
    assert r.returncode == 0, (
        f"subprocess-only scenario must pass without targets.local; "
        f"returncode={r.returncode}, stderr={r.stderr!r}"
    )
    env = json.loads(r.stdout)
    assert env["verdict"] == "pass" and env["gate"] == "pass", env


def test_cli_still_errors_on_missing_target_when_http_step_present(tmp_path):
    """Regression — keep the existing 'missing target URL' guard for the
    case the lesson left untouched: at least one step needs an HTTP URL."""
    bundle = tmp_path / "mixed-bundle.json"
    # Borrow the existing _BUNDLE (two http_call steps) to prove the guard
    # still fires when an http step is present.
    bundle.write_text(json.dumps(_BUNDLE), encoding="utf-8")
    (tmp_path / ".sulis").mkdir()
    (tmp_path / ".sulis" / "repo-contract.yml").write_text(
        "profile: published-artifact\n", encoding="utf-8")
    r = subprocess.run(
        [sys.executable, str(_SCRIPT), "--bundle", str(bundle),
         "--target", "local", "--repo-root", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert r.returncode == 2
    assert "target" in r.stderr.lower()
