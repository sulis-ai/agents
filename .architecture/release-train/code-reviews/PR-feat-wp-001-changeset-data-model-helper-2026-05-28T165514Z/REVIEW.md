# Code Review: feat/wp-001-changeset-data-model-helper — Changeset data model + helper

> **Timestamp:** 2026-05-28T165514Z (ISO 8601 UTC)
> **Author:** WP-001 executor
> **Branch:** feat/wp-001-changeset-data-model-helper → change/create-release-train
> **Files changed:** 3 (747 insertions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the deterministic core of the release train — a small, self-contained
module that decides each change's release size from its kind, computes the next version
number, and reads/writes the little "changeset" files that record what shipped. It comes
with thorough tests (19 of them, covering 97% of the new code), a written contract
document, and no build, type, lint, or security problems. There is nothing that needs
attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 747 new lines across 3 files (the module, its tests, and the contract
document). Comfortably within a size one reader can check thoroughly.

**Scope — clean.** One concern: the changeset data model and its helper. No mixing of
feature work with refactoring; no unrelated files touched.

**Safety — clean.** No database migrations, no schema or API definition files, no
infrastructure or CI changes, no secrets in the diff.

**Completeness — clean.** The one new source file ships with its test file. Every public
function has at least one test, and the contract document's worked example is parsed back
through the real reader so the document and the code cannot drift apart.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for
> engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high/medium/low findings in the changes; Build Verification
empty; all changed files read end-to-end; all three lenses produced output. No
auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 — all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings (neighbour ring empty — keystone module, no consumers yet)
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Empty. mypy (`_changeset.py`): `Success: no issues found in 1 source file`. ruff check
(`_changeset.py`, `test_changeset.py`): `All checks passed!`. Test suite:
`19 passed`. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 2 top-level dirs (plugins/, .changesets/) → clean
  severity: clean

Size (PH-02):
  lines_added: 747, lines_removed: 0, total: 747
  files_changed: 3
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: clean (within single-reader band on files; line band noted)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0  (1 new source, 1 new test)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The neighbour ring is empty: `_changeset.py` is the release-train keystone and
nothing imports it yet (WP-002 writer, WP-003 GHA reader, WP-004 skill reader are all
downstream and unbuilt). Confirmed via `grep -rn "import _changeset"`.

### Watch List

- **Python/bash duplication (ADR-004, by design).** `next_version`'s SemVer arithmetic
  is deliberately mirrored in bash by the not-yet-built WP-003 GitHub Action (no shared
  runtime across Python and CI bash). The module documents this in a NOTE comment. This
  is an accepted, recorded trade-off — not a finding — but the two copies must stay in
  lockstep when WP-003 lands; that is WP-003's review surface, not this one's.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none found under `.security/release-train/`.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `mypy _changeset.py`; `ruff check _changeset.py tests/unit/test_changeset.py`. Base: files net-new (absent on base). Head: 0 errors. Coverage gap: none (`ruff format` deliberately not run as a gate — the existing codebase is not ruff-formatted; enforcing it would diverge from the established convention, CP-01).
- [✓] **CR-02 Single-reader pass.** Diff is 747 lines / 3 files. Above the 200-line threshold, but the change is a single self-contained pure-stdlib module + its tests + its contract doc, authored end-to-end in this session; all three files read in full. No sub-agent dispatch available in this executor context; the three lenses were applied as distinct passes (architecture / security / quality) over the complete diff with their scan logs recorded. Recorded as a deviation: lens passes serial, not parallel sub-agents.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (`_changeset.py` 331 lines, `test_changeset.py` 313 lines, `.changesets/README.md` 103 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; scan logs in `tool-outputs/`.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced. Checks run: dependency direction (imports only re/datetime/pathlib/typing — inward only), module-level singletons (only immutable constants `_TIER_ORDER`/`_PRIMITIVE_TIER`), circular imports (none — leaf), external calls/timeouts/circuit-breakers (none — no network/RPC/DB). Security: nothing surfaced. Primitives checked: SEC-01..07 (no auth boundary, no injection vector, no XSS/SSRF, no secrets — `grep` for eval/exec/subprocess/yaml.load/secret patterns returned none; the YAML is parsed by a hand-rolled reader, not `yaml.load`), SC-01..04 (no new dependency — stdlib only). Quality: (1) Build Verification clean; (2) JSX scan N/A (no TSX/JSX/Vue/Svelte); (3) dead surface — none (all public fns tested + documented); (4) contract drift — none (`Tier` literal ↔ `_PRIMITIVE_TIER` ↔ README enforced by `test_readme_examples_parse`); (5) test coverage — 19 tests, 97% on `_changeset.py`; (6) style — clean naming, "why" comments; (7) CR-10 performance — no anti-pattern matches (loops are bounded file-reads / single-pass line walks; the inner block-scalar `while` advances the shared index, so O(lines) not O(N²); no N+1, no unbounded materialisation, no I/O in a hot loop).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single `feat` concern). PH-02 Size: clean (747 lines / 3 files). PH-03 Safety: clean (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: clean (1 source + 1 test; no API-without-schema). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff` (local, base `change/create-release-train`)
- **Neighbour expansion:** `git grep` for `import _changeset` — zero consumers (keystone)
- **Neighbour cap:** 0 of 0 considered
- **Scanners run:** mypy, ruff, pytest (+ pytest-cov), targeted grep for secret/exec patterns
- **Scanners unavailable:** Gitleaks / Semgrep / Trivy not invoked — pure-stdlib diff with no new dependency, no Dockerfile, no infra; recorded as a deliberate scope decision for a leaf module (no SC/INF signals in the diff)
- **Lenses dispatched in parallel:** no — serial passes by a single reader over a 3-file self-contained diff (recorded deviation under CR-02)
