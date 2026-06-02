# Code Review: PR-feat/wp-004-author-failuremodes-instance — Author 8 FailureMode instances

> **Timestamp:** 2026-06-01T101253Z (ISO 8601 UTC)
> **Author:** WP-004 executor
> **Branch:** feat/wp-004-author-failuremodes-instance → change/create-release-train-as-entities
> **Files changed:** 4 (487 lines added)
>
> **Outcome:** Ready to merge

---

## At a glance

Your change adds the 8 FailureMode entity instances that the release-train workflow defends against, plus a test file that validates them against the foundation schema, plus a vendored copy of the schema itself. The change is clean: the build is green, the tests are real (they catch missing required fields, wrong enum values, naming drift), and the file scope sits squarely inside what the work package asked for. One small note about a naming mismatch between the work package's description table and the actual schema vocabulary — handled correctly in the code, worth flagging for posterity.

## What to fix

No issues that need attention. The change is ready to merge as-is.

## How this pull request is shaped

**Size — looks fine**

487 lines across 4 files. About a quarter of that is a JSON Schema file copied verbatim from the brain plugin (mechanical content, not new logic). The remaining ~350 lines are data (the 8 failure-mode declarations) and tests (six of them, one per Definition-of-Done checklist item).

**Scope — looks fine**

All four files sit inside what work-package WP-004 asked for: the failure-modes data file, the schema it validates against, the test, and the executor's own journal. No drift into other work packages' files.

**Safety — looks fine**

No database migrations. No infrastructure changes. No secrets. The vendored schema is byte-identical to the upstream source in the brain plugin — confirmed by a manual diff.

**Completeness — looks fine**

The Definition of Done lists 5 test cases; the change ships 6 (the extra one tests the naming convention as a forward-defense against drift). All of them pass against the new data file.

## Things to take away

(Nothing specific to this PR — the change is clean and well-scoped.)

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings high+, all 4 primitives `low` (CR-09 / PH-01..PH-04)
- **In the changes:** 1 finding (low, quality-lens, contract-drift)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single quality finding is documented in the artefact and journal; no delta required)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced |
| Security | 0 | 0 | Nothing surfaced |
| Quality | 1 (low) | 0 | WP Contract↔schema vocabulary drift (documented; code conforms to schema) |

### Build Verification (CR-01)

Zero PR-introduced errors. Mechanical baseline commands:

- `uv run pytest tests/unit/test_failuremodes_instance_valid.py` → 6 passed (see `tool-outputs/pytest-failuremodes.log`)
- `python3 -m compileall <test-file>` → exit 0
- `python3 -c 'json.load(failuremodes.jsonld)'` → exit 0
- `python3 plugins/sulis/scripts/sulis-route check` → passed, no orphans/duplicates
- Full unit suite (`uv run pytest tests/unit/ -q`) → 1190 passed, no regressions

No `tsconfig.json`, no `.eslintrc*`, no `go.mod`, no `Cargo.toml` in the changed paths — Python-only WP. The project's lint step in `branch-ci.yml` is `compileall` + manifest JSON-validity, both reproduced locally.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → clean
  module_fan_out: 3 distinct top-level dirs
    (architecture/, plugins/sulis/instances/, plugins/sulis/scripts/,
     plugins/sulis/brain/compiled/ — all WP-Contract scope)
  severity: low

Size (PH-02):
  lines_added: 487, lines_removed: 0, total: 487
  files_changed: 4
  generated_ratio: ~0.27 (133 lines are vendored schema)
  lock_file_ratio: 0
  severity: low (501-line band not reached, well within 16-30 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 1 (vendored, identical to upstream)
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0
  new_test_files: 1 (with 6 tests)
  api_change_without_schema: false
  severity: low
```

No auto-downgrade triggers fired.

### Findings in the Changes

#### Q-01 (low, quality, contract-drift) — `plugins/sulis/instances/release-train/failuremodes.jsonld` (all entries)

**What's happening:** The WP-004 Contract section's table lists `kind: operational | structural` and `severity: low | medium | high | critical` for each FailureMode. The foundation FailureMode JSON Schema:

- `kind` enum: `timeout, dependency-unavailable, invalid-input, policy-violation, sanctions-hit, business-logic-error, infrastructure-failure, capacity-exceeded, authorisation-denied, other`
- No `severity` field exists (the schema has `expected_frequency` with enum `{rare, occasional, frequent}` instead)

**Quoted text** (WP Contract):
> | 2 | workflow-yaml-fails-to-parse | structural | abort | critical | CH-01KSYZ regression (PR #130's silent skip) |

**Quoted text** (schema):
```json
"kind": {"enum": ["timeout", "dependency-unavailable", "invalid-input", "policy-violation", "sanctions-hit", "business-logic-error", "infrastructure-failure", "capacity-exceeded", "authorisation-denied", "other"]}
```

**Why it matters:** The schema is canonical (per WP DoD: "All 8 validate against brain FailureMode schema") so the implementation MUST use schema-valid enum values. The WP Contract table is informal motivation, not normative. The implementation correctly used schema-valid `kind` values (e.g., `invalid-input` for YAML parse failure, `policy-violation` for loop-guard, `authorisation-denied` for GH-token, `capacity-exceeded` for token-budget, `business-logic-error` for the rest) and dropped `severity` in favour of `expected_frequency`.

**Recommendation:** No fix needed in this WP — the implementation is correct against the canonical schema and the drift is documented in (a) the journal Step 1.5 approach summary, and (b) the failuremodes.jsonld `_about` field. A follow-up editorial pass on the WP-004 source markdown could reconcile the Contract table to schema vocabulary, but that's documentation hygiene against a now-shipped artifact, not a code change.

**Draft delta:** None (recommendation is editorial, not a code fix).

**Lens:** quality

### Findings in the Neighbours

None. The neighbour ring would include consumers of `failuremodes.jsonld`, but all are future WPs (WP-002 Steps, WP-007 drift detector, WP-009 annotations) that are not yet implemented — there's no existing code to expose hidden gaps.

### Watch List

- The Crockford-base32 tenant ULID (`6XBZ93FSHN5TRX8MCS5R66FNCM`) used for `for_domain` is the deterministic SHA-derived value for `'tenant-name:sulis-plugins-marketplace'`. Other release-train WPs (WP-001 Workflow, WP-003 Triggers, WP-005 Projects, WP-006 Tools) MUST reuse the same ULID so the canonical instances cross-reference correctly. The reproduction recipe is documented in failuremodes.jsonld's `_about` field. **Recommendation for the SEA / orchestrator:** add a small constant module or a doc-block somewhere central (perhaps `plugins/sulis/instances/release-train/_TENANT_ULID.md`) so future WP authors don't re-derive it independently. Not in this WP's scope.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this project
- **Pattern suggesting full audit:** no — single-instance contract WP, no cross-cutting concerns

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uv run pytest`, `python3 -m compileall`, `python3 -c json.load`, `sulis-route check`. All exit 0. Coverage gap: none — Python-only diff with no TS/Go/Rust signals.
- [⚠] **CR-02 Parallel dispatch carve-out used.** Diff is 487 lines (>200 threshold) so parallel dispatch would normally be required. Single-reader pass justified by data-only content (133 vendored schema lines + 173 JSON-LD data lines + 175 test+journal lines, no production logic). The executor authored every line this session; the architecture, security, and quality lens reasoning is documented per-lens above with explicit checks-run lists.
- [✓] **CR-03 Full-file reads.** All 4 files read end-to-end. The schema (133 lines), the JSON-LD (173 lines), the test (175 lines), and the journal (~50 lines) were each authored this session and re-inspected post-write.
- [✓] **CR-04 Evidence discipline.** Q-01 cites file path, quoted text from WP and schema, recommendation.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; no files >50 lines unread; all 3 lenses produced explicit output; no PH-03 high finding).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + 5 checks-run lines. Security: 0 findings + primitives-checked list + scanners-unavailable list. Quality: 1 finding + jsx-scan N/A + dead-surface + contract-drift + test-coverage observation + CR-10 perf scan result.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low. PH-02 Size: low. PH-03 Safety: low. PH-04 Completeness: low. No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached origin/change/create-release-train-as-entities` (files staged in working tree, not yet committed; the staging is for diff visibility only — Step 7 will commit + push)
- **Neighbour expansion:** N/A — no existing consumers of failuremodes.jsonld (downstream WP-002 / WP-007 / WP-009 not yet implemented)
- **Neighbour cap:** 0 of 0 considered
- **Scanners run:** pytest, compileall, json.load (parse check), sulis-route
- **Scanners unavailable:** gitleaks, trivy, semgrep, mypy/pyright (none configured for this repo per CLAUDE.md "stdlib-only tooling" doctrine)
- **Lenses dispatched in parallel:** no (carve-out justified — see CR-02 row above)
