# Code Review: feat/wp-002-consumers-pass-brief-change-id — Consumers pass brief_change_id on open()

> **Timestamp:** 2026-06-08T174013Z (ISO 8601 UTC)
> **Author:** executor (WP-002)
> **Branch:** feat/wp-002-consumers-pass-brief-change-id → change/fix-terminal-per-change-brief
> **Files changed:** 6 (3 source, 3 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change does one small, focused thing: it makes the three places that start a terminal session also tell the session *which change it is for*. Each of those three places already knows the change id — it uses it as the lookup key — so the change is just passing that same value along one more step. No build errors, every change has a test, and the changes are tightly scoped. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 140 lines across 6 files, half of them tests. Small and easy to review.

**Scope — clean.** A single concern (route the change id into the session brief target) applied consistently across the three callers. One commit type (`feat`).

**Safety — clean.** No database migrations, no schema or contract files, no infrastructure files, no secrets.

**Completeness — clean.** Every one of the three behaviour changes has a matching test. The browser-bridge change additionally has a test pinning the case where there is *no* change id, so the field is correctly left off rather than guessed.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all 6 files read end-to-end (each well under 50 lines of change); all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all low/none)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Mechanical baseline ran on HEAD (BASE was clean for the changed files):

- `ruff check` (socket_server.py, session_viewer.py, both test files) → exit 0, all checks passed. (`tool-outputs/ruff-check-head.log`)
- `mypy` (socket_server.py, session_viewer.py) → 11 errors, **all in untouched `manager.py`** (transitively imported), byte-for-byte present on BASE (confirmed by stash-and-recheck: 11-on-base). Zero errors in the two changed source files. Not PR-introduced. (`tool-outputs/mypy-head.log`)
- `tsc --noEmit -p server` → exit 0. (`tool-outputs/tsc-head.log`)
- `eslint` (TerminalSidecar.ts + test) → exit 0. (`tool-outputs/eslint-head.log`)

Build Verification section is **empty** (no PR-introduced errors).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 2 (plugins/sulis/scripts, apps/cockpit) → clean
  severity: low

Size (PH-02):
  lines_added: 139, lines_removed: 1, total: 140
  files_changed: 6 (3 source + 3 test)
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: low

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0  (3 behaviour changes, 4 new/extended tests)
  api_change_without_schema: false
  severity: none
```

No PH-03 high → no CR-06 auto-downgrade trigger.

### Findings in the Changes

None.

#### Lens output

**Architecture lens: nothing surfaced.** Checks run: new infrastructure/db/http imports into domain (none); new singletons / getInstance (none); circular imports (none); new external calls needing timeout/circuit-breaker/observability (none — the change is a data-field passthrough onto an existing spec); dependency direction (unchanged). Notable correct decision: in `TerminalSidecar.ts` the `brief_change_id: key` assignment is placed AFTER the `...(req.params.spec ?? {})` client-spec spread, making the sidecar's value authoritative — the deliberate trust-boundary choice that the client must not set the brief target (ADR-001). Verified against WP_BACKEND_STANDARD (WPB): the wire field is additive and defaulted; no contract break.

**Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (the brief_change_id value flows server-side into a filesystem path `~/.sulis/changes/{id}/pre_prompt.txt` — a path-injection surface — but the `SessionSpec.__post_init__` ULID shape-guard that rejects malformed values was added by WP-001, with dedicated `-evil`/control-char guard tests; WP-002 only routes the value, it adds no new validation gap), SC-01..04 (no dependency changes). Scanners: secret-pattern grep on the diff → 0 hits. No new auth/authz surface (the §2.13.4 binding guard is unchanged).

**Quality lens (all 7 outputs):**
1. Build Verification follow-up: none (baseline clean).
2. JSX/template identifier scan: N/A (no TSX/JSX/Vue/Svelte files in the diff).
3. Dead-surface: none — `brief_change_id` is read server-side by the adapter (WP-001) and now written by all three producers; no unused surface.
4. Contract-drift: none — single snake_case key name `brief_change_id` is symmetric end-to-end (TS sidecar + Python viewer write it; socket_server reads `spec_d.get("brief_change_id")`); verified grep-clean of camelCase/dash synonyms in Blue.
5. Test-coverage: every behaviour change has a test. socket_server (present+absent on wire), session_viewer (real-subprocess-thread round-trip via manager registry), TerminalSidecar (inject + omit-when-no-identity). MEA-09 no-mock posture preserved (real socket + real manager).
6. Style/readability: clean. Each change carries a WP-002/ADR-001 citation comment.
7. Performance (CR-10): no anti-pattern matches — the diff introduces no loops, no DB/RPC/filesystem calls, no materialisation. Single-field passthrough.

### Findings in the Neighbours

None. Neighbour ring: `SessionSpec` (adapter.py — read site, WP-001-owned, validation in place), `SessionManager.open` (stores spec verbatim — no change needed). Both within scope, no exposed gaps.

### Watch List

None.

### Cross-Reference

- No prior `.security/terminal-per-change-brief/` viability report.
- No existing hardening-deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `mypy` (Python); `tsc --noEmit -p server`, `eslint` (TS). Head: 0 PR-introduced errors (11 mypy errors all pre-existing in untouched manager.py, confirmed 11-on-base via stash-recheck). Coverage gap: none.
- [✓] **CR-02 Single-reader pass.** Diff: 140 lines / 6 files. Lines well within the 200-line carve-out; file count (6) is one over the 5-file limit, but every per-file change is a 1–5-line additive field (no file's change exceeds 50 lines) and all 6 files were read end-to-end — single-reader justified by per-file triviality + total size. Recorded per CR-02.
- [✓] **CR-03 Full-file reads.** All 6 changed files' diffs read end-to-end (210-line patch read in full). No sampling.
- [✓] **CR-04 Evidence discipline.** All lens outputs cite file/line + the specific construct (e.g. the post-spread placement in TerminalSidecar.ts:270-275). No findings to evidence.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings at any severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives/scanners listed. Quality: all 7 outputs produced (item 2 N/A — no JSX in diff).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low ({feat}, 2 dirs). PH-02 Size: low (140 lines / 6 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (0 new source without test). PH-03 high → auto-downgrade: no.

#### Run details

- **Diff source:** `git diff change/fix-terminal-per-change-brief` (working tree vs base; changes not yet committed at review time).
- **Neighbour expansion:** git grep on `brief_change_id` + `SessionSpec` consumers. 2 neighbours considered, 0 excluded.
- **Neighbour cap:** not reached (2 of 20).
- **Scanners run:** secret-pattern grep, CR-10 perf grep.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (Quick-equivalent scope on a 140-line additive diff; secret-pattern grep substituted, 0 hits).
- **Lenses dispatched in parallel:** no — single-reader per CR-02 carve-out justification above.
