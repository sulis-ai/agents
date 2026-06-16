# Inspiration — cockpit product experience

Real-world structural patterns the refined product experience draws on, per
founder concern. The founder asked for Mobbin as the primary source; the Mobbin
MCP (`mcp__plugin_honest_mobbin__search_screens`) was **not connected to this
session**, so — per the "never fabricate references" rule (UXD-15) — I did **not**
invent Mobbin screen URLs. Instead I grounded each pattern in the **documented,
shipped behaviour** of the apps the founder named (Linear, Notion, Vercel, Height,
GitHub Projects), sourced from each product's own docs/changelog (links below).

The probe scope is strict (UXD-15): **structure transfers — section ordering,
density, the micro-interaction beats — visual choices do NOT.** Every colour,
font, radius and spacing in the mockup is the cockpit's own `tokens.css`. We are
borrowing *how these controls behave*, never *how they look*.

See `_mobbin-context.md` for the structural-pattern notes distilled per concern.

---

## Concern A — Switching / filtering the board by product (the "All vs scoped" model)

The recurring shape across every workspace tool: a **single scope control in the
top-left of the persistent chrome**, where the top of its menu is the *unscoped*
"everything" option and the products/teams/projects list below it. Scope is a
**filter you layer on**, not a place you navigate into — picking a product
re-scopes the same board in place.

- **Linear** — the workspace switcher sits top-left; "All teams" / "All issues"
  views sit at the top of the scope, with each team's view below; scope is
  expressed as a saved filter on one list, not a separate destination.
  ([Custom Views](https://linear.app/docs/custom-views),
  [Filters](https://linear.app/docs/filters),
  [Concepts](https://linear.app/docs/conceptual-model))
- **Vercel** — a top-left team/scope switcher; the project list filters within the
  chosen scope; "all projects in the selected scope" is the default read.
  ([Moving between teams and projects](https://vercel.com/changelog/improved-experience-for-moving-between-your-teams-and-projects),
  [Projects overview](https://vercel.com/docs/projects))
- **GitHub Projects / Notion** — the same "one list, scoped by a filter chip" shape;
  the unscoped "all" view is the resting default and each scope is reachable in one
  click. ([Notion list view](https://www.notion.com/help/lists))

*Steal (structure only):* keep the **top-left scope control**; make **"All" the
explicit, always-present top item** (an everything-tile, not a blank); express the
active scope **in the chrome at all times** so the founder never wonders "what am I
looking at". *Reject (visuals):* their palettes, their avatar colours, their type.

## Concern B — Seeing & changing a change's product (replace the raw `<select>`)

Every one of these tools represents an item's parent/owner as a **labelled,
click-to-edit property** in the detail view — never a bare OS dropdown. The
resting state is a **value chip** (often with the parent's monogram/icon); clicking
it opens a **searchable menu (combobox)** in a popover; choosing **commits
immediately, no Save button**; the chip updates in place.

- **Linear** — the issue's **Project** / **Assignee** / **Labels** are properties in
  the detail sidebar; click the value to open a searchable menu, pick, and it
  commits instantly (also `A`-to-assign as a keyboard accelerator).
  ([Assign and delegate issues](https://linear.app/docs/assigning-issues))
- **Notion** — page properties are **inline, click-to-edit**: the value renders as a
  chip/select and is edited in place with no separate save step.
  ([Database properties](https://www.notion.com/help/database-properties),
  [Layouts](https://www.notion.com/help/layouts))
- **Height / GitHub Projects** — same property-row idiom: a labelled field whose
  value is a chip, opening a typeahead menu, committing on select.

*Steal (structure):* the **labelled property row → value chip → searchable popover →
commit-on-select** beat, and the **"Unassigned" empty value reads as a real,
clickable state** (not a disabled placeholder). *Reject (visuals):* keep our
monogram tile neutral (a locked cockpit decision), our tokens, our type.

## Concern C — Surfacing unassigned changes & making assignment feel lightweight

Two reinforcing patterns:
- **Unassigned is a first-class bucket**, not an absence. Linear's "No project" /
  GitHub's "No milestone" appear as a real, selectable group you can filter to.
- **Assign in context, cheaply.** Linear lets you assign from the **board card**
  (click the property) and from the **list row**, not only the detail — the same
  popover, surfaced wherever the item lives.
  ([Assigning issues](https://linear.app/docs/assigning-issues))

*Steal:* make **"Unassigned" an explicit scope** in the switcher (so the founder can
see exactly what still needs a home), and let the **same product control be
reachable from the board card on hover**, not only deep in the detail.

## Concern D — How setup connects (products / projects / repos)

- **Linear / Vercel** — "**＋ Create / set up**" lives **at the foot of the same
  scope switcher**, so creating a new scope is one click from where you switch
  scope; deeper structural management lives in Settings.
  ([Vercel projects](https://vercel.com/docs/projects))

*Steal:* keep "Set up a new product" **in the switcher menu foot** (it already is),
and make the **switcher → Settings** path obvious, so "switch / create / manage"
form one coherent spine rather than three disconnected entry points.

---

### Sources

- Linear: [Custom Views](https://linear.app/docs/custom-views) ·
  [Filters](https://linear.app/docs/filters) ·
  [Conceptual model](https://linear.app/docs/conceptual-model) ·
  [Assigning issues](https://linear.app/docs/assigning-issues) ·
  [Sidebar redesign](https://linear.app/changelog/2022-01-20-linear-preview-new-sidebar-and-team-icons)
- Notion: [Database properties](https://www.notion.com/help/database-properties) ·
  [Layouts](https://www.notion.com/help/layouts) ·
  [List view](https://www.notion.com/help/lists)
- Vercel: [Moving between teams and projects](https://vercel.com/changelog/improved-experience-for-moving-between-your-teams-and-projects) ·
  [Projects overview](https://vercel.com/docs/projects)

**Honest provenance note:** these are web-sourced from each product's own
documentation/changelog, describing patterns that are stable and publicly
documented. They are cited as **structural references** (how the control behaves),
not as Mobbin screen captures. If the Mobbin MCP is connected on a later pass, the
same concerns can be re-probed for additional shipped examples — the structural
recommendations below would not change, only the citation count.
