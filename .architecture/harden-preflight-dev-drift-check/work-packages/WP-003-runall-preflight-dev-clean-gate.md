---
id: WP-003
slug: runall-preflight-dev-clean-gate
title: wpx-preflight dev-clean entrypoint + run-all Step 0 hard blocker
kind: backend
status: pending
primitive: Create
group: expand
source_delta: HD-002
dependsOn: [WP-001]
blocks: []
estimated_token_cost: "input: ~16k / output: ~6k"
files:
  - plugins/sulis/scripts/wpx-preflight
  - plugins/sulis/scripts/tests/unit/test_wpx_preflight.py
  - plugins/sulis/skills/run-all/SKILL.md
---

## Context

Implements HD-002. The primary fix surface of lesson #52. Wraps WP-001's
`_preflight_ci_conclusion` in a tested `wpx-preflight dev-clean` CLI (the repo's
skill↔script split: deterministic logic in a script, skills orchestrate), and
wires a Step 0 gate into `/sulis:run-all` that STOPS with one up-front blocker
when the base branch HEAD is CI-red — before any wave is dispatched.

## Contract

**New CLI** `plugins/sulis/scripts/wpx-preflight` with subcommand `dev-clean`:

```
wpx-preflight dev-clean --repo <org/repo> --branch <branch=dev>
```

Emits the same JSON envelope shape as `wpx-arrival-check`
(`{"ok": bool, "errors": [...], "warnings": [...]}`) + exit code:

| verdict (from WP-001) | ok | exit | errors / warnings |
|---|---|---|---|
| `green` | true | 0 | — |
| `unknown` (no runs recorded) | true | 0 | warning: "no CI recorded for <branch> HEAD yet" |
| `pending` (runs in-flight) | true | 0 | warning: "CI still running on <branch>" |
| `failed` | false | 2 | error `rule:"PRE-01"`, `actual:"N pre-existing CI failures: [names]"`, `expected:"green"` |

`PRE-01` blocker is a hard stop — no override (spec decided-by-default,
consistent with the train pausing on red). Absence of evidence
(`unknown`/`pending`) does NOT block — the pre-flight reads recorded state, it
does not wait.

**run-all/SKILL.md MODIFIED** — new **Step 0** in "The parallel loop", before
Step 1 (read INDEX):
- Determine `BASE_BRANCH` by reusing the existing CW-04 detection (Step 12 already
  computes `change/*` vs `dev`).
- Invoke `"$WPX_DIR/wpx-preflight" dev-clean --repo <org/repo> --branch "$BASE_BRANCH"`.
- `ok:false` → STOP; emit ONE founder-English blocker naming the count + check
  names; dispatch nothing.
- `ok:true` → proceed to Step 1 exactly as today.

## Definition of Done

### Red (failing tests first)

`plugins/sulis/scripts/tests/unit/test_wpx_preflight.py` (subprocess style,
`run_tool` + `mock_gh`; `wpx-preflight` does not exist yet → all fail):

- `test_preflight_red_dev_emits_blocker_with_count` — `commits/dev/check-runs`
  mock with one `failure` (name `web`) → `ok:false`, exit 2, `PRE-01` error whose
  `actual` contains the count `1` and the name `web`.
- `test_preflight_green_dev_is_ok` — all success → `ok:true`, exit 0.
- `test_preflight_reads_conclusion_explicitly` — `status:completed` +
  `conclusion:failure` → `ok:false` (lesson #59 guard, end-to-end).
- `test_preflight_unknown_no_runs_is_ok_with_warning` — empty `check_runs` →
  `ok:true`, exit 0, advisory warning present.
- `test_preflight_pending_in_flight_is_ok_with_warning` — a `status:in_progress`
  run → `ok:true`, exit 0, advisory warning present (did not block, did not poll).

### Green (make them pass)

- Add `wpx-preflight` with the `dev-clean` subcommand importing
  `_wpxlib._preflight_ci_conclusion` (WP-001).
- All five tests pass.
- Mark the script executable (matches sibling `wpx-*` scripts; the `run_tool`
  fixture invokes `scripts_dir / tool` directly).
- run-all/SKILL.md documents Step 0: invoke → stop-on-`ok:false` → else proceed.
  The blocker copy is plain-English and names the count + failing check names.

### Blue (refactor)

- Confirm the JSON envelope matches `wpx-arrival-check`'s `_Report.emit` shape so
  the skill parses it with the pattern it already uses (no new contract). If the
  envelope-building duplicates `_Report`, consider importing/reusing it; if the
  shape is trivial, a local builder is fine — document the choice.
- Confirm Step 0 reuses CW-04 base-branch detection rather than re-deriving it.
- Verify the green path is byte-for-byte unchanged for an already-green dev
  (spec acceptance: "run proceeds exactly as today").

## Test strategy

Script tests are subprocess + `mock_gh` (deterministic, no live `gh`). The
skill-body Step 0 is markdown — not unit-testable; its guarantee lives in
`wpx-preflight` + WP-001. Reviewer checks: gate BEFORE dispatch, hard stop on
`ok:false`, single plain-English blocker, base-branch reuse. A
`/sulis:verify-architecture` pass should drive the run-all surface against a
mocked-red dev (or at minimum assert the `wpx-preflight` gate).

## Honest note

`/sulis:run-all` flows are founder-facing even though this change is internal
tooling — the blocker copy MUST pass founder-English (no `WP-`, `PRE-01`,
`_poll_ci`, jargon). Lead with what to do: "dev has N pre-existing CI failures —
fix these first, then re-run. Nothing was dispatched."
