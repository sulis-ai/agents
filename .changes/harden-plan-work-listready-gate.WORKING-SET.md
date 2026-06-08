# Working Set — harden-plan-work-listready-gate

> Live reasoning state for this change/session. **Read at the START of every turn;
> update as a side-effect of each decision** (never as a separate chore — that's
> how it dies). Sections 1–5 are current-state (overwritten as thinking moves);
> section 6 is append-only (never edited). Crystallizes into Opportunity / Design
> / Decision at the session boundary; if a session ends abruptly, this file IS
> the handoff to the next. Spec: plugins/sulis/docs/working-set-and-session-chain.md.

## 1. Problem  (→ Opportunity)
Make plan-work's DoD drive the real consumer (wpx-index list-ready round-trip) so a non-canonical INDEX is caught at creation — killing the recurring 0-WP class (#60/#218/#222/#233/#97). Lean path: wire the round-trip into the existing lint so Step 9.5 enforces it for free.

## 2. Current best solution  (→ Design)
Make the decompose done-check DRIVE the real consumer: run `wpx-index list-ready`
against the just-written INDEX and assert the authored WPs round-trip (≥1 ready when
deps allow; ideally ready+blocked-by-dep == count of `pending` rows). 0 returned while
WPs exist = NOT done. This single property subsumes all three recurrence variants
(missing table / bad header / wrong status) because each manifests as list-ready
returning 0. Lean path: wire the round-trip INTO `wpx-index lint` so plan-work's
EXISTING Step 9.5 ("lint non-zero = not done", SKILL.md ~L467-482) enforces it for free.

Confirmed mechanics (recon):
- Real consumer: `cmd_list_ready` → `_collect_status_across_tables` + `_resolve_deps`;
  keys on status=='pending'; errors "no WP table with ID + Status columns" when empty.
- Current gate: `cmd_lint` → `validate_wp_index_header` (`_WP_TABLE_HEADER_RE`) — HEADER
  SHAPE only. Blind to #222 (canonical header + status 'ready'/'blocked' → list-ready
  empty, lint passes). THIS is the gap the round-trip closes that header-lint cannot.

## 3. Decisions in flight  (→ Decision; status: ACCEPTED)
- **Gate surface = extend `cmd_lint` (NOT a new subcommand)** — ACCEPTED at design.
  Rationale: plan-work Step 9.5's existing "lint non-zero = not done" wiring enforces
  the round-trip for free; a separate subcommand needs a second wiring edit and a gate
  that can drift. Boring single-gate path wins. Rejected: distinct `verify`/`round-trip`
  subcommand (no concrete reason to separate).
- **Assertion property = "every authored `pending` WP accounted for (ready ∪ dep-blocked)"**
  — ACCEPTED. NOT "ready ≥ 1" (a fully dep-chained INDEX legitimately has 0 ready). Pinned
  by a dedicated test (fully-depchained/0-ready → PASS).
- **EP-03 single source of truth** — round-trip reuses `_collect_status_across_tables` +
  `_resolve_deps` (the exact helpers `cmd_list_ready` calls); gate can't disagree with consumer.

## 4. Open questions / unknowns
- RESOLVED (specify): assertion property = "every authored `pending` WP is accounted for
  by list-ready (ready ∪ dependency-blocked)", NOT "ready ≥ 1". Recorded in SPEC Constraints.
  Design finalises the exact implementation shape.
- For design: the precise gate surface — extend `lint` (lean) vs new `verify` subcommand.

## 5. Rejected so far  (→ Decision.rejected_alternatives)
- "Just fix the header lint" — REJECTED. Header lint tests a proxy (header spelling),
  not the property that matters (the tracker can parse + drive the INDEX). It structurally
  cannot catch #222 (status vocab) or a status-only failure. Same proxy-vs-real-gate
  failure family as #80/#97.

## 6. Working log  (append-only)
- 2026-06-08T21:37:30Z — Working Set created.
- 2026-06-08T22:40:00Z — Recon done. Confirmed list-ready is the real consumer, lint is
  header-shape-only (blind to #222 status-vocab). Locked thesis: round-trip gate via
  list-ready; lean path = wire into lint. Next: /sulis:specify (test-first variant matrix).
- 2026-06-08T22:55:00Z — Specify done (standard, authored from context — no interrogation).
  SPEC.md written with 4-variant Verification Plan. Audit done: 1 gap → 1 hardening delta.
- 2026-06-08T23:05:00Z — Design/plan-work done. SEA authored WP-001 (single RGB WP), extend-lint
  surface decision ACCEPTED. lint exit 0; rubric PASS-WITH-RATIONALE; list-ready round-trips
  the new INDEX (ready=[WP-001]). 6 failing-first tests pinned. Next: /sulis:run-all (build).
