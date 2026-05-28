# Code Review: feat/wp-002 — Distinguish free-plan 403 from genuine missing protection

> **Timestamp:** 2026-05-28T135410Z (ISO 8601 UTC)
> **Author:** WP-002 executor
> **Branch:** feat/wp-002-freeplan-403-protection-distinction → change/harden-preflight-dev-drift-check
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change is small, well-scoped, and tested. It refines one function in the
repository arrival-check so that a private repo on GitHub's free plan — which
genuinely *cannot* turn on branch protection — is flagged with a gentle warning
instead of a hard error, while a repo that *can* turn on protection but hasn't
still gets the hard error it should. There are no build errors, the new
behaviour is covered by tests, and the existing behaviour is pinned by a
"before" test so nothing slipped. No issues that need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Clean across the board. It does one thing (refine the protection check), touches
two files (the script and its tests), adds 90 lines and removes 5, includes a
test for the new behaviour, and carries no database, schema, infrastructure, or
secret changes.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings — all four primitives clean (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

No PR-introduced errors. Mechanical floor for this repo (stdlib-only,
published-artifact profile, per `.sulis/repo-contract.yml`):

- `python3 -m compileall -q plugins/sulis/scripts` → clean (`tool-outputs/compileall-head.log`)
- manifest JSON validity → `manifests OK` (`tool-outputs/manifest-head.log`)
- routing-coverage gate (`sulis-route check`) → `passed: true` (`tool-outputs/route-gate-head.log`)
- `pytest plugins/sulis/scripts/tests/unit/test_wpx_arrival_check.py -q` → 15 passed (`tool-outputs/pytest-arrival.log`); full unit suite 767 passed / 1 skipped
- **Coverage gap (recorded):** no type-checker configured for this repo — stdlib-only tooling per the plugin contract (`type_check: ""` in repo-contract). Not skipped silently; this is the documented floor.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {refactor}               → clean (single concern)
  module_fan_out: 1 top-level dir (plugins/)   → clean
  severity: clean

Size (PH-02):
  lines_added: 90, lines_removed: 5, total: 95
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: clean (≤200 lines / ≤5 files — within CR-02 carve-out)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0
  tests_included: true (characterisation + new-branch test)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The only neighbour is the `_gh` helper (already returns the
`(rc, stdout, stderr)` 3-tuple); the diff consumes its existing 3rd element
rather than changing it. The `_Report.warn` channel already exists.

### Watch List

- **Marker-string brittleness (informational, not a finding):** detection keys on
  the substring `"upgrade to github pro"` in `gh` stderr. If GitHub changes the
  403 body wording, the free-plan path would silently revert to a hard error.
  This is the deliberate boring-code choice per HD-003 (explicit, greppable, no
  regex), and the failure is loud — the pinned test `test_rc02_freeplan_403_is_not_a_hard_error`
  would fail. No delta; noted for awareness.

### Cross-Reference

- **Existing Hardening Deltas covered:** HD-003 (this WP implements it).
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `compileall`, manifest JSON, `sulis-route check`, `pytest`. HEAD: 0 errors. Coverage gap: no type-checker (stdlib-only per plugin contract) — recorded, not skipped silently.
- [✓] **CR-02 Single-reader pass justified by diff size: 95 lines, 2 files** (≤200 lines AND ≤5 files).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (the script's `_check_rc02_protections` region + module docstring; the test file's new tests). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; Watch-List item cites the marker constant and its pinning test.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no new infra→domain import, no new external call, no module-level state; predicate is pure). Security: nothing surfaced — no authz change (read-only check), no injection (constant substring match; `repo` path interpolation unchanged), no secret exposure (matched string is a public GitHub error body), no new dependency. Quality: 0 findings — build clean, no dead surface (`_is_freeplan_protection_403` used twice, `_FREEPLAN_403_MARKER` consumed), no contract drift (rides existing `_Report.warn`), tests included for new behaviour + characterisation, CR-10 no anti-pattern matches (no loops/N+1/waterfall/subprocess introduced — `tool-outputs/cr10-loops.log`, `cr10-subproc.log` empty).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single `refactor` concern). PH-02 Size: clean (95 lines / 2 files). PH-03 Safety: clean (0 migrations/schemas/secrets/infra). PH-04 Completeness: clean (tests included). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/harden-preflight-dev-drift-check` (working tree; edits uncommitted at review time)
- **Neighbour expansion:** git grep on `_gh` / `_Report.warn` — single neighbour, no fan-out
- **Neighbour cap:** 1 of 1 considered, 0 excluded
- **Scanners run:** compileall, manifest JSON, routing gate, pytest; secret-shape + CR-10 grep scans
- **Scanners unavailable:** Gitleaks / Semgrep / Trivy not installed (stdlib-only repo) — substituted with diff grep for secret-shaped strings (none) and CR-10 procedural patterns (none)
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out
