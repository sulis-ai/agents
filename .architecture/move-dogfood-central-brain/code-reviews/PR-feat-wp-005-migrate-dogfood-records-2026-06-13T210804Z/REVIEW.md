# Code Review: WP-005 — Migrate dogfood records + roadmap label to central; git-rm

> **Timestamp:** 2026-06-13T210804Z (ISO 8601 UTC)
> **Author:** autonomous executor (Sulis)
> **Branch:** wp/create/wp-005-migrate-dogfood-records → change/move-dogfood-central-brain
> **Files changed:** 2 (+976 lines)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a one-shot tool that moves the project's own captured records
out of the repository and into the central knowledge store on the machine,
merges two near-duplicate "product" entries into one, and then reports which
files to remove from the repo. It is well-scoped: one new tool plus a thorough
set of tests, all run against throwaway temporary folders — nothing touches your
real data. There are no build errors, no security issues, and the tests cover
every required behaviour including the tricky "two products become one" rule and
the "run it twice and nothing changes" guarantee. One minor efficiency note for
awareness, but nothing to fix before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 976 lines across 2 files, one of which is the test file. A new
tool with its tests is exactly the right shape for one piece of work.

**Scope — clean.** Single concern: the migration tool. No mixed refactor +
feature.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets. Critically, the tool defaults to a preview ("dry-run") mode
and only changes anything when explicitly told to, and even then it works
against a temporary copy in tests — the real migration is run separately, with
you watching.

**Completeness — clean.** 4 new behaviours, 14 new tests. The source-to-test
ratio is strong.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, WPB-NN, lens
> IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high, 0 medium findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 critical, 0 high, 0 medium, 1 low (note)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single note is a Watch-List item, not a delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — hexagonal-lite, reuses existing ports |
| Security | 0 | 0 | none — no hardcoded ids/secrets; dest via brain_base_dir |
| Quality | 1 (low) | 0 | double file read per record (negligible for one-shot) |

### Build Verification (CR-01)

Mechanical baseline ran on HEAD (the diff is purely additive; BASE has neither
file, so every HEAD result is the delta):

- `ruff check migrate_dogfood_to_central.py tests/unit/test_migrate_dogfood.py`
  → `All checks passed!` (0 errors)
- `python3 -m py_compile <both files>` → OK (this is CI's actual lint gate per
  `.github/workflows/branch-ci.yml`: manifest JSON validity + py_compile)
- `mypy --follow-imports=silent migrate_dogfood_to_central.py` → `Success: no
  issues found`. (Repo has no type-checker in CI — stdlib-only tooling per
  plugin contract; mypy run here for diligence. The 16 errors mypy emits when
  it follows imports all live in the pre-existing `_wpxlib.py`, out of scope.)
- `uv run pytest tests/unit/test_migrate_dogfood.py -q` → 14 passed

Build Verification section empty → does not block PASS.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (plugins/)   → clean
  severity: none

Size (PH-02):
  lines_added: 976, lines_removed: 0, total: 976
  files_changed: 2 (1 source + 1 test)
  generated_ratio: 0.0
  severity: low (501-1000 line band, but 1 source file + its test)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (the source file ships with 14 tests)
  api_change_without_schema: false
  severity: none
```

PH-03 high did NOT fire → no CR-06 auto-downgrade.

### Findings in the Changes

#### Watch List (CR-04 incomplete — no failing test, no delta)

**`migrate_dogfood_to_central.py` — double JSON read per record — low (quality)**

`compute_migration_set` calls `_read_json(f)` to extract `entity_id` for each
entry, and then `_plan_records`/`migrate` re-read the same file via
`_read_json(e.src)`. Each migrated record is therefore parsed twice.

- **Why it is a note, not a finding:** this is a one-shot tool over ~124 records;
  the full suite (14 tests, all I/O) completes in <0.6s, so the second parse is
  immeasurable. Caching the parsed record on the `MigrationEntry` dataclass would
  trade a touch of memory + a wider value object for no observable gain on a tool
  that runs once. CR-10 pattern #8 (wasted roundtrips) technically matches but
  the context (one-shot, bounded N, sub-second) makes it benign per CR-10's
  "downgrade with justification after reading context" rule.
- **No delta:** there is no failing characterisation test to anchor a fix (the
  behaviour is correct; only micro-efficiency differs), so per CR-04 this stays
  on the Watch List.

### Findings in the Neighbours

None. The neighbour ring is the three helpers the tool imports —
`_brain_location.brain_base_dir`, `_brain_labels.roadmap_sidecar_path`,
`_change_emission.resolve_for_product` — all read end-to-end during
implementation recon. The tool consumes their public contracts unchanged; it
introduces no new gap in them.

### Architecture lens (WPB-01..12)

- **WPB-01/04 (hexagonal-lite, handler-as-source-of-truth):** pure core
  (`compute_migration_set`, `_repoint`, `_merge_product_metadata`,
  `_write_if_changed`) carries the logic; `migrate`/`build_manifest` are the two
  handlers; `main` is a thin CLI delegate that translates argv → handler call →
  JSON out. Business logic lives in exactly one place. ✓
- **EP-03 (reuse-first):** dest resolution reuses `brain_base_dir` (no
  hard-coded path); label path reuses `roadmap_sidecar_path`; the post-condition
  test asserts against the real `resolve_for_product`. No new port invented. ✓
- **Idempotency / reversibility (Armor):** `_write_if_changed` makes a second run
  a no-op; the manifest records source/dest/id/sha256 + edge rewrite as the
  single reversibility source; `reverse_record` restores the original edge. ✓
- **No new entity types/schemas** (ADR-002 / WP Blue constraint). ✓

Architecture lens: nothing surfaced. Checks run: dependency-direction (domain
imports no infra; lazy imports of `_brain_*` confined to the I/O edge),
secrets (none), observability (one-shot CLI prints a JSON summary — appropriate),
contract-test (post-condition asserted against real resolver).

### Security lens

Security lens: nothing surfaced. Primitives checked: SEC-02 (path handling —
all paths derived from `brain_base_dir` + relative record paths, no traversal
from user input beyond argparse ids), SEC-06 (secrets exposure — none; no
hardcoded ULIDs, the only `dna:product:` literal is argparse help text), DAT-03
(logging — JSON summary carries ids + paths, no secrets). No new dependencies
(stdlib-only) → SC-01..04 N/A. The tool's mutation is gated behind an explicit
`--execute` (default dry-run), reducing blast-radius by construction.

### Quality lens

1. **Build Verification follow-up:** none (baseline clean).
2. **JSX/template identifier scan:** N/A (no TSX/JSX/Vue/Svelte in diff).
3. **Dead-surface:** none. All 5 public functions (`compute_migration_set`,
   `build_manifest`, `migrate`, `reverse_record`, `main`) exercised by tests.
4. **Contract-drift:** none. The manifest dict shape is produced by one helper
   (`_edge_rewrite_row`) and consumed by `reverse_record`; the round-trip is
   asserted (`test_migration_reversible_by_record` checks restored sha256 ==
   recorded `src_sha256`).
5. **Test-coverage observation:** 14 tests, 97% line coverage on the new module
   (measured via ephemeral `pytest-cov`). Covers every DoD case incl. ADR-002
   single-product post-condition, idempotent copy + re-point, merge-not-collide,
   reversibility, library-not-migrated, git-ls-files (in a throwaway git repo).
6. **Style/readability:** clear names, small functions, docstrings explain
   "why". No TODO/FIXME. Boring-code compliant.
7. **Performance (CR-10):** one match (pattern #8, double read per record) —
   downgraded to Watch-List note after reading context (one-shot, bounded N,
   sub-second). No other patterns match.

### Watch List

- Double JSON read per record (see Findings in the Changes). Note only.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none — neighbour ring is clean.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff (0 errors), py_compile (OK, CI's
  gate), mypy isolated (0 errors), pytest (14 passed). Diff is additive → HEAD
  results are the delta. Coverage gap: no CI type-checker (stdlib-only plugin
  contract) — noted.
- [✓] **CR-02 Dispatch shape.** Diff 976 lines / 2 files — above the 200-line
  carve-out, so lens work was conducted in full (not a skim). Single new source
  file + its test; both read end-to-end. Lenses run sequentially by the one
  reviewer against a 2-file surface (no parallel sub-agent dispatch needed for a
  2-file diff; full-file reads satisfied).
- [✓] **CR-03 Full-file reads.** Both changed files (506-line source, 470-line
  test) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single note cites file + the specific
  call sites (`_read_json` at set-computation vs plan/migrate). No delta drafted
  (no failing characterisation test — behaviour is correct).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  fired (Build Verification empty; all files read end-to-end; all lenses
  produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks listed.
  Security: nothing surfaced + primitives listed. Quality: all 7 outputs
  produced (items 2/6 N/A-with-reason; item 7 one downgraded note).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat). PH-02 Size:
  low (1 source + 1 test). PH-03 Safety: none (0 migrations/schemas/secrets/
  infra). PH-04 Completeness: none (source ships with tests). PH-03 high → no
  auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached` (staged WP files) vs change branch.
- **Neighbour expansion:** manual — the 3 imported helpers, all read during
  implementation recon.
- **Neighbour cap:** 3 of 3 considered, none excluded.
- **Scanners run:** ruff, mypy, py_compile, pytest (+ pytest-cov ephemeral).
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked — diff is
  stdlib-only Python with no new deps, no secrets surface; manual SEC scan
  covered the applicable primitives.
- **Lenses dispatched in parallel:** no (2-file diff; full-file reads satisfied
  by direct read).
