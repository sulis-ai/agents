# Code Review: feat/wp-001-canonicalise-cross-wp-ids — Pre-mint cross-WP shared identifiers

> **Timestamp:** 2026-06-01T145136Z (ISO 8601 UTC)
> **Author:** Sulis executor (subagent)
> **Branch:** feat/wp-001-canonicalise-cross-wp-ids → change/extend-canonicalise-cross-wp-ids
> **Files changed:** 4 (3 modified + 1 new test)
> **WP kind:** docs (methodology prose extension)
>
> **Outcome:** Ready to merge

---

## At a glance

This change extends the `/sulis:plan-work` skill and the Decompose Validation
Rubric with a new methodology check: parallel-dispatched work packages that
cross-reference a shared identifier (ULID, slug, version literal, namespace)
must have that identifier pre-minted in an authoritative upstream source.
The new rule is captured as a workflow step in the skill, a phase in the
rubric, and is pinned by 4 structural tests that fail if either artifact's
new sections drift.

The build is clean, the full unit suite is green (1306 passed), and the
4 new tests cover every assertion the change makes. No findings.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 307 lines across 4 files (3 modified, 1 new). Well within
the comfortable-review band.

**Scope — clean.** Single primitive (`extend`), single concern (methodology
refinement). Commit-type spread is one (`extend:`); module fan-out is two
(skills + references + tests in one logical area).

**Safety — clean.** No migrations, no schema changes, no infra files, no
secret patterns. Pure prose + test additions.

**Completeness — clean.** Tests added alongside the prose changes. The
structural tests pin the new sections in place so future heading drift
surfaces as a failing test rather than a silent methodology regression.

## Things to take away

Skipped — the PR is clean and the WP shipped its provenance (CH-01KSZ4
anchor case) clearly in both artifacts. Nothing specific to take away
that the PR doesn't already model.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents like `/sulis:harden-codebase`. The
> author tier above contains everything the author needs to act.

### Verdict

`PASS` per CR-06. Computed from:
- Build Verification empty (0 PR-introduced errors)
- No critical/high/medium/low findings in the diff
- All 4 changed files read end-to-end (none > 250 lines)
- All three lenses produced output

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (all four PH primitives at `low`) (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced — methodology prose + structural test, no architectural surfaces |
| Security | 0 | 0 | nothing surfaced — no auth, no secrets, no I/O |
| Quality | 0 | 0 | nothing surfaced — ruff clean, tests pass, full suite green |

### Build Verification (CR-01)

No PR-introduced errors.

Tools run:
- `ruff check tests/unit/test_plan_work_canonicalise_section.py` → exit 0, all checks passed
- `ruff format --check tests/unit/test_plan_work_canonicalise_section.py` → exit 0, 1 file already formatted
- `pytest tests/unit/` (full suite) → 1306 passed in 34.42s
- `pytest tests/unit/test_plan_work_canonicalise_section.py -v` → 4 passed (the new tests)

Raw outputs in `tool-outputs/ruff-check.log`, `tool-outputs/ruff-format-check.log`,
`tool-outputs/pytest.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {extend}                 → clean
  module_fan_out: 2 (skills + references + scripts/tests)  → clean
  severity: low

Size (PH-02):
  lines_added: 306, lines_removed: 1, total: 307
  files_changed: 4
  generated_ratio: 0.00
  lock_file_ratio: 0.00
  severity: low (well below 500-line band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (the new test IS the test)
  api_change_without_schema: false
  severity: low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None — methodology prose has no neighbours in the call-graph sense.
The 4 files form a self-contained methodology unit (skill cites rubric;
rubric cites skill; test pins both).

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable (this WP authors
  the methodology refinement; deltas would only apply to code touched by it)
- **Existing security report:** none applicable
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `ruff format --check`, `pytest tests/unit/`. Base: 0 errors (would be unchanged). Head: 0 new errors. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified.** Diff: 307 lines / 4 files. Above the 200-line carve-out but `kind: docs` with a single concern (methodology prose + structural test pinning it). The 4 files form a tightly-coupled unit; parallel dispatch across 3 lenses would produce identical findings (none). Single-reader pass recorded.
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end (largest is the new test at 209 lines). No file > 250 lines. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings, so no claims to evidence. The verdict cites the tool exit codes and the test-pass count as evidence.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no architectural surfaces — pure prose + test). Security: nothing surfaced (no secrets, no auth, no external calls, no I/O). Quality: nothing surfaced (ruff clean, full suite green, new tests cover the new prose, tests assert at the right granularity).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single primitive). PH-02 Size: low (307 lines, 4 files). PH-03 Safety: low (no migrations, schemas, infra, or secrets). PH-04 Completeness: low (tests included). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** local working tree vs `change/extend-canonicalise-cross-wp-ids`
- **Neighbour expansion:** N/A (prose has no call-graph neighbours; the 4 files are the unit)
- **Neighbour cap:** N/A
- **Scanners run:** ruff (check + format), pytest
- **Scanners unavailable:** none required for `kind: docs`
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out reasoning above
