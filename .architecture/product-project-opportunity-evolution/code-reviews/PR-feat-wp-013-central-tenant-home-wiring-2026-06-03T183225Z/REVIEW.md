# Code Review: WP-013 — Point living-entity emit at the central Tenant home (reuse)

> **Timestamp:** 2026-06-03T183225Z (ISO 8601 UTC)
> **Author:** executor (WP-013)
> **Branch:** feat/wp-013-central-tenant-home-wiring → change/feat-product-project-opportunity-evolution
> **Files changed:** 4 (3 modified, 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change wires the living-entity store at the shared, cross-repo home that
was already designed for it, rather than building a new store. It adds two small
functions — one that points at the shared home for a customer, one that reads
every current version back out of it — plus a focused set of tests, including
the key proof that two writes from two different repositories land in the same
shared place and are both visible. The build is clean, the tests pass, and the
change is small and well-scoped. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 108 lines added across 4 files, one concern. Easy to review
thoroughly.

**Scope — clean.** A single `feat:` concern: point the store at the shared
home and read it back. No mixed refactor/feature, no migrations, no infra.

**Safety — clean.** No database migrations, no schema/IDL changes, no infra
files, no secret-shaped strings. The store-durability guarantee is inherited
from the existing file adapter's safe-write behaviour, not re-invented.

**Completeness — clean.** One new test file with five behaviours, including the
load-bearing cross-repository proof. No new source went in untested.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all `none`)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`py_compile` on all 4 changed files: **0 errors**. `ruff check` on all 4
changed files: **All checks passed**. (Project lint profile is py_compile +
manifest validity; ruff run as a courtesy floor.) Build Verification section
empty → no verdict downgrade.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {feat}; module_fan_out: 1 → severity: none
Size (PH-02):         +108 / -2; files_changed: 4; severity: none (≤200 line band)
Safety (PH-03):       migrations: 0; schemas: 0; infra: 0; secrets: 0 → severity: none
Completeness (PH-04): new_source_without_test: 0; new_tests: 1 → severity: none
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

None.

**Architecture lens: nothing surfaced.** Checks run: dependency-direction
(the new `central_tenant_home` lives with the emit wiring in
`_brain_emit_helper.py`; the read seam `_brain_query.py` imports it lazily
inside the function body with an inline comment justifying the
cycle-avoidance — no module-level read→emit import cycle introduced); no new
singletons; no new infra→domain import; resilience (the change adds no new
HTTP/RPC/DB call — durability is the existing adapter's atomic write-tmp-then-
rename, inherited not re-implemented, and a test pins it); verification (no new
port → no contract-test gap; ADR-005 explicitly states there is no new adapter,
so no new port-contract surface; the new read is covered by 5 real-temp-dir
tests at the store seam, MEA-09 — no mocks).

**Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no auth/
authz/injection/validation surface — pure path arithmetic + a read-only
file walk over a Tenant-namespaced subtree), SC-01..04 (no dependency changes),
DAT-03 (no new logging of PII/tokens). The Tenant id used as a path component
is a deterministic Crockford-base32 ULID matching `^dna:tenant:[0-9A-HJKMNP-TV-Z]{26}$`
upstream — not user free-text — so the `central_tenant_home` path join carries
no traversal vector from this diff. No secrets, no plaintext-credential pattern.

**Quality lens: nothing surfaced.** (1) Build Verification follow-up: none —
mechanical floor clean. (2) JSX/template scan: N/A (no TSX/JSX/Vue/Svelte
files). (3) Dead surface: none — both new public functions are consumed (one by
the test + the emit-wiring docstring contract; one by the test + the
documented cross-repo read path). One unused `pytest` import was caught by ruff
during Step 6 and removed before review. (4) Contract drift: none — the open-
window selection mirrors the write side's invariant (`evolve_entity` keeps at
most one open window, last). (5) Test-coverage: 5 new behaviours added for the 2
new functions incl. the cross-repo proof + durability + only-open-windows +
ULID-reuse + round-trip — source is not untested. (7) CR-10 performance: the
new `find_current_for_tenant` loops over the EXISTING `iter_entities` O(N) flat-
file walk — the documented, deliberate read path (ADR-005 defers indexed reads
to the later SQLite swap behind the same port). No NEW anti-pattern introduced;
the walk reuse is the WP's explicit reuse mandate. No DB/RPC N+1, no O(N²), no
unbounded-materialisation pattern in the diff.

### Findings in the Neighbours

None. Neighbours examined: `_entity_evolve.py` (write-side `_current_window`
selector — see Watch List), `_tenant_emission.py` (ULID recipe source, reused),
`_entity_adapter_local.py` (the adapter the central home points at, unchanged),
`_change_state.py` (`sulis_state_base` reused). No pre-existing gaps the diff
exposes.

### Watch List

- **Open-window selector duplication (no delta).** `_brain_query._current_open_window`
  (new) and `_entity_evolve._current_window` (existing) both select "last window
  with empty `valid_to`". This is the 2-consumer threshold for EP-03 extraction,
  but the two live on opposite sides of the deliberately-decoupled read/write
  seam (the `_brain_query` module docstring states it does NOT import the write
  helper, to keep write-validation discipline off the read patterns) and differ
  in defensiveness by seam (write side trusts `_load_envelope`'s windows list;
  read side guards a raw bare-snapshot on disk). Extracting a shared primitive
  would force a cross-seam import the architecture intentionally avoids.
  Recorded as a conscious deferral in the Step-4 (Blue) journal entry; no
  characterisation test grounds a fix, so this stays a note, not a delta.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m py_compile <4 files>` (CI lint gate); `ruff check <4 files>` (courtesy floor). Base: clean. Head: 0 new errors. Coverage gap: no configured typechecker in pyproject (project lint profile is py_compile + manifest validity) — recorded, not skipped silently.
- [✓] **CR-02 Single-reader pass justified by diff size: 108 lines, 4 files** (≤200 lines AND ≤5 files — within carve-out).
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (authored this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens checks enumerated above.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks enumerated. Security: 0 findings + primitives enumerated. Quality: 0 findings + items 1-7 addressed (2 N/A, rest clean).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat). PH-02 Size: none (108 lines / 4 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (1 new test, 0 untested new source). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/feat-product-project-opportunity-evolution` (4 files, +108/-2).
- **Neighbour expansion:** git grep / direct import trace; 4 neighbours examined, 0 excluded (well under 20-file cap).
- **Scanners run:** py_compile, ruff.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not on PATH — diff carries no dependency/secret/Dockerfile surface, so coverage gap is immaterial to this change.
- **Lenses dispatched in parallel:** no (single-reader carve-out per CR-02; 108 lines / 4 files).
