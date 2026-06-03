# Code Review: feat/wp-002-compose-requirement-from-idea — Add compose_requirement_from_idea pure transform

> **Timestamp:** 2026-06-03T070749Z (ISO 8601 UTC)
> **Author:** executor (WP-002)
> **Branch:** feat/wp-002-compose-requirement-from-idea → change/create-brain-backlog-and-traversal
> **Files changed:** 2 (1 source, 1 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one new helper that turns a captured idea into a draft requirement, and refuses to do so unless the idea is properly rooted in a real opportunity. The code is clean, well-tested (12 new tests), and reuses the existing building blocks rather than re-inventing them. There are no build errors and nothing that needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: 96 new lines in one file plus a focused test file. One concern, one commit-type (`feat`), no migrations, no schema changes, no secrets, tests included alongside the new code. This is exactly the shape a change like this should take.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the one changed source file >50 lines read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`ruff check` clean on both touched files; `py_compile` OK. See `tool-outputs/ruff-check.log` and `tool-outputs/py-compile.log`. Base had no errors on these files (the source file is pre-existing and clean; the test file is new). No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (plugins/sulis/scripts)  → clean
  severity: none

Size (PH-02):
  lines_added: ~290 (96 source + 194 test), lines_removed: 0
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (well within carve-out: <200 source lines, ≤5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0   (consumes the pre-existing vendored requirement schema; does not modify it)
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0   (the new fn ships with 12 tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

**Architecture lens (WP_BACKEND_STANDARD rubric): nothing surfaced.** Checks run:
- WPB-01 (hexagonal boundary): `compose_requirement_from_idea` is a pure domain transform — no imports of HTTP/DB/SDK/framework; no I/O. Clean.
- WPB-03/08 (in-memory-first / TDD): pure fn unit-tested directly without a store, mirroring the existing `compose_*` tests; RGB cycle recorded in the WP journal.
- WPB-12 (clean code / boring-code): explicit kwargs, no metaprogramming, no module-level mutable state, descriptive names; the new module-level `_OPPORTUNITY_REF_RE` is an immutable `Final` constant (consistent with the file's existing `_FR_HEADER_RE` etc.).
- EP-03 (reuse-first): `_deterministic_ulid_from` and `_flatten` reused unchanged; distinct id namespace (`requirement-from-idea:`) prevents collision with the from-SRD path.
- Contract adherence: `compose_requirements_from_srd` is untouched (verified by diff + regression test `test_does_not_touch_from_srd_path`).

**Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no auth/access surface — pure transform), SC-01..04 (no new dependencies; `jsonschema` is test-only and pre-declared). No secrets, no injection vector, no network. The `_OPPORTUNITY_REF_RE` regex is fully anchored (`^...$`) over a fixed-length character class — no ReDoS exposure. The `ValueError` message interpolates `source!r` (the rejected input) — a developer-facing diagnostic, not a user-facing log; acceptable.

**Quality lens: nothing surfaced.**
1. Build Verification follow-up: no CR-01 findings to translate.
2. JSX/template scan: N/A (no TSX/JSX/Vue/Svelte files).
3. Dead surface: none — the new fn is exercised by tests and is a declared blocker dependency for WP-004.
4. Contract drift: none — output dict carries exactly the schema's required + optional keys; validates clean under `unevaluatedProperties:false` (independently verified).
5. Test coverage: 12 tests for the new behaviour, covering purity/determinism, verbatim source pass-through, the malformed-source rejection (7 malformed variants incl. `actor`, bad ULID, wrong length, non-Crockford char), schema validity, defaults, namespace distinctness, and from-SRD regression.
6. Style/readability: clear; docstring documents the load-bearing invariant and rationale (why, not what).
7. CR-10 performance: no anti-pattern matches — pure dict-builder, no loops, no I/O, no collection iteration.

### Findings in the Neighbours

None. The only neighbour is `compose_requirements_from_srd` (same module), which the change deliberately does not touch (Contract requirement), confirmed by the regression test.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `uv run ruff check` + `uv run python -m py_compile` on both touched files. Base: 0 errors. Head: 0 errors. Coverage gap: no mypy/pyright configured for this scripts package (stdlib-style modules); `py_compile` is the configured syntax/type floor and CI lints via py_compile, recorded as the baseline.
- [✓] **CR-02 Single-reader pass justified by diff size: ~290 lines (96 source), 2 files — within the ≤200-source-line / ≤5-file carve-out.**
- [✓] **CR-03 Full-file reads.** The one changed source file (`_requirement_emission.py`, 300 lines) read end-to-end; the new test file (194 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Zero findings; invariant/schema/reuse claims independently re-verified by executing the composer against the real vendored schema (logged in session).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture: 0 findings (WPB-01/03/08/12 + EP-03 checked). Security: nothing surfaced (SEC-01..07, SC-01..04). Quality: 0 findings + all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none ({feat}, 1 dir). PH-02 Size: none (~290 lines / 2 files). PH-03 Safety: none (0 migrations, 0 schemas modified, 0 secrets, 0 infra). PH-04 Completeness: none (new fn ships with tests). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/create-brain-backlog-and-traversal...HEAD` + untracked new test file
- **Neighbour expansion:** same-module symbol scan (`compose_requirements_from_srd`); cap not reached
- **Neighbour cap:** 1 of 1 considered, 0 excluded
- **Scanners run:** ruff, py_compile
- **Scanners unavailable:** gitleaks/trivy/semgrep not in this environment — no secrets/dep surface in a pure stdlib transform, so coverage gap is non-material
- **Lenses dispatched in parallel:** no (single-reader, justified by CR-02 carve-out)
