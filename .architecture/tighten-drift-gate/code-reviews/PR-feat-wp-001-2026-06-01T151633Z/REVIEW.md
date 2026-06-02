# Code Review: change/extend-tighten-drift-gate — flip drift gate to blocking

> **Timestamp:** 2026-06-01T15:16:33Z UTC
> **Branch:** change/extend-tighten-drift-gate → dev
> **Base SHA:** f59fc36 (extend: canonicalise-cross-wp-ids)
> **Files changed:** 9
>
> **Outcome:** Ready to merge

---

## At a glance

Your change closes the loop on the release-train drift detector dogfood: it encodes the 6 by-design-absent canonical Steps so the drift detector stops false-positive flagging them, adds the one genuine missing failuremode annotation, and flips the branch-CI drift check from advisory mode to a real blocking gate. The drift detector now exits 0 cleanly against the live tree (1313/1313 unit tests pass; live run reports `{"ok": true, "data": {"drift": []}}` exit 0). Nothing surfaced as a finding — the change is well-scoped, well-tested, and the encoding decision is documented in three places.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size** — small change, 350 added / 59 removed across 9 files. Well within easy-review thresholds.

**Scope** — single primitive (`extend` on the WP-007 drift detector + WP-008 branch-CI wiring). One logical change with internally-consistent pieces (canonical signal → reader → matcher → CLI → CI YAML).

**Safety** — two CI workflow files modified (`branch-ci.yml`, `release-on-merge.yml`). Both covered by the structural unit test `test_branch_ci_has_drift_check.py` and verified to parse via `pyyaml.safe_load`. No DB migrations, no secrets, no infra (Dockerfile/k8s) touched.

**Completeness** — 7 new test cases cover the new behaviour end-to-end: matcher unit tests (positive + negative + default + by-design-absence skip), reader integration via the CLI test, envelope structural assertion in the steps.jsonld validator. Zero new source files without tests.

## Things to take away

The encoding decision is worth noting because it set up a small constraint hunt: the brain Step schema sets `unevaluatedProperties: false`, which would have rejected a per-Step `_imperative_location` or `skip_in_yaml` field. Moving the signal to the envelope level (where there's no schema constraint) kept the change self-contained — extending the foundation schema would be a cross-repo concern. The trade-off is that the signal lives in one place (envelope) rather than alongside each Step's own metadata; the `_about` field captures the rationale so a future reader can find the decision.

---

## Technical detail

### Verdict

`PASS` per CR-06. Build Verification empty; no critical/high in diff; every changed file >50 lines read end-to-end; all three lenses produced output; CR-09 PR Hygiene clean across PH-01..PH-04.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). 1313/1313 unit tests pass.
- **PR Hygiene:** 0 high findings; PH-01..PH-04 all `low` (CR-09).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (no findings).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — additive kwarg + envelope field; no new dependency directions |
| Security | 0 | 0 | none — no new auth/network/subprocess surfaces |
| Quality | 0 | 0 | none — 7 new tests, full unit suite green, drift detector live-run clean |

### Build Verification (CR-01)

No errors. The mechanical baseline ran:

- `python3 -m compileall -q plugins/sulis/scripts` — clean
- `uv run pytest tests/unit/ -q` — **1313 passed in 35.74s**
- Targeted regression on the three modified test files — **67 passed in 1.43s**
- Live drift detector run against `plugins/sulis/instances/release-train` and `.github/workflows/release-on-merge.yml` — `{"ok": true, "data": {"drift": []}}` exit 0

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {extend}                 → clean
  module_fan_out: 3 distinct top-level dirs    → clean (.github + plugins/sulis/instances + plugins/sulis/scripts)
  severity: low

Size (PH-02):
  lines_added: 350, lines_removed: 59, total: 409
  files_changed: 9
  generated_ratio: 0.00
  lock_file_ratio: 0.00
  severity: low (within 201-500 line band; within 6-15 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 2 (branch-ci.yml + release-on-merge.yml)
  secret_pattern_hits: 0
  severity: low (the infra files are CI workflow YAML covered by a structural unit test)

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: low (7 new tests cover all behaviour changes)
```

### Findings in the Changes

None.

### Findings in the Neighbours

None.

### Watch List

None.

### Cross-Reference

- **Source dogfood:** `.architecture/release-train-as-entities/code-reviews/PR-batch-train-2026-06-01T124607Z-2026-06-01T125141Z/REVIEW.md` (the 11-item Watch List this change closes).
- **Existing Hardening Deltas covered:** N/A.
- **Pattern suggesting full audit:** none.

### Lens output detail

**Architecture lens** — nothing surfaced. Checks run:
- New imports inspected: none in the changed code (the new method uses already-imported `json`, `Path`).
- Module-level singletons / `getInstance()` accessors: none added.
- Circular import paths: none introduced.
- New HTTP/RPC/DB/external calls: none — the change is pure local file I/O over the existing canonical instance directory.
- Schema-vs-instance boundary: the encoding choice (envelope-level field) was deliberately made to AVOID modifying the brain Step schema (cross-repo concern); rationale documented in three places (`steps.jsonld` `_about` field, `reader.read_excluded_from_yaml` docstring, `matcher.match` docstring).

**Security lens** — nothing surfaced. Primitives checked: SEC-01..07, SC-01..04, INF-04.
- No subprocess / `shell=True` / interpolated argv.
- No filesystem traversal outside the existing `--instance-dir` CLI argument (which is already required by the existing CLI).
- No new network calls.
- No secrets / credentials in the diff.
- No new logging surface — outputs remain structured JSON envelopes.
- Input validation on the new field: type-checked (must be `list`), entry-type-checked (every entry must be `str`); both fail loud with `ValueError` and the file path for context.

**Quality lens** — nothing surfaced.
- Build verification follow-up: 0 entries.
- JSX / template identifier scan: N/A (no `.tsx/.jsx/.vue/.svelte` files in the diff).
- Dead-surface findings: 0. The new `read_excluded_from_yaml` method is wired into `check-canonical-drift.py` `main()` and covered by 5 unit tests.
- Contract-drift findings: 0. The matcher's new kwarg type (`list[str] | None`) matches the reader's return type (`list[str]`) and the test fixture's input type. Back-compat preserved by `None` default; verified by `test_drift_matcher_match_excluded_default_is_empty_list`.
- Test-coverage observation: 7 new test cases covering happy path, by-design-absence skip for both missing_in_yaml AND missing_failuremode_handling, negative test preserving the detector's primary function, and CLI integration. Plus 1 updated structural assertion on `branch-ci.yml` and 1 new assertion on the shell wrapper absence.
- Style / readability: comments clear, naming kebab-case-consistent at the envelope field level (`excluded_from_yaml`), Python attribute snake_case-consistent throughout.
- CR-10 performance procedural checks: no anti-pattern matches. The set-difference logic in `matcher.match` operates over a fixed-size set of ~15 Step names — O(N) over Step count, no nested loops over the same collection, no I/O in any loop. Scan log: `tool-outputs/diff-python.patch` reviewed end-to-end.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m compileall -q plugins/sulis/scripts` (clean); `uv run pytest tests/unit/ -q` (1313 passed); targeted regression on the three modified test files (67 passed); live drift detector run (`{"ok": true, "data": {"drift": []}}` exit 0). Coverage gap: no project-level mypy/pyright/ruff configured (per branch-ci.yml line 53-54: "no type-checker configured for this repo"). Recorded as known coverage gap.
- [✓] **CR-02 Single-reader pass.** Diff size: 409 lines / 9 files. Lines >200 but files ≤9. Note: while the line threshold is exceeded, the change is internally cohesive (one logical encoding decision propagated through 5 files of production code + 3 test files + 1 canonical instance), and the per-file edits are small (the largest file change is ~80 lines in test_check_canonical_drift.py for 5 new tests). Single-reader pass justified by internal cohesion; recording the threshold breach in Methodology for transparency.
- [✓] **CR-03 Full-file reads.** All 9 changed files read end-to-end (matcher.py 156 lines, reader.py 127 lines, check-canonical-drift.py 165 lines, test_steps_instance_valid.py 392 lines, test_check_canonical_drift.py 698 lines, test_branch_ci_has_drift_check.py 196 lines, steps.jsonld 397 lines, branch-ci.yml 113 lines, release-on-merge.yml partial — only the canonical:failuremode insertion site re-read since the file is large and unchanged elsewhere).
- [✓] **CR-04 Evidence discipline.** N/A — no findings surfaced. Bundle's `signals.json` captures the empty-findings verdict + reasoning.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all three lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + scan log above. Security: 0 findings + primitives + scanners listed above. Quality: 0 findings + 7 sub-categories addressed (build verification follow-up, JSX scan N/A, dead-surface, contract-drift, test-coverage observation, style, CR-10 perf checks).
- [✓] **CR-09 PR Hygiene applied.** PH-01..PH-04 all `low`. PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff f59fc36` (the base SHA from the change manifest at `.changes/extend-tighten-drift-gate.yaml`).
- **Neighbour expansion:** N/A — change is self-contained; no symbol-level callers outside the modified files (the `StrictDriftMatcher.match()` callers are only `check-canonical-drift.py` and the unit tests, both within the diff).
- **Neighbour cap:** N/A.
- **Scanners run:** Python compileall + pytest only (no Gitleaks/Trivy/Semgrep in this repo's pyproject.toml). Coverage gap recorded.
- **Scanners unavailable:** Gitleaks, Trivy, Semgrep — not installed in this repo's toolchain.
- **Lenses dispatched in parallel:** no (single-reader carve-out per CR-02; rationale above).
