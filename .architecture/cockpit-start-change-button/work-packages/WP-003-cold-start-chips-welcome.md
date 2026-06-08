---
id: WP-003
title: Cold-start chips + soft welcome on the StartFromIntent empty state
status: pending
kind: frontend
sequence_id: WP-003
dependsOn: []
blocks: []
estimated_token_cost:
  input: 8k
  output: 4k
tdd_section: Form — "Cold-start empty state" seam
adrs: [ADR-001]
primitive: extend
group: expand
visual_contract: ".design/cockpit-start-change-button/SIGNOFF.md (production-approved 2026-06-08) — signed-off mockup MOCKUP.html state 2 (cold-start/empty); no separate visual-contract WP per change brief (contract already signed)."
verification:
  adapter: frontend
  artifact: apps/cockpit/client/src/tests/StartFromIntent.test.tsx::cold_start_chips_render_on_empty_idle
---

> **Branch note (MUST read before implementing).** This WP builds on
> `change/create-change-owned-terminal-shared-session`, **not** `main`.
> `StartFromIntent.tsx`, its CSS module, `useStartFromIntent`, and the existing
> `StartFromIntent.test.tsx` only exist on that branch. Do not build against `main`.

## Context

The one genuinely-new piece of the start screen. The SPEC and design (MOCKUP
state 2) require that a first-timer with no changes sees cold-start help —
example chips + a soft welcome — not an empty wall. The existing
`<StartFromIntent />` on the target branch has a hero + intent box but **no
chips**; this WP adds them **inside that existing component** (ADR-001: not a
new surface). Clicking a chip prefills the intent box through the component's
existing local `draft` state and reaches the existing `propose()` entry point —
it rides the same single start path; it adds no lifecycle.

This is an **extend** primitive: a block added inside an existing component
through its existing `draft` state and `propose()` entry — no new hook, no new
state machine, no change to `useStartFromIntent`.

## Contract

The component signature is unchanged. A cold-start block is added to the render,
gated on the empty/idle condition, wired to the existing draft + propose path.

```typescript
// apps/cockpit/client/src/components/StartFromIntent.tsx (exists — this WP edits it)
// Existing local state: const [draft, setDraft] = useState("");
// Existing entry point: start.propose(intent)  (via the local submit()).
// Existing lifecycle:   start.state  ∈ "idle" | "classifying" | ... | "started"
//                        start.proposal  (null until a proposal is shown)
//
// This WP renders a cold-start block ONLY when:
//   start.state === "idle" && draft === "" && start.proposal === null
//
// The block contains a soft welcome line + example chips. Clicking a chip:
//   setDraft(chipText)   // prefill the intent box
//   (and MAY immediately submit via the existing submit()/propose() path)
//
// Chip set (from the design / TDD): "Fix something that's broken",
// "Add a new feature", "I'm not sure yet".
export function StartFromIntent(props: Props): JSX.Element
```

Invariants the contract MUST preserve:
- The chips/welcome render **only** on the idle + empty-draft + no-proposal
  state, and **disappear** once the draft is non-empty or a proposal is shown
  (TDD Proof: "chips do not render once a proposal is shown or the box is
  non-empty").
- Chips are real focusable controls (`<button>`), keyboard-operable, with the
  `--ring` focus treatment; colour is never the only signal (each chip carries
  a text label) — SPEC a11y; WPF-06.
- Clicking a chip reaches `propose()` through the **existing** path (no parallel
  start path; ADR-001) — verified via the injected `streamStartFromIntent` fake.
- Design tokens only (WPF-07); headings degrade to Inter (Satoshi not loaded);
  the green "Start this work"/confirm button styling is untouched here (its
  AA-large contrast handling is a design-time Blue-step note, not this WP's
  scope to restyle beyond keeping label bold/≥16px if touched).
- The existing confirm-gate / started / error paths are **unchanged** (reuse
  guard).

## Definition of Done

### Red — Failing tests written
- [ ] `apps/cockpit/client/src/tests/StartFromIntent.test.tsx::cold_start_chips_render_on_empty_idle` — on idle with an empty box and no proposal, the chips + welcome render.
- [ ] `apps/cockpit/client/src/tests/StartFromIntent.test.tsx::chip_click_fills_intent_box` — clicking a chip puts its text in the intent box (and reaches `propose()` via the injected fake; assert the fake was called or the proposal appears).
- [ ] `apps/cockpit/client/src/tests/StartFromIntent.test.tsx::chips_hidden_when_draft_non_empty` — typing in the box hides the chips/welcome.
- [ ] `apps/cockpit/client/src/tests/StartFromIntent.test.tsx::chips_hidden_when_proposal_shown` — once a proposal is shown, the chips are gone.
- [ ] `apps/cockpit/client/src/tests/StartFromIntent.test.tsx::chips_keyboard_focusable_with_visible_focus` — chips are Tab-reachable with a visible focus ring.
- [ ] jest-axe on the cold-start state — no violations (WPF-06).
- [ ] **Reuse-guard regression (MUST keep green):** the existing `StartFromIntent.test.tsx` proposal-before-start (confirm gate), started, and error tests still pass unchanged — proof the start machine was not altered.

### Green — Implementation makes tests pass
- [ ] Cold-start block added to `StartFromIntent.tsx`, gated on `state === "idle" && draft === "" && proposal === null`.
- [ ] Chips wired to `setDraft` (+ existing `submit()`/`propose()`); no new lifecycle/state added.
- [ ] CSS for the block added to `apps/cockpit/client/src/styles/StartFromIntent.module.css` using design tokens only.
- [ ] All Red tests pass; all pre-existing `StartFromIntent.test.tsx` tests pass.
- [ ] Implementation follows `boring-code.md` — explicit conditions, no metaprogramming.

### Blue — Refactor complete
- [ ] The chip list is a single declarative array mapped to buttons (no copy-pasted markup) — WPF-01/WPF-13.
- [ ] The empty-state visibility condition is a single readable predicate (e.g. `showColdStart`).
- [ ] No new behaviour introduced in Blue; the confirm-gate path remains byte-for-byte behaviourally identical.
- [ ] All tests still green; lint + typecheck clean (WPF-14 workspace-deps-built if required).

## Sequence

- **dependsOn:** none (target branch provides `StartFromIntent`, its CSS module,
  `useStartFromIntent` with the injectable `streamStartFromIntent` fake, and the
  signed visual contract — all satisfied prerequisites).
- **blocks:** none.
- **Parallelisable with:** WP-001, WP-002 (different files / different test scope).

## Estimated Token Cost

- **Input:** ~8k (this WP + `StartFromIntent.tsx` + `useStartFromIntent.ts` + the CSS module + ADR-001)
- **Output:** ~4k (the component edit + CSS + extended test file)
- **Total:** ~12k

## Notes

- Chip copy comes from the TDD / design: "Fix something that's broken",
  "Add a new feature", "I'm not sure yet". Confirm against MOCKUP state 2 at
  implementation time; the signed mockup is the visual source of truth.
- Whether a chip click submits immediately or only prefills is the
  implementer's call within the contract — both satisfy "rides the existing
  `propose()` path". Default to prefill-and-submit for the two concrete chips
  and prefill-only for "I'm not sure yet" (it has no concrete intent yet).
