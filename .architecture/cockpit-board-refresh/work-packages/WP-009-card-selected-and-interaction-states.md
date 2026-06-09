# WP-009 — Card alternate states: selected (route-derived) + interaction/focus

- **Sequence ID:** WP-009
- **dependsOn:** [WP-005]
- **kind:** frontend
- **primitive:** EXPAND-Create (selected marker) + REORGANISE-Refactor (`ChangeCard` focus styling)
- **group:** expand
- **characterisation_test:** `client/src/tests/ChangeCard.test.tsx` (WP-005's; re-asserts the card link + aria-label before adding the markers)
- **Estimated token cost:** input ~12k / output ~5k
- **visual_contract:** production-approved (`MOCKUP.html` — selected ring + focus ring)

## Context

SRD §7c CS-1 + CS-2. Two alternate card states that are **orthogonal to the
content verdict** and compose additively onto any card (precedence table, SRD
§7c): the card is **marked selected** when its change is the open route, and the
card is **fully keyboard-operable** with a **visible focus ring**. Both reuse
existing shell patterns (the Sidebar already does route-derived selection); the
**board card** has neither today.

## Contract

- **Selected marker (CS-1 / FR-50 / BR-20 / BR-21).** `ChangeCard` (or its lane
  parent) reads the active change id the **same way the shell does** —
  `useMatch("/c/:changeId")` → `activeChangeId` (`WorkspaceShell.tsx` line 18–19),
  reused, not reinvented. A card is selected when `change.changeId ===
  activeChangeId`. The marker is **not colour-alone**: `aria-current="true"` +
  a persistent non-colour signal (inset ring / left-edge marker), distinguishable
  in greyscale. **At most one** card selected; on a non-change route (`/`) **no**
  card is selected. Selection is **route-derived, never stored on the card or
  feed** — it survives a feed re-poll (carry-over of EF-3's last-good discipline).
- **Interaction / focus (CS-2 / FR-51 / BR-22 / BR-23).** The card-as-`<Link>` is
  already focusable + Enter-activates natively; this WP **pins the visible
  `:focus-visible` ring** on the card (NFR-A11Y-5) and asserts **no signal
  depends on hover** (everything reachable on hover is reachable on focus). The
  inner "Open terminal" control (when present, `ChangeCard.tsx` line 58–75) keeps
  its own focusable control + `stopPropagation` — card-link focus and the inner
  button are **distinct tab stops**. Space is not required to activate the link
  (ARIA link pattern); the card MUST NOT trap/swallow it.

These markers are **additive**: they never hide health, waiting, the probe, the
recency, or a degraded notice (SRD §7c precedence — selection + interaction are
always additive).

## Definition of Done

### Red
- [ ] `client/src/tests/ChangeCard.selected.test.tsx`:
  - rendered with the active route at `/c/:id` for one seeded change, **that**
    card carries `aria-current="true"` + the non-colour marker; **no other** card
    is marked; with the route at `/`, **no** card is marked (**S-32**).
  - selection survives a simulated feed re-poll (route unchanged → still marked).
  **Fails** (no selection awareness on the card).
- [ ] `client/src/tests/ChangeCard.focus.test.tsx`:
  - Tab reaches the card; it shows a visible `:focus-visible` ring and is in tab
    order; **Enter** navigates to `/c/:id`; the inner control is a separate tab
    stop; no signal depends on hover (**S-33**).
  **Fails** (focus ring not asserted/pinned).

### Green
- [ ] Selected marker + focus ring implemented (reusing `useMatch` selection);
      both tests pass.
- [ ] jest-axe on the card in **selected** and **focused** states, light + dark.

### Blue
- [ ] Selection read from the route only (grep: no `selected` field on the feed
      or local card state).
- [ ] Marker + focus ring use tokens (ring colour/width via tokens, not literals).
- [ ] Additive: a selected + waiting + unknown-liveness card still shows all
      three reads (precedence assertion).

## Definition of Done — requirements & scenarios

- **Satisfies:** CS-1 (FR-50, BR-20, BR-21), CS-2 (FR-51, BR-22, BR-23);
  NFR-A11Y-1, NFR-A11Y-5.
- **Makes pass:** **S-32** (selected card marked from the open route), **S-33**
  (keyboard-focus a card + activate it).

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/ChangeCard.selected.test.tsx
```
