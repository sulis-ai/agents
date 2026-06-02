# Code Review: feat/wp-006-rt-wiring — release-train drift-check preflight + dev-sha-at-open pin writer

> **Timestamp:** 2026-06-02T075904Z (ISO 8601 UTC)
> **Author:** WP-006 executor
> **Branch:** feat/wp-006-rt-wiring → change/extend-auto-back-merge-on-release
> **Files changed:** 3 (2 functional + 1 journal sidecar)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds two small, well-scoped safety steps to the release-train instructions: a check at the start that refuses to run if production has moved ahead of the work branch, and a step just before opening the release pull request that records which commit the release was cut against. Both pieces lean on existing, already-shipped building blocks rather than re-inventing anything, and the change ships with its own tests. There are no build errors and nothing to fix before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 71 lines of real change (the rest is the standard work-tracking file). One file of instructions, one file of tests. Easy to review thoroughly.

**Scope — clean.** A single, focused piece of work: wire two new steps into one set of instructions. Nothing unrelated bundled in.

**Safety — clean.** No database changes, no infrastructure changes, no secrets. The one value the change records — a commit identifier — is already public information.

**Completeness — clean.** The change ships with tests that prove both new steps are present, in the right order, and that the recorded-commit format matches exactly what the automated release step on the other side expects to read back. That cross-check is the most valuable test here: it guarantees the two halves of the release machinery agree on a shared format down to the character.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high findings in the diff; Build Verification empty; both functional files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (delegates to drift_check.sh; cites ADR-005/006 — no copy-paste, no reinvention) |
| Security | 0 | 0 | — (no secrets; pinned value is a public SHA from `git rev-parse`) |
| Quality | 0 | 0 | — (tests included; parity test enforces producer/consumer seam) |

### Build Verification (CR-01)

No mechanical-floor errors. The diff is methodology prose (SKILL.md) plus one structural Python test.

- `python3 -m py_compile tests/unit/test_release_train_drift_and_pin.py` → exit 0
- `uv run pytest tests/unit/test_release_train_drift_and_pin.py -q` → 9 passed
- `bash -n` over both prose shell snippets (the drift guard + the pin-write) → both valid

Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single WP)
  module_fan_out: 1 (plugins/sulis)            → clean
  severity: none

Size (PH-02):
  lines_added: 401, lines_removed: 7
  functional_lines: 71 (SKILL.md +64 / test +283 / sidecar +54)
  files_changed: 3 (2 functional + 1 journal sidecar)
  severity: none

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the new file IS a test; SKILL.md change is covered by it)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

#### Architecture lens — nothing surfaced

Checks run: dependency-direction (no new imports; the SKILL.md is prose), single-source-of-truth (the Step 1 prose DELEGATES to `plugins/sulis/scripts/drift_check.sh` and does NOT inline `git merge-base --is-ancestor` — ADR-003 honoured; verified by the test `test_step1_invokes_drift_check_helper`), canonical-format reuse (the pin wrapper is cited from ADR-005/ADR-006/TDD §3, not reinvented — the parity test asserts byte-equivalence against the canonical reader regex `<!-- dev-sha-at-open: [a-f0-9]{40} -->`), no new singletons/circular-imports/secrets. The repo-root resolution in the test (`Path(__file__).resolve().parents[5]`) matches the established idiom in `test_branch_ci_has_drift_check.py`.

#### Security lens — nothing surfaced

Primitives checked: SEC-02 (injection — the only external input is `git rev-parse origin/dev`, a 40-hex SHA constrained by the reader regex; no shell-injection surface in the documented snippet), SEC-06 (secrets exposure — none; the pinned value is a public commit identifier, and ADR-005 places it in an HTML comment that does not render in the GitHub UI), DAT-03 (no new logging of sensitive data). No scanners required for a prose+test diff with zero secret-pattern hits.

#### Quality lens — all outputs

1. **Build Verification follow-up:** none (CR-01 empty).
2. **JSX/template identifier scan:** N/A (no TSX/JSX/Vue/Svelte files).
3. **Dead-surface:** none. The test's single module-level constant `CANONICAL_PIN_READ_REGEX` is consumed by two test functions.
4. **Contract-drift:** none — the parity test (`test_pin_format_round_trips_through_canonical_reader_regex` + `test_skill_pin_literal_matches_canonical_reader_regex`) is the explicit producer/consumer seam guard between WP-006's writer and WP-003's reader (the latter cited from the canonical source, ADR-006, since WP-003's workflow YAML is still in flight).
5. **Test-coverage observation:** the diff IS test + prose. The new behaviour (drift preflight + pin writer) is covered by 6 behavioural assertions + 3 guards/parity checks = 9 tests, all passing.
6. **Style/readability:** clean. Docstrings on every test; intent comments cite the canonical source by ID.
7. **Performance procedural checks (CR-10):** no anti-pattern matches. The two list-comprehensions in the ordering test iterate an already-materialised, bounded list of regex match offsets (in-memory; no IO, no DB, no N+1).

**Quality lens correctness self-check (recorded):** the ordering assertion `test_step5_pin_write_precedes_pr_create` was verified to target the REAL open call (`gh pr create --body-file $DRAFT_FLAG` at body-offset 16045), not the dry-run example (`gh pr create` at offset 14220, which is before the pin-write at 14983). The assertion `create_after_pin` correctly requires a create occurrence after the pin-write — sound.

### Findings in the Neighbours

None. The neighbour ring is `drift_check.sh` (WP-001, shipped — the SKILL.md calls it; the helper's exit 0/1 contract matches the prose's `if ! bash ...; then exit 1` guard) and the canonical pin-read regex owned by ADR-006 / WP-003's reusable workflow (the parity test binds to it). Both are consistent with the change; no pre-existing gaps exposed.

### Watch List

- **WP-003 reader parity at integration time.** This review asserts the writer format against the *canonical source* (ADR-006 / TDD §3 regex), because WP-003's reusable-workflow pin-read step is still `in_progress` and not yet in the YAML. When WP-003 lands, WP-009's `test_pin_read_parity.sh` / `test_canonical_strings_parity.sh` is the cross-WP seam test that confirms the shipped reader regex equals the canonical one this WP wrote against. No action for WP-006 — flagged for the WP-009 integration gate.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** py_compile + pytest (9 passed) on the new test; `bash -n` on both prose snippets. Base had no such file; Head clean. Coverage gap: no TS/Go/Rust signals (prose + Python diff) — N/A.
- [✓] **CR-02 Single-reader pass justified by diff size: 71 functional lines, 2 functional files (≤200 / ≤5).**
- [✓] **CR-03 Full-file reads.** Both functional files (SKILL.md region, the 283-line test) read end-to-end. Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings: none; lens outputs cite the specific assertions/offsets verified.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks listed). Security: nothing surfaced (primitives listed). Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (71 functional lines / 2 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (tests included). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff origin/change/extend-auto-back-merge-on-release` (staged+working, pre-commit local diff)
- **Neighbour expansion:** git grep + manual (drift_check.sh, ADR-006 canonical regex)
- **Neighbour cap:** 2 of 2 considered, 0 excluded
- **Scanners run:** none required (prose+test diff, 0 secret-pattern hits)
- **Lenses dispatched:** single-reader (CR-02 carve-out justified)
