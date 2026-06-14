# fix: wpx-preflight treats a no-runs 404 as advisory, not a crash

Closes #310.

## Problem

run-all's pre-flight `wpx-preflight dev-clean --branch <change-branch>` raised
an unhandled `RuntimeError` ("gh check-runs failed: gh: Not Found (HTTP 404)")
when the base change branch had no CI runs yet (fresh branch / commit GitHub
has no check-runs ref for), crashing the loop instead of returning the
advisory `{ok:true, warnings:[...]}` envelope it expects for "no CI recorded".

`_dev_clean` already maps `verdict == "unknown"` to that advisory envelope —
but `_preflight_ci_conclusion` raised inside `_gh_check_runs` before it could
return `unknown`.

## Fix

Wrap the `_gh_check_runs` call in `_preflight_ci_conclusion`: a RuntimeError
whose message contains `404` / `Not Found` is "no CI recorded" → return
`("unknown", [])` (the same verdict as an empty runs list — absence of
evidence is not a red). Any other gh failure (auth, rate-limit, network) still
re-raises.

## Tests

`tests/unit/test_wpxlib_preflight_ci.py`:
- `test_preflight_no_runs_404_returns_unknown_not_crash` — the 404 → unknown.
- `test_preflight_non_404_gh_error_still_raises` — a 403/rate-limit still
  surfaces.
Full preflight suite green (15 passed).
