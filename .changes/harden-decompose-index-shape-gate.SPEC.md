# harden: decompose-time INDEX shape gate (wire wpx-index lint)

Closes #103.

## Problem

During CH-01KSSV, SEA's `plan-work` produced an `INDEX.md` with the WPs as
bullet lists rather than the canonical
`| ID | Title | Primitive | Status | Depends On | Blocks |` table the
`wpx-*` tools require. `wpx-index flip-status` / `list-ready` then failed
at run-all time with `Could not find WP table (no | ID | header)` — the
exact #60 class. The #60 fix had already added a `wpx-index lint`
subcommand, but it wasn't run at decompose time, so the drift still
reached the loop, hours after the architect was "done."

## Fix

Wire `wpx-index lint` into `plan-work` SKILL.md as an explicit **MUST**
gate at **Step 9.5** (between writing `INDEX.md` at Step 9 and reporting
at Step 10):

```bash
"$WPX_DIR/wpx-index" lint --project {project}
```

A non-zero exit blocks the decompose from being declared done. The
architect must fix the INDEX to the canonical table form and re-run the
lint before proceeding to Step 10.

Also strengthen Step 9's prose to explicitly forbid the bullet-list
shape ("The WP Table MUST be a markdown table headed
`| ID | Title | Primitive | Status | Depends On | Blocks |` — never a
bullet list") and Step 10's Report to list the lint result as part of
the decompose outcome.

## Why this is the right layer

- The `wpx-index lint` subcommand already exists (#60); the gap was
  workflow integration, not new code.
- Failing at decompose time is **surgical** (architect re-emits the
  table); failing at run-all dispatch time is a **hard recovery** that
  blocks the entire ship.
- The fix lives in the SKILL.md the architect runs — no executor-side
  or runtime change needed.

## Tests

Documentation-only orchestrator-instruction amendment — no executable
test. Verification is review + the existing `Canonical-vs-implementation
drift` CI gate.
