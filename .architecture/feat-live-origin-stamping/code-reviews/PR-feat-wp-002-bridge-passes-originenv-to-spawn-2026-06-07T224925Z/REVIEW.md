# Code Review: WP-002 — Bridge adapter passes `originEnv` through to the spawn

> **Timestamp:** 2026-06-07T224925Z (ISO 8601 UTC)
> **Author:** executor (WP-002)
> **Branch:** feat/wp-002-bridge-passes-originenv-to-spawn → change/feat-live-origin-stamping
> **Files changed:** 3
>
> **Outcome:** Ready to merge

---

## At a glance

This change is small, focused, and clean. It wires the chat bridge so a web-chat
session can carry its "who started this work" stamp through to the agent it
launches — exactly the one job the work package asked for. There are no build
errors, the new behaviour has tests for both the "stamp present" and "no stamp"
cases, and the read-only safety check still passes. Nothing needs fixing before
merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 92 lines added, 1 removed, across 3 files. Small and easy to
review thoroughly.

**Scope — clean.** A single concern: forward the origin stamp to the spawn. One
behaviour-adding change plus its tests.

**Safety — clean.** No database migrations, no schema or infrastructure files, no
secrets. The change passes env to a spawn that was already permitted to start —
it writes nothing and starts no new process, so the cockpit stays read-only.

**Completeness — clean.** Two new tests accompany the behaviour change, covering
both the stamp-present and stamp-absent paths.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents like `/sulis:harden-codebase`.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all changed
files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`npx tsc --noEmit -p server` → 0 errors (HEAD). `npx tsc --noEmit -p client` →
0 errors. `npx eslint --ext .ts,.tsx <changed>` → 0 errors. Base had 0 errors;
no PR-introduced errors. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat} (single concern)  → clean
  module_fan_out: 1 (apps/cockpit/server)       → clean
  severity: clean

Size (PH-02):
  lines_added: 92, lines_removed: 1, total: 93
  files_changed: 3
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: clean (≤200 line band; ≤5 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0 (no new source files; 2 new tests added)
  api_change_without_schema: false
  severity: clean
```

### Findings in the Changes

None.

Lens detail:

- **Architecture lens: nothing surfaced.** Checks run: dependency direction
  (port `SessionBridge.ts` owns the widened signature; adapter
  `StreamJsonSessionBridge.ts` forwards inward-only — no new infra import, no
  singleton, no circular path); resilience (no new external call — env is
  passed to the already-sanctioned spawn; no new timeout/retry/CB surface);
  verification (the port's contract is exercised by the existing reusable
  contract suite plus the 2 new adapter tests). The change conforms to ADR-017
  (optional widening to match the production default) and ADR-003 (no new
  spawn site; `check-read-only.sh` clean, exit 0, 196 files).
- **Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no new
  authz surface, no injection vector — env forwarded AS-IS to a spawn already
  permitted; per ADR-013/WP-003 the #216 `parse_origin_env` is the single
  boundary sanitiser, so the adapter correctly does NOT double-sanitise),
  DAT-03 (no PII/token-shaped logging added). Secrets scan on diff: 0 hits.
  No new dependency (SC-01..04 n/a).
- **Quality lens:** (1) Build Verification follow-up: none (CR-01 clean).
  (2) JSX/template identifier scan: n/a (server-only TS, no TSX/JSX).
  (3) Dead-surface: none — the new `originEnv` param is consumed (forwarded to
  `spawnBridge`). (4) Contract-drift: none — port signature, adapter
  signature, and the 2 tests are aligned; the optional 4th param is assignable
  for the narrower `RecordedSessionBridge.relay` implementation (TS interface
  satisfaction). (5) Test-coverage: present — both stamp-present and
  stamp-absent paths covered. (6) Style: clear naming, "why" comment on the
  forward; nothing to flag. (7) CR-10 performance: no anti-pattern matches (no
  loops, no DB/RPC/fs calls introduced).

### Findings in the Neighbours

None. Neighbours examined: the `relay` call sites
(`routes/chat.ts`, `lib/discovery/onboardingOrchestrator.ts`) and the sibling
adapter `RecordedSessionBridge` (the other `SessionBridge` implementer). All
continue to call `relay` with 3 args; the optional 4th param leaves them
byte-identical. WP-004 will wire the assisted origin at the chat route.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npx tsc --noEmit -p server`;
  `npx tsc --noEmit -p client`; `npx eslint --ext .ts,.tsx <changed>`. Base: 0
  errors. Head: 0 errors. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 93 lines, 3 files**
  (within the ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end (the two
  source files in full; the test file in full). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence (clean diff); lens
  checks-run enumerated above.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  fired (Build Verification empty; all files read end-to-end; all lenses
  produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks run.
  Security: nothing surfaced + primitives checked + secrets scan. Quality: all
  seven outputs produced (1–5, 7 explicit; 6 empty — permitted).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single feat concern,
  1 module). PH-02 Size: clean (93 lines / 3 files). PH-03 Safety: clean (0
  migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: clean (0 new
  source w/o test; 2 tests added). PH-03 high → CR-06 auto-downgrade: no.

#### Run details

- **Diff source:** local git working-tree diff (branch
  feat/wp-002-bridge-passes-originenv-to-spawn vs base
  change/feat-live-origin-stamping @ b40f9d4; changes uncommitted at review
  time — reviewed pre-commit at Step 6.5)
- **Neighbour expansion:** git grep for `.relay(` call sites + sibling
  `SessionBridge` implementers
- **Neighbour cap:** 3 of 3 considered, 0 excluded
- **Scanners run:** tsc, eslint, manual secrets grep on diff
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed — diff-scoped
  manual secrets grep substituted (diff is 93 lines, no new deps); coverage
  gap noted
- **Lenses dispatched in parallel:** no (single-reader carve-out, CR-02)
