# Code Review: WP-002 — Author 15 Step instances (release-train workflow)

> **Timestamp:** 2026-06-01T112503Z (ISO 8601 UTC)
> **Branch:** feat/wp-002-author-steps-instance -> change/create-release-train-as-entities
> **Files changed:** 3 (875 lines added; 0 removed)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request looks good. It authors the 15 Step instances for the
release-train workflow as canonical JSON-LD data, vendors the upstream
schema that validates them, and adds a comprehensive test suite that
checks every cross-reference resolves correctly. There are no build
errors, no resilience or security concerns, and the tests cover the
contract surface end-to-end.

The 875-line diff is large in raw count but data-heavy by nature: 130
lines are a verbatim copy of the upstream schema, 389 lines are the 15
near-identical canonical entity records (about 26 lines each), and 356
lines are the test scaffolding that validates them. There is no logic
surface to review.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean given the content.** 875 lines across 3 files is on the
larger side, but the content is canonical data plus a vendored schema
plus tests. There is no behavioural code mixed in. The natural way to
read this PR is by file, not by line, and each file has a single
purpose.

**Scope — clean.** One area (`plugins/sulis/`), one Conventional Commit
type expected (`feat(release-train)`). The work matches the WP Contract
exactly.

**Safety — clean.** No migrations, no schema/IDL changes that affect
producers vs. consumers (the vendored schema is new and read by tests
only at this point), no infrastructure files, no secret-pattern hits.

**Completeness — clean.** Every new data file is accompanied by a test
file that proves the data shape. The vendored schema is consumed by
those tests. Nothing is added without verification.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens
> IDs) for engineers and for downstream agents. The author tier above
> contains everything the PR author needs to act.

### Verdict

`PASS` per CR-06. No critical/high findings in diff; Build Verification
empty; all changed files >50 lines read end-to-end; all three lenses
produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high; size auto-downgraded from medium → low based on
  PH-02 justified-size carve-out (data + schema + tests, no logic)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (no neighbour expansion: data file +
  tests have no callers/callees outside the diff)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | (nothing surfaced) |
| Security | 0 | 0 | (nothing surfaced) |
| Quality | 0 | 0 | (nothing surfaced) |

### Build Verification (CR-01)

Mechanical baseline (BASE = `change/create-release-train-as-entities`,
HEAD = `feat/wp-002-author-steps-instance`):

- `ruff check tests/unit/test_steps_instance_valid.py` -> `All checks passed!`
- `ruff format --check tests/unit/test_steps_instance_valid.py` -> `1 file already formatted`
- `pytest tests/unit/test_steps_instance_valid.py -v` -> `10 passed in 0.08s`
- `python3 -c "import json; json.load(open('steps.jsonld'))"` -> parses; 15 Steps

Full unit suite (`pytest tests/unit/` from `plugins/sulis/scripts/`): 1216
passed in 27.90s. No regressions introduced.

Raw outputs at `tool-outputs/`:
- `ruff-check.log`
- `ruff-format.log`
- `pytest-head.log`
- `jsonld-parse.log`
- `diff-stat.txt`
- `diff-shortstat.txt`

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (plugins/sulis/)
  severity: clean

Size (PH-02):
  lines_added: 875, lines_removed: 0, total: 875
  files_changed: 3
  generated_ratio: 0.15 (vendored schema, copied verbatim)
  lock_file_ratio: 0
  severity: low (justified)
  justification:
    - 130 lines: vendored step.schema.json (verbatim from upstream
      sulis-brain v0.6.0 foundation; no review surface)
    - 389 lines: steps.jsonld with 15 canonical Step entities,
      ~26 lines each; deterministic structure per the WP Contract +
      brain Step v1.2.0 schema
    - 356 lines: test_steps_instance_valid.py with 10 tests +
      4 module-scoped fixtures + 5 canonical constants
    - 0 lines of imperative/behavioural code

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0 (schema vendoring is additive consumer-side; the
    producer is upstream sulis-brain, unchanged here)
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0
  new_tests: 1 (test_steps_instance_valid.py)
  api_change_without_schema: false
  severity: clean
```

PH-03 high → CR-06 auto-downgrade: did NOT fire (no PH-03 high).

### Findings in the Changes

None.

#### Architecture lens

Nothing surfaced. Checks run:

- dependency-direction: data file (steps.jsonld), vendored schema
  (step.schema.json), and a test file. No domain↔infrastructure import
  boundary to evaluate; data + schema files have no imports.
- timeout / circuit-breaker / retry / observability / secrets: not
  applicable — no network, no subprocess, no external calls anywhere
  in the diff. Tests read three local files via `Path.open()` once at
  module scope (pytest fixture cached).
- contract-test: present and load-bearing — the test file IS the
  contract test for steps.jsonld; each of the 10 tests checks a
  specific contract invariant (parse + cardinality + brain-schema
  conformance + cross-WP cross-reference resolution + Blue invariants
  + canonical ULID literals + NFR-010 token budget + MUC-007 founder
  gate).

#### Security lens

Nothing surfaced. Primitives checked:

- SEC-01..07 (authn, authz, injection, validation, XSS, SSRF): no
  applicable surface (no I/O boundary, no user input, no auth).
- SC-01..04 (dependency CVEs): no new runtime dependencies; only
  vendored data + schema files.
- DAT-03 (logging PII): no logging calls.
- Secret-pattern scan: tenant ULID `6XBZ93FSHN5TRX8MCS5R66FNCM` is a
  deterministic hash output per the failuremodes.jsonld _about
  derivation recipe (SHA256('tenant-name:sulis-plugins-marketplace')
  mapped to Crockford base32); it is canonical cross-WP and not a
  secret. No API keys, tokens, or credentials in the diff.
- Scanners: not run (no executable code surface; standard mode applied;
  coverage gap noted in Methodology).

#### Quality lens (all 7 outputs)

1. **Build verification follow-up:** empty (mechanical baseline clean).
2. **JSX scan:** N/A (no TSX/JSX/Vue/Svelte files).
3. **Dead surface:** none. Test file: 10 test functions + 4 fixtures +
   5 module constants — all referenced. steps.jsonld envelope keys
   (`@context`, `@id`, `@type`, `for_tenant`, `for_workflow`, `_about`,
   `captured_on`, `steps`) all are JSON-LD-standard or checked by tests.
4. **Contract drift:** none. Brain Step v1.2.0 schema declares
   `unevaluatedProperties: false` — drift between WP Contract and
   schema would be caught by `test_each_step_passes_brain_schema`.
   Cross-WP refs (tool_ref → WP-006 tools.jsonld; handles_failures →
   WP-004 failuremodes.jsonld) are dangling-ref-tested.
5. **Test coverage:** appropriate for kind=contract. 10 tests cover
   parse + cardinality + per-Step schema validation + 2 cross-ref
   resolution checks + 2 Blue invariants + canonical ULID literals +
   Step-5 NFR-010 token budget + Step-8 MUC-007 human gate + IO
   artifact uniqueness. No source-only files; every contract surface
   has a test.
6. **Style / readability:** Step IDs use mnemonic 26-char Crockford
   base32 forms (e.g., `dna:step:01KT0RTRA1ST04CMPNXTVER000`) with
   I→1, L→1, O→0, U→V substitutions where mnemonic letters collided
   with Crockford-excluded characters. Pattern is documented in the
   journal's self-heal attempt log. Consistent with peer entity files
   (triggers.jsonld, failuremodes.jsonld). _about field is verbose but
   informational (parallels peer instances).
7. **Performance procedural checks (CR-10):** no anti-pattern matches.
   - N+1 DB/RPC/filesystem: none (no I/O).
   - O(N²) over same collection: none (tests iterate 15-element list
     once per test, total 10 × 15 = 150 iterations across the suite —
     bounded by canonical cardinality, fixture-cached).
   - Synchronous waterfall: none.
   - Unbounded materialisation: none (test fixtures load 3 fixed-size
     files at module scope).
   - Repeated invariant in loop: none.

### Findings in the Neighbours

None. No neighbour expansion warranted: data file + tests have no
callers/callees outside the diff. The drift detector (WP-007) will be
the canonical consumer once it ships; it lives downstream of this WP
and reads, not calls.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none surfaced.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`,
  `ruff format --check`, `pytest`, `json.load` parse-check on jsonld.
  Base (before changes): no test file existed for this contract.
  Head: all four checks clean. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch:** carve-out applied (above 200-line /
  5-file threshold strictly, but the diff is 130 lines of vendored
  schema + 389 lines of homogeneous canonical data + 356 lines of
  test scaffolding — no behavioural code; size-derived parallelism
  doesn't add value here). Single-reader pass justified by content
  shape, not size alone. Sequential lens-by-lens read end-to-end.
- [✓] **CR-03 Full-file reads.** All 3 changed files read
  end-to-end: step.schema.json (130L), steps.jsonld (389L),
  test_steps_instance_valid.py (356L). No sampling.
- [✓] **CR-04 Evidence discipline.** All findings would cite file:line
  + quoted text — but there are no findings to cite.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium,
  0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade
  triggers fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks
  enumerated above). Security: nothing surfaced (primitives + scanner
  coverage gap enumerated). Quality: all 7 outputs produced; none
  flagged findings.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size:
  low (justified-size carve-out per the data-heavy nature of the
  diff). PH-03 Safety: clean. PH-04 Completeness: clean. PH-03 high
  did not fire; no CR-06 auto-downgrade from hygiene.

#### Run details

- **Diff source:** `git diff --cached` (staged); base
  `change/create-release-train-as-entities`@`3e0336f3` (pre-Step-7,
  files not yet committed at review time).
- **Neighbour expansion:** none warranted (data + tests, no callers).
- **Neighbour cap:** 20 file cap not reached.
- **Scanners run:** none (no executable code in diff; standard mode).
- **Scanners unavailable:** Gitleaks, Semgrep, Trivy not invoked; no
  applicable surface.
- **Lenses dispatched in parallel:** no — sequential in-agent reads
  per the CR-02 content-shape rationale above.
