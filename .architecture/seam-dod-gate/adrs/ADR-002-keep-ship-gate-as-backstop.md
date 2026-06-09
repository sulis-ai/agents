# ADR-002 — Keep the ship-stage acceptance gate (4.8) as a backstop; do not replace it

- **Status:** accepted
- **Change:** CH-01KTP7 (`feat` · `seam-dod-gate`)
- **Date:** 2026-06-09

## Context

This change re-times the real-data acceptance drive from the ship stage (gate
4.8 in `change/SKILL.md`) to seam-close. A reasonable reading is "the seam-close
gate replaces the ship gate — the catch moved, so the old site is redundant."

## Decision

**Keep the ship-stage gate (4.8) as a backstop. The seam-close gate moves the
*primary* catch earlier; it does not remove the ship-stage drive.** Defence in
depth, not replacement.

## Why (the recommendation, lead position)

The seam-close gate fires inside the build loop at the per-WP done-transition.
That transition can be **bypassed**: a manual / non-train merge, a WP shipped
outside the normal loop, a project that disables evidence emission, or a seam
that closes in a code path the hook didn't see. If the seam-close gate were the
*only* drive, any such bypass leaves a hole — exactly the "ships green but never
works" failure the program exists to kill, reintroduced through a different
door.

Both gates run the **same runner** (`sulis-verify-acceptance`) over the **same**
observed-or-blocked verdict-invariant, so keeping both is cheap and consistent —
no second decision rule, no second runner. The ship gate becomes a final
backstop that catches any seam the earlier gate missed; in the common case it is
a fast re-confirmation of already-green seams.

This matches the established defence-in-depth convention for blocking gates:
an earlier, cheaper check plus a final authoritative check at the boundary
that actually ships.

## Alternatives considered

- **Replace the ship-stage gate entirely with the seam-close gate.**
  **Rejected:** leaves a hole if the seam-close hook is bypassed (manual merge,
  evidence disabled, unusual close path). The whole point of the program is that
  no un-driven seam reaches "done" silently; a single removable gate
  re-introduces that risk.

## Consequences

- Two gate sites, one runner, one decision rule (`gate_decision` reused at both).
- The ship gate's wording is unchanged by this ADR; the seam-close gate is added
  alongside it. (CF-12 documents the timing relationship: seam-close primary,
  ship backstop.)
- A green seam may be driven twice (once at seam-close, once at ship). Wasteful
  but correct; acceptable for the safety it buys.
