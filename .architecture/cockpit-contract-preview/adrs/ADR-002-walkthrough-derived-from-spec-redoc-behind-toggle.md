# ADR-002 — The founder-legible default view is the full picture (auto-hidden section-by-section); the technical render lives behind a toggle; both derive from the contract's own fields

> Status: accepted · 2026-05-29 (revised 2026-05-29 several times: once after founder review for ServiceSpec-first; again for the full-picture default view; Rev 4 demoted the permission code; Rev 5 restored the readable permission to the default view; Rev 6 pairs each readable form with its ACTUAL machine value — the operation identifier and the permission code — in the default view) · change: cockpit-contract-preview
> Supersedes the SPEC's original framing of WP-5 (SDK/usage) as optional.
> Revision 1: the renderer derives from the **ServiceSpec** first, not OpenAPI
> (format-precedence recorded in ADR-005).
> Revision 2 (binding founder decision, 2026-05-29): the default view is the
> **full picture**, not just the walkthrough — every ServiceSpec dimension a
> change defines is shown, each section **auto-hidden** when the spec doesn't
> carry it.
> Revision 3 (binding founder decision, 2026-05-29, after a deeper review
> against the authoritative `core/service/types.py` + `core/forms/annotations.py`):
> the default view ALSO surfaces, each auto-hidden when absent — (a) the **form
> fields** a user fills in (the priority surface), (b) the **languages** the
> change is available in (moved out of the technical toggle), (c) a
> **"runs in the background"** flag for `async` operations, and (d) the
> **enriched retirement** detail (sunset date + replacement) on the existing
> deprecated badge. **Events are confirmed out of scope** — the ServiceSpec
> contract does not carry them (see ADR-005 "Out of scope").
> Revision 4 (binding founder decision, 2026-05-29, after a founder review of
> the rendered mockup): the permission display **leads with plain English** —
> "Who can do this: Platform administrators" — derived from the permission
> definition's `typicallyAssignedTo` (and its `description`). The **raw
> permission code** (`platform.platforms:create`) is **demoted out of the
> default view into the technical-detail layer**. The earlier "enriched code
> pill with expander" (Revision-1 framing where the code was the primary,
> visible label) is **superseded**: the code is no longer the founder-facing
> label; the plain "who can do this" line is.
> Revision 5 (binding founder decision, 2026-05-29, after a founder review of
> the Rev-4 mockup): Rev 4 was an **over-correction** — by demoting the raw
> code *and* framing the permission's meaning as a mere "supporting line", it
> demoted the **permission itself** out of the default view, so a founder
> reviewing the page said "I can't see the permissions any more?" Rev 5
> **restores the permission to the default view in readable form**. Per
> operation in the default view, show **both**: (a) the **permission as a
> readable capability** — its plain-English *meaning* derived from
> `spec.permissions[code].description` (e.g. "Permission: lets you create
> platforms"), surfaced as its own clearly-labelled line, *not* buried as
> incidental prose; and (b) **who holds it** — "Who can do this: Platform
> administrators" (from `typicallyAssignedTo`), as Rev 4 introduced. **Only the
> raw dotted policy code** (`platform.platforms:create`) stays in the
> technical-detail layer. So the founder *sees* the permission (what it is +
> who has it) in the default view; only the machine-readable code string is
> demoted. Operations with **no required permission** still show "No sign-in /
> anyone". The readable permission + who-can lines belong to **that
> operation's row** (visually tied to the action), not a separate global block
> — keeping the action→permission relationship legible (the prior "permissions
> hard to understand in relation to the actions" issue stays fixed).
> Revision 6 (binding founder decision, 2026-05-29, after a founder review of
> the Rev-5 mockup): keep the human-readable text exactly as Rev 5 has it (it is
> right) but **also show the ACTUAL machine value alongside each readable form,
> in the default view** — for **both** the action and the permission:
> - **Action.** Alongside the human action description ("An admin can set up a
>   new platform") show the operation's **actual canonical identifier** as a
>   secondary, monospace value on the operation's row, clearly paired with the
>   readable description. The canonical identifier is the platform's own
>   operation **key** `{service}/{operation}` (from `core/service/registry.py`,
>   `f"{service_name}/{metadata.name.lower().replace(' ', '-')}"`, e.g.
>   `platform/create-platform`) and/or the operation's **`method_name`**
>   (`OperationMetadata.method_name`, emitted as `"method"` by
>   `_operation_to_dict`, e.g. `create_platform`). It is read directly from the
>   contract — never invented; absent → the secondary value is omitted (auto-trim
>   unchanged).
> - **Permission.** Alongside the Rev-5 readable "Permission: lets you create
>   new platforms" line **and** the "Who can do this: …" line, **bring the actual
>   permission code back into the default view** (`platform.platforms:create`),
>   paired with its readable meaning. **Rev 5's toggle-only placement of the code
>   is superseded:** the code now appears in the default view next to its human
>   meaning. (The technical toggle need not duplicate the bare code; the binding
>   requirement is that the code is VISIBLE in the default view next to its human
>   meaning.)
>
> The pattern in both cases: the **human-readable label is primary**, and the
> **actual machine value is shown as a paired secondary** (monospace, muted) —
> readable + real value together, per action and per permission. Keep it legible,
> not a code dump. Auto-trim is unchanged: a value the contract doesn't carry is
> simply omitted. Everything else — area grouping, the "Who can do this" line,
> the sign-in / background / retirement flags, form fields, languages, states,
> rules, journeys, what-each-action-changes, example, errors, generic
> resolution, events-out-of-scope, rendering-only — is **unchanged** from Rev 5.

## Decision

`CONTRACT.html` opens in a **founder-legible full-picture** register. The
default view — everything *above* the "show technical detail" toggle — surfaces
the whole shape of the change, with **each section rendered only if the source
ServiceSpec carries content for it** (auto-trim; no empty headings). Small
changes stay tight; rich changes show everything. The default view comprises:

1. **What it does** — a concrete worked walkthrough (hero scenario: "an admin
   creates a platform → here's exactly what comes back: `{id, name, slug,
   created}`") plus a plain-English **"What it does"** list, one line per
   operation, verb-tagged, with per-operation flags:
   - **the action's actual identifier alongside its readable description**
     (Revision 6) — the human action description ("An admin can set up a new
     platform") is **primary**, and the operation's **actual canonical
     identifier** is shown as a paired **secondary, monospace** value on the
     same row. The identifier is the platform's own operation **key**
     `{service}/{operation}` (`core/service/registry.py`, e.g.
     `platform/create-platform`) and/or the operation's **`method_name`**
     (`OperationMetadata.method_name`, emitted as `"method"`, e.g.
     `create_platform`) — read from the contract, never invented; absent → the
     secondary value is omitted (auto-trim).
   - **the permission, in readable form, paired with its actual code**
     (Revisions 5 + 6) — three values on the operation's own row, derived from
     the required permission's definition:
     - **the permission as a readable capability** — its plain-English
       *meaning* from `spec.permissions[code].description`, surfaced as its
       own clearly-labelled line ("Permission: lets you create platforms").
       This is **the permission itself, made legible** — not a code, but not
       hidden either. A founder reading the page can *see what permission the
       action requires*, in words.
     - **its actual code** (Revision 6) — the **actual permission code**
       (`platform.platforms:create`) shown as a paired **secondary, monospace**
       value next to the readable meaning, **in the default view**. Rev 5's
       toggle-only placement of the code is **superseded** — the code now
       appears next to its human meaning in the default view.
     - **who holds it** — "Who can do this: Platform administrators" from
       `typicallyAssignedTo`, the action→audience answer a founder needs.

     All three are **visible in the default view** and **belong to that
     operation's row** (visually tied to the action, not a separate global
     block), so the action→permission relationship is legible at a glance — the
     readable meaning is primary, the actual code is its paired secondary.
     Operations with **no required permission** show "No sign-in / anyone"
     exactly as before. When the contract carries no permission definition for a
     required code, the lines degrade to a plain "Requires sign-in" (no invented
     permission meaning or "who" prose); the **actual code is still shown** when
     a code is required even if its definition is absent, since the code itself
     is contract-carried.
   - **whether it needs sign-in** (derived from `userGuide.prerequisites` and
     whether any `permissions` are required) — kept as a small flag alongside
     the "who can do this" line, and
   - **whether it runs in the background** — a small **"runs in the background"**
     flag when `operations.{op}.async` is true, alongside the sign-in flag.
   A `deprecated` operation gets a small **"being retired"** badge here,
   **enriched with its sunset date** ("being retired — until {sunsetDate}") and
   **its replacement** ("use {replacementOperation} instead") when the spec
   carries `sunsetDate` / `replacementOperation`.
2. **The form fields a user fills in (the priority surface)** — a founder-legible
   projection of each entity's `properties` and each operation's `input` schema:
   the field **label**, **placeholder**, **input type**, **grouping/order**, the
   **validation rules** (required, min/max length+value, pattern as a plain
   hint), the **allowed options with their human labels** (`enum` paired with
   `x-enum-labels`), and the **conditional show-when** (`x-visibility`) /
   **depends-on** (`x-dependent-enum`) logic. Rendered as a readable "fields"
   view, **never a raw schema dump**. This answers the single most
   founder-judgeable question: *"does the form ask the right things, with the
   right labels and the right rules?"*
3. **The things that exist + their states** — the spec's `entities`: each
   entity's name + description, and its **`lifecycle`** rendered as a
   founder-legible state chain (e.g. "a Platform: draft → active → suspended").
4. **Business rules** — entity `constraints` in plain language (e.g. "a slug
   can't change once set").
5. **Languages** — the change's `default_locale` + `supported_locales`, rendered
   as a plain one-line default-view fact ("Available in: English, Spanish").
   Moved out of the technical toggle into the default view.
6. **Step-by-step journeys** — the spec's `workflows` (steps + successCriteria)
   as readable journeys.
7. **What each action changes** — per-operation `stateEffects`, each naming the
   entity and the state it moves to, linked to the entity lifecycle in (3).
8. A concrete **example request/response**.
9. The **errors** surface (each error's user-facing `message`).
10. The full **technical render** behind a `<details>` "show technical detail"
    toggle, collapsed by default — see "What lives behind the toggle" below.

Everything in 1–9 is **derived from the contract's own fields**. With a
ServiceSpec these come directly from native fields that exist for exactly this
purpose — `entities` (`properties` *with their embedded form metadata* /
`relationships` / `lifecycle` / `constraints`), `operations` (`input` schemas
*with their embedded form metadata*, `async`, `deprecated` + `sunsetDate` +
`replacementOperation`), `userGuide` (`summary` / `whenToUse` / `prerequisites` /
`nextSteps`), `leadsTo`, `stateEffects`, `workflows`, `permissions` (codes +
their definitions), `audiences`, `errors`, and the `i18n` block (default +
supported locales). The form metadata is carried *inside* the property schemas —
`label` / `placeholder` / `group` / `order` / `readonly` / `hidden`
(`DisplayMetadata`), `min_length` / `max_length` / `min_value` / `max_value` /
`pattern` / `enum` / `error_message` (`ValidationMetadata`), and the
`x-display` / `x-enum-labels` / `x-dependent-enum` / `x-visibility` extensions
injected by `core/forms/annotations.py`. With OpenAPI the renderer derives what
those fields allow (operations, schemas, `examples`, errors-from-responses, and
a **basic form-fields view** from the request body) and **auto-hides** the
richer sections (entities/lifecycle, constraints, journeys, state effects,
permission definitions, languages, background flag) and the rich form metadata
(human enum labels, show-when logic). Where an example is absent it is
**synthesised from the schema** (types + formats + required fields). Worked
examples are CORE to the renderer, not optional: the old WP-5 folds into WP-1's
hero view.

### What lives behind the toggle (engineer-facing, not default)

`rateLimits`, the `idempotent` flag, `bindings` (host / basePath / routing), the
**raw** `input`/`output` JSON schemas (the raw schema — distinct from the
founder-legible **form-fields** projection, which is in the default view), error
`relatedDocs` links, and the full ServiceSpec JSON-LD — or, for OpenAPI, the
Redoc render. The technical render is **appropriate to the source format**.
**Note: i18n/locales moved OUT of the toggle into the default view** (decision
item 5) — it now reads as the plain "Languages" line, not engineer-facing
detail. **The raw permission code is no longer toggle-only (Revision 6):** it is
shown in the default view paired with the permission's readable meaning. Rev 4
had demoted the code into this toggle and Rev 5 left it here; Rev 6 supersedes
that — the actual code now appears in the default view next to its human meaning
(the toggle's full ServiceSpec JSON-LD render still contains the code in
context, but the default view no longer hides it). The **actual operation
identifier** (`{service}/{operation}` key / `method_name`) is likewise shown in
the default view paired with the readable action description (Revision 6).

## Why

- **The ServiceSpec already carries founder-legible fields.** The platform's
  native, pervasive contract format (ADR-005) was designed to be AI- and
  human-legible: `userGuide`, `leadsTo`, `workflows`, `permissions`,
  `audiences`, and a rich `errors` catalog. Deriving the walkthrough, the
  "What it does" list, and the auth/permission flags from these fields means
  the founder view is a faithful projection of the contract — not a
  re-interpretation. OpenAPI carries almost none of this, so where only OpenAPI
  exists the founder view is necessarily thinner.
- **Audience (AAF, CLAUDE.md rule 6).** The primary user is a non-technical
  founder. A raw JSON-LD dump or a raw Redoc render is unreadable to them; it is
  the wrong default. Plain-English-first / detail-on-request is the Sulis
  dual-register pattern.
- **The founder wants to judge the whole change, not just one happy path
  (binding decision).** A walkthrough alone answers "what does the main action
  return?" but not "what things exist, what states do they move through, what
  rules govern them, what are the journeys, what does each action change?" The
  full-picture default view answers all of these from the same source-of-truth.
- **Permissions must read as "who can do this", not as a jargon code (binding
  decision, Revision 4).** A founder judging a change asks *"who is allowed to
  do this action?"* — an action→audience question. Leading each operation with
  the raw code `platform.platforms:create` and hiding the plain meaning behind
  an expander answered a different, engineer's question ("what's the permission
  string?") and buried the one the founder actually has. The spec already
  carries `typicallyAssignedTo` ("Platform administrators") and a plain
  `description`; surfacing those as the *primary, always-visible* line — and
  demoting the code to the technical layer — makes the action→audience
  relationship legible at a glance, which is the whole point of the default
  view (AAF, CLAUDE.md rule 6). The code is still available for the developer,
  one toggle away.
- **But the founder must still SEE the permission — demoting the code is not
  demoting the permission (binding decision, Revision 5).** Rev 4 over-corrected:
  it pushed the raw code into the toggle *and* framed the permission's meaning
  as a mere "supporting line", with the effect that a founder reviewing the
  rendered page asked *"I can't see the permissions any more?"* The founder
  judging a change needs to see **what permission each action requires** — not
  the dotted code, but the capability in words ("this action requires the
  permission to *create platforms*"). Rev 5 therefore restores the permission
  to the default view in **readable** form: each operation's row carries a
  clearly-labelled **readable permission line** (the `description`, e.g.
  "Permission: lets you create platforms") *and* the **"who can do this"** line
  (`typicallyAssignedTo`). Both are tied to that operation's row, so the
  action→permission relationship reads at a glance (fixing the earlier
  "permissions hard to understand in relation to the actions" issue). Only the
  raw dotted code string remains in the technical layer. The principle: the
  *jargon* is engineer detail; the *permission* is a founder-facing fact.
- **Form fields are the most founder-judgeable part (binding decision, priority).**
  The thing a non-technical founder can most directly evaluate is the form a
  user fills in: *are the labels right? is anything required that shouldn't be?
  do the dropdown options read well? does the conditional field appear at the
  right time?* The ServiceSpec carries all of this inside its property and input
  schemas (`DisplayMetadata` + `ValidationMetadata` + the `x-*` form
  extensions), so projecting it into a readable fields view costs no new source
  of truth — and surfacing it is the highest-leverage legibility win. A raw
  schema dump would defeat the purpose; the projection is deliberately
  founder-legible.
- **Auto-trim keeps the full picture honest.** Showing every heading regardless
  of content would produce empty sections on small changes — noise that trains
  the founder to ignore the page. Rendering a section *only* when the spec
  carries it means the page's size tracks the change's actual richness, and an
  absent section is a true signal ("this change defines no entities"), not a
  rendering gap. This is also forced by the platform's own serialiser, which
  emits these fields inconsistently (see Consequence).
- **No drift (the whole point of the feature).** Because the prose, the flags,
  and the example are generated *from the contract's own fields*, they cannot
  diverge from what is built. Hand-written walkthrough copy, or hand-typed
  "this operation needs admin" notes, would re-introduce exactly the drift the
  feature exists to prevent (the FE-03 break that motivated this change).
- **Convention (CP-01) for the technical layer.** Redoc is the established
  OpenAPI render; the ServiceSpec JSON-LD is the platform's own technical
  artifact. We keep both — we just demote the technical view from "the page" to
  "the detail behind a toggle," and pick the one that matches the source format.

## Rejected alternatives

- **A technical render as the default view.** Rejected: illegible to the
  primary user, regardless of format.
- **Walkthrough + "What it does" only as the default (the pre-revision view).**
  Rejected by the binding founder decision: it hides the entities, their states,
  the business rules, the journeys, and what each action changes — all of which
  the founder needs to judge the change. These are exactly the dimensions the
  ServiceSpec carries natively and OpenAPI does not, so showing only the
  walkthrough would waste the richest source of legibility.
- **Show every section always, with "none defined" placeholders.** Rejected:
  empty headings are noise that erodes trust in the page; and the platform's
  serialiser omits some fields entirely, so a placeholder can't distinguish
  "the change defines none" from "the serialiser didn't emit it." Auto-trim
  (render-only-if-present) is the honest behaviour.
- **A bare permission code (no enrichment).** Rejected by founder decision 1: a
  code like `platform.platforms:create` tells a non-technical founder nothing.
  The spec carries `description` / `grantsAccessTo` / `typicallyAssignedTo` for
  exactly this; surface them.
- **An enriched code *pill* as the visible label, with the meaning hidden behind
  an expander (the Revision-1 framing).** Superseded by Revision 4: a founder
  review of the rendered mockup found the code-pill-with-expander still *led*
  with the jargon code and hid the one thing the founder needs — *who is
  allowed to do this* — inside a `<details>` they have to open. The
  action→audience relationship was invisible at a glance. The fix leads with
  the plain "Who can do this: Platform administrators" line (from
  `typicallyAssignedTo` + `description`) and demotes the raw code to the
  technical-detail layer. The enrichment data is the same; only its *placement
  and primacy* changed — plain audience first, code as engineer detail.
- **Demoting the permission ENTIRELY out of the default view (the Rev-4
  framing, where only "who can do this" showed and the permission's meaning was
  incidental supporting prose).** Superseded by Revision 5: a founder review of
  the Rev-4 mockup reacted *"I can't see the permissions any more?"* Rev 4 fixed
  the jargon problem but over-corrected into a *visibility* problem — by hiding
  the raw code **and** under-surfacing the meaning, it removed the founder's
  ability to see *what permission an action requires*. The fix (Rev 5) keeps the
  raw dotted code in the toggle but restores the permission to the default view
  in **readable** form: a clearly-labelled "Permission: …" line (from
  `description`) **plus** the "Who can do this" line (from `typicallyAssignedTo`),
  both on the operation's row. Demoting the jargon is right; demoting the
  permission is not.
- **Keeping the raw permission code toggle-only, and showing no actual operation
  identifier in the default view (the Rev-5 framing).** Superseded by Revision 6:
  a founder review of the Rev-5 mockup confirmed the human-readable text was
  right but asked to *also* see the **actual values** — the real operation
  identifier and the real permission code — paired with the readable forms in
  the default view, so the page shows both what an action/permission *means* and
  *exactly which* operation and code it is. Rev 6 keeps every readable line and
  **adds the actual machine value as a paired, muted, monospace secondary**: the
  operation's `{service}/{operation}` key / `method_name` next to the action
  description, and the permission code next to the readable meaning. The readable
  form stays primary; the actual value is a secondary, not a code dump. Demoting
  the jargon (Rev 4) and restoring the readable permission (Rev 5) were both
  right; *hiding the actual value entirely* was the remaining gap.
- **A raw input/output JSON-schema dump as the "form" view.** Rejected by the
  founder decision: a raw schema is unreadable to a non-technical founder and is
  the wrong default. The raw schema stays behind the toggle; the default view
  gets a *projected* readable fields view (labels, placeholders, plain validation
  hints, human enum labels, conditional logic).
- **Leaving i18n / async / retirement-detail behind the technical toggle.**
  Rejected by the founder decision: which languages a change supports, whether
  an action runs in the background, and when a deprecated action retires (and
  what replaces it) are all founder-facing facts, not engineer detail — they
  belong in the default view. (The raw rate-limit numbers, bindings, and raw
  schemas remain behind the toggle.)
- **Rendering domain events in the default view.** Rejected — out of scope. The
  platform has domain events, but the ServiceSpec **contract** does not carry
  them, so rendering them would require scraping code outside the contract and
  would break the no-drift guarantee. The contract-native approximation,
  `stateEffects` ("what each action changes"), is already shown. Events are
  deferred pending a contract-format extension (ADR-005 "Out of scope").
- **Hand-authored walkthrough copy or hand-typed auth/lifecycle/rule notes.**
  Rejected: re-introduces drift; violates "render from source-of-truth."
- **Deriving the founder view from OpenAPI only.** Rejected: OpenAPI does not
  carry `userGuide`, `permissions`, `entities`/`lifecycle`/`constraints`,
  `workflows`, `stateEffects`, `audiences`, `leadsTo`, or a user-facing error
  catalog, so the most founder-legible fields would be unavailable. See
  ADR-005 for the full format-precedence rationale.

## Consequence

The renderer needs a contract parser with two front-ends — a ServiceSpec
(JSON-LD) parser as primary and an OpenAPI parser as secondary — feeding a
common internal model, plus a schema→example synthesiser, plus section builders
for **form fields** (the priority surface — projecting each property/input
schema into readable fields), entities + lifecycle, business rules
(constraints), journeys (workflows), and what-each-action-changes (stateEffects),
a permission enricher that joins each code to the spec's `permissions`
definition and produces **default-view content** — a **readable permission
line** (the capability in words, from `description`, e.g. "Permission: lets you
create platforms"), a **"who can do this" line** (from `typicallyAssignedTo`),
**and the actual permission code** (`platform.platforms:create`) shown as a
paired secondary next to the readable meaning, **all in the default view**
(Revision 6 — Rev 5 had kept the code toggle-only; Rev 6 brings it into the
default view paired with its meaning). The enricher also surfaces each
operation's **actual identifier** — the `{service}/{operation}` key /
`method_name` — as a paired secondary next to the readable action description in
the default view (Revision 6). Plus small derivers for the **languages** line
(`i18n`), the **background flag** (`async`), and the **enriched retirement**
badge (`deprecated` + `sunsetDate` + `replacementOperation`).

**Area grouping (Revision 5 — see ADR-006).** When a change's contract spans
**more than one service/area**, the renderer **groups every default-view
section by area** under clear headings (and adds a short "areas covered"
overview at the top); a single-area change renders one ungrouped block with no
redundant heading. The grouping is derived from the ServiceSpec structure
(operation keys `{Service}/{Operation}`, the `@type: ServiceCatalog` shape with
its `contributions`, and/or multiple ServiceSpec sources in one worktree).
ADR-006 records that decision in full; ADR-002 governs *what* each section
shows, ADR-006 governs *how sections are grouped* when there are multiple
areas.

The **form-fields builder is the most substantial new piece**: it reads, per
property, the `DisplayMetadata` keys (label / placeholder / group / order /
readonly / hidden), the `ValidationMetadata` keys (min/max length+value /
pattern / enum / error_message), and the `x-display` / `x-enum-labels` /
`x-dependent-enum` / `x-visibility` extensions, and projects them into a
founder-legible field card — not a raw schema dump. A `hidden` property is
omitted; a bare-typed property with no form metadata still renders as a basic
field. (This is the ASR-10 increment recorded in `SIZING.md`.)

**The parser must tolerate field-by-field absence.** The platform's
`ServiceSpec.to_jsonld()` (`core/service/types.py`) emits `entities.lifecycle`
as a flat `list[str]` and, at the time of writing, does **not** emit
per-operation `leadsTo` or `stateEffects` in that serialiser — those live in
`OperationNavigation.to_dict()` (`core/service/workflow.py`, keyed `toState` /
`fromStates`). The per-property form metadata is likewise independently optional
(a property may carry all, some, or none of it). `async` and the `i18n` block
*are* reliably emitted. So each section is independently optional, and the
auto-trim rule is mandatory, not cosmetic.

The keystone runs on a **rich ServiceSpec fixture** (asserting operations,
the sign-in flag, the **readable permission line** (the permission's *meaning*
from `description`, present in the default view) and the **"who can do this"
line** (from `typicallyAssignedTo`, also in the default view), the **actual
permission code** (`platform.platforms:create`) present **in the default view**
paired with the readable meaning (Revision 6 — Rev 5's toggle-only code is
superseded), and the **actual operation identifier** (the `{service}/{operation}`
key / `method_name`) present **in the default view** for each operation, paired
with the readable action description (Revision 6), **form fields with a
label/placeholder, a validation rule, a human-labelled enum, and a show-when
condition**, entities + lifecycle, constraints, **the languages line**,
workflows, state effects, **the background flag on an async operation**,
walkthrough, example, errors, **the enriched "being retired" badge with sunset +
replacement**, and that rateLimits/idempotent/bindings/raw-schemas
stay behind the toggle while the form-fields/languages/background/retirement
surfaces, the **readable permission line + the "who can do this" line + the
actual permission code**, and the **actual operation identifier** are all
in the default view, Revision 6)
**and a minimal ServiceSpec fixture** (asserting the absent sections are
auto-hidden with no empty headings, including the languages line and the
background/retiring flags, and that a plain typed input still renders as basic
fields with no fabricated metadata). A third test runs the **OpenAPI-fallback
fixture** and asserts graceful degradation: operations + example + basic form
fields present, the richer sections and rich form metadata absent, no empty
headings. The technical render is embedded self-contained so the page opens from
`file://` or is served by the cockpit with no external fetch.
