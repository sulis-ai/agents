# ADR-005 — The renderer is ServiceSpec-first: ServiceSpec → OpenAPI → raw-contract precedence

> Status: accepted · 2026-05-29 · change: cockpit-contract-preview
> Drives the revision of ADR-002. Scoped to *rendering* only — see "Out of scope".

## Decision

The `wpx-render-contract` renderer resolves a change's data contract using a
fixed **input-format precedence**:

| Order | Format | Role | Why |
|---|---|---|---|
| (a) | **ServiceSpec (JSON-LD)** | **PRIMARY** | The platform's native, pervasive contract format. Carries the founder-legible fields directly. |
| (b) | **OpenAPI** (`openapi.{yaml,json}`, `swagger.json`) | Secondary | The established cross-ecosystem convention (CP-01) where present. Derive what it carries; degrade the rest. |
| (c) | **Raw contract + plain note** | Fallback | Whatever data-contract file exists, shown verbatim with a plain-English "this is the raw contract" note. Never break. |

The renderer locates contracts generically inside the worktree (ADR-003), tries
(a) first, falls back to (b), then (c). Where a change carries more than one
contract, each is rendered (one section per contract), still in precedence
order.

The founder-facing default view is the **full picture** (ADR-002): every
ServiceSpec dimension a change defines, each section auto-hidden when the spec
doesn't carry it. Every element is derived from the ServiceSpec's own fields:

| View element (default view) | ServiceSpec source field |
|---|---|
| "What it does" list (one line per operation) | `operations.{op}.name` / `.description` / `.userGuide.summary` |
| Verb / kind tag | `operations.{op}.method` + name heuristics |
| **Needs sign-in flag** | `operations.{op}.userGuide.prerequisites` (auth phrasing) + whether `operations.{op}.permissions` is non-empty |
| **"Runs in the background" flag** | `operations.{op}.async` (emitted as `async` by `_operation_to_dict`) |
| **Enriched permission** (code + what it means + who holds it) | `operations.{op}.permissions` (the code) joined to top-level `permissions.{code}` → `.description`, `.grantsAccessTo`, `.typicallyAssignedTo` |
| **Form fields a user fills in** (priority surface) — label, placeholder, input type, group/order, required, validation rules, allowed options + human labels, show-when / depends-on | the **per-property metadata inside** `entities.{E}.properties.{p}` and `operations.{op}.input.properties.{p}`: `DisplayMetadata` (`label`/`description`/`placeholder`/`group`/`order`/`readonly`/`hidden`) + `ValidationMetadata` (`min_length`/`max_length`/`min_value`/`max_value`/`pattern`/`enum`/`error_message`) + the `x-display` / `x-enum-labels` / `x-dependent-enum` / `x-visibility` extensions (`core/forms/annotations.py`) |
| **The things that exist + their states** | `entities.{E}.name` / `.description`; `entities.{E}.lifecycle` (state names) → rendered as a state chain |
| **Business rules** | `entities.{E}.constraints` → plain-language rules |
| **Languages** (plain default-view fact, e.g. "Available in: English, Spanish") | the `i18n` block: `i18n.defaultLocale` + `i18n.supportedLocales` (from `ServiceSpec.default_locale` / `.supported_locales`) |
| **Step-by-step journeys** | `workflows.{W}.steps` + `.successCriteria` |
| **What each action changes** | `operations.{op}.stateEffects` (entity → toState), linked to the entity lifecycle above |
| Worked-walkthrough hero | a chosen operation's `userGuide` + `output` schema, sequenced by `leadsTo` / `workflows` |
| Example request/response | `operations.{op}.input` / `.output`; the OpenAPI `examples` when present; else synthesised from schema |
| What comes next | `operations.{op}.leadsTo`, `userGuide.nextSteps` |
| Error behaviour | `errors.{CODE}.message` / `.cause` / `.fix` |
| **Enriched "being retired" badge** (sunset + replacement) | `operations.{op}.deprecated` (+ `sunsetDate` → "until {date}" / `replacementOperation` → "use {X} instead") |

Kept **behind the technical toggle** (not in the default view): `rateLimits`,
the `idempotent` flag, `bindings` (host/basePath/routing), the **raw**
`input`/`output` JSON schemas (distinct from the founder-legible form-fields
projection, which is in the default view), error `relatedDocs` links, and the
full ServiceSpec JSON-LD (or Redoc for OpenAPI). **`i18n`/locales moved OUT of
the toggle into the default view** as the plain "Languages" line (decision,
2026-05-29).

Because all of these come from the contract's own fields, they cannot drift
from what is built. **Auto-trim (MUST):** each default section renders only if
its source field is present — no empty headings. Where a change has **only
OpenAPI**, the renderer derives operations, schemas, `examples`,
errors-from-responses, and a **basic form-fields view** from the request body
(field `type` / `format` / `required` / `enum` / `pattern` only), and auto-hides
the founder-legible extras (no `userGuide` prose, no permission definitions, no
entities/lifecycle, no constraints, no workflows, no stateEffects, no languages
line, no background flag) and the **rich** form metadata (no `x-display` labels/
placeholders/groups, no `x-enum-labels` human option labels, no
`x-visibility`/`x-dependent-enum` conditional logic) — surfacing a plain note
that this contract carries less guidance.

**Field-by-field optionality (grounding, MUST tolerate).** The platform's
`ServiceSpec.to_jsonld()` (`core/service/types.py`) emits `entities.lifecycle`
as a flat `list[str]` and `entities.constraints` as a `list[dict]`, and — at the
time of writing — does **not** emit per-operation `leadsTo`/`stateEffects` in
that serialiser (those are defined in the schema doc and emitted by
`OperationNavigation.to_dict()` in `core/service/workflow.py`, keyed
`toState`/`fromStates`). The renderer therefore reads each of `lifecycle`,
`constraints`, `leadsTo`, `stateEffects`, `workflows`, and the `permissions`
definitions defensively and independently — and `stateEffects` from either the
operation object or a navigation block. The **per-property form metadata** is
likewise independently optional: a property may carry `DisplayMetadata`,
`ValidationMetadata`, the `x-*` extensions, all of them, or none — `build_form_fields`
reads each key defensively and a bare-typed property still renders as a basic
field. By contrast, **`async` and the `i18n` block are reliably emitted** by
`_operation_to_dict` / `to_jsonld`, so the background flag and the languages
line are stable; `deprecated` / `sunsetDate` / `replacementOperation` are emitted
only when set. This is *why* auto-trim is mandatory: the platform's own output
varies field by field.

## Why

- **ServiceSpec is the platform's native, pervasive format.** Nearly every
  feature under `platform/features/` ships a `SERVICE_SPECIFICATION.md`, and the
  format is derived from `@operation`-decorated handlers
  (`platform/apps/api/sulis/core/service/types.py` — `ServiceSpec.to_jsonld()`).
  Rendering the format the platform actually uses, first, is the boring,
  correct default (CP-01 priority 0: internal prior art).
- **ServiceSpec natively carries the founder-legible fields; OpenAPI does not.**
  The platform's own ontology doc states this directly: OpenAPI tells you
  endpoints/methods/params/responses but "does NOT tell you how to display
  fields, what error messages to show, how operations relate, what workflows
  users follow." The ServiceSpec carries `userGuide`, `permissions`,
  `audiences`, `leadsTo`, `workflows`, and a user-facing `errors` catalog —
  exactly the fields this feature needs to be legible to a non-technical
  founder.
- **Graceful degradation, not a hard requirement.** A change that only has
  OpenAPI is common and must still render. Precedence + degrade is the boring
  resilience pattern; the feature never breaks on a thinner contract.

## Rejected alternatives

- **OpenAPI-first (the original ADR-002 framing).** Rejected: OpenAPI is not the
  platform's native format and lacks the founder-legible fields, so an
  OpenAPI-first renderer would discard the richest source of legibility and
  re-derive a poorer version of it.
- **ServiceSpec only.** Rejected: changes that carry only OpenAPI (or only a raw
  contract) would render nothing. Degradation is required.
- **Render both formats side by side, equal weight.** Rejected: produces two
  competing default views and confuses the precedence; the founder needs one
  clear default with technical detail on request (ADR-002).

## Out of scope

This ADR governs **what the renderer prefers when rendering a contract a change
already has**. It does **not** standardise Sulis's broader contract-FIRST design
process on the ServiceSpec format — that is a separate standards-level change.
This change only renders whatever contract a change has, preferring ServiceSpec.

**Events — deliberately excluded (recorded by founder decision, 2026-05-29).**
The platform has domain events (`platform/apps/api/sulis/.../domain/events/`),
and "what events does this action emit?" is a legitimate thing a founder might
want to see. But the **ServiceSpec contract** (`core/service/types.py` →
`ServiceSpec.to_jsonld()`) does **not carry events** — there is no `events`
field on `OperationMetadata`, `EntityMetadata`, or `ServiceSpec`. Rendering them
would require scraping the events package out of the codebase, which is
precisely the drift this feature exists to prevent: the rendered preview would
then assert something the contract does not guarantee. Events are therefore
**out of scope for this rendering-only change**, pending a **contract-format
extension** that adds events to the ServiceSpec (tracked separately). Until then,
the contract-native approximation of "what happens as a result of an action" —
`stateEffects` ("what each action changes") — is already in the default view
(ADR-002 decision item 7), and is the honest, no-drift answer the contract can
support today.

**The renderer remains rendering-only.** Adding form fields, languages,
background flags, and retirement detail does **not** make this a contract-FIRST
standards change — these are all projections of fields the ServiceSpec already
carries. The boundary is unchanged: we render what a change's contract has; we
do not change how contracts are authored.

## Consequence

WP-1's parser grows a ServiceSpec front-end (primary) alongside the OpenAPI
front-end (secondary), both feeding a common internal model, plus section
builders for **form fields** (the priority surface — projecting each property/
input schema into readable fields, reading `DisplayMetadata` + `ValidationMetadata`
+ the `x-*` form extensions), entities + lifecycle, business rules, journeys, and
what-each-action-changes, a permission enricher, and small derivers for the
**languages** line, the **background** flag, and the **enriched retirement**
badge. The keystone unit test runs on a **rich ServiceSpec fixture** (operations
with userGuide/permissions/errors/leadsTo/stateEffects, **one async operation**,
**one deprecated operation with sunset + replacement**, an entity whose
`properties` carry form metadata — a labelled/placeheld field, a validated
field, an enum with `x-enum-labels`, an `x-visibility` field — plus lifecycle +
constraints, a workflow, and multi-locale `supported_locales`) and asserts the
rendered HTML surfaces operations, the enriched sign-in + permission, **the form
fields in a readable view**, the entities + lifecycle, the constraints as rules,
**the languages line**, the workflows as journeys, the state effects, **the
background flag**, the walkthrough, the example, the errors, and **the enriched
"being retired" badge** — and that rateLimits/idempotent/bindings/raw-schemas
stay behind the toggle while form-fields/languages/background/retirement are in
the default view. A **minimal ServiceSpec fixture** asserts the absent sections
auto-hide with no empty headings (including the languages line and the
background/retiring flags) and that a plain typed input still renders as basic
fields; an **OpenAPI-fallback fixture** asserts graceful degradation (operations
+ example + basic form fields present, richer sections and rich form metadata
absent, no empty headings). ADR-003 (generic per-change resolution) is unchanged:
discovery is still a generic glob over the worktree — it just now recognises the
ServiceSpec JSON-LD shape ahead of OpenAPI.
