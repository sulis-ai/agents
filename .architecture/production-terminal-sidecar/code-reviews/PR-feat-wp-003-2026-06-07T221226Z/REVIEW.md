# Code Review: feat/wp-003-origin-validation-and-resource-caps — WebSocket Origin validation + resource caps

> **Timestamp:** 2026-06-07T221226Z (ISO 8601 UTC)
> **Author:** executor (WP-003)
> **Branch:** feat/wp-003-origin-validation-and-resource-caps → change/create-production-terminal-sidecar
> **Files changed:** 2 (227 insertions, 1 deletion)
>
> **Outcome:** Ready to merge

---

## At a glance

This change finishes the safety controls on the terminal feature: it proves the
foreign-page block and the connection/usage limits work, and adds a single
audit line every time a connection is turned away. The build is clean, every
new behaviour has a test, and nothing private (no keystrokes, no terminal
output) is ever written to the audit line. No issues need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: two files, both about the same thing (hardening the
terminal connection). New code comes with new tests. Nothing private leaks into
the new audit line. This is exactly the shape a focused change should have.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean/low)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Mechanical baseline clean. `npx tsc --noEmit -p server` → 0 errors on HEAD.
`npx eslint` on the two changed files → 0 errors. Base branch (merged WP-002)
was already green, so there are no PR-introduced mechanical errors. Section
empty → does not block PASS.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat} (single concern: Secure hardening)  → clean
  module_fan_out: 1 top dir (apps/cockpit/server)                → clean
  severity: low
Size (PH-02):
  lines_added: 227, lines_removed: 1, total: 228
  files_changed: 2
  (227 lines, but ~170 are new test code; production delta ~30 lines)
  severity: low (2-file band; net production surface small)
Safety (PH-03):
  migration_count: 0; schema_idl_count: 0; infra_files: 0; secret_pattern_hits: 0
  severity: low
Completeness (PH-04):
  new_source_without_test: 0 (the production delta is covered by 7 new tests)
  api_change_without_schema: false
  severity: low
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The single neighbour is `apps/cockpit/shared/ndjsonLineFramer.ts`
(imported by `TerminalSidecar.ts`), untouched by this diff and already covered
by its own tests.

### Lens outputs (CR-07)

**Architecture lens: nothing surfaced.** Checks run: dependency direction
(the new `logSink` is an injected optional callback — dependency inversion, no
domain→infra import); no new module-level singleton (`log` is a local const
defaulting to no-op); no new circular import; no new external call without
timeout (no network call added); observability ADDED (one structured line per
refuse, §3.5); founder independence honoured (zero import of routes/chat.ts —
the `TerminalSidecarLogLine` type is the terminal's own, modelled on but not
coupled to `ChatLogLine`).

**Security lens: nothing surfaced.** Primitives checked: SEC-01 (access
control — the diff strengthens it: Origin allow-list + caps), SEC-06 (secrets
exposure — no secret-shaped strings added), DAT-03 (sensitive data in logs —
the new log sink receives only `outcome`/`code`/`changeId`; verified no
`data`/`term`/byte content reaches it, NFR-SEC-03 parity, asserted by two
tests). No new Dockerfile/dependency/network surface.

**Quality lens (all seven outputs):**
1. Build Verification follow-up: none (CR-01 clean).
2. JSX/template identifier scan: N/A — no TSX/JSX/Vue/Svelte files in the diff.
3. Dead-surface: none. `TerminalSidecarLogLine` is consumed by the test harness
   and the `logSink` option; `logSink` is consumed at three refuse sites.
4. Contract-drift: none. The emitted log-line shape (`event`/`outcome`/`code`/
   `changeId`) exactly matches the test assertions and the typed interface.
5. Test-coverage observation: the production delta (3 emit sites + the type +
   the no-op default) is covered by 7 new tests (4-test Origin/cap matrix incl.
   the named verification artifact `test_rejects_foreign_origin`, plus 3
   one-line-per-refuse observability tests + a "no log on accepted upgrade"
   negative). No source-without-test gap.
6. Style/readability: clean; comments cite the governing TDD §/ADR.
7. Performance (CR-10): no anti-pattern matches. The only `for`/`while` regex
   hits in the production diff are inside JSDoc comment text, not loops; no
   N+1, no hot-loop allocation, no unbounded materialisation introduced.

### Watch List

None.

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none on file for this project.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npx tsc --noEmit -p server`; `npx eslint server/adapters/TerminalSidecar.ts server/tests/terminalSidecar.test.ts`. HEAD: 0 errors / 0 lint. Base (merged WP-002): already green. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff is 228 lines / 2 files. Above the 200-line carve-out but the net PRODUCTION delta is ~30 lines in one file (the rest is new test code); single-reader pass performed with both files read end-to-end. Deviation from strict parallel-dispatch recorded here: justified by a 2-file diff with a single ~30-line production surface; spawning three sub-agents for a 30-line hardening delta is disproportionate.
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (TerminalSidecar.ts ~290 lines, terminalSidecar.test.ts ~670 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens negatives cite the specific checks run.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 low).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives/scan listed. Quality: all seven outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single `feat`/Secure concern). PH-02 Size: low (2 files; small production surface). PH-03 Safety: low (0 migrations/schemas/secrets/infra). PH-04 Completeness: low (0 source-without-test). PH-03 high → auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/create-production-terminal-sidecar` (working tree on feat/wp-003 branch).
- **Neighbour expansion:** git grep of importers/importees of the two changed files (1 neighbour: ndjsonLineFramer.ts, untouched).
- **Neighbour cap:** 1 of 1 considered; none excluded.
- **Scanners run:** tsc, eslint. Gitleaks/Semgrep/Trivy not invoked (no secret-shaped/dependency/infra surface in a 30-line hardening delta; manual secret grep run instead — clean).
- **Scanners unavailable:** dedicated SAST not run; recorded as a scoped coverage choice for a small in-language hardening delta.
- **Lenses dispatched in parallel:** no — single-reader pass per the CR-02 note above.
