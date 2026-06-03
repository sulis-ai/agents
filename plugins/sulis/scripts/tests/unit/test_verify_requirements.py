"""Tests for `_verify_requirements.py` — the DoD gate logic.

Strategy: build a brain by hand (one Requirement per FR, plus selected
passing/failing TestResults verifying them), then run the gate against
the SRD that produced the Requirement ids. The gate must compute the
verdict correctly for every coverage pattern: full, partial, none,
empty SRD, missing brain, failing-claim.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from _entity_adapter_local import LocalFileEntityAdapter
from _requirement_emission import emit_requirements_from_srd
from _testresult_emission import emit_testresult
from _testrun_emission import emit_testrun
from _verify_requirements import (
    FrCoverage,
    VerifyRequirementsResult,
    enumerate_fr_ids,
    verify_requirements,
)


_SRD = """\
# SRD — Test

**FR-001: Login**

Auth users.

**Acceptance criteria:**
- Valid creds → 200.

**FR-002: Logout**

End session.

**Acceptance criteria:**
- Session cleared.

**FR-003: Profile**

View profile.

**Acceptance criteria:**
- Profile renders.

**NFR-001: Latency**

Login p95 ≤ 200ms.
"""


def _seed_brain(tmp_path: Path, srd_text: str = _SRD) -> tuple[Path, Path]:
    """Write SRD + emit Requirements + open the brain.

    Returns (srd_path, base_dir).
    """
    srd_dir = tmp_path / ".specifications" / "demo"
    srd_dir.mkdir(parents=True)
    srd = srd_dir / "SRD.md"
    srd.write_text(srd_text)
    base = tmp_path / ".brain" / "instances"
    adapter = LocalFileEntityAdapter(base_dir=base, domain="product-development")
    emit_requirements_from_srd(srd, adapter)
    return srd, base


def _make_testrun_and_emit_pass(
    base: Path, requirement_id: str, *, outcome: str = "pass",
) -> None:
    """Helper: emit a TestRun + one TestResult verifying `requirement_id`."""
    adapter = LocalFileEntityAdapter(base_dir=base, domain="product-development")
    run = emit_testrun(repo=adapter, ran_at="2026-05-31T10:00:00Z", harness="pytest")
    emit_testresult(
        repo=adapter, of_run=run["id"], verifies=[requirement_id],
        type="unit", outcome=outcome,
    )


def _resolved_req_id(srd_path: Path, fr_id: str) -> str:
    """Re-derive the dna:requirement:<ulid> the gate will compute for FR-NN."""
    from _requirement_emission import _deterministic_ulid_from
    return f"dna:requirement:{_deterministic_ulid_from(f'requirement:{srd_path.resolve()}:{fr_id}')}"


# ─── enumerate_fr_ids ──────────────────────────────────────────────────


class TestEnumerateFrIds:
    def test_finds_fr_and_nfr_blocks(self) -> None:
        pairs = enumerate_fr_ids(_SRD)
        ids = [p[0] for p in pairs]
        assert ids == ["FR-001", "FR-002", "FR-003", "NFR-001"]
        titles = dict(pairs)
        assert titles["FR-001"] == "Login"
        assert titles["NFR-001"] == "Latency"

    def test_empty_srd_returns_empty(self) -> None:
        assert enumerate_fr_ids("# No FR blocks at all\n") == []

    def test_sub_numbered_fr(self) -> None:
        text = "**FR-001.2: Sub-feature**\nbody.\n"
        pairs = enumerate_fr_ids(text)
        assert pairs == [("FR-001.2", "Sub-feature")]

    def test_inline_body_canonical_format(self) -> None:
        """#170 — the canonical SRD heading is `**FR-NN: Title.** body` with
        the body on the SAME line as the closing `**`. The regex must enumerate
        all blocks, not just the ones where the heading sits alone on its line.
        """
        text = """\
# SRD

**FR-01: First requirement.** Body text inline.

**FR-02: Second requirement.** More body text inline.

**FR-03: Third requirement.** Yet more inline body.

**NFR-01: Latency.** Bounded.
"""
        pairs = enumerate_fr_ids(text)
        ids = [p[0] for p in pairs]
        assert ids == ["FR-01", "FR-02", "FR-03", "NFR-01"], (
            f"inline-body canonical format must enumerate ALL FR/NFR blocks; "
            f"got {ids}. Anchoring the regex to end-of-line ($) after the "
            f"closing `**` drops every inline-body heading silently."
        )

    def test_mixed_inline_and_standalone_headings(self) -> None:
        """A real-world SRD mixes both shapes — heading-on-its-own-line and
        heading-with-inline-body. Both must enumerate."""
        text = """\
**FR-01: Standalone**

Body underneath.

**FR-02: Inline body.** Body on the same line.

**FR-03: Also standalone**

More underneath.
"""
        ids = [p[0] for p in enumerate_fr_ids(text)]
        assert ids == ["FR-01", "FR-02", "FR-03"]


# ─── Verdict shapes ────────────────────────────────────────────────────


class TestPassVerdict:
    def test_all_requirements_verified(self, tmp_path: Path) -> None:
        srd, base = _seed_brain(tmp_path)
        # Emit a passing TestResult per FR/NFR
        for fr in ("FR-001", "FR-002", "FR-003", "NFR-001"):
            _make_testrun_and_emit_pass(base, _resolved_req_id(srd, fr))

        result = verify_requirements(srd, base_dir=base)
        assert result.verdict == "pass", result.as_dict()
        assert result.total == 4
        assert result.verified_count == 4
        assert result.unverified_count == 0


class TestPartialVerdict:
    def test_some_requirements_verified(self, tmp_path: Path) -> None:
        srd, base = _seed_brain(tmp_path)
        # Verify FR-001 + FR-002 only; FR-003 + NFR-001 left bare
        for fr in ("FR-001", "FR-002"):
            _make_testrun_and_emit_pass(base, _resolved_req_id(srd, fr))

        result = verify_requirements(srd, base_dir=base)
        assert result.verdict == "partial", result.as_dict()
        assert result.verified_count == 2
        assert result.unverified_count == 2
        unverified_fr_ids = {c.fr_id for c in result.coverage if not c.verified}
        assert unverified_fr_ids == {"FR-003", "NFR-001"}


class TestFailVerdict:
    def test_no_requirements_verified(self, tmp_path: Path) -> None:
        srd, base = _seed_brain(tmp_path)
        # No TestResults at all
        result = verify_requirements(srd, base_dir=base)
        assert result.verdict == "fail", result.as_dict()
        assert result.verified_count == 0
        assert result.unverified_count == 4

    def test_failing_testresult_does_not_count_as_verifying(
        self, tmp_path: Path
    ) -> None:
        """LOAD-BEARING — pins the DoD semantic: a test that CLAIMS to
        verify but failed does NOT verify.
        """
        srd, base = _seed_brain(tmp_path)
        # Emit a FAILING TestResult for FR-001
        _make_testrun_and_emit_pass(base, _resolved_req_id(srd, "FR-001"),
                                     outcome="fail")
        # Emit a SKIPPED TestResult for FR-002
        _make_testrun_and_emit_pass(base, _resolved_req_id(srd, "FR-002"),
                                     outcome="skip")
        # FR-003 + NFR-001 have nothing

        result = verify_requirements(srd, base_dir=base)
        assert result.verdict == "fail", result.as_dict()
        assert result.verified_count == 0
        assert result.unverified_count == 4


# ─── Failure modes ─────────────────────────────────────────────────────


class TestErrorModes:
    def test_empty_srd_returns_fail_with_error(self, tmp_path: Path) -> None:
        srd, base = _seed_brain(tmp_path, srd_text="# Empty\n")
        result = verify_requirements(srd, base_dir=base)
        assert result.verdict == "fail"
        assert result.total == 0
        assert any("no FR/NFR blocks" in e for e in result.errors)

    def test_missing_srd_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            verify_requirements(
                tmp_path / "nope.md", base_dir=tmp_path / ".brain" / "instances",
            )

    def test_missing_brain_dir_returns_fail_with_error(self, tmp_path: Path) -> None:
        srd_dir = tmp_path / ".specifications" / "demo"
        srd_dir.mkdir(parents=True)
        srd = srd_dir / "SRD.md"
        srd.write_text(_SRD)
        # No brain emission — base dir doesn't exist
        result = verify_requirements(
            srd, base_dir=tmp_path / ".brain" / "instances",
        )
        # Surfaces as fail with explicit error explaining why
        assert result.verdict == "fail"
        assert any("brain base dir not found" in e for e in result.errors)
        # FR enumeration still happens so the founder sees what's unverified
        assert result.total == 4
        assert result.unverified_count == 4


# ─── Symmetry with harness pass-fixture ────────────────────────────────


class TestSymmetryWithHarness:
    def test_full_dict_round_trip_for_serialisation(self, tmp_path: Path) -> None:
        srd, base = _seed_brain(tmp_path)
        for fr in ("FR-001", "FR-002"):
            _make_testrun_and_emit_pass(base, _resolved_req_id(srd, fr))
        result = verify_requirements(srd, base_dir=base)
        data = result.as_dict()
        # Every key must be JSON-serialisable (the CLI envelope demands it)
        assert json.loads(json.dumps(data)) == data
        # Verdict fields surface in expected shapes
        assert data["verdict"] == "partial"
        assert "verified" in data and "unverified" in data
        assert len(data["verified"]) + len(data["unverified"]) == data["total_requirements"]
