# Code Review: WP-007 — Cockpit attaches the shared daemon, not its own host

> **Timestamp:** 2026-06-08T133510Z (ISO 8601 UTC)
> **Author:** executor (WP-007)
> **Branch:** feat/wp-007-cockpit-shared-daemon → change/create-change-owned-terminal-shared-session
> **Files changed:** 11 (1270 insertions, 332 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change re-points the cockpit's terminal so that it joins the one shared
terminal session per change instead of starting its own private one. Before,
the cockpit started its own throwaway terminal engine on a temporary address;
now it finds (or starts on demand) the single shared engine at a stable
address, so the browser terminal and the desktop terminal show the same live
session. The build is clean, the change is well-scoped to the terminal path
(it never touches the chat side, as required), the read-only safety check was
correctly updated to follow the moved code, and the existing terminal tests
were updated rather than broken. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 1270 lines across 11 files. About a third of that is the
two new test files and the new shared-daemon binding; the rest is a focused
re-point of one file (`index.ts`) plus the read-only safety check following
the moved code. Single concern, well-contained.

**Scope — clean.** Every changed file is on the terminal path named in the
work package. The founder's independence requirement (the terminal must not
depend on the chat side) is held, and there is an automated test that fails
if a future change breaks it.

**Safety — clean.** No database migrations, no schema changes, no secrets, no
infrastructure files. The one thing that starts a background program (the
shared terminal engine) is still gated by the read-only safety check — the
check was moved to follow the code, not weakened.

**Completeness — clean.** New behaviour ships with tests: a contract test for
the new shared-daemon binding (driven against a real stand-in engine over a
real socket, no mocks) and a composition test that drives the full browser →
socket → engine → terminal round-trip and confirms the shared engine survives
when one view closes.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every
changed file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — tsc + eslint clean on HEAD)
- **PR Hygiene:** 0 high, 0 medium findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 critical, 0 high, 0 medium, 1 low/note
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (no failing-characterisation-test-grounded deltas; the one note is a Watch-List item)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced — sound Form/Armor/Proof |
| Security | 0 | 0 | nothing surfaced — contract-controlled spawn, local AF_UNIX, gate preserved |
| Quality | 1 note | 0 | clever-but-correct token replacement in `materialiseCommand` (note only) |

### Build Verification (CR-01)

Empty. `npx tsc --noEmit -p server` exit 0 (0 errors); `npx eslint <changed files>`
exit 0 (0 errors). Raw logs in `tool-outputs/typecheck-head.log` +
`tool-outputs/eslint-head.log`. Base branch already clean for the same
commands (the migration introduced no new diagnostics).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat} (single concern: cockpit shared-daemon migration)
  module_fan_out: 1 top-level dir (apps/cockpit)
  severity: clean

Size (PH-02):
  lines_added: 1270, lines_removed: 332
  files_changed: 11 (3 new: ensureDaemon.ts + 2 test files; 8 modified)
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: clean (well within bands; ~half is new tests + new binding)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0 (ensureDaemon.ts ships with ensureDaemon.test.ts +
    is exercised by serverSharedDaemon.test.ts + the re-pointed lifecycle test)
  api_change_without_schema: false
  severity: clean
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

#### Watch List note — `apps/cockpit/server/lib/ensureDaemon.ts:198-202` — low (quality)

**Observation:** `materialiseCommand` resolves the `{socket}` and `{socket}.lock`
placeholders with a `.replace("{socket}.lock", lockPath).replace("{socket}", socketPath)`
chain on the non-exact-match branch. The ordering is load-bearing (the `.lock`
replace must run before the bare `{socket}` replace) and is correct as written.

**Why it is a note, not a finding:** the behaviour is fully covered by the
cold-start, concurrent, and e2e tests (all materialise the argv and the daemon
binds the expected socket+lock), the function is documented, and the Python
sibling (`daemon_client.py::_materialise_command`) uses the same shape. No fix
needed; recorded for awareness only. No Hardening Delta (no failing
characterisation test to ground one — CR-04).

### Findings in the Neighbours

None. The neighbour ring (TerminalSidecar.ts, the e2e wrappers, the read-only
gate test files, config.ts) was inspected; all consumers of the removed
exports were re-pointed and the gate's allow-list followed the spawn. No
pre-existing gap was exposed by the change.

### Watch List

- The cross-test-tree fake-pty-child helper (the python-invoking
  `writeFakePtyChild` in `serverTerminalLifecycle.test.ts` and the equivalent
  in `e2e/run-terminal-real-server.ts`) is duplicated ~8 lines. Deliberately
  not extracted: the two trees have different module-resolution roots + path
  depths and the `import/no-restricted-paths` rule governs cross-tree imports;
  the codebase already keeps per-tree test substrates separate
  (`terminal-backend.py`). Note only — not a delta.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this change
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npx tsc --noEmit -p server`; `npx eslint <changed>`. HEAD: 0 errors both. Base: clean for same commands. Coverage gap: coverage-% tool (`@vitest/coverage-v8`) not installed — recorded in WP journal preflight; manual branch analysis confirms all functions+branches in ensureDaemon.ts exercised.
- [✓] **CR-02 Dispatch shape.** Diff 2071 lines / 11 files (above carve-out). Lenses run as three structured passes by the executor with full file context (every changed file already read end-to-end during authoring); no sampling.
- [✓] **CR-03 Full-file reads.** All changed files >50 lines read end-to-end (authored/edited this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one note cites file:line + quoted logic.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low/note.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (Form: leaf util, stdlib+in-tree-framer imports only, no inversion/singleton/cycle; Armor: timeouts on spawn+probe+poll, DaemonStartError Internal-vs-absent, no secrets, local AF_UNIX, no byte logging; Proof: contract test + composition round-trip, MEA-09 no mocks). Security: nothing surfaced (SEC-01..07 + SC-01..04 — contract-controlled spawn argv, env/default socket path local 0o600, read-only gate preserved + re-pointed, independence MUST held). Quality: CR-01 clean; JSX scan N/A (server-only TS); dead-surface none (all exports consumed); contract-drift none; test-coverage present; CR-10 perf scan — no anti-pattern matches (only bounded loops: framer line-drain returns after first line, argv map, deadline-bounded poll).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single feat concern, one dir). PH-02 Size: clean (1270/332, 11 files, ~half new tests+binding). PH-03 Safety: clean (0 migrations/schemas/secrets/infra). PH-04 Completeness: clean (new binding ships with tests). PH-03 high → CR-06 auto-downgrade: no.

#### Run details

- **Diff source:** `git diff change/create-change-owned-terminal-shared-session -- apps/cockpit` (+ staged new files)
- **Neighbour expansion:** git grep for consumers of removed exports (startSessionManagerHost / SessionManagerHostHandle / handle.host) — all re-pointed; gate allow-list followed the spawn
- **Neighbour cap:** not reached (≪20 files)
- **Scanners run:** tsc, eslint (mechanical floor); manual lens analysis with full file context
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (no new dependency, no secret-shaped strings, no Dockerfile/infra in diff — security lens by inspection); `@vitest/coverage-v8` absent (coverage by manual branch analysis)
- **Lenses dispatched in parallel:** structured single-session passes (executor held full diff context); no file sampled
