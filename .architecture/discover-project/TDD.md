# TDD — Discover Project (mint a consumer-owned Project entity)

**Source SPEC:** `../../.specifications/discover-project/SRD.md`
**Tier:** L (per `SIZING.md`)
**Execution path:** Path A — canonical-as-spec, imperative-as-implementation, drift-detector as bridge
**Structural template:** `../../.architecture/release-train-as-entities/` (identical Path A pattern)
**Depends on:** CH-01KSZ4 release-train-as-entities (canonical pattern + drift detector + foundation schemas vendored)

## Overview

Two deliverables compose this design:

1. **Canonical entity instances** at `plugins/sulis/instances/discover-project/` — five JSON-LD files (workflow, steps, triggers, failuremodes, tools) plus tool schemas. These are the specification of truth for what discovery does. *No `projects.jsonld` here — discovery produces Project entities; it does not own a Project entity itself.*
2. **Skill imperative** at `plugins/sulis/skills/discover-project/SKILL.md` — the operator-runnable prose that conforms to the canonical Workflow. Drift detector enforces conformance at PR time.

No new runtime, no new executor port. The entity-emitter Tool (already validated) does the JSON-LD write; the drift detector from `release-train-as-entities` validates the new Workflow + skill; the foundation v0.6.0 Project schema is the entity contract.

This is the **n=2 dogfood of Path A**. The same drift discipline that catches `release-train` skill/canonical divergence catches `discover-project` skill/canonical divergence — proving Path A holds beyond the first encoded Workflow.

## Source specification

Driven by `SRD.md` (sibling). Functional coverage: FR-001..012 in full. All 6 NFRs covered. All 8 MUCs encoded as FailureModes. The five Open Questions are resolved in ADRs (ADR-002..006 below).

---

## Canonical Identifiers (P8 rubric, pre-canonicalised)

Per the cross-WP identifier canonicalisation rubric (`f59fc36 extend: canonicalise-cross-wp-ids`, decompose Phase 8), every ULID and identifier that crosses WP boundaries is pinned here as the authoritative source. Each WP Contract references this section rather than re-minting.

### Workflow ULID (this change)

| Identifier | Value | Derivation / Rationale |
|---|---|---|
| `discover-project` Workflow | `dna:workflow:01KT1WDSCVRWFW00000000000A` | Mnemonic-stamped Crockford-base32. `01KT1W` = the change-prefix shared by every CH-01KT1W canonical entity (matches release-train's `01KT0R` convention). `DSCVRWFW` reads as "discover workflow" in the human-scan sense. Trailing zeros + `A` per ULID character set (no I/L/O/U; final A is a permitted character in Crockford). Locked in WP-001 and referenced from every Step's `for_workflow`. |

### Tenant ULIDs

| Identifier | Value | Notes |
|---|---|---|
| Marketplace tenant | `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM` | Identical to release-train. Sourced from `plugins/sulis/instances/release-train/failuremodes.jsonld` `_about` (derivation: `SHA256("tenant-name:sulis-plugins-marketplace")` → Crockford base32). **No minting in this change.** The canonical discover-project Workflow itself binds to the marketplace tenant because the Workflow definition is marketplace-owned. |
| Consumer tenant | Derived per ADR-002 | Each consuming repo gets its own deterministically-derived tenant ULID. Cross-tenant boundary at the Project entity is by design — the consumer's Project carries `belongs_to_tenant: <consumer-tenant>` while `release_workflow_ref` crosses to the marketplace tenant's release-train Workflow. |

### Consumer-tenant derivation recipe (canonical, locked in ADR-002)

```
input  = "tenant-name:" + <repo-org> + "/" + <repo-name>
         where <repo-org>/<repo-name> is the GitHub-shorthand form of source.repo
         (e.g., "acme/payments-app")

digest = SHA256(input)                       # 256 bits

# ULID format: 26 Crockford base32 chars = 130 bits
# ULID character set: 0123456789ABCDEFGHJKMNPQRSTVWXYZ (no I L O U)

bits   = digest[:130]                        # first 130 bits, most-significant
ulid26 = crockford_base32_encode(bits, 26)   # 26-char string

# ULID first-char-clamp per ULID spec — first char encodes top 3 bits;
# only 0..7 are valid (5 bits would overflow the 48-bit timestamp prefix).
# Clamp via: if first_char > '7', subtract 8 from its numeric value.
ulid_final = clamp_first_char_to_0_through_7(ulid26)
```

Worked example (test fixture): `tenant-name:acme/payments-app` → fixed ULID, identical across every discovery run for that repo. The derivation is deterministic, collision-resistant (SHA256), and publicly verifiable (anyone with the repo URL computes the same value).

The recipe is encoded as test-fixture pairs in WP-002 so any future regenerate produces byte-identical ULIDs.

### Step ULIDs (this change — 9 Steps across 5 phases)

Pre-canonicalised here so every WP Contract can reference. Mnemonic-stamped with prefix `01KT1WDS` (shared change prefix + DiScovery):

| # | Phase | Step name | Step ULID |
|---|---|---|---|
| 1 | Detect | `read-repo-root` | `dna:step:01KT1WDSST01RDREP0R00T000A` |
| 2 | Detect | `read-package-manifests` | `dna:step:01KT1WDSST02RDPKGMAN1FEST0` |
| 3 | Detect | `read-ci-workflows` | `dna:step:01KT1WDSST03RDC1W0RKF10W00` |
| 4 | Detect | `read-repo-contract` | `dna:step:01KT1WDSST04RDREP0C0NTR00A` |
| 5 | Infer | `propose-configuration-values` | `dna:step:01KT1WDSST05PR0P0SEC0NFG00` |
| 6 | Ask | `confirm-or-override-inferences` | `dna:step:01KT1WDSST06C0NF1RM0VRD000` |
| 7 | Ask | `gather-ambiguous-fields` | `dna:step:01KT1WDSST07GATHERAMBF1000` |
| 8 | Mint | `write-project-entity` | `dna:step:01KT1WDSST08WR1TEPR0JEC000` |
| 9 | Verify | `run-drift-detector-on-mint` | `dna:step:01KT1WDSST09RVNDR1FTDET000` |

### Trigger ULIDs

| Trigger name | ULID | Kind |
|---|---|---|
| `manual-discover-project-invocation` | `dna:trigger:01KT1WDSTRG1MANVA10000000A` | manual (founder runs `/sulis:discover-project`) |

(The `auto-suggest-on-missing-entity` Trigger is deferred to v2 per ADR-004. No second Trigger ULID is minted in v1.)

### FailureMode ULIDs (8 — one per MUC)

| MUC | FailureMode name | ULID |
|---|---|---|
| MUC-001 | `non-git-directory` | `dna:failuremode:01KT1WFM01N0NG1TD1R000000A` |
| MUC-002 | `mid-flow-cancellation` | `dna:failuremode:01KT1WFM02CANCE1M1DF10W000` |
| MUC-003 | `entity-already-exists` | `dna:failuremode:01KT1WFM03ENT1TYEX1STS0000` |
| MUC-004 | `inferred-value-rejected` | `dna:failuremode:01KT1WFM041NFERREJECTED000` |
| MUC-005 | `unknown-workflow-ulid` | `dna:failuremode:01KT1WFM05VNKN0WNWFV11D000` |
| MUC-006 | `git-no-remote` | `dna:failuremode:01KT1WFM06G1TN0REM0TE00000` |
| MUC-007 | `monorepo-sibling-collision` | `dna:failuremode:01KT1WFM07M0N0REP0C0110000` |
| MUC-008 | `token-budget-exceeded` | `dna:failuremode:01KT1WFM08TKBDGTEXCEED0000` |

### Tool ULIDs (5 new + 2 reused)

Reused (no new ULID minted):

| Tool | Source ULID | Reuse contract |
|---|---|---|
| `entity-emitter` | (existing in codebase per feedback-log task #58) | Writes JSON-LD entity files conforming to the foundation Project schema. The load-bearing reuse. |
| `drift-detector` | (existing per `7d666df`) | Invoked from the Verify phase scoped to the just-minted entity. |

New (minted in this change):

| Tool name | ULID | Kind |
|---|---|---|
| `git-remote-read` | `dna:tool:01KT1WT101G1TREM0TEREAD000` | query (reads `git remote get-url origin`, branch, repo root) |
| `read-package-json` | `dna:tool:01KT1WT102RDPKGJS0N000000A` | query (parses `package.json` to a typed shape) |
| `read-pyproject-toml` | `dna:tool:01KT1WT103RDPYPR0JT0M10000` | query (parses `pyproject.toml`) |
| `read-ci-workflows` | `dna:tool:01KT1WT104RDC1WF000000000A` | query (enumerates `.github/workflows/*.yml`, `.gitlab-ci.yml`) |
| `derive-consumer-tenant` | `dna:tool:01KT1WT105DER1VETENANT0000` | query (the SHA256 → Crockford-base32 recipe; deterministic) |
| `infer-configuration-values` | `dna:tool:01KT1WT1061NFERC0NF1G00000` | side-effect (LLM call; the only probabilistic Tool in this change) |

The "Read repo contract" Step reuses the harness `Read` primitive — no new typed Tool unless a downstream WP determines a schema is required.

### Canonical-Identifiers Pre-canonicalisation Manifest

For Phase 8 of the decompose rubric, the WP set will reference these identifiers from this section by anchor (e.g., `# canonical-source: TDD.md§Canonical Identifiers — Step 5 ULID`). No WP invents a ULID inline.

---

## Form — Structural Design

### Component inventory

| # | Component | Lives at | Kind | LOC estimate |
|---|---|---|---|---|
| 1 | Canonical workflow instance | `plugins/sulis/instances/discover-project/workflow.jsonld` | JSON-LD entity | ~80 |
| 2 | Canonical steps instance | `plugins/sulis/instances/discover-project/steps.jsonld` | JSON-LD entity (9 Steps) | ~280 |
| 3 | Canonical triggers instance | `plugins/sulis/instances/discover-project/triggers.jsonld` | JSON-LD entity (1 Trigger) | ~20 |
| 4 | Canonical failuremodes instance | `plugins/sulis/instances/discover-project/failuremodes.jsonld` | JSON-LD entity (8 FailureModes) | ~140 |
| 5 | Canonical tools instance | `plugins/sulis/instances/discover-project/tools.jsonld` | JSON-LD entity (5 new + 2 reused-by-reference) | ~180 |
| 6 | Tool schemas (new) | `plugins/sulis/instances/discover-project/schemas/tools/*.schema.json` | JSON Schema (5 input + 5 output) | ~150 |
| 7 | Skill prose | `plugins/sulis/skills/discover-project/SKILL.md` | Markdown (front matter + 5 phase sections + safety + tests-this-skill-passes) | ~250 |
| 8 | Python helpers | `plugins/sulis/scripts/_discovery/{detect.py, infer.py, mint.py, verify.py, tenant.py, slug.py}` | Python module (deterministic logic for Detect/Mint/Verify; tenant derivation; slug derivation) | ~350 |
| 9 | Tests (unit + integration) | `plugins/sulis/scripts/tests/unit/test_discovery_*.py` + `tests/integration/test_discover_e2e.py` | Pytest | ~400 |
| 10 | Test fixtures (4 consumer repos) | `tests/fixtures/discover-project/{empty,populated,monorepo,pre-existing}/` | Fixture repos (synthetic .git/, manifests, CI) | ~100 |
| 11 | Drift detector parity test | `plugins/sulis/scripts/tests/unit/test_check_canonical_drift_discover.py` | Pytest | ~60 |

**Total new code/content:** ~2,000 lines (mostly tests + fixtures + JSON-LD entity data).

### Module boundaries + dependency graph

```
                  [SOURCE OF TRUTH]
                          │
            ┌─────────────┴────────────────────┐
            │                                  │
            ▼                                  ▼
plugins/sulis/instances/discover-project/   (read by)
  ├── workflow.jsonld                        │
  ├── steps.jsonld                           │
  ├── triggers.jsonld                        ├──► check-canonical-drift.py
  ├── failuremodes.jsonld                    │     (existing — extended to scan
  ├── tools.jsonld                           │      discover-project's annotations)
  └── schemas/tools/*.schema.json            │
                          │                  │
                          │                  └──► /sulis:discover-project SKILL.md
                          │                        (the imperative; carries
                          │                         # canonical:step:<name>
                          │                         annotations like release-train's
                          │                         YAML carries them)
                          │
                          ▼
              Operator runs the skill
                          │
                          ▼
         Detect ──► Infer ──► Ask ──► Mint ──► Verify
         (det.)    (prob.)   (human)  (det.)   (det.)
            │         │         │       │        │
            ▼         ▼         ▼       ▼        ▼
       Tools:    Tool:      (human   Tool:     Tool:
       git-      infer-     prompts) entity-   drift-
       remote-   config-              emitter   detector
       read +    values                (write    (validate
       read-     (LLM)                 atomic    .sulis/projects/
       pkg/                            to        <slug>.jsonld)
       pyproj/                         .sulis/
       ci, +                           projects/
       Read                            <slug>.jsonld)
       primitive                          │
                                          ▼
                              .sulis/projects/<slug>.jsonld
                              (consumer-owned Project entity)
                                          │
                                          │ (later, when the consumer
                                          │  runs /sulis:release-train,
                                          │  release-train binds to it via
                                          │  source path resolution)
                                          ▼
```

The canonical is the apex. Two consumers: (a) the drift detector validates the skill conforms; (b) operators run the skill which conforms to the canonical and produces the consumer's Project entity at `.sulis/projects/<slug>.jsonld`.

### Ports & Adapters

The skill is mostly orchestration. Two ports are worth naming explicitly because they're the abstraction boundaries the tests exercise:

```python
# Port 1 — Repo inspection (Detect phase consumes)
class RepoInspector(Protocol):
    def read_root(self, path: Path) -> RepoRoot: ...        # → {is_git, remote_url, primary_branch, has_remote}
    def read_package_manifests(self, path: Path) -> list[Manifest]: ...   # package.json, pyproject.toml, etc.
    def read_ci_workflows(self, path: Path) -> list[CiWorkflow]: ...      # .github/workflows/*, .gitlab-ci.yml
    def read_repo_contract(self, path: Path) -> RepoContract | None: ...  # .sulis/repo-contract.yml if present

# Port 2 — Configuration inference (Infer phase consumes)
class ConfigurationInferrer(Protocol):
    def infer(self, detected: DetectionResult, token_budget: int) -> InferenceResult: ...
    # InferenceResult.tokens_consumed enforces NFR-002;
    # raises TokenBudgetExceeded when over.

# Port 3 — Tenant derivation (used by Mint phase to populate belongs_to_tenant)
class TenantDeriver(Protocol):
    def derive_consumer_tenant(self, repo_org_slash_name: str) -> str: ...
    # Returns "dna:tenant:<26-char ULID>" per ADR-002 recipe.
    # Pure function; same input → same output; tested via fixed-vector test.
```

### Adapters (concrete implementations)

| Adapter | Implements | Backed by |
|---|---|---|
| `LocalFilesystemInspector` | `RepoInspector` | `subprocess` to `git remote get-url origin`, `git rev-parse --show-toplevel`, `git branch --show-current`; `Path.read_text` for manifests; `glob` for CI workflows. Each method returns a typed result or raises a typed error per Detect-phase FailureModes. |
| `LLMConfigurationInferrer` | `ConfigurationInferrer` | Calls the LLM with a strict prompt template (input = manifest + CI summary; output = JSON of `{field: {value, confidence}}`). Token-counted via the LLM provider's `usage` response. On budget exceedance, raises `TokenBudgetExceeded`. |
| `NullConfigurationInferrer` | `ConfigurationInferrer` | Returns empty `InferenceResult` immediately. Used when NFR-006 graceful-degradation triggers (LLM unavailable) — the skill falls back to all-human-ask. Same port, different adapter. Hexagonal architecture for the LLM seam. |
| `Sha256CrockfordTenantDeriver` | `TenantDeriver` | Pure-Python implementation of the ADR-002 recipe. Tested with fixed input/output vectors. |

### Composition root

The skill orchestrates these adapters in phase order. Because the skill is the canonical operator-facing entry point, the composition lives in the skill's prose (which calls the harness `Read`, the deterministic Python helpers in `plugins/sulis/scripts/_discovery/`, and the LLM via the agent's normal LLM-call surface — not via a Python `composition_root()` function).

For testability, `plugins/sulis/scripts/_discovery/__init__.py` exports a `run_discovery_headless(args) -> DiscoveryResult` function that wires the adapters together and exercises every phase. Integration tests invoke this function against fixture consumer repos; the skill's prose maps each Step to a call into this module.

### Where the Project entity lives

| Repo type | Path | Owner | Schema |
|---|---|---|---|
| Marketplace's own Projects (4 of them) | `plugins/sulis/instances/release-train/projects.jsonld` | Marketplace (per ADR-004 of `release-train-as-entities`) | foundation Project v1.0.0 |
| Consumer Projects (any number) | `.sulis/projects/<slug>.jsonld` (one file per Project) | Consumer | foundation Project v1.0.0 |

The discovery skill writes ONLY to the second path. Per NFR-004, it cannot write to `plugins/sulis/instances/release-train/projects.jsonld` even by accident. The path-safety check is encoded as a precondition in the `write-project-entity` Step's `agent_instructions`.

The discriminator at runtime: the skill computes the target path as `{consuming_repo_root}/.sulis/projects/{slug}.jsonld` where `consuming_repo_root = git rev-parse --show-toplevel`. The check `not target_path.resolve().is_relative_to(consuming_repo_root / ".sulis" / "projects")` aborts the mint.

### Slug derivation

Per MUC-007 pre-mortem #3, slug derivation must be deterministic and collision-aware:

```
slug(project_name)         = lowercase(replace(project_name, /[^a-z0-9-]/, "-"))
slug(monorepo_path)        = lowercase(basename(path))
                             # e.g., apps/cli → "cli"; packages/@scoped/foo → "foo"

# Collision detection in Mint:
if Path(".sulis/projects/{slug}.jsonld").exists():
    if --update flag absent: refuse (MUC-003 / MUC-007)
    if --update flag present: enter per-field diff flow (ADR-005)
```

---

## Armor — Operational Hardening

### External dependencies

| Dependency | Where used | Resilience policy |
|---|---|---|
| `git` CLI (subprocess) | `LocalFilesystemInspector.read_root` runs `git remote get-url origin`, `git rev-parse --show-toplevel`, `git branch --show-current` | Each subprocess call has a 5-second timeout. Non-zero exit codes are mapped to typed errors: `git remote get-url` non-zero → `git-no-remote` (MUC-006); `rev-parse --show-toplevel` non-zero → `non-git-directory` (MUC-001). No retries — these are deterministic local commands, failure is a real signal. |
| Local filesystem | `read_package_manifests`, `read_ci_workflows`, `read_repo_contract` | Read-only in Detect/Infer/Ask phases. Mint writes via atomic write semantics (see below). All writes confined to `<consuming_repo_root>/.sulis/projects/` (NFR-004). |
| LLM provider | `LLMConfigurationInferrer.infer` (Infer phase only) | 90-second timeout (NFR-001). Token budget enforced at 10k input+output per ADR-006. Network/auth/rate-limit failure → `NullConfigurationInferrer` (NFR-006 graceful degradation). Each failure path produces a typed exception that the skill prose maps to a user-facing plain-English message. |
| Drift detector | `python3 plugins/sulis/scripts/check-canonical-drift.py --scope .sulis/projects/<slug>.jsonld` invoked from Verify phase | Same drift detector as release-train (`7d666df`). Local; no network. Exit code 0 = pass; non-zero = roll back the mint (delete the just-written file) and surface the failure per MUC-005. |

### Atomic write semantics (the Mint phase contract)

Per MUC-002 (cancel mid-flow) + NFR-003 (deterministic re-run) + NFR-004 (path safety), the Mint phase MUST be atomic:

```python
def write_project_entity(target_path: Path, entity: dict) -> None:
    # Precondition: target_path is under <consuming_repo_root>/.sulis/projects/
    # Precondition: <consuming_repo_root>/.sulis/projects/ exists (mkdir -p if needed)
    # Precondition: target_path does not exist OR --update flag is present

    tmp = target_path.with_suffix(".jsonld.tmp")
    tmp.write_text(json.dumps(entity, indent=2))
    os.fsync(tmp.open("rb").fileno())   # durability
    tmp.replace(target_path)             # atomic rename on POSIX
```

Cancellation (SIGINT) between `tmp.write_text` and `tmp.replace` leaves a `.tmp` file. The skill's signal handler (and the next discovery run's startup) sweeps `.sulis/projects/*.tmp` and removes them. This satisfies MUC-002's "no partial entity persists" rule.

### Path-safety check

Before any write, the Mint phase asserts:

```python
resolved = target_path.resolve()
consuming_root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"]).decode().strip()).resolve()
allowed_dir = consuming_root / ".sulis" / "projects"
assert resolved.is_relative_to(allowed_dir), f"Refusing to write outside {allowed_dir}: {resolved}"
```

This blocks symlink-shenanigans, `..` traversal, and accidental writes to `plugins/sulis/instances/release-train/projects.jsonld` (which would corrupt the marketplace's own Projects).

### Secrets

No secrets in the discovery path. The skill does not read environment variables for credentials. The LLM call uses whatever credentials the host harness has already configured (Claude Code's own auth) — the skill doesn't see them.

### Observability

Each phase logs a structured line to stderr in plain English:

```
[discover-project] Detect phase: reading repo root, package manifests, CI workflows
[discover-project] Infer phase: proposing 12 configuration values (tokens used: 4,237 / 10,000)
[discover-project] Ask phase: 12 inferred values to confirm; 3 ambiguous fields to gather
[discover-project] Mint phase: writing to .sulis/projects/payments-app.jsonld (atomic)
[discover-project] Verify phase: drift detector PASS
```

These satisfy founder English (FE-01..FE-10) — no internal IDs, plain language. The full structured output (for downstream tooling) is a JSON envelope on stdout matching the marketplace's existing `{ok, data}` shape.

### Armor primitives, MUC-by-MUC

| MUC | Armor primitive | Implementation |
|---|---|---|
| MUC-001 (non-git directory) | Detect-phase precondition + typed error | `read-repo-root` Step checks for `.git/` and a remote; on absence, raises `non-git-directory` FailureMode; skill prose surfaces the exact error from SRD MUC-001 |
| MUC-002 (cancel mid-flow) | Atomic write + .tmp sweep on startup | `write_project_entity` writes-to-tmp-then-renames; the skill's session-startup sweeps stale `.tmp` files in `.sulis/projects/` |
| MUC-003 (entity already exists) | Pre-mint existence check | Mint phase checks `target_path.exists()` before any write; without `--update`, refuses and surfaces the MUC-003 error |
| MUC-004 (LLM incorrect deploy target) | Mandatory consumer confirmation gate | Ask phase surfaces every inferred value; `gather-ambiguous-fields` Step's postcondition is "no inferred value reaches Mint without explicit consumer approval" (FR-011) |
| MUC-005 (unknown Workflow ULID) | Post-mint drift verification + roll-back | Verify phase runs drift detector; failure deletes the just-written entity (the `.tmp` rename is reversed by `unlink(target_path)`) and surfaces the failure |
| MUC-006 (no git remote) | Detect-phase precondition + `--source-repo` override | `read-repo-root` distinguishes `not-git` from `git-no-remote`; the second permits `--source-repo <org/name>` override per FR-007 |
| MUC-007 (monorepo sibling collision) | `--path` scoping + slug collision detection | When `--path` is omitted and `.sulis/projects/` is non-empty, refuse; when `--path` is set, derived slug is checked against existing siblings; collision → refuse with MUC-007 error |
| MUC-008 (token budget exceeded) | Token counter + fallback adapter | `LLMConfigurationInferrer` raises `TokenBudgetExceeded` at the 10k boundary; the skill catches and swaps in `NullConfigurationInferrer`; degraded Ask phase prompts for every field |

### Cross-tenant drift semantics

A consumer's Project entity carries `belongs_to_tenant: <consumer-tenant>` (derived per ADR-002) while `release_workflow_ref` points at the marketplace tenant's `dna:workflow:01KT0RTRA1NWFW00000000000A`. This is a **valid cross-tenant reference**, not drift.

The Verify phase invokes the drift detector with a flag (`--cross-tenant-refs-allowed-for=release_workflow_ref,belongs_to_product_ref`) instructing it to treat those specific fields as cross-tenant boundaries rather than violations. If the drift detector doesn't already support this flag in its `7d666df` form, WP-009 extends it; the extension is small (a CLI argument + a check in the matcher).

---

## Proof — Verification Protocol

### Contract tests per port

**`RepoInspector` (port 1):**
- `read_root` against a fixture with `.git/` and a remote → returns `RepoRoot(is_git=True, has_remote=True, remote_url=..., primary_branch=...)`.
- `read_root` against a fixture without `.git/` → raises `NonGitDirectoryError` (mapped to MUC-001).
- `read_root` against a fixture with `.git/` but no remote → raises `NoRemoteError` (mapped to MUC-006).
- `read_package_manifests` on the populated fixture → returns the expected manifest list with parsed `name`, `version`, `private` fields.
- `read_ci_workflows` enumerates `.github/workflows/*.yml` correctly.

**`ConfigurationInferrer` (port 2):**
- `LLMConfigurationInferrer.infer` with a mocked LLM returning a known shape → returns the expected `InferenceResult`.
- Same adapter with token budget set to 100 (below realistic usage) → raises `TokenBudgetExceeded` and the exception carries the over-budget count.
- `NullConfigurationInferrer.infer` returns an empty `InferenceResult` immediately (no LLM call).

**`TenantDeriver` (port 3):**
- Fixed input/output vector test: `derive_consumer_tenant("acme/payments-app")` → exact expected ULID (locked in WP-002).
- Determinism test: 100 invocations with same input return byte-identical output.
- Different inputs → different outputs (collision resistance sanity).

### Integration tests (the load-bearing ones — FR-008 + dogfood acceptance)

`tests/integration/test_discover_e2e.py` ships with 4 fixture consumer repos and a real (or carefully mocked) LLM:

| Fixture | Shape | Test |
|---|---|---|
| `fixtures/empty/` | `.git/` + remote, no manifests, no CI | UC-001 happy path with all-human-ask fallback (NFR-006 path) → asserts entity written, drift verify passes, contains the expected `source.repo` |
| `fixtures/populated/` | `.git/` + remote + `package.json` + `.github/workflows/release.yml` | UC-001 happy path with full Infer phase → asserts inferred values surface to the human prompt + override flow records the override (UC-006 path) |
| `fixtures/monorepo/` | `.git/` + remote + `apps/backend/package.json` + `apps/cli/package.json` | UC-003 with `--path apps/cli` → asserts only `cli.jsonld` is written; running again with `--path apps/backend` adds `backend.jsonld` without touching `cli.jsonld` |
| `fixtures/pre-existing/` | `.git/` + remote + `.sulis/projects/foo.jsonld` already present | MUC-003 path: discovery without `--update` refuses; with `--update` enters per-field diff flow (UC-002) |

Plus four explicit-error fixtures (created on-the-fly in tests):

- `non-git/` (no `.git/`) → asserts non-zero exit + exact MUC-001 error + no files written.
- `no-remote/` (`.git/` but no remote) → asserts MUC-006 error.
- `token-budget/` (LLM mock that exceeds 10k) → asserts fallback to all-human-ask and a valid entity persists.
- `bad-workflow-ref/` (mock the Mint phase to write a bad `release_workflow_ref`) → asserts drift detector blocks and the partial entity is rolled back.

### Drift detector parity test

`plugins/sulis/scripts/tests/unit/test_check_canonical_drift_discover.py`:

- `fixture_pass/` — canonical Steps fully annotated in SKILL.md (annotations: `<!-- canonical:step:read-repo-root -->` etc.); FailureModes handled. Drift detector exits 0.
- `fixture_drift_missing_step/` — one canonical Step has no matching annotation in SKILL.md. Drift detector exits 1; envelope names the missing Step.
- `fixture_drift_extra_annotation/` — SKILL.md has an annotation for a Step not in canonical. Drift detector exits 1.

These mirror release-train's drift-detector tests exactly; the test file is a parallel copy with the discover-project fixtures.

### Idempotent-cancellation test

`test_discover_cancellation_idempotent.py`:

1. Run discovery against the populated fixture; cancel at the start of the Ask phase via `os.kill(os.getpid(), signal.SIGINT)`.
2. Assert `.sulis/projects/` is empty (or contains only directories — no `.jsonld` or `.tmp` files).
3. Re-run discovery on the same fixture without flags; assert the second run produces the same outcome as a first-time run would.

### Chaos tests

Not applicable in the strict sense — the skill is a CLI/operator skill with no network surface beyond the LLM call. The LLM-unavailable test (chaos-shaped) is covered by injecting `NullConfigurationInferrer` and asserting the all-human-ask path produces a valid entity.

---

## Trade-offs

| Decision | Chosen | Rejected | One-line reason |
|---|---|---|---|
| Execution strategy | Path A (canonical-as-spec + skill + drift detector) | Path B (LLM walks at every discovery); Path C (deterministic Python runner) | Path A established by `release-train-as-entities`; n=2 dogfood validates the pattern (ADR-001) |
| Skill name | `/sulis:discover-project` | `/sulis:setup` | Canonical drives imperative; the Workflow's name should be the skill's name (ADR-003) |
| Auto-prompt on missing entity | Fail-fast with clear error | Auto-route to discovery | Governance over mystification — the founder should always know what's about to happen (ADR-004) |
| Re-discovery semantics | Per-field diff with explicit approval | Bulk overwrite; merge with conflict markers | Founder owns mints; avoids silent drift between re-discovery runs (ADR-005) |
| Probabilistic token budget | 10k input+output | Higher (matches GPT-class budgets); lower (penny-pinch); no budget | 10k is the release-train precedent (NFR-010); instrument, revisit v1.1 (ADR-006) |
| Consumer tenant ULID | Derived per repo via SHA256 | Shared marketplace tenant; random ULID per run | Deterministic + collision-resistant + publicly verifiable + correct cross-tenant boundary at the drift detector (ADR-002) |
| Tool minting fidelity | Mint 5 new Tools fully (with schemas); reuse 2 existing | Mint all 5 as stubs; build no new Tools at all | The five new Tools are the load-bearing inputs (git read, manifest read, CI read, derivation, LLM); stubs would not provide the schema validation the drift detector needs |
| Atomic mint semantics | Write-to-tmp-then-rename + signal sweep | Direct write + cleanup-on-error | Atomic rename is POSIX-guaranteed; signal handler can't reliably clean partial writes in shell-killed processes |

---

## Open Architecture Questions

The five SRD Open Questions are resolved in ADRs (ADR-002..006). Two design-pass questions surfaced during this TDD that the founder may want to weigh in on but are not blocking:

1. **Annotation format inside SKILL.md.** Release-train uses YAML comments (`# canonical:step:<name>`) because release-on-merge.yml is YAML. SKILL.md is Markdown — proposed format is HTML comments (`<!-- canonical:step:read-repo-root -->`) placed immediately above the section heading for each phase Step. The drift detector's annotation parser needs a small extension to handle `<!--` vs `#`. **Recommendation:** HTML comments; extend the parser in WP-009.

2. **Should `derive-consumer-tenant` be a Tool entity or inline math?** The recipe is ~10 lines of Python. Elevating to a Tool entity adds discoverability (other future skills could call it) but adds JSON Schemas + a Tool ULID for a single-caller. **Recommendation:** elevate to Tool entity — the discoverability surface matters for the next consumer (env-init sibling) which will derive the same tenant ULID from the same repo. The Tool's `implementation_kind: python_import` keeps the cost negligible.

Neither is blocking. Plan-work can proceed without resolution; both will surface naturally in WP-001 (canonical entities) and WP-002 (tenant derivation) review.

### Reserved-Vocabulary Sweep

Proposed abstracts: `RepoInspector`, `ConfigurationInferrer`, `TenantDeriver`, `LocalFilesystemInspector`, `LLMConfigurationInferrer`, `NullConfigurationInferrer`, `Sha256CrockfordTenantDeriver`, `DetectionResult`, `InferenceResult`, `RepoRoot`, `Manifest`, `CiWorkflow`, `RepoContract`, `TokenBudgetExceeded`, `NonGitDirectoryError`, `NoRemoteError`.

Checked against the marketplace's existing reserved-vocabulary hint and GLOSSARY.md — none collide. `Inspector`, `Inferrer`, `Deriver` are not used as dispatch keys in any k8s/Sulis configuration. No GLOSSARY collisions (all new).

**Sweep result:** 16 abstracts checked / 0 collisions found.

---

## Sizing Report

See `SIZING.md` for the full sFPC + ASR breakdown. Highlights:

- **Tier:** L (computed; not overridden) — sFPC=15 (M-band) / ASR=21 (L-band) → take higher
- **TDD length:** ~370 lines (target: ≤ 400, satisfied)
- **ADRs produced:** 6 (target: 6 expected from dispatch, satisfied — ADR-001 Path-A-continuity, ADR-002 tenant recipe, ADR-003 skill name, ADR-004 fail-fast on missing, ADR-005 re-discovery diff, ADR-006 token budget)
- **Pillar coverage applied:** Form = PARTIAL (Path A pattern inherited from release-train; new = phase shape + ports); Armor = PARTIAL (drift detector + token budget inherited; new = atomic mint + LLM degradation + cross-tenant semantics); Proof = PARTIAL (drift-test discipline inherited; new = 4 consumer-repo fixtures + LLM mock + idempotent-cancellation)
- **Authoritative sources referenced:** release-train TDD, release-train ADR-001..004, decompose-validation-rubric Phase 8, foundation v0.6.0 schemas (Project/Workflow/Step/Trigger/FailureMode/Tool), CONTRACT_FIRST_STANDARD (canonical entities ARE the contract), WP_BACKEND_STANDARD (for Python helpers)
- **Sections that referenced rather than restated:** drift detector implementation, foundation entity schemas, Path A rationale, annotation format
- **Circuit breakers triggered:** none (TDD length within target; ADR count at expected number)
- **Reserved-Vocabulary Sweep:** 16 abstracts checked / 0 collisions / 0 renames / 0 shared-dispatch ADRs

### Expected WP set (8-10 atomic WPs)

For `/sulis:plan-work` to decompose:

| # | WP slug | Primitive | Contract focus |
|---|---|---|---|
| WP-001 | `canonical-entities-discover-project` | expand-create | All 5 JSON-LD entity files + 5 Tool schemas at `plugins/sulis/instances/discover-project/` |
| WP-002 | `tenant-derivation-tool` | expand-create | `derive-consumer-tenant` Tool + Python implementation + fixed-vector tests + recipe docs |
| WP-003 | `detect-phase` | expand-create | `RepoInspector` port + `LocalFilesystemInspector` adapter + 4 Detect Steps' helper functions |
| WP-004 | `infer-phase` | expand-create | `ConfigurationInferrer` port + LLM adapter + token-budget enforcement + null-adapter fallback |
| WP-005 | `ask-phase` | expand-create | Skill prose for `confirm-or-override-inferences` + `gather-ambiguous-fields`; founder-English prompts |
| WP-006 | `mint-phase` | expand-create | `write_project_entity` atomic write + path safety + signal handler + slug derivation |
| WP-007 | `verify-phase` | expand-create | Drift-detector invocation scoped to one entity + roll-back on failure + cross-tenant-refs-allowed flag |
| WP-008 | `discover-project-skill` | expand-create | `plugins/sulis/skills/discover-project/SKILL.md` with the 5 phase sections + canonical annotations |
| WP-009 | `drift-detector-extensions` | substitute-strangle (small) | Two surgical changes to the existing drift detector: HTML-comment annotation parsing; `--cross-tenant-refs-allowed-for` flag |
| WP-010 | `e2e-fixtures-and-dogfood` | reinforce-test | 4 fixture consumer repos + the integration test + a manual dogfood-on-marketplace-repo verification step |

WP-001..WP-010 has 1 dependency chain (WP-001 produces canonical → WP-009 reads it → WP-008 conforms to it → WP-010 exercises the full path). WPs 2-7 are largely parallel; WP-009 depends only on WP-001 for the annotation source; WP-008 depends on WP-001..WP-007; WP-010 depends on WP-008.

Recommend `/sulis:plan-work` to confirm this shape and add the Red-Green-Blue DoDs.
