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
| ADR-001 | LifecycleRun **is** the `prov:Activity`; it **instantiates** a Step (a `prov:Plan`) via `sulis:viaStep`; v2.1.0 `step` ref points at that Step. Project is ALSO a `prov:Plan` (excluded from provenance) | Form (grammar shape) |
| ADR-002 | PROV edge **reuses the existing `prov_constraints` convention** (`wasGeneratedBy → lifecyclerun`, card `0..1`) on **Product + Opportunity ONLY** — NO snake_case wire field; Project + `wasRevisionOf` excluded; routed through the upstream mint | Form (grammar) + Armor (single PROV writer) |
| ADR-003 | The evolve mechanism lives in a shared `_entity_evolve` helper **above** the port; provenance write is **conditional** (prov:Entity types only — Project gets windows but no `wasGeneratedBy`) | Form + Armor (window invariants) |
| ADR-004 | LifecycleRun v1.0.0 → v2.1.0 **surgical RE-VENDOR** of the already-minted canonical schema (DR-009 + DR-013), lockstep/atomic with the emitter migration in ONE WP; `step_label` + `used`-on-run DROPPED | Armor (migration atomicity) |
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
| `lifecyclerun` | 1.0.0 | **2.1.0** | **RE-VENDOR of already-minted canonical** (DR-009 `step_name`→`step` v2.0.0; DR-013 `+run_id/deterministic/inputs_ref/outputs_ref` v2.1.0). No `step_label`, no `used`-on-run | **YES** (ADR-004) |
| `product` | 1.0.0 | 1.1.0 | additive `wasGeneratedBy` `prov_constraints` edge, card `0..1` (ADR-002) — **upstream-minted**, re-vendored | no |
| `opportunity` | 2.0.0 | 2.1.0 | additive `wasGeneratedBy` `prov_constraints` edge, card `0..1` (ADR-002) — **upstream-minted**, re-vendored | no |
| `project` (foundation) | 1.0.0 | **— (no change)** | Project is `prov:Plan`; `wasGeneratedBy` is a type violation. NO edit, NO bump (ADR-002, ADR-006) | no |
| `step` (foundation, referenced) | 1.2.0 | — | unchanged; the `step` ref target type (a `prov:Plan`) | no |

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

The `name→Step-ULID` resolution map (ADR-004) lives in `_brain_emit_helper` /
`_lifecyclerun_emission` (both edited atomically in WP-002) keyed by the
known-name prefix (`change-started` / `change-shipped`); unknown names resolve to
`unclassified-lifecycle-step`. The original free string, where trace grouping is
needed, is carried by the **canonical `run_id` field** — **NOT** a `step_label`
field, which does not exist in canonical v2.1.0 (DR-013 rejected payload-on-the-
run-record). The map is the single source of truth for the events-known-name
split; encoded as test-fixture pairs so a regenerate is byte-stable.

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
| 2 | PROV edge (re-vendored) | `wasGeneratedBy` `prov_constraints` edge on **Product + Opportunity** vendored compiled copies (Project excluded) — **upstream-minted**, no snake_case field, no `_predicate_map` edit | JSON Schema (re-vendor) | 002 |
| 3 | LifecycleRun v2.1.0 re-vendor + emitter (ATOMIC) | re-vendor canonical `lifecyclerun.schema.json` 2.1.0 + `_lifecyclerun_emission.py` + `_brain_emit_helper.py` (`step` ref; ID seed from step+timestamp; per-run detail → `run_id`, NOT `step_label`) — one atomic lockstep WP | JSON Schema + Python | 001/004 |
| 4 | Instance migration script | `plugins/sulis/scripts/migrate_lifecyclerun_v1_to_v2.py` (or `sulis-emit-lifecyclerun --migrate`) | Python | 004 |
| 5 | `_entity_evolve` helper | `plugins/sulis/scripts/_entity_evolve.py` — `evolve_entity(...)` + `_LIVING_ENTITY_TYPES` allowlist | Python (above the port) | 003 |
| 6 | As-of-time read | new function on `_brain_query.py` — `(type, id, as_of) → window whose [valid_from, valid_to) contains as_of` | Python (read seam) | 003 |
| 7 | Central Tenant home wiring | point the living-entity emit `base_dir` at `~/.sulis/instances/{tenant_id}/` (Tenant ULID from the existing `_tenant_emission.py` derivation); reuse `LocalFileEntityAdapter` — no new module | Python (wiring, existing adapter) | 005 |
| 8 | Cross-repo Tenant read | `find_current_for_tenant(...)` over the central home using the existing `_brain_query` flat-file walk | Python (read seam) | 005 |
| 9 | Project reconcile in minter | `_discovery/minter.py` — canonical `repo.save("project", …)` + `write_project_mirror(…)` | Python (refactor) | 006 |
| 10 | discover-project Mint prose + canonical Workflow Step | `plugins/sulis/skills/discover-project/SKILL.md` + canonical instance | Markdown + JSON-LD | 006 |

### The PROV shape (ADR-001) and the evolve flow (ADR-003)

```
Step (the prov:Plan / the recipe)  ◀── step (sulis:viaStep) ───  LifecycleRun (the prov:Activity / the run that instantiated it)
                                                                       │
                                                                       │ wasGeneratedBy (prov_constraints edge, card 0..1)
                                                                       ▼
                                       Product / Opportunity (prov:Entity living version)   ← Project is prov:Plan: NO wasGeneratedBy
                                                                       │
                          evolve_entity():  close prior window (valid_to)
                                            open new window (valid_from + confidence + sys_status)
                                              + (prov:Entity types only) the wasGeneratedBy edge
                                            persist BOTH via repo (the file adapter,
                                                                    repo-local OR central home)
```

`evolve_entity` sits **above** the port (ADR-003), so it works unchanged against
either adapter. **Two orthogonal guards:** the `_LIVING_ENTITY_TYPES` allowlist
(Product / Opportunity / Project) keeps evolve **off** event entities (Decision /
LifecycleRun stay append-only) — all three living types get windows; the
**provenance** write is a *separate* conditional (`generated_by is not None`) so
Product/Opportunity get the `wasGeneratedBy` edge and **Project does not** (it is
`prov:Plan` — the edge is a type violation; ADR-002, ADR-006). There is **no
`used` edge written here** — canonical v2.1.0 LifecycleRun has no `used` field.
The file adapter materialises
the window pair in the single-file history-envelope idiom (ADR-003) — the same
idiom whether the entity lives in the repo-local tree or the central Tenant home.
A later SQLite adapter (ADR-005, deferred) would materialise windows in rows; that
is ADR-003's OAQ-1, deferred with the SQLite swap.

### Change-primitive classification (per WP)

| Build-order piece | Primitive | Group | Note |
|---|---|---|---|
| 1 lifecyclerun-revendor | substitute-strangle (re-vendor + emitter, ATOMIC) | substitute | re-vendor canonical v2.1.0 + emitter migration in ONE WP; deprecated `--step-name` CLI alias; `removal_plan` target = next minor after consumers migrate |
| 2 prov-edge | substitute-strangle (re-vendor) | substitute | re-vendor the **upstream-minted** `wasGeneratedBy` `prov_constraints` edge on Product + Opportunity (Project excluded); **upstream-gated** |
| 3 evolve-mechanism | expand-create | expand | new helper above the port; **not** a wrap; conditional prov-write |
| 4 apply-evolve | reorganise-refactor + reinforce | reorganise | emitters move from `save` to `evolve_entity` (Product/Opp w/ prov; Project windows-only); **characterisation test first** |
| 5 platform-store | reuse | (reuse) | **reuse** the existing file adapter at the central Tenant home — no new code (ADR-005); SQLite deferred |
| 6 project-reconcile | reorganise-refactor | reorganise | minter refactor (Project windows + supersedes, no prov); **characterisation test first** (ADR-006) |

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

A single writer: `_entity_evolve` is the **only** writer of the `wasGeneratedBy`
edge — and it writes it as the canonical `prov_constraints`-style edge (never a
snake_case scalar), **conditionally**, only for `prov:Entity` types (Product,
Opportunity). Project's evolve passes `generated_by=None` and writes no edge
(`prov:Plan` — type violation). **There is no `used` edge written** — canonical
v2.1.0 LifecycleRun has no `used` field (DR-013 settled its field-set with
content-addressed `inputs_ref`/`outputs_ref`); modelling consumed inputs as ABox
`prov:used` triples is a separate, later concern. `wasRevisionOf` is excluded and
stays excluded (lineage is the bitemporal window chain + event `supersedes`).
The grammar change itself (adding the edge) is **upstream-minted**, not authored
here — this change consumes the re-vendored schemas.

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
| **Evolve close/open-window characterisation test** | First-emission opens one window; second emission closes the prior (`valid_to` set) + opens a new one; the prior+new windows abut exactly (prior `valid_to` == new `valid_from`); a byte-identical re-emit is a no-op (no new window); an attempt to evolve a `_LIVING_ENTITY_TYPES`-excluded type **raises** | `_entity_evolve.evolve_entity` | 003 |
| **PROV-edge-emission test** | An evolved **Product/Opportunity** version (prov:Entity) carries the `wasGeneratedBy` edge → a valid `dna:lifecyclerun:<ulid>` ref, expressed via the `prov_constraints` convention (NOT a snake_case scalar); an evolved **Project** version (prov:Plan) carries **NO** `wasGeneratedBy` edge; the helper writes **no `used` field**; **no** `wasRevisionOf` anywhere | the `wasGeneratedBy` edge on Product/Opportunity (Project paired-negative) | 002 |
| **re-vendor + v1→v2 LifecycleRun migration test** | The re-vendored schema is byte-faithful to canonical v2.1.0 (no `step_label`, no `used`); a v1 fixture (`step_name` string, no `step`) in → a v2.1.0 instance out (`step` ref resolved via the name map; **`step_name` dropped, NOT into a `step_label`**; per-run detail → `run_id` where needed); re-validates against 2.1.0; idempotent on re-run (v2 in ⇒ skipped); an unmappable name resolves to `unclassified-lifecycle-step`; rejects-on-still-invalid | re-vendored schema + `migrate_lifecyclerun_v1_to_v2` | 004 |
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
1. lifecyclerun-revendor    (the PROV spine — RE-VENDOR canonical v2.1.0 + emitter, ATOMIC)
        │  produces: re-vendored v2.1.0 schema, canonical Steps, migrated emitter+CLI+instances
        ▼
2. prov-edge                (wasGeneratedBy prov_constraints edge on Product + Opportunity)
        │  depends on 1: the edge points at a LifecycleRun, whose v2.1.0 ref shape
        │  must exist in the vendored tree first
        │  UPSTREAM-GATED: the edge is added by the mint (accepted → recompiled →
        │  re-vendored) before this in-repo re-vendor can land
        ▼
3. evolve-mechanism         (shared _entity_evolve: close/open-window + CONDITIONAL prov-write)
        │  depends on 2: it WRITES the wasGeneratedBy edge for prov:Entity types,
        │  so the edge must exist in the Product/Opportunity grammar
        ▼
4. apply-evolve             (Product + Opportunity become living WITH prov; Project living WINDOWS-ONLY)
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
| 1 lifecyclerun-revendor | — | substitute-strangle (ATOMIC) | RE-VENDOR canonical `lifecyclerun` 2.1.0 (`step`, NO `step_label`, NO `used`) + emitter core (compose + helper) in one WP; canonical Steps; name→ULID map; migration script |
| 2 prov-edge | 1 | substitute-strangle (re-vendor) | re-vendor the **upstream-minted** `wasGeneratedBy` `prov_constraints` edge (Product 1.1.0 + Opportunity 2.1.0; **Project excluded**); NO snake_case field, NO `_predicate_map` edit; **upstream-gated** |
| 3 evolve-mechanism | 2 | expand-create | `evolve_entity(...)` with **conditional** prov-write; `_LIVING_ENTITY_TYPES`; as-of-time read function |
| 4 apply-evolve | 3 | reorganise-refactor + reinforce | Product/Opportunity emitters call `evolve_entity(generated_by=<ref>)`; Project emitter calls it with `generated_by=None` (windows-only); **characterisation_test** required |
| 5 platform-store | 3 | reuse | point living-entity emit `base_dir` at `~/.sulis/instances/{tenant_id}/` (existing file adapter + existing Tenant ULID); `find_current_for_tenant` over the central home via the existing `_brain_query` walk; SQLite deferred |
| 6 project-reconcile | 3, 4, 5 | reorganise-refactor | `minter.write_project_entity` → canonical `repo.save` + `write_project_mirror`; Project evolve = windows + supersedes, no prov; **characterisation_test** required; path-safety preserved |

Pieces 1→2→3 are a strict chain. 4 and 5 both depend on 3 and can proceed in
parallel after it. 6 is the join (depends on 3, 4, 5). Piece 2 (and everything it
gates: 3→6) is **upstream-blocked** on the `wasGeneratedBy` mint being accepted +
recompiled + re-vendored; the pre-gate spine (piece 1) lands independently.
`/sulis:plan-work` owns the real WP count (13 after the re-cut) and the
Red-Green-Blue DoDs.

---

## Trade-offs

| Decision | Chosen | Rejected | One-line reason |
|---|---|---|---|
| Where evolve lives | shared helper **above** the port | methods on the port; per-emitter logic | keeps the port per-instance; one shared primitive (ADR-003, EP-03) |
| PROV idiom | reuse the existing `prov_constraints` `wasGeneratedBy` edge (Product/Opportunity only) | snake_case `was_generated_by` scalar; `wasRevisionOf`; a side-file triple store; the edge on Project | PROV not greenfield — convention already wired on 5 entities; Project is prov:Plan (type violation); lineage already in the bitemporal chain (ADR-002) |
| LifecycleRun migration | **surgical re-vendor** of already-minted canonical v2.1.0 + emitter, one atomic WP + eager script | author a new shape with `step_label`/`used`; the wholesale `sync-from-canonical.sh`; optional `step`; keep `step_name` | re-vendor not author (DR-009 + DR-013 already minted it); "no half-migrated state"; respect the mixed-version vendor (ADR-004) |
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
| PROV edge emission (Product/Opportunity only) | **in-process** schema-validated; **upstream-gated** on the mint | existing (gated) | concrete — `tests/unit/test_prov_edge_schemas.py::test_was_generated_by_edge_on_product_and_opportunity`, `::test_project_schema_unchanged`, `tests/unit/test_entity_evolve.py::test_project_evolve_writes_NO_prov_edge`, `::test_no_wasrevisionof` |
| LifecycleRun re-vendor + v1→v2 migration | **real fixture-in / instance-out** | existing | concrete — `tests/unit/test_lifecyclerun_schema_v2.py::test_revendored_schema_matches_canonical`, `tests/unit/test_lifecyclerun_migration.py::test_v1_fixture_migrates`, `::test_idempotent`, `::test_unmappable_to_unclassified`, `::test_rejects_invalid` |
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

**No deferred verification infrastructure.** The central Tenant home needs no
vendor mock, no test OAuth account, no seed-data service — it is a temp directory
served by the existing file adapter. The canonical Step instances + vendored
compiled schemas are committed fixtures. The deferred-need list aggregated at
slice-end is empty for this change. The SQLite backend (#30) is deferred
*engineering*, not deferred verification infrastructure.

**One upstream PREREQUISITE (not a verification deferral):** the prov-edge WP
(piece 2 / WP-008) cannot land until the `wasGeneratedBy` mint
(`.specifications/business-dna/mint-requests/wasgeneratedby-provenance-edge-2026-06-03.md`)
is accepted → walked → recompiled → re-vendored. Its test
(`test_was_generated_by_edge_on_product_and_opportunity`) ships *with* WP-008 the
moment that prerequisite clears — it is a gated-but-concrete test, not a
deferred-to-follow-on need identifier. The pre-gate spine (piece 1) is verifiable
immediately.

### Per-WP `verification:` frontmatter shape (for `/sulis:plan-work`)

Every WP in this change ships **Shape 1 — concrete** (`adapter: backend` +
`artifact: <pytest nodeid>`) — each WP lands with a real test the moment it
merges. **WP-008 is Shape-1 concrete but starts `blocked`** on the upstream
`wasGeneratedBy` mint (its test ships with it once the mint is re-vendored — a
gated-but-concrete test, NOT a Shape-2 deferral). No Shape-2 (deferred-to-
follow-on) WPs. Shape-3 (trivial carveout) applies only to a mechanical
vendored-schema-copy WP if `/sulis:plan-work` splits one out (`na: true` +
justification ≥ 30 chars).

---

## Sizing Report

See `SIZING.md` for the full sFPC + ASR breakdown. Highlights:

- **Tier:** L (computed sFPC 17 / ASR 13 both mid-M; taken to L for crossing four bounded contexts + a hard migration chain). Confirmed, not overridden.
- **TDD length:** within the tier-L target; the hexagonal seams are **referenced, not restated** (no Clean-Architecture re-derivation — `SIZING.md` Respect-Don't-Restate).
- **ADRs produced:** 6 (ADR-001..006 — at the ARCH.yaml expected count; each records a decision affecting >1 component or locking a technology/grammar choice).
- **Pillar coverage applied:** Form = PARTIAL (port/adapter/query seams inherited; new = evolve layering, PROV edge re-vendor (convention reuse, not new grammar), central-Tenant-home wiring (reuse, no new adapter), Project move); Armor = PARTIAL (graceful-degradation + atomic-write + reject-on-invalid inherited; new = re-vendor+migration atomicity, window invariants, central-home write durability, append-only guard); Proof = PARTIAL (contract-test + drift-parity infra inherited; new = central-home read/write test, evolve characterisation test, prov-edge-emission test (Product/Opportunity only + Project paired-negative), re-vendor + v1→v2 migration test).
- **Authoritative sources referenced:** the four existing seams (port / file adapter / query / emit helper), the four landed design docs, `discover-project` + `release-train-as-entities` TDDs (Path-A prior art), `CONTRACT_FIRST_STANDARD` (the `EntityRepository` Protocol IS the contract), `WP_BACKEND_STANDARD`, W3C PROV-O.
- **Sections that referenced rather than restated:** the hexagonal seams, the drift-detector implementation, the Path-A rationale, the graceful-degradation discipline.
- **Circuit breakers triggered:** none (TDD within target; ADR count at expected; no section restates an authoritative source).

### Actual WP set (13 atomic WPs — produced by `/sulis:plan-work`, see `work-packages/INDEX.md`)

> The pre-plan-work estimate (12-16) resolved to **13 WPs** after the
> brain-governance re-cut. The defining shape changes vs the naïve estimate: the
> LifecycleRun schema + the two emitter moves **collapse into one atomic re-vendor
> WP** (lockstep mandate); the prov work is **a re-vendored `prov_constraints`
> edge on Product + Opportunity only** (Project excluded, prov:Plan), **upstream-
> gated on the mint**.

| Build-order piece | WPs | Primitive |
|---|---|---|
| 1 lifecyclerun-revendor | WP-001 canonical-lifecycle-steps; **WP-002 revendor-emitter-lockstep (ATOMIC — absorbs the old schema+compose+helper WPs)**; WP-005 cli-step-arg; WP-006 instance-migration-script; WP-007 drift-parity | substitute-strangle (atomic) |
| 2 prov-edge (UPSTREAM-GATED) | WP-008 prov-edge-product-opportunity (re-vendor the upstream-minted `wasGeneratedBy` `prov_constraints` edge; Project excluded) | substitute-strangle (re-vendor) |
| 3 evolve-mechanism | WP-009 entity-evolve-helper (conditional prov-write + allowlist); WP-010 as-of-time-read | expand-create + extend |
| 4 apply-evolve | WP-011 emitter-characterisation-test; WP-012 apply-evolve (Product/Opp w/ prov; Project windows-only) | reinforce-test + reorganise-refactor |
| 5 platform-store | WP-013 central-tenant-home-wiring | reuse |
| 6 project-reconcile | WP-014 minter-characterisation-test; WP-015 minter-canonical-plus-mirror (Project windows + supersedes, no prov) | reinforce-test + reorganise-refactor |

The `dependsOn` graph, Red-Green-Blue DoDs, and Shape-1 `verification:`
frontmatter are pinned in `work-packages/` (validated PASS — see
`work-packages/DECOMPOSE_VALIDATION.md`).
