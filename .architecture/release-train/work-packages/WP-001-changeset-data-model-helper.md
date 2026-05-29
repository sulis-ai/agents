---
# Identity (WP-01)
id: WP-001
title: "Changeset data model + helper (_changeset.py) + the YAML contract"
kind: backend
source: feature
parent_phase: release-train
change_id: 01KSQNPBPN7W74QVAZ25F79RNH

# Scope (WP-02..04)
atomic_branch: yes
estimate: medium
blast_radius: low                       # new leaf module + new docs; nothing depends on it yet

# Change primitive
primitive: create
group: expand

acceptance_criteria:
  - "plugins/sulis/scripts/_changeset.py exists and is import-safe (no side effects on import)"
  - ".changesets/README.md documents the YAML contract: change_id, primitive, tier, touches_plugin, summary, created_at + the triple-key filename"
  - "tier_for_primitive maps every fix/chore/refactor/docs→patch; feat/create/extend/compose/reuse/strangle/wrap/harden/instrument→minor; breaking→major; admin/docs-only→None"
  - "cumulative_tier returns the SemVer max; [] → None"
  - "next_version bumps correctly for patch/minor/major on BOTH the 0.x.y plugin series and the 1.x.y marketplace series; tier=None → unchanged"
  - "the triple-key filename builder is collision-proof (same primitive+slug at different datetimeZ → distinct paths)"
  - "write_changeset / read_changesets round-trip with field fidelity; read_changesets ignores non-.yaml files"
  - "every public function in _changeset.py has a unit test in plugins/sulis/scripts/tests/unit/test_changeset.py"
  - "full suite green (existing + new tests)"

test_plan:
  unit:
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_tier_for_primitive_full_mapping"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_tier_for_primitive_breaking_overrides_to_major"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_tier_for_primitive_admin_docs_only_is_none"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_cumulative_tier_max_precedence"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_cumulative_tier_empty_is_none"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_next_version_plugin_series"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_next_version_marketplace_series"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_next_version_none_tier_unchanged"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_changeset_filename_triple_key_collision_proof"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_changeset_filename_sanitises_slug"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_write_read_changeset_round_trip"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_read_changesets_ignores_non_yaml"
    - "plugins/sulis/scripts/tests/unit/test_changeset.py::test_readme_examples_parse"
  integration: []
  verification:
    - "branch-ci workflow green on the WP branch"
verification_gates: [unit]              # pure module — no API boundary, no integration

# Lineage (WP-06)
derived_from:
  - finding: spec::.changes/release-train.SPEC.md::WP-1 (keystone)
    found_in: .changes/release-train.SPEC.md
    severity_at_discovery: n/a
generated_by:
  activity: draft-architecture/release-train
  agent: sulis-engineering-architect
addresses_findings:
  - "issue-66::ship-flow-does-not-mandate-version-bump (root: deterministic core)"
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
status: pending
depends_on: []                          # KEYSTONE — nothing precedes it
blocks: [WP-008]                        # WP-008 remediates the merged keystone; the writer/authority/skill now build on WP-008's finalised contract

# Composite (WP-08)
child_wps: []
kinds: null

rollback: |
  Delete plugins/sulis/scripts/_changeset.py, its test file, and .changesets/README.md.
  Nothing imports the module yet (it is the keystone; producers/consumers land after),
  so removal is clean — pure new-file revert.
---

# WP-001 — Changeset data model + helper (TDD KEYSTONE)

## Context

TDD §Form (the changeset YAML seam) + §Proof (the deterministic core).
ADR-002 (tier from primitive), ADR-003 (`next_version` dual-series), ADR-005
(the contract lands first). This is the keystone: WP-002 (writer), WP-003 (GHA
reader), and WP-004 (skill reader) all depend on it. It lands first per
CONTRACT_FIRST.

The module lives at `plugins/sulis/scripts/_changeset.py`, **alongside
`_wpxlib.py`** (the established home for sulis scripts). Tests live at
`plugins/sulis/scripts/tests/unit/test_changeset.py` and import the module
directly (`import _changeset`) — the root `conftest.py` already adds
`scripts/` to `sys.path` and isolates `SULIS_STATE_DIR`. Match the style of
`tests/unit/test_change_store.py`.

## Contract — the public surface of `_changeset.py`

```python
Tier = Literal["patch", "minor", "major"]

def tier_for_primitive(primitive: str, *, breaking: bool = False) -> Tier | None:
    """Deterministic tier from the change primitive (ADR-002).
    breaking=True → "major" regardless of primitive.
    admin / docs-only (or any primitive whose change does not touch
    plugins/sulis/**) → None (caller writes NO changeset)."""

def cumulative_tier(changesets: list[dict]) -> Tier | None:
    """SemVer max over a batch's tiers (major > minor > patch).
    Empty list → None ("nothing to release")."""

def next_version(current: str, tier: Tier | None) -> str:
    """Apply tier to a dotted SemVer string. Series-agnostic — works for
    both 0.77.0 (plugin) and 1.122.0 (marketplace). tier=None → current
    unchanged. patch: x.y.(z+1); minor: x.(y+1).0; major: (x+1).0.0."""

def changeset_filename(primitive: str, slug: str, created_at: datetime) -> str:
    """Triple-key, collision-proof: {primitive}-{slug}-{datetimeZ}.yaml,
    datetimeZ = compact UTC ISO-8601 (e.g. 20260528T173000Z). Slug is
    sanitised (lowercased, non-alnum → '-', collapsed)."""

def write_changeset(
    changesets_dir: Path, *, change_id: str, primitive: str, tier: Tier,
    touches_plugin: bool, summary: str, created_at: datetime | None = None,
) -> Path:
    """Write one changeset YAML; returns the path written. Creates
    changesets_dir if absent."""

def read_changesets(changesets_dir: Path) -> list[dict]:
    """Read every *.yaml in the dir into dicts. Ignores non-.yaml files.
    Missing dir → []."""
```

The contract document `.changesets/README.md` records the same shape in prose +
a worked example + the lifecycle (write on ship → accumulate on dev → GHA
consumes on merge to main), mirroring honest-claude's `.changesets/README.md`.
The README's worked-example YAML is parsed by `read_changesets` in
`test_readme_examples_parse` so the doc and the code cannot drift (ADR-005).

## Definition of Done — Red / Green / Blue

### Red (write the failing tests first — MUST)

Write `test_changeset.py` with the 13 named tests above **before** any
implementation. Run them; confirm they fail (ImportError / NameError). Key
assertions:

- `test_tier_for_primitive_full_mapping` — table-driven: assert `patch` for
  `{fix, chore, refactor, docs}`, `minor` for `{feat, create, extend, compose,
  reuse, strangle, wrap, harden, instrument}`.
- `test_tier_for_primitive_breaking_overrides_to_major` — any primitive +
  `breaking=True` → `"major"`.
- `test_tier_for_primitive_admin_docs_only_is_none` — `admin` / `docs-only` (or
  unknown) → `None`.
- `test_cumulative_tier_max_precedence` — `[{tier:"patch"},{tier:"minor"}]` →
  `"minor"`; `[patch,patch,major]` → `"major"`.
- `test_cumulative_tier_empty_is_none` — `[]` → `None`.
- `test_next_version_plugin_series` — `("0.77.0","patch")→"0.77.1"`,
  `("0.77.0","minor")→"0.78.0"`, `("0.77.0","major")→"1.0.0"`.
- `test_next_version_marketplace_series` — `("1.122.0","minor")→"1.123.0"`,
  `("1.122.0","patch")→"1.122.1"`, `("1.122.0","major")→"2.0.0"`.
- `test_next_version_none_tier_unchanged` — `("1.122.0",None)→"1.122.0"`.
- `test_changeset_filename_triple_key_collision_proof` — same `(primitive,slug)`
  at two distinct `created_at` → two distinct filenames.
- `test_changeset_filename_sanitises_slug` — a slug with spaces/caps/punctuation
  → a clean kebab filename component.
- `test_write_read_changeset_round_trip` — write 2 changesets into `tmp_path`,
  `read_changesets` returns 2 dicts with the written fields intact.
- `test_read_changesets_ignores_non_yaml` — drop a `.txt` and a `.md` in the dir
  → not returned; missing dir → `[]`.
- `test_readme_examples_parse` — extract the YAML block from `.changesets/
  README.md` and assert `read_changesets` (or the same YAML loader) parses it
  with the contract fields present.

### Green (minimum boring code to pass)

Implement `_changeset.py` per the contract. Use the stdlib + the same YAML
approach the rest of `scripts/` uses (check `_wpxlib.py` for the project's YAML
dependency; prefer it over inventing a new one — EP-03). No reflection, no
dynamic dispatch by string beyond the explicit tier-mapping dict. The mapping is
a literal dict; `cumulative_tier` is a `max` over an ordered enum; `next_version`
is integer arithmetic on the split parts. Author `.changesets/README.md` with the
contract + worked example + lifecycle. All 13 tests green.

### Blue (refactor — MUST, not optional)

- Extract the tier ordering (`patch < minor < major`) into one constant used by
  both `tier_for_primitive` and `cumulative_tier` — single source of truth.
- If the primitive→tier mapping overlaps with the 22-primitive vocabulary in
  `references/change-primitives.md`, reference that vocabulary in a comment so
  the mapping's completeness is auditable against the canonical list (don't
  duplicate the list; cite it).
- Confirm no second copy of SemVer bump logic already exists in `_wpxlib.py`; if
  one does, extract the shared primitive now (EP-03 second-caller rule). If not,
  leave a comment noting the GHA (WP-003) will mirror this logic in bash per
  ADR-004.
- Re-run the full suite; confirm green.

## Estimated token cost

input: ~10k / output: ~7k

## Notes

- **Pure module — no mocks.** Tests use `tmp_path` for file I/O, exactly like
  `test_change_store.py`. No network, no `gh`, no subprocess.
- **`next_version` is series-agnostic** so the same function serves both the
  `0.x.y` plugin series and the `1.x.y` marketplace series (ADR-003); the GHA
  applies it three times.
- This is the only WP whose tests cover *every function* — it is the
  deterministic core the whole train rests on.
