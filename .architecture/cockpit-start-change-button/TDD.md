# TDD — "Start something new" front door (CH-01KTMF)

> Tier **S** (see `SIZING.md`). This is a small, reuse-heavy frontend feat.
> It builds on the in-flight branch
> `change/create-change-owned-terminal-shared-session`, **not** on `main`.
> Design signed off: `.design/cockpit-start-change-button/SIGNOFF.md`
> (`production-approved`; the mockup is the visual contract of record — not
> re-run here).
>
> This TDD **references** the existing cockpit architecture and the in-flight
> branch rather than restating them. The whole start state machine, the
> server-side confirm gate, and the top-bar chrome already exist; this change
> wires a front door into them.

## What's in scope

Three thin client seams, all on the target branch's code:

1. **The front door** — a single "Start something new" primary button in
   `WorkspaceTopBar`, with a quiet `⌘N` hint, that navigates to `/start`.
2. **The accelerant** — a global ⌘N / ⌘K hotkey to the same `/start` flow.
3. **The cold-start empty state** — example chips + a soft welcome on the intent
   screen, added inside the existing `<StartFromIntent />` (the only genuinely
   new piece of the start screen; everything else is reuse).

## What's explicitly NOT in scope

- The in-change experience (coaching chat, terminal, stage bar, files view) —
  untouched, per SPEC Non-goals.
- The start state machine, the proposal/confirm gate, the started/error states —
  **already built** in `useStartFromIntent` + `<StartFromIntent />`; reused, not
  modified (beyond adding the cold-start block).
- Any new server capability — the existing confirm-gated funnel
  (`streamStartFromIntent`) is reused unchanged (SPEC Non-goals).
- The hand-off after start — `<StartFromIntentPage />` already navigates to the
  board on `onStarted`, and the founder lands in the existing change workspace.

---

## Form — Structural

The cockpit's hexagonal/component shape is established and authoritative on the
target branch. This change adds controls inside existing components; it
introduces **no new layers, no new ports, no new routes**.

| Seam | Where | Shape |
|---|---|---|
| Front-door button | `apps/cockpit/client/src/components/WorkspaceTopBar.tsx` | A new primary control rendered in the existing top bar. Calls the component's existing `navigate()` (already imported) → `navigate("/start")`. The button carries the `⌘N` hint in JetBrains Mono. |
| Global hotkey | new `apps/cockpit/client/src/api/useStartHotkey.ts` (or `hooks/`), mounted once in `apps/cockpit/client/src/layouts/WorkspaceShell.tsx` | A tiny `useEffect`-based `document` keydown listener with cleanup, mirroring the `ProductSwitcher` idiom (ADR-002). Maps ⌘N / ⌘K → `navigate("/start")`. Guards: no-op when focus is in an input/textarea/contenteditable. |
| Cold-start empty state | `apps/cockpit/client/src/components/StartFromIntent.tsx` (+ its CSS module `styles/StartFromIntent.module.css`) | A block rendered only when `state === "idle"` and `draft === ""` and there is no proposal: example chips ("Fix something that's broken", "Add a new feature", "I'm not sure yet") + a soft welcome. Clicking a chip prefills the intent box (and may submit) through the existing `propose()` / draft state — no new lifecycle. |

**Dependency direction:** unchanged. The button and hotkey depend on
`react-router`'s `useNavigate` (already used by the top bar); the cold-start
block depends only on the component's local draft state and the existing hook.
Nothing new reaches into infrastructure.

**One front door (ADR-001).** Button and hotkey both resolve to
`navigate("/start")` → `StartFromIntentPage` → `StartFromIntent` →
`useStartFromIntent` → `streamStartFromIntent`. There is exactly one path; the
accelerant cannot drift from the button.

## Armor — Operational

Resilience for the start flow is **server-authoritative and already in place** —
nothing is added here.

- **Confirm gate:** the existing `confirmToken` flow (`propose` → `confirm`) in
  `streamStartFromIntent` is the single consequential boundary. The front door
  only navigates; it triggers nothing consequential. "Start this work" remains
  the one and only point at which anything is created (SPEC Acceptance).
- **Never a dead end:** the existing `useStartFromIntent` already projects a
  typed error + a re-statable intent box (the honest retry/rename). The front
  door inherits it; this change adds no new failure surface.
- **The hotkey carries no network.** It is a pure client navigation. No
  timeout / retry / breaker applies (there is no external call on this path).
- **No secrets, no new logging, no PII.** Pure UI controls.

## Proof — Verification

Test stack is the cockpit's existing one: React Testing Library + Vitest, with
`streamStartFromIntent` injectable as a fake (the established pattern in
`StartFromIntent.test.tsx`). No new test infrastructure.

| Target | Test | Asserts |
|---|---|---|
| Front-door button | `WorkspaceTopBar.test.tsx` (new or extended) | the button renders as the single primary action; clicking it navigates to `/start` (assert via a MemoryRouter route probe); it is keyboard-focusable and shows a visible focus ring; the `⌘N` hint is present. |
| Global hotkey | `useStartHotkey.test.tsx` (new) | ⌘N navigates to `/start`; ⌘K navigates to `/start`; the key is a **no-op when focus is in a textarea/input** (drive a focused textarea, fire ⌘N, assert no navigation); listener is removed on unmount. |
| Cold-start chips/welcome | `StartFromIntent.test.tsx` (extended) | on the idle/empty state, chips + welcome render; clicking a chip fills the intent box (and reaches `propose()` via the injected fake); the chips do **not** render once a proposal is shown or the box is non-empty. |
| Reuse guard (regression) | existing `StartFromIntent.test.tsx` | the proposal-before-start (confirm gate), started, and error paths still pass unchanged — proof the start machine was not altered. |

**A11y proof (design flags carried in the SPEC):**

- The new button and chips are real focusable controls with the cockpit's `--ring`
  focus treatment; tested for Tab-reachability + visible focus.
- **Green "Start this work" contrast (3.30:1, AA-large only):** this is the
  existing confirm button. The build keeps its label ≥16px or 14px-bold so it
  qualifies for AA-large (or darkens `--positive` at the token level). A
  design-time check, recorded as a Blue-step item, not a new test harness.
- **Satoshi not loaded:** headings render in Inter (`--font-display` falls back).
  Do not assume Satoshi; no code action beyond not adding a Satoshi dependency.
- **Colour independence:** the chips and welcome carry text labels; no state is
  signalled by colour alone.

---

## Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

This is a `kind: frontend` change. Per the canonical kind→adapter table, the
verification adapter for `frontend` is component tests (Vitest + React Testing
Library) and, for the runtime surface, a Playwright/manual drive of the running
cockpit. There is no SRD Verification Plan to inherit (this is a change SPEC);
the plan below is concretised directly from the SPEC's Acceptance list.

1. **User-observable behaviour being verified.** From inside the cockpit a
   founder sees one obvious "Start something new" button; clicking it (or ⌘N /
   ⌘K) opens the intent screen; describe → clarify → confirm → "Start this
   work" creates a change and lands them in its workspace; a first-timer sees
   cold-start help, not a blank wall; nothing is created before "Start this
   work"; a failed start offers retry/rename.

2. **Verification environment(s).** Local dev (Vitest component tests) for the
   three new seams; the running cockpit (`apps/cockpit`, Vite client + Express
   server) for the runtime drive of the end-to-end front-door → started flow.

3. **Bootstrap-from-zero.** A fresh checkout of this branch (on top of the
   in-flight branch) builds the cockpit client and runs the component tests with
   no extra setup; the injected `streamStartFromIntent` fake means the new tests
   need no live funnel.

4. **Per-integration verification strategy.** The only integration is the
   existing start-from-intent funnel — **reused, not introduced**, classified
   `existing`. Strategy: the new client tests use the **injectable
   `streamStartFromIntent` fake** (the established seam in `useStartFromIntent`),
   so the front door is verified without a live server. The real funnel is
   exercised in the runtime drive only. No new mock contract is authored — the
   fake's contract is the existing `StreamStartFromIntentFn` type.

5. **Per-kind verification adapter.** `frontend` → Vitest + React Testing
   Library specs:
   - `apps/cockpit/client/src/tests/WorkspaceTopBar.test.tsx` — front-door
     button renders + navigates + focus.
   - `apps/cockpit/client/src/tests/useStartHotkey.test.tsx` — hotkey →
     `/start`, input-focus no-op, unmount cleanup.
   - `apps/cockpit/client/src/tests/StartFromIntent.test.tsx` — cold-start
     chips/welcome (extended) + the unchanged confirm/started/error regression.
   Plus a manual/Playwright runtime drive of the running cockpit for the
   end-to-end front-door → confirm → started → hand-off path.

6. **Infrastructure needs surfaced (deferred).** None. No vendor mocks, test
   accounts, or seed fixtures are required — the existing injectable fake covers
   the client tests, and the runtime drive uses the cockpit as it already runs.

**Per-WP verification shape (for `/sulis:plan-work`):** all three seams are
**concrete** — each ships its own Vitest spec the moment it lands
(`adapter: frontend` + the `artifact:` path above). No deferred or trivial
carveouts.

---

## Sizing Report

> Cross-references `SIZING.md`.

- **Tier:** computed **S**; confirmed **S**. (ASR count 7 sits in the M band but
  is dominated by inherited a11y/reuse constraints; the only net-new
  architecture is one global hotkey hook + one empty-state block — see SIZING.)
- **TDD length vs target:** within the ~120–180 line tier-S target.
- **ADRs:** 2 produced (front-door routing; accelerant-as-hotkey) — both record
  a genuine rejected alternative (modal; command palette). Within tier-S
  expectations.
- **Referenced rather than restated:** the cockpit hexagonal shape, the
  `WorkspaceShell`/`WorkspaceTopBar` chrome, the `/start` route, the
  `useStartFromIntent` state machine, and the server-side confirm funnel are all
  referenced as existing on the target branch — not re-derived here.
- **Circuit breakers triggered:** none (length within target; ADRs within max).
