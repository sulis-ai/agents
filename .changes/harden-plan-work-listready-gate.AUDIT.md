# Audit — harden-plan-work-listready-gate (CH-01KTMJ)

Brownfield gap audit. Right-sized: recon already mapped the three files in
play; this is a single, crisp gap with a single hardening delta. Full
whole-codebase structural analysis skipped (surgical 3-file harden, code
already read). Journey-walk: **exempt** — pure non-user-facing build tooling,
no user round-trip.

## The gap (one, load-bearing)
`cmd_lint` (plugins/sulis/scripts/wpx-index) → `validate_wp_index_header`
(_wpxlib.py) gates decompose on a **proxy**: the WP-table header regex
(`_WP_TABLE_HEADER_RE`). It is structurally blind to:
- (a) a wholly-missing table that still trips no header (prose-only "readable
  layout") — #97;
- (b) the status-vocabulary variant — a CANONICAL header whose Status cells are
  `ready`/`blocked` (not `pending`), so the real consumer `cmd_list_ready`
  returns an empty ready/pending set while lint passes — #222. **This is the
  load-bearing miss.**
The real consumer (`cmd_list_ready` → `_collect_status_across_tables` +
`_resolve_deps`) tests the property that matters; the gate tests a proxy for
it. Same proxy-vs-real-gate failure family as #80/#97.

## Hardening delta (one proposed fix)
Make the decompose-time gate **drive the real consumer**: run the same parse
`list-ready` runs against the just-written INDEX and assert every authored
`pending` WP is accounted for (ready ∪ dependency-blocked). 0-WP / parse-fail
while WPs exist = BLOCKING.

**Lean path (preferred):** fold the round-trip INTO `cmd_lint` so plan-work
Step 9.5's existing "lint non-zero = not done" wiring enforces it for free.
Design (plan-work/SEA) confirms extend-lint vs a distinct `verify` subcommand.

**Single source of truth (EP-03):** reuse `_collect_status_across_tables` /
`_resolve_deps` — the gate must never disagree with the real consumer.

## Test-first (MUST)
Pin the 4-variant matrix (SPEC Verification Plan): missing-table FAIL,
bad-header FAIL, wrong-status FAIL, canonical PASS. Cases 1-3 must fail against
TODAY's gate (proving the bug) before implementation.

## Size estimate
Engineering-architect-light: ~1-2 WPs (round-trip + tests as one RGB WP;
optional tiny plan-work/SKILL.md note). Confirm at plan-work.
