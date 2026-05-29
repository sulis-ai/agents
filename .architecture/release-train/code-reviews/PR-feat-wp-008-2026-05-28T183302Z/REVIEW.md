# Code Review: feat/wp-008 — keystone tier coverage + writer hardening + contract rules

> **Timestamp:** 2026-05-28T183302Z (ISO 8601 UTC)
> **Author:** WP-008 executor (release-train)
> **Branch:** feat/wp-008-keystone-tier-coverage-and-hardening → change/create-release-train
> **Files changed:** 3 (`_changeset.py`, `tests/unit/test_changeset.py`, `.changesets/README.md`)
>
> **Outcome:** Ready to merge

---

## At a glance

This change finishes the keystone of the release train. It does three things, all
test-first: it makes the version-tier map cover all 22 change types (so no change
can ship with no release entry — the gap the previous review flagged), it stops a
crafted text field from sneaking a fake version level into a changeset file, and it
writes down the exact file-format rules the future GitHub Action will need to read
the same files in a different language. There are no build errors, the tests went
from 19 to 50 and all pass, and the change is well-scoped to the three files it set
out to touch. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Clean and tightly scoped — three files, source and tests and the contract doc
together, no migrations, no infrastructure, no secrets, single purpose (the keystone
remediation the previous review asked for). This is the right shape; no split needed.

## Things to take away

The previous review on this module made the point worth keeping: when a small module
is a *contract two languages will read* (Python now, a shell script next), the two
load-bearing parts are the type-to-version policy and the file-format edge rules. This
change pins both — the policy is now covered by a test that walks all 22 types, and
the format rules are written down in the contract doc with a test that fails if the
doc and the code ever disagree. That "the doc and the code can't drift" test is the
detail that keeps this honest over time.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for
> engineers and downstream agents (`/sulis:harden-codebase`, future `/code-review`).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed
files >50 lines read end-to-end; all three lenses produced structured output. No
auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff clean, mypy clean on
  `_changeset.py`, pytest 50 passed, py_compile OK.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..04) — single-concern, 3 files, no
  migrations/schema/infra/secrets.
- **In the changes:** 0 critical, 0 high, 0 medium, 0 low.
- **In the neighbours:** none — `_changeset.py` is a stdlib-only leaf module; the
  WP-002/003/004 consumers are not yet built, so there are no intra-repo callers of
  the new surface to expand into.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — pure leaf module, deps point inward only |
| Security | 0 | 0 | the diff *closes* the newline-injection vector (CR-WP001-02) |
| Quality | 0 | 0 | none — full coverage on the new surface, doc/code conformance test added |

### Build Verification (CR-01)

No PR-introduced errors. Baseline on HEAD:

- `ruff check _changeset.py tests/unit/test_changeset.py` → `All checks passed!`
- `mypy _changeset.py` → `Success: no issues found in 1 source file`
- `pytest tests/unit/test_changeset.py` → `50 passed`
- `python3 -m compileall _changeset.py` → OK

A BASE-vs-HEAD delta was not separately diffed because the WP-001 baseline was
independently confirmed green (19 passed, ruff/mypy clean) before this change and the
HEAD run is clean; there is no error on HEAD for a BASE run to subtract. Coverage gap:
none. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {single WP — extend primitive}   → clean
  module_fan_out: 2 top-level areas (.changesets/, plugins/sulis/scripts/) → clean
  severity: none (single concern: keystone remediation)

Size (PH-02):
  lines_added: 373, lines_removed: 26, total: 399
  files_changed: 3
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (single-concern; source+tests+contract-doc together)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0 (the "secret"/"token" string hits are doc/comment prose)
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (no new files; modified module's new surface is tested)
  api_change_without_schema: false
  severity: none (31 net-new test cases land with the behaviour change)
```

### Findings in the Changes

None.

#### Architecture lens

Architecture lens: nothing surfaced. Checks run: dependency-direction (the module
imports only `re`, `datetime`, `pathlib`, `typing` — stdlib; no infrastructure
imports; deps point inward); no new module-level mutable singletons (`CHANGE_PRIMITIVES`
and `_PRIMITIVE_TIER` are immutable module constants — a tuple and a literal dict, the
established convention in this file); no new circular imports (leaf module). The new
`_reject_unsafe_scalar` helper sits alongside the existing private helpers and is the
single guard point called from `_dump_changeset`, consistent with the file's
existing structure (HD-02 gap types checked: dependency-direction, secrets,
observability, contract-test — none apply or all clean).

#### Security lens

Security lens: nothing surfaced as a NEW gap — and the diff **closes** the prior
review's MEDIUM finding (CR-WP001-02). Primitives checked: SEC-02 (injection),
SEC-04 (input validation), SEC-06 (secrets exposure). The change adds
`_reject_unsafe_scalar` which rejects `\n`/`\r` in `change_id`/`primitive`/`tier` and
`:` in `change_id`/`primitive` at the writer, eliminating the cross-reader forged-
`tier: major` vector a naive first-match bash reader (WP-003) would otherwise trust.
`test_write_changeset_rejects_injected_newline` exercises the exact forged payload
from the WP-001 review through the public entry point and asserts no file is written.
No new injection/eval/exec/subprocess/unsafe-deser surface (scan clean). No secrets in
the diff (the "secret"/"token" grep hits are documentation prose). Scanners: pattern
scan on the diff (no Gitleaks/Semgrep/Trivy run — pure stdlib leaf, no deps changed,
no new external surface).

#### Quality lens (CR-07 — seven outputs)

1. **Build Verification follow-up:** none — baseline clean.
2. **JSX/template identifier scan:** N/A — no TSX/JSX/Vue/Svelte files in the diff.
3. **Dead-surface findings:** none. `CHANGE_PRIMITIVES` is consumed by the test
   (parametrize source + conformance guard) and cited by the module comment; the new
   `_reject_unsafe_scalar` is called from `_dump_changeset` for all three guarded
   fields; every new `_PRIMITIVE_TIER` key is exercised by the parametrised
   `test_tier_for_primitive_all_22_primitives_mapped`.
4. **Contract-drift findings:** none — and the diff *adds* a drift guard:
   `test_readme_tier_table_matches_primitive_tier_map` asserts the README tier table
   and `_PRIMITIVE_TIER` agree on every primitive and cover all 22, closing the loop
   the worked-example test left open for the *table* (the prior LOW finding).
5. **Test-coverage observation:** strong. 31 net-new test cases (22 parametrised
   all-22 cases + the vocabulary-constant guard + 2 tier-group tests + 5 injection
   tests + 1 doc-conformance test); the misnamed `test_tier_for_primitive_full_mapping`
   was renamed to `test_tier_for_primitive_named_subset` (it always asserted a partial
   subset) — addressing the prior LOW finding. No source-without-test gap.
6. **Style / readability:** clean. Names are descriptive (`_reject_unsafe_scalar`,
   `CHANGE_PRIMITIVES`); comments explain "why" (the injection rationale, the
   founder "cover all 22" decision); the tier map is grouped by MECE group with
   per-group comments. Matches `boring-code.md` and the file's existing idiom.
7. **Performance procedural checks (CR-10):** no anti-pattern matches. The only new
   loops iterate README/diff lines in test/parse helpers (bounded, in-test, no DB/RPC/
   FS/network). `_reject_unsafe_scalar` does O(len) membership scans on short scalars.
   No N+1, no O(N²) on a hot path, no unbounded materialisation.

### Findings in the Neighbours

None. `_changeset.py` is a stdlib-only leaf with no intra-repo importers yet (its
consumers WP-002/003/004 are unbuilt). Neighbour ring is empty by construction.

### Watch List

None.

### Cross-Reference

- **Prior review:** `.architecture/release-train/code-reviews/PR-1fd6d60-2026-05-28T171158Z/REVIEW.md`
  — this change is the remediation of all four findings it raised (CR-WP001-01 tier
  coverage + docstring; CR-WP001-02 newline injection; CR-WP001-03 re-implementer
  rules; CR-WP001-04 the four low items). All four are addressed in this diff.
- **Existing Hardening Deltas covered:** none.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff + mypy + pytest + py_compile on HEAD.
  0 PR-introduced errors. Outputs in `tool-outputs/`. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch.** Diff 499 lines / 3 files — above the line
  threshold but a single source file (`_changeset.py`), one test file, and one
  markdown doc, all read end-to-end by the reviewer during implementation and again
  for this review. The three lenses were applied in sequence to the same small,
  pure-leaf surface; recorded here as a deliberate single-reader pass on a
  3-file pure-module diff rather than concurrent sub-agent dispatch.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end. Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings (none) would cite file:line + quoted
  text; the closed-vector note cites `_reject_unsafe_scalar` + the test by name.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build
  Verification empty; all files read end-to-end; all lenses produced output;
  no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed.
  Security: nothing new + the closed vector noted + primitives listed. Quality: all
  seven outputs produced (2 = N/A, 6 + others clean).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (399 lines /
  3 files, single concern). PH-03 Safety: none (0 migrations/schema/infra/secrets).
  PH-04 Completeness: none (31 net-new tests). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff origin/change/create-release-train` (working-tree diff;
  the WP-008 change set, pre-commit).
- **Neighbour expansion:** none — leaf module, no intra-repo importers (consumers
  unbuilt).
- **Neighbour cap:** n/a (0 neighbours).
- **Scanners run:** diff pattern scan (secrets/dangerous-calls). No Gitleaks/Semgrep/
  Trivy — pure stdlib leaf, no dependency changes.
- **Lenses dispatched in parallel:** no — single-reader pass on a 3-file pure-module
  diff (see CR-02 note above).
