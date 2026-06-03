---
id: WP-016
title: Re-vendor LifecycleRun v2.2.0 (additive for_project ref) + wire for_project at change-start
status: blocked
blocked_reason: UPSTREAM — gated on the mint-request `for-project-edge-2026-06-03` (LifecycleRun 2.1.0 → 2.2.0, +1 optional `for_project: ref→project` property) being accepted → a mint walk recompiling → the bumped v2.2.0 schema (PD canonical + insurance mirror) re-vendored into canonical compiled output. The in-repo re-vendor + emitter wiring cannot land until that upstream artifact exists. SAME gating shape as WP-008's `wasGeneratedBy` gate.
kind: contract
primitive: substitute-strangle
group: SUBSTITUTE
change_id: CH-01KT61
sequence_id: WP-016
dependsOn: [WP-002, WP-005, WP-013]
upstream_dependsOn:
  - "mint-request: .specifications/business-dna/mint-requests/for-project-edge-2026-06-03.md (PROPOSAL → must be ACCEPTED + walked + recompiled + re-vendored)"
  - "outcome: LifecycleRun schema_version 2.1.0 → 2.2.0, +1 optional `for_project` plain ref property (range dna:entity:project, card 0..1, predicate sulis:forProject) → re-vendored PD canonical + insurance mirror"
blocks: []
removal_plan:
  deprecated_surface: "the vendored LifecycleRun 2.1.0 compiled schema (no for_project property)"
  target: "replaced in this WP by the bumped 2.2.0 copy once the upstream mint re-vendors it; additive MINOR drop-in over WP-002's v2.1.0 — no transitional surface retained, no instance migration (pre-bump 2.1.0 instances validate unchanged)"
estimated_token_cost:
  input: 3k
  output: 3k
tdd_section: Form #3 (v2.2.0 increment); Canonical Identifiers — Schema versions (lifecyclerun 2.2.0); ADR-004 (two-stage re-vendor), ADR-007
adrs: [ADR-004, ADR-007]
verification:
  adapter: backend
  artifact: tests/unit/test_lifecyclerun_for_project.py::test_change_start_run_carries_for_project
---

## Context

The run→Project traceability increment (ADR-007), **a separate, mint-gated step
ON TOP OF the v2.1.0 re-vendor spine.** It un-defers the `LifecycleRun.for_project`
edge that ADR-001 + ADR-006 named as the deferred run-side link — now in-scope by
founder decision (2026-06-03).

`for_project` is a NEW optional property recording **which Project (release-unit /
repo) a run operated in.** With it, an app-started or terminal-started change's
emitted LifecycleRun links back to its Project, closing the
**Tenant → Product → Opportunity → Project** trace.

| Schema | schema_version | Added |
|---|---|---|
| **LifecycleRun** | 2.1.0 → **2.2.0** | optional `for_project: ref→project`, card `0..1`, predicate `sulis:forProject` |

**Three facts that fix the shape (ADR-007):**

1. **A plain ref, NOT a `prov_constraints` edge.** `for_project` is modelled
   exactly like the **live** `Workflow.for_project` (foundation v0.5.0 /
   Workflow v1.1.0, DR-017): a plain optional `properties` ref string with
   pattern `^dna:(project):[0-9A-HJKMNP-TV-Z]{26}$`. It is a **scope** assertion
   ("this run ran in that Project"), not a PROV-O generation assertion. It does
   **NOT** touch the PROV vocabulary, the `_predicate_map` (`sulis:forProject` is
   already present — it powers `Workflow.for_project`), or `@context`. Contrast
   WP-008's `wasGeneratedBy`, which IS a `prov_constraints` Entity→Activity edge.
2. **NOT v0.7-gated.** The reference is PD (LifecycleRun) → foundation (Project),
   with a live predicate + a live property shape. PD→foundation refs resolve
   today. The ontology v0.7 NON-GOAL gates `belongs_to_product_ref` resolution
   only — a different ref on a different entity.
3. **This is an UPSTREAM-GATED re-vendor, not an in-repo author.** The grammar
   change (the v2.2.0 bump) is routed through a mint request + a
   `/sulis-brain:mint-coach` walk (compile → admission gate → DR → re-vendor).
   This WP **consumes** the result: it re-vendors the bumped v2.2.0 compiled
   schema over WP-002's v2.1.0 copy. **It cannot land until the upstream mint is
   accepted + recompiled + re-vendored** (see `blocked_reason` +
   `upstream_dependsOn`) — the SAME gate shape as WP-008.

**Buildable-now is preserved.** WP-002 keeps re-vendoring **v2.1.0** (the
already-minted step-ref spine) and stays buildable immediately — the step-ref
emitter migration does NOT wait on the `for_project` mint. This WP is the v2.2.0
increment that supersedes WP-002's v2.1.0 file, additively (one optional
property), once its own mint clears.

# canonical-source: TDD.md §Canonical Identifiers — Schema versions (lifecyclerun 2.2.0); the `for_project` ref shape is the live `Workflow.for_project` precedent (plugins/sulis/brain/compiled/foundation/workflow.schema.json:60, predicate sulis:forProject)

## Contract

### Files modified (in-repo, once upstream clears)

```
plugins/sulis/brain/compiled/product-development/lifecyclerun.schema.json   # RE-VENDOR v2.1.0 → 2.2.0 (additive: +1 optional for_project ref property)
plugins/sulis/scripts/_brain_emit_helper.py                                 # emit_change_started_event resolves the Project ULID → sets for_project (optional)
plugins/sulis/scripts/_lifecyclerun_emission.py                             # compose_lifecyclerun gains optional for_project param (emitted only when provided)
sulis-emit-lifecyclerun (CLI)                                               # --for-project arg → emit_lifecyclerun(for_project=...) (optional)
```

**NOT modified:** `project.schema.json` (Project carries no edge — ADR-006,
ADR-007). No `_predicate_map` file (`sulis:forProject` already present). No
`@context` map. No snake_case fork (the property IS `for_project`, matching
`Workflow.for_project`). No instance migration (additive MINOR — pre-bump 2.1.0
instances validate unchanged).

### The property (reusing the live Workflow.for_project shape verbatim)

```jsonc
// lifecyclerun.schema.json properties — 2.2.0 (additive over 2.1.0)
"for_project": {
  "type": "string",
  "pattern": "^dna:(project):[0-9A-HJKMNP-TV-Z]{26}$",
  "description": "the Project (release-unit / repo) this run operated in — optional; omitted for meta / pre-Project / cross-Project runs; predicate sulis:forProject; mirrors Workflow.for_project (foundation v0.5.0)"
}
```

Not in `required`. `card 0..1`. The `$id` ends `/lifecyclerun/2.2.0`.

### compose + emit (additive, optional — never breaks existing callers)

```python
def compose_lifecyclerun(
    *,
    step: str,
    outcome: str,
    at: str | None = None,
    by_actor: str = "",
    run_id: str | None = None,
    for_project: str | None = None,   # NEW: dna:project:<ulid> ref; emitted only when provided
) -> dict:
    ...
    # for_project added to the dict only when truthy (unevaluatedProperties:false clean)
```

- `emit_change_started_event` resolves the current Project ULID (the repo's
  discovered Project, via the existing Project resolution the change-start path
  has access to) and passes `for_project=<ulid>`. When no Project resolves
  (meta run, pre-discovery), it passes `for_project=None` → the field is omitted.
- `sulis-emit-lifecyclerun --for-project dna:project:<ulid>` threads to
  `for_project`; absent → omitted.

Graceful-degradation discipline unchanged: a Project that cannot be resolved
never fails the emit — `for_project` is simply absent.

## Definition of Done

### Red — Failing tests written

- [ ] `tests/unit/test_lifecyclerun_schema_v2_2.py::test_revendored_schema_is_2_2_0` — `$id` ends `/lifecyclerun/2.2.0`; the vendored file is byte-faithful to the upstream-recompiled canonical v2.2.0
- [ ] `::test_for_project_property_present_and_optional` — `for_project` is in `properties`, NOT in `required`, pattern `^dna:(project):[0-9A-HJKMNP-TV-Z]{26}$`
- [ ] `::test_for_project_shape_matches_workflow` — the `for_project` property shape (type/pattern) equals `Workflow.for_project`'s (the live precedent), proving convention reuse
- [ ] `::test_no_prov_constraints_for_project` — `for_project` is a plain `properties` ref, NOT a `prov_constraints` edge; no `_predicate_map` or `@context` change
- [ ] `::test_v2_1_instance_still_valid_under_2_2` — a v2.1.0 run with NO `for_project` validates against v2.2.0 (zero-migration additive MINOR)
- [ ] `tests/unit/test_lifecyclerun_for_project.py::test_compose_emits_for_project_when_provided` — `compose_lifecyclerun(for_project="dna:project:<ulid>")` includes the field
- [ ] `::test_compose_omits_for_project_when_none` — `for_project=None` → field absent (unevaluatedProperties:false clean)
- [ ] `::test_compose_rejects_non_project_ref` — a non-`dna:project:` value is rejected
- [ ] `::test_change_start_run_carries_for_project` — `emit_change_started_event` with a resolvable Project produces a run whose `for_project` is that Project's ULID, validating against v2.2.0
- [ ] `::test_change_start_omits_for_project_when_no_project` — no resolvable Project → emit succeeds, `for_project` absent (graceful degradation)
- [ ] `tests/unit/test_emit_lifecyclerun_cli_for_project.py::test_for_project_flag_threads` — `--for-project dna:project:<ulid>` sets the field; absent → omitted

### Green — Implementation makes tests pass

- [ ] Upstream mint accepted + walked + recompiled (the gate — verified before this WP starts)
- [ ] Bumped v2.2.0 compiled schema re-vendored over WP-002's v2.1.0 copy (additive, single file)
- [ ] `compose_lifecyclerun` gains optional `for_project`; emitted only when provided
- [ ] `emit_change_started_event` resolves the Project ULID → sets `for_project` (or omits when none)
- [ ] CLI `--for-project` threads through; absent → omitted

### Blue — Refactor complete

- [ ] `for_project` shape is identical to `Workflow.for_project` (one convention, EP-03) — no snake_case fork, no `prov_constraints` encoding, no `_predicate_map`/`@context` edit
- [ ] Re-vendored v2.2.0 copy is byte-faithful to the upstream-recompiled canonical + insurance mirror (drift detector parity, WP-007 machinery re-pointed at 2.2.0)
- [ ] Project resolution reuses the existing change-start Project lookup — no new Project-discovery code
- [ ] Operator-facing log lines stay plain-English (FE-01..FE-10); a missing Project is a quiet omission, not an error log

## Sequence

- **dependsOn:**
  - **WP-002** — the v2.1.0 re-vendor + emitter core must exist first; this WP
    re-vendors v2.2.0 *over* WP-002's v2.1.0 file (additive supersession) and
    extends the same `compose_lifecyclerun` / `emit_change_started_event` that
    WP-002 migrated to the `step` ref.
  - **WP-005** — peer-collision serialisation on `sulis-emit-lifecyclerun` (the
    CLI). WP-005 migrates the CLI to `--step` (and the `--step-name` deprecated
    alias); this WP adds `--for-project` to the same CLI entry. Both edit the same
    file → serialise (P6): this WP lands after WP-005's CLI migration, so no two
    WPs modify the CLI in parallel.
  - **WP-013** — peer-collision serialisation. WP-013 edits `_brain_emit_helper.py`
    (the central-Tenant-home `base_dir` resolution); this WP also edits
    `_brain_emit_helper.py` (the change-start `for_project` resolution). Both
    touch the same file → serialise (P6): this WP lands after WP-013, so no two
    WPs modify `_brain_emit_helper.py` in parallel. (WP-002 also touches it, and
    is already an ancestor via the v2.1.0 dependency.)
- **upstream_dependsOn:** the `for-project-edge-2026-06-03` mint acceptance + walk
  + recompile + re-vendor (see frontmatter). **This is the upstream gate** — the
  WP starts `blocked` and is unblocked only when the bumped canonical compiled
  v2.2.0 schema exists. Mirror of WP-008's gate on the `wasGeneratedBy` mint.
- **blocks:** none — this is a leaf increment.

## Estimated Token Cost

- **Input:** ~3k (the bumped upstream v2.2.0 schema + the live `Workflow.for_project` precedent + ADR-004/ADR-007 + the two emitter modules)
- **Output:** ~3k (1 re-vendored compiled copy + the additive emitter param + CLI flag + tests)
- **Total:** ~6k

## Notes

- `substitute-strangle`: the vendored LifecycleRun 2.1.0 schema (no `for_project`)
  is replaced by its 2.2.0 successor; the `removal_plan` records the replaced
  surface. Unlike WP-002's breaking swap, this is an **additive** replacement
  (one optional property), so no instance migration and no reject-on-invalid
  window — pre-bump 2.1.0 instances stay valid under 2.2.0.
- **The upstream gate is the load-bearing dependency of the run→Project
  traceability story.** This WP is a pure consumer of the upstream `for_project`
  mint decision, never an authority on the grammar — exactly like WP-008 is for
  the `wasGeneratedBy` mint.
- **Project carries no edge** (ADR-006, ADR-007). The run is the carrier. No
  `project.schema.json` touch, now or ever.
- The two upstream mints in this change are **independent**: WP-008 waits on the
  `wasGeneratedBy` mint (Product + Opportunity schemas); this WP waits on the
  `for_project` mint (LifecycleRun schema). Neither gates the other; both are
  authored in parallel upstream.
