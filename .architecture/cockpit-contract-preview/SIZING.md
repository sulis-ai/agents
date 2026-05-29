# Sizing — cockpit-contract-preview

> Computed 2026-05-29 from the SPEC + the existing cockpit codebase. Read this
> instead of recomputing in downstream skills.
>
> Re-checked 2026-05-29 after the **full-picture default view** revision
> (founder decision: the default view renders the whole shape of the change —
> entities + lifecycle, business rules, journeys, what-each-action-changes,
> enriched permission — auto-hidden section-by-section). **Tier unchanged: M.**
> The expansion lands entirely inside the existing keystone step (WP-1) and the
> WP-3 visual-contract declaration: no new entities, integrations, endpoints, or
> client surfaces. sFPC unchanged (7); ASR 7 → 9; ADR count unchanged (5,
> revised in place); WP count unchanged.
>
> Re-checked again 2026-05-29 after the **second** full-picture pass (deeper
> founder review against the authoritative ServiceSpec code), which added
> **form fields** (the priority surface — labels, placeholders, input types,
> grouping, validation, human enum labels, show-when/depends-on), moved
> **languages (i18n)** into the default view, and added **background-action**
> and **enriched-retirement** (sunset + replacement) flags. Events confirmed
> **out of scope** (not carried by the ServiceSpec contract). **Tier still
> unchanged: M.** Still no new entities/integrations/endpoints/client surfaces —
> all of it is derivation inside WP-1's keystone renderer reading a contract
> already located in the worktree. **sFPC unchanged (7); ASR 9 → 10** (added:
> form-fields projection with auto-trim + OpenAPI degradation — a non-trivial
> JSON-Schema→readable-fields renderer; the i18n/async/retirement moves are
> small derivations folded into existing section-builders, not separate ASRs).
> ADR count unchanged (5, revised in place); WP count unchanged.
>
> Re-checked again 2026-05-29 after the **founder review of the rendered
> mockup**, which raised two view-structure refinements (the renderer's
> source-of-truth / no-drift / auto-trim rules are UNCHANGED):
> (1) **permissions lead with plain English** — each operation shows "Who can
> do this: …" derived from the permission's `typicallyAssignedTo` /
> `description`, with the raw permission **code demoted into the technical
> toggle** (ADR-002 Revision 4); and (2) **the default view groups by
> service/area** when a change spans more than one area, with an "areas covered"
> overview, single-area rendering ungrouped (new **ADR-006**). **Tier still
> unchanged: M.** Still no new entities/integrations/endpoints/client surfaces —
> both refinements are derivation/layout inside WP-1's keystone renderer.
> **sFPC unchanged (7); ASR 10 → 11** (added: the area-grouping derivation — a
> non-trivial structural parse of service boundaries from three sources +
> per-area section restructuring + single-vs-multi rule + OpenAPI tag fallback;
> the permission "who can do this" change is a small reordering of an existing
> derivation, not a separate ASR). **ADR count 5 → 6** (Issue 2 multi-area
> grouping warrants its own ADR-006; Issue 1 permission display is a
> revision-in-place of ADR-002). WP count unchanged.

## Functional complexity (sFPC)

| Element | Count | Items |
|---|---|---|
| ILF (internal data) | 1 | the per-change contract-artifact set (CONTRACT.html / UI.html / a manifest) written into a worktree |
| EIF (external data) | 2 | the OpenAPI spec(s) located in a worktree; the visual contract / tokens located in a worktree |
| EI (mutating ops) | 1 | `wpx-render-contract` (writes rendered artifacts) |
| EO (deriving ops) | 2 | the two new cockpit read endpoints that derive/serve a rendered contract + UI |
| EQ (retrieving ops) | 1 | per-change link resolution (which artifacts exist for a change) |
| **sFPC** | **7** | |

## Architecturally significant requirements (ASR)

| ASR | Source |
|---|---|
| Render from source-of-truth, no drift | SPEC "What to avoid" |
| Founder-legible **full-picture** default view with **auto-trim** (what-it-does, entities + lifecycle, business rules, journeys, what-each-action-changes; each section hidden when the spec omits it) | Founder decision (2026-05-29, binding) |
| Permission display leads with plain-English "Who can do this" (from the spec's `permissions` definition `typicallyAssignedTo` + `description`); raw permission code demoted to the technical toggle | Founder decision 1 (revised; ADR-002 Rev 4) — *reordering of an existing derivation, not a separate ASR* |
| **Area grouping** — group the default view by service/area when a change spans more than one (operation keys `{service}/{op}`, `ServiceCatalog` contributions, or multiple ServiceSpec docs); "areas covered" overview; single-area ungrouped; OpenAPI tag fallback | Founder decision (2026-05-29, ADR-006) |
| **Form-fields projection** (priority surface) — readable fields from entity `properties` + operation `input` schemas: label, placeholder, input type, group/order, validation rules, human enum labels (`x-enum-labels`), show-when (`x-visibility`) / depends-on (`x-dependent-enum`); auto-trim + OpenAPI degradation (basic fields, no rich metadata) | Founder decision (2026-05-29, binding) |
| Graceful degradation (non-OpenAPI / no visual contract) | SPEC + founder |
| Generic per-change resolution (anti-hard-wiring) | Founder decision 3 |
| Pre-dispatch review gate timing + on-demand | SPEC WP-3 |
| Recreate-on-demand for shipped changes | SPEC WP-4 (#56) |
| Cockpit read-only invariant preserved | existing cockpit TDD §17 |
| Languages / background-action / enriched-retirement surfaced in the default view (small derivations folded into existing section-builders, from `i18n` / `async` / `deprecated`+`sunsetDate`+`replacementOperation`) — *not counted as separate ASRs* | Founder decision (2026-05-29, binding) |
| **ASR count** | **11** |

## Tier

- sFPC 7 → tier S band; ASR 11 → tier M band. **Take the higher: tier M.**
- The first full-picture revision added 2 ASRs (full-picture-with-auto-trim;
  enriched permission semantics); the second added 1 more (form-fields
  projection with auto-trim + OpenAPI degradation); the third (founder review of
  the rendered mockup) added 1 more — **area grouping** (ADR-006). All are
  derivations inside the existing keystone renderer (WP-1), reading ServiceSpec
  structure already present in the worktree's located contract(s). The
  area-grouping derivation is non-trivial (parse service boundaries from three
  sources, restructure every section per-area, single-vs-multi rule, OpenAPI
  tag fallback), comparable to the form-fields projection, which is why it
  counts as an ASR; the permission "who can do this" change is a small
  reordering of `enrich_permission`'s existing field reads and is **not** counted
  separately. sFPC unchanged at 7. ASR 11 is still well inside the tier-M band
  (6–15). **No tier shift (M→L did not occur).**
- File-count sanity check: the change adds ~1 Python step + ~2 endpoints +
  ~1 client surface. Consistent with tier M. No mismatch.

## Per-pillar addressable coverage

| Pillar | Coverage | Action |
|---|---|---|
| Form | Partial — the cockpit's hexagonal shape (port/adapter, route layering, `shared/` boundary) is established and authoritative. | Reuse it; the new step lives in `plugins/sulis/scripts/` (wpx convention), the new endpoints extend the existing router table. Fill only the new seams. |
| Armor | Partial — the cockpit already has timeouts, the spawn-not-exec rule, read-only inventory gate, error envelope. | The renderer is a deterministic local step (no network on the hot path); apply the same spawn/timeout discipline to the recreate call. |
| Proof | Partial — contract-test + fake-adapter + integration patterns exist. | The renderer keystone gets unit tests on a **rich, two-area** fixture (entities + lifecycle, constraints, workflows, stateEffects, the plain "who can do this" line with the raw code only in the technical block, area grouping + "areas covered" overview) **and a minimal single-area** fixture (auto-hide + no-area-heading assertion); the OpenAPI-fallback test asserts graceful degradation with no empty headings + tag-grouping; new endpoints get route tests; recreate path gets a fake. |

## Confirmed

- Tier: **M** (computed M at draft; re-confirmed M after each revision — latest
  after the founder review of the rendered mockup: sFPC 7 / ASR 11 / 6 ADRs,
  all inside tier M; no override requested).
- Target TDD length: ~250–400 lines for tier M with partial coverage. This TDD
  references the existing cockpit architecture rather than restating it.
