# fix: sulis-verify-acceptance allows subprocess-only scenarios without targets.local

Closes #171.

## Problem

`sulis-verify-acceptance --scenario --target local` refused to run with
"No local target URL in the repo-contract" on a published-artifact /
plugin / library repo with no standing app, **even when every step in the
scenario was a subprocess-mechanism step that never dereferences a target
URL**. This blocked the from-graph acceptance gate (and therefore the
v0.95.0 scenario-route TestResult deposit) for any repo without a
standing local app.

## Fix

Resolve the journey's step + tool lookup tables BEFORE the target-URL
check, then ask whether any step's driver is `http_call`. Only require
`targets.local` when the answer is yes. Subprocess and human steps run
with an empty base URL (they never use it).

A new module-level helper `_journey_needs_target_url(steps_by_id,
tools_by_id, ordered_step_ids)` keeps the inspection compact and
testable. Both bundle and `--scenario` (from-graph) sources share the
same gate.

## Tests

- `test_cli_passes_on_subprocess_only_scenario_without_local_target` —
  RED before the fix; subprocess-only bundle now succeeds with no
  `targets.local`.
- `test_cli_still_errors_on_missing_target_when_http_step_present` —
  regression: bundles with any `http_call` step still get the
  exit-2 + "no target URL" guard.
- Full scenario/acceptance/verify suite green (124 tests).
