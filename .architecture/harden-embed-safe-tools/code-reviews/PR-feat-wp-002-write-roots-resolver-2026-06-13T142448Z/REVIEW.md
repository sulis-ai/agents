# Code Review: feat/wp-002-write-roots-resolver — write-roots resolver, one source for file-tools + sandbox

> **Timestamp:** 2026-06-13T142448Z (ISO 8601 UTC)
> **Author:** executor (WP-002)
> **Branch:** feat/wp-002-write-roots-resolver → change/harden-embed-safe-tools
> **Files changed:** 2 (`plugins/sulis/scripts/_file_scope.py`, `plugins/sulis/scripts/tests/unit/test_write_roots_resolver.py`)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one writable folder (the "brain", when it lives outside the
working copy) to the safety list that decides where the agent is allowed to
write, and a small helper that hands the same list to the operating-system
sandbox — so the two can never disagree. The work is well-scoped (one module
plus its tests), the build is clean, and it is fully tested test-first.

The review found one thing worth hardening — and fixed it in place: a brain
folder that was accidentally pointed at the whole shared state area would have
let the agent reach *other* pieces of work's files. The resolver now refuses a
brain folder that broad, which is exactly the rule the design document calls
for. After the fix, all 77 related tests pass.

## What to fix

No issues that need attention. The one finding below was resolved inside this
change during review.

### Worth fixing (resolved in this change) — `plugins/sulis/scripts/_file_scope.py`, `_resolve_brain_root`

**What's happening:** The new code asks a shared helper where the "brain"
folder lives and adds it to the list of places the agent can write. That
helper returns whatever has been configured. If someone configured it to point
at the whole shared state area (the folder that holds every piece of work's
private files), the resolver would have added that whole area as writable.

**Why it matters:** Each piece of work is supposed to be confined to its own
files. A writable folder that contains *every* piece of work's files reopens
the exact cross-contamination risk this safety layer exists to prevent — one
job could overwrite another's state.

**What to do (done):** The resolver now refuses a brain folder that is, or
contains, the per-job state area — it falls back to "no extra folder" rather
than widening access. This matches the design rule "the specific resolved
subtree, never the whole shared area." A test was added first to prove the hole
existed, then the guard closed it.

## How this change is shaped

**Size — clean.** Small and focused: 372 lines added across 2 files, one of
them the test file.

**Scope — clean.** A single feature on one module, with its tests.

**Safety — clean.** No database migrations, no schema or infrastructure
changes, no secrets.

**Completeness — clean.** Tests were written before the code (test-first), and
cover the new behaviour including the adversarial misconfiguration case and a
property-based check of the "one source" guarantee.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
changed files read end-to-end; all three lenses produced output. The one
medium architecture finding was resolved inline (with a failing-then-passing
characterisation test), so no merge-blocker remains.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff check clean, `py_compile` OK, no type-checker configured (stdlib contract).
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean).
- **In the changes:** 1 finding (0 critical, 0 high, 1 medium, 0 low) — resolved inline.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single finding was fixed in-change rather than deferred to a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (resolved) | 0 | Narrowest-root invariant documented but not enforced for a misconfigured brain → fixed |
| Security | 0 | 0 | gitleaks clean; no injection/authz/SSRF surface in a pure path-resolver |
| Quality | 0 | 0 | Test-first, full RGB; no CR-10 anti-patterns |

### Build Verification (CR-01)

None. `ruff check` clean on both files; `python3 -m compileall` OK; no
type-checker configured for this repo (stdlib-only plugin contract, per
branch-ci.yml).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {feat}; module_fan_out: 1 → clean
Size (PH-02):         +372 / -8; files_changed: 2 → clean
Safety (PH-03):       migrations: 0; schema/idl: 0; infra: 0; secrets: 0 → clean
Completeness (PH-04): new_source_without_test: 0; api_change_without_schema: false → clean
```

### Findings in the Changes

#### `plugins/sulis/scripts/_file_scope.py` — `_resolve_brain_root` — medium (architecture) — RESOLVED INLINE

**Quoted text (pre-fix):**
```python
brain = canonical(brain_base_dir(repo_root))
if brain is None:
    return None
if _is_within(brain, worktree):
    return None
return brain
```

**Gap (HD-02 type: scope-widening / cross-tenant isolation):** `brain_base_dir`
returns whatever is configured. The docstring claimed the narrowest-root
invariant ("never all of `~/.sulis/`"), but the code did not enforce it: a
brain configured to the state base — or any ancestor of `changes_base()` —
would be added as a writable root containing every sibling change's state,
reopening the #130 cross-change risk ADR-004 rejects. Verified reproducible
before the fix (a write to `changes/{OTHER}/state.json` returned `ok=True`).

**Fix applied:** Added a guard refusing a brain root that is, or contains, the
per-change `changes/` tree (`_is_within(changes_root, brain)` → `return None`),
plus the `changes_base` import. Fail-closed.

**Characterisation test (CR-04):** `test_misconfigured_brain_at_state_base_refused`
— written first (failed: `brain_dir` was the state base), passes after the
guard. Post-fix verification across `state-base`, `changes-base`, and
`legit-relocated` cases confirms only the legitimate relocated brain is added,
and a sibling-change write is refused in every case.

### Findings in the Neighbours

None. `within_allowed_scope` / `permitted_for` callers (the file-tools, the hook
in WP-003/005) consume the same `AllowedRoots` and inherit the corrected
behaviour for free. No neighbour gap exposed.

### Watch List

- The WP-004 sandbox recipe will paste `sandbox_write_roots(...)` output into
  `sandbox.filesystem.allowWrite`. The `git_common_dir` root is partly
  redundant under the sandbox's automatic `.git` allow (documented in the
  function docstring per ADR-004) — intentional, not a defect; noted for the
  WP-004 reviewer.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this change.
- **Pattern suggesting full audit:** none — the finding is local to this WP's
  new function and was closed in-change.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `uv run ruff check` (configured linter) + `python3 -m compileall` (CI lint floor). Base + Head both clean; 0 PR-introduced errors. Type-checker: none configured (stdlib contract) — recorded, not skipped silently.
- [✓] **CR-02 Single-reader pass justified by diff size:** 372 lines, 2 files — within the ≤200-lines-OR-≤5-files? No: 372 > 200. Re-evaluated: line count exceeds 200, but file count (2) and the fact one file is the test file and the source delta is a single cohesive pure-function module kept this a single-reader pass with end-to-end reads of both files (CR-03 satisfied). Note: borderline; full end-to-end read performed in lieu of sub-agent dispatch given the single-module, no-neighbour-fanout shape.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (`_file_scope.py` 355 lines; test file 262 lines). No sampling.
- [✓] **CR-04 Evidence discipline.** Finding cites file + symbol + quoted pre-fix text + reproduction + characterisation test.
- [✓] **CR-05 Severity rubric.** 1 medium (operational/safety isolation gap, requires misconfiguration to trigger; not exploitable on default or normal-relocated paths). Resolved inline.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: 1 finding (resolved). Security: nothing surfaced — primitives checked SEC path/scope-widening, DAT-03 secret exposure; gitleaks clean on both files; semgrep/trivy available, no applicable signals in a stdlib pure-path-resolver. Quality: 0 findings + CR-10 scan (no loop-I/O / N+1 / O(N²) — the one production loop iterates a ≤5-element in-memory list) + dead-surface (none; new symbols all consumed by tests + documented WP-004 consumer) + contract-drift (none) + test-coverage (test-first, RGB, property test for single-source invariant).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: clean. PH-03 Safety: clean (0 migrations/schemas/secrets/infra). PH-04 Completeness: clean (tests-first). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/harden-embed-safe-tools` (local).
- **Neighbour expansion:** git grep on `within_allowed_scope` / `AllowedRoots` / `resolve_allowed_roots` / `sandbox_write_roots` — consumers are the file-tools + hook (WP-003/004/005, not yet present) and the existing `test_file_scope.py`; all inherit corrected behaviour. No neighbour finding.
- **Neighbour cap:** not reached (single-module change).
- **Scanners run:** gitleaks (clean, both files). semgrep + trivy available; no applicable signals.
- **Lenses dispatched in parallel:** no — single-reader pass with full end-to-end reads (single cohesive module, no neighbour fan-out).
