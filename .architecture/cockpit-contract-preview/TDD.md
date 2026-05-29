# TDD — cockpit "see the contracts before you go" preview

> Change: CH-01KSSV · feat · cockpit-contract-preview · closes #85
> Status: designed · Tier: M (see `SIZING.md`)
> Source spec: `.changes/cockpit-contract-preview.SPEC.md`
> (the "Design-stage founder decisions (2026-05-29)" section is binding)

This TDD **reuses the existing cockpit architecture** rather than restating it.
The cockpit's hexagonal shape — the `ChangeStoreReader` port, the
`SulisChangeStoreReader` adapter, the GET-only router table, the typed-error
envelope, the `shared/api-types.ts` wire contract, the read-only inventory gate
— is authoritative and unchanged. This document specifies only the new seams.

---

## 1. Problem & shape

The data contract and the visual/UI contract are produced at design time but
are inert files buried in a change worktree. The founder wants to *judge* the
work — before dispatch (a review gate) and again while testing — and today has
no surface to see them. A **rendered** contract eyeballed **before dispatch** is
defect-prevention, not just comfort.

The data contract is rendered **ServiceSpec-first** (ADR-005). The platform's
native, pervasive contract format is the **ServiceSpec** (JSON-LD, derived from
`@operation`-decorated handlers — see
`platform/architecture/SERVICE_SPECIFICATION.md` and
`platform/apps/api/sulis/core/service/types.py`). The ServiceSpec natively
carries the exact founder-legible fields this feature needs — per-operation
`userGuide` (summary / whenToUse / prerequisites / nextSteps), `permissions`
(with `description` / `grantsAccessTo` / `typicallyAssignedTo` definitions),
`audiences`, `errors` (user-facing message + cause + fix), `leadsTo`,
`stateEffects`; plus `entities` (properties, relationships, `lifecycle`,
`constraints`) and `workflows` (steps + successCriteria) — which OpenAPI does
not. The renderer therefore prefers ServiceSpec, falls back to OpenAPI where
only that exists, and falls back again to a raw contract + plain note. This is a
*rendering* precedence only — standardising Sulis's broader contract-FIRST
process on the ServiceSpec format is explicitly out of scope (ADR-005).

**The default view is the full picture (founder decision, 2026-05-29, binding).**
The founder-legible default register — everything *above* the "show technical
detail" toggle — renders the whole shape of the change: what it does, **the form
fields a user actually fills in** (labels, placeholders, input types, grouping,
validation rules, allowed options with human labels, and conditional show-when
logic), **what languages it's available in**, the things that exist and the states
they move through, the business rules, the step-by-step journeys, and what each
action changes. Operations that **run in the background** carry a small flag
alongside the sign-in flag; an operation **being retired** shows its sunset date
and replacement. Each section is **auto-hidden when the change's ServiceSpec
doesn't define it**, so a small change stays tight and a rich change shows
everything. Nothing is hand-written: every section is a projection of the
ServiceSpec's own fields (and the forms-annotation metadata carried inside its
property schemas), so it cannot drift from what is built (ADR-002).

**Form fields are the priority surface (founder decision, 2026-05-29, binding).**
The single most founder-judgeable question is *"does the form ask the right
things, with the right labels and the right rules?"* The ServiceSpec carries this
natively but not as a separate block: each entity's `properties` and each
operation's `input` schema are JSON-Schema objects whose per-property metadata
(`label` / `description` / `placeholder` / `group` / `order` / `readonly` /
`hidden` from `DisplayMetadata`; `min_length` / `max_length` / `min_value` /
`max_value` / `pattern` / `enum` / `error_message` from `ValidationMetadata`;
and the `x-display` / `x-enum-labels` / `x-dependent-enum` / `x-visibility`
extensions injected by `core/forms/annotations.py`) describes the actual form.
The renderer projects these into a **readable "fields" view** — never a raw
schema dump.

Four pieces, in build order:

| WP | Piece | Primitive |
|---|---|---|
| WP-1 | `wpx-render-contract` data-contract renderer (**keystone**) | EXPAND-Create |
| WP-2 | UI-contract renderer (reuses design-system VIEWER) | EXPAND-Create |
| WP-3 | cockpit wiring: per-change links + review-gate timing | EXPAND-Create + frontend |
| WP-4 | recreate-on-demand for shipped changes | EXPAND-Create (composes `sulis-change recreate`) |
| (gate) | visual-contract WP for the CONTRACT.html default view | `kind: contract` |

Decisions live in ADR-001..006. The ServiceSpec-first format precedence is
ADR-005; the founder-legible default view + technical toggle is ADR-002 (which
also, per its Revisions 5 + 6, shows each operation's permission in the default
view in **readable** form — a labelled **readable permission line** (the meaning,
from `description`) **and** a **"Who can do this"** line (from
`typicallyAssignedTo`) — **paired with the actual permission code**
(`platform.platforms:create`) and **the actual operation identifier**
(`{service}/{operation}` key / `method_name`), all in the default view, the
readable form primary and the actual value as a paired monospace secondary —
Rev 6 supersedes Rev 5's toggle-only code); **grouping the default view by service/area when a change spans more
than one** is ADR-006. The founder-facing default view is mocked with real
tokens at `mockups/CONTRACT-walkthrough.mockup.html` (UXD-14 gate), which now
shows a **two-area** example so the grouping + the "areas covered" overview are
visible.

---

## 2. Form — structural integrity

### 2.1 Where each piece lives

- **Renderers** are `wpx-*` Python steps in `plugins/sulis/scripts/`
  (`wpx-render-contract`, and the UI render either as a subcommand or a sibling
  `wpx-render-ui`). They are stdlib-first, build on `_wpxlib.py`, emit the
  standard `emit_ok`/`emit_error` JSON, and are dispatched via the `wpx` shim.
  See ADR-001.
- **Cockpit endpoints** extend the existing router table in
  `apps/cockpit/server/app.ts`. They are GET-only (read-only inventory gate
  preserved). They resolve a change generically via `requireChange` +
  `resolveWorktreeRoot` — the same path tree/file/diff already use.
- **Cockpit client** gains per-change "open data contract / open UI" affordances
  on the existing change surfaces (`Dashboard` / `ThreadView`).

### 2.2 Dependency direction (unchanged invariant)

The renderer's only inputs are a **worktree path** + the **change record**. It
reaches the change store only through facts already on the record
(`worktreePath`, `branch`, `shipped_sha`) — never by hard-wiring a change
(ADR-003). The cockpit reaches the renderer's *output* (files in the worktree),
not the renderer. No new path escapes the `apps/cockpit/` boundary.

### 2.3 The renderer's internal seams (WP-1)

The parser has **two front-ends feeding one common internal model**
(`ContractModel`): a ServiceSpec (JSON-LD) front-end as primary and an OpenAPI
front-end as secondary (ADR-005). Everything downstream of `ContractModel` —
walkthrough, "What it does" list, flags, example, compose — is format-agnostic.

```
wpx-render-contract --worktree <path> [--out <path>]
  ├── locate_contracts(worktree)      → list[(Path, Format)]  (generic glob + content sniff; ADR-003/005)
  │                                      Format ∈ {servicespec, openapi, raw}, in precedence order
  ├── parse_servicespec(path)         → ContractModel   (PRIMARY: operations w/ userGuide,
  │                                      permissions, audiences, errors, leadsTo, stateEffects;
  │                                      entities w/ lifecycle + constraints; workflows;
  │                                      permission definitions)
  ├── parse_openapi(path)             → ContractModel   (SECONDARY: operations, schemas, examples,
  │                                      errors-from-responses; entities/lifecycle/constraints/
  │                                      workflows/stateEffects/permission-defs absent → auto-hidden)
  ├── synthesise_example(schema)      → dict            (when the contract has no example)
  ├── build_form_fields(schema)       → list[FormField] (PRIORITY: projects a property/input schema
  │                                      into founder-legible fields — label, placeholder, input type,
  │                                      group/order; validation rules (required, min/max length+value,
  │                                      pattern, enum); human enum labels (x-enum-labels); show-when
  │                                      (x-visibility) + depends-on (x-dependent-enum). NOT a raw dump)
  ├── derive_auth_flags(operation)    → AuthFlags       (needs_signin from userGuide.prerequisites +
  │                                      non-empty permissions; permission code(s) from permissions[];
  │                                      runs_in_background from operations.{op}.async)
  ├── enrich_permission(code, defs)   → PermissionView  (the DEFAULT view shows THREE values
  │                                      on the operation's row: (a) meaning = description, rendered
  │                                      as a labelled readable permission line ("Permission: lets you
  │                                      create platforms"); (b) who_can = typicallyAssignedTo
  │                                      ("Who can do this: Platform administrators"); (c) the ACTUAL
  │                                      code (platform.platforms:create) shown as a paired monospace
  │                                      secondary next to the meaning — all in the DEFAULT view.
  │                                      ADR-002 Revision 6: Rev 5 kept the code toggle-only; Rev 6
  │                                      brings it into the default view paired with its meaning.
  │                                      No permission defn → "Requires sign-in" + the actual code
  │                                      (the code is contract-carried even when its definition is
  │                                      absent). No required permission → "anyone".)
  ├── derive_retirement(operation)    → RetirementView  (deprecated + sunsetDate ("until {date}") +
  │                                      replacementOperation ("use {X} instead"); absent → no badge)
  ├── derive_languages(ContractModel) → LanguageView    (default_locale + supported_locales, from the
  │                                      spec's i18n block; absent / single "en" → may auto-trim)
  ├── build_walkthrough(ContractModel)→ WalkthroughModel (hero scenario from a chosen operation's
  │                                      userGuide + output, sequenced via leadsTo/workflows)
  ├── build_entity_views(ContractModel)→ list[EntityView] (name + description, properties → form
  │                                      fields (build_form_fields), lifecycle states → transition
  │                                      chain, constraints → plain rules)
  ├── build_workflow_views(ContractModel)→ list[WorkflowView] (steps + successCriteria as journeys)
  ├── build_state_effects(ContractModel)→ list[ActionEffect] (per operation: which entity moves to
  │                                      which state, linked to the entity lifecycle above)
  ├── derive_areas(ContractModel)     → list[AreaView]  (ADR-006: attribute each operation/entity/
  │                                      workflow/error/permission to a service/AREA. Sources, in order:
  │                                      multiple ServiceSpec docs → each spec.name is an area; a
  │                                      @type:ServiceCatalog → area = prefix of the {service}/{op}
  │                                      operation key, confirmed by `contributions` + per-contribution
  │                                      service_name; a single @type:ServiceSpec → exactly one area.
  │                                      Result: ordered areas; >1 ⇒ grouped + overview, ==1 ⇒ ungrouped)
  ├── render_technical(path, fmt)     → str             (self-contained HTML fragment behind the
  │                                      toggle: full ServiceSpec JSON-LD render, or Redoc for
  │                                      OpenAPI; holds rateLimits, idempotent flag, bindings
  │                                      host/basePath/routing, raw input/output JSON schemas,
  │                                      error→relatedDocs links. NOTE the actual permission codes
  │                                      and operation identifiers are now in the DEFAULT view
  │                                      paired with their readable forms — ADR-002 Rev 6; the
  │                                      JSON-LD here still contains them in context.)
  └── compose_html(areas…)            → CONTRACT.html (+ manifest)
                                         when areas > 1: renders an "areas covered" overview, then one
                                         grouped block per area under a heading, each block's sections
                                         auto-trimmed within the area. When areas == 1: one ungrouped
                                         block, NO area heading, NO overview (ADR-006). Auto-trims every
                                         default section absent from the (area's) model.
```

**What stays behind the "show technical detail" toggle (not in the default
view).** `rateLimits`, the `idempotent` flag, `bindings` (host / basePath /
routing), raw `input`/`output` JSON schemas (the *raw* schema — distinct from
the founder-legible **form-fields** projection, which is in the default view),
error `relatedDocs` links, and the full ServiceSpec JSON-LD (or Redoc render for
OpenAPI). **The actual permission code and the actual operation identifier are
NOT toggle-only (ADR-002 Revision 6):** both are shown in the default view
paired with their readable forms (the permission code next to the readable
"Permission: …" meaning; the `{service}/{operation}` key / `method_name` next to
the readable action description). Rev 4 had demoted the code into the toggle and
Rev 5 left it there; Rev 6 supersedes that. The default view surfaces the
founder-legible *projection* of the contract **plus the actual values paired
with it**; the toggle holds the remaining raw, engineer-facing detail.

**Moved into the default view by the founder decision (2026-05-29).** Two things
that previously lived behind the toggle are now plain default-view facts:

- **Languages (i18n).** `default_locale` + `supported_locales` (the spec's `i18n`
  block) render as a one-line plain fact ("Available in: English, Spanish") in
  the default view — `derive_languages`. (A single-locale `["en"]` spec may
  auto-trim this line as uninformative; see auto-trim rule.)
- **Form fields.** The founder-legible projection of each entity's `properties`
  and each operation's `input` schema (`build_form_fields`) is a default-view
  section. The *raw* JSON schema stays behind the toggle; the readable fields
  view does not.

A `deprecated` operation gets a small **"being retired"** badge in the default
view, enriched with its **sunset date** ("being retired — until {date}") and
**replacement** ("use {X} instead") when the spec carries `sunsetDate` /
`replacementOperation`. An operation with `async: true` gets a small
**"runs in the background"** flag in the default view, alongside the sign-in
flag (`derive_auth_flags.runs_in_background`).

The `ContractModel` is the format-agnostic internal model. It carries:

- **operations** — per operation: `name`, `description`, `summary`
  (`userGuide.summary`), `when_to_use`, the **operation identifier** — the
  `{service}/{operation}` key and/or `method_name` (`OperationMetadata.method_name`,
  emitted as `"method"`), shown in the default view as a paired monospace
  secondary next to the readable action description (ADR-002 Rev 6) —
  `needs_signin` + `runs_in_background`
  (from `async`) + `permission_views` (the enriched permission, below — whose
  default-view face is the **readable permission line** (meaning) **plus** the
  "Who can do this" line **plus the actual permission code** as a paired
  secondary, all in the default view, ADR-002 Rev 6),
  `form_fields` (the founder-legible projection of the
  operation's `input` schema), `example` (input/output, real or synthesised),
  `leads_to`, `next_steps`, `state_effects`, `retirement` (deprecated + sunset +
  replacement when present), `area` (the service/area it belongs to, derived per
  ADR-006 — the `{service}/{op}` key prefix, the owning ServiceSpec's `name`, or
  the single area).
- **entities** — per entity: `name`, `description`, `form_fields` (the
  founder-legible projection of the entity's `properties`), `relationships`,
  `lifecycle` (the ordered/linked state names), `constraints`, `area` (ADR-006).
- **workflows** — per workflow: `name`, `steps`, `success_criteria`, `area`
  (ADR-006).
- **areas** — the ordered set of distinct service/areas across the model
  (ADR-006). When more than one, `compose_html` renders a grouped view with an
  "areas covered" overview; when exactly one, it renders ungrouped with no area
  heading.
- **permission_defs** — per permission code: `description`, `grants_access_to`,
  `typically_assigned_to` (the platform's `permissions` block; ServiceSpec only).
- **errors** — the contract-level catalog (`message` / `cause` / `fix`).
- **languages** — `default_locale` + `supported_locales` (the spec's `i18n`
  block; default `"en"` / `["en"]`).

**Form fields (founder decision — priority).** A `FormField` is the readable
projection of one JSON-Schema property. It carries: `name`, `label`
(`x-display.label` / `DisplayMetadata.label`, falling back to a humanised
property name), `description`, `placeholder`, `input_type`
(`x-display.inputType`, else inferred from JSON-Schema `type` / `format`),
`group` + `order` (for sectioning/ordering the fields a user fills in),
`required` (from the schema's `required` list), and validation rules —
`min_length` / `max_length` / `min_value` / `max_value` / `pattern` (surfaced as
a plain "must look like…" hint, not the raw regex where a friendlier form
exists), `enum` **paired with its human labels** (`x-enum-labels` /
`EnumLabels`), `error_message`, plus conditional logic: `visible_when`
(`x-visibility`) and `depends_on` (`x-dependent-enum`: this field's options
depend on another field's value). `readonly` / `hidden` properties
(`DisplayMetadata`) are marked or omitted accordingly — a `hidden` field is not
shown to the founder. `build_form_fields` reads every one of these defensively
(missing key → that detail simply absent on the field).

ServiceSpec populates the model from native fields. OpenAPI populates the subset
it carries (operations, schemas, examples, errors-from-responses) and leaves the
rest **absent** — not empty-with-headings.

**Permission display — show the readable permission + who-can + the actual code
in the default view (founder decision 1, revised by ADR-002 Revisions 5 + 6).**
The default view shows the permission in **readable** form **and** its actual
code — the readable meaning is primary, the actual code is its paired secondary.
`enrich_permission` joins each operation's permission code to the spec's
top-level `permissions` definition and produces a `PermissionView` whose
**default-view face is three values on the operation's own row**:

- a **readable permission line** — the permission's plain-English *meaning* from
  `description`, rendered as a clearly-labelled line ("Permission: lets you
  create platforms"), so the founder can *see what permission the action
  requires*; and
- a **"Who can do this" line** — *who* from `typicallyAssignedTo` ("Who can do
  this: Platform administrators"), with `grantsAccessTo` available for
  expandable detail; and
- the **actual permission code** (`platform.platforms:create`) — shown as a
  paired monospace secondary next to the readable meaning, **in the default
  view** (ADR-002 Revision 6).

All three are visually tied to that operation (not a separate global block),
keeping the action→permission relationship legible: the readable meaning is
primary and the actual code is its paired secondary. The same operation row
also carries the **actual operation identifier** (`{service}/{operation}` key /
`method_name`) paired with the readable action description (ADR-002 Revision 6).
This is ADR-002 Revision 6: Rev 4 demoted the *code* into the toggle, Rev 5
restored the readable permission *meaning* to the default view but kept the code
toggle-only, and Rev 6 — after a founder reviewing the Rev-5 mockup asked to
*also* see the actual values — brings the actual permission code (and the actual
operation identifier) into the default view paired with their readable forms.
The readable form stays primary; the actual value is a secondary, not a code
dump. Degradation:

- **No permission definition for a required code** (or OpenAPI fallback): the
  readable line degrades to a plain **"Requires sign-in"** — no invented
  permission meaning or "who" prose — but the **actual code is still shown**
  when a code is required, since the code itself is contract-carried.
- **No required permission at all**: the operation shows **"No sign-in /
  anyone"** exactly as today.

The "Needs sign-in" flag is kept alongside the readable permission + "Who can do
this" lines.

**Grounding caveat the renderer MUST tolerate (load-bearing).** The platform's
`ServiceSpec.to_jsonld()` (`core/service/types.py`) emits `entities.lifecycle`
as a flat `list[str]` of state names and `entities.constraints` as a
`list[dict]`, and — at the time of writing — does **not** emit per-operation
`leadsTo` or `stateEffects` in that serialiser, even though the schema doc and
`OperationNavigation.to_dict()` (`core/service/workflow.py`) define them (the
latter with `toState` / `fromStates` keys). The renderer therefore treats
`lifecycle`, `constraints`, `leadsTo`, `stateEffects`, `workflows`, and the
`permissions` definitions as **independently optional** and reads `stateEffects`
from either the operation object *or* a navigation block. This is the technical
reason auto-trim is mandatory rather than cosmetic: the platform's own output
varies field-by-field, so the renderer must render only what is present and
hide the rest. Each accessor is defensive (missing key → section absent).

The same field-by-field tolerance governs **form fields**. The per-property
form metadata is carried *inside* each property's JSON-Schema object —
`entities.{E}.properties.{p}` and `operations.{op}.input.properties.{p}` — as
`DisplayMetadata` keys plus the `x-display` / `x-enum-labels` / `x-dependent-enum`
/ `x-visibility` extensions (`core/forms/annotations.py`). A property may carry
all of them, some, or none: a bare-string property with no `Display` annotation
still renders as a field (humanised name + inferred input type), and richer
properties render richer field cards. `build_form_fields` reads each key
defensively. **`async` and the `i18n` block are reliably emitted** by
`ServiceSpec._operation_to_dict` and `to_jsonld` respectively (so the background
flag and the languages line are stable), whereas `deprecated` /
`sunsetDate` / `replacementOperation` are emitted only when set — all read
defensively.

**Auto-trim rule (MUST).** Every default-view section
(`build_form_fields`, `build_entity_views`, `build_workflow_views`,
`build_state_effects`, the errors surface, the languages line, even the
"What it does" list) renders **only if the source ServiceSpec carries content
for it**. `compose_html` is handed an ordered list of section models and skips
any that is empty/absent — producing **no empty headings**. A minimal change
with one operation, no form fields, no entities and no workflows shows a tight
page; a rich change shows everything. Specifically: no form-fields section when
no property/input schema carries any field; no languages line for a default
single-locale spec; no background flag on a synchronous operation; no
"being retired" badge on a live operation.

**Area grouping (MUST when areas > 1; ADR-006).** A change's contract can span
**more than one service/area**; a real change is not always a single service.
`derive_areas` attributes each operation/entity/workflow/error/permission to a
service/area — from multiple ServiceSpec sources (each spec's `name`), from a
`@type: "ServiceCatalog"` document's `{service}/{operation}` key prefixes
(confirmed by its `contributions` + per-contribution `service_name`), or from a
single `@type: "ServiceSpec"` (one area). When the derived area count is
**greater than one**, `compose_html` renders a short **"areas covered"
overview** at the top, then **one grouped block per area** under a clear heading
(e.g. "Payments", "Notifications"), each block carrying that area's own
operations / form fields / entities + states / rules / journeys /
what-each-action-changes / errors — **all still auto-trimmed within the area**.
When the area count is **exactly one**, the view renders as **one ungrouped
block with no area heading and no overview** (no redundant-heading tax). Grouping
is a *projection of the contract's own structure* (ADR-003 — derived, never
hard-wired), so it is part of the same no-drift integrity property as auto-trim:
the page's *breadth* tracks the change's actual area count, just as auto-trim
makes its *depth* track the change's richness. OpenAPI fallback groups by **tag**
when tags are present, else a single ungrouped block (ADR-006).

**EVENTS — deliberately out of scope (recorded).** The platform has domain
events (`platform/apps/api/sulis/.../domain/events/`), but the **ServiceSpec
contract** (`core/service/types.py` → `to_jsonld()`) does **not** carry them.
Rendering events would require scraping the codebase outside the contract,
breaking the no-drift guarantee that is the whole point of this feature. Events
are therefore excluded, pending a contract-format extension that is tracked
separately (recorded in ADR-005's "Out of scope"). The contract-native
approximation of "what happens as a result of an action" — `stateEffects`
("what each action changes") — is already in the default view (§above).

Degradation (ADR-002/003/005): zero contracts found → emit a "no contract found
— raw contract + plain note" page from whatever data-contract file exists; never
break. OpenAPI-only → derive what those fields allow (operations, schemas,
examples, errors-from-responses, and a **basic form-fields view** from the
request-body schema — OpenAPI carries field `type` / `format` / `required` /
`enum` / `pattern`, but **not** the `x-display` labels/placeholders/groups, the
`x-enum-labels` human option labels, or the `x-visibility` / `x-dependent-enum`
conditional logic, so the fields degrade to name + type + basic rules; and the
readable permission line, the "Who can do this" line, and the actual permission
code are all **absent** because OpenAPI carries no `permissions` block at all —
there is no permission code to show and none is fabricated; ADR-002 Rev 6's
"show the actual code in the default view" applies only where the contract
carries one) and
auto-hide the richer sections (entities/lifecycle, constraints, workflows, state
effects, permission definitions, background flag, languages); group by **tag**
when the OpenAPI doc carries tags, else a single ungrouped block (ADR-006); show
a plain "this contract carries less guidance" note. More than one contract →
render each, one section per contract, in precedence order (and the area
grouping of §"Area grouping" applies across them).

### 2.4 The UI renderer (WP-2)

Reuses the **design-system skill's VIEWER** generation pointed at the change's
visual contract / tokens, producing `UI.html`. Where the change has no visual
contract (non-user-facing), it emits **nothing + a note** recorded in the
manifest so the cockpit can show "no UI contract for this change" rather than a
broken link.

---

## 3. Armor — operational hardening

The hot path here is local file I/O and subprocess invocation, not network, so
the Armor surface is small but specific:

- **Subprocess discipline.** Any shell-out (the recreate call in WP-4; the Redoc
  CLI invocation inside the renderer) uses `spawn`/`subprocess.run` with an
  **argv array, `shell=false`, and a bounded timeout** — matching the cockpit's
  `SulisChangeStoreReader` contract and `wpx-worktree`'s `_run`. No string
  command lines.
- **Read-only invariant preserved.** New cockpit endpoints are `router.get`
  only; the read-only inventory test must still pass. Rendering/recreate are
  *steps*, not in-process server work (ADR-001/004).
- **Bounded recreate.** The recreate-on-demand call (WP-4) has its own timeout
  and a typed failure → the cockpit degrades to "couldn't reach this shipped
  change's contracts" rather than hanging a request.
- **No drift = an integrity property.** Rendering strictly from the contract's
  own fields/tokens (never hand-copied) is the feature's core guarantee. The
  full-picture founder-legible default view — the "What it does" list, the
  **form fields** a user fills in (labels, placeholders, input types, grouping,
  validation rules, human enum option labels, and show-when/depends-on logic),
  the **languages** it's available in, the **sign-in flag + the readable
  permission line (meaning, from `description`) + the "Who can do this" line**
  (from `typicallyAssignedTo`) **+ the actual permission code** and **the actual
  operation identifier** (`{service}/{operation}` key / `method_name`), all in
  the default view paired with their readable forms (ADR-002 Rev 6 — Rev 5's
  toggle-only code superseded), the **background-action**
  flag, the entities + their **lifecycle** states, the **business rules** (entity
  constraints), the **step-by-step journeys** (workflows), **what each action
  changes** (state effects), the **retirement** detail (sunset + replacement),
  the walkthrough, the example, and — when the change spans more than one area —
  the **per-area grouping + "areas covered" overview** (ADR-006) — is derived
  **entirely** from the ServiceSpec's own `entities` (incl. their `properties`
  and the form metadata carried inside them) / `operations` (`input` schemas,
  `async`, `deprecated` + `sunsetDate` + `replacementOperation`, and the
  `{service}/{op}` key that gives the area) / `userGuide` / `leadsTo` /
  `stateEffects` / `workflows` / `permissions` / `audiences` / `errors` / `i18n`,
  so it cannot diverge from what is built. The auto-trim rule **and the
  area-grouping rule** (§2.3) are both part of the integrity property: a section
  the spec doesn't define is *absent* (never stubbed), and the area boundaries
  are the contract's own service boundaries (never invented). The unit tests on
  the rich fixture (now **two services/areas**), the minimal-fixture auto-hide
  assertion, and the single-area no-heading assertion are what enforce all of
  this (Proof §4).
- **Path safety.** Spec discovery and artifact writes stay inside the resolved
  worktree root (reuse `safeJoin`/`resolveWorktreeRoot` semantics); reject
  traversal shapes, as the existing file route does.

No secrets, no PII, no new external service. Observability: the steps emit the
standard wpx JSON result (machine-readable success/failure + what was produced).

---

## 4. Proof — verification protocol

### 4.1 Keystone unit test (WP-1, test-first)

Two fixtures, one keystone test file. Both are committed ServiceSpec (JSON-LD)
documents under the renderer's test dir, shaped per
`platform/apps/api/sulis/core/service/types.py` `ServiceSpec.to_jsonld()`.

**Fixture A — rich, MULTI-AREA contract (two services/contributions; ADR-006).**
The rich fixture now spans **two service areas** — modelled either as two
ServiceSpec documents in the fixture worktree, or as one `@type: "ServiceCatalog"`
whose operations are keyed `{service}/{operation}` across two `service_name`s
(e.g. a **"Platforms"** area and a **"Notifications"** area), with its
`contributions` naming both. Across the two areas it carries: ≥3 **operations**
total (each with `userGuide`, `permissions`, `audiences`, `errors`; at least one
with `leadsTo` and `stateEffects`; **one with `async: true`**; **one
`deprecated` with a `sunsetDate` AND a `replacementOperation`**); top-level
**`permissions` definitions** (`description`, `grantsAccessTo`,
`typicallyAssignedTo`) for the codes the operations use; ≥1 **entity** (in at
least one area) whose **`properties`** carry real form metadata — at least one
property with a **`label`** + **`placeholder`** + **`group`**, at least one with
**validation** (`min_length`/`max_length` or `pattern` and a `required` mark),
at least one **`enum` property paired with `x-enum-labels`** (human option
labels), and at least one property with an **`x-visibility`** show-when
condition; the entity also has a multi-state **`lifecycle`** (e.g.
`["draft", "active", "suspended"]`) and ≥1 **`constraint`**; at least one
**operation `input`** schema that likewise carries form metadata; ≥1
**`workflow`** with `steps` + `successCriteria`; **`supported_locales`** with
more than one locale (e.g. `["en", "es"]`). Against the rendered
`CONTRACT.html`, assert it:

0. **groups the default view by area** (ADR-006): the rendered HTML carries a
   heading for **each** area (e.g. "Platforms" and "Notifications"), **in order**,
   with each area's operations / fields / entities / rules / journeys /
   state-effects scoped to that area's block; and a short **"areas covered"
   overview** appears at the top naming both areas. (The area set is derived from
   the `{service}/{operation}` key prefixes / the two ServiceSpec `name`s, not
   hard-wired.)
1. references each of the spec's **operations** (the "What it does" list is
   complete, across both areas), AND surfaces, per operation, in the default
   founder-legible view, **the actual operation identifier** — the
   `{service}/{operation}` key (e.g. `platform/create-platform`) and/or the
   operation's `method_name` (e.g. `create_platform`) — paired with the readable
   action description on the operation's row (ADR-002 Revision 6: readable
   description primary, actual identifier as a paired monospace secondary);
2. surfaces, per operation, **all three** in the default founder-legible view,
   on the operation's own row, alongside the **sign-in flag**:
   - the **readable permission line** — the permission's plain-English
     *meaning* derived from `spec.permissions[code].description` (e.g.
     "Permission: lets you create platforms"), rendered as a clearly-labelled
     line so the founder can *see what permission the action requires*; AND
   - the **"Who can do this" line** derived from the permission's
     `typicallyAssignedTo` (e.g. "Who can do this: Platform administrators"); AND
   - the **actual permission code** (e.g. `platform.platforms:create`) shown
     **in the default view**, paired with the readable meaning as a monospace
     secondary (ADR-002 Revision 6 — Rev 5's toggle-only code is superseded);

   The assertion checks **both** the readable permission meaning **and** the
   actual permission code are present in the default-view DOM (ADR-002 Revision
   6: the meaning is primary and the code is its paired secondary, both in the
   default view; Rev 5's "code only in the toggle" assertion is replaced). For
   an operation with **no required permission**, the row instead shows "No
   sign-in / anyone";
3. renders the **form fields** a user fills in, in a readable (non-raw-schema)
   form: the field **label** and **placeholder** (not the bare property name),
   the **input type**, the **grouping**, the **validation rules** (the
   `required` mark and at least the min/max-length or pattern rule rendered as a
   plain hint), the **allowed options with their human labels** (the enum value
   *and* its `x-enum-labels` text), and the **show-when** condition
   (`x-visibility`) surfaced as conditional logic — for both an entity's
   `properties` and an operation's `input`;
4. renders the **entities** — each entity's name + description, and its
   **lifecycle** rendered as a founder-legible state chain (e.g.
   `draft → active → suspended`);
5. renders the entity **constraints** as plain **business rules**;
6. surfaces the **languages** line — the `supported_locales` rendered as a plain
   default-view fact (e.g. "Available in: English, Spanish"), **in the default
   view, not the technical toggle**;
7. renders the **workflows** as readable step-by-step **journeys** (steps +
   successCriteria);
8. renders **what each action changes** — the operation **`stateEffects`**,
   each naming the entity and the state it moves to, referencing the same
   lifecycle states surfaced in (4);
9. flags the **`async` operation** with a **"runs in the background"** indicator
   in the default view, alongside the sign-in flag;
10. contains the **synthesised worked walkthrough** (the hero scenario derived
    from a chosen operation's `userGuide` + `output`, sequenced via
    `leadsTo` / `workflows`);
11. contains a concrete **example request/response** (from `input`/`output`,
    real example when present, else synthesised from the schema);
12. surfaces the contract's **errors** (each with its user-facing `message`);
13. shows the **"being retired" badge** on the deprecated operation in the
    default view, **enriched with its sunset date** ("until {sunsetDate}") **and
    its replacement** ("use {replacementOperation} instead");
14. embeds the technical region (the full ServiceSpec JSON-LD render) behind the
    toggle, and keeps rateLimits / idempotent flag / bindings / raw schemas /
    error relatedDocs links **inside** that toggle, **not** in the default view
    — while the **form-fields projection**, the **languages line**, the
    **background flag**, the **retirement detail**, **the readable permission
    line, the "Who can do this" line, the actual permission code**, and **the
    actual operation identifier** are all in the **default view** (ADR-002
    Revision 6). The actual permission code and the actual operation identifier
    being present in the default view is the counterpart of assertions 1 and 2;
    Rev 5's "raw code only in the toggle" assertion is **superseded** — the code
    now appears in the default view paired with its readable meaning (the full
    ServiceSpec JSON-LD in the toggle still contains the code in context, but the
    default view no longer hides it).

**Fixture B — minimal, SINGLE-AREA ServiceSpec (auto-hide + no-heading
assertion).** A single `@type: "ServiceSpec"` (one `name` → exactly one area)
with a single operation with a `userGuide` and an `input`/`output` of **plain
typed properties with no form metadata** (no `label` / `placeholder` / `enum` /
`x-visibility`), no `async`, not `deprecated`, a default single-locale
(`["en"]`), and **no** `entities`, **no** `workflows`, **no** `stateEffects`,
**no** `constraints`. Against its rendered `CONTRACT.html`, assert:

15. the "What it does" list and example **are** present;
16. the entities/lifecycle, business-rules, journeys, and what-each-action-changes
    sections are **absent**; the **languages line is absent** (single default
    locale), there is **no "runs in the background" flag** and **no "being
    retired" badge** — and specifically that there is **no empty heading** for
    any of them (the auto-trim rule: assert the section headings' text does not
    appear in the output);
17. the operation's plain `input` still renders as **basic fields** (name +
    inferred input type), with **no** rich form-metadata chrome (no enum-option
    list, no show-when block) — proving the form-fields view degrades gracefully
    rather than fabricating metadata the spec doesn't carry;
18. **single-area renders ungrouped (ADR-006):** there is **no area heading** and
    **no "areas covered" overview** — the change is one area, so it renders as a
    single ungrouped block with no redundant heading (assert the overview text
    and any area-heading chrome do not appear).

This is the keystone Red: write both fixtures and assertions, see them fail,
then build the renderer.

### 4.2 OpenAPI-fallback + degradation tests

- **OpenAPI-fallback fixture** (retained/added): a fixture worktree with **only
  an OpenAPI document** (whose request body carries `type` / `format` /
  `required` / `enum` / `pattern`, but none of the `x-display` / `x-enum-labels`
  / `x-visibility` extensions) → page renders what those fields allow — the
  **operations**, a **basic form-fields view** (field name + inferred type +
  required/enum/pattern rules only), a concrete **example** (from `examples` or
  synthesised), and errors derived from responses — embeds the Redoc render
  behind the toggle, and shows the plain "this contract carries less guidance"
  note. The test asserts **graceful degradation**: the richer founder-legible
  sections (entities + lifecycle, business rules, step-by-step journeys,
  what-each-action-changes, permission definitions, **the languages
  line, the background flag**) are **absent**, the **"Who can do this" line is
  absent** (OpenAPI has no permission definitions — no fabricated "who", and no
  raw code in the default view either), and the form fields render **without**
  human enum labels or show-when logic, all with **no empty headings** — the
  same auto-trim assertion as Fixture B, applied to the format boundary.
  (OpenAPI carries none of `userGuide` / `permissions` definitions /
  `entities.lifecycle` / `constraints` / `workflows` / `stateEffects` /
  `async` / the `i18n` block / the `x-*` form extensions.)
- **OpenAPI tag-grouping (ADR-006).** Two variants: (a) an OpenAPI doc **with
  tags** → the page **groups operations by tag** (each tag an area heading) with
  the "areas covered" overview when there is more than one tag; (b) an OpenAPI
  doc **with no tags** → a **single ungrouped block, no area heading**. Assert
  both — and assert the grouping never fabricates the richer per-area content
  (entities/lifecycle/journeys/"Who can do this") that OpenAPI doesn't carry.
- Fixture worktree with **no contract at all** → page renders the raw contract +
  plain note; no exception.
- Fixture with **two contracts** → both appear, in precedence order
  (ServiceSpec ahead of OpenAPI).
- Change with **no visual contract** (WP-2) → manifest records "none"; cockpit
  shows the note, not a broken link.

### 4.3 Cockpit endpoint tests

Route tests (supertest, the existing pattern) for the new GET endpoints:
artifact-present → served; worktree-absent-but-recreatable → recreate invoked
then served (recreate stubbed via a fake); absent-and-not-recreatable → 404 /
typed note. A `FakeChangeStoreReader`-style fake covers the recreate seam so
integration tests use a real adapter shape, not ad-hoc mocks (MEA-09).

### 4.4 Anti-hard-wiring acceptance (release gate, ADR-003)

Open the cockpit, **walk every in-flight change**, confirm each surfaces its
**own** data + UI contracts. This is an explicit release-acceptance step, not a
single-change smoke test.

### 4.5 Visual-contract gate (UXD-14)

The CONTRACT.html **full-picture** default view is a user-facing surface → a
`kind: contract` (`contract_type: visual`) WP carries the real-token mockup at
`mockups/CONTRACT-walkthrough.mockup.html`. The mockup shows a **two-area
example** (a "Platforms" area and a "Notifications" area; ADR-006) with the
**"areas covered" overview** at the top and one grouped block per area, so the
grouping is visible for sign-off. Within each area it shows the full default
register — what-it-does (with the **readable permission line** (the meaning)
*and* the **"Who can do this" line** *and* the **actual permission code** paired
with the meaning, the **actual operation identifier** paired with the action
description, plus the **background-action flag**; all in the default view —
ADR-002 Rev 6), the **form fields** a user fills in (with a labelled field, a
validation rule, a human-labelled enum, and a show-when field), the **languages**
line, entities + lifecycle, business rules, a workflow journey,
what-each-action-changes, the **enriched retirement badge** (sunset +
replacement), the errors surface, and the collapsed technical toggle — so the
WP-3 frontend work declares `visual_contract:` against it and `review` verifies
the shipped render matches. The auto-trim behaviour (sections present only when
the spec carries them) **and the single-area-no-heading behaviour** are proven
by the unit tests (§4.1 Fixture B, §4.2), not by the mockup.

---

## 5. Timing — review gate + on-demand (WP-3)

Two moments, one renderer:

- **Design-time (pre-dispatch review gate):** after `decompose`, before
  `run-all` dispatch, render the in-flight change's `CONTRACT.html` + `UI.html`
  so the founder can eyeball them before anything is built on the contract.
- **On-demand (the testing moment):** the cockpit's per-change links render (or
  re-render) the artifacts when the founder clicks, recreating a tidied
  worktree first if needed (WP-4). The founder never navigates a worktree.

---

## 6. Reuse ledger (what we do NOT build)

| Need | Reused thing |
|---|---|
| ServiceSpec model + JSON-LD shape (operations, entities, lifecycle, constraints, workflows, stateEffects, permission defs, `async`, `deprecated`+`sunsetDate`+`replacementOperation`, `i18n`) | the platform's `ServiceSpec.to_jsonld()` + `OperationNavigation.to_dict()` (`platform/apps/api/sulis/core/service/types.py`, `workflow.py`) — the parser targets these shapes (field-by-field optional), doesn't reinvent them |
| Service/area keying for grouping (ADR-006) | the platform's own `{service_name}/{operation}` operation key (`core/service/registry.py`), the `@type: "ServiceCatalog"` shape + its `contributions` / per-`ServiceContribution.service_name` (`core/service/types.py`) — `derive_areas` reads the platform's existing service boundary, it does not invent an area taxonomy |
| Form-field metadata shape (per-property `label`/`placeholder`/`group`/`order`/`readonly`/`hidden`, validation, `x-display`/`x-enum-labels`/`x-dependent-enum`/`x-visibility`) | `DisplayMetadata` / `ValidationMetadata` (`core/service/types.py`) + the `Display` / `EnumLabels` / `DependsOn` / `VisibleWhen` annotations (`core/forms/annotations.py`) — `build_form_fields` reads the keys these emit into property schemas; it does not redefine the form model |
| OpenAPI render (fallback) | Redoc (convention) — invoked by the step, embedded self-contained |
| Visual preview | the `design-system` skill's VIEWER generation |
| Worktree resurrection | `sulis-change recreate` (#56, shipped) |
| Step shape + JSON emit | `_wpxlib.py` + the `wpx` dispatcher |
| Change resolution | `ChangeStoreReader` port + `requireChange` / `resolveWorktreeRoot` |
| Subprocess + timeout discipline | the `SulisChangeStoreReader` / `wpx-worktree` pattern |

---

## 7. Open questions / gaps

- **Where the rendered artifacts are written** (in-worktree vs a sibling cache):
  default to in-worktree (source-of-truth-adjacent, removed when the worktree is
  tidied, regenerated on recreate). Decompose may revisit if caching is wanted.
- **Technical-render mechanics per format**: for OpenAPI, Redoc invocation (npx
  vs a pinned local binary) is a decompose-time detail; ADR-001 fixes that the
  Python step owns the invocation. For ServiceSpec, the technical render is a
  self-contained JSON-LD view (pretty-printed / lightly structured) the step
  produces directly — no external CLI.

---

## 8. Sizing report

- Tier: **M** (re-checked 2026-05-29 three times; latest after the founder
  review of the rendered mockup; sFPC 7 / ASR 11 — see `SIZING.md`). The
  expansions add founder-legible derivation surfaces *inside* the existing
  keystone step (WP-1): no new entities, integrations, endpoints, or client
  surfaces. sFPC is unchanged at 7 (still tier-S band). ASR rose 7 → 9 → 10 →
  **11** — the latest +1 is the **area-grouping** derivation (ADR-006): parse a
  change's service/area boundaries from three sources (multiple ServiceSpec
  docs, a `ServiceCatalog`'s `{service}/{op}` keys + `contributions`, or a single
  ServiceSpec), restructure every default-view section to render per-area with an
  "areas covered" overview, the single-vs-multi no-heading rule, and the
  OpenAPI tag-grouping fallback — a non-trivial structural derivation comparable
  to the form-fields projection. The Issue-1 permission change (lead with "who
  can do this", demote the code) — and its **Revision-5 follow-up** (restore the
  permission's readable *meaning* to the default view after Rev 4 over-demoted
  the permission itself; only the dotted *code string* stays in the toggle) — are
  both **small reorderings of an existing derivation** (`enrich_permission`
  already reads `description` + `typicallyAssignedTo`; Rev 5 simply surfaces the
  `description` it already had as its own labelled line), **not** new ASRs. The
  **Revision-6** change (also pair each readable form with its actual machine
  value in the default view — the operation identifier and the permission code)
  is likewise **not** a new ASR: the operation key / `method_name` and the
  permission code are already on the parsed `ContractModel` (the renderer reads
  them today; Rev 6 just renders them as a paired secondary instead of leaving
  the code toggle-only), so it adds no new derivation surface. ASR
  11 is still inside the tier-M band (6–15). **Tier unchanged: M.** No override.
- TDD length: within the tier-M target band; this document references the
  existing cockpit architecture rather than restating it (the largest source of
  potential bloat avoided per the right-sizing circuit breaker).
- ADRs produced: **6** (renderer-is-a-wpx-step; walkthrough-default +
  technical-toggle; generic-resolution; recreate-on-demand; ServiceSpec-first
  format precedence; **group-default-view-by-service-area**). ADR count rose
  **5 → 6**: the founder review's Issue 2 (multi-area grouping) is a **new
  cross-cutting decision** affecting how every default-view section is laid out
  when a change spans more than one service, with a single-vs-multi rule and a
  named derivation source — it warrants its own ADR (**ADR-006**). The founder
  review's Issue 1 (permission display leads with "who can do this", code
  demoted) is *not* a new ADR — it is a revision-in-place of the existing
  permission-display decision in **ADR-002** (Revision 4, with follow-up
  Revision 5 that restores the permission's readable meaning to the default view
  after the Rev-4 over-correction, and Revision 6 that pairs each readable form
  with its actual machine value — the operation identifier and the permission
  code — in the default view; all in-place, no new ADR). No External ADR
  Registry exists for this project (each `.architecture/{project}/adrs/` numbers
  from ADR-001), and the new ADR is numbered ADR-006 (one past the prior highest,
  ADR-005), so no collision.
- WP count: unchanged (WP-1..4 + the visual-contract gate WP). The area-grouping
  work and the permission "who can do this" reordering both land entirely inside
  WP-1 (the keystone renderer) and the WP-3 frontend's visual-contract
  declaration; no new WP is introduced.
- Restated authoritative sources: none — cockpit architecture referenced, not
  reproduced.
- Circuit breakers triggered: none.
