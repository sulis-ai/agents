# Code Review: feat/wp-008-discover-project-skill-v2 — Author plugins/sulis/skills/discover-project/SKILL.md

> **Timestamp:** 2026-06-01T184026Z (ISO 8601 UTC)
> **Author:** WP-008 executor
> **Branch:** feat/wp-008-discover-project-skill-v2 → change/create-discover-project
> **Files changed:** 3 (2 new, 1 modified)
>
> **Outcome:** Ready to merge

---

## At a glance

Your pull request is clean. It authors the `SKILL.md` deliverable for
WP-008 plus the 11 structural conformance tests that pin its shape,
and adds a 12th n=2 dogfood test that runs the canonical-drift
detector against the new file. Every test passes; the drift detector
returns exit 0 against the real SKILL.md (which is the load-bearing
acceptance for the whole change). Nothing blocks merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Three files, about 560 lines total: the SKILL.md
itself (260 lines of structured markdown with annotations), the new
conformance test file (250 lines, 11 tests), and a 52-line dogfood
test appended to the existing drift-detector test file. The size is
proportional to a single docs deliverable with thorough conformance
coverage.

**Scope — clean.** One concern: WP-008's SKILL.md deliverable plus
the tests that prove its conformance to the canonical Workflow.

**Safety — clean.** No migrations, schema changes, infra, or
secrets touched.

**Completeness — clean.** The tests for the new deliverable ship in
the same PR as the deliverable itself.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high findings, 0 medium, 0 note (CR-09 / PH-01..PH-04 all low severity)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

- `ruff check` against the new test file: clean (exit 0).
- `pytest` against the new conformance file + the modified
  drift-test file: 25/25 pass.
- `check-canonical-drift.py` invoked against
  `plugins/sulis/skills/discover-project/SKILL.md` with
  `--cross-tenant-refs-allowed-for release_workflow_ref`: exit 0,
  `{"ok": true, "data": {"drift": []}}`. This is the load-bearing
  ADR-001 acceptance signal — the imperative matches the canonical.

No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {docs}                  → clean
  module_fan_out: 1 top-level dir (plugins/)  → clean
  severity: low

Size (PH-02):
  lines_added: ~562 (SKILL.md 261 + new test 249 + appended test 52)
  files_changed: 3
  generated_ratio: 0
  lock_file_ratio: 0
  severity: low (within 501-1000 band but single-concern; size
  attributable to one prose deliverable + its conformance harness)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: low
```

### Findings in the Changes

Architecture lens: nothing surfaced. Checks run:
- New domain imports: none (test file imports only stdlib + pytest).
- New module-level singletons / `getInstance()` patterns: none.
- New circular imports: none (test file's only sys.path manipulation
  is the existing convention; new conformance test resolves
  marketplace root via relative-path math, no new imports).
- New HTTP/RPC/DB calls without timeout: none.
- New retries without backoff/jitter: none.
- New external calls without circuit breaker: none.
- Hardcoded credentials: none.
- New service-to-service plain-HTTP calls: none.
- New OpenTelemetry-missing handlers: none.
- PII in logs: none.

Security lens: nothing surfaced. Primitives applicable to a markdown
deliverable + python conformance tests are SEC-05 (input validation
on dynamic file reads) — N/A here: the test reads a fixed-path
markdown file shipped in-repo. No SC-NN dependency surface (no new
deps).

Quality lens:
1. Build Verification follow-up: 0 errors.
2. JSX/template scan: N/A (no TSX/JSX/Vue/Svelte files in diff).
3. Dead-surface findings: 0 (initial `heading = f"## Phase "`
   dead-variable iteration artifact was removed during Step 6 lint
   pass; current code is clean).
4. Contract-drift findings: 0. The conformance tests' contract IS
   the canonical Step set; the dogfood test enforces zero drift
   between canonical and imperative.
5. Test-coverage observation: 12 tests for the new deliverable, all
   in the same PR. No source-without-test gap.
6. Style/readability: SKILL.md ordering matches WP-001 phases field
   (Detect → Infer → Ask → Mint → Verify); pre-flight sweep
   correctly sits BEFORE Phase 1 heading (the specific refinement
   over the prior dispatch).
7. CR-10 procedural performance checks: not applicable; no loops,
   no DB calls, no RPC calls in the diff. The conformance tests
   themselves run in <0.1s wall-clock.

### Findings in the Neighbours

Nothing surfaced. Neighbour ring: `check-canonical-drift.py`,
`_canonical_drift/matcher.py` (the file the WP-009 fix at SHA
`7438818` patched), `_canonical_drift/parser.py`. All read; no
PR-exposed gaps.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable.
- **Existing security report:** none applicable.
- **Pattern suggesting full audit:** none surfaced.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` on the two test files (exit 0); `pytest` on both test files (25/25 pass); `check-canonical-drift.py` against the new SKILL.md with the cross-tenant flag (exit 0, `{"ok": true, "data": {"drift": []}}`). Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified.** Diff: ~562 lines / 3 files. Above the strict 200-line threshold but the work is bounded (1 markdown deliverable + its conformance tests, no business logic, no runtime code) and falls within the file-count carve-out. Recorded here as the carve-out reason rather than dispatching parallel lenses for a docs PR.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (SKILL.md 261 lines; test_discover_project_skill_conformance.py 249 lines; test_check_canonical_drift_discover.py diff 52 lines + surrounding context).
- [✓] **CR-04 Evidence discipline.** No findings to evidence; the build-verification section cites verbatim tool outputs.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; no lens silent; PH-03 low).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives listed. Quality: all seven outputs produced (4 explicitly clean; 2 N/A documented; 1 documented as zero matches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low. PH-02 Size: low (within band, single-concern justification). PH-03 Safety: low. PH-04 Completeness: low. No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** local working tree vs origin/change/create-discover-project
- **Neighbour expansion:** git grep for symbols touched by the diff; reviewed `_canonical_drift/matcher.py` (the WP-009 fix at 7438818), `_canonical_drift/parser.py` (HTML-comment parser), `check-canonical-drift.py` (CLI entry point).
- **Neighbour cap:** 3 files considered; under the 20-cap.
- **Scanners run:** ruff, pytest, check-canonical-drift CLI.
- **Scanners unavailable:** Gitleaks/Trivy/Semgrep not invoked (no security-sensitive surface in a markdown + python-conformance-tests diff).
- **Lenses dispatched in parallel:** no — single-reader carve-out justified per above.
