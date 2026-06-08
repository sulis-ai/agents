---
founder_facing: false
---

# Spec — plan-work's done-check drives the real consumer (the WP tracker), not a header proxy

**Change:** CH-01KTMJ · harden

## Intent

When `/sulis:plan-work` (decompose) finishes, its Definition-of-Done must
prove the **builder can actually read the to-do list it just wrote** — not
merely that the list's table header is spelled correctly. Today the
decompose-time gate (`wpx-index lint`) validates the WP table *header shape*
via a regex. That is a proxy. It is structurally blind to a canonical-header
INDEX whose **status values** are wrong (`ready`/`blocked` instead of
`pending`), which makes the real builder consumer (`wpx-index list-ready`)
return an empty set — the builder sees zero tasks and the break surfaces
mid-build, not at creation.

This is a recurring failure-class, past the build-now threshold: #60 (closed),
#218, #222, #233, and the watchlist meta-diagnosis #97 — four distinct
recurrences in ~10 days. The fix is the methodology thesis applied one level
down: **verify the property that matters (the tracker can parse and drive the
INDEX), not a proxy for it.**

## Scope

- **Add a round-trip assertion to the decompose-time gate**: against the
  just-written `INDEX.md`, run the *exact* parse the builder runs
  (`wpx-index list-ready` / `_collect_status_across_tables` + `_resolve_deps`)
  and assert every authored `pending` WP is accounted for. A `0`-WP /
  parse-fail result while WPs exist is a **BLOCKING** decompose failure.
- **Lean path (preferred, to be confirmed at design): wire the round-trip
  INTO `wpx-index lint`** so plan-work's *existing* Step 9.5 wiring
  ("`lint` non-zero exit = decompose NOT done", `plan-work/SKILL.md` ~L467-482)
  enforces it for free — no new gate to wire, maximal enforcement, minimal
  surface. Design weighs this against a distinct `wpx-index verify` /
  `round-trip` subcommand.
- **Test-first (the point of this change)**: author failing tests FIRST that
  pin each recurrence variant, then make them pass. See Verification Plan.

## Non-goals

- **Not** changing what the canonical INDEX header *is* (that's #60's fix,
  already shipped) — this hardens the *gate*, not the template.
- **Not** fixing `list-ready`'s dependency-gating semantics (#76) — adjacent,
  but a separate change. This change consumes `list-ready` as-is; if its dep
  gating is wrong, that's tracked elsewhere.
- **Not** touching the scenario runner / verification-substrate change (#98) —
  this is a parallel track (plan-work + wpx-index only). No collision.
- **Not** rewriting `plan-work`'s decompose logic — only its done-check wiring.

## Acceptance

The gate behaves as a true round-trip against the real consumer. Pinned by
the test variant matrix (Verification Plan) — all four MUST hold:

1. An INDEX with **no WP table at all** → gate **FAILS**.
2. An INDEX with a **non-canonical header** (`| WP |`/`| Kind |`) → gate
   **FAILS** (#218/#233).
3. An INDEX whose WP **statuses are all non-`pending`** (`ready`/`blocked`)
   → gate **FAILS** (#222). *This is the case header-lint cannot catch and is
   the load-bearing addition.*
4. A **canonical INDEX with ≥1 `pending` WP** → gate **PASSES** (no
   false-positive).

And: plan-work's Step 9.5 surfaces a non-zero exit (decompose NOT done) for
cases 1–3, and exit 0 for case 4 — with a founder-readable error naming what's
wrong and the next step.

## Constraints

- **Test-first is a MUST** (EP-02): write each variant test, see it fail
  (cases 1–3 must fail against *today's* gate to prove the bug; case 4 must
  already pass), then implement until all four are green.
- **Single source of truth** (EP-03): the round-trip must reuse the same parse
  path the builder uses (`_collect_status_across_tables` / `_resolve_deps` /
  the `list-ready` accounting), so the gate can never disagree with the real
  consumer about what counts as a runnable INDEX. Do not re-implement parsing.
- **Reuse existing fixtures**: tests live near the existing wpx-index tests
  (`plugins/sulis/scripts/tests/unit/` — `test_wpx_index_status_vocab.py`,
  `test_wpx_index_columns.py`, `test_wpx_index_multitable.py`).
- **Assertion property**: "every authored `pending` WP is accounted for by
  `list-ready` (ready ∪ dependency-blocked)", NOT the weaker "ready ≥ 1" — a
  legitimately fully dep-chained INDEX can have 0 *immediately ready* WPs while
  every WP still round-trips. (Recorded decision; design finalises shape.)
- **Files in play**: `plugins/sulis/scripts/wpx-index` (`cmd_lint` /
  `cmd_list_ready`), `plugins/sulis/scripts/_wpxlib.py`
  (`validate_wp_index_header`, `parse_index_md`, `resolve_wp_columns`),
  `plugins/sulis/skills/plan-work/SKILL.md` (Step 9.5 / Definition of Done).
- **No third-party platform touch** — pure in-repo tooling; no Platform
  Contract needed.
- **On ship (watchlist hygiene)**: comment the build on #97 (structural fix
  shipped → graduates after clean executions); #218/#222/#233 can close.

## Verification Plan

How we will actually verify this works — the verification is the test variant
matrix, run against the real consumer's parse path. This is observed-or-blocked
applied to the INDEX artifact itself.

### Mechanism
Unit tests in `plugins/sulis/scripts/tests/unit/` (pytest), each constructing
an `INDEX.md` fixture and asserting the gate's exit/return. The gate under test
is whichever surface design picks (extended `lint` or new subcommand); the
tests assert *behaviour*, so they survive that choice.

### The variant matrix (test-first — author failing, then green)
| # | Fixture | Expected | Pins |
|---|---|---|---|
| 1 | INDEX with no WP table (prose only) | gate FAILS (non-zero) | #97 |
| 2 | Canonical-shaped but non-canonical header (`\| WP \| ... \| Kind \|`) | gate FAILS | #218, #233 |
| 3 | Canonical header, all statuses `ready`/`blocked` (none `pending`) | gate FAILS | #222 |
| 4 | Canonical header, ≥1 `pending` WP | gate PASSES (exit 0) | no false-positive |

### Wiring check
A test (or an existing plan-work self-check assertion) confirming Step 9.5's
"non-zero exit = not done" path treats cases 1–3 as decompose-not-done and
case 4 as done.

### Observable outcome
`pytest plugins/sulis/scripts/tests/unit/ -k <new test module>` is green; cases
1–3 demonstrably fail against the *pre-change* gate (proving the bug), then pass
after implementation; case 4 passes throughout (proving no false-positive).
