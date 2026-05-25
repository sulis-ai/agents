# ADR-212 amendment: optimistic eligibility (v0.18.0)

**Date:** 2026-05-22
**Status:** Active (ships in sulis-execution v0.18.0)
**Amends:** ADR-212 D6 (eligibility rules; v0.11.0)

## Context

ADR-212 D6 defined train eligibility as a 5-rule check:

1. status == step-7-complete (or force-include override)
2. branch exists on origin
3. **branch CI is green** (or force-include override)
4. all dependencies have status == done
5. WP is not hold-overridden

Rule 3 — per-WP branch CI green — was conservative: a train would
only consider including a WP whose own branch CI had completed
successfully.

In practice (live executor sessions against the platform repo, May
2026), Rule 3 produced a workflow gap: the founder could push a WP's
branch, CI would start, and the train wouldn't be eligible to fire
until CI completed. CI runs can take 15-30 min. The founder waits.

This contradicts the "fire and continue, come back if there's an
issue" pattern that modern merge queues use (GitHub Merge Queue,
Bors, Shopify Shipit). Those systems treat per-branch CI as a hint;
the queue's integration CI (post-rebase, bundled-tip) is the real
gate.

## Decision

Drop Rule 3 from default eligibility. Keep the check available via
a `--strict-ci` flag for callers who want pre-batch confidence on
individual branches.

New default eligibility (v0.18.0+):

1. status == step-7-complete (or force-include override)
2. branch exists on origin
3. ~~branch CI is green~~ *(removed from default; available via --strict-ci)*
4. all dependencies have status == done
5. WP is not hold-overridden

The bundled-tip CI (lifecycle Step 8) remains the real gate. Per-WP
CI is now surfaced as informational data in queue-list / status
output, not as a gate.

## Justification

**Why this is safe.** The bundled-tip CI catches everything per-WP
CI would have caught, and more — it tests the actual code that's
about to merge (after sequential rebases), which is what matters.
Per-WP CI tests each branch in isolation; bundled-tip CI tests the
composition.

**Why per-WP CI is still useful** (just not as a gate). It signals
to the founder which branches are likely to be problematic. The
new `queue-list` output surfaces CI status alongside eligibility
so the founder can see at a glance "WP-X is eligible but its branch
CI is failing — might want to hold it."

**Why the strict mode escape hatch exists.** Some teams have very
slow bundled-tip CI (e.g., 30+ min). For them, a strict per-WP gate
saves time by refusing to batch branches that are clearly broken.
Those callers pass `--strict-ci` to preserve the v0.11.0 behaviour.

## Risk + mitigation

**Risk:** A WP with red CI gets included in a batch; bundled-tip CI
also fails; the train wastes time on the rebase + bundled-tip CI
phases before failing.

**Mitigation:** The train fails fast — Phase 4 (bundled-tip CI) is
already part of the existing flow, and a CI failure there triggers
the existing `_handle_post_merge_failure` path. With Phase 2.2
(paused-state recovery), the train enters `phase: paused` rather
than failing terminally, so the founder can drop the offending WP
via Phase 3.3 (`wpx-train skip-wp`) and resume the rest.

Net effect: same wall-time as before in the failure case; faster
wall-time in the (more common) case where per-WP CI was actually
green or about-to-be-green.

## What does NOT change

- The bundled-tip CI gate at Step 8. Unchanged.
- The ADR-212 batching rules (per-batch deploy + health + smoke).
- The status enum (step-7-complete / step-7-held / step-7-blocked).
- Per-WP rebase conflict handling (existing flow continues to flip
  to step-7-blocked + write per-WP BLOCKER + drop from batch).
- Per-WP queue overrides (train-overrides.yaml force-include + hold).

## Migration

Callers that explicitly relied on the strict CI gate add the
`--strict-ci` flag. No other changes required.

For the marketplace's own callers (`/sulis:run-all`):
no change needed. The skill invokes `wpx-train run` without
`--strict-ci`; it gets the new default (optimistic). This is the
intended behaviour for the founder workflow.

## See also

- `references/lifecycle.md` — full lifecycle reference
- `scripts/_wpxlib.py` — `find_eligible_branches(strict_ci=False)` is
  the canonical implementation
- `scripts/tests/unit/test_wpx_train_eligibility.py` — both modes
  pinned by tests
