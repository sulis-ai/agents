"""test_lifecycle_steps_canonical — WP-001 (CH-01KT61,
product-project-opportunity-evolution).

Validates that `plugins/sulis/instances/lifecycle-steps/steps.jsonld`:

1. Parses as valid JSON-LD with the expected envelope shape.
2. Declares exactly 3 canonical lifecycle Step instances.
3. Each Step validates against the vendored foundation Step JSON
   Schema (v1.2.0) at
   `plugins/sulis/brain/compiled/foundation/step.schema.json`.
4. The 3 Step ULIDs are byte-exact against the canonical identifiers
   pinned in `TDD.md §Canonical Identifiers — Canonical lifecycle Step
   instances` (the load-bearing cross-WP source — WP-002 / WP-006 /
   WP-007 transcribe these, never re-mint).
5. Every ULID is a clean 26-char Crockford base32 string (no I/L/O/U).

These Steps are the `prov:Plan` definitions the v2.1.0 LifecycleRun
`step` ref points at (ADR-001: a LifecycleRun *instantiates* a Step via
`sulis:viaStep`). The three reusable Plans are `change-started`,
`change-shipped`, and the catch-all `unclassified-lifecycle-step`.

Deliberately deterministic + offline — no network, no LLM, no
subprocess. The schema comes from the vendored brain/compiled
directory; the instance from the lifecycle-steps instances directory.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

# plugins/sulis/scripts/tests/unit/<this file> → parents[5] == repo root
_REPO_ROOT = Path(__file__).resolve().parents[5]
_INSTANCE_PATH = (
    _REPO_ROOT / "plugins" / "sulis" / "instances" / "lifecycle-steps" / "steps.jsonld"
)
_SCHEMA_PATH = (
    _REPO_ROOT
    / "plugins"
    / "sulis"
    / "brain"
    / "compiled"
    / "foundation"
    / "step.schema.json"
)

# ── Canonical identifiers — byte-exact from TDD §Canonical Identifiers ──
# Source: .architecture/product-project-opportunity-evolution/TDD.md
#   §Canonical lifecycle Step instances (ADR-001/004). Drift in any of
#   these breaks the whole lifecyclerun-migration chain (WP-002/006/007
#   resolve their `step` refs against these exact ULIDs).
_CANONICAL_STEP_ULIDS: dict[str, str] = {
    "change-started": "dna:step:01KT61X5ST01CHANGESTART00A",
    "change-shipped": "dna:step:01KT61X5ST02CHANGESH1PP00A",
    "unclassified-lifecycle-step": "dna:step:01KT61X5ST03VNC1ASS1F1ED0A",
}
_EXPECTED_STEP_COUNT = len(_CANONICAL_STEP_ULIDS)  # 3

# Crockford base32 charset excludes I, L, O, U. A clean Step ULID is
# the literal `dna:step:` prefix + exactly 26 Crockford-valid chars.
_ULID_BODY_RE = re.compile(r"^dna:step:[0-9A-HJKMNP-TV-Z]{26}$")
_FORBIDDEN_CROCKFORD_CHARS = set("ILOU")


# ── fixtures ──


@pytest.fixture(scope="module")
def instance() -> dict:
    """The parsed steps.jsonld envelope."""
    assert _INSTANCE_PATH.exists(), f"steps.jsonld missing at {_INSTANCE_PATH}"
    with _INSTANCE_PATH.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def steps(instance: dict) -> list[dict]:
    """The list of Step entries inside the envelope."""
    return instance["steps"]


@pytest.fixture(scope="module")
def schema() -> dict:
    """The vendored foundation Step schema (v1.2.0)."""
    assert _SCHEMA_PATH.exists(), f"foundation Step schema missing at {_SCHEMA_PATH}"
    with _SCHEMA_PATH.open() as f:
        return json.load(f)


# ── Test 1 — JSON-LD parses with the expected envelope shape ──


def test_steps_jsonld_parses(instance: dict) -> None:
    """The file is well-formed JSON-LD with the expected envelope."""
    assert "@context" in instance
    assert "@id" in instance
    assert "@type" in instance
    assert instance["@type"] == "step-instances"
    assert "steps" in instance
    assert isinstance(instance["steps"], list)


# ── Test 2 — exactly 3 Step instances ──


def test_steps_count_is_3(steps: list[dict]) -> None:
    """Exactly the 3 canonical lifecycle Steps, by exact-name match."""
    assert len(steps) == _EXPECTED_STEP_COUNT, (
        f"expected {_EXPECTED_STEP_COUNT} Steps, found {len(steps)}"
    )
    names = {s["name"] for s in steps}
    expected = set(_CANONICAL_STEP_ULIDS)
    missing = expected - names
    extra = names - expected
    assert not missing, f"missing Step names: {sorted(missing)}"
    assert not extra, f"unexpected Step names: {sorted(extra)}"


# ── Test 3 — each Step validates against the foundation Step schema ──


def test_each_step_validates_against_foundation_step_schema(
    steps: list[dict], schema: dict
) -> None:
    """Every Step validates against the foundation Step schema (v1.2.0).

    The schema sets `unevaluatedProperties: false` and requires
    id/name/for_domain/input_artifacts/output_artifacts/mechanism/state/
    sys_status — so the instances must carry the full IDEF0 contract,
    not a trimmed shape.
    """
    validator = Draft202012Validator(schema)
    errors_by_name: dict[str, list[str]] = {}
    for s in steps:
        errs = sorted(validator.iter_errors(s), key=lambda e: list(e.path))
        if errs:
            errors_by_name[s.get("name", "<unnamed>")] = [
                f"{list(e.path)}: {e.message}" for e in errs
            ]
    assert not errors_by_name, (
        f"schema validation failed for {len(errors_by_name)} Step(s): "
        f"{json.dumps(errors_by_name, indent=2)}"
    )


# ── Test 4 — the 3 ULIDs are byte-exact vs TDD §Canonical Identifiers ──


def test_step_ulids_match_canonical(steps: list[dict]) -> None:
    """Each Step's id is byte-identical to the TDD-pinned canonical ULID
    for its name. This file is the single source the migration chain
    transcribes — drift here breaks WP-002/006/007.
    """
    by_name = {s["name"]: s for s in steps}
    mismatches: list[str] = []
    for name, expected_ulid in _CANONICAL_STEP_ULIDS.items():
        actual = by_name.get(name, {}).get("id")
        if actual != expected_ulid:
            mismatches.append(f"{name}: got {actual!r}, expected {expected_ulid!r}")
    assert not mismatches, (
        "Step ULID drift vs TDD §Canonical Identifiers: " + "; ".join(mismatches)
    )


# ── Test 5 — every ULID is a clean 26-char Crockford string ──


def test_ulids_are_crockford_clean(steps: list[dict]) -> None:
    """Every Step id matches `dna:step:` + 26 Crockford-base32 chars,
    with no forbidden I/L/O/U in the 26-char body.
    """
    bad_pattern = [s["id"] for s in steps if not _ULID_BODY_RE.match(s["id"])]
    assert not bad_pattern, (
        f"Step ids fail the dna:step:<26 Crockford> pattern: {bad_pattern}"
    )
    bad_chars: list[str] = []
    for s in steps:
        body = s["id"].split("dna:step:", 1)[-1]
        offenders = _FORBIDDEN_CROCKFORD_CHARS & set(body)
        if offenders:
            bad_chars.append(f"{s['id']} contains forbidden {sorted(offenders)}")
    assert not bad_chars, (
        "Step ids contain forbidden Crockford chars (I/L/O/U): " + "; ".join(bad_chars)
    )


# ── Blue invariants — pin the refactor so it can't drift ──


def test_step_field_order_is_consistent(steps: list[dict]) -> None:
    """All 3 Steps carry the same field set in the same order — the
    deterministic shape that makes a regenerate byte-stable (DoD Blue).
    """
    orders = {tuple(s.keys()) for s in steps}
    assert len(orders) == 1, (
        f"Step field order/set is not consistent across entries: {orders}"
    )


def test_all_steps_mechanism_mixed(steps: list[dict]) -> None:
    """Every lifecycle Step is `mechanism: mixed` — each lifecycle moment
    is part automated command, part human/agent decision (DoD Blue).
    """
    bad = [
        (s["name"], s.get("mechanism")) for s in steps if s.get("mechanism") != "mixed"
    ]
    assert not bad, f"Steps with non-mixed mechanism: {bad}"


def test_envelope_carries_founder_readable_about(instance: dict) -> None:
    """The founder-readable note lives at the envelope (the foundation
    Step schema's `unevaluatedProperties: false` rejects a per-Step note
    field). It must be present and non-trivial (DoD Blue).
    """
    about = instance.get("_about")
    assert isinstance(about, str) and len(about.strip()) >= 80, (
        "envelope `_about` must be a substantive founder-readable note"
    )
