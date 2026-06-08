---
id: WP-001
title: "Fold a list-ready round-trip into wpx-index lint so the decompose gate drives the real consumer"
primitive: harden
group: reinforce
kind: backend
status: pending
dependsOn: []
blocks: []
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_wpx_index_roundtrip.py::test_status_vocab_all_nonpending_fails_gate"
estimated_token_cost:
  input: ~25k
  output: ~9k
characterisation_test: "N/A — REINFORCE/harden, not a REORGANISE refactor of existing behaviour. The four variant tests below are net-new failing tests authored test-first per EP-02, not characterisation tests over existing logic."
---

# WP-001 — Fold a list-ready round-trip into `wpx-index lint`

## Context

- **Architecture component:** the decompose-time INDEX gate.
  `plan-work/SKILL.md` Step 9.5 runs `wpx-index lint --project {project}`
  and treats a non-zero exit as a BLOCKING decompose failure.
- **Source of record:** `.changes/harden-plan-work-listready-gate.SPEC.md`
  (intent, scope, 4-variant acceptance matrix) and `.AUDIT.md` (the single
  load-bearing gap + the one hardening delta).
- **The gap (one, load-bearing):** today's gate calls
  `validate_wp_index_header` (`_wpxlib.py` ~L1549), which keys off
  `_WP_TABLE_HEADER_RE` — a regex over the WP table *header shape*. That is a
  **proxy** for "the builder can read the to-do list". It is structurally blind
  to a canonical-header INDEX whose Status cells are `ready`/`blocked` (never
  `pending`): the real builder consumer (`wpx-index list-ready` →
  `_collect_status_across_tables` + `_resolve_deps`, ~L466) then returns an
  empty ready/pending set, and the break surfaces mid-build, not at creation.
  This is failure-class #60/#218/#222/#233 (meta-diagnosis #97) — four
  recurrences in ~10 days.
- **The fix:** make the gate **drive the real consumer**. Run the *exact*
  parse `list-ready` runs against the just-written INDEX and assert every
  authored `pending` WP is accounted for (ready ∪ dependency-blocked). A
  `0`-WP / parse-fail result while WPs exist is BLOCKING.
- **Primitive choice — `harden` (REINFORCE):** this adds a verification
  primitive (a round-trip assertion) on top of existing decompose behaviour
  without changing what the canonical INDEX *is* (#60's already-shipped fix)
  or `list-ready`'s semantics (#76, out of scope). It is REINFORCE running
  orthogonally on the existing gate, not EXPAND/SUBSTITUTE/REORGANISE.
- **Surface decision — extend `cmd_lint`, NOT a new `verify`/`round-trip`
  subcommand (recorded):** the SPEC and AUDIT both name extend-lint as the
  lean path. Folding the round-trip into `cmd_lint` means plan-work's
  **existing** Step 9.5 wiring ("lint non-zero exit = decompose NOT done")
  enforces it for free — no new gate to wire, maximal enforcement, minimal
  surface. A distinct subcommand was evaluated and rejected: it would require
  a second wiring edit in `plan-work/SKILL.md` and create a second gate that
  can drift from the first. **No concrete reason to separate exists** (the
  round-trip is the same decompose-time concern as the header check), so the
  boring, single-gate path wins (CP: older/more-boring convention; EP-03
  single source of truth). Recorded here rather than as a standalone ADR per
  the engineering-architect-light right-sizing of this change.

## Contract

This WP modifies **one function** and adds **one test module**. No public
CLI surface changes (`wpx-index lint --project {project}` keeps its exact
invocation and its exit-code contract; only the set of failures it detects
widens).

### Modified — `plugins/sulis/scripts/wpx-index` · `cmd_lint`

`cmd_lint` keeps its current behaviour (header check via
`validate_wp_index_header`) and **additionally** runs the real-consumer
round-trip after the header check passes:

```
cmd_lint(args):
    text = _read_index(args)

    # (existing) header-shape check — keep, runs first
    error = validate_wp_index_header(text)
    if error is not None:
        emit_error(error)            # exit non-zero, founder-readable

    # (new) round-trip: run the SAME parse list-ready runs
    status_by_id = _collect_status_across_tables(text)
    if not status_by_id:
        emit_error(<missing/unparseable WP table message>)   # exit non-zero

    pending = [wp for wp, s in status_by_id.items() if s == "pending"]
    if not pending:
        emit_error(<no pending WP accounted-for message>)     # exit non-zero

    # every authored `pending` WP must be accounted for by the consumer:
    # ready ∪ dependency-blocked (NOT the weaker "ready >= 1").
    depends_by_id = _resolve_deps(args, text, set(status_by_id))
    accounted = set()
    for wp_id in pending:
        deps = depends_by_id.get(wp_id, [])
        # ready: all deps done; dependency-blocked: >=1 dep not done.
        # Either way the consumer SEES the WP — that is "accounted for".
        accounted.add(wp_id)
    unaccounted = set(pending) - accounted
    if unaccounted:
        emit_error(<names the unaccounted WPs>)               # exit non-zero

    emit_ok(data={"header": "canonical",
                  "round_trip": "ok",
                  "pending": len(pending),
                  "accounted": len(accounted)})
```

**Contract invariants the implementation MUST honour:**

1. **EP-03 single source of truth.** The round-trip reuses
   `_collect_status_across_tables` and `_resolve_deps` — the *exact* helpers
   `cmd_list_ready` calls. It MUST NOT re-implement INDEX parsing or status
   collection. The gate can never disagree with `list-ready` about what
   counts as a runnable INDEX, because it runs the same code.
2. **Assertion property = "accounted for (ready ∪ dependency-blocked)", NOT
   "ready ≥ 1".** A legitimately fully dep-chained INDEX can have 0
   *immediately ready* WPs while every WP still round-trips (it is seen by the
   consumer, just dependency-blocked). The gate MUST pass that case. The
   failure condition is the consumer being *blind* to authored pending WPs
   (empty `status_by_id`, or a pending WP the consumer cannot see at all),
   not the consumer reporting them as not-yet-ready.
3. **Founder-readable errors.** Each `emit_error` names what is wrong and the
   next step, consistent with the existing header-error message style
   (`validate_wp_index_header`'s message is the reference). No internal IDs in
   the operator-facing string.
4. **Exit-code contract unchanged.** `emit_error` exits non-zero;
   `emit_ok` exits zero. Step 9.5's "non-zero = not done" reads this
   unchanged.

### Added — `plugins/sulis/scripts/tests/unit/test_wpx_index_roundtrip.py`

Loads the `wpx-index` script via `SourceFileLoader` (the established pattern
in `test_wpx_index_multitable.py` ~L30) and writes INDEX fixtures into a
`tmp_path` project (reuse the `_write_project` / `_args` helper shape from
that module). Each test invokes `cmd_lint` and asserts exit code + emitted
payload.

## Definition of Done

### Red — author failing tests FIRST (MUST, EP-02)

Cases 1–3 MUST FAIL against **today's** `cmd_lint` (proving the bug). Case 4
MUST PASS throughout (proving no false-positive). Run the suite once before
any implementation change and confirm the 1–3 reds and the 4 green.

- [ ] `test_missing_wp_table_fails_gate` — fixture: an INDEX with **no WP
  table** (prose / "readable layout" only). Assert `cmd_lint` exits non-zero.
  Pins #97. *(Fails today: header regex finds no table → `validate_wp_index_header`
  already errors here, so confirm this is red-or-green against today's gate and
  record which; the round-trip backstops it regardless.)*
- [ ] `test_noncanonical_header_fails_gate` — fixture: canonical-shaped rows
  under a **non-canonical header** (`| WP | Title | Kind | ... |`). Assert
  `cmd_lint` exits non-zero. Pins #218/#233.
- [ ] `test_status_vocab_all_nonpending_fails_gate` — fixture: **canonical
  header**, all Status cells `ready`/`blocked` (none `pending`). Assert
  `cmd_lint` exits non-zero. **Pins #222 — the load-bearing case the header
  lint cannot catch.** This MUST be red against today's gate.
- [ ] `test_canonical_with_pending_passes_gate` — fixture: canonical header,
  ≥1 `pending` WP (mix of immediately-ready and dependency-blocked). Assert
  `cmd_lint` exits 0 and `data.round_trip == "ok"`. MUST be green throughout
  (no false-positive).
- [ ] `test_fully_depchained_zero_ready_still_passes` — fixture: canonical
  header, all WPs `pending` but every WP depends on another pending WP (0
  immediately ready). Assert `cmd_lint` exits 0 — proves the property is
  "accounted for", not "ready ≥ 1" (Contract invariant 2).
- [ ] **Wiring assertion** `test_step95_treats_variants_as_done_state` —
  assert the Step 9.5 contract holds at the exit-code level: cases 1–3 yield
  non-zero (decompose NOT done) and case 4 yields zero (done). This is the
  SPEC "Wiring check" expressed as a test over `cmd_lint`'s exit code, which
  is exactly what Step 9.5 reads.

### Green — make them pass with the boring change

- [ ] Extend `cmd_lint` per the Contract pseudocode. Header check first
  (unchanged), then the round-trip using `_collect_status_across_tables` +
  `_resolve_deps` (reused, not re-implemented).
- [ ] All six Red tests green.
- [ ] No change to `validate_wp_index_header`, `_collect_status_across_tables`,
  `_resolve_deps`, or `cmd_list_ready` — the round-trip *consumes* them
  as-is (EP-03).

### Blue — refactor + leave the surface better

- [ ] Extract the round-trip body into a small named helper
  (e.g. `_roundtrip_accounting(args, text) -> tuple[set[str], set[str]]`
  returning `(pending, unaccounted)`) if `cmd_lint` grows past ~15 lines, so
  the gate logic is unit-addressable and the `emit_error`/`emit_ok` wiring
  stays thin. Only if it improves readability — do not over-abstract a
  three-line check.
- [ ] Confirm no duplicate parse path was introduced (grep for any new
  `parse_md_table` / `_find_all_wp_tables` call inside `cmd_lint` that
  duplicates `_collect_status_across_tables`; there must be none).
- [ ] **plan-work/SKILL.md Step 9.5 note (same logical change, one-file
  touch):** update the Step 9.5 prose (~L470-487) so it states the gate now
  also drives a `list-ready` round-trip (not only the header shape) — naming
  the new failure modes it catches (missing table, non-canonical header,
  all-non-`pending` statuses). Mechanical doc edit; no characterisation test
  required (it documents behaviour this WP's tests already pin). Keep it
  founder-readable.
- [ ] `wpx-index lint --project harden-plan-work-listready-gate` exits 0
  against this change's own canonical INDEX (dogfood).

## Sequence

- **Sequence ID:** WP-001
- **dependsOn:** none — single atomic WP.
- **blocks:** none.

## Estimated token cost

- input: ~25k (three source files + three existing test modules for fixture
  reuse)
- output: ~9k (one ~120-line test module + a ~20-line `cmd_lint` diff + a
  short SKILL.md prose edit)
