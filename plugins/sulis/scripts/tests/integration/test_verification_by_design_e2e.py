"""End-to-end methodology test + dogfood acceptance for verification-by-design.

WP-008 — the terminal piece of CH-01KT2B (verification-by-design). Two
test categories per the WP Contract (Proof pillar test class 3 + 5,
NFR-005 dogfood gate):

1. **Methodology test** — assert the *real* updated requirements-analyst
   agent prompt cites ``VERIFICATION_QUESTIONS.md`` by relative path AND
   declares the six required ``## Verification Plan`` subsections that
   future SRDs must carry. The agent prompt is the source of truth for
   what a dispatch would produce; if the prompt names the subsections
   then a faithful agent will emit them. (We do not invoke an actual LLM
   here — Sulis test policy is hermetic; non-deterministic LLM output
   would violate the no-flakiness-budget rule in WP-008 Notes.)

2. **Dogfood assertion** — run the P-VER rubric (the harness from WP-007)
   against this very change's own artifacts:

   - ``.specifications/verification-by-design/SRD.md`` (the worked
     example Verification Plan section)
   - ``.architecture/verification-by-design/TDD.md`` (the second worked
     example)
   - Every ``WP-NNN-*.md`` under
     ``.architecture/verification-by-design/work-packages/`` (each
     carries the new ``verification:`` frontmatter per ADR-003)

   P-VER MUST return PASS. This is the ship gate per ADR-002 + NFR-005.

3. **Grandfather check** — a synthetic fixture with a backdated
   ``started_at`` returns ``PASS_GRANDFATHERED`` and skips every other
   check (ADR-002 + ADR-006).

4. **WP frontmatter shape** — every WP-NNN-*.md carries the
   ``verification:`` field per ADR-003's three valid shapes
   (concrete / deferred / trivial-carveout).

The dogfood test specifically defends NFR-005: this change cannot merge
to ``dev`` until P-VER passes against its own artifacts.

Per WP Notes: no flakiness budget. All assertions are structural
(section presence, subsection count, ≥30-char content, citation by
relative path, verdict equality). No assertions on specific wording.
"""

from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

# tests/integration/ -> tests/ -> scripts/
_SCRIPTS_DIR = Path(__file__).resolve().parents[2]
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _p_ver_rubric import run_p_ver  # noqa: E402 — path-insert above

# ---------------------------------------------------------------------------
# Repo + artifact paths
# ---------------------------------------------------------------------------
#
# scripts/ -> sulis/ -> plugins/ -> repo root
_REPO_ROOT = _SCRIPTS_DIR.parent.parent.parent
_AGENT_PROMPT = _REPO_ROOT / "plugins" / "sulis" / "agents" / "requirements-analyst.md"
_CANONICAL_REL_PATH = "plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md"

_SRD = _REPO_ROOT / ".specifications" / "verification-by-design" / "SRD.md"
_TDD = _REPO_ROOT / ".architecture" / "verification-by-design" / "TDD.md"
_WPS_DIR = _REPO_ROOT / ".architecture" / "verification-by-design" / "work-packages"

# The six required Verification Plan subsections, in order, per the
# requirements-analyst agent's Phase 3 output spec (and the SRD's
# FR-001). Future agent dispatches MUST emit these exact headings.
_REQUIRED_SUBSECTIONS = (
    "### What user-observable behaviour are we verifying?",
    "### Verification environment(s)",
    "### Bootstrap-from-zero case",
    "### Per-integration verification strategy",
    "### Per-kind verification adapter",
    "### Infrastructure needs surfaced (deferred)",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _stage_dogfood_artifacts(into: Path) -> None:
    """Copy this change's own SRD + TDD + every WP into ``into``.

    P-VER globs ``*.md`` under one directory; staging the live artifacts
    into a single tmp dir lets us run the harness against the real prose
    without changing the harness's contract. ``WP-008`` is included even
    though it is this WP — by the time the dogfood test runs in CI the
    file will have its final shape.
    """
    shutil.copy(_SRD, into / "SRD.md")
    shutil.copy(_TDD, into / "TDD.md")
    for wp in sorted(_WPS_DIR.glob("WP-*.md")):
        shutil.copy(wp, into / wp.name)


def _extract_front_matter(text: str) -> str | None:
    """Return the YAML front-matter block between leading ``---`` fences."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if match is None:
        return None
    return match.group(1)


# ---------------------------------------------------------------------------
# Test 1 — Methodology: agent prompt cites canonical + names subsections
# ---------------------------------------------------------------------------


def test_methodology_agent_prompt_cites_canonical_and_specifies_six_subsections() -> (
    None
):
    """Proof pillar test class 3 — structural assertion.

    The methodology test asserts the *real* agent prompt (the source of
    truth for what a dispatch produces) contains:

    1. The canonical citation by relative path
       (``plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md``)
       so the rubric's 9.06 citation check finds it in produced SRDs.
    2. Each of the six required Verification Plan subsection headings
       so a faithful dispatch emits them all (and the rubric's 9.01
       section-presence check passes).
    3. A reference to Phase 3 (when the verification questions are asked
       per the agent prompt's "Asking the Verification Questions" block).

    No LLM dispatch is performed — this is a structural acceptance test
    of the prompt itself. Verifying the prompt's contract surface is the
    deterministic equivalent of dispatching the agent.
    """
    assert _AGENT_PROMPT.exists(), (
        f"requirements-analyst agent prompt missing at {_AGENT_PROMPT}. "
        "WP-003 should have shipped this update."
    )
    prompt_text = _AGENT_PROMPT.read_text(encoding="utf-8")

    # (1) Canonical citation by relative path
    assert _CANONICAL_REL_PATH in prompt_text, (
        f"requirements-analyst.md does not cite the canonical at "
        f"{_CANONICAL_REL_PATH!r}. WP-003's agent update must add the "
        "citation so the rubric's 9.06 check anchors cleanly."
    )

    # (2) Each of the six required subsection headings appears in the prompt
    for heading in _REQUIRED_SUBSECTIONS:
        assert heading in prompt_text, (
            f"requirements-analyst.md does not name the required "
            f"Verification Plan subsection {heading!r}. The agent's "
            "Phase 3 output spec must enumerate every subsection so a "
            "faithful dispatch emits the full set (rubric 9.01)."
        )

    # (3) Phase 3 context — the prompt must instruct the agent to ask the
    # verification questions during convergent specification.
    assert re.search(r"\bPhase\s*3\b", prompt_text), (
        "requirements-analyst.md must reference Phase 3 (convergent "
        "specification) — the phase during which the verification "
        "questions are asked per FR-003."
    )


# ---------------------------------------------------------------------------
# Test 2 — Dogfood: P-VER PASS on this change's own artifacts
# ---------------------------------------------------------------------------


def test_dogfood_p_ver_passes_on_own_artifacts(tmp_path: Path) -> None:
    """Proof pillar test class 5 — NFR-005 dogfood gate.

    Stage this change's own SRD + TDD + every WP into a temp directory
    (P-VER globs ``*.md`` under one fixture dir; the live artifacts
    span three real directories) and run the harness.

    Expected: ``Verdict.verdict == "PASS"``. Any other verdict surfaces
    the rubric's exact failed-check ID + remediation message so the
    failure is debuggable per WP Blue D-o-D bullet 2.

    Per ADR-002: this change cannot merge to ``dev`` until this test
    returns green in CI. This is the load-bearing acceptance evidence
    for the whole refinement.
    """
    fixture_dir = tmp_path / "dogfood"
    fixture_dir.mkdir()
    _stage_dogfood_artifacts(fixture_dir)

    verdict = run_p_ver(fixture_dir)

    assert verdict.verdict == "PASS", (
        f"P-VER FAILED on this change's own artifacts (NFR-005 dogfood "
        f"gate violated). Failed check: {verdict.failed_check!r}. "
        f"Artifact: {verdict.artifact!r}. Message: {verdict.message!r}."
    )
    assert verdict.failed_check is None, (
        f"PASS verdict must have no failed_check; got {verdict.failed_check!r}."
    )


# ---------------------------------------------------------------------------
# Test 3 — Grandfather check returns PASS_GRANDFATHERED
# ---------------------------------------------------------------------------


def test_grandfather_check_returns_pass_grandfathered_for_pre_merge_change(
    tmp_path: Path,
) -> None:
    """Proof pillar — grandfather sub-phase per ADR-002 + ADR-006.

    Construct a synthetic fixture whose change record's ``started_at``
    precedes the rubric's ``verification_required_from`` constant. The
    fixture's SRD is deliberately *missing* a Verification Plan section
    — under normal scoring this would FAIL 9.01, but the grandfather
    sub-phase MUST short-circuit and return ``PASS_GRANDFATHERED``.

    The synthetic SRD also omits the canonical citation; if 9.06 were
    to fire, the test would fail loudly.
    """
    fixture_dir = tmp_path / "grandfathered"
    fixture_dir.mkdir()

    # SRD without Verification Plan section, without citation — would
    # FAIL 9.01 + 9.06 under normal scoring.
    (fixture_dir / "SRD.md").write_text(
        "# Pre-merge SRD — grandfathered\n\nLegacy content.\n",
        encoding="utf-8",
    )

    # rubric.yaml — the test-local stand-in for the merge-date constant.
    (fixture_dir / "rubric.yaml").write_text(
        "verification_required_from: 2026-06-15\n",
        encoding="utf-8",
    )

    # Change record with a backdated started_at.
    changes_dir = fixture_dir / ".changes"
    changes_dir.mkdir()
    (changes_dir / "legacy.yaml").write_text(
        "kind: documentation\nstarted_at: 2026-05-01T00:00:00Z\n",
        encoding="utf-8",
    )

    verdict = run_p_ver(fixture_dir)

    assert verdict.verdict == "PASS_GRANDFATHERED", (
        f"Grandfathered change should short-circuit to "
        f"PASS_GRANDFATHERED, got {verdict.verdict!r}. "
        f"Message: {verdict.message!r}."
    )
    assert verdict.failed_check is None, (
        f"Grandfathered verdict must have no failed_check; got "
        f"{verdict.failed_check!r}."
    )


# ---------------------------------------------------------------------------
# Test 4 — Every WP carries verification: frontmatter (ADR-003)
# ---------------------------------------------------------------------------


def test_every_wp_has_verification_frontmatter_per_adr_003() -> None:
    """ADR-003 dogfood — every WP in this set carries the new
    ``verification:`` frontmatter field in one of three valid shapes.

    Shape 1 (concrete):     adapter + artifact
    Shape 2 (deferred):     adapter + deferred-to-follow-on
    Shape 3 (trivial):      na: true + justification

    This is the first WP set to enforce ADR-003. The rubric's 9.07 check
    fires on missing fields; this test fails loudly with the specific
    WP path if any WP omits the field, so debugging is one assertion-
    line away.
    """
    wp_files = sorted(_WPS_DIR.glob("WP-*.md"))
    assert wp_files, (
        f"No WP files found under {_WPS_DIR}. This is the dogfood "
        "fixture root; the test cannot run."
    )

    missing: list[str] = []
    for wp_path in wp_files:
        front_matter = _extract_front_matter(wp_path.read_text(encoding="utf-8"))
        if front_matter is None:
            missing.append(f"{wp_path.name}: no front matter")
            continue
        # Field exists if `verification:` appears as a top-level key.
        if not re.search(r"^\s*verification:\s*$", front_matter, re.MULTILINE):
            missing.append(f"{wp_path.name}: no `verification:` field")
            continue
        # And the field is one of the three ADR-003 shapes.
        has_adapter = bool(re.search(r"^\s+adapter:\s*\S+", front_matter, re.MULTILINE))
        has_artifact = bool(
            re.search(r"^\s+artifact:\s*\S+", front_matter, re.MULTILINE)
        )
        has_deferred = bool(
            re.search(
                r"^\s+deferred[_-]to[_-]follow[_-]on:", front_matter, re.MULTILINE
            )
        )
        has_na_true = bool(re.search(r"^\s+na:\s*true\b", front_matter, re.MULTILINE))
        # Shape 1 = adapter + artifact; Shape 2 = adapter + deferred-to-follow-on;
        # Shape 3 = na: true (justification scrutinised by rubric, not here).
        shape_1 = has_adapter and has_artifact
        shape_2 = has_adapter and has_deferred
        shape_3 = has_na_true
        if not (shape_1 or shape_2 or shape_3):
            missing.append(
                f"{wp_path.name}: verification: field is not one of the "
                "three ADR-003 shapes (concrete / deferred / "
                "trivial-carveout)"
            )

    assert not missing, (
        "ADR-003 dogfood failed — some WPs are missing or malformed "
        "verification: frontmatter:\n  - " + "\n  - ".join(missing)
    )
