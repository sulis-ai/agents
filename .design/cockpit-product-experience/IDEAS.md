# Cockpit product experience — ideas

The founder added several product-scoping pieces fast, and they feel "a bit
hacky": a product switcher with a quickly-added "All" option, and — the sharpest
pain — a **raw native dropdown** jammed into a change's nav for assigning it to a
product. This pass refines the whole thing into one coherent experience. As with
the signed board refresh, everything here is built on the cockpit's **real**
colours, fonts and spacing (`apps/cockpit/client/src/tokens.css`) — nothing
invented — and rendered in `MOCKUP.html` (light + dark). The structural patterns
are grounded in how Linear, Notion and Vercel actually behave (`INSPIRATION.md`);
their *looks* are theirs, our *tokens* are ours.

A quick orientation first, because it shapes every recommendation. The data model
is a simple nesting: a **Tenant** has **Products**; a Product has **Projects**; a
Project points at a git repo; a **Change** optionally belongs to one Product (the
`for_product` link). **Most changes are unassigned** — they live under "All". So
the guiding principle throughout is: **product is a light scope you lay over the
board, not a place you go — and assigning a change to one should feel as cheap as
ticking a box, from wherever you happen to be looking at it.**

The four concerns:

- **A — Scope model:** how the founder switches/filters the board by product.
- **B — The change's product control:** replacing the raw `<select>`.
- **C — Unassigned changes:** surfacing them and making assignment lightweight.
- **D — Setup spine:** how product / project / repo setup connects to all this.

---

## Concern A — The scope model ("All vs a product")

**Today:** a top-left **product switcher** with an "All" item at the top (default)
and each product below; the header reads "Viewing: All / <Product>". It works, but
the "All + filter" model was bolted on quickly, the trigger's visual treatment is
basic, and "All" reads as just another product rather than as "everything".

**The principle** (from Linear, Vercel, GitHub Projects): product is a **filter you
layer on one board**, not a destination you navigate into. The unscoped
"everything" view is the **resting default and the explicit top item**; each product
is a scope below it; picking one **re-scopes the same board in place**. The active
scope is **always named in the chrome** so the founder never wonders what they're
looking at.

### Options

- **A1. Keep the top-left switcher, but make it considered (recommended).**
  Same shape the founder already has — a top-left control that opens a menu — but
  refined into a real, deliberate control:
  - **"Viewing" → an explicit scope.** The trigger shows the scope's monogram tile +
    its name + a chevron, exactly as now, but **"All" gets its own treatment**: an
    "everything" tile (a small grid-of-dots glyph, not two letters) and the word
    **"All products"**, so it reads as "everything", not as a product called "All".
  - **A count on each row.** Every menu row shows how many changes are in that scope
    (e.g. "All products · 23", "Clinics · 6", "Unassigned · 9"), so the founder sees
    the shape of their work before switching — the same "counts do double duty"
    trick the board's stage chips use.
  - **"Unassigned" becomes a real scope** in the menu (see Concern C), sitting just
    under "All products".
  - **The header echoes the scope.** A quiet "Viewing <scope>" stays in the chrome;
    when scoped to a product it also offers a one-tap "× clear" back to All.
  *Why:* it keeps the model the founder already learned (lowest change, Jakob's
  Law), fixes the two real faults ("All" reading as a product; a basic trigger), and
  matches every workspace tool's "scope is a filter, expressed in the top-left
  chrome" pattern.
  *Informed by:* Linear workspace switcher + "All teams" views; Vercel scope
  switcher; the counts idiom from the board's own stage chips.

- **A2. A left sidebar of products.** A persistent rail listing All / Unassigned /
  each product down the left. Powerful when there are *many* scopes — but it spends
  a permanent column of width on a list that, for most tenants, is 1–3 products, and
  it competes with the change's own left-nav inside an open change. Heavier than the
  problem.

- **A3. A row of tabs** (All · Clinics · …) across the top under the chrome. Reads
  well at 2–4 products but breaks down past ~5 (overflow/scroll), and a tab strip
  says "these are peer destinations" — which fights the "All is everything, products
  are filters" hierarchy. The board already has a stage-chip row; a second chip/tab
  row would crowd it.

**Recommendation: A1.** It's the smallest, most coherent move — it keeps the
founder's existing mental model and the existing top-left placement, and just makes
the control *considered*: "All products" reads as everything, counts give shape,
"Unassigned" becomes reachable. The sidebar (A2) and tabs (A3) both spend more
screen and impose a heavier model than a 1–3-product tenant needs. The mockup shows
A1 open, with the everything-tile, the counts, and "Unassigned" in place.

### Accessibility

- The trigger is a real `<button>` with `aria-haspopup="menu"` / `aria-expanded`;
  the menu is `role="menu"` with `role="menuitemradio"` rows and `aria-checked` on
  the active scope (this already matches the current component).
- The active scope is carried by a **tick + bold weight + the header label**, never
  by colour alone — strip colour and the ticked, bolder row is still the active one.
- "All products" is distinguished from a product by **a different glyph + different
  words** (grid tile + "All products"), not by colour.
- Counts are real text in the accessible name ("All products, 23 changes"), so a
  screen reader hears the shape too.
- Full keyboard: open on Enter/Space, arrow between rows, Escape closes (already
  present); the trigger keeps a visible `:focus-visible` ring (`--ring`).

---

## Concern B — The change's product control (replace the raw `<select>`)

**Today — the acute one:** a **raw native `<select>`** sits under the stage track in
a change's left-nav. It's functional and (being native) accessible, but it looks
crude, it's visually unrelated to everything around it, and it sits oddly between
the stage track and the views. It reads as "a control someone dropped in", which is
exactly the hacky feeling the founder named.

**The principle** (from Linear, Notion, Height): an item's parent is a **labelled,
click-to-edit property** — a quiet **value chip** at rest, a **searchable popover**
on click, **commit-on-select with no Save button**, the chip updating in place.
Never a bare OS dropdown.

### Options

- **B1. A labelled "Product" property with a chip + a menu popover (recommended).**
  In the change's left-nav, a proper little property:
  - **Label:** a quiet "Product" in the same muted small-caps the nav already uses
    for its "Views" / "Stage" section labels — so it belongs to the nav, not floats
    in it.
  - **Value chip (assigned):** the product's neutral **monogram tile + its name** +
    a small chevron — visually a sibling of the top-bar switcher's trigger, so the
    "product" idea looks the *same* everywhere (one vocabulary).
  - **Value chip (unassigned):** a real, clickable **"＋ Add to a product"** chip in
    the muted/dashed "no signal yet" language the board already uses for absence —
    not a disabled "Assign a product…" placeholder. Unassigned is a state you can
    act on, not a greyed nothing.
  - **The menu:** clicking the chip opens a **popover** (the same surface the
    switcher uses) listing the founder's products, the current one ticked, a
    typeahead search when there are many, a **"Remove from product"** option when
    assigned, and a **"Set up a new product"** foot — so you can assign, reassign,
    unassign, or create, all from one place.
  - **Commit-on-select:** picking a product **commits immediately** (the endpoint
    the current picker already calls), the chip swaps to the new product, and a
    brief **"Saved" tick** confirms. No Save button, no modal.
  *Why:* it kills the raw `<select>`, makes "product" one consistent visual idea
  across the switcher and the change, and matches the property-row idiom from every
  tool the founder named. It's also the same popover component as the switcher —
  one thing to build, two homes.
  *Informed by:* Linear's Project/Assignee properties (click value → searchable menu
  → commit instantly); Notion inline editable properties (no Save step).

- **B2. Keep a dropdown but style it as a custom select.** Less work, but a styled
  select still reads as "a dropdown bolted on" and can't carry the
  monogram chip, the "Unassigned" affordance, search, or "create new" — it papers
  over the hacky feeling rather than resolving it.

- **B3. Inline-editable text field** (type the product name). Wrong model — products
  are a known small set, not free text; a menu is faster and prevents typos/
  mismatches. (We'd only reach for this if products were unbounded free-form, which
  they aren't.)

**Recommendation: B1.** It's the direct, considered replacement for the `<select>`:
a labelled property, a chip that speaks the same "product" language as the switcher,
a searchable menu, commit-on-select, and a real "Unassigned" affordance. It turns
the most hacky-feeling control into the most polished one. The mockup shows it in
the change nav in all three states — assigned, unassigned, and mid-menu.

### Where it sits on the change

In the change's left-nav, **moved out from under the stage track** to sit with the
change's *identity* (just under the change name + stage badge, above the "Views"
section), because "which product owns this" is an identity fact, not a navigation
control. Grouping it with the name/stage matches how Linear groups an issue's
Project with its other identity properties, and stops it reading as a stray control
wedged between the stage track and the views.

### Accessibility

- The chip trigger is a real `<button>` with `aria-haspopup="menu"` /
  `aria-expanded`; the popover is `role="menu"` with `aria-checked` radios — the
  same proven pattern as the switcher, so one accessible model covers both.
- The unassigned chip has a clear accessible name ("Add this change to a product")
  and is keyboard-reachable; "Unassigned" is conveyed by **word + dashed shape**,
  never colour alone.
- **Commit feedback isn't colour-only:** the "Saved" confirmation is a **tick icon +
  the word "Saved"**, briefly, with an `aria-live="polite"` announcement so a screen
  reader hears it; while the request is in flight the chip shows a "Saving…" text
  state (the current picker disables during the mutation — preserved).
- Search field inside the menu is a labelled `<input>`; arrow keys move the
  highlighted option, Enter commits, Escape closes — full keyboard parity with the
  mouse path.
- Touch targets: the chip and every menu row are ≥ 44px tall.

---

## Concern C — Unassigned changes & lightweight assignment

**Today:** unassigned changes simply appear under "All", with no way to see *just*
the ones still needing a home, and assigning means opening the change and using the
raw `<select>`. Assignment is neither visible nor cheap.

**The principle** (from Linear "No project" / GitHub "No milestone"): **"unassigned"
is a first-class bucket, not an absence** — you can scope to it and clear it in a
sweep; and **assignment is reachable in context** (from the card, the row, the
detail), using the *same* control everywhere.

### Recommendations (three small, reinforcing moves)

- **C1. "Unassigned" is an explicit scope in the switcher.** Just under "All
  products", an **"Unassigned · N"** scope (with the dashed "no signal yet" tile)
  filters the board to exactly the changes with no product. Now "what still needs a
  home?" is one click, and the count tells the founder how big the pile is at a
  glance. *Informed by:* Linear's "No project" / GitHub's "No milestone" as
  selectable groups.

- **C2. Assign from the board card, in context.** On a board card, when it's
  unassigned, a **quiet "＋ Product" affordance** appears on hover/focus (and is
  always present, not hover-only, for keyboard/touch — hover only *emphasises* it).
  Clicking opens the **same product popover** as the change nav, so the founder
  assigns without opening the change. When a card *is* assigned, it carries a small,
  quiet **product monogram chip** in its foot-meta so the board reads product
  membership at a glance under the "All" scope. *Informed by:* Linear assign-from-card.
  *(Honest note: this rides the board card, which is the board-refresh's territory —
  see the build note. It's offered as the lightweight-assignment answer; if it
  crowds the card it can ship as detail-only first.)*

- **C3. One consistent product vocabulary.** The **same monogram-chip + popover**
  is the product control in all three homes — the top-bar switcher (scope), the
  change nav (this change's product), and the board card (assign-in-context). One
  thing to learn, one thing to build, three placements. This consistency *is* the
  refinement: today's hacky feeling comes partly from three unrelated-looking
  product touchpoints (a switcher, a `<select>`, nothing on the card); making them
  one vocabulary is what makes the experience feel considered.

**Recommendation: C1 + C3 firmly; C2 as the lightweight-assignment answer, with an
honest "detail-first if it crowds the card" fallback.** C1 (unassigned as a scope)
and C3 (one vocabulary) are pure wins and cheap. C2 is the nicest assignment beat
but lands on the board card, so it's sequenced behind / alongside the board refresh.

### Accessibility

- The "Unassigned" scope is conveyed by **word + dashed tile**, distinct from both a
  product and from "All products" — never colour alone.
- The board-card "＋ Product" affordance is **always in the DOM and keyboard-
  reachable** (hover only changes emphasis, never presence), with a clear accessible
  name ("Add this change to a product"); ≥ 44px target.
- The card's assigned-product chip exposes the product name as text (in the card's
  accessible name), so a screen reader hears which product a card belongs to.

---

## Concern D — How setup connects (the spine)

**Today:** product/project/repo setup lives in a Settings page (ProductRow /
ProjectRow / RepoRow / AttachRepoForm); the older chat onboarding is the cold-start
path; "Set up a new product" routes to the Settings form. The pieces work but feel
disconnected from the switcher.

**The principle** (Linear, Vercel): **switch / create / manage form one spine.**
Creating a new scope is one click from where you switch scope (the switcher menu
foot); deeper structural management lives in Settings, reachable from the same place.

### Recommendation

- **D1. Keep "Set up a new product" at the switcher menu foot** (it already is) — so
  "create" sits next to "switch". Add a quiet **"Manage products"** item beside it
  that routes to Settings, so "switch / create / manage" are one coherent group in
  one menu. The Settings page itself is unchanged in this pass (it's already a
  considered tree) — this concern is only about **connecting** it to the switcher so
  the spine reads as one idea. *Informed by:* Linear/Vercel "create at the switcher
  foot, manage in settings".

- **Cold-start unchanged.** The chat onboarding stays the empty-tenant path; once a
  product exists, the switcher + the property control are the everyday surfaces. No
  change to onboarding in this pass.

**Recommendation: D1 (light touch).** Setup is genuinely the least-broken of the
four concerns; the only refinement needed is to make the switcher the obvious
front door to create/manage, which is a two-item menu-foot change. The mockup shows
the switcher menu with both "Set up a new product" and "Manage products" at the
foot.

### Accessibility

- Both foot actions are real menu items with clear labels and the menu's keyboard
  model; "Set up a new product" keeps its `＋` icon + word, "Manage products" a gear
  + word — icon **and** word, never icon-only.

---

## The one consistent idea across all four concerns

The refinement isn't four separate fixes — it's **one product vocabulary** applied
in three places, plus making "All" and "Unassigned" honest scopes:

1. **One control, three homes.** The neutral **monogram-chip + searchable popover**
   is *the* way "product" is shown and changed everywhere — the top-bar **switcher**
   (which scope am I viewing), the change-nav **property** (this change's product),
   and the board **card** (assign in context). Same look, same behaviour, same
   keyboard model. (Replaces: the basic switcher trigger, the raw `<select>`, and
   "nothing on the card".)
2. **"All" and "Unassigned" are real, explicit scopes** — "All products" with an
   everything-tile, "Unassigned" with a dashed tile, each with a live count — not a
   product called "All" and an invisible pile of orphans.
3. **Commit-on-select, no modals.** Assigning/reassigning/unassigning a change is
   one click that commits immediately with a "Saved" tick — the cheapest possible
   beat, reachable from the card or the detail.
4. **Switch / create / manage are one spine** off the switcher menu.

Across all four: **colour is always reinforcement, never the only signal** — "All"
vs a product vs "Unassigned" differ by glyph + words; the active scope by tick +
weight; "Saved" by tick + word; unassigned by dashed shape + word — and everything
is keyboard-reachable with a visible focus ring, ≥ 44px touch targets, and a
reduced-motion-safe "Saved" confirmation.

---

## Accessibility — the consolidated pass (the founder asked for this explicitly)

Re-run point-by-point and measured against the **real** `tokens.css` in **both**
light and dark.

**1. Never colour alone — every state is word + shape/glyph.**
- Scope rows: "All products" (grid tile) vs a product (monogram) vs "Unassigned"
  (dashed tile) — told apart by **glyph + words**; the active scope by **tick + bold
  weight**, not colour.
- The change's product chip: assigned = monogram + name; unassigned = dashed "＋ Add
  to a product". Different **shape + words**, zero reliance on colour.
- "Saved" confirmation = **tick icon + the word "Saved"** + an `aria-live` announce,
  never a colour flash alone.

**2. AA contrast — verified light + dark against the real tokens.** Every text label
clears WCAG AA (4.5:1) and every graphical cue clears the 3:1 bar (WCAG 1.4.11), in
both themes. The control reuses the **exact** token pairings the signed switcher and
board already use, so the numbers inherit from already-verified contracts:

| Element (text) | Light | Dark |
|---|---:|---:|
| Switcher trigger product name (`--text` on `--card`) | 16.1:1 ✓ | 11.6:1 ✓ |
| "Viewing" / scope label (`--text-muted` on `--card`) | 4.7:1 ✓ | 5.5:1 ✓ |
| Menu row name (`--text-secondary` on `--card`) | 7.5:1 ✓ | 5.5:1 ✓ |
| Scope count (`--text-muted` on `--card`) | 4.7:1 ✓ | 5.5:1 ✓ |
| Product chip name in change nav (`--text` on `--card`) | 16.1:1 ✓ | 11.6:1 ✓ |
| "Add to a product" (dashed chip, `--text-secondary`) | 7.5:1 ✓ | 5.5:1 ✓ |
| "Saved" confirmation (`--positive`-tinted, label `--text`) | 16.1:1 ✓ | 11.6:1 ✓ |
| Monogram tile letters (`--text-secondary` on `--muted`) | 7.2:1 ✓ | 6.4:1 ✓ |

| Element (graphical, 3:1 bar) | Light | Dark |
|---|---:|---:|
| Active-row tick (`--accent`) | 3.4:1 ✓ | 5.0:1 ✓ |
| Menu/chip border (`--border` on `--card`) | — (decorative) | — |
| Dashed "Unassigned" tile edge (`--input`) | 3.3:1 ✓ | 3.4:1 ✓ |
| Focus ring (`--ring`, 2px) | 3.4:1 ✓ | 5.0:1 ✓ |

(The labels are the load-bearing carriers; the tick, the dashed edge and the focus
ring are the only graphical cues that must clear 3:1, and each does in both themes.)

**3. Keyboard + screen reader.**
- Trigger and chip are real buttons (`aria-haspopup`, `aria-expanded`); menus are
  `role="menu"` with `aria-checked` radios; the search field is a labelled input;
  arrow/Enter/Escape all work; the visible `:focus-visible` ring (`--ring`) is on
  every interactive element.
- Scope and product names ride the accessible name *with* their counts ("All
  products, 23 changes"; "Clinics product, 6 changes").
- "Saved" is announced via `aria-live="polite"`; the in-flight state announces
  "Saving…".

**4. Reduced motion.** The only motion is the menu's open transition and the "Saved"
tick's brief fade; both have a `prefers-reduced-motion: reduce` fallback that drops
the animation and shows the end state immediately. (The "Saved" word stays — motion
was never the carrier.)

**5. Touch + responsive.** Every trigger, chip and menu row is ≥ 44px tall on touch.
At narrow widths the switcher trigger condenses to its monogram tile + chevron (the
scope name folds, but stays on the accessible name), exactly as the existing top bar
already folds — one consistent responsive rule.

---

## Honest build note — what the data feed already supports vs what's new

Checked against the real wire types (`apps/cockpit/shared/api-types.ts`), the
current components (`ProductSwitcher.tsx`, `ProductPicker.tsx`, `ChangeNav.tsx`,
`WorkspaceTopBar.tsx`) and the assign endpoint (`assignChangeProduct.ts`).

| Piece | State of the data / wiring today |
|---|---|
| **Switcher refinement (A1)** | **Mostly free.** `ProductList` already carries `products[]` + `activeProductId`; the switcher already re-scopes in place via `onSelect(null \| productId)` (null = All). The refinement is **client-only chrome**: the everything-tile + "All products" wording, the chip polish, the header echo. **New data:** the **per-scope counts** ("All · 23", "Clinics · 6", "Unassigned · 9") — the board feed already returns the changes, so the All/per-product counts can be computed **client-side** from the already-fetched list; only the "Unassigned" count needs the feed to expose `forProduct` on each `Change` (it already does — `Change.forProduct` is on the wire). So counts are **derivable client-side today**, no new endpoint. |
| **"Unassigned" scope (C1)** | **Free.** `Change.forProduct` is already on the board feed (`?: string \| null`). Filtering to "no product" is a client predicate over the list the board already has; the count likewise. The only server consideration is if the board feed is *server-paginated by product* — then an "unassigned" filter value needs to be accepted server-side; if the feed returns the full list and the client filters, it's pure client work. |
| **The change's product property (B1)** | **The write already exists; the control is new chrome.** `useAssignChangeProduct(changeId)` + `assignChangeProduct.ts` already do the commit, and `useProducts()` already lists the products — the **current raw `<select>` calls exactly this**. B1 reuses both verbatim; what's new is the **presentational control** (chip + popover + "Saved" tick + the unassigned/remove affordances). **One genuinely new write:** **unassign** ("Remove from product") — today the picker can only *set* a product (its `<option value="">` is `disabled`); clearing a change back to unassigned needs the endpoint to accept a null/empty product id (or a small `DELETE`-shaped variant). Worth confirming the assign endpoint accepts "unassign". |
| **Assign-from-card (C2)** | **Write is free; the surface is the board card.** The same `assignChangeProduct` write powers it. The new part is **placing the chip/affordance on the board card** — which is the board-refresh's component, so this is **sequenced with that work**. The data it needs (`Change.forProduct` for the assigned-chip; the product list for the menu) is already on the feed. Honest fallback: ship B1 (detail) first, add C2 (card) alongside the board refresh. |
| **Setup spine (D1)** | **Free.** "Set up a new product" already routes to `/settings?new=product`; adding a "Manage products" item that routes to `/settings` is a one-line menu addition. No new data. |

**Summary of free vs new:**
- **Free today (client chrome over existing data/writes):** the refined switcher
  (A1), the "Unassigned" scope + all the counts (C1) — both derivable from
  `Change.forProduct`, already on the wire — the new product property *control* (B1)
  over the existing assign write, and the setup-spine menu items (D1).
- **One small new write:** **unassign** (clear a change's product back to "All") —
  the current endpoint only sets a product; B1's "Remove from product" needs it to
  accept an empty/null value.
- **Sequenced (lands on the board card):** assign-from-card (C2) — same write, new
  placement, best shipped with the board refresh.

So the refinement is **overwhelmingly a presentation/coherence change over data and
writes that already exist** — exactly what you'd hope for "make the hacky bits feel
considered". The single functional gap is the unassign write; everything else is the
same data and the same endpoint, dressed in one consistent, accessible product
vocabulary.

The mockup carries every token verbatim from `tokens.css` (light + dark) and shows
all three control homes — the refined switcher (open, with counts + "All products" +
"Unassigned"), the change-nav product property (assigned / unassigned / mid-menu),
and the board card with its quiet product chip and the in-context "＋ Product"
affordance.
