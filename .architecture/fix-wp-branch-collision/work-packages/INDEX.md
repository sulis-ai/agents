# Work Packages — fix-wp-branch-collision (CH-7BF1VZ)

> Change: `01KTQ950H47BF1VZ6Z51ZHFCAB` · primitive: fix · branch:
> `change/fix-wp-branch-collision`. Design: `../TDD.md`. Branch-naming
> decision: `../adrs/ADR-001-wp-branch-naming-scheme.md`.

## Build constraint — direct-merge-on-green per wave (MUST)

This change's own WPs are exposed to the collision being fixed, so they MUST
NOT integrate via the train. Per wave: verify each WP branch's CI →
squash-merge to `change/fix-wp-branch-collision` → run the full unit suite
(`pytest plugins/sulis/scripts/tests/unit/`) → proceed to the next wave.
Branch-CI is advisory on this repo; "shipped" is measured against the blocking
gate. WP branches for *this* change are minted the legacy `feat/...` way (the
new mint path doesn't exist until WP-005) — no bootstrap paradox: the resolver
under test is exercised by unit tests, not by these WPs' own branches.

## Status

| WP | Title | Wave | kind | status | dependsOn |
|----|-------|------|------|--------|-----------|
| WP-001 | Thread change identity into `_branch_name` | 1 | backend | done | — |
| WP-002 | Widen `_JOURNAL_PUSHED_BRANCH_RE` (wp/ + change/) | 1 | backend | done | — |
| WP-003 | Dual-prefix resolution in `resolve_wp_branch` | 2 | backend | done | WP-001 |
| WP-004 | Thread scope through eligibility + status + CLI | 2 | backend | done | WP-001, WP-003 |
| WP-005 | `wpx-wp branch-name` emitter + skill wiring | 3 | backend | done | WP-001 |
| WP-006 | Migrate test fixtures to dual-prefix coverage | 4 | backend | done | WP-003, WP-004 |
| WP-007 | Reconcile WORK_PACKAGE_STANDARD + CW-04 | 4 | docs | done | WP-003 |

## Waves (integration order)

```
Wave 1  (leaves — no caller contract change yet; parallel)
  WP-001  _branch_name(change_scope)   ─┐
  WP-002  journal regex widening        │  (independent of WP-001)
                                         │
          ── merge wave 1, run full suite ──
                                         │
Wave 2  (resolver scoping; depends on WP-001)
  WP-003  resolve_wp_branch dual-prefix ─┤  (depends WP-001)
  WP-004  eligibility/status/CLI scope  ─┘  (depends WP-001, WP-003)
          ── merge wave 2, run full suite ──

Wave 3  (mint path; depends on WP-001 — can overlap wave 2 but
         sequenced after for a clean single-suite gate per wave)
  WP-005  wpx-wp branch-name + skill    ─   (depends WP-001)
          ── merge wave 3, run full suite ──

Wave 4  (follow the contract — fixtures + docs trail the code)
  WP-006  fixture dual-prefix coverage  ─   (depends WP-003, WP-004)
  WP-007  standards reconciliation      ─   (depends WP-003)
          ── merge wave 4, run full suite ──  ✅ change ready to verify
```

### Intra-wave ordering (MUST)

A wave is a full-suite CI gate, not a parallelism guarantee. Where two WPs
share a wave AND one depends on the other, the dependency orders them *within*
the wave:

- **Wave 2:** WP-003 merges before WP-004 (WP-004 calls the scoped
  `resolve_wp_branch` that WP-003 introduces). They are not parallel.
- **Wave 4:** WP-006 and WP-007 are independent of each other and may merge in
  either order; both depend only on already-merged earlier-wave WPs.

WP-001 and WP-002 (Wave 1) are mutually independent and may be built in
parallel; merge both, then run the suite once before Wave 2.

### Why this order

- **Regex (WP-002) and `_branch_name` (WP-001) are leaves** — nothing depends
  on their output shape except later WPs, and they don't change any caller's
  behaviour (WP-001 defaults to legacy; WP-002 only broadens a match). Land
  first so the contract the resolver threads is in place.
- **Resolver scoping (WP-003) before eligibility/status threading (WP-004)** —
  WP-004 calls the scoped `resolve_wp_branch`, which must exist first.
- **Mint path (WP-005) after `_branch_name`** — it emits via `_branch_name` and
  uses `current_change_scope` (added in WP-004), so it depends on WP-001 and is
  cleanest sequenced after Wave 2; placed in its own wave for an isolated
  suite gate.
- **Fixtures (WP-006) and docs (WP-007) last** — they assert / describe the
  contract WP-003/004 change, so per the build order they follow the code that
  changes that contract.

## Acceptance trace (SPEC → WP)

| SPEC acceptance criterion | Covered by |
|---|---|
| WP no longer resolves to / false-eligibled onto a foreign change's branch | WP-003 (`test_scoped_glob_does_not_match_foreign_change_branch`), WP-004 |
| Newly minted WP branches carry the change-scoped name | WP-001, WP-005 |
| Old-shape branch still resolves (via journal Step-0; legacy glob only for no-scope callers) | WP-003 (`test_resolve_scoped_inflight_legacy_branch_resolves_via_journal`, `test_resolve_scoped_suppresses_legacy_glob_when_no_journal`), WP-006 |
| Step-7 traces recording a `change/...` pushed branch parsed correctly | WP-002 |
| Full unit suite passes; both paths explicitly covered | WP-006 |
| Standards describe the implemented hierarchy, no contradiction | WP-007 |
| #229 journal Step-0 contract preserved; `gh=None` shim signatures intact | WP-003 (Red/Green oracles), WP-004 |
