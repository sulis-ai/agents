# Code Review: feat/wp-001-canonical-entities — Author canonical entities + Tool schemas at instances/discover-project/

> **Timestamp:** 2026-06-01T165135Z (ISO 8601 UTC)
> **Author:** Executor (WP-001 re-dispatch)
> **Branch:** feat/wp-001-canonical-entities → change/create-discover-project
> **Files changed:** 17 new (5 JSON-LD entities + 10 JSON Schemas + 1 Python test + 1 journal)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request looks good. It authors the five JSON-LD entity instances + ten Tool JSON Schemas that define what the discover-project skill is — every other piece of the discovery work will conform to the contract this PR lays down. The build is clean (all 17 new tests pass, lint clean, JSON valid), the structure mirrors the proven release-train pattern, and every identifier comes byte-exact from the corrected source-of-truth table in the design document. Nothing to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** ~1,150 lines across 17 files, but 16 of those are declarative data files (JSON-LD entities + JSON Schemas) and 1 is a test file. The data files don't carry runtime behaviour — they are the contract the rest of the work conforms to. The actual reviewable surface is the test file (~410 LOC) plus the structural correctness of the JSON.

**Scope — clean.** All changes are inside one directory (`plugins/sulis/instances/discover-project/`) plus one test file at the canonical test location. Single concern: stand up the contract for the discover-project skill.

**Safety — clean.** No database migrations, no schema changes to existing systems, no infrastructure files, no secrets. The brain foundation schemas this code depends on are pre-existing and already vendored.

**Completeness — clean.** 17 new tests cover the 16 new artifacts: parse + cardinality + brain-schema validation + canonical-ULID match + cross-WP reference resolution + verbatim user-message match against MISUSE_CASES.md. Test count is appropriate for a contract WP.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents.

### Verdict

`PASS` per CR-06. No critical/high findings in the diff; Build Verification empty; every file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — pytest 17/17, ruff clean, all 15 JSON files parse.
- **PR Hygiene:** clean across PH-01..PH-04 (CR-09)
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (canonical-as-spec; data files; no domain → infrastructure violations possible) |
| Security | 0 | 0 | — (declarative JSON; no auth/secrets/injection surfaces) |
| Quality | 0 | 0 | — (17 tests + ruff clean + pytest 1330-test full suite green) |

### Build Verification (CR-01)

No PR-introduced errors. Mechanical baseline:

| Check | Command | Outcome |
|---|---|---|
| JSON validity | `python3 -c 'json.loads(...)'` on each .jsonld + .json | 15/15 parse |
| JSON Schema lint | `Draft202012Validator(doc).check_schema(doc)` | 10/10 valid Draft 2020-12 schemas |
| Brain-schema conformance | `iter_errors` against foundation/{workflow,step,trigger,failuremode,tool}.schema.json | 5+9+1+8+5 = 28 entities all conform |
| Test suite | `pytest plugins/sulis/scripts/tests/unit/test_discover_project_canonical_entities.py` | 17/17 pass in 0.12s |
| Lint | `ruff check plugins/sulis/scripts/tests/unit/test_discover_project_canonical_entities.py` | All checks passed |
| Full unit suite | `pytest plugins/sulis/scripts/tests/unit/` | 1330/1330 pass, no regressions |

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single Conventional Commit type)
  module_fan_out: 1 directory                  → clean
  severity: clean

Size (PH-02):
  lines_added: ~1150 (estimate; mostly JSON data)
  files_changed: 17 (16 new artifacts + 1 journal)
  generated_ratio: 0 (no codegen)
  lock_file_ratio: 0
  severity: note (file count is high but content is declarative data, not behaviour code)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 10 (new JSON Schemas — but these are forward-looking contracts for not-yet-written code, not changes to existing schemas)
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0 (16 new artifacts × 17 tests covering parse + schema + cardinality + canonical-ULID match)
  api_change_without_schema: false
  severity: clean
```

PH-03 auto-downgrade did NOT fire (0 migrations, 0 secrets, 0 infra).

### Findings in the Changes

None. Single-reader pass justified by the diff shape: 16 of 17 new files are declarative JSON-LD / JSON Schema data files whose correctness is enforced by the 17-test contract suite; the 17th is the test file itself which ran end-to-end with no errors.

### Findings in the Neighbours

None. The neighbour ring (1-hop) includes:
- `plugins/sulis/brain/compiled/foundation/*.schema.json` — pre-existing brain schemas the new entities validate against; not touched.
- `plugins/sulis/instances/release-train/*.jsonld` — the reference pattern; not touched.
- `.specifications/discover-project/MISUSE_CASES.md` — read by the test for verbatim user-message check; not touched.
- `.architecture/discover-project/TDD.md` — canonical source for ULIDs; not touched (corrected in upstream commit 2bc3a68 as part of the calling session's TDD fix).

All neighbours are read-only references. No cross-tenant ULIDs, no domain → infrastructure imports possible (data files), no contract drift.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable to this WP
- **Existing security report:** none generated for this WP (no security surface)
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `pytest`, `ruff check`, `python3 -c 'json.loads'` per-file, Draft202012Validator self-check on schemas. Base: 1313 unit tests green. Head: 1330 unit tests green (+17 new). Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified.** Diff shape: 17 files but 16 are declarative data (JSON-LD entities + JSON Schemas) — the reviewable surface is one Python test file (~410 LOC) which the agent read end-to-end. Single-reader path matches the data-file character of the change.
- [✓] **CR-03 Full-file reads.** All 17 changed files read end-to-end. test file: 410 LOC, read entire. workflow.jsonld: 60 LOC, read entire. steps.jsonld: 165 LOC, read entire. failuremodes.jsonld: 130 LOC, read entire. tools.jsonld: 100 LOC, read entire. triggers.jsonld: 25 LOC, read entire. All 10 schemas <30 LOC each, read entire.
- [✓] **CR-04 Evidence discipline.** No findings to evidence.
- [✓] **CR-05 Severity rubric.** No findings raised. Applied to mechanical baseline: 0 PR-introduced errors → no `critical (quality)` raised.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced. Checks run: domain → infrastructure imports (N/A, data files), module-level singletons (N/A), circular imports (N/A), timeout/CB/retry on external calls (N/A, data files), hardcoded secrets (none — scanned all 16 data files), telemetry (the JSON-LD entities themselves carry observability invariants in the form of mechanism_detail + handles_failures). Security: nothing surfaced. Primitives checked: SEC-01..07 (no auth/access boundary, no input validation surfaces, no XSS/SSRF, no secrets in any of 16 JSON files, no injection vectors — declarative data), SC-01..04 (no new dependencies added). Scanners: manual scan of all 16 JSON files for credential patterns + secret regexes (none found). Quality: nothing surfaced. Checks: build-verification follow-up (0 errors), JSX/template ident scan (N/A — no TSX/JSX in diff), dead-surface (0 unused imports per ruff F401), contract-drift (verbatim MISUSE_CASES.md system-response strings match per test), test-coverage observation (17 tests for 16 artifacts = appropriate), CR-10 procedural checks (in-memory iteration over ≤9-element lists; no N+1, no O(N²), no unbounded materialisation, no waterfalls).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single feat type, 1 directory). PH-02 Size: note (~1150 lines / 17 files but declarative-data heavy). PH-03 Safety: clean (0 migrations, 0 secrets, 0 infra). PH-04 Completeness: clean (17 tests cover all 16 artifacts). PH-03 high → auto-downgrade: no.

#### Run details

- **Diff source:** `git diff change/create-discover-project...feat/wp-001-canonical-entities` + untracked files (all new)
- **Neighbour expansion:** git grep + manual graph analysis (canonical-as-spec means neighbours are read-only schema + reference data)
- **Neighbour cap:** 4 of 4 considered (foundation schemas, release-train instances, MISUSE_CASES.md, TDD.md)
- **Scanners run:** pytest, ruff (F401, full), json.loads per-file, JSON Schema Draft 2020-12 self-check
- **Scanners unavailable:** Gitleaks, Semgrep, Trivy — N/A for declarative JSON data + a pytest file with no I/O surface; manual scan substituted
- **Lenses dispatched in parallel:** no (single-reader path per CR-02 carve-out justified above)
