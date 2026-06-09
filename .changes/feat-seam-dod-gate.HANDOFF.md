# Handoff — feat-seam-dod-gate (CH-01KTP7) — task #95 (fix "A")

> Seed for this scoped session, written while the methodology program was fresh. Read
> before `/sulis:recon` → `/sulis:specify`. This is fix **A** of the 4-change program;
> its upstream (#98 substrate) has SHIPPED, so this is now unblocked and ready to build.

## The problem this closes (the methodology program's core thesis)

"Ships green but never works / long find-one-fix-one cycle." WPs are tested hermetically
against builder-authored fixtures — they certify the SHAPE of each slice, but the REAL
data crossing the **seam between two slices** is never driven until ship. So each ship
surfaces the next un-driven seam: a slow, serial find-one-fix-one tail.

The acceptance drive (`sulis-verify-acceptance`, observed-or-blocked) currently fires
**too late** — at SHIP stage only. By then the work is already merged-adjacent; a blocked
seam is expensive to unwind.

## The fix (re-time the gate: ship → seam-close)

**A:** drive the real-data Scenario acceptance check at **seam-close** — the moment a
contract-first seam between two pieces of work closes (a producer WP and its consumer WP
both done, or a CONTRACT_FIRST seam boundary reached) — NOT deferred to ship. Move
observed-or-blocked earlier so an un-driven seam is caught when it's cheap to fix, not
after merge.

This is observed-or-blocked applied at the SEAM, the same way #99 applied it to the INDEX
artifact and #66/#83 applied it at ship.

## What's already built FOR you (#98 substrate — SHIPPED as PR #259, commit e4cb9a09)

The verification substrate this gate CONSUMES is live on main:
- The headless scenario runner is now **tiered** (`scripted` vs `agent-step` driver),
  **isolated** (reset→process→env clean-slate ladder, default = cheap reset), and
- carries an **equality | property verdict-invariant** evaluated over the real saved
  record → `observed | blocked`. **This verdict-invariant is the field your gate reads.**
- Plus a read-only working-set-derived dispatch brief.
- Commit message is explicit: *"it does not close #95 — it unblocks it."* The producer
  substrate shipped; **consumer-side seams (CLI surfacing, live subagent dispatcher) were
  captured as follow-ups** — confirm what's surfaced vs still-stub at recon.

So this change is the CONSUMER: wire the seam-close gate to run the substrate's tiered/
isolated drive and read its equality|property verdict.

## Where the acceptance gate fires today (the re-timing targets)
- `plugins/sulis/skills/change/SKILL.md` — ship gate **4.8** calls `sulis-verify-acceptance`
  at SHIP. (Also draft-architecture walk + prove.) This is the "too late" timing.
- `sulis-verify-acceptance` is the runner to invoke at the seam too.
- The SEAM definition lives in `CONTRACT_FIRST_STANDARD.md` (producer/consumer seam —
  contract WP first, parallel per-kind, integration last). Seam-close = the integration
  point. The gate hooks where a seam's consumer WP closes (run-wp / run-all completion of
  a seam-spanning WP).

## Load-bearing uncertainty to resolve at recon/specify (don't assume — check)
1. **Do enumerated Scenarios tile the seam set 1:1?** (Is each seam the last hop of some
   Scenario?) If YES → the gate's unit is the Scenario. If NO → the unit drops to the
   seam / contract-WP, and the gate keys off the CONTRACT_FIRST seam boundary, not a
   Scenario id. This determines the gate's trigger shape — resolve it FIRST.
   (This was flagged as the #1 instrument-don't-block uncertainty in #98's handoff.)

## Test-first (MUST)
Author failing tests FIRST:
1. A seam closes with its real-data Scenario UN-driven → gate BLOCKS at seam-close (today
   it passes silently until ship — that's the bug).
2. A seam whose Scenario drives green (equality verdict) → gate PASSES at seam-close.
3. A property-verdict seam (record matching shape X appeared) → PASSES.
4. A deferred/blocked seam → BLOCKS (observed-or-blocked: deferred ≠ done), surfaced in
   founder English (which seam, what wasn't driven).

## Files in play
- `plugins/sulis/skills/run-wp/`, `plugins/sulis/skills/run-all/` — where a seam-spanning
  WP closes (the new gate's trigger point).
- `plugins/sulis/skills/change/SKILL.md` — gate 4.8 (the ship-stage drive; re-time/share).
- `plugins/sulis/references/standards/CONTRACT_FIRST_STANDARD.md` — seam definition +
  where to add the seam-close DoD rule.
- `plugins/sulis/references/standards/WORK_PACKAGE_STANDARD.md` — WP DoD wording.
- `plugins/sulis/scripts/sulis-verify-acceptance` (+ the #98 substrate it now wraps) —
  the runner the gate invokes.

## Relationships
- Upstream #98 (substrate): SHIPPED (#259). This consumes its verdict-invariant.
- Siblings: #96 (B — spiral-back transitions), #97 (C — dependency-as-child-change) —
  separate changes, not blockers.

## Suggested next step
`/sulis:recon` (confirm what #259 surfaced vs left stubbed; find the exact seam-close
point in run-wp/run-all; resolve the 1:1-tiling uncertainty above) → `/sulis:specify`.
