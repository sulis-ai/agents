# Code Review: feat/wp-004-capture-idea-orchestrator — capture_idea orchestrator

> **Timestamp:** 2026-06-03T085304Z (ISO 8601 UTC)
> **Author:** executor (WP-004)
> **Branch:** feat/wp-004-capture-idea-orchestrator → change/create-brain-backlog-and-traversal
> **Files changed:** 2 (1 modified, 1 new test file)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the piece that makes "every idea gets a reason before it's saved" a real rule in the code, not just a guideline. It's well-scoped — one new function plus its safety net of tests, all in one file — and it builds cleanly with every test passing. There are no issues that need attention before merging.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: one module touched, one new test file. 317 lines of new code, 425 lines of tests — more test than code, which is the right ratio for a rule this important.

**Scope — clean.** Single purpose (the capture orchestrator), single concern, one `feat:` change.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets.

**Completeness — clean.** Ten tests cover every path: the reject-blank-reason gate, the quick path with and without a follow-up requirement, the full path reading a matured idea back, the three refusal cases (missing id, broken chain, store unavailable), idempotency, and the roadmap flag.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; both changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean/low)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (nothing surfaced) |
| Security | 0 | 0 | — (nothing surfaced) |
| Quality | 0 | 0 | — (nothing surfaced) |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check` clean on both files; `py_compile` OK;
`test_brain_capture.py` 10 passed; full unit suite 1787 passed, 9 skipped.
No type-checker is configured for this repo (stdlib-only plugin tooling
contract) — recorded as a coverage gap in Methodology, consistent with
branch-ci.yml's `type-check — (none configured)` step.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 (plugins/sulis/scripts)    → clean
  severity: none

Size (PH-02):
  lines_added: 317, lines_removed: 6 (impl); +425 new test file
  files_changed: 2
  severity: low (single module; test-heavy)

Safety (PH-03):
  migration_count: 0; schema_idl_count: 0; infra_files: 0; secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the source change ships with 10 tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

**Architecture lens: nothing surfaced.** Checks run: dependency-direction
(the orchestrator depends inward on the `EntityRepository` port + the pure
`compose_*_from_idea` transforms, never on a concrete adapter — WPB-01/02
respected; the adapter is injected, WPB-07); no new module-level singletons;
no new circular imports (imports are siblings already in the module's import
set); resilience — the `_store` wrapper converts every store touch's failure
to `CaptureError` (graceful degradation, NFR-01, mirrors `_brain_emit_helper`
`_safely`); no new external HTTP/RPC calls; verification — the new behaviour
is covered by real-adapter tests against vendored schemas (MEA-09, no mocks),
matching the in-memory-first discipline (WPB-03/08).

**Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no
access-control surface — pure orchestration behind an injected port; no
injection vector — ids are schema-validated at the adapter boundary; no
user-supplied path traversal — paths are derived, `seed`/`why`/`what` flow
only into deterministic id derivation + schema-validated entity fields),
SC-01..04 (no new dependencies). Scanners: secret-pattern grep over the diff
— 0 hits. No plaintext credentials, no tokens.

**Quality lens: nothing surfaced.**
1. Build Verification follow-up — none (baseline clean).
2. JSX/template identifier scan — N/A (no TSX/JSX/Vue/Svelte files).
3. Dead-surface — none; every new helper (`_store`, `_acquire_quick_opportunity`,
   `_acquire_full_opportunity`, `_emit_requirement_if_what`) has a live caller
   in `capture_idea`; `CaptureError` and `capture_idea` are the public surface
   the CLI (WP-006) consumes.
4. Contract-drift — none; the result dict matches the WP Contract's documented
   shape (`opportunity_id`, `requirement_id`, `roadmap`, `chain`,
   `bootstrapped`); the three `CaptureError` paths match ADR-003/004/005.
5. Test-coverage observation — strong; 10 tests, source ships with tests, all
   branches of the new orchestrator exercised (incl. the two NFR-01 refusal
   branches and store-degradation).
6. Style/readability — clean; descriptive names, "why" comments, explicit
   `Literal` branch (boring-code), the why-first gate is a literal `if`.
7. Performance procedural checks (CR-10) — no anti-pattern matches; the module
   has no loops, no N+1 (each capture does a bounded, fixed number of store
   touches), no unbounded materialisation.

Note on the one broad-except: `_store` catches `Exception` at line 313 with an
explicit `# noqa: BLE001` and a comment naming it the deliberate degradation
boundary — this is the NFR-01 contract (a brain-unavailable store must yield
`CaptureError`, never an uncaught crash), re-raising `CaptureError` unwrapped
first. Intentional and tested (`test_brain_unavailable_store_degrades_to_capture_error`).
Not a finding.

### Findings in the Neighbours

None. The diff calls into `bootstrap_backing_chain`, `roadmap_add`,
`compose_opportunity_from_idea`, `compose_requirement_from_idea`,
`LocalFileEntityAdapter` — all pre-existing, already tested, unchanged by this
WP.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`,
  `python -m py_compile`, `pytest tests/unit/test_brain_capture.py`. Head: 0
  errors. Coverage gap: no type-checker configured (stdlib-only plugin
  contract; matches branch-ci.yml).
- [—] **CR-02 Parallel dispatch.** Diff is 2 files (1 impl module + 1 test
  file), single module, single purpose, authored end-to-end this session and
  already read fully. Lenses applied inline given the bounded single-module
  scope. Recorded as a deliberate carve-out: the >200-line trigger is driven
  by the test file, not breadth — fan-out is 1 directory, 1 production module.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end
  (`_brain_capture.py` 540 lines, `test_brain_capture.py` 425 lines). Unread
  files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens scans cited.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  (Build Verification empty; all files read end-to-end; all lenses produced
  output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks
  listed. Security: nothing surfaced + primitives/scanners listed. Quality:
  all seven outputs produced (item 2 N/A — no JSX).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (1 dir, feat-only).
  PH-02 Size: low (2 files; test-heavy). PH-03 Safety: none (0 migrations/
  schemas/secrets/infra). PH-04 Completeness: none (source ships with 10
  tests). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff origin/change/create-brain-backlog-and-traversal`
  (working tree; pre-commit review per Step 6.5).
- **Neighbour expansion:** git grep over the symbols the diff calls; all
  neighbours pre-existing + unchanged.
- **Neighbour cap:** not reached (0 neighbour findings).
- **Scanners run:** ruff, secret-pattern grep.
- **Scanners unavailable:** type-checker (none configured — plugin contract).
- **Lenses dispatched in parallel:** no — single-module carve-out (see CR-02).
