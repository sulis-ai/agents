# ADR-006 — The default view groups by service/area when a change spans more than one; a single-area change renders ungrouped

> Status: accepted · 2026-05-29 · change: cockpit-contract-preview
> Related: ADR-002 (governs *what* each default-view section shows; this ADR
> governs *how* sections are grouped when a change covers multiple areas),
> ADR-003 (generic per-change resolution — grouping is derived, never
> hard-wired), ADR-005 (ServiceSpec-first format precedence — the grouping
> source is the ServiceSpec structure).

## Context

A founder review of the rendered mockup raised that the view illustrated a
**single** service (one Platform, one operation set), but a real change's
contract can touch **many** services/areas. The platform's own service model
makes multi-area the normal case, not the exception:

- A `ServiceCatalog` (`core/service/types.py`) is *assembled from multiple
  `ServiceContribution`s*, each carrying its own `service_name`; the catalog
  tracks them in `contributions` and serialises as `@type: "ServiceCatalog"`.
- Operations in the assembled catalog are **keyed `{service_name}/{operation}`**
  (registry.py: `operation_key = f"{service_name}/{metadata.name...}"`; the
  routes layer filters on `key.startswith(f"{service}/")`). The prefix before
  the first `/` is the canonical area key.
- A worktree may also simply contain **more than one ServiceSpec document**
  (`@type: "ServiceSpec"`, each with its own single `name`).

The pre-revision flat layout rendered all operations, fields, entities, rules,
journeys, state-effects and what-changes in one undifferentiated list, so a
multi-area change read as a jumble with no sense of *which area each thing
belongs to*.

## Decision

When a change's contract covers **more than one service/area**, the default view
**groups every default-view section by area** under a clear area heading
(e.g. "Payments", "Notifications"). Each area carries its **own** operations /
form fields / entities + states / business rules / journeys / what-each-action-
changes / errors — all still **auto-trimmed** within the area (a section absent
for that area shows no heading). A short **"areas covered" overview** sits at the
top of the page when there is more than one area, naming each area (and,
optionally, a one-line count or description).

When a change's contract covers **exactly one area**, the view renders as **one
ungrouped block** — no area heading, no overview — exactly as the single-service
mockup does today. The single-area case must not pay a "redundant heading" tax.

### Where the grouping comes from (derivation, not hard-wiring — ADR-003)

The area key for each piece of content is derived from the ServiceSpec
structure, in this order:

1. **Multiple ServiceSpec sources in the worktree** → each ServiceSpec's `name`
   is an area; its operations/entities/etc. belong to that area.
2. **A `@type: "ServiceCatalog"` document** → the area for each operation is the
   prefix of its `{service_name}/{operation}` key (the segment before the first
   `/`); the `contributions` list and per-contribution `service_name` confirm
   the area set. Entities, errors, workflows and permissions are attributed to
   an area by the same `service_name` where the catalog carries it, and fall
   back to an "unattributed/shared" area only when no attribution exists.
3. **A single `@type: "ServiceSpec"`** (one `name`, un-prefixed operation keys)
   → exactly one area → ungrouped render.

The number of distinct areas after this derivation decides single-vs-multi:
`> 1` area ⇒ grouped + overview; `== 1` area ⇒ ungrouped, no heading.

The grouping is **generic** — it reads the same change record + worktree the
rest of the feature reads (ADR-003); no service name is embedded in code.

### OpenAPI fallback

OpenAPI carries no `service_name`/contribution structure. The fallback groups by
**OpenAPI tag** when tags are present (each tag is an area heading); when there
are no tags, it renders a **single ungrouped block**. The richer per-area
content (entities, lifecycle, journeys, state-effects, the plain "who can do
this" line) remains absent under OpenAPI per ADR-002's degradation — grouping
does not fabricate it.

## Why

- **Multi-area is the platform's normal shape (grounded).** The service model is
  explicitly an *aggregation of contributions keyed by service*. A renderer that
  assumed one service would mis-render the common case. Grouping by the same
  `service_name`/operation-key the platform itself uses keeps the view faithful
  to the contract's structure (no drift — the ADR-002 integrity property).
- **The founder judges "which area does this belong to".** A founder reviewing a
  change that touches Payments and Notifications needs to see each area's shape
  separately to judge it; a flat list hides the boundary. The "areas covered"
  overview answers the first question a reviewer asks of a multi-area change:
  *what does this touch?*
- **Single-area changes must stay tight (auto-trim's sibling).** Adding an area
  heading and an overview to a one-service change is the same kind of noise that
  empty section headings would be (ADR-002 auto-trim). The one-area-no-heading
  rule keeps a small change small — the page's structure tracks the change's
  actual breadth, just as auto-trim makes it track the change's depth.
- **Derivation, not configuration (ADR-003).** The area set is computed from the
  contract, never declared per change. This is the same anti-hard-wiring trust
  property the rest of the feature holds.

## Rejected alternatives

- **Always group, even for one area.** Rejected: a single-service change would
  carry a redundant "Platforms" heading and an "areas covered: Platforms"
  overview — noise that the founder review's sibling concern (Issue 1, jargon)
  warns against. One area ⇒ no heading.
- **Never group; one flat list regardless of area count.** Rejected by the
  founder review: it's the status quo that prompted the issue. A multi-area
  change reads as an undifferentiated jumble with no area boundary.
- **Group, but by entity rather than by service.** Rejected: entities don't map
  cleanly onto the founder's mental model of "areas of the product", and the
  platform's own structural key is `service_name`, not entity. Grouping by the
  platform's own key keeps the view a faithful projection.
- **A separate rendered page per area.** Rejected: the founder wants to judge
  the *whole change* in one pre-dispatch view; splitting it across pages defeats
  the review gate. One page, grouped sections, one overview.
- **Hard-coding the known platform service names.** Rejected: hard-wiring
  (ADR-003); rots as services are added; the area set must be derived from the
  contract present in each change's worktree.

## Consequence

- The `ContractModel` (the format-agnostic internal model, TDD §2.3) gains an
  **area attribution**: each operation/entity/workflow/error/permission carries
  the area it belongs to, derived once at parse time from the rules above. The
  section builders render **per area** when the area count is `> 1`, and a
  top-of-page **"areas covered" overview** is built from the area set.
- `compose_html` is handed an ordered list of **areas**, each with its ordered
  list of (auto-trimmed) section models, plus the overview model when areas
  `> 1`. The auto-trim rule (ADR-002) now applies *within each area* as well as
  across the page.
- The keystone test (TDD §4.1) gains a **two-service/two-contribution rich
  fixture**: it asserts the rendered HTML groups by area under headings, in
  order, with the "areas covered" overview present, and that each area's
  sections are scoped to that area. A **single-area fixture** asserts there is
  **no area heading and no overview**. The OpenAPI fallback asserts tag-grouping
  when tags are present and a single ungrouped block when they are absent.
- The visual-contract mockup (`mockups/CONTRACT-walkthrough.mockup.html`, UXD-14)
  shows a **two-area example** (a "Platforms" area and a "Notifications" area)
  so the grouping + overview + the per-operation "who can do this" line are all
  visible for sign-off.
- This is a **rendering/grouping** decision only. It does not change the
  source-of-truth, no-drift, or auto-trim rules; it does not change the
  Python `wpx-render-contract` step's contract, the generic per-change
  resolution, WP-2/3/4, or the events-out-of-scope decision.
