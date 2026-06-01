"""WP-001 — canonical entity instances + Tool schemas at
``plugins/sulis/instances/discover-project/``.

These tests are the contract for the discover-project Workflow. Per ADR-001
(Path A — canonical-as-spec) the JSON-LD entity instances ARE the
specification of truth: the skill prose (WP-008) conforms to them, the
drift detector (WP-007, WP-009) parses them, and downstream Python helpers
(WP-002, WP-003, WP-004, WP-006, WP-007) resolve identifiers pinned here.

Every ULID asserted in this module is sourced byte-exact from
``.architecture/discover-project/TDD.md`` §Canonical Identifiers (P8 rubric
pre-canonicalisation). NO inline minting; NO drift permitted.

Test surface (17 tests per WP-001 Definition of Done):

Parse + cardinality
- test_workflow_jsonld_parses
- test_steps_count_is_9
- test_triggers_count_is_1
- test_failuremodes_count_is_8
- test_tools_count_is_5_new

Schema validation (brain foundation schemas)
- test_workflow_validates_against_brain_schema
- test_each_step_validates_against_brain_schema
- test_each_muc_has_a_failuremode  (cardinality cross-check)
- test_each_tool_passes_brain_schema
- test_each_primary_tool_input_schema_lints

Canonical-ULID pin (TDD §Canonical Identifiers byte-exact)
- test_workflow_ulid_matches_canonical
- test_step_ulids_match_canonical
- test_marketplace_tenant_ulid_matches_release_train

Cross-WP refs resolve (graph integrity)
- test_step_tool_refs_resolve
- test_step_failuremode_refs_resolve  (handles_failures field)
- test_tool_error_catalogue_refs_resolve
- test_failuremode_user_messages_match_misuse_cases_md
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator, Draft7Validator


# ─── Path constants ──────────────────────────────────────────────────────

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parent.parent.parent.parent.parent  # → repo root
_INSTANCES_DIR = _REPO_ROOT / "plugins" / "sulis" / "instances" / "discover-project"
_SCHEMA_DIR = _REPO_ROOT / "plugins" / "sulis" / "brain" / "compiled" / "foundation"
_TOOL_SCHEMA_DIR = _INSTANCES_DIR / "schemas" / "tools"
_RELEASE_TRAIN_DIR = _REPO_ROOT / "plugins" / "sulis" / "instances" / "release-train"
_MISUSE_CASES_PATH = _REPO_ROOT / ".specifications" / "discover-project" / "MISUSE_CASES.md"


# ─── Canonical identifiers (TDD §Canonical Identifiers — byte-exact) ────

WORKFLOW_ULID = "dna:workflow:01KT1WDSCVRWFW00000000000A"
MARKETPLACE_TENANT_ULID = "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM"

STEP_ULIDS_IN_ORDER = [
    "dna:step:01KT1WDSST01RDREP0R00T000A",  # 1 read-repo-root
    "dna:step:01KT1WDSST02RDPKGMAN1FEST0",  # 2 read-package-manifests
    "dna:step:01KT1WDSST03RDC1W0RKF10W00",  # 3 read-ci-workflows
    "dna:step:01KT1WDSST04RDREP0C0NTR00A",  # 4 read-repo-contract
    "dna:step:01KT1WDSST05PR0P0SEC0NFG00",  # 5 propose-configuration-values
    "dna:step:01KT1WDSST06C0NF1RM0VRD000",  # 6 confirm-or-override-inferences
    "dna:step:01KT1WDSST07GATHERAMBF1000",  # 7 gather-ambiguous-fields
    "dna:step:01KT1WDSST08WR1TEPR0JEC000",  # 8 write-project-entity
    "dna:step:01KT1WDSST09RVNDR1FTDET000",  # 9 run-drift-detector-on-mint
]

TRIGGER_ULID = "dna:trigger:01KT1WDSTRG1MANVA10000000A"

FAILUREMODE_ULIDS = {
    "MUC-001": "dna:failuremode:01KT1WFM01N0NG1TD1R000000A",
    "MUC-002": "dna:failuremode:01KT1WFM02CANCE1M1DF10W000",
    "MUC-003": "dna:failuremode:01KT1WFM03ENT1TYEX1STS0000",
    "MUC-004": "dna:failuremode:01KT1WFM041NFERREJECTED000",
    "MUC-005": "dna:failuremode:01KT1WFM05VNKN0WNWFV11D000",
    "MUC-006": "dna:failuremode:01KT1WFM06G1TN0REM0TE00000",
    "MUC-007": "dna:failuremode:01KT1WFM07M0N0REP0C0110000",
    "MUC-008": "dna:failuremode:01KT1WFM08TKBDGTEXCEED0000",
}

TOOL_ULIDS = {
    "git-remote-read": "dna:tool:01KT1WT101G1TREM0TEREAD000",
    "read-package-json": "dna:tool:01KT1WT102RDPKGJS0N000000A",
    "read-pyproject-toml": "dna:tool:01KT1WT103RDPYPR0JT0M10000",
    "read-ci-workflows": "dna:tool:01KT1WT104RDC1WF000000000A",
    "derive-consumer-tenant": "dna:tool:01KT1WT105DER1VETENANT0000",
    "infer-configuration-values": "dna:tool:01KT1WT1061NFERC0NF1G00000",
}

# Primary Tools that MUST carry input + output JSON Schemas at schemas/tools/.
# Per WP-001 Contract: 5 primary Tools × 2 schemas = 10 schema files.
# derive-consumer-tenant is excluded — its Tool entity + Python implementation
# + fixed test vectors live in WP-002 (which also authors its schema pair
# downstream). The 5 primaries here are the Tools authored end-to-end in
# this WP.
PRIMARY_TOOL_NAMES = [
    "git-remote-read",
    "read-package-json",
    "read-pyproject-toml",
    "read-ci-workflows",
    "infer-configuration-values",
]


# ─── Loaders (read once, cached via pytest fixtures) ────────────────────


def _load_jsonld(name: str) -> dict:
    path = _INSTANCES_DIR / f"{name}.jsonld"
    return json.loads(path.read_text())


def _load_schema(name: str) -> dict:
    path = _SCHEMA_DIR / f"{name}.schema.json"
    return json.loads(path.read_text())


@pytest.fixture(scope="module")
def workflow_doc() -> dict:
    return _load_jsonld("workflow")


@pytest.fixture(scope="module")
def steps_doc() -> dict:
    return _load_jsonld("steps")


@pytest.fixture(scope="module")
def triggers_doc() -> dict:
    return _load_jsonld("triggers")


@pytest.fixture(scope="module")
def failuremodes_doc() -> dict:
    return _load_jsonld("failuremodes")


@pytest.fixture(scope="module")
def tools_doc() -> dict:
    return _load_jsonld("tools")


# ─── Parse + cardinality ────────────────────────────────────────────────


def test_workflow_jsonld_parses(workflow_doc):
    """workflow.jsonld is valid JSON and carries the expected envelope shape."""
    assert workflow_doc["@type"] == "workflow-instances"
    assert workflow_doc["for_tenant"] == MARKETPLACE_TENANT_ULID
    assert isinstance(workflow_doc["workflows"], list)
    assert len(workflow_doc["workflows"]) == 1


def test_steps_count_is_9(steps_doc):
    """Exactly 9 Step entities per TDD §Canonical Identifiers — Step ULIDs."""
    assert len(steps_doc["steps"]) == 9


def test_triggers_count_is_1(triggers_doc):
    """Per ADR-004: only the manual Trigger ships in v1."""
    assert len(triggers_doc["triggers"]) == 1
    assert triggers_doc["triggers"][0]["name"] == "manual-discover-project-invocation"


def test_failuremodes_count_is_8(failuremodes_doc):
    """One FailureMode per MUC; MISUSE_CASES.md defines MUC-001..MUC-008."""
    assert len(failuremodes_doc["failuremodes"]) == 8


def test_tools_count_is_5_new(tools_doc):
    """5 new typed Tools (state=active) authored in this WP.

    Reused Tools (`entity-emitter`, `drift-detector`) are declared via
    ``_reused_from`` rather than minting new ULIDs — they do not count
    toward the 5-new bound.
    """
    new_tools = [
        t for t in tools_doc["tools"] if t.get("state") == "active"
    ]
    assert len(new_tools) == 5, (
        f"Expected 5 state=active Tools; got {len(new_tools)}: "
        f"{[t['name'] for t in new_tools]}"
    )


# ─── Schema validation (brain foundation schemas) ───────────────────────


def _draft_validator(schema: dict):
    """Pick the right Draft validator based on the $schema declaration."""
    declared = schema.get("$schema", "")
    if "2020-12" in declared:
        return Draft202012Validator(schema)
    return Draft7Validator(schema)


def test_workflow_validates_against_brain_schema(workflow_doc):
    schema = _load_schema("workflow")
    validator = _draft_validator(schema)
    wf = workflow_doc["workflows"][0]
    errors = sorted(validator.iter_errors(wf), key=lambda e: e.path)
    assert not errors, "Workflow violates brain schema: " + "; ".join(
        f"{list(e.path)}: {e.message}" for e in errors
    )


def test_each_step_validates_against_brain_schema(steps_doc):
    schema = _load_schema("step")
    validator = _draft_validator(schema)
    bad = []
    for step in steps_doc["steps"]:
        errors = sorted(validator.iter_errors(step), key=lambda e: e.path)
        if errors:
            bad.append((step.get("name"), errors))
    assert not bad, "Steps violate brain schema: " + "; ".join(
        f"{name} → " + ", ".join(f"{list(e.path)}: {e.message}" for e in errs)
        for name, errs in bad
    )


def test_each_muc_has_a_failuremode(failuremodes_doc):
    """MUC-001..MUC-008 each map to exactly one FailureMode entity."""
    ids_present = {fm["id"] for fm in failuremodes_doc["failuremodes"]}
    missing = [
        muc for muc, ulid in FAILUREMODE_ULIDS.items() if ulid not in ids_present
    ]
    assert not missing, f"FailureModes missing for: {missing}"


def test_each_tool_passes_brain_schema(tools_doc):
    schema = _load_schema("tool")
    validator = _draft_validator(schema)
    bad = []
    # Only state=active Tools are full entities. _reused_from-only declarations
    # are descriptor rows (not full Tool entities) and are excluded from the
    # brain-schema validation pass.
    for tool in tools_doc["tools"]:
        if tool.get("state") != "active":
            continue
        errors = sorted(validator.iter_errors(tool), key=lambda e: e.path)
        if errors:
            bad.append((tool.get("name"), errors))
    assert not bad, "Tools violate brain schema: " + "; ".join(
        f"{name} → " + ", ".join(f"{list(e.path)}: {e.message}" for e in errs)
        for name, errs in bad
    )


def test_each_primary_tool_input_schema_lints():
    """Each of 10 sub-schemas (5 input + 5 output) is a valid JSON Schema document."""
    files_seen = 0
    for tool in PRIMARY_TOOL_NAMES:
        for axis in ("input", "output"):
            path = _TOOL_SCHEMA_DIR / f"{tool}-{axis}.schema.json"
            assert path.exists(), f"Missing schema: {path}"
            doc = json.loads(path.read_text())
            # Self-validate: the document must declare $schema and be a valid object schema.
            assert "$schema" in doc, f"{path} missing $schema declaration"
            assert doc.get("type") == "object", f"{path} must be an object schema"
            # Confirm draft-version validator can compile it (raises on malformed schema).
            _draft_validator(doc).check_schema(doc)
            files_seen += 1
    assert files_seen == 10, f"Expected 10 sub-schemas; saw {files_seen}"


# ─── Canonical-ULID pin (TDD §Canonical Identifiers byte-exact) ─────────


def test_workflow_ulid_matches_canonical(workflow_doc):
    """Workflow ULID is byte-identical to TDD §Canonical Identifiers."""
    assert workflow_doc["workflows"][0]["id"] == WORKFLOW_ULID


def test_step_ulids_match_canonical(steps_doc):
    """All 9 Step ULIDs match TDD §Canonical Identifiers byte-exact, in order."""
    actual = [s["id"] for s in steps_doc["steps"]]
    assert actual == STEP_ULIDS_IN_ORDER, (
        f"Step ULID drift.\n  Expected: {STEP_ULIDS_IN_ORDER}\n  Actual:   {actual}"
    )


def test_marketplace_tenant_ulid_matches_release_train():
    """The marketplace tenant ULID this WP uses is byte-identical to
    release-train/failuremodes.jsonld _about block (reused, never re-minted).
    """
    rt = json.loads((_RELEASE_TRAIN_DIR / "failuremodes.jsonld").read_text())
    assert rt["for_tenant"] == MARKETPLACE_TENANT_ULID, (
        "Marketplace tenant ULID drift between discover-project and release-train."
    )


# ─── Cross-WP refs resolve (graph integrity) ────────────────────────────


def test_step_tool_refs_resolve(steps_doc, tools_doc):
    """Every Step's ``tool_ref`` resolves to a Tool ID in tools.jsonld.

    Resolution covers two forms:
    - ``id`` on a full Tool entity (state=active), authored in this WP.
    - ``_forward_declaration_ulid`` on a ``_reused_from`` descriptor row,
      which reserves a canonical Tool ULID in this contract WP while
      deferring the full Tool entity authorship to a downstream WP (per
      Path A — the contract pre-canonicalises the ULIDs even when the
      implementation work splits across WPs).
    """
    full_entity_ids = {t["id"] for t in tools_doc["tools"] if "id" in t}
    forward_decl_ids = {
        t["_forward_declaration_ulid"]
        for t in tools_doc["tools"]
        if "_forward_declaration_ulid" in t
    }
    resolvable_ids = full_entity_ids | forward_decl_ids
    unresolved = []
    for step in steps_doc["steps"]:
        ref = step.get("tool_ref")
        if ref is None:
            continue  # mechanism=human Steps may omit tool_ref
        if ref not in resolvable_ids:
            unresolved.append((step["name"], ref))
    assert not unresolved, (
        f"Unresolved Step.tool_ref values: {unresolved}"
    )


def test_step_failuremode_refs_resolve(steps_doc, failuremodes_doc):
    """Every Step's ``handles_failures`` entry resolves to a FailureMode ID."""
    fm_ids = {fm["id"] for fm in failuremodes_doc["failuremodes"]}
    unresolved = []
    for step in steps_doc["steps"]:
        for ref in step.get("handles_failures", []) or []:
            if ref not in fm_ids:
                unresolved.append((step["name"], ref))
    assert not unresolved, (
        f"Unresolved Step.handles_failures references: {unresolved}"
    )


def test_tool_error_catalogue_refs_resolve(tools_doc, failuremodes_doc):
    """Every Tool's ``error_catalogue`` entry resolves to a FailureMode ID."""
    fm_ids = {fm["id"] for fm in failuremodes_doc["failuremodes"]}
    unresolved = []
    for tool in tools_doc["tools"]:
        if tool.get("state") != "active":
            continue
        for ref in tool.get("error_catalogue", []) or []:
            if ref not in fm_ids:
                unresolved.append((tool["name"], ref))
    assert not unresolved, (
        f"Unresolved Tool.error_catalogue references: {unresolved}"
    )


def test_failuremode_user_messages_match_misuse_cases_md(failuremodes_doc):
    """Every FailureMode's user-facing message matches MISUSE_CASES.md verbatim.

    The brain FailureMode schema's ``description`` field carries the
    user-facing system response string. We extract the *italicised* system-
    response text from each MUC-NNN section in MISUSE_CASES.md and assert
    byte-equality with the corresponding FailureMode entity's description
    field (one source of truth per WP-001 Blue gate).

    Behavioural-only MUCs (MUC-002 mid-flow-cancellation is the canonical
    example — its system response is a behavioural contract, not a surfaced
    string) carry no italicised quoted text in MISUSE_CASES.md. For those
    the test falls back to asserting the FailureMode description references
    the MUC by name (e.g., ``MUC-002``) — preserving the one-source-of-truth
    binding without requiring a non-existent verbatim string.
    """
    text = _MISUSE_CASES_PATH.read_text()
    # Each MUC section has one bold-italic "MUST fail fast with the exact error:"
    # or "MUST surface:" or "Exit with:" line whose italic content is the
    # verbatim system response. We capture every italicised quoted string in
    # each MUC-NNN section and assert at least one of them appears verbatim in
    # the corresponding FailureMode's description.
    sections = re.split(r"^## MUC-(\d+)", text, flags=re.MULTILINE)
    # split yields [pre, "001", body1, "002", body2, ...]
    muc_responses: dict[str, list[str]] = {}
    for i in range(1, len(sections), 2):
        muc_num = sections[i].zfill(3)
        body = sections[i + 1]
        # Capture italicised quoted strings: *"..."*
        responses = re.findall(r'\*"([^"]+)"\*', body)
        muc_responses[f"MUC-{muc_num}"] = responses

    name_by_id = {fm["id"]: fm.get("name") for fm in failuremodes_doc["failuremodes"]}
    desc_by_id = {fm["id"]: fm.get("description", "") for fm in failuremodes_doc["failuremodes"]}

    drift = []
    for muc, ulid in FAILUREMODE_ULIDS.items():
        expected_strings = muc_responses.get(muc, [])
        description = desc_by_id.get(ulid, "")
        if expected_strings:
            # MUC has at least one verbatim system-response string. At least one
            # of them MUST appear byte-exact in the FailureMode's description.
            if not any(s in description for s in expected_strings):
                drift.append(
                    f"{muc} ({name_by_id.get(ulid)}): none of "
                    f"{expected_strings!r} appears verbatim in description={description!r}"
                )
        else:
            # Behavioural-only MUC — no verbatim string to match. Fall back to
            # asserting the FailureMode description names the MUC explicitly.
            if muc not in description:
                drift.append(
                    f"{muc} ({name_by_id.get(ulid)}): MISUSE_CASES.md carries no "
                    f"italic system-response string; FailureMode description must "
                    f"reference {muc!r} by name but does not — description={description!r}"
                )
    assert not drift, "MISUSE_CASES.md ↔ failuremodes.jsonld drift:\n  " + "\n  ".join(drift)
