# Code Review: feat/wp-009-entity-evolve-helper — Build `_entity_evolve` helper

> **Timestamp:** 2026-06-03T154144Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling (WP-009 executor)
> **Branch:** feat/wp-009-entity-evolve-helper → change/feat-product-project-opportunity-evolution
> **Files changed:** 3 (1 new helper, 1 new test, 1 small adapter change)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the core history-writing helper that turns on version
tracking for living entities (Products, Opportunities, Projects). It is a new
self-contained piece that nothing else calls yet — the wiring into the actual
emitters comes in a later piece of work. The build is clean, every new line of
the helper is covered by a test, and the tests run against a real on-disk store
rather than a fake. No issues need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Around 290 lines of new helper code plus a focused test
file. Single concern, single module.

**Scope — clean.** One logical change: the evolve helper, plus a small,
directly-required tidy-up to the storage adapter (making one internal path
helper public so the new code can reuse it instead of duplicating the layout).

**Safety — clean.** No database migrations, no schema changes, no
infrastructure files, no secrets. The helper writes files using a
write-to-a-temp-file-then-swap technique, so a crash mid-write never leaves a
half-written file visible.

**Completeness — clean.** 1 new source file, 1 new test file with 16 tests
covering every described behaviour, including the tricky conditional (Products
and Opportunities get a provenance link to the run that produced them; Projects
deliberately do not).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high/medium findings in the diff; Build
Verification empty; all changed files >50 lines read end-to-end; all three
lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 critical, 0 high, 0 medium, 1 low (note)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (above-port design, Protocol-typed, atomic write present) |
| Security | 0 | 0 | — (no secrets, no network, local FS only) |
| Quality | 1 (low) | 0 | tmp-file naming under cross-process concurrency (note, out-of-scope) |

### Build Verification (CR-01)

Empty. Mechanical baseline on HEAD:
- `ruff check _entity_evolve.py _entity_adapter_local.py tests/unit/test_entity_evolve.py` → All checks passed.
- `mypy _entity_evolve.py` → Success: no issues found.
- `compileall` → OK.
- `pytest tests/unit/test_entity_evolve.py --cov=_entity_evolve` → 16 passed, **100% coverage** on the new file.

The repo's CI gate is `ruff check` + `compileall` + manifest-JSON validity
(per `branch-ci.yml`: "no type-checker configured for this repo"). All pass.
mypy was run as an extra floor on the new module and is clean.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (plugins/sulis/scripts)
  severity: clean

Size (PH-02):
  lines_added: ~305 (helper 283 + adapter 15 net + test 509 new)
  lines_removed: 1
  files_changed: 3
  generated_ratio: 0
  lock_file_ratio: 0
  severity: clean (single-module, well-scoped)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0 (helper ships with 16-test characterisation file)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

No critical / high / medium findings.

#### Watch List (low / note — out of scope for this WP)

**`_entity_evolve.py:271` — tmp-file naming under cross-process concurrency
(note, quality).**

```python
tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
tmp.write_text(payload)
os.replace(tmp, path)
```

`os.getpid()` makes the temp filename unique per process, and `os.replace`
is atomic, so two concurrent evolves of the *same* entity from *different*
processes cannot produce a torn file — the last writer wins cleanly. A genuine
**lost-update** under concurrent multi-process writes to one entity (process A
and B both read window-list N, both append, B's replace clobbers A's window)
is theoretically possible, but that is the **central-home concurrency story
owned by WP-013** (ADR-005), not this file-adapter-only WP (ADR-003 OAQ-1
explicitly scopes this WP to the file-adapter envelope; SQLite/transactional
durability is deferred behind the same port). In-process single-writer use —
the only use this WP enables, since no emitter calls it yet (WP-012 wires it)
— has no race. No delta; recorded for the WP-013 reviewer's awareness.

### Findings in the Neighbours

None. Neighbour ring (≤20 files):
- `_entity_adapter_local.py` `save` / `find_by_id` still resolve via
  `_instance_path`, now a thin delegate to the new public `instance_path` —
  backward-compatible (full unit suite 1811 passed confirms no regression).
- `_entity_evolve` has no importers yet (correct — WP-012 wires the emitters).
- `test_golden_thread_integration.py`'s `_instance_path` is a *local test
  helper function*, unrelated to the adapter method — unaffected.

### Watch List

See "Findings in the Changes → Watch List" above (the tmp-file concurrency
note). No failing-characterisation-test grounding in this WP's scope → no
delta (CR-04).

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `mypy _entity_evolve.py`, `compileall`, `pytest --cov`. Base (the helper is net-new, so base has no helper): adapter change verified non-regressing via full suite. Head: 0 errors, 100% coverage. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff is one cohesive new module (~290 source lines) + its test file + a 15-line adapter delegation. Single-reader pass applied with full-file end-to-end reads of every changed file; the diff is a single self-contained module with no cross-file behavioural coupling (the helper has zero importers yet), so the three lenses were applied inline rather than as separate sub-agents. Recorded per CR-02.
- [✓] **CR-03 Full-file reads.** `_entity_evolve.py` (283 lines) and `test_entity_evolve.py` (509 lines) and the `_entity_adapter_local.py` change read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single note cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low (note, out-of-scope).
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — checks run: domain→infra import (none), new singleton (none), circular import (none), timeout/CB/retry (no network calls — local FS only; atomic write present), port-without-contract-test (helper HAS a characterisation test, real temp adapter no mock per MEA-09). Security: nothing surfaced — primitives checked SEC-01..07 (no auth/injection/validation surface; no user input; local FS), SC-01..04 (no new deps); secret-pattern scan clean. Quality: Build-Verification follow-up (empty); JSX scan (N/A — pure Python backend); dead-surface (ruff F401/F811/F841 clean); contract-drift (signature matches WP Contract + ADR-003: `evolve_entity(*, repo, entity_type, entity_id, new_fields, generated_by, at)`, no `used`, no `wasRevisionOf`); test-coverage observation (16 tests, 100% cov); style (clean); CR-10 perf (no loops with I/O — all I/O is O(1) per call, no N+1).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single `feat`, 1 dir). PH-02 Size: clean (3 files, single module). PH-03 Safety: clean (0 migrations, 0 schema, 0 secrets, 0 infra). PH-04 Completeness: clean (helper ships with its test file). PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/feat-product-project-opportunity-evolution` + untracked new files (`_entity_evolve.py`, `test_entity_evolve.py`).
- **Neighbour expansion:** `git grep` on `instance_path` / `evolve_entity` / `_entity_evolve` imports.
- **Neighbour cap:** 3 of 3 considered, 0 excluded.
- **Scanners run:** ruff (F-rules), mypy, manual secret-pattern grep.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (no new deps, no network, no secrets surface; manual grep covered the secret floor).
- **Lenses dispatched:** inline single-reader (justified above), all three produced output.
