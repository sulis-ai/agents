"""Unit tests for _wpxlib._preflight_ci_conclusion (HD-001 / WP-001).

These tests exercise the non-polling pre-flight CI-conclusion helper that
reads a branch HEAD's CURRENT recorded CI conclusion and returns
``(verdict, failed_check_names)`` — without waiting for in-flight runs.

Style matches test_ghclient_protocol.py / test_wpxlib_tables.py: in-process
import of ``_wpxlib`` with a minimal in-test ``GHClient`` stub injected via
the existing ``gh=`` keyword seam (no monkeypatching of internals).

The stub's ``check_runs`` returns the ``{"check_runs": [...]}`` envelope
shape of ``RealGHClient.check_runs`` (_wpxlib.py:996), which is exactly the
shape ``_poll_ci`` already consumes (_wpxlib.py:1201).
"""

from __future__ import annotations

import pytest

import _wpxlib


# ─── In-test GHClient stub ───────────────────────────────────────────


def _run(name: str, status: str, conclusion):
    """Build one check-run dict in the RealGHClient.check_runs envelope shape."""
    return {"name": name, "status": status, "conclusion": conclusion}


class _CheckRunsStub:
    """Minimal GHClient double whose ``check_runs`` returns a fixed envelope.

    Only ``check_runs`` is implemented — the pre-flight helper touches no
    other GHClient method, so a partial stub is sufficient and keeps the
    test focused on the behaviour under test.
    """

    def __init__(self, runs: list[dict]) -> None:
        self._runs = runs

    def check_runs(self, repo: str, branch: str) -> dict:
        return {"check_runs": self._runs}


# ─── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def fake_gh_red():
    """One completed run failed (name='web'), the rest completed/success."""
    return _CheckRunsStub([
        _run("lint", "completed", "success"),
        _run("web", "completed", "failure"),
        _run("unit", "completed", "success"),
    ])


@pytest.fixture
def fake_gh_green():
    """All completed runs in the pass set (success / neutral / skipped)."""
    return _CheckRunsStub([
        _run("lint", "completed", "success"),
        _run("unit", "completed", "neutral"),
        _run("optional", "completed", "skipped"),
    ])


@pytest.fixture
def fake_gh_in_flight():
    """At least one run not yet completed (status != 'completed')."""
    return _CheckRunsStub([
        _run("lint", "completed", "success"),
        _run("web", "in_progress", None),
    ])


@pytest.fixture
def fake_gh_no_runs():
    """No check-runs recorded for this HEAD yet."""
    return _CheckRunsStub([])


# ─── Tests (Red — helper does not exist yet) ─────────────────────────


def test_preflight_red_dev_returns_failed_with_names(fake_gh_red):
    verdict, failed = _wpxlib._preflight_ci_conclusion(
        "sulis-ai/agents", "dev", gh=fake_gh_red)
    assert verdict == "failed"
    assert failed == ["web"]  # count == len(failed) == 1


def test_preflight_green_dev_returns_green_empty(fake_gh_green):
    verdict, failed = _wpxlib._preflight_ci_conclusion(
        "sulis-ai/agents", "dev", gh=fake_gh_green)
    assert verdict == "green"
    assert failed == []


def test_preflight_does_not_poll_when_runs_in_flight(fake_gh_in_flight, monkeypatch):
    # A non-completed run must NOT trigger a wait: assert time.sleep is never
    # called, and the verdict is returned immediately as "pending".
    slept: list = []
    monkeypatch.setattr(_wpxlib.time, "sleep", lambda s: slept.append(s))
    verdict, failed = _wpxlib._preflight_ci_conclusion(
        "sulis-ai/agents", "dev", gh=fake_gh_in_flight)
    assert slept == []  # never polled
    assert verdict == "pending"
    assert failed == []


def test_preflight_reads_conclusion_explicitly_not_status(fake_gh_red):
    # Regression guard for lesson #59: a run with status="completed" and
    # conclusion="failure" is failed even though status alone looks "done".
    verdict, _failed = _wpxlib._preflight_ci_conclusion(
        "sulis-ai/agents", "dev", gh=fake_gh_red)
    assert verdict == "failed"


def test_preflight_no_runs_recorded_returns_unknown(fake_gh_no_runs):
    verdict, failed = _wpxlib._preflight_ci_conclusion(
        "sulis-ai/agents", "dev", gh=fake_gh_no_runs)
    assert verdict == "unknown"
    assert failed == []
