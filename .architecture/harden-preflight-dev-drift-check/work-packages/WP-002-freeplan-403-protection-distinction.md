---
id: WP-002
slug: freeplan-403-protection-distinction
title: Distinguish private-free-plan 403 from genuine missing protection in arrival-check
kind: backend
status: pending
primitive: Refactor
group: reorganise
source_delta: HD-003
dependsOn: []
blocks: [WP-004]
characterisation_test: "tests/unit/test_wpx_arrival_check.py::test_rc02_genuine_missing_protection_still_errors"
estimated_token_cost: "input: ~14k / output: ~4k"
files:
  - plugins/sulis/scripts/wpx-arrival-check
  - plugins/sulis/scripts/tests/unit/test_wpx_arrival_check.py
---

## Context

Implements HD-003. Foundation for the unprotected-repo warning (WP-004).
Refines `_check_rc02_protections` (`wpx-arrival-check:128`) so a private
free-plan 403 ("Upgrade to GitHub Pro…") is classified as a warning-eligible
*unavailable-on-plan* condition rather than a hard RC-02 error — while a genuine
missing protection on a capable repo still hard-errors (spec constraint:
public/protected RC-02 semantics MUST be preserved).

REORGANISE (Refactor) of existing behaviour → a characterisation test pins the
preserved path first (CLAUDE.md non-negotiable #3).

## Contract

In `plugins/sulis/scripts/wpx-arrival-check`:

```python
_FREEPLAN_403_MARKER = "upgrade to github pro"

def _is_freeplan_protection_403(rc: int, stderr: str) -> bool:
    """True when protection is unavailable because the repo is private on the
    free plan (403 'Upgrade to GitHub Pro…'), vs a genuine missing/misconfigured
    protection on a capable repo."""
```

`_check_rc02_protections` MODIFIED to:
- Capture stderr from `_gh(...)` (today it discards it: `rc, out, _ = ...`).
- On free-plan 403: `rep.warn("RC-02", ...)` naming the gating gap; NOT an error.
- On other `rc != 0`: existing `rep.error("RC-02", ...)` — UNCHANGED.
- On `rc == 0`: existing required-status-checks parsing — UNCHANGED.
- `main` protection probe: free-plan 403 → no double-warn; else existing error.

No change to RC-01/03/05/07/10. The `_Report.warn` channel already exists
(`wpx-arrival-check:99`).

## Definition of Done

### Red (characterisation first, then the new branch)

In `plugins/sulis/scripts/tests/unit/test_wpx_arrival_check.py` (uses `run_tool`
+ `mock_gh`; `exit_code` + `stderr` already supported by the fixture):

- `test_rc02_genuine_missing_protection_still_errors` — **CHARACTERISATION.**
  `branches/dev/protection` → `exit_code:1`, stderr `"gh: Not Found (HTTP 404)"`
  (no free-plan marker). Asserts RC-02 error still present. **Confirm this passes
  against CURRENT code before refactoring.**
- `test_rc02_freeplan_403_is_not_a_hard_error` — **NEW (fails).**
  `dev` + `main` protection → `exit_code:1`, stderr with "Upgrade to GitHub Pro…".
  Asserts: no RC-02 error; an RC-02 warning present; warning names the
  unavailable-on-plan case.

### Green (make the new test pass without breaking the characterisation)

- Add `_FREEPLAN_403_MARKER` + `_is_freeplan_protection_403`.
- Wire the branch into `_check_rc02_protections`.
- Both new/characterisation tests pass.
- **Every existing `test_wpx_arrival_check.py` test still passes** — especially
  `test_rc02_requires_branch_ci_only_not_merge_queue_ci`,
  `test_rc02_fails_if_merge_queue_ci_is_a_classic_required_check`, and
  `test_published_solo_repo_passes` (public-repo semantics intact).

### Blue (refactor)

- Predicate + marker constant are named and documented.
- Warning text is plain-English and carries the gating-gap explanation, so WP-004
  can reuse the exact wording (one voice).
- Note for WP-004: if `wpx-preflight` will also consume the predicate, leave it
  here for now; the shared-primitive extraction to `_wpxlib.py` is WP-004's Blue
  (the second caller is what triggers the extract-now rule).

## Test strategy

Subprocess style (`run_tool` invoking `wpx-arrival-check`), `mock_gh` substring
dispatch with `exit_code`/`stderr`. Matches the existing arrival-check test file
exactly. `sulis-ai/agents` is public, so the free-plan 403 is only reachable via
the mock — which is the correct and only way to test it deterministically.
