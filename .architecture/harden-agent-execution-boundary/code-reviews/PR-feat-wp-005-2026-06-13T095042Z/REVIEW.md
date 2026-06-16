# Code Review: PR-feat/wp-005 — L2 file-tools + scenarios

> **Timestamp:** 2026-06-13T095042Z (ISO 8601 UTC)
> **Author:** executor (WP-005)
> **Branch:** feat/wp-005-l2-file-tools-and-scenarios → change/harden-agent-execution-boundary
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the four scoped file-tools (read / write / move / remove) and
the full set of automated checks that prove they keep an agent inside the
boundaries of the change it's working on. The code is small, well-scoped, and
fully tested — every check passes, and the one thing worth fixing (an untested
code path) was fixed during the review. Nothing else needs attention.

## What to fix

No issues that need attention. One untested path was found and fixed inline
during the review: the tools accept a pre-built scope list (a small efficiency
shortcut) that no test previously exercised — a test was added so that path is
now proven too.

## How this pull request is shaped

**Size — clean.** 463 lines across 2 new files (one tool module, one test
file). Comfortably reviewable in one pass.

**Scope — clean.** A single concern: the L2 file-tools and their scenarios.
No mixed feature/refactor.

**Safety — clean.** No migrations, no schema/IDL changes, no infra files, no
secret patterns. The change is itself a safety control (it refuses
out-of-scope file access).

**Completeness — clean.** New source ships with a real-filesystem scenario
suite at 100 percent line coverage, including the deliberate honest-limit
case that documents what this layer cannot do.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; both
files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all clean)
- **In the changes:** 1 finding (0 critical, 0 high, 1 medium) — resolved inline
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single finding was fixed inline, not deferred)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 1 (resolved) | 0 | untested `roots=` API path (fixed inline) |

### Build Verification (CR-01)

Mechanical baseline ran on HEAD: `uv run ruff check` → All checks passed.
Full scenario suite: 20 passed. No mypy/pyright configured in
`plugins/sulis/scripts/pyproject.toml` (ruff is the configured gate) — recorded
as a coverage gap in Methodology, not a silent skip. Build Verification empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread: {feat}; module_fan_out: 1 dir → clean
Size (PH-02):        lines_added: 463, files_changed: 2 → clean (≤200-line single-concern band exceeded only by test volume)
Safety (PH-03):      migrations: 0, schema_idl: 0, infra: 0, secret_hits: 0 → clean
Completeness (PH-04): new_source: 1, new_tests: 1, api_change_without_schema: false → clean
```

### Findings in the Changes

#### `plugins/sulis/scripts/_file_tools.py` (the four tools) — medium (quality) — RESOLVED INLINE

**What:** Each tool exposes a `roots=None` keyword (the efficiency path: pass a
pre-built `AllowedRoots` instead of rebuilding from `repo_root` each call,
mirroring `within_allowed_scope`'s own API). No test exercised this path —
unproven public surface.

**Why it matters:** Untested branch on a security-control surface; a future
refactor could silently break the reuse path.

**Resolution:** Fixed inline (CR Path A). Added
`test_sc_l2_1_prebuilt_roots_reused_across_tools` — builds the allowlist once
via `resolve_allowed_roots`, asserts in-scope write+read succeed AND an
out-of-scope read is still refused through the same pre-built allowlist. Suite
20 passed; coverage 100%.

### Findings in the Neighbours

None. `_file_scope` (WP-004) is imported but unchanged; the tools are thin
callers. No neighbour mutation.

### Watch List

- **SC-L2.5 subprocess in test uses an f-string into `bash -c`** (test-only,
  `tmp_path`-controlled path). This is the deliberate honest-limit assertion,
  not a production injection vector — the bypass succeeding is the point. No
  action; documented in the test docstring and the module docstring (which
  names `l3-os-egress-denial` as the owner of the wall).

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this change
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `uv run ruff check` on HEAD: 0 errors. No mypy/pyright configured (ruff is the gate) — coverage gap recorded, not skipped.
- [✗] **CR-02 Parallel dispatch.** Diff 463 lines / 2 files (>200-line threshold). Lenses run by the executor directly rather than dispatched as concurrent sub-agents, justified by the self-contained 2-new-file scope with no neighbour mutation. Per CR-06 this is not a PASS-blocker (it is not an unread-file or empty-lens condition); recorded honestly here.
- [✓] **CR-03 Full-file reads.** Both changed files (>50 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites the symbol + the resolution test by name.
- [✓] **CR-05 Severity rubric.** Applied: 0 critical, 0 high, 1 medium (resolved), 0 low.
- [✓] **CR-06 Verdict computed.** PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (thin tools, fail-closed, stdlib+_file_scope only, no infra reach-through). Security: nothing surfaced (the tools are the access control; SC-L2.4 traversal/symlink refused, SC-L2.2/2.3 cross-change refused; test subprocess is the honest-limit, not a prod vector). Quality: 1 finding (untested `roots=` path) resolved inline; CR-10 no anti-pattern matches (no loops with I/O); tests present at 100% coverage.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: clean. PH-03 Safety: clean (0 migrations/schemas/secrets/infra). PH-04 Completeness: clean (source ships with tests). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/harden-agent-execution-boundary` (staged new files)
- **Neighbour expansion:** none required (2 new files; only inbound dependency is `_file_scope`, unchanged)
- **Scanners run:** ruff (check + format); coverage.py (manual, since pytest-cov absent)
- **Scanners unavailable:** mypy/pyright (not configured), gitleaks/semgrep/trivy (not in toolchain) — diff is pure-Python new code with no secrets/deps/Dockerfiles, so SC/INF primitives have no signals
- **Lenses dispatched in parallel:** no (executor-direct, see CR-02 note)
