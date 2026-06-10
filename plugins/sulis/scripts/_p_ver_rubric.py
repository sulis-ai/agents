"""P-VER rubric harness — eight failure-mode checks + grandfather sub-phase.

The validation contract is the prose in
``plugins/sulis/references/decompose-validation-rubric.md`` § Phase 9
(shipped by WP-002). This module is the smallest mechanical
implementation that applies the eight checks 9.01..9.08 plus the
grandfather sub-phase to a directory of synthetic SRD/TDD/WP
artifacts.

Scope (per WP-007 Notes):

- This harness is scoped to P-VER. Other rubric phases have their
  own runners.
- Stdlib-only — no PyYAML. The synthetic fixtures use the trivial
  front-matter subset the rubric needs (top-level scalars + the
  ``verification:`` field's three documented shapes per ADR-003).
- WP Notes flagged a target ceiling around ~100 LOC; the actual
  implementation lands at ~400 LOC because each of the eight checks
  ships with a remediation message + scope-relative path resolution
  + idempotency guarantees, which the prose ceiling did not foresee.
  If the harness grows beyond ~600 LOC, split per the WP Notes
  follow-on plan.

Contract:

* ``run_p_ver(fixture_dir: Path) -> Verdict`` — invokes the rubric
  against every ``.md`` artifact (SRD, TDD, WP) under the fixture
  directory plus the optional ``.changes/*.yaml`` change record.
  Returns the **first** failing check or a PASS verdict.
* Verdict semantics — exactly three:
    - ``PASS`` — every check on every artifact returned pass.
    - ``FAIL`` — one or more checks failed; ``failed_check`` carries
      the first failure's ID (9.01..9.08) and ``message`` carries the
      remediation prose from the rubric.
    - ``PASS_GRANDFATHERED`` — the change's ``started_at`` precedes
      ``verification_required_from`` (ADR-002 + ADR-006). Short-
      circuits all 9.01..9.08 checks.

The rubric prose is the source of truth; this module pins the prose
in code. Drift between the two is the failure mode P-VER itself
exists to catch — caught here by ``test_p_ver_rubric.py``.
"""

from __future__ import annotations

import datetime as _dt
import re
from dataclasses import dataclass
from pathlib import Path

from _wpxlib import is_wp_id_filename

_CANONICAL_REL_PATH = "plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md"

_PLACEHOLDER_TOKENS = ("TBD", "tbd", "TODO", "todo", "…", "FIXME")

# Adapter rows in VERIFICATION_QUESTIONS.md (locked by ADR-007).
_VALID_KINDS = frozenset(
    {
        "methodology",
        "backend",
        "frontend",
        "async",
        "infrastructure",
        "documentation",
        "contract",
    }
)


@dataclass(frozen=True)
class Verdict:
    """The outcome of a P-VER run against a fixture directory."""

    verdict: str  # "PASS" | "FAIL" | "PASS_GRANDFATHERED"
    failed_check: str | None  # "9.01".."9.08" on FAIL, else None
    message: str
    artifact: str | None = None  # path that triggered the failure


def run_p_ver(fixture_dir: Path) -> Verdict:
    """Apply the P-VER rubric to every artifact under ``fixture_dir``.

    Order of operations:

    1. **Grandfather sub-phase.** Read ``.changes/*.yaml`` for the
       change. If ``started_at`` precedes ``verification_required_from``
       (the fixture's own ``rubric.yaml`` carries the comparison
       constant), short-circuit to ``PASS_GRANDFATHERED``.
    2. **9.05 unmapped-kind.** Read the change's ``kind:`` and verify
       it appears in the adapter table (ADR-007). Runs first so an
       unmapped kind fails before any per-artifact check.
    3. **Per-artifact checks** in 9.01 → 9.02 → 9.03 → 9.06 → 9.04
       order on each SRD/TDD; 9.07/9.08 on each WP.

    Returns the first failing check encountered. PASS only if every
    artifact clears every applicable check.
    """
    # ----- Grandfather sub-phase -----
    grandfather_verdict = _check_grandfather(fixture_dir)
    if grandfather_verdict is not None:
        return grandfather_verdict

    # ----- 9.05 unmapped-kind (whole-fixture check) -----
    kind_verdict = _check_kind_mapped(fixture_dir)
    if kind_verdict is not None:
        return kind_verdict

    # ----- Per-artifact checks: SRD + TDD (9.01, 9.02, 9.03, 9.06, 9.04) -----
    for artifact in sorted(fixture_dir.glob("*.md")):
        name = artifact.name
        # WPs run their own check set; skip them here. is_wp_id_filename
        # recognises prefixed `CH-…-WP-NNN-*.md` files too (they start with
        # `CH-`, so the old `startswith("WP-")` mis-classified them as
        # SRD/TDD artifacts) — ADR-001 single-source matcher.
        if is_wp_id_filename(name):
            continue
        text = artifact.read_text(encoding="utf-8")
        for check in (
            _check_section_present,  # 9.01
            _check_no_placeholders,  # 9.02
            _check_na_justified,  # 9.03
            _check_citation_present,  # 9.06
            _check_existing_paths_resolve,  # 9.04
        ):
            verdict = check(text, artifact, fixture_dir)
            if verdict is not None:
                return verdict

    # ----- Per-WP checks (9.07, 9.08) -----
    change_kind = _read_change_kind(fixture_dir)
    for wp_artifact in sorted(fixture_dir.glob("WP-*.md")):
        text = wp_artifact.read_text(encoding="utf-8")
        for check in (
            _check_wp_verification_field,  # 9.07
            _check_wp_adapter_matches,  # 9.08
        ):
            verdict = check(text, wp_artifact, change_kind)
            if verdict is not None:
                return verdict

    return Verdict(verdict="PASS", failed_check=None, message="All checks passed.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_change_yaml(fixture_dir: Path) -> dict[str, str]:
    """Read the change record (.changes/*.yaml) into a flat dict.

    The fixtures use a trivial scalar-only YAML subset — one key per
    line, optional quoted-string value. No nested structures.
    """
    changes_dir = fixture_dir / ".changes"
    if not changes_dir.exists():
        return {}
    for path in sorted(changes_dir.glob("*.yaml")):
        return _parse_flat_yaml(path.read_text(encoding="utf-8"))
    return {}


def _parse_flat_yaml(text: str) -> dict[str, str]:
    """Trivial flat-scalar YAML parser (one key: value per line)."""
    result: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        value = value.strip().strip("'\"")
        result[key.strip()] = value
    return result


def _read_change_kind(fixture_dir: Path) -> str | None:
    """Return the ``kind:`` field from the fixture's change record."""
    return _read_change_yaml(fixture_dir).get("kind")


def _check_grandfather(fixture_dir: Path) -> Verdict | None:
    """Grandfather sub-phase per ADR-002 + ADR-006.

    Reads ``verification_required_from`` from the fixture's
    ``rubric.yaml`` (the test-local stand-in for the real rubric's
    front-matter constant — keeps the fixtures self-contained) and
    compares it against the change record's ``started_at``.
    """
    rubric_yaml = fixture_dir / "rubric.yaml"
    if not rubric_yaml.exists():
        return None  # No grandfather data → fall through to normal checks.
    rubric_cfg = _parse_flat_yaml(rubric_yaml.read_text(encoding="utf-8"))
    required_from = rubric_cfg.get("verification_required_from", "")
    if not required_from:
        return None  # Empty constant → dogfood mode; check every change.
    change_cfg = _read_change_yaml(fixture_dir)
    started_at = change_cfg.get("started_at", "")
    if not started_at:
        return None  # Unparseable → fall through (not grandfathered).
    try:
        required_dt = _dt.date.fromisoformat(required_from)
        started_dt = _dt.date.fromisoformat(started_at[:10])
    except ValueError:
        return None  # Malformed → fall through.
    if started_dt < required_dt:
        return Verdict(
            verdict="PASS_GRANDFATHERED",
            failed_check=None,
            message=(
                f"Change started_at {started_at} precedes "
                f"verification_required_from {required_from}; P-VER skipped."
            ),
        )
    return None


def _check_kind_mapped(fixture_dir: Path) -> Verdict | None:
    """9.05 — change ``kind:`` must have an adapter row in the canonical."""
    kind = _read_change_kind(fixture_dir)
    if kind is None:
        return None  # No change record → 9.05 N/A; per-artifact checks handle it.
    if kind not in _VALID_KINDS:
        return Verdict(
            verdict="FAIL",
            failed_check="9.05",
            message=(
                f"Change kind: {kind!r} has no adapter row in "
                f"{_CANONICAL_REL_PATH}. Add the row via a methodology "
                "change (ADR-007), then re-run P-VER."
            ),
            artifact=str(fixture_dir / ".changes"),
        )
    return None


def _verification_plan_body(text: str) -> str | None:
    """Return the text of the ``## Verification Plan`` section, or None."""
    match = re.search(r"^##\s+Verification\s+Plan\s*$", text, re.MULTILINE)
    if not match:
        return None
    start = match.end()
    next_header = re.search(r"^##\s+", text[start:], re.MULTILINE)
    end = start + next_header.start() if next_header else len(text)
    return text[start:end]


def _check_section_present(text: str, artifact: Path, _: Path) -> Verdict | None:
    """9.01 — ``## Verification Plan`` section heading must be present."""
    if _verification_plan_body(text) is None:
        return Verdict(
            verdict="FAIL",
            failed_check="9.01",
            message=(
                f"Missing `## Verification Plan` section in {artifact.name}. "
                "Add the heading and populate the six subsections."
            ),
            artifact=str(artifact),
        )
    return None


def _check_no_placeholders(text: str, artifact: Path, _: Path) -> Verdict | None:
    """9.02 — no placeholder tokens inside the Verification Plan body."""
    body = _verification_plan_body(text)
    if body is None:
        return None  # 9.01 already failed this — defensive guard.
    for token in _PLACEHOLDER_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", body):
            return Verdict(
                verdict="FAIL",
                failed_check="9.02",
                message=(
                    f"Placeholder {token!r} in Verification Plan body of "
                    f"{artifact.name}. Replace with a concrete answer "
                    "(>=30 chars) — see Q1..Q4 in the canonical."
                ),
                artifact=str(artifact),
            )
    return None


def _check_na_justified(text: str, artifact: Path, _: Path) -> Verdict | None:
    """9.03 — bare ``n/a`` without a >=30-char justification fails."""
    body = _verification_plan_body(text)
    if body is None:
        return None
    for line in body.splitlines():
        stripped = line.strip()
        # Match `n/a` standalone OR `n/a` followed by < 30 chars of content
        match = re.match(
            r"^[-*]?\s*(?:[A-Z][^:]+:\s*)?n/a\b(.*)$", stripped, re.IGNORECASE
        )
        if match:
            tail = match.group(1).strip(" -—:.")
            if len(tail) < 30:
                return Verdict(
                    verdict="FAIL",
                    failed_check="9.03",
                    message=(
                        f"Bare `n/a` without justification in {artifact.name}. "
                        "Add a >=30-character sentence explaining why this "
                        "subsection does not apply (Q9 / Q17 guidance)."
                    ),
                    artifact=str(artifact),
                )
    return None


def _check_citation_present(text: str, artifact: Path, _: Path) -> Verdict | None:
    """9.06 — artifact must cite VERIFICATION_QUESTIONS.md by relative path."""
    if _CANONICAL_REL_PATH not in text:
        return Verdict(
            verdict="FAIL",
            failed_check="9.06",
            message=(
                f"{artifact.name} is missing the citation to "
                f"{_CANONICAL_REL_PATH}. Add the canonical HTML-comment "
                "annotation immediately before the `## Verification Plan` "
                "section."
            ),
            artifact=str(artifact),
        )
    return None


def _check_existing_paths_resolve(
    text: str, artifact: Path, fixture_dir: Path
) -> Verdict | None:
    """9.04 — `existing: <path>` lines in Verification Plan must resolve.

    The fixture's `existing:` lines are resolved relative to the
    fixture directory itself (the synthetic-repo root).
    """
    body = _verification_plan_body(text)
    if body is None:
        return None
    for match in re.finditer(r"existing:\s*([^\s`]+)", body):
        cited = match.group(1).rstrip(".,)")
        if not (fixture_dir / cited).exists():
            return Verdict(
                verdict="FAIL",
                failed_check="9.04",
                message=(
                    f"{artifact.name} claims `existing` infrastructure at "
                    f"{cited!r}, but no file at that path exists. Either "
                    "fix the path, classify as `deferred` with a canonical "
                    "need identifier, or remove the entry."
                ),
                artifact=str(artifact),
            )
    return None


def _check_wp_verification_field(
    text: str, artifact: Path, _: str | None
) -> Verdict | None:
    """9.07 — WP frontmatter must carry a ``verification:`` field."""
    front_matter = _extract_front_matter(text)
    has_field = front_matter is not None and re.search(
        r"^\s*verification:\s*$", front_matter, re.MULTILINE
    )
    if not has_field:
        return Verdict(
            verdict="FAIL",
            failed_check="9.07",
            message=(
                f"WP `{artifact.name}` is missing the `verification:` "
                "frontmatter field. See ADR-003 for the three valid "
                "shapes (concrete / deferred / trivial carveout)."
            ),
            artifact=str(artifact),
        )
    return None


def _check_wp_adapter_matches(
    text: str, artifact: Path, change_kind: str | None
) -> Verdict | None:
    """9.08 — WP ``verification.adapter`` must equal the change ``kind:``."""
    front_matter = _extract_front_matter(text)
    if front_matter is None:
        return None  # 9.07 already failed this.
    # Trivial-carveout shape (`na: true`) skips the adapter check.
    if re.search(r"^\s*na:\s*true\b", front_matter, re.MULTILINE):
        return None
    adapter_match = re.search(r"^\s*adapter:\s*(\S+)", front_matter, re.MULTILINE)
    if adapter_match is None:
        return None  # 9.07 covers absence of the field.
    adapter = adapter_match.group(1).strip("'\"")
    if change_kind is not None and adapter != change_kind:
        return Verdict(
            verdict="FAIL",
            failed_check="9.08",
            message=(
                f"WP `{artifact.name}` declares `verification.adapter: "
                f"{adapter}` but the change `kind:` is `{change_kind}`. "
                "Adapter must match the change kind (or list it in "
                "additional-adapters)."
            ),
            artifact=str(artifact),
        )
    return None


def _extract_front_matter(text: str) -> str | None:
    """Return the YAML front-matter block between leading ``---`` fences."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if match is None:
        return None
    return match.group(1)
