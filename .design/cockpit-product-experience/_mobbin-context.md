# Structural-pattern notes (the "Mobbin-context" distillation)

Mobbin MCP status: **not connected this session** → `inspiration: web-sourced`,
not Mobbin screen captures. No screen URLs are fabricated (UXD-15). What follows is
the *structural* distillation — section ordering, density, micro-interaction beats —
drawn from the documented behaviour of the apps the founder named. **Visual identity
does not transfer; the cockpit's `tokens.css` stays authoritative.**

## Scope switcher (the "All vs a product" control)

- **Placement:** top-left of the persistent chrome, first thing read.
- **Menu ordering:** unscoped "everything" item **first**, a separator, then the
  scoped list, then the "create new" action at the **foot**. (Linear, Vercel.)
- **Density:** menu rows ~36–40px tall, monogram/icon + name + a trailing tick on
  the active row. Comfortable, not cramped.
- **Micro-interaction:** select → menu closes → the **same** board re-scopes in
  place (no route change, no full reload). The header label updates to name the
  scope. (Linear views, Vercel scope.)
- **"All" is a real item**, with its own everything-tile, never a blank/placeholder.

## Item → parent property (the change's product control)

- **Resting state:** a **labelled property** ("Product") whose value is a **chip**
  (monogram + name), or an **"Unassigned"** chip when empty — the empty value is
  itself clickable, not a greyed placeholder.
- **Edit beat:** click the chip → **popover with a searchable list** (typeahead when
  the list is long) → pick → **commits immediately, no Save** → chip updates, a
  brief "Saved" tick. (Linear project/assignee, Notion inline properties.)
- **Placement on the detail:** with the other identity properties, not jammed under
  an unrelated control. Linear groups Project/Assignee/Labels/Status together.
- **Density:** one property per row, label in muted small-caps/secondary, value chip
  at body size. Quiet until interacted with.

## Assign-in-context (lightweight assignment)

- The **same** product popover is reachable from the **board card** (on hover/focus
  a small "＋ product" affordance), not only the detail — assignment where the eye
  already is. (Linear assign-from-card.)
- **"Unassigned" is a filter/scope**, so the founder can pull up exactly the changes
  that still need a home and clear them in a sweep.

## Setup spine

- "Set up a new product" stays at the **switcher menu foot**; "Manage products"
  routes to Settings. Switch / create / manage read as one spine, three depths.
