# ADR-003 — Hook the seam-close gate at the WP done-transition (`wpx-step12 wrap`), not in run-wp/run-all directly

- **Status:** accepted
- **Change:** CH-01KTP7 (`feat` · `seam-dod-gate`)
- **Date:** 2026-06-09

## Context

The SPEC says the gate fires "in the build loop (run-wp / run-all) … when a
producer WP and its consumer WP both reach done, or an integration / composite
WP completes." That names *run-wp* and *run-all* as the loci. But run-wp and
run-all are two separate skills, and "a WP reaches done" happens at different
mechanical moments depending on path:

- **Single-WP (`run-wp --force-single`):** Steps 8–12 run inline; the `done`
  flip happens at `wpx-step12 wrap` Step 12.2.
- **Default / batch (`run-wp` → train, `run-all` → `wpx-train`):** Steps 8–10
  run per-batch in the train, but each WP is still finalised through
  `wpx-step12 wrap` (the `done` flip is per-WP, not per-batch).

A WP is **not** `done` at Step 7 (push) — CI, merge, deploy, health, smoke, and
security all run after Step 7 and before the `done` flip.

## Decision

**Hook the seam-close gate at the WP done-transition — inside `wpx-step12 wrap`,
immediately after Step 12.2 (`flip-status --to done --expected in_progress`).**
Both run-wp and run-all converge on `wpx-step12 wrap`, so a single hook covers
both paths. The run-wp / run-all SKILLs document the gate (for the wiring tests
and founder-English surfacing); the *logic* lives at the one transition.

## Why (the recommendation, lead position)

- **One site, both paths.** Single-WP and batch both finalise through
  `wpx-step12 wrap`. Hooking there means one place to implement, one place to
  test, and correct firing whether a seam closes inside a batch or across two
  batches. Hooking in run-wp *and* run-all would duplicate the logic across two
  skills (which are prose, not code) and risk drift.
- **The `done` flip is the true "WP completed" event.** Step 7 (push) is not
  completion — Steps 8–12 can still block. The seam-close predicate ("are all
  WPs on both sides of this seam now `done`?") must read post-flip INDEX state,
  so the natural place is right after the flip.
- **After the flip, not before.** The predicate must observe the current WP as
  `done` to answer. Running after the flip keeps the predicate a clean read over
  INDEX state instead of special-casing "…and this one, about to flip."
- **Do not roll back the flip on a block.** The WP genuinely reached `done`; it
  is the *seam* that isn't done. The gate reports the seam as blocked (emits a
  gate-block in the wrap envelope) and the calling session halts seam-close —
  mirroring the ship gate, where a blocked acceptance verdict refuses to call the
  change done without un-merging it.

## Alternatives considered

- **Hook in run-wp Step 7 completion.** **Rejected:** Step 7 is push, not done;
  the WP isn't `done` yet and the seam predicate would read stale INDEX state.
  It also misses the batch path entirely (run-all defers Steps 8–12 to the train).
- **Hook in `wpx-train` Step 10 (per-batch).** **Rejected:** the train batches
  deploy/health/smoke per-batch, but the `done` flip is still per-WP via
  `wpx-step12 wrap`. Hooking at batch granularity would mis-fire when a seam
  closes across two batches and would still need a separate single-WP hook.
- **A standalone gate skill the orchestrator calls after each WP.** **Rejected:**
  adds a new coordination surface and a second place for the rule to live; the
  done-transition already exists and already runs on both paths.

## Consequences

- `wpx-step12 wrap` gains a step 12.2a that calls
  `_seam_close_gate.evaluate(...)` and threads the result into its JSON envelope.
- The gate logic is pure (`_seam_close_gate`), so it is unit-tested without a
  subprocess; `wpx-step12` only wires it. The wiring test asserts `wpx-step12`
  references the gate (mirroring `test_ship_acceptance_gate_wiring.py`).
- run-wp / run-all SKILL.md gain documentation of the seam-close gate and its
  founder-English block surfacing (no behaviour in the skills themselves beyond
  surfacing the wrap envelope's gate-block).
