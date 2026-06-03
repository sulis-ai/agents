# TDD — Product / Project / Opportunity: emitted + evolving, with the cross-repo Platform home built

**Source SPEC:** `../../.changes/feat-product-project-opportunity-evolution.SPEC.md`
**Recon:** `../../.changes/feat-product-project-opportunity-evolution.RECON.md`
**Tier:** L (per `SIZING.md` — sFPC 17 / ASR 13, taken to L for crossing four bounded contexts with a hard migration chain)
**Execution path:** Path A — canonical-as-spec where grammar/Workflow entities change; imperative emitters follow
**Structural template:** `../../.architecture/discover-project/` (same Path-A house style + Canonical-Identifiers discipline)
**WP doctrine:** `WP_BACKEND_STANDARD` (WPB-01..12). `founder_facing: false` — this is grammar / store / emitter work; **no visual contract**, no `WP_FRONTEND_STANDARD`.
**Depends on (in main):** CH-01KSWZ #118 (basic Product/Opportunity emit), `release-train-as-entities` / `discover-project` (Path-A pattern + drift detector + vendored foundation schemas).

## Overview

This change turns the brain's **evolution machinery ON** for living entities for
the first time, and **builds the cross-repo home** they live in. Six ADRs
decide it; this TDD ties them into one buildable design and one dependency-
ordered build plan.

The work is **not** a new runtime. The hexagonal seam already exists and is
explicitly designed for exactly this: the `EntityRepository` port, the
`LocalFileEntityAdapter`, the `_brain_query` read seam, and the
`_brain_emit_helper` graceful-degradation discipline. Per `SIZING.md`'s
Respect-Don't-Restate note, this TDD **references** those seams rather than
re-deriving the hexagonal architecture — the addressable work is the *new*
layering on top of them.

Six landed design docs on main are the prior thinking and were read at design
time (SPEC Constraint): `docs/plugin-evolution-context-brief.md`,
`docs/sulis-distribution-and-deployment-design.md`,
`docs/trunk-based-release-workflow-remodel.md`,
`docs/claude-code-plugin-distribution-brief.md`.

### The six ADRs at a glance

| ADR | Decision | Pillar driven |
|---|---|---|
| ADR-001 | LifecycleRun **is** the `prov:Activity`; Step is its type; v2 `step` ref points at a Step definition | Form (grammar shape) |
| ADR-002 | PROV vocabulary = W3C PROV-O `wasGeneratedBy` / `used`; `wasRevisionOf` excluded | Form (grammar) + Armor (single PROV writer) |
| ADR-003 | The evolve mechanism lives in a shared `_entity_evolve` helper **above** the port | Form + Armor (window invariants) |
| ADR-004 | LifecycleRun v1.0.0 → v2.1.0 lockstep migration (schema + helper + CLI + instances) | Armor (migration atomicity) |
| ADR-005 | Platform store = the EXISTING file adapter pointed at the central `~/.sulis/instances/{tenant_id}/` Tenant home (reuse, not build); SQLite deferred to a later change behind the same port | Form + Armor (central-home read consistency) |
| ADR-006 | Project home reconciliation — brain store canonical, `.sulis/projects/<slug>.jsonld` a human mirror | Form + Armor (path-safety preserved) |

### Non-goals (from ARCH.yaml — honoured throughout)

- Ontology v0.7 cross-artifact ref resolution — `belongs_to_product_ref` stays a plain string.
- Retrofitting evolve onto event entities — Decision + LifecycleRun stay append-only.
- The founder-facing "see/steer your living product" UI (ADE / Platform tier, downstream).
- Re-creating the basic capture-path emit (already in main).

---

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

## Canonical Identifiers (pre-canonicalised)

Per the cross-WP identifier canonicalisation rubric (decompose Phase 8), every
ULID and identifier that crosses WP boundaries is pinned here as the
authoritative source. Each WP Contract references this section rather than
re-minting. ULID character set: `0123456789ABCDEFGHJKMNPQRSTVWXYZ` (no I/L/O/U).

### Schema versions (the grammar revs this change makes)

| Schema | From | To | Why | Breaking? |
|---|---|---|---|---|
| `lifecyclerun` | 1.0.0 | **2.1.0** | major: `step_name`→`step` ref (ADR-001/004); minor: `+used` (ADR-002) | **YES** (ADR-004) |
| `product` | 1.0.0 | 1.1.0 | additive `+was_generated_by` (ADR-002) | no |
| `opportunity` | 1.0.0 | 1.1.0 | additive `+was_generated_by` (ADR-002) | no |
| `project` (foundation) | 1.0.0 | 1.1.0 | additive `+was_generated_by` (ADR-002) | no |
| `step` (foundation, referenced) | 1.2.0 | — | unchanged; the `step` ref target type | no |

### Canonical lifecycle Step instances (ADR-001/004 — definitions runs point at)

Authored at `plugins/sulis/instances/lifecycle-steps/steps.jsonld`, Path-A
style, deterministic ULIDs (mnemonic-stamped, prefix `01KT61X5` = the CH-01KT61
change-prefix + a Crockford-valid stamp; the Crockford base32 charset excludes
I/L/O/U, so no "LS" mnemonic — all three ULIDs verified clean of forbidden
characters and 26 chars long):

| Step name | ULID | Meaning | mechanism |
|---|---|---|---|
| `change-started` | `dna:step:01KT61X5ST01CHANGESTART00A` | a `sulis-change start` completed | mixed |
| `change-shipped` | `dna:step:01KT61X5ST02CHANGESH1PP00A` | a `sulis-change mark-shipped` completed | mixed |
| `unclassified-lifecycle-step` | `dna:step:01KT61X5ST03VNC1ASS1F1ED0A` | the catch-all for free `step_name` strings with no known mapping | mixed |

The `name→Step-ULID` resolution map (ADR-004) lives in `_lifecyclerun_emission`
keyed by the known-name prefix (`change-started` / `change-shipped`); unknown
names resolve to `unclassified-lifecycle-step` and preserve the original string
in the additive `step_label` field. The map is the single source of truth for
the events-known-name split; encoded as test-fixture pairs so a regenerate is
byte-stable.

### Canonical-Identifiers Pre-canonicalisation Manifest

For Phase 8 of the decompose rubric, the WP set references these identifiers by
anchor (e.g. `# canonical-source: TDD.md§Canonical Identifiers — change-started Step ULID`).
No WP invents a ULID inline.

### Canonical need identifiers (deferred infrastructure, per Verification Plan §6)

Recipe: `{noun}-{noun}-{vendor-or-scope}`. None deferred — every integration in
this change is verifiable at land time with in-process fixtures (the central
Tenant home is a temp directory; no external vendor; no network). The slice-end
aggregation reads an empty deferred list for this change. (Note: the SQLite
backend is deferred *engineering work* for a later change, not deferred
verification infrastructure for this one — this change ships nothing that needs
it.)

---

## Form — Structural Design

The codebase is **already hexagonal**. Coverage is high; the addressable Form
work is the *new* layering. The four seams below are **referenced, not restated**
(`SIZING.md` Respect-Don't-Restate):

| Seam (existing) | Lives at | Role | This change |
|---|---|---|---|
| `EntityRepository` port | `plugins/sulis/scripts/_entity_repository.py` | save / find_by_id / validate; reject-on-invalid | Unchanged. A later change adds a SQLite adapter behind it (ADR-005, deferred). |
| `LocalFileEntityAdapter` | `plugins/sulis/scripts/_entity_adapter_local.py` | file-per-instance write adapter; relocatable `base_dir` | Gains the ADR-003 history-envelope layout; **reused as the cross-repo Platform home** by pointing `base_dir` at `~/.sulis/instances/{tenant_id}/` (ADR-005). |
| `iter_entities` read seam | `plugins/sulis/scripts/_brain_query.py` | set-shaped reads; impl-swappable behind signatures | Gains as-of-time + cross-repo Tenant queries (the same flat-file walk over the central Tenant home — ADR-005). |
| `_brain_emit_helper` | `plugins/sulis/scripts/_brain_emit_helper.py` | graceful-degradation emission call sites | The 3 LifecycleRun helpers resolve Step refs (ADR-004); evolve call sites added. |

### New components (the addressable Form work)

| # | Component | Lives at | Kind | ADR |
|---|---|---|---|---|
| 1 | Canonical lifecycle Step instances | `plugins/sulis/instances/lifecycle-steps/steps.jsonld` | JSON-LD (3 Steps) | 001/004 |
| 2 | PROV grammar fields | the 4 schemas above (`+was_generated_by`, `+used`) + vendored compiled copies | JSON Schema | 002 |
| 3 | LifecycleRun v2.1.0 schema + emitter | `lifecyclerun.schema.json` 2.1.0 + `_lifecyclerun_emission.py` (`step` + `step_label` + ID seed from step+timestamp) | JSON Schema + Python | 001/004 |
| 4 | Instance migration script | `plugins/sulis/scripts/migrate_lifecyclerun_v1_to_v2.py` (or `sulis-emit-lifecyclerun --migrate`) | Python | 004 |
| 5 | `_entity_evolve` helper | `plugins/sulis/scripts/_entity_evolve.py` — `evolve_entity(...)` + `_LIVING_ENTITY_TYPES` allowlist | Python (above the port) | 003 |
| 6 | As-of-time read | new function on `_brain_query.py` — `(type, id, as_of) → window whose [valid_from, valid_to) contains as_of` | Python (read seam) | 003 |
| 7 | Central Tenant home wiring | point the living-entity emit `base_dir` at `~/.sulis/instances/{tenant_id}/` (Tenant ULID from the existing `_tenant_emission.py` derivation); reuse `LocalFileEntityAdapter` — no new module | Python (wiring, existing adapter) | 005 |
| 8 | Cross-repo Tenant read | `find_current_for_tenant(...)` over the central home using the existing `_brain_query` flat-file walk | Python (read seam) | 005 |
| 9 | Project reconcile in minter | `_discovery/minter.py` — canonical `repo.save("project", …)` + `write_project_mirror(…)` | Python (refactor) | 006 |
| 10 | discover-project Mint prose + canonical Workflow Step | `plugins/sulis/skills/discover-project/SKILL.md` + canonical instance | Markdown + JSON-LD | 006 |

### The three-layer PROV shape (ADR-001) and the evolve flow (ADR-003)

```
Step (definition / type)  ◀── step ───  LifecycleRun (the Activity / occurrence)
                                               │  used →  input entity versions
                                               │ wasGeneratedBy
                                               ▼
                            Product / Opportunity / Project (living Entity version)
                                               │
                          evolve_entity():  close prior window (valid_to)
                                            open new window (valid_from + confidence
                                                             + sys_status + was_generated_by)
                                            persist BOTH via repo (the file adapter,
                                                                    repo-local OR central home)
```

`evolve_entity` sits **above** the port (ADR-003), so it works unchanged against
either adapter. The `_LIVING_ENTITY_TYPES` allowlist (Product / Opportunity /
Project) is the single guard that keeps evolve **off** event entities (Decision /
LifecycleRun stay append-only — non-goal honoured). The file adapter materialises
the window pair in the single-file history-envelope idiom (ADR-003) — the same
idiom whether the entity lives in the repo-local tree or the central Tenant home.
A later SQLite adapter (ADR-005, deferred) would materialise windows in rows; that
is ADR-003's OAQ-1, deferred with the SQLite swap.

### Change-primitive classification (per WP)

| Build-order piece | Primitive | Group | Note |
|---|---|---|---|
| 1 lifecyclerun-migration | substitute-strangle (schema) + reinforce-test | substitute / reinforce | breaking swap; deprecated `--step-name` CLI alias; `removal_plan` target = next minor after consumers migrate |
| 2 prov-grammar | expand-create | expand | additive schema fields |
| 3 evolve-mechanism | expand-create | expand | new helper above the port; **not** a wrap |
| 4 apply-evolve | reorganise-refactor + reinforce | reorganise | emitters move from `save` to `evolve_entity`; **characterisation test first** |
| 5 platform-store | reuse | (reuse) | **reuse** the existing file adapter at the central Tenant home — no new code (ADR-005); SQLite deferred |
| 6 project-reconcile | reorganise-refactor | reorganise | minter refactor; **characterisation test first** (ADR-006) |

**Reuse before build.** ADR-005's Platform home is **reuse** — the existing
`LocalFileEntityAdapter` pointed at the existing `~/.sulis/instances/{tenant_id}/`
convention, top of the change-primitive decision priority (REUSE existing code).
No new module, no wrap. The SQLite adapter the seam anticipates is a deferred
EXPAND-Create for a *later* change, behind the same port. ADR-006's minter change
is Refactor-on-internal-code, gated by a characterisation test, never a wrap over
the existing `write_project_entity`.

---

## Armor — Operational Hardening

Coverage is partial-high: graceful-degradation (`_brain_emit_helper`), atomic-
write + path-safety (`minter.py`), reject-on-invalid (the port) **already exist
and are reused**. The addressable Armor work is the four new guarantees below.

| New guarantee | ADR | Implementation | Failure mode it closes |
|---|---|---|---|
| **Migration atomicity** (no half-migrated state) | 004 | Schema bump + emitter updates land in one dependency-ordered slice; the instance-migration script re-validates each instance against v2.1.0 BEFORE writing (reject-on-invalid), is idempotent (presence of `step` ⇒ skip), runs eager on the marketplace's own store, lazy for consumers | A store with mixed v1/v2 LifecycleRuns; a v2 validator rejecting a v1 instance mid-flight |
| **Window invariants** | 003 | Close-prior-then-open-new is the **single-file history-envelope rewrite** on the file adapter (close `valid_to` + open new window in one atomic envelope write — ADR-003). No instant with two open windows (`valid_to IS NULL`) for one entity. No-op (byte-identical re-emit) opens no window — idempotent re-runs don't churn history | Overlapping valid-windows; history churn on re-run |
| **Central-home write durability** | 005 | The central Tenant home reuses the file adapter's existing `_atomic_write` discipline (write-tmp-then-rename) — a committed window survives process crash; a half-written file is never visible. SQLite WAL/transaction durability is **deferred** with the SQLite swap to a later change (drop-in behind the same port) | Lost write on crash; torn read during a window-swap |
| **Append-only guard for event entities** | 003 | `_LIVING_ENTITY_TYPES` allowlist in `_entity_evolve`; `evolve_entity` **refuses** a type not on the list. Decision / LifecycleRun can never be evolved | Accidental evolve of an append-only event entity |
| **Path-safety preserved on reconcile** | 006 | The mirror write keeps `minter.py`'s `_assert_path_safety` (`.resolve()` + `is_relative_to(<repo_root>/.sulis/projects)`), `_atomic_write`, `_assert_not_exists` (MUC-003), stale-tmp sweep, SIGINT handler — verbatim, now guarding the mirror | Symlink / `..` traversal; partial mirror on cancel |

### PROV write discipline (ADR-002)

A single writer per edge: `_entity_evolve` is the **only** writer of
`was_generated_by`; `_lifecyclerun_emission` is the **only** writer of `used`.
No other code writes PROV edges — this keeps the grammar's first PROV writes
disciplined and auditable. `wasRevisionOf` is excluded and stays excluded
(lineage is the bitemporal window chain + event `supersedes`).

### Graceful degradation (reused, unchanged)

Emission stays best-effort: `_brain_emit_helper` returns `dict | None`; the host
operation (`change start`, `deploy`) never fails because emission failed. The
evolve call sites and the Project reconcile inherit this — a canonical store
write that fails degrades gracefully (logged), the founder's host operation
continues. Project reconcile is canonical-first / mirror-second: a failed
canonical write writes no mirror; a failed mirror after a good canonical save is
a logged best-effort degradation.

### Secrets / observability

No secrets in any path (the central home is a local directory tree; no network;
no credentials). The home path is the Tenant-scoped default
`~/.sulis/instances/{tenant_id}/`, resolved from the deterministic Tenant ULID —
no secret material. Emission logging stays plain-English to stderr (founder English,
FE-01..FE-10): no internal IDs in operator-facing log lines.

---

## Proof — Verification Protocol

Coverage is partial: contract-test discipline + drift-detector parity infra
**exist and are reused**. The addressable Proof work is the four test postures
below — one per ADR's load-bearing claim.

| Test | Posture | Subject | ADR |
|---|---|---|---|
| **Central-home read/write test** | The existing `LocalFileEntityAdapter`, pointed at a temp `~/.sulis/instances/{tenant_id}/`-shaped `base_dir`, round-trips living-entity versions: save validates, the central-home read returns them, reject-on-invalid never persists. (The existing port contract test already covers the file adapter — no new-adapter contract test, because there is no new adapter.) | the existing file adapter at the central home | 005 |
| **Evolve close/open-window characterisation test** | First-emission opens one window; second emission closes the prior (`valid_to` set) + opens a new one with `was_generated_by`; the prior+new windows abut exactly (prior `valid_to` == new `valid_from`); a byte-identical re-emit is a no-op (no new window); an attempt to evolve a `_LIVING_ENTITY_TYPES`-excluded type **raises** | `_entity_evolve.evolve_entity` | 003 |
| **PROV-emission test** | An evolved entity version carries `was_generated_by` → a valid `dna:lifecyclerun:<ulid>` ref; the generating LifecycleRun carries `used` → the consumed input refs; the JSON-LD `@context` maps `was_generated_by`→`prov:wasGeneratedBy`, `used`→`prov:used`; **no** `wasRevisionOf` anywhere | the PROV edges on living entities + LifecycleRun | 002 |
| **v1→v2 LifecycleRun migration test** | A v1 fixture (`step_name` string, no `step`) in → a v2.1.0 instance out (`step` ref resolved via the name map; original string preserved in `step_label`; `step_name` removed); re-validates against 2.1.0; idempotent on re-run (v2 in ⇒ skipped); an unmappable name resolves to `unclassified-lifecycle-step`; rejects-on-still-invalid (never writes an invalid instance) | `migrate_lifecyclerun_v1_to_v2` | 004 |
| **Append-only event-entity guard test** | `evolve_entity(entity_type="decision", …)` and `…="lifecyclerun"` both **raise** (not on the allowlist); `save` of those types still works (append-only path intact) | `_LIVING_ENTITY_TYPES` guard | 003 |
| **As-of-time read test** | Given three windows of one entity, `(type, id, as_of)` returns the window whose `[valid_from, valid_to)` contains `as_of`; `as_of` after the latest open window returns the open window; before the first returns None | the new `_brain_query` as-of function | 003 |
| **Cross-repo Tenant read test** | `find_current_for_tenant(tenant, "product")` over the central `~/.sulis/instances/{tenant_id}/` home returns every open-window Product for that Tenant written there across repos; a read of a single repo-local tree cannot (asserts the central Tenant home is the reason this works) | the existing `_brain_query` walk over the central home | 005 |
| **Drift-detector parity (Path A)** | The lifecycle-steps canonical + the updated discover-project Mint Workflow Step conform to their skill prose; drift detector exits 0 on conformance, non-zero on a missing/extra annotation | canonical ↔ skill conformance | 001/006 |

**Integration tests use real adapters** (MEA-09): the file adapter is exercised
against a real temp directory (both the repo-local tree and a temp central
`~/.sulis/instances/{tenant_id}/`-shaped home), not a mock. No mocks at the
store seam.

**Central-home parity:** the query-seam tests run the existing `iter_entities` /
`find_entities` walk against **both** the repo-local tree and the central Tenant
home behind the same signatures — proving relocation is behaviour-preserving.
(The future SQLite-backend cross-backend parity test arrives with the deferred
SQLite swap, ADR-005.)

---

## Build Order + Dependency Chain (for `/sulis:plan-work`)

The six pieces from `ARCH.yaml`, with the dependency chain made explicit. This
is the spine the decomposition pass consumes — WPs are atomic within each piece;
ordering is the `dependsOn` graph below.

```
1. lifecyclerun-migration   (the PROV spine — everything hangs off the Activity)
        │  produces: v2.1.0 schema, canonical Steps, migrated emitter+CLI+instances
        ▼
2. prov-grammar             (wasGeneratedBy / used vocabulary)
        │  depends on 1: `used` rides in the v2.1.0 bump; was_generated_by needs
        │  a LifecycleRun ref shape to point at
        ▼
3. evolve-mechanism         (shared _entity_evolve: close/open-window + PROV-write)
        │  depends on 2: it WRITES was_generated_by, so the field must exist
        ▼
4. apply-evolve             (Product, Opportunity, Project become living)
        │  depends on 3: emitters call evolve_entity; characterisation-test-first
        ▼
5. platform-store           (point the emit base_dir at the central Tenant home —
        │                    existing file adapter at ~/.sulis/instances/{tenant_id}/;
        │                    SQLite deferred to a later change behind the same port)
        │  depends on 3: the central home stores the WINDOWS evolve produces,
        │  so the window contract must exist first
        ▼
6. project-reconcile        (discover-project / minter land Project in the brain home)
           depends on 3 (evolve, so re-discovery is an evolve),
                     5 (the reconciled home is whichever adapter the port has),
                     and 4 (Project is a living entity by then)
```

| Piece | dependsOn | Primitive | Key contract surface |
|---|---|---|---|
| 1 lifecyclerun-migration | — | substitute-strangle + reinforce | `lifecyclerun` 2.1.0 schema; `step`+`step_label`; canonical Steps; name→ULID map; migration script |
| 2 prov-grammar | 1 | expand-create | `+was_generated_by` (Product/Opportunity/Project 1.1.0); `+used` (LifecycleRun 2.1.0); `@context` term maps |
| 3 evolve-mechanism | 2 | expand-create | `evolve_entity(...)`; `_LIVING_ENTITY_TYPES`; as-of-time read function |
| 4 apply-evolve | 3 | reorganise-refactor + reinforce | Product/Opportunity/Project emitters call `evolve_entity`; **characterisation_test** required |
| 5 platform-store | 3 | reuse | point living-entity emit `base_dir` at `~/.sulis/instances/{tenant_id}/` (existing file adapter + existing Tenant ULID); `find_current_for_tenant` over the central home via the existing `_brain_query` walk; SQLite deferred |
| 6 project-reconcile | 3, 4, 5 | reorganise-refactor | `minter.write_project_entity` → canonical `repo.save` + `write_project_mirror`; **characterisation_test** required; path-safety preserved |

Pieces 1→2→3 are a strict chain. 4 and 5 both depend on 3 and can proceed in
parallel after it. 6 is the join (depends on 3, 4, 5). `expected_workpackages:
12-16` (ARCH.yaml) — `/sulis:plan-work` owns the real count and the Red-Green-Blue
DoDs.

---

## Trade-offs

| Decision | Chosen | Rejected | One-line reason |
|---|---|---|---|
| Where evolve lives | shared helper **above** the port | methods on the port; per-emitter logic | keeps the port per-instance; one shared primitive (ADR-003, EP-03) |
| PROV idiom | W3C PROV-O `wasGeneratedBy` / `used` | `wasRevisionOf`; a side-file triple store | SPEC-fixed convention; lineage already in the bitemporal chain (ADR-002) |
| LifecycleRun migration | one atomic lockstep slice + eager script | optional `step`; lazy-only; keep `step_name` | "no half-migrated state" (ADR-004) |
| Platform store home | **reuse** the existing file adapter at the central `~/.sulis/instances/{tenant_id}/` Tenant home | build a new SQLite backend now; multi-repo file walk | check-before-building: the central home + relocatable `base_dir` already exist; reuse beats build (ADR-005) |
| SQLite backend (#30) | **deferred** to a later change, drop-in behind the same port | build it now | no query-scale need yet; the swap stays cheap because the port is the contract (ADR-005) |
| Project home | brain store canonical + `.sulis/projects` mirror | `.sulis/projects` only; delete the mirror; sync job | one canonical writer, one derived mirror; safety discipline preserved (ADR-006) |
| `belongs_to_product_ref` | stays a plain string | resolve to a live ref | ontology v0.7 resolution is a NON-GOAL |

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

This change has **no SRD `## Verification Plan`** (Path-A change from a SPEC, not
an SRD). This section is authored design-time-first per the SEA Verification-
Plan-Concretion discipline, populated across the six canonical subsections. The
change's `kind:` is **backend** → the per-kind adapter is pytest nodeids
(`tests/...::test_...`). `founder_facing: false` → no visual / Playwright surface.

### 1. User-observable behaviour being verified

Not founder-facing UI. The observable behaviour is **data behaviour**: a living
entity that changes leaves a closed prior window + a new open window + a PROV
`wasGeneratedBy` edge, queryable as-of-time; a Product/Opportunity is readable
cross-repo for one Tenant; LifecycleRun emits at v2.1.0 with a real `step` ref.
These are asserted at the Python package boundary (the emitter / helper / adapter
public functions), not at a screen.

### 2. Verification environment(s)

Local + CI. All tests run in-process against temp directories — both the
repo-local tree and a temp central `~/.sulis/instances/{tenant_id}/`-shaped home,
all served by the existing file adapter — no external service, no network, no
credentials. Fixtures live under `plugins/sulis/scripts/tests/`. The same suite
runs identically local and in CI (the slice's PR gate).

### 3. Bootstrap-from-zero case

A fresh clone at the merge SHA, after `uv sync`, can run the full suite green.
The central home needs no provisioning (it is a temp directory created by the
test, written by the existing file adapter). The canonical lifecycle Steps +
vendored compiled schemas are committed artifacts in the repo — no generation
step is required to verify.
Bootstrap test: `tests/integration/test_evolve_store_e2e.py` exercises
emit → evolve → central-home-write → cross-repo-read from a cold temp central
Tenant home.

### 4. Per-integration verification strategy

| Integration point | Strategy | Classification | Concretion (shape) |
|---|---|---|---|
| Central Tenant home (existing file adapter, relocated `base_dir`) | **real temp-dir** `~/.sulis/instances/{tenant_id}/`-shaped home, existing `LocalFileEntityAdapter` | existing | concrete — `tests/unit/test_central_tenant_home.py::test_round_trip_central_home`, `::test_cross_repo_tenant_read`, `::test_atomic_write_durable` |
| The `EntityRepository` port (file adapter) | **existing contract test** (already covers `LocalFileEntityAdapter`) | existing | concrete — `tests/unit/test_entity_repository_contract.py::test_contract[file]` (no `[sqlite]` parametrisation in this change — SQLite adapter deferred) |
| Evolve helper above the port | **in-process**, real adapter | existing | concrete — `tests/unit/test_entity_evolve.py::test_close_open_window`, `::test_noop_idempotent`, `::test_refuses_event_entity` |
| PROV emission | **in-process** schema-validated | existing | concrete — `tests/unit/test_prov_emission.py::test_was_generated_by_on_living`, `::test_used_on_lifecyclerun`, `::test_no_wasrevisionof` |
| LifecycleRun v1→v2 migration | **real fixture-in / instance-out** | existing | concrete — `tests/unit/test_lifecyclerun_migration.py::test_v1_fixture_migrates`, `::test_idempotent`, `::test_unmappable_to_unclassified`, `::test_rejects_invalid` |
| Project reconcile (minter) | **characterisation-first**, real temp repo + real store | existing | concrete — `tests/unit/test_minter_reconcile.py::test_canonical_save_then_mirror`, `::test_path_safety_preserved`, `::test_muc003_refuses` |
| Drift detector (Path A) | **existing detector**, fixture pass/drift | existing | concrete — `tests/unit/test_check_canonical_drift_lifecycle_steps.py` |

No `deferred-to-follow-on` rows — every integration is verifiable at land time
(the central home is a temp directory served by the existing file adapter; no
external vendor; no network seam needing a recording mock).

### 5. Per-kind verification adapter

`kind: backend` → adapter = **pytest nodeids** (per the canonical kind→adapter
table). Every row in §4 names a pytest nodeid. No Vitest / Playwright (not
frontend); no `tests/methodology/` fixtures (not a methodology change).

### 6. Infrastructure needs surfaced (deferred)

**None.** The central Tenant home needs no vendor mock, no test OAuth account, no
seed-data service — it is a temp directory served by the existing file adapter.
The canonical Step instances + vendored compiled schemas are committed fixtures,
not deferred infrastructure. The deferred-need list aggregated at slice-end is
empty for this change (§Canonical need identifiers above). The SQLite backend
(#30) is deferred *engineering*, not deferred verification infrastructure.

### Per-WP `verification:` frontmatter shape (for `/sulis:plan-work`)

Every WP in this change ships **Shape 1 — concrete** (`adapter: backend` +
`artifact: <pytest nodeid>`) — each WP lands with a real test the moment it
merges. No Shape-2 (deferred) WPs. Shape-3 (trivial carveout) applies only to a
mechanical vendored-schema-copy WP if `/sulis:plan-work` splits one out
(`na: true` + justification ≥ 30 chars).

---

## Sizing Report

See `SIZING.md` for the full sFPC + ASR breakdown. Highlights:

- **Tier:** L (computed sFPC 17 / ASR 13 both mid-M; taken to L for crossing four bounded contexts + a hard migration chain). Confirmed, not overridden.
- **TDD length:** within the tier-L target; the hexagonal seams are **referenced, not restated** (no Clean-Architecture re-derivation — `SIZING.md` Respect-Don't-Restate).
- **ADRs produced:** 6 (ADR-001..006 — at the ARCH.yaml expected count; each records a decision affecting >1 component or locking a technology/grammar choice).
- **Pillar coverage applied:** Form = PARTIAL (port/adapter/query seams inherited; new = evolve layering, PROV grammar, central-Tenant-home wiring (reuse, no new adapter), Project move); Armor = PARTIAL (graceful-degradation + atomic-write + reject-on-invalid inherited; new = migration atomicity, window invariants, central-home write durability, append-only guard); Proof = PARTIAL (contract-test + drift-parity infra inherited; new = central-home read/write test, evolve characterisation test, PROV-emission test, v1→v2 migration test).
- **Authoritative sources referenced:** the four existing seams (port / file adapter / query / emit helper), the four landed design docs, `discover-project` + `release-train-as-entities` TDDs (Path-A prior art), `CONTRACT_FIRST_STANDARD` (the `EntityRepository` Protocol IS the contract), `WP_BACKEND_STANDARD`, W3C PROV-O.
- **Sections that referenced rather than restated:** the hexagonal seams, the drift-detector implementation, the Path-A rationale, the graceful-degradation discipline.
- **Circuit breakers triggered:** none (TDD within target; ADR count at expected; no section restates an authoritative source).

### Expected WP set (12-16 atomic WPs — `/sulis:plan-work` owns the real count)

| Build-order piece | Likely WPs | Primitive |
|---|---|---|
| 1 lifecyclerun-migration | canonical-lifecycle-steps; lifecyclerun-2.1.0-schema; emitter-step-ref; brain-emit-helper-step-resolution; cli-step-arg; instance-migration-script; drift-parity | substitute-strangle + reinforce |
| 2 prov-grammar | prov-fields-living-schemas; used-on-lifecyclerun; context-term-maps; vendored-compiled-copies | expand-create |
| 3 evolve-mechanism | entity-evolve-helper; living-entity-allowlist; as-of-time-read | expand-create |
| 4 apply-evolve | product-emitter-evolve; opportunity-emitter-evolve; project-emitter-evolve (each characterisation-first) | reorganise-refactor + reinforce |
| 5 platform-store | central-tenant-home-wiring (point emit base_dir at ~/.sulis/instances/{tenant_id}/); cross-repo-tenant-read; central-home-read-write-test | reuse |
| 6 project-reconcile | minter-canonical-plus-mirror (characterisation-first); discover-project-skill-mint-prose | reorganise-refactor |

Recommend `/sulis:plan-work` to confirm this shape, pin the `dependsOn` graph
from §Build Order, and add the Red-Green-Blue DoDs + the Shape-1 `verification:`
frontmatter from §Verification Plan.
