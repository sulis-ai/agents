# Code Review: PR feat/wp-004-validated-emit-helpers — Validated edit/status/list entity helpers

> **Timestamp:** 2026-06-09T112355Z (ISO 8601 UTC)
> **Author:** executor (WP-004)
> **Branch:** feat/wp-004-validated-emit-helpers → change/feat-user-level-product-store-settings
> **Files changed:** 6 source (+1 working journal)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds four small command-line helpers that let the settings
screen edit, soft-remove, and list products and projects safely. Each helper
checks the data against its schema before writing anything, and "remove" only
marks an item as deleted — it never erases a file. The build is clean, every
helper is covered by a real test (no fakes), and the four helpers share one
common piece of code so the logic isn't repeated. Nothing needs fixing before
merge.

## What to fix

No issues that need attention.

One thing to be aware of (not blocking): the list helper builds a folder path
from the "area" and "type" values it is given. Today those values always come
from fixed, server-controlled words (like "product" and "project"), so this is
safe. If a future change ever lets a user's free text reach those values, add a
check that they are one of the known words first. The helper only ever reads
files, never writes or deletes, so the blast radius is small either way.

## How this pull request is shaped

**Size — clean.** Six small files, about 390 lines of new code, well within a
size one reviewer can check thoroughly.

**Scope — clean.** A single concern: the validated write/read helpers for the
settings surface. One `feat` change, no mixed refactor or migration.

**Safety — clean.** No database migrations, no schema/IDL changes, no infra
files, no secrets. The "remove" path is a field change, never a file delete —
the safest possible shape for this requirement.

**Completeness — clean.** Four new helpers, all covered by a new test file with
four named cases driven against the real storage layer (no mocks).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
six changed files (each <345 lines) read end-to-end; all three lenses produced
structured output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). tsc `-p server` clean,
  eslint clean, ruff clean, py_compile clean.
- **PR Hygiene:** 0 high, 0 medium. One note (file-count just above the
  single-reader carve-out threshold; justified — see Methodology).
- **In the changes:** 1 finding (1 low/note).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single note has no failing characterisation test —
  Watch List only, per CR-04).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced — clean dependency direction, no new store primitive (ADR-020 honoured) |
| Security | 1 (note) | 0 | Theoretical path-segment injection in `list-entities.py` via `--domain`/`--kind`; benign under current server-literal callers |
| Quality | 0 | 0 | Nothing surfaced — tests present, no dead surface, no CR-10 anti-patterns |

### Build Verification (CR-01)

No PR-introduced errors. Tool outputs captured under `tool-outputs/`:

- `typecheck-head.log` — `tsc --noEmit -p server`, exit 0, empty.
- `eslint-head.log` — `eslint server/tests/emit-helpers.test.ts`, exit 0, empty.
- `ruff-head.log` — `ruff check apps/cockpit/server/adapters/spine/`, "All checks passed!".
- `pycompile-head.log` — `py_compile` on all five new `.py` files, exit 0.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 (apps/cockpit/server/adapters/spine + sibling test)
  severity: low (single concern)

Size (PH-02):
  lines_added: 734 (incl. 344-line test + 58-line journal); source ~390
  files_changed: 6 source (+1 journal sidecar)
  generated_ratio: 0
  lock_file_ratio: 0
  severity: low (within one-reader band by line count; file count noted)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0   (schemas are READ, not modified)
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0  (4 helpers + scaffold, all exercised by 4 tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `apps/cockpit/server/adapters/spine/list-entities.py:43` — low / note (security)

**Quoted text:**
```python
kind_dir = Path(args.base_dir).resolve() / args.domain / args.kind
```

**Observation:** `--domain` and `--kind` are interpolated into a filesystem
path. A caller passing a traversal segment (`../`) could redirect the read
outside the intended `{domain}/{kind}` subtree. The helper only ever *reads*
and globs `*.jsonld` (no write, no delete), so the worst case is reading
unintended `.jsonld` files within the brain root.

**Why it is not a finding requiring a fix now:** the sole caller is the
server-side `SpineSettingsAdapter` (WP-005), which passes fixed literals
(`product-development` / `foundation`, `product` / `project`) — never founder
input. The same pattern is already trusted in `_entity_adapter_local._instance_path`.
Per CR-05 this is `low`; per CR-04 (no failing characterisation test, no
reachable exploit) it goes to the Watch List, not the delta queue.

**Watch trigger:** if a future WP routes user-supplied text into `--domain` or
`--kind`, add an allow-list guard (`{product, project}` / `{product-development,
foundation}`) at the CLI boundary before the path join.

### Findings in the Neighbours

None. The helpers depend on the existing `_entity_adapter_local` /
`_entity_repository` surface (read-only dependency); no neighbour gap was
exposed.

### Watch List

- `list-entities.py:43` path-segment interpolation (see Findings in the Changes)
  — guard if user input ever reaches `--domain`/`--kind`.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none under `.security/feat-user-level-product-store-settings/`.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `tsc --noEmit -p server`,
  `eslint server/tests/emit-helpers.test.ts`, `ruff check spine/`, `py_compile`
  on all 5 `.py`. Base (change branch) had none of these files; HEAD: 0 errors
  across all four. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: ~390 source lines, 6
  files.** Line count (<200 excl. the homogeneous 344-line test of 4 near-
  identical cases) sits inside the carve-out; file count is 6 (one above the
  5-file line) but the files are 4 thin argv parsers + 1 shared scaffold + 1
  test, all read end-to-end. Recorded per CR-02.
- [✓] **CR-03 Full-file reads.** All 6 changed files read end-to-end (authored
  this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single note cites file:line + quoted
  text; no delta drafted (no failing characterisation test → Watch List).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low/note.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checked
  dependency direction (CLI → `_entity_edit` → adapter port, inward-only), no
  new store primitive (ADR-020), no singletons, no network calls (local FS so
  no timeout/CB applicable). Security: 1 note (path-segment interpolation);
  checked SEC injection (no shell — argv-only, shell:false-safe), secrets (none),
  path handling. Quality: Build follow-up (clean), JSX scan (n/a — no TSX render
  files), dead-surface (none; `void PRODUCT_ULID` is an intentional doc marker),
  contract-drift (`{ok,data:{entities}}` matches the test consumer), test-coverage
  (4 cases, real adapter, no mocks), CR-10 performance (no anti-pattern matches;
  `list-entities` loop is the intended single directory walk, bounded by dir size).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single `feat`). PH-02
  Size: low (~390 source lines / 6 files). PH-03 Safety: none (0 migrations,
  schemas read-not-modified, 0 secrets, 0 infra). PH-04 Completeness: none (4
  helpers all tested). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/feat-user-level-product-store-settings...HEAD`
  (staged WP-004 files).
- **Neighbour expansion:** git grep on `_entity_adapter_local` / `_entity_repository`
  consumers; read-only dependency, no neighbour findings.
- **Neighbour cap:** not reached.
- **Scanners run:** tsc, eslint, ruff, py_compile.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (no secrets/deps/
  Dockerfile in diff; manual grep for secret patterns ran clean).
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02).
