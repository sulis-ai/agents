"""WP-008 — conformance tests for plugins/sulis/skills/discover-project/SKILL.md.

The SKILL.md is the imperative side of Path A for the discover-project
Workflow (per ADR-001). Conformance has two surfaces:

1. Structural — the file exists with the right frontmatter, mentions
   each phase helper, describes the 3 CLI flags, emits per-phase
   structured log lines, and specifies the JSON envelope shapes. The
   `<!-- canonical:step:<name> -->` annotation set matches the
   canonical `steps.jsonld` set exactly (n=2 dogfood of the drift
   detector's HTML-comment parser, ADR-001).

2. Drift detector — invoking `check-canonical-drift.py` with the skill
   as the imperative target returns exit 0. This is the load-bearing
   acceptance check for the WP.

Tests in this file cover the structural surface (11 tests). The drift
detector dogfood test lives in `test_check_canonical_drift_discover.py`
(WP-009 + WP-008 acceptance) to keep that file's fixture machinery
co-located with its other dogfood asserts.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

# Resolve the marketplace root from this test's location.
# Layout: <root>/plugins/sulis/scripts/tests/unit/test_*.py
_HERE = Path(__file__).resolve().parent
_MARKETPLACE_ROOT = _HERE.parent.parent.parent.parent.parent  # five levels up

_SKILL_MD = (
    _MARKETPLACE_ROOT
    / "plugins"
    / "sulis"
    / "skills"
    / "discover-project"
    / "SKILL.md"
)
_STEPS_JSONLD = (
    _MARKETPLACE_ROOT
    / "plugins"
    / "sulis"
    / "instances"
    / "discover-project"
    / "steps.jsonld"
)

# Expected byte-exact canonical workflow ULID per TDD §Canonical Identifiers.
_EXPECTED_WORKFLOW_ULID = "dna:workflow:01KT1WDSCVRWFW00000000000A"
_EXPECTED_CANONICAL_SOURCE = (
    "plugins/sulis/instances/discover-project/workflow.jsonld"
)

# The phase helpers the skill must reference by name (the Python
# symbols imported from `_discovery.*` plus the slug helpers).
_PHASE_HELPERS = [
    "LocalFilesystemInspector",
    "LLMConfigurationInferrer",
    "NullConfigurationInferrer",
    "write_project_entity",
    "verify_and_roll_back_on_failure",
    "Sha256CrockfordTenantDeriver",
    "slug_from_project_name",
    "slug_from_monorepo_path",
    "stale_tmp_sweep",
    "install_sigint_handler",
]

# The 3 CLI flags per ADR-005 + the WP Contract.
_FLAGS = ["--update", "--path", "--source-repo"]

# The 5 phases per WP-001's workflow.jsonld phases order.
_PHASES = ["Detect", "Infer", "Ask", "Mint", "Verify"]

# The 3 prose-fragment paths the skill must reference (WP-005 source-of-
# truth files; SKILL.md includes them by reference, never duplicates).
_PROMPT_FRAGMENTS = [
    "_prompts/confirm-or-override.md",
    "_prompts/gather-ambiguous-fields.md",
    "_prompts/per-field-diff.md",
]


# ─── Helpers ─────────────────────────────────────────────────────────────


def _read_skill() -> str:
    """Read the SKILL.md content."""
    return _SKILL_MD.read_text(encoding="utf-8")


def _split_frontmatter(content: str) -> tuple[dict[str, str], str]:
    """Split off YAML frontmatter (`---` delimited) and return (frontmatter, body).

    Returns ({}, content) if no frontmatter is present.
    """
    if not content.startswith("---\n"):
        return {}, content
    end = content.find("\n---\n", 4)
    if end == -1:
        return {}, content
    fm_text = content[4:end]
    body = content[end + 5 :]
    fm: dict[str, str] = {}
    for line in fm_text.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            fm[key.strip()] = val.strip()
    return fm, body


def _canonical_step_names() -> set[str]:
    """Return the set of canonical Step names from steps.jsonld."""
    data = json.loads(_STEPS_JSONLD.read_text(encoding="utf-8"))
    return {s["name"] for s in data["steps"]}


# ─── Tests ───────────────────────────────────────────────────────────────


def test_skill_md_exists():
    """The skill markdown file is present at the WP-specified path."""
    assert _SKILL_MD.exists(), (
        f"SKILL.md missing at {_SKILL_MD}; WP-008 deliverable not authored."
    )


def test_skill_canonical_source_field():
    """Front-matter `canonical_source` names the WP-001 workflow.jsonld."""
    fm, _ = _split_frontmatter(_read_skill())
    assert fm.get("canonical_source") == _EXPECTED_CANONICAL_SOURCE, (
        f"canonical_source != expected; got {fm.get('canonical_source')!r}"
    )


def test_skill_workflow_ulid_field():
    """Front-matter `canonical_workflow_ulid` is byte-exact."""
    fm, _ = _split_frontmatter(_read_skill())
    assert fm.get("canonical_workflow_ulid") == _EXPECTED_WORKFLOW_ULID, (
        f"canonical_workflow_ulid != expected; got "
        f"{fm.get('canonical_workflow_ulid')!r}"
    )


def test_skill_has_one_annotation_per_canonical_step():
    """Set of `<!-- canonical:step:<name> -->` annotations == canonical Step set.

    n=2 dogfood of the drift detector's HTML-comment parser. No missing,
    no extra.
    """
    content = _read_skill()
    annotation_re = re.compile(
        r"<!--\s*canonical:step:(?P<name>[A-Za-z0-9._-]+)\s*-->"
    )
    annotated = {m.group("name") for m in annotation_re.finditer(content)}
    canonical = _canonical_step_names()
    missing = canonical - annotated
    extra = annotated - canonical
    assert not missing and not extra, (
        f"Annotation mismatch — missing={sorted(missing)} extra={sorted(extra)}"
    )


def test_skill_imports_each_phase_helper():
    """Body references every phase helper symbol by name."""
    content = _read_skill()
    missing = [h for h in _PHASE_HELPERS if h not in content]
    assert not missing, f"Helper symbols not referenced in SKILL.md: {missing}"


def test_skill_describes_3_flags():
    """The Flags section names each CLI flag."""
    content = _read_skill()
    missing = [f for f in _FLAGS if f not in content]
    assert not missing, f"CLI flags missing from SKILL.md: {missing}"


def test_skill_emits_structured_log_lines_per_phase():
    """Each phase has a `[discover-project] <Phase> phase:` line."""
    content = _read_skill()
    missing = []
    for phase in _PHASES:
        marker = f"[discover-project] {phase} phase:"
        if marker not in content:
            missing.append(marker)
    assert not missing, f"Per-phase structured log lines missing: {missing}"


def test_skill_specifies_json_envelope():
    """Output envelope section names both ok-true and ok-false shapes."""
    content = _read_skill()
    assert '"ok": true' in content, "JSON envelope ok-true shape missing"
    assert '"ok": false' in content, "JSON envelope ok-false shape missing"


def test_skill_specifies_pre_flight_sweep():
    """`stale_tmp_sweep` is invoked before Phase 1.

    The pre-flight sentence mentioning `stale_tmp_sweep` MUST appear in
    the file BEFORE the `## Phase 1` heading. Prior dispatch had the
    sweep mentioned but in the wrong sequence; this test pins ordering.
    """
    content = _read_skill()
    sweep_idx = content.find("stale_tmp_sweep")
    phase_1_idx = content.find("## Phase 1")
    assert sweep_idx >= 0, "stale_tmp_sweep not mentioned at all"
    assert phase_1_idx >= 0, "## Phase 1 heading missing"
    assert sweep_idx < phase_1_idx, (
        f"stale_tmp_sweep (idx {sweep_idx}) must precede ## Phase 1 "
        f"(idx {phase_1_idx}); pre-flight sweep belongs before Phase 1."
    )


def test_skill_includes_prompt_fragments():
    """Each WP-005 prose-fragment path is referenced verbatim."""
    content = _read_skill()
    missing = [p for p in _PROMPT_FRAGMENTS if p not in content]
    assert not missing, f"Prompt fragment paths not referenced: {missing}"


def test_skill_phase_sections_in_canonical_order():
    """Phase headings appear in the WP-001 workflow.jsonld order.

    Detect → Infer → Ask → Mint → Verify. Drift between SKILL.md
    ordering and the canonical phases field would split the imperative
    from the canonical contract.
    """
    content = _read_skill()
    indices = []
    for phase in _PHASES:
        # find the specific phase heading
        idx = content.find(f"— {phase}")
        if idx == -1:
            idx = content.find(f"- {phase}")
        if idx == -1:
            # fall back: search for "Phase N — <name>" pattern
            for n in range(1, 6):
                cand = content.find(f"Phase {n} — {phase}")
                if cand >= 0:
                    idx = cand
                    break
        assert idx >= 0, f"Phase heading for {phase!r} not found"
        indices.append(idx)
    assert indices == sorted(indices), (
        f"Phase sections out of canonical order; indices={indices} for {_PHASES}"
    )
