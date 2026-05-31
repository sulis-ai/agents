"""Tests for `_verify_environment.py`.

The library runs subprocess pytest + emitter calls, so these tests
intentionally exercise the whole pipeline against a real workspace —
they ARE production-like e2e tests.

The CLI's own self-test path is covered separately by the integration
test below; here we test the library's stage-level behaviour.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _verify_environment import (
    EnvironmentCheckResult,
    run_environment_check,
)


_SRD_TEXT = """\
# SRD — Test

**FR-001: Login**

The system authenticates users.

**Acceptance criteria:**
- Valid credentials → 200.

**FR-002: Logout**

Users may log out.

**Acceptance criteria:**
- Session cleared.

**FR-003: Profile**

Users may view their profile.

**Acceptance criteria:**
- Profile renders.
"""

_TESTS_TEXT_FULL_COVERAGE = '''\
import pytest

@pytest.mark.verifies("FR-001")
def test_login(): pass

@pytest.mark.verifies("FR-002")
def test_logout(): pass

@pytest.mark.verifies("FR-003")
def test_profile(): pass
'''

_TESTS_TEXT_PARTIAL_COVERAGE = '''\
import pytest

@pytest.mark.verifies("FR-001")
def test_login(): pass

# FR-002 and FR-003 intentionally unmarked
def test_logout(): pass
def test_profile(): pass
'''

_TESTS_TEXT_NO_COVERAGE = '''\
def test_a(): pass
def test_b(): pass
'''

_TESTS_TEXT_FAILING_VERIFY = '''\
import pytest

@pytest.mark.verifies("FR-001")
def test_login():
    assert False, "intentional fail"
'''


@pytest.fixture
def scripts_src() -> Path:
    """Resolve the marketplace scripts dir from this test's location."""
    return Path(__file__).resolve().parent.parent.parent


# ─── Happy path ─────────────────────────────────────────────────────────


class TestFullCoverage:
    def test_status_pass_when_every_requirement_verified(
        self, tmp_path: Path, scripts_src: Path
    ) -> None:
        result = run_environment_check(
            tmp_path, scripts_src=scripts_src,
            srd_text=_SRD_TEXT, tests_text=_TESTS_TEXT_FULL_COVERAGE,
        )
        assert result.status == "pass", result.as_dict()
        assert result.requirements_emitted == 3
        assert len(result.requirements_verified) == 3
        assert result.requirements_unverified == []
        assert result.testresults_emitted == 3
        assert result.testrun_id is not None
        assert result.testrun_id.startswith("dna:testrun:")


class TestPartialCoverage:
    def test_status_partial_when_some_requirements_unverified(
        self, tmp_path: Path, scripts_src: Path
    ) -> None:
        result = run_environment_check(
            tmp_path, scripts_src=scripts_src,
            srd_text=_SRD_TEXT, tests_text=_TESTS_TEXT_PARTIAL_COVERAGE,
        )
        assert result.status == "partial", result.as_dict()
        assert result.requirements_emitted == 3
        assert len(result.requirements_verified) == 1
        assert len(result.requirements_unverified) == 2


class TestNoCoverage:
    def test_status_fail_when_no_requirement_verified(
        self, tmp_path: Path, scripts_src: Path
    ) -> None:
        result = run_environment_check(
            tmp_path, scripts_src=scripts_src,
            srd_text=_SRD_TEXT, tests_text=_TESTS_TEXT_NO_COVERAGE,
        )
        assert result.status == "fail", result.as_dict()
        assert result.requirements_emitted == 3
        assert result.requirements_verified == []
        assert len(result.requirements_unverified) == 3


class TestFailingVerify:
    def test_failing_test_does_not_count_as_verifying(
        self, tmp_path: Path, scripts_src: Path
    ) -> None:
        """A test that CLAIMS to verify FR-001 but FAILS is not a passing
        verifier. The Requirement remains unverified. This is the
        load-bearing semantics for the DoD gate."""
        result = run_environment_check(
            tmp_path, scripts_src=scripts_src,
            srd_text=_SRD_TEXT, tests_text=_TESTS_TEXT_FAILING_VERIFY,
        )
        # 3 Requirements emitted, 1 TestResult emitted with outcome=fail,
        # so FR-001 should be in unverified (not verified).
        assert result.requirements_emitted == 3
        assert result.testresults_emitted == 1
        assert result.status in ("partial", "fail")
        # The failing-marked Requirement is NOT in verified
        # (only passing TestResults verify):
        assert len(result.requirements_verified) == 0
        assert len(result.requirements_unverified) == 3


# ─── Graceful failure ──────────────────────────────────────────────────


class TestErrorHandling:
    def test_empty_srd_returns_fail_with_error(
        self, tmp_path: Path, scripts_src: Path
    ) -> None:
        result = run_environment_check(
            tmp_path, scripts_src=scripts_src,
            srd_text="# Empty SRD\n",  # no FR/NFR blocks
            tests_text=_TESTS_TEXT_FULL_COVERAGE,
        )
        assert result.status == "fail"
        assert result.requirements_emitted == 0
        assert any("no Requirements emitted" in e or "no Requirements in brain" in e
                   for e in result.errors), result.as_dict()


# ─── Structural ────────────────────────────────────────────────────────


class TestResultShape:
    def test_as_dict_round_trips_through_json(
        self, tmp_path: Path, scripts_src: Path
    ) -> None:
        result = run_environment_check(
            tmp_path, scripts_src=scripts_src,
            srd_text=_SRD_TEXT, tests_text=_TESTS_TEXT_FULL_COVERAGE,
        )
        data = result.as_dict()
        # All values must be JSON-serialisable for the CLI envelope.
        round_tripped = json.loads(json.dumps(data))
        assert round_tripped == data
        assert set(data.keys()) >= {
            "status", "requirements_emitted", "testrun_id",
            "testresults_emitted", "requirements_verified",
            "requirements_unverified", "pytest_outcome", "errors",
        }


class TestDataclass:
    def test_default_status_is_fail(self) -> None:
        r = EnvironmentCheckResult(status="fail")
        assert r.status == "fail"
        assert r.requirements_verified == []
        assert r.requirements_unverified == []
        assert r.errors == []
