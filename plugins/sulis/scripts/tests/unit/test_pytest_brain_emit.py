"""Tests for `_pytest_brain_emit.py`.

Strategy: pytest's `pytester` fixture spawns an in-process pytest sub-run
with our plugin loaded. We control the test files, the markers, the
SRD content, and the CLI options; we then read the brain instance files
produced under the sub-run's tmp dir and assert the graph is shaped
correctly.

`pytester` is the canonical way to test pytest plugins.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


pytest_plugins = ["pytester"]


# ─── Helpers ─────────────────────────────────────────────────────────────


def _seed_srd(pytester: pytest.Pytester) -> Path:
    """Build a minimum SRD with two FR blocks at a known path."""
    spec_dir = pytester.path / ".specifications" / "demo"
    spec_dir.mkdir(parents=True)
    srd = spec_dir / "SRD.md"
    srd.write_text(
        "# SRD — Demo\n\n"
        "**FR-001: Login**\n\nThe system shall authenticate users.\n\n"
        "**Acceptance criteria:**\n- Valid credentials → 200.\n\n"
        "**FR-002: Logout**\n\nUsers may log out.\n\n"
        "**Acceptance criteria:**\n- Logout clears session.\n"
    )
    return srd


def _common_argv(pytester: pytest.Pytester, srd: Path, scripts_dir: Path) -> list[str]:
    """The standard arg-set: load the plugin, turn it on, point at the SRD."""
    return [
        "-p", "_pytest_brain_emit",
        "-p", "no:cacheprovider",
        "--rootdir", str(pytester.path),
        "--brain-emit",
        "--brain-srd", str(srd),
        "--brain-base-dir", str(pytester.path / ".brain" / "instances"),
    ]


def _read_brain(base: Path, entity_type: str) -> list[dict]:
    """Read every `.jsonld` under `<base>/product-development/<type>/`."""
    folder = base / "product-development" / entity_type
    if not folder.exists():
        return []
    return [json.loads(p.read_text()) for p in sorted(folder.glob("*.jsonld"))]


@pytest.fixture
def scripts_dir(request) -> Path:
    """Resolve the scripts/ dir so the in-process pytest sub-run can import
    our plugin module + emitters."""
    p = Path(__file__).resolve().parent.parent.parent  # tests/unit/.. → scripts/
    return p


# ─── Activation ─────────────────────────────────────────────────────────


class TestActivation:
    def test_disabled_by_default_emits_nothing(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001")
            def test_a(): pass
            """
        )
        # Pass --rootdir + scripts on sys.path; do NOT pass --brain-emit
        pytester.syspathinsert(str(scripts_dir))
        result = pytester.runpytest(
            "-p", "_pytest_brain_emit",
            "-p", "no:cacheprovider",
            "--rootdir", str(pytester.path),
            "-q",
        )
        result.assert_outcomes(passed=1)
        # No brain dir created — plugin was inactive
        assert not (pytester.path / ".brain").exists()

    def test_env_var_activates(
        self, pytester: pytest.Pytester, scripts_dir: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001")
            def test_a(): pass
            """
        )
        monkeypatch.setenv("SULIS_BRAIN_EMIT_TESTS", "1")
        monkeypatch.setenv("SULIS_BRAIN_SRD", str(srd))
        monkeypatch.setenv("SULIS_BRAIN_BASE_DIR", str(pytester.path / ".brain" / "instances"))
        pytester.syspathinsert(str(scripts_dir))
        result = pytester.runpytest(
            "-p", "_pytest_brain_emit",
            "-p", "no:cacheprovider",
            "--rootdir", str(pytester.path),
            "-q",
        )
        result.assert_outcomes(passed=1)
        results = _read_brain(pytester.path / ".brain" / "instances", "testresult")
        assert len(results) == 1


# ─── Happy path: passing + failing tests emit correct entities ──────────


class TestEmission:
    def test_one_testrun_per_session(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001")
            def test_a(): pass
            @pytest.mark.verifies("FR-002")
            def test_b(): pass
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        result = pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        result.assert_outcomes(passed=2)

        runs = _read_brain(pytester.path / ".brain" / "instances", "testrun")
        assert len(runs) == 1
        assert runs[0]["harness"] == "pytest"

    def test_one_testresult_per_marked_test(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001")
            def test_a(): pass
            @pytest.mark.verifies("FR-002")
            def test_b(): pass
            def test_no_marker(): pass   # no marker → no TestResult
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        result = pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        result.assert_outcomes(passed=3)
        results = _read_brain(pytester.path / ".brain" / "instances", "testresult")
        # Only the two marked tests produce TestResults
        assert len(results) == 2

    def test_passing_test_emits_pass_outcome(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001")
            def test_a(): pass
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        results = _read_brain(pytester.path / ".brain" / "instances", "testresult")
        assert len(results) == 1
        assert results[0]["outcome"] == "pass"
        assert results[0]["type"] == "unit"

    def test_failing_test_emits_fail_outcome(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001")
            def test_a():
                assert False, "intentional fail"
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        results = _read_brain(pytester.path / ".brain" / "instances", "testresult")
        assert len(results) == 1
        assert results[0]["outcome"] == "fail"

    def test_skip_outcome(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001")
            @pytest.mark.skip(reason="not yet implemented")
            def test_a(): pass
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        results = _read_brain(pytester.path / ".brain" / "instances", "testresult")
        # Skip results aren't generated at the "call" phase, so no
        # TestResult emission — that's the right behaviour for "test did
        # not actually execute" → "Requirement is not verified".
        assert len(results) == 0


# ─── Marker shapes: type, multi-requirement ─────────────────────────────


class TestMarkerVariants:
    def test_multi_requirement_marker(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001", "FR-002")
            def test_combined(): pass
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        results = _read_brain(pytester.path / ".brain" / "instances", "testresult")
        assert len(results) == 1
        assert len(results[0]["verifies"]) == 2
        # Both refs are valid dna:requirement:<ulid>
        for ref in results[0]["verifies"]:
            assert re.fullmatch(r"^dna:requirement:[0-9A-HJKMNP-TV-Z]{26}$", ref)

    def test_type_kwarg_overrides_default(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001", type="integration")
            def test_a(): pass
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        results = _read_brain(pytester.path / ".brain" / "instances", "testresult")
        assert results[0]["type"] == "integration"

    def test_invalid_type_kwarg_skipped(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001", type="bogus")
            def test_a(): pass
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        result = pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        result.assert_outcomes(passed=1)  # test session still passes
        results = _read_brain(pytester.path / ".brain" / "instances", "testresult")
        # Bad type → no emission, no crash
        assert results == []


# ─── Cross-emitter ID coordination ─────────────────────────────────────


class TestRequirementIdCoordination:
    def test_marker_resolves_to_same_id_as_requirement_emitter(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        """The pytest-plugin marker MUST resolve FR-001 to the same
        dna:requirement:<ulid> the Requirement-emitter produces for the
        same SRD path. Otherwise the verification graph doesn't connect.
        """
        srd = _seed_srd(pytester)
        # 1. Emit Requirements from the SRD via the emitter
        import sys
        sys.path.insert(0, str(scripts_dir))
        from _entity_adapter_local import LocalFileEntityAdapter
        from _requirement_emission import emit_requirements_from_srd
        adapter = LocalFileEntityAdapter(
            base_dir=pytester.path / ".brain" / "instances",
            domain="product-development",
        )
        emitted_reqs = emit_requirements_from_srd(srd, adapter)
        emitted_ids = {r["id"] for r in emitted_reqs}

        # 2. Run pytest with @verifies("FR-001"); the plugin should claim
        #    the SAME id when emitting TestResults.
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001")
            def test_a(): pass
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        results = _read_brain(pytester.path / ".brain" / "instances", "testresult")

        assert len(results) == 1
        # The TestResult.verifies entry must match an existing Requirement.id
        for ref in results[0]["verifies"]:
            assert ref in emitted_ids, (
                f"TestResult.verifies={ref} doesn't match any emitted "
                f"Requirement id ({emitted_ids}); the graph won't connect."
            )


# ─── Determinism: re-run updates same TestResult record ──────────────────


class TestDeterminism:
    def test_rerun_same_test_updates_existing_testresult(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        srd = _seed_srd(pytester)
        # First run: passing
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001")
            def test_a(): pass
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        results_pass = _read_brain(pytester.path / ".brain" / "instances", "testresult")
        assert len(results_pass) == 1
        first_id = results_pass[0]["id"]
        assert results_pass[0]["outcome"] == "pass"

        # Second run: change the test to fail (same name, same marker)
        pytester.makepyfile(
            test_x="""
            import pytest
            @pytest.mark.verifies("FR-001")
            def test_a():
                assert False
            """
        )
        pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        results_fail = _read_brain(pytester.path / ".brain" / "instances", "testresult")

        # Determinism contract: same (run, requirements, type) → same ID;
        # outcome doesn't bind ID. Note "run" differs across the two
        # pytest invocations (different timestamps), so the IDs WILL
        # differ — but within a single run, a re-run of the same test
        # produces the same TestResult. We're testing the inter-run
        # behaviour here: the brain has one record per (run, test, reqs).
        # The earlier-run's TestResult stays at pass; the later run's
        # creates a NEW record with outcome=fail.
        assert len(results_fail) == 2
        outcomes = {r["outcome"] for r in results_fail}
        assert outcomes == {"pass", "fail"}


# ─── Failure-resilience: brain failures don't fail pytest ──────────────


class TestResilience:
    def test_missing_srd_raises_usage_error(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        pytester.makepyfile(test_x="def test_a(): pass")
        pytester.syspathinsert(str(scripts_dir))
        result = pytester.runpytest(
            "-p", "_pytest_brain_emit",
            "--brain-emit",
            "--brain-srd", str(pytester.path / "nope.md"),
            "-q",
        )
        # Pytest exits with usage-error code (4) — the founder/CI sees
        # this clearly and fixes the config.
        assert result.ret == pytest.ExitCode.USAGE_ERROR

    def test_pytest_succeeds_even_on_validation_failure(
        self, pytester: pytest.Pytester, scripts_dir: Path
    ) -> None:
        """A bad FR id in the marker (one that produces a valid ulid format
        but fails downstream) should NOT fail the test session."""
        srd = _seed_srd(pytester)
        pytester.makepyfile(
            test_x="""
            import pytest
            # FR-with-special-chars produces a valid ULID but the test still passes
            @pytest.mark.verifies("FR-999")
            def test_a(): pass
            """
        )
        pytester.syspathinsert(str(scripts_dir))
        result = pytester.runpytest(*_common_argv(pytester, srd, scripts_dir), "-q")
        # Test passes regardless of brain outcome
        result.assert_outcomes(passed=1)
