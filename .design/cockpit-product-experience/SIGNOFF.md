# Sign-off — Cockpit product experience

```yaml
status: signed-off
provenance: production-approved
signed_off_at: 2026-06-16T12:08:00Z
signed_off_by: founder
artifact: MOCKUP.html + IDEAS.md
```

The founder reviewed `MOCKUP.html` (light + dark) and the recommendations in
`IDEAS.md` and signed off ("Looks good"). This design is the locked visual +
behavioural contract for the cockpit product-experience refinement; any build
of it is verified against this mockup.

## Scope signed off

- **Board scope switcher** — refined: "All products" as a distinct everything
  option, live per-option counts, "Unassigned" as a first-class choice.
- **The change's product control** — the single "Product" field + searchable
  menu (instant save, "Saved" tick, "＋ Add to a product" empty state),
  replacing the raw native `<select>`.
- **Unassigned view + assign-from-card** on the board.
- **Setup** — a "Manage products" link in the switcher menu.
- **The one genuinely new ability:** removing a change from a product
  (un-assign), not just assigning.

## Inspiration provenance (honest note)

The Mobbin tool was NOT connected this session. Patterns were grounded in
Linear / Notion / Vercel published design docs and cited honestly in
`INSPIRATION.md` + `_mobbin-context.md`. The founder signed off knowing this;
a Mobbin re-run was offered and deferred — it would add examples but the
designer judged it would not change the recommendations.
