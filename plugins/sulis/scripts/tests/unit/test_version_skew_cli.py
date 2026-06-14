"""CLI-wiring tests for sulis-version-skew (#125).

The pure compare is pinned in test_version_skew.py; here we pin the CLI glue:
cache enumeration, the SessionStart hook payload shape, silence when current,
strict non-fatality of --hook mode, and the human-mode exit codes.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from importlib.machinery import SourceFileLoader
from pathlib import Path

_SCRIPTS = Path(__file__).resolve().parents[2]


def _load():
    loader = SourceFileLoader("sulis_version_skew_mod", str(_SCRIPTS / "sulis-version-skew"))
    spec = importlib.util.spec_from_loader("sulis_version_skew_mod", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_mod = _load()


def _make_cache(tmp_path: Path, version_dirs: list[str]) -> Path:
    """Build a fake plugin cache with the given sulis version dirs."""
    sulis = tmp_path / "sulis-ai-agents" / "sulis"
    sulis.mkdir(parents=True)
    for v in version_dirs:
        (sulis / v).mkdir()
    return tmp_path


# ─── cached_versions ───────────────────────────────────────────────────────


def test_cached_versions_lists_dirs(tmp_path):
    root = _make_cache(tmp_path, ["0.141.0", "0.144.0"])
    assert set(_mod.cached_versions(root)) == {"0.141.0", "0.144.0"}


def test_cached_versions_empty_when_no_cache(tmp_path):
    assert _mod.cached_versions(tmp_path / "nope") == []


# ─── hook_output: nudge iff behind, silent otherwise ───────────────────────


def test_hook_output_emits_nudge_when_behind():
    skew = {"loaded": "0.141.0", "newest": "0.144.0", "behind": True, "determinable": True}
    out = _mod.hook_output(skew)
    payload = json.loads(out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert "0.141.0" in ctx and "0.144.0" in ctx
    assert "reload" in ctx.lower()


def test_hook_output_silent_when_current():
    skew = {"loaded": "0.144.0", "newest": "0.144.0", "behind": False, "determinable": True}
    assert _mod.hook_output(skew) == ""


def test_hook_output_silent_when_undeterminable():
    skew = {"loaded": None, "newest": "0.144.0", "behind": False, "determinable": False}
    assert _mod.hook_output(skew) == ""


# ─── compute: loaded-version override + real cache ─────────────────────────


def test_compute_behind_with_a_loaded_override(tmp_path, monkeypatch):
    root = _make_cache(tmp_path, ["0.141.0", "0.144.0"])
    monkeypatch.setattr(_mod, "plugin_version", lambda *a, **k: "0.141.0")
    skew = _mod.compute(root)
    assert skew["behind"] is True and skew["newest"] == "0.144.0"


def test_compute_undeterminable_when_loaded_unknown(tmp_path, monkeypatch):
    root = _make_cache(tmp_path, ["0.144.0"])
    monkeypatch.setattr(_mod, "plugin_version", lambda *a, **k: None)
    skew = _mod.compute(root)
    assert skew["determinable"] is False and skew["behind"] is False


# ─── main: --hook always exits 0; human mode exit codes ────────────────────


def test_hook_mode_always_exits_zero_and_prints_nudge(tmp_path, monkeypatch, capsys):
    root = _make_cache(tmp_path, ["0.141.0", "0.144.0"])
    monkeypatch.setattr(_mod, "plugin_version", lambda *a, **k: "0.141.0")
    rc = _mod.main(["--hook", "--cache-root", str(root)])
    assert rc == 0
    assert "SessionStart" in capsys.readouterr().out


def test_hook_mode_silent_and_zero_when_current(tmp_path, monkeypatch, capsys):
    root = _make_cache(tmp_path, ["0.144.0"])
    monkeypatch.setattr(_mod, "plugin_version", lambda *a, **k: "0.144.0")
    rc = _mod.main(["--hook", "--cache-root", str(root)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == ""


def test_human_mode_exit_codes(tmp_path, monkeypatch):
    root = _make_cache(tmp_path, ["0.141.0", "0.144.0"])
    monkeypatch.setattr(_mod, "plugin_version", lambda *a, **k: "0.141.0")
    assert _mod.main(["--cache-root", str(root)]) == 1   # behind
    monkeypatch.setattr(_mod, "plugin_version", lambda *a, **k: "0.144.0")
    assert _mod.main(["--cache-root", str(root)]) == 0   # current
    monkeypatch.setattr(_mod, "plugin_version", lambda *a, **k: None)
    assert _mod.main(["--cache-root", str(root)]) == 2   # undeterminable


def test_hook_mode_is_non_fatal_on_internal_error(tmp_path, monkeypatch, capsys):
    # A blowup anywhere in compute must degrade to exit 0 + no output, never
    # break a session start.
    def _boom(*a, **k):
        raise RuntimeError("disk on fire")
    monkeypatch.setattr(_mod, "compute", _boom)
    rc = _mod.main(["--hook", "--cache-root", str(tmp_path)])
    assert rc == 0
    assert capsys.readouterr().out.strip() == ""


# ─── end-to-end: invoke the real executable as the hook would ──────────────


def test_executable_runs_as_a_subprocess(tmp_path):
    root = _make_cache(tmp_path, ["0.0.1"])  # ancient cache → dev tree is "ahead" → silent
    proc = subprocess.run(
        [sys.executable, str(_SCRIPTS / "sulis-version-skew"), "--hook",
         "--cache-root", str(root)],
        capture_output=True, text=True)
    assert proc.returncode == 0  # never breaks a session start
