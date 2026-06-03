"""DoD gate logic — given an SRD + a brain, compute the verification verdict.

Companion to `_verify_environment.py`:

  - `_verify_environment` stands up a fresh workspace, drives the
    pipeline, and queries the resulting brain. It's the harness — the
    automation pass that proves the pipeline works end to end.
  - `_verify_requirements` (this module) takes an EXISTING brain and an
    SRD, computes the same verdict, and that's it. It's the gate — the
    thing `change ship` can call to refuse a merge.

Semantics (identical to the harness; pinned by the same load-bearing
test):

    A Requirement is VERIFIED iff there exists at least one TestResult
    in the brain graph with:
      - outcome == "pass"
      - its `verifies` array contains the Requirement.id

This rule is route-agnostic: a passing TestResult is a passing TestResult
whether it came from a `@verifies`-tagged unit test or from a green Scenario
run. The Scenario loop (`sulis-verify-acceptance --scenario`) deposits its own
TestResult per run (see `_scenario_evidence.py`), so a requirement proven only
by a green Scenario journey reads as covered here — closing the false-red where
the gate saw the @verifies route but not the Scenario route.

The gate enumerates FR-NN / NFR-NN ids from the SRD body, resolves each
to `dna:requirement:<ulid>` using the SAME deterministic seed
Requirement-emission uses (`requirement:{srd_path}:{fr_id}`), then for
each: queries the brain. A FR-NN whose resolved Requirement is missing
from the brain entirely is still UNVERIFIED — emission didn't happen
upstream, the gate doesn't get to claim coverage anyway.

Verdict:
  - PASS   — every FR/NFR has at least one passing TestResult verifying it
  - PARTIAL — some FR/NFR have passing verifiers, some don't
  - FAIL   — no FR/NFR has a passing verifier (or no FR/NFR found in the SRD)

The CLI uses these to set exit code:
  0 — PASS
  1 — PARTIAL (some coverage, not full)
  2 — FAIL (no coverage)
  3 — pipeline/gate error (couldn't read SRD, brain dir missing, etc.)

PARTIAL is intentionally non-zero so a CI gate that demands full
coverage can use `exit_code == 0` as the binary signal.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from _brain_query import find_passing_testresults_verifying
from _requirement_emission import _deterministic_ulid_from


# The same regex Requirement-emission uses to find FR/NFR headers in the
# SRD body. Kept local-and-narrow to avoid coupling to the emitter's
# whole module structure — we just need to enumerate ids.
#
# #170 — the closing `**` is the heading terminator; the line MAY carry
# inline body text after it (the canonical `**FR-NN: Title.** body`
# format). The previous trailing `\s*$` anchored to end-of-line and
# silently dropped every inline-body heading.
_FR_HEADER_RE: re.Pattern[str] = re.compile(
    r"^\*\*((?:FR|NFR)-\d+(?:\.\d+)?):\s*(.+?)\*\*",
    re.MULTILINE,
)


@dataclass
class FrCoverage:
    """One Requirement's verification status."""

    fr_id: str            # human-readable (e.g. "FR-001")
    requirement_id: str   # full dna:requirement:<ulid>
    title: str            # text after the colon in the marker
    verified: bool        # at least one passing TestResult exists
    passing_testresults: int = 0


@dataclass
class VerifyRequirementsResult:
    """Full DoD verdict for one SRD against one brain."""

    verdict: str  # "pass" | "partial" | "fail"
    srd_path: str
    brain_base_dir: str
    coverage: list[FrCoverage] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def verified_count(self) -> int:
        return sum(1 for c in self.coverage if c.verified)

    @property
    def unverified_count(self) -> int:
        return sum(1 for c in self.coverage if not c.verified)

    @property
    def total(self) -> int:
        return len(self.coverage)

    def as_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "srd_path": self.srd_path,
            "brain_base_dir": self.brain_base_dir,
            "total_requirements": self.total,
            "verified_count": self.verified_count,
            "unverified_count": self.unverified_count,
            "verified": [
                {"fr_id": c.fr_id, "requirement_id": c.requirement_id,
                 "title": c.title, "passing_testresults": c.passing_testresults}
                for c in self.coverage if c.verified
            ],
            "unverified": [
                {"fr_id": c.fr_id, "requirement_id": c.requirement_id,
                 "title": c.title}
                for c in self.coverage if not c.verified
            ],
            "errors": list(self.errors),
        }


# ─── Public API ─────────────────────────────────────────────────────────


def enumerate_fr_ids(srd_text: str) -> list[tuple[str, str]]:
    """Walk the SRD body; return [(fr_id, title), ...] in document order.

    `fr_id` is the human form (FR-001, NFR-003.2); `title` is the text
    immediately after the colon in the header. Duplicates are kept (an
    SRD with two `**FR-001:**` blocks is a bug, but enumerating both
    lets the caller surface it).
    """
    return [
        (m.group(1).strip(), m.group(2).strip())
        for m in _FR_HEADER_RE.finditer(srd_text)
    ]


def verify_requirements(
    srd_path: Path,
    *,
    base_dir: Path,
    domain: str = "product-development",
) -> VerifyRequirementsResult:
    """Compute the DoD verdict for `srd_path` against the brain at `base_dir`.

    Reads the SRD, enumerates FR/NFR ids, resolves each to a
    dna:requirement:<ulid> using the deterministic seed
    `requirement:{srd_path}:{fr_id}` (same as Requirement-emission), then
    queries the brain for passing TestResults verifying each.

    A missing brain dir surfaces as a single error in `errors` and a
    FAIL verdict with empty coverage. A missing SRD raises FileNotFoundError
    (callers — the CLI — handle this).
    """
    srd_path = Path(srd_path).resolve()
    base_dir = Path(base_dir).resolve()

    result = VerifyRequirementsResult(
        verdict="fail",
        srd_path=str(srd_path),
        brain_base_dir=str(base_dir),
    )

    if not srd_path.exists():
        raise FileNotFoundError(f"SRD not found: {srd_path}")

    srd_text = srd_path.read_text(encoding="utf-8")
    fr_pairs = enumerate_fr_ids(srd_text)

    if not fr_pairs:
        result.errors.append(
            f"no FR/NFR blocks found in SRD ({srd_path}); nothing to verify"
        )
        return result

    if not base_dir.exists():
        # Brain hasn't been populated at all — every requirement is unverified
        # by definition. Surface this explicitly rather than silently failing.
        result.errors.append(
            f"brain base dir not found ({base_dir}); no entities emitted yet"
        )
        # Still enumerate FRs into coverage so the founder can see which ones
        # exist on paper but aren't verified.

    for fr_id, title in fr_pairs:
        req_ulid = _deterministic_ulid_from(f"requirement:{srd_path}:{fr_id}")
        req_id = f"dna:requirement:{req_ulid}"
        if base_dir.exists():
            passing = find_passing_testresults_verifying(base_dir, req_id, domain=domain)
        else:
            passing = []
        result.coverage.append(FrCoverage(
            fr_id=fr_id, requirement_id=req_id, title=title,
            verified=bool(passing), passing_testresults=len(passing),
        ))

    # Verdict
    v = result.verified_count
    u = result.unverified_count
    if u == 0 and v > 0:
        result.verdict = "pass"
    elif v == 0:
        result.verdict = "fail"
    else:
        result.verdict = "partial"

    return result
