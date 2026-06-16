# Code Review: PR feat/wp-003-unassign-server — Unassign server write (helper --clear, adapter, DELETE route)

> **Author:** executor (WP-003)
> **Branch:** wp/feat-cockpit-product-experience/wp-003-unassign-server → change/feat-cockpit-product-experience
> **Files changed:** 6
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the "remove a change from a product" ability on the server side, behind the
same single, audited write path the assign feature already uses. It is small (about 360 lines),
backend-only, and every new behaviour has a test. The build is clean (types, linting, and the
full test suites all pass), and there are no security or design concerns. No issues need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Well-shaped: one purpose (the server half of un-assign), 6 files, no database migrations, no
infrastructure changes, no dependency changes. New code and its tests land together — the helper,
the adapter method, and the new route each ship with their own tests.

## Things to take away

Nothing specific — the change is clean and well-tested.

---

## Technical detail

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files >50
lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — clear path stays behind the single allow-listed write site |
| Security | 0 | 0 | none — ULID-validated before helper; explicit `--clear` keeps assign validation strict |
| Quality | 0 | 0 | none — full test coverage of new behaviour; docstring corrected |

### Build Verification (CR-01)

Mechanical baseline run on HEAD: `tsc --noEmit -p server && tsc --noEmit -p client` (exit 0);
`eslint --ext .ts,.tsx .` (clean); `python3 -m py_compile set-change-product.py` (OK). Full
cockpit Vitest suite 1552 passed / 0 failed; full `plugins/sulis/scripts/tests/unit` pytest
3190 passed / 9 skipped. 0 PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 2 → none
Size (PH-02):         +326 / -34; files 6 → none (within 5-file band by intent; small)
Safety (PH-03):       migrations 0; schemas 0; infra 0; secrets 0 → none
Completeness (PH-04): new_source_without_test 0; api_change_without_schema false → none
```

### Findings in the Changes

None.

Architecture lens — nothing surfaced. Checks run: dependency direction (no new domain→infra
import; the new `clearChangeProduct` stays inside the adapter, the route remains a thin
parse-then-delegate handler — WPB-01/04); single write site preserved (the clear drives the same
sanctioned `set-change-product.py` helper, ADR-001); request-controlled `changeId` ULID-validated
before any helper runs (WPB-05 / path-confinement parity with assign); no new external network,
no timeout/circuit-breaker surface (the helper subprocess inherits the adapter's bounded 30s
timeout); structured `logWrite("clear-change-product")` audit line (WPB-10).

Security lens — nothing surfaced. Primitives checked: SEC validation/access-control,
secrets exposure. `clearChangeProduct` validates `changeId` against `CHANGE_ULID_RE` before the
helper runs (rejects `../`-laden ids with VALIDATION_FAILED — covered by a test). The clear drives
an explicit `--clear` flag, never an empty `--for-product`, so the assign path's strict
`dna:product:` validation is unweakened (verified by the pytest mutual-exclusion + empty-rejection
cases). Helper errors surface through the existing `unwrap` opaque-message path (CWE-209 inherited).
No secret-shaped additions in the diff.

Quality lens — 0 findings.
1. Build Verification follow-up: none (baseline clean).
2. JSX/template identifier scan: n/a (no TSX/JSX files in diff).
3. Dead-surface: none — `parseSavedChangeId` has 2 consumers; `clearChangeProduct` is wired into
   the DELETE route + the port interface.
4. Contract-drift: none — the DELETE route returns `{ ok, id, forProduct: null }`, matching
   `ClearChangeProductResult` (extends `ChangeProductResultBase`, carries `ok`). The stale
   docstring claiming the clear result is "without the `ok` envelope" was corrected (folded in
   from WP-001's security review advisory).
5. Test-coverage: full — helper pytest (clear/idempotent/mutual-exclusion/empty-rejection),
   adapter test (real-helper clear + malformed-id rejection), route test (delegate + 400-guard +
   writer-error). No source-only-without-test surface.
6. Style/readability: clean.
7. Performance procedural checks (CR-10): no anti-pattern matches — no new loops with per-iteration
   I/O; the clear is a single read-modify-save.

### Findings in the Neighbours

None. Neighbours: `app.ts` (composition root, injects `SpineSettingsAdapter` which now implements
both port methods — typechecks), `api-types.ts` (`ClearChangeProductResult` unchanged, already
carries `ok`), the existing PUT assign route + its tests (unchanged; the `appWith` test helper now
fills default stubs so the assign cases keep passing after `clearChangeProduct` became required).

### Watch List

None.

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for this change.
- WP-001 security-review advisory (stale docstring) — addressed in this PR.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** tsc (server+client) exit 0; eslint clean; py_compile OK; vitest 1552 pass; pytest unit 3190 pass. Base clean, head clean. Coverage gap: none.
- [✓] **CR-02 Dispatch.** Diff 326 lines / 6 files. Single-reader pass: all 6 files read end-to-end during implementation + review; backend-only, single-concern, no cross-kind surface. Recorded as a deliberate single-reader review for a focused backend WP.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (authored this session). Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings: none; lens notes cite the specific mechanisms (ULID validation, single write site, contract match).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 none).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks listed. Security: 0 findings + primitives listed. Quality: all 7 outputs produced (0 findings).
- [✓] **CR-09 PR Hygiene applied.** PH-01 none; PH-02 none; PH-03 none (0 migrations/secrets/infra); PH-04 none. No auto-downgrade.

#### Run details

- **Diff source:** git diff change/feat-cockpit-product-experience...HEAD
- **Neighbour expansion:** git grep for `ChangeProductWriter` / `clearChangeProduct` / `assignChangeProduct` call sites (composition root + tests + api-types).
- **Neighbour cap:** not reached (4 neighbour files considered).
- **Scanners run:** tsc, eslint, py_compile, vitest, pytest; diff-level secret + CR-10 perf grep.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (diff-level secret grep used; no secret-shaped additions; backend-only diff with no dependency change).
- **Lenses dispatched in parallel:** no — single-reader pass for a focused 6-file backend WP (CR-02 recorded).
