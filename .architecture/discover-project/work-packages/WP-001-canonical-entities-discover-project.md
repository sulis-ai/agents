---
id: WP-001
title: Author canonical entities + Tool schemas at plugins/sulis/instances/discover-project/
status: pending
kind: contract
primitive: create
group: GENERATE
change_id: CH-01KT1W
sequence_id: WP-001
dependsOn: []
blocks: [WP-002, WP-003, WP-004, WP-006, WP-007, WP-009]
estimated_token_cost:
  input: 6k
  output: 8k
tdd_section: Form #1-6; Canonical Identifiers
adrs: [ADR-001, ADR-002, ADR-003, ADR-004, ADR-005, ADR-006]
---

## Context

Authors the five canonical JSON-LD entity instances + 10 Tool JSON
Schemas at `plugins/sulis/instances/discover-project/`. Per ADR-001,
these are the **specification of truth** for the discover-project
Workflow — the skill prose (WP-008) and the drift detector (WP-007,
WP-009) both bind to them. The Path A pattern from
`release-train-as-entities` applies unchanged.

This WP is the head of the dependency graph: every other WP in the set
either reads from these files (WP-008 conforms to them; WP-009 parses
annotations against them) or writes Python that resolves identifiers
pre-canonicalised here (WP-002, WP-003, WP-004, WP-006, WP-007).

**Pre-canonicalised identifiers (P8 rubric MUST):** every ULID this WP
mints — Workflow, Steps, Triggers, FailureModes, Tools — is pinned in
TDD.md §Canonical Identifiers. This WP transcribes those values
verbatim into the JSON-LD; it does not invent new ones.

## Contract

### Files created

```
plugins/sulis/instances/discover-project/
├── workflow.jsonld
├── steps.jsonld
├── triggers.jsonld
├── failuremodes.jsonld
├── tools.jsonld
└── schemas/tools/
    ├── git-remote-read-input.schema.json
    ├── git-remote-read-output.schema.json
    ├── read-package-json-input.schema.json
    ├── read-package-json-output.schema.json
    ├── read-pyproject-toml-input.schema.json
    ├── read-pyproject-toml-output.schema.json
    ├── read-ci-workflows-input.schema.json
    ├── read-ci-workflows-output.schema.json
    ├── derive-consumer-tenant-input.schema.json
    ├── derive-consumer-tenant-output.schema.json
    ├── infer-configuration-values-input.schema.json
    └── infer-configuration-values-output.schema.json
```

15 files: 5 JSON-LD entity instances + 10 Tool JSON Schemas (5 input +
5 output for the 5 new typed Tools listed in TDD.md §Canonical
Identifiers — Tool ULIDs).

### Canonical-source bindings

Every ULID in this WP is sourced from TDD.md §Canonical Identifiers:

| Entity | Source anchor | Value |
|---|---|---|
| `discover-project` Workflow | TDD §Canonical Identifiers — Workflow ULID | `dna:workflow:01KT1WDSCVRWFW00000000000A` |
| Marketplace tenant | TDD §Canonical Identifiers — Tenant ULIDs | `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM` (reused; no new mint) |
| 9 Step ULIDs | TDD §Canonical Identifiers — Step ULIDs | `dna:step:01KT1WDSST01RDREPOROOT00A` ... `dna:step:01KT1WDSST09RUNDRIFTDET` |
| 1 Trigger ULID | TDD §Canonical Identifiers — Trigger ULIDs | `dna:trigger:01KT1WDSTRG1MANUAL00000A` |
| 8 FailureMode ULIDs | TDD §Canonical Identifiers — FailureMode ULIDs | `dna:failuremode:01KT1WFM01NONGITDIR0000A` ... `dna:failuremode:01KT1WFM08TKBDGTEXCEED` |
| 6 Tool ULIDs | TDD §Canonical Identifiers — Tool ULIDs | `dna:tool:01KT1WTL01GITREMOTEREAD` ... `dna:tool:01KT1WTL06INFERCONFIG0` |

# canonical-source: TDD.md §Canonical Identifiers

### Workflow entity shape

```jsonld
{
  "id": "dna:workflow:01KT1WDSCVRWFW00000000000A",
  "name": "discover-project",
  "for_domain": "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM",
  "kind": "deterministic-with-probabilistic-phase",
  "phases": [
    {"name": "Detect", "mechanism": "deterministic", "steps": ["read-repo-root", "read-package-manifests", "read-ci-workflows", "read-repo-contract"]},
    {"name": "Infer", "mechanism": "probabilistic", "steps": ["propose-configuration-values"]},
    {"name": "Ask", "mechanism": "human", "steps": ["confirm-or-override-inferences", "gather-ambiguous-fields"]},
    {"name": "Mint", "mechanism": "deterministic", "steps": ["write-project-entity"]},
    {"name": "Verify", "mechanism": "deterministic", "steps": ["run-drift-detector-on-mint"]}
  ],
  "triggers": ["dna:trigger:01KT1WDSTRG1MANUAL00000A"],
  "failuremodes": [
    "dna:failuremode:01KT1WFM01NONGITDIR0000A",
    "dna:failuremode:01KT1WFM02CANCELMIDFLOW",
    "dna:failuremode:01KT1WFM03ENTITYEXISTS0",
    "dna:failuremode:01KT1WFM04INFERREJECTED",
    "dna:failuremode:01KT1WFM05UNKNOWNWFULID",
    "dna:failuremode:01KT1WFM06GITNOREMOTE0",
    "dna:failuremode:01KT1WFM07MONOREPOCOLL",
    "dna:failuremode:01KT1WFM08TKBDGTEXCEED"
  ],
  "version": "1.0.0",
  "state": "active",
  "sys_status": "active",
  "valid_from": "2026-06-01T00:00:00Z"
}
```

### Steps shape (one entry — repeat the shape for all 9 Steps)

```jsonld
{
  "id": "dna:step:01KT1WDSST01RDREPOROOT00A",
  "name": "read-repo-root",
  "for_workflow": "dna:workflow:01KT1WDSCVRWFW00000000000A",
  "phase": "Detect",
  "mechanism": "deterministic",
  "tool_ref": "dna:tool:01KT1WTL01GITREMOTEREAD",
  "preconditions": ["consuming repo is the cwd"],
  "postconditions": ["{is_git, has_remote, remote_url, primary_branch} structured result available to downstream Steps"],
  "failuremode_refs": ["dna:failuremode:01KT1WFM01NONGITDIR0000A", "dna:failuremode:01KT1WFM06GITNOREMOTE0"],
  "agent_instructions": "Invoke git-remote-read Tool against the current working directory. On non-git directory → raise non-git-directory FailureMode (MUC-001). On .git/ but no remote → raise git-no-remote FailureMode (MUC-006)."
}
```

The 9 Steps in order: `read-repo-root`, `read-package-manifests`,
`read-ci-workflows`, `read-repo-contract`, `propose-configuration-values`,
`confirm-or-override-inferences`, `gather-ambiguous-fields`,
`write-project-entity`, `run-drift-detector-on-mint`.

### Triggers shape (1 entry)

```jsonld
{
  "id": "dna:trigger:01KT1WDSTRG1MANUAL00000A",
  "name": "manual-discover-project-invocation",
  "for_workflow": "dna:workflow:01KT1WDSCVRWFW00000000000A",
  "kind": "manual",
  "fires_when": "Operator runs `/sulis:discover-project` (with optional --update, --path, --source-repo flags)"
}
```

Per ADR-004: v1 ships ONLY this Trigger. The auto-suggest Trigger is
deferred to v2.

### FailureModes shape (one entry — repeat for all 8)

```jsonld
{
  "id": "dna:failuremode:01KT1WFM01NONGITDIR0000A",
  "name": "non-git-directory",
  "for_workflow": "dna:workflow:01KT1WDSCVRWFW00000000000A",
  "for_muc": "MUC-001",
  "raised_in_step": "dna:step:01KT1WDSST01RDREPOROOT00A",
  "detection": "git rev-parse --show-toplevel exits non-zero",
  "recovery_strategy": "fail-fast-with-clear-error",
  "user_message": "This directory is not a git repository. discover-project requires a git remote to mint a Project. Run `git init` and add a remote first, or specify `--source-repo <org/name>` explicitly."
}
```

All 8 FailureModes follow this shape with the per-MUC system response
text from MISUSE_CASES.md verbatim in `user_message`.

### Tools shape (one entry — repeat for all 5 new typed Tools)

```jsonld
{
  "id": "dna:tool:01KT1WTL01GITREMOTEREAD",
  "name": "git-remote-read",
  "for_domain": "dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM",
  "kind": "query",
  "inputs_schema_ref": "schemas/tools/git-remote-read-input.schema.json",
  "outputs_schema_ref": "schemas/tools/git-remote-read-output.schema.json",
  "error_catalogue": [
    "dna:failuremode:01KT1WFM01NONGITDIR0000A",
    "dna:failuremode:01KT1WFM06GITNOREMOTE0"
  ],
  "implementation_kind": "subprocess",
  "implementation_detail": "{\"command\":\"git\",\"args\":[\"remote\",\"get-url\",\"origin\"],\"timeout_s\":5}",
  "version": "1.0.0",
  "state": "active",
  "sys_status": "active",
  "valid_from": "2026-06-01T00:00:00Z"
}
```

For reused Tools (`entity-emitter`, `drift-detector`), `tools.jsonld`
declares `_reused_from` pointing at the source instance file rather
than minting new ULIDs (per TDD.md §Canonical Identifiers — Tool ULIDs
reuse block).

### Tool JSON Schemas — primary 5, full populated per WP-006 precedent

Each schema describes the Tool's load-bearing fields only (per
release-train WP-006's "schemas are minimal" Blue gate):

- `git-remote-read-input.schema.json` — `{cwd: string}`
- `git-remote-read-output.schema.json` — `{is_git: bool, has_remote: bool, remote_url: string|null, primary_branch: string|null, repo_root: string|null}`
- `read-package-json-input.schema.json` — `{path: string}`
- `read-package-json-output.schema.json` — `{name: string|null, version: string|null, private: bool|null, scripts_keys: string[]}`
- `read-pyproject-toml-input.schema.json` — `{path: string}`
- `read-pyproject-toml-output.schema.json` — `{name: string|null, version: string|null, dependencies_count: integer}`
- `read-ci-workflows-input.schema.json` — `{repo_root: string}`
- `read-ci-workflows-output.schema.json` — `{workflows: [{path: string, name: string|null, triggers: string[]}]}`
- `derive-consumer-tenant-input.schema.json` — `{repo_org_slash_name: string}`
- `derive-consumer-tenant-output.schema.json` — `{tenant_ulid: string}` (with `pattern: "^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$"`)
- `infer-configuration-values-input.schema.json` — `{detection_result: object, token_budget: integer}`
- `infer-configuration-values-output.schema.json` — `{inferences: {<field>: {value: string, confidence: number}}, tokens_consumed: integer}`

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_workflow_jsonld_parses` — JSON parse round-trip
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_workflow_validates_against_brain_schema` — validates against `plugins/sulis/brain/compiled/foundation/workflow.schema.json`
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_workflow_ulid_matches_canonical` — `dna:workflow:01KT1WDSCVRWFW00000000000A` byte-exact
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_steps_count_is_9` — exactly 9 Step entities
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_each_step_validates_against_brain_schema`
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_step_ulids_match_canonical` — all 9 ULIDs from TDD §Canonical Identifiers byte-exact
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_step_tool_refs_resolve` — every `tool_ref` resolves to a Tool ID in `tools.jsonld`
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_step_failuremode_refs_resolve` — every `failuremode_refs` entry resolves to a FailureMode ID
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_triggers_count_is_1` — only `manual-discover-project-invocation` (per ADR-004)
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_failuremodes_count_is_8`
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_each_muc_has_a_failuremode` — MUC-001..MUC-008 each map to one FailureMode
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_failuremode_user_messages_match_misuse_cases_md` — verbatim equality with MISUSE_CASES.md system response strings
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_tools_count_is_5_new` — 5 new typed Tools authored (reused Tools are declared by reference)
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_each_tool_passes_brain_schema`
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_each_primary_tool_input_schema_lints` — each of 5 input + 5 output schemas is valid JSON Schema (draft-07)
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_tool_error_catalogue_refs_resolve` — every Tool's `error_catalogue` entry resolves to a FailureMode ID
- [ ] `tests/unit/test_discover_project_canonical_entities.py::test_marketplace_tenant_ulid_matches_release_train` — the marketplace tenant ULID this WP uses is byte-identical to `release-train/failuremodes.jsonld` `_about`

### Green — Implementation makes tests pass

- [ ] `plugins/sulis/instances/discover-project/workflow.jsonld` authored per Contract
- [ ] `plugins/sulis/instances/discover-project/steps.jsonld` authored — 9 Step entries
- [ ] `plugins/sulis/instances/discover-project/triggers.jsonld` authored — 1 Trigger entry
- [ ] `plugins/sulis/instances/discover-project/failuremodes.jsonld` authored — 8 FailureMode entries, `user_message` strings copied verbatim from MISUSE_CASES.md
- [ ] `plugins/sulis/instances/discover-project/tools.jsonld` authored — 5 new typed Tools + 2 `_reused_from` declarations for `entity-emitter` and `drift-detector`
- [ ] 10 JSON Schema files at `plugins/sulis/instances/discover-project/schemas/tools/<tool>-{input,output}.schema.json`
- [ ] All ULIDs match TDD.md §Canonical Identifiers byte-exact (no inline minting; no drift)

### Blue — Refactor complete

- [ ] Schemas describe load-bearing fields only — no over-specification
- [ ] Per-FailureMode `user_message` text matches MISUSE_CASES.md verbatim (one source of truth)
- [ ] Tool `implementation_detail` JSON shapes are consistent across Tools of the same `implementation_kind`
- [ ] Each entity carries `_about` text describing what it is and why (founder-readable, no internal taxonomy)

## Sequence

- **dependsOn:** — (head of graph)
- **blocks:** WP-002 (reads tenant Tool spec), WP-003 (reads RepoInspector Tool specs), WP-004 (reads ConfigurationInferrer Tool spec), WP-006 (reads Step write-project-entity spec), WP-007 (reads Step run-drift-detector spec), WP-009 (parses canonical annotations from steps.jsonld + failuremodes.jsonld)
- **Parallelisable with:** WP-005 (Ask prose has no code deps — it can be drafted at t=0 in parallel)

## Estimated Token Cost

- **Input:** ~6k (TDD §Canonical Identifiers + foundation v0.6.0 schemas + MISUSE_CASES.md + release-train tools.jsonld for the marketplace-tenant cross-check)
- **Output:** ~8k (5 JSON-LD files ≈ 5k + 10 JSON Schemas ≈ 3k)
- **Total:** ~14k

## Notes

- The 17 LOC-estimate items in TDD.md §Form (component inventory rows 1-6) collapse into one atomic WP because they share a single directory + are mutually-validating (Steps reference Tools; Tools reference FailureModes; nothing parses without the full set). Splitting would produce 5 WPs that each only build a partial graph.
- Per Path A (ADR-001), this WP is the contract — every downstream WP reads it. The drift detector (WP-007 invocation + WP-009 extension) is the gate that catches any divergence.
- Marketplace-tenant ULID is reused, not minted. The cross-check test `test_marketplace_tenant_ulid_matches_release_train` enforces this.
- Touch surface is 15 files (1 dir + 5 JSON-LD + schemas/tools/ dir + 10 schemas). Within MUST ≤ 15 ceiling; just over the SHOULD ≤ 8 — rationale in DECOMPOSE_VALIDATION.md: the contract is atomic (one mutually-validating graph) per Path A discipline.
