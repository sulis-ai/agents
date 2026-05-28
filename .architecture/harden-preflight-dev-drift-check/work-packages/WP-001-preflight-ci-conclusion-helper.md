---
id: WP-001
slug: preflight-ci-conclusion-helper
title: Non-polling pre-flight CI-conclusion helper in _wpxlib
kind: backend
status: pending
primitive: Create
group: expand
source_delta: HD-001
dependsOn: []
blocks: [WP-003]
estimated_token_cost: "input: ~12k / output: ~4k"
files:
  - plugins/sulis/scripts/_wpxlib.py
  - plugins/sulis/scripts/tests/unit/test_wpxlib_preflight_ci.py
---

## Context

Implements HD-001. Foundation for the run-all pre-flight blocker (WP-003).
Adds a thin, non-polling read of a branch HEAD's **recorded** CI conclusion that
returns both the verdict and the failed-check names — reusing the existing
`GHClient`/`_gh_check_runs` port (`_wpxlib.py:1120`, `:924`). Does NOT modify
`_poll_ci` (`_wpxlib.py:1196`); the train keeps its wait-then-verdict semantics.

This is **EXPAND-Create against an existing domain-owned port**, not a Wrap: the
`GHClient` Protocol is owned by `_wpxlib`; the new helper calls it. (The module's
own HD-005 comment at `_wpxlib.py:917` confirms this classification.)

## Contract

New module-level function in `plugins/sulis/scripts/_wpxlib.py`:

```python
def _preflight_ci_conclusion(
    repo: str, branch: str, *, gh: GHClient | None = None,
) -> tuple[str, list[str]]:
    """Return (verdict, failed_check_names) for branch HEAD's CURRENT recorded
    CI conclusion. No polling. verdict ∈ {green, failed, pending, unknown}.
    failed_check_names is non-empty only when verdict == 'failed'."""
```

- Reads `_gh_check_runs(repo, branch, gh=gh)["check_runs"]`.
- Reads each run's `conclusion` **explicitly** (lesson #59) — never an exit code.
- Pass set: `("success", "neutral", "skipped")`.
- No `time.sleep`, no loop, no `cap`/`interval` parameters.
- `gh` keyword seam preserved for test injection (no monkeypatching internals).

No other public surface changes. `_poll_ci` is untouched.

## Definition of Done

### Red (failing tests first)

`plugins/sulis/scripts/tests/unit/test_wpxlib_preflight_ci.py` — imports `_wpxlib`
directly; uses an in-test `GHClient` stub whose `check_runs` returns the
`{"check_runs": [...]}` envelope shape of `RealGHClient.check_runs`
(`_wpxlib.py:996`). Named tests (all fail — helper undefined):

- `test_preflight_red_dev_returns_failed_with_names` — one `conclusion:"failure"`
  run named `web`, rest success → `("failed", ["web"])`.
- `test_preflight_green_dev_returns_green_empty` → `("green", [])`.
- `test_preflight_does_not_poll_when_runs_in_flight` — monkeypatch
  `_wpxlib.time.sleep`, assert never called; a non-completed run → `("pending", [])`.
- `test_preflight_reads_conclusion_explicitly_not_status` — `status:"completed"` +
  `conclusion:"failure"` → `("failed", ...)` (lesson #59 guard).
- `test_preflight_no_runs_recorded_returns_unknown` — empty `check_runs`
  → `("unknown", [])`.

### Green (make them pass)

- Add `_preflight_ci_conclusion` per the Contract.
- All five tests pass.
- `_poll_ci` unchanged; the existing `test_wpx_train_*` suite still passes
  (run `pytest plugins/sulis/scripts/tests/unit/test_wpx_train_run.py` etc.).
- No new imports beyond what's already in `_wpxlib.py` (`time`, `json` present).

### Blue (refactor)

- Confirm NO shared-predicate extraction with `_poll_ci` yet: two callers, and
  the pass-set predicate is intentionally independent (train verdict and
  pre-flight verdict must be free to diverge). Document that intent in the
  helper docstring. (If/when a third caller appears, extract
  `_classify_check_runs` — explicitly out of scope now.)
- Docstring names the faithfulness rationale (recorded conclusion = real
  workflow = build order inherited) and the lesson-#59 explicit-read guard.
- Run the full unit suite for `_wpxlib`; zero regressions.

## Test strategy

Pure unit, in-process import of `_wpxlib`, fake `GHClient` injected via the `gh`
keyword. No subprocess, no live `gh`. Matches `test_wpxlib_tables.py` style.
