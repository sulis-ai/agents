# WP Frontend Standard

> **Sulis-local v0.1.0 (2026-05-26).** The opinionated frontend
> implementation doctrine for `kind: frontend` Work Packages — the consumer-
> side twin of `WP_BACKEND_STANDARD.md`. It deliberately **mirrors the backend
> spine** (so a reviewer sees the same principles applied) and **layers on the
> frontend-only patterns** (accessibility, design tokens, component tiers, UI
> states). The frontend builds against **two contracts**: the *data* contract
> (`CONTRACT_FIRST_STANDARD.md`) and the *visual* contract
> (`UX_VISUAL_DESIGN_STANDARD.md`).

<!-- summary -->
Every frontend Work Package is built component-first (base → composed →
page), consumes data through a **typed client behind the data contract**
(never `fetch` in a component), keeps **one source of truth for state**,
renders **loading / error / empty** for every async surface, meets **WCAG AA
gated automatically** (jest-axe per component, Playwright-axe per page),
consumes **design tokens never hardcoded values**, wraps pages in **error
boundaries**, and is built **outside-in (double-loop TDD)** with a definition
of done that means **wired, accessible, and reachable** — not just rendered.
<!-- detail -->

## Severity convention

`MUST` — non-negotiable; violations block the WP. `SHOULD` — default;
deviation needs a one-line rationale. `MAY` — judgement.

## Relationship to existing standards (reference, don't restate)

- `WP_BACKEND_STANDARD.md` — the **sibling**. The two share a spine; this maps
  each backend pattern to its frontend form (see the table below).
- `CONTRACT_FIRST_STANDARD.md` — the **data contract** the frontend consumes.
  WPF-02 (typed client) conforms to it (CF-06); WPF-03 (mock-first) *is* its
  contract mock (CF-04/05); WPF-05 (error/empty states) consume its three
  error categories (CF-03).
- `UX_VISUAL_DESIGN_STANDARD.md` — the **visual contract**. WPF-06
  (accessibility) and WPF-07 (design tokens) implement to it.
- `engineering-principles.md` (EP-02 TDD, EP-07 SOLID/clean code, EP-08 no
  bloat), `boring-code.md`, `red-green-blue.md` — referenced, not restated.
- `WORK_PACKAGE_STANDARD.md` — the WP shape; this is its `kind: frontend`
  execution detail.

### Backend ↔ frontend spine (the same principles, the frontend form)

| Backend (WPB) | Frontend form (WPF) |
|---|---|
| Ports & adapters | Component tiers: components are the adapter to the DOM (WPF-01) |
| Repository | Typed client / data layer; no `fetch` in components (WPF-02) |
| In-memory adapter first | Mock-first from the contract — MSW / fake client (WPF-03) |
| Handler = single source of truth | One source of truth for state: store + server-cache (WPF-04) |
| Typed Result | `{data, loading, error}` + error boundaries + the three UI states (WPF-05, WPF-08) |
| Composition root + DI | App root + context providers (WPF-09) |
| Outside-in double-loop TDD | Same — RTL/Playwright outer, unit inner, + jest-axe (WPF-10) |
| Done means wired | Routed/mounted + states + a11y + reachable (WPF-11) |
| Clean code / boy scout | Same (WPF-13) |
| Authorization at the handler | **Diverges** — frontend only shows/hides; the real gate is the backend (see note) |

---

## The patterns

### WPF-01 — Component-driven architecture · MUST

Build from the smallest composable units up: **base** components (stateless,
token-consuming, accessible) → **composed** components (base + state + data) →
**pages** (layout + composed + error boundary). State lives closest to where
it's consumed (colocation).

> **Anti-pattern:** page-sized god components; business logic in a leaf
> component; copy-pasted markup instead of a shared base component.

### WPF-02 — Data behind a typed client, never `fetch` in a component · MUST

Components never call `fetch`/the network directly. Data access goes through a
**typed client generated from / conforming to the data contract**
(`CONTRACT_FIRST_STANDARD.md`). A query layer (e.g. TanStack Query) is the
modern form. The client is the frontend's "repository."

> **Anti-pattern:** `await fetch('/api/...')` inside a render/component;
> reshaping responses ad hoc in the component instead of conforming to the
> contract (CF-06).

### WPF-03 — Mock-first (the contract mock) · MUST

The frontend builds against a **mock generated from the data contract** (MSW,
or a fake client fed by the contract's JSON stubs) — including the **error and
empty** stubs (CF-04). This is the frontend's "in-memory adapter first": it
lets the frontend build in parallel with the backend (CF-05) and is the test
substrate. Never hand-mock individual `fetch` calls.

> **Anti-pattern:** waiting for the real backend before building UI;
> ad-hoc `jest.fn()` fetch mocks instead of the contract mock.

### WPF-04 — One source of truth for state · MUST

UI state lives in **one store** (per feature); server data lives in **one
cache** (the query layer). Components **subscribe**; they don't each hold their
own copy of truth. Colocate state with its consumer.

> **Anti-pattern:** the same data duplicated in three components' local state;
> prop-drilling server data five levels deep instead of a cache.

### WPF-05 — Loading / error / empty states for every async surface · MUST

Every surface that loads data renders **all three** of loading, error, and
empty — by contract. The error and empty states map to the data contract's
**three error categories** (CF-03): a `NotFound` (Expected) → empty/“not found”
state; an `Internal`/`Protocol` → error state with a retry where appropriate.

> **Anti-pattern:** a spinner that never resolves on error; a blank screen on
> an empty list; an unhandled rejection surfacing as a white screen.

### WPF-06 — Accessibility baseline (WCAG AA), gated automatically · MUST

Every component meets **WCAG 2.1 AA**, verified by automated audit:
**`jest-axe` on every component test, Playwright-axe on every page**. Plus the
non-negotiables: keyboard-operable (never mouse-only), **visible focus** (never
`outline:none`; use the focus-visible ring), ARIA name/role/value, real
`<label>`s (placeholder is not a label), information **never by colour alone**.
Accessibility is decided at design time in the visual contract
(`UX_VISUAL_DESIGN_STANDARD.md`) and verified here.

> **Anti-pattern:** `outline:none`; `<div onClick>` with no keyboard handler;
> colour-only error indication; shipping a component with no axe assertion.

### WPF-07 — Design tokens, never hardcoded values · MUST

Components consume **semantic / component-tier design tokens** — never raw
hex/px values, never primitive tokens directly. Tokens are the visual
contract's source of truth (`UX_VISUAL_DESIGN_STANDARD.md`) and carry theming +
pre-validated contrast for free.

> **Anti-pattern:** `style={{ color: '#1a1a1a' }}`; `className="text-neutral-900"`
> (primitive) in a component; a one-off colour that bypasses the token system.

### WPF-08 — Error boundaries · MUST

Every page is wrapped in an **error boundary** so a render failure degrades to
a recoverable UI, not a white screen. Components fail gracefully.

### WPF-09 — Composition root + dependency injection · MUST

Wiring happens at the **app root** via context providers (router, query
client, theme, the injected API client). Components receive dependencies via
props/context — not global imports reaching across the tree.

> **Anti-pattern:** a component importing a singleton API client module;
> provider-less global state.

### WPF-10 — Outside-in (double-loop) TDD + a11y audits · MUST

Built outside-in: **integration / E2E tests first and failing** (React Testing
Library for flows; Playwright for journeys), then unit RED→GREEN→BLUE per
`red-green-blue.md` on base → composed → page. **A11y audits are part of the
loop** — jest-axe on each component, Playwright-axe on each page — not a final
afterthought.

> **Anti-pattern:** snapshot tests as the only coverage; testing
> implementation details instead of user-visible behaviour; a11y checked
> manually, once, at the end.

### WPF-11 — Done means wired, accessible, and reachable · MUST

A frontend capability is **not done** until it is **routed/mounted** in a page,
has its **loading/error/empty** states, **passes a11y audits**, and is
**reachable in the running app**. The frontend equivalent of a 404 is an
orphaned component never imported into a route.

> **Anti-pattern:** a component reachable only from a test; a page built but
> never added to the router; "states later."

### WPF-12 — Agentic-interface principles (AI surfaces) · MUST for AI features

When the surface involves AI / chat / autonomous actions (the cockpit), it
follows `UX_VISUAL_DESIGN_STANDARD.md`'s agentic-interface principles —
notably: **chat coordinates, outcomes deliver** (purpose-built UI, not a chat
transcript for the real work); **human-in-the-loop approval** before
consequential actions; **failure recovery** (change approach after repeated
failure); **honest-confidence transparency** (source attribution, no false
certainty — ties to `TONE_STANDARD.md`).

### WPF-13 — Clean code + leave-it-better (boy scout) · MUST

Applies EP-07 + `boring-code.md` — clear names, small focused components, no
duplication. Leaves every file better than found, **bounded to the WP scope**;
structural change to existing components follows characterisation-test-first.
(Points to the canonical standards; mirrors WPB-12.)

> **Note — authorization diverges from backend.** The frontend does **not**
> enforce authorization; it only **shows/hides** based on permissions. The
> real access gate is the backend (WPB-05). Never treat client-side
> show/hide as a security control.

---

## Verification gates (per `kind: frontend`)

From `engineering-principles.md`'s verification-operationalisation mapping,
the frontend gates are:

| Gate | Tool class (example) |
|------|----------------------|
| Tests pass | component + integration runner (e.g. vitest / jest + React Testing Library) |
| E2E / journeys | Playwright |
| Accessibility | jest-axe (component) + Playwright-axe (page) — **WCAG AA** |
| Lint | linter (e.g. eslint) |
| Types | type checker (e.g. tsc) |
| Performance | perf budget (e.g. lighthouse) |

The tools are scope-specific (declared per project); the **gate classes** are
fixed for frontend WPs.

---

## Profiles

| Profile | When | Doctrine |
|---------|------|----------|
| **Production (React/TS)** | Real product surfaces — the cockpit | All patterns above; design tokens; full test + a11y gating |
| **Prototype (Alpine/Tailwind)** | `--prototype` changes; throwaway spikes | Semantic-HTML-first + progressive enhancement + a11y + the three states + `data-test` hooks; single-file, "just works"; the heavier production apparatus is relaxed |

Most real `kind: frontend` WPs are **production**. The prototype profile maps
to `--prototype` changes — disposable, not held to the full production bar.

---

## Provenance

Consolidated from the reviewed frontend documents (2026-05-26):

- platform `.claude/skills/frontend-development/SKILL.md` — component tiers
  (WPF-01), token consumption (WPF-07), accessibility patterns (WPF-06),
  error boundaries (WPF-08), state colocation (WPF-04), double-loop TDD +
  jest-axe/Playwright (WPF-10), the backend↔frontend mapping, the
  authorization divergence note.
- platform `FRONTEND_BEST_PRACTICES.md` (Alpine/Tailwind, both copies) — the
  prototype profile + the semantic-HTML/progressive-enhancement fundamentals +
  the three UI states + `data-test` testability.
- platform `accessibility-wcag-aa.md` — the WCAG AA baseline (WPF-06) — see
  also `UX_VISUAL_DESIGN_STANDARD.md` where it's owned at design time.
- platform `agentic-interface.md` — the AI-surface principles (WPF-12).

**Platform couplings stripped** (not part of this standard): the specific
design-system files (`HIG.md`, `DESIGN_TOKENS.json`, `scope-profile.yaml`),
the `apps/web/src/` layout. The patterns are the contract; the framework
(React assumed for production), the token source, and the file layout are the
implementer's choice.

---

## Version history

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-05-26 | Initial sulis-local definition. 13 patterns (WPF-01..WPF-13) mirroring the backend spine + frontend-only patterns (a11y/tokens/component-tiers/UI-states/agentic). Builds against two contracts (data: CONTRACT_FIRST; visual: UX_VISUAL_DESIGN). Two profiles (production React / prototype Alpine). Authorization-divergence note. SHOULD-tier items carry 90-day calibration; promote to MUST on evidence from 3+ frontend WP executions. |
