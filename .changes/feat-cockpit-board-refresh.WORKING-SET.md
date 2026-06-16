# Working Set — feat-cockpit-board-refresh

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
Refresh the cockpit board to match the signed-off design: full-height lanes, redesigned change cards (handle + liveness/time-since-active on top; 'Waiting on you' XOR change-health at foot), revive 'Start something new' button, dark-mode surface elevation token fixes + sharper waiting amber, responsive breakpoints (tablet sideways-scroll, mobile one-lane with stage chips as switcher). Change-health signal scoped to cheap first step (tests + rigor-for-stage); scope-drift deferred.

## 2. Current best solution  (→ Design)
_(not yet established)_

## 3. Decisions in flight  (→ Decision; status: proposed)
_(none yet — one entry per non-trivial choice being weighed: the choice, options
considered, rejected alternatives + rationale, status proposed→accepted on lock)_

## 4. Open questions / unknowns
_(none yet — the live "what we still don't know" parking lot)_

## 5. Rejected so far  (→ Decision.rejected_alternatives)
_(none yet — paths tried and abandoned, **with the why**)_

## 6. Working log  (append-only)
- 2026-06-16T07:44:45Z — Working Set created.
- 2026-06-16T07:47:25Z — Specify stage: wrote SPEC.md from the signed-off design (.design/cockpit-board-refresh/). Standard depth — design already answered the what; drafted by inference rather than re-interviewing. Health signal scoped to cheap first cut (tests + rigor-for-stage, two levels); Worth-a-look + scope-drift deferred to change-stage OODA-spiral work.
- 2026-06-16T08:01:48Z — Review stage: security clean (reason-containment + never-500 hold; 3 minor advisories, none blocking). Build gate was red on two stale tests (verbatim fixture missing WP-001 fields; routes.changes asserting old 'unknown' liveness). Fixed both (commit f7f9429e); typecheck green, 1494/1494 tests pass. Verdict: good to ship.
- 2026-06-16T09:43:58Z — Added 'All' default scope to the board (commit aec8aac8): multi-product hid every change because the change->product rollup matches worktree-under-repo-path, which never holds (worktrees live in ~/.sulis/changes). Now null/no-selection = All (every change); a product is a filter. 1499 tests green.
- 2026-06-16T10:09:58Z — Caught board-refresh up to live trunk (merge 4eefe53f, 71 commits incl. brain re-homing). Conflict-free; typecheck + full suite green (1501/1501) on a clean run — the first run's 4 'failures' were flaky async/axe waitFor timeouts under load. Branch now 0 behind trunk, 39 ahead. Delta is clean: the board-refresh feature set + 3 fixes on top of today's platform. Proper change->product brain link now available for assignment.
- 2026-06-16T10:29:09Z — Assignment layer 1 (read side) done + committed (d64d630f): rollup reads change.for_product from the brain Change entity, wins over the path heuristic. Live: Sulis filter now shows its 27 assigned changes (was 0). 27 readProducts/scope tests green. NEXT: layer 2 (write path: set for_product via sanctioned cockpit write, emit-change for the ~174 record-less changes) + layer 3 (assign control in change detail view).
- 2026-06-16T10:40:32Z — Assignment layer 2 (write engine) done + committed (32a7ea8b): set-change-product.py spine script — validated read-modify-save (update existing entity) + compose-from-change.json (record-less changes), writes to cockpit's --base-dir brain, schema-validates for_product. 4 pytest cases green; read-only gate clean. REMAINING for clickable: cockpit port+adapter+route (PUT /api/changes/:id/product calling the script) + client product-picker in the change detail view.
- 2026-06-16T11:05:24Z — Assignment layer 2 cockpit endpoint done + committed (ffac5d61): SpineSettingsAdapter.assignChangeProduct + PUT /api/changes/:id/product, both read-only gates allowlist changes.ts by path, wired in app.ts. Verified end-to-end live (PUT sets brain for_product). Backend fully complete: read (rollup) + write (script+endpoint) all working — assignment is functional via the API now. REMAINING: layer 3 client UI — product picker in the change detail view + API client + board cache invalidation on assign.
- 2026-06-16T11:24:57Z — Assignment FINISHED (layer 3 UI, commit b46b66ba): ProductPicker in the change header — shows current product, pick to assign, invalidates the board. Change.forProduct surfaced on the wire (OPTIONAL per founder's call — no fixture churn). Full feature clickable + verified live. Whole assignment span: read rollup (d64d630f) + write engine (32a7ea8b) + endpoint (ffac5d61) + UI (b46b66ba). 1509 tests green, lint + both read-only gates clean.
- 2026-06-16T12:09:34Z — Founder signed off the cockpit product-experience design (.design/cockpit-product-experience/, SIGNOFF.md, production-approved). Refines the tactical product pieces: one 'Product' field + searchable menu everywhere (replaces raw select), refined scope switcher (All/Unassigned/counts), un-assign ability, assign-from-card. Mobbin tool wasn't connected — grounded in Linear/Notion/Vercel, founder signed off knowing this. NEXT: build as its OWN change (separate from board-refresh); board-refresh still pending ship.
