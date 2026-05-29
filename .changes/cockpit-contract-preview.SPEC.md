---
founder_facing: false
status: SPEC — founder-raised; scoped + decomposed, build-ready (tier-M/L)
---
# Spec — cockpit "see the contracts before you go" preview

**Change:** feat · cockpit-contract-preview
**Closes:** [#85](https://github.com/sulis-ai/agents/issues/85)
**Source:** founder, testing the agent-journey — "I couldn't see the data
contract, I couldn't see the UI contract," and reaching them means
arduous worktree navigation.

## Problem

The data contract and the UI/visual contract are produced at design time but
are inert artifacts (OpenAPI YAML, tokens, markdown) buried in a change
worktree. At the moment the founder wants to *judge* the work — before
dispatch, and again while testing — there is no surface to see them.

## Reframe (why it's worth more than visibility)

A **rendered** contract eyeballed **before dispatch** is a review gate. The
FE-03 break this session (data contract shipped missing `agents:list`/`get`)
is exactly what a founder glancing at a rendered API doc catches *before*
anything is built on it. Defect-prevention, not just comfort.

## Approach (reuse conventions + what exists; don't reinvent)

- **Data contract → `CONTRACT.html`** via **Redoc** (or Swagger UI) from the
  OpenAPI spec (CP — established convention; always reflects the spec). From
  the *same* spec, surface the generated **SDK/client usage** ("how to call
  it") alongside the rendered doc.
- **UI contract → `UI.html`** by reusing the existing **`design-system`
  skill's VIEWER** (live token-rendered visual preview) pointed at the
  change's visual contract.
- **Cockpit** gains per-change **"open data contract / open UI"** links.

## Decomposition (build order)

**WP-1 — data-contract renderer (keystone, deterministic).** A
`wpx-render-contract` step: locate the change's OpenAPI spec(s), render to a
self-contained `CONTRACT.html` via Redoc; emit a "no OpenAPI found — raw
contract + note" fallback so non-OpenAPI projects degrade gracefully. Unit-
tested on a fixture spec (rendered HTML references the spec's operations).

**WP-2 — UI-contract renderer.** Reuse the `design-system` VIEWER to render
the change's visual contract / tokens to `UI.html`. Where no visual contract
exists (non-user-facing change), emit nothing + note it.

**WP-3 — cockpit wiring.** Per change, surface "open data contract / open
UI" links; render the two artifacts **at design-time** (after decompose,
before `run-all` dispatch) as the pre-dispatch review gate, and **on-demand**
(the testing moment). Founder never touches a worktree.

**WP-4 — worktree recreate-on-demand integration.** To reach a *tidied*
(shipped) change's contracts, recreate the worktree from `shipped_sha`
(the #56 lifecycle work) before rendering, transparently.

**WP-5 (optional) — SDK face.** Generate + surface the client/SDK usage from
the OpenAPI spec on the `CONTRACT.html` page (openapi-generator convention).

## How we'll know it's done

- From the cockpit, one click opens a rendered, readable data contract and a
  visual UI preview for a change — no worktree navigation.
- The render is produced from the source-of-truth artifacts (no drift) and
  available before dispatch (review gate) + on-demand.
- Non-OpenAPI / non-user-facing changes degrade gracefully.
- `wpx-render-contract` unit-tested; review gate PASS.

## What to avoid

- Don't hand-build the HTML or copy the contract into it — render from the
  spec/tokens so it can't drift from what's built.
- Don't reinvent the visual preview — reuse the `design-system` VIEWER.
- Don't assume every project's data contract is OpenAPI — degrade gracefully.

## References / composes with

- `design-system` skill (VIEWER.html) — the UI render building block
- `plugins/sulis/references/standards/CONTRACT_FIRST_STANDARD.md`,
  `UX_VISUAL_DESIGN_STANDARD.md` — the contracts being rendered
- cockpit (#47 retheme), worktree recreate (#56, shipped)
- Redoc / Swagger UI (OpenAPI render); openapi-generator (SDK) — conventions
- #85 (closes)
