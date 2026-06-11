# Code Review: WP-008 — Phase 2 stateful model-based test (change lifecycle never acts on the wrong id)

> **Timestamp:** 2026-06-11T150218Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-008)
> **Branch:** feat/wp-008-stateful-model-based-test → change/fix-use-change-id-not-handle
> **Files changed:** 1 (new test file)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one new test file — a property-based "state machine" test
that drives random sequences of the change lifecycle (start / ship / nuke /
recreate / focus) and, after every step, checks that no operation ever acts on
the wrong change and that an ambiguous short handle always refuses rather than
guessing. It adds no production code. The build is clean, all tests pass, and
the file is well-scoped. One small readability cleanup was applied during
review (a cryptic one-liner was replaced with a named helper). Nothing else
needs attention.

## What to fix

No issues that need attention.

One minor readability improvement was applied inline during the review: a
hard-to-read one-line trick for raising an error from a lambda was replaced
with a plainly-named helper function, matching how the existing sibling tests
do the same thing.

## How this pull request is shaped

**Size — clean.** 486 lines in a single new test file. Large for a test, but
it is one cohesive artifact (a state machine plus four deterministic anchor
tests), not mixed concerns.

**Scope — clean.** One file, one purpose (`test:` only). No production code,
no migrations, no schema, no infra, no dependency changes.

**Safety — clean.** No migrations, no secrets, no infrastructure files. The
test runs entirely in-memory (a dict-backed store model) with no git or
filesystem side effects; state isolation is provided by the repo-wide test
fixture.

**Completeness — clean.** The change IS the test. It complements the existing
example-based collision suite by proving the same safety holds universally
(generated inputs) and across operation sequences.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the
single changed file was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean for a single test-only file)
- **In the changes:** 1 finding (1 low — readability, fixed inline)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the one finding was fixed inline, not deferred)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — test-only; no domain/infra imports, no network, no secrets |
| Security | 0 | 0 | None — synthetic ULID constants; no auth/injection/secret surface |
| Quality | 1 (fixed) | 0 | Cryptic lambda-raise idiom → replaced with named `_raise_refused` |

### Build Verification (CR-01)

Mechanical baseline (the marketplace profile's lint gate is `py_compile` +
manifest JSON validity; ruff additionally run as Boy-Scout check):

- `ruff check` → All checks passed (see `tool-outputs/ruff-head.log`).
- `python -m py_compile` → OK (see `tool-outputs/pycompile-head.log`).
- `uv run pytest tests/unit/test_change_lifecycle_stateful.py -q` → 5 passed.
- `uv run pytest tests/unit/ -q` → 2612 passed, 9 skipped (no regression).

No PR-introduced errors. Build Verification section empty → PASS not blocked.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type: {test}; module_fan_out: 1 dir   → clean
Size (PH-02):         +486 / -0; files_changed: 1; generated: 0    → low (single cohesive test file)
Safety (PH-03):       migrations: 0; schema: 0; secrets: 0; infra: 0 → clean
Completeness (PH-04): new_source_without_test: 0 (this IS the test) → clean
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

#### `tests/unit/test_change_lifecycle_stateful.py:99` — low (quality), FIXED INLINE

**What:** `_patch_refusal` raised `_Refused` from a lambda via the
`(_ for _ in ()).throw(...)` generator-throw idiom.

**Quoted (pre-fix):**
```python
side_effect=lambda message, context=None: (_ for _ in ()).throw(_Refused(...))
```

**Why it matters:** The idiom is cryptic and diverges from the codebase
convention (the example-based suites use a plain `def _err(...): raise ...`
side-effect). Readability only — no behavioural defect.

**Resolution:** Replaced with a named `_raise_refused(message, context=None)`
helper used as the `side_effect`. Re-ran ruff (clean) and the file's tests
(5 passed). Fixed in-scope; no Hardening Delta needed.

### Findings in the Neighbours

None. The diff imports `sulis-change` and `_change_identity_strategies` but
modifies neither; both are read-only consumers. The lazily-imported
`_change_state.change_worktree_dir` was verified to be pure path computation
(no `mkdir`/write), confirming the BLUE DoD "no on-disk side effects".

### Watch List

None.

### Cross-Reference

- Per-call analogue: `test_change_identity_properties.py` (WP-007).
- Example-based real-store complement: `test_collision_regression.py` (WP-004).
- No prior security report for this project; nothing to cite.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `py_compile` + pytest on HEAD; base is green by construction (new file). 0 PR-introduced errors. Coverage gap: pytest-cov absent (recorded in WP pre-flight); test module fully exercised by its own 5 tests.
- [✓] **CR-02 Dispatch shape.** Single-reader pass: 1 file, test-only, no neighbour modifications. Above the 200-line size threshold but a single cohesive artifact with a 0-file neighbour-modification ring; lenses run inline.
- [✓] **CR-03 Full-file read.** The one changed file (486 lines) read end-to-end.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line + quoted text; fixed inline (no theoretical delta).
- [✓] **CR-05 Severity rubric.** 1 low (readability). No critical/high/medium.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no domain/infra imports, no network/timeouts/secrets; worktree path verified pure). Security: nothing surfaced (synthetic constants; no auth/injection/secret surface; no scanners needed for a test-only diff). Quality: 1 finding (fixed) + dead-surface clean (ruff F) + CR-10 perf scan clean (the `.get()` hits are dict accesses on the in-memory model, not DB/RPC/FS) + test-coverage (the change is the test).
- [✓] **CR-09 PR Hygiene applied.** PH-01..04 all clean (single test-only file). PH-03 high → no.

#### Run details

- **Diff source:** `git diff --cached` vs `change/fix-use-change-id-not-handle`
- **Neighbour expansion:** none required (no modified neighbours; imports read-only)
- **Scanners run:** ruff, py_compile, pytest
- **Scanners unavailable:** pytest-cov (manual coverage analysis applied)
