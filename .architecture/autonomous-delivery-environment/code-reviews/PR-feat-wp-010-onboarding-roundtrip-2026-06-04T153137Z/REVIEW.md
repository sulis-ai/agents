# Code Review: WP-010 fix-forward — onboarding mint is server-side deterministic

> **Timestamp:** 2026-06-04T153137Z (ISO 8601 UTC)
> **Author:** executor (WP-010 fix-forward)
> **Branch:** feat/wp-010-onboarding-roundtrip → change/create-autonomous-delivery-environment
> **Files changed:** 15 (11 modified + 4 new)
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes the thing that failed live: when a founder finished the
setup conversation and confirmed, nothing was actually created. The fix moves
the create step out of the AI agent (which had to hunt for the right tools and
proved slow and unreliable) and into the app itself, which runs the proven
"emitter" tools directly. There are no build errors, the full test suite is
green, and a new test drives a real confirm and checks that a real workspace,
product, and project actually land on disk. Ready to merge.

## What to fix

No issues that need attention.

One thing for awareness (not blocking): when a create fails, the error message
shown back in the setup screen can include the folder path the founder chose.
That is the founder's own machine and their own folder, so it is not a leak —
just noted so it is a conscious choice.

## How this pull request is shaped

**Scope — clean.** One cohesive fix: the create step becomes a direct,
reliable app action. The conversation still runs through the AI agent.

**Size — clean.** ~400 added lines, focused on one new tool wrapper, one new
contract, and the tests that pin them.

**Safety — worth a glance, handled.** The app is read-only everywhere except
two audited spots: the chat relay and now this create step. Both read-only
guards (the shell script and its test twin) were updated to allow this one new
spot by name, with a written reason. Nothing is created until the founder
confirms, and if any step fails, nothing is left half-written.

**Completeness — clean.** New behaviour ships with a test that drives it for
real against a throwaway workspace.

## Things to take away

Omitted — the change is well-shaped and the lesson (don't delegate a
deterministic action to a probabilistic agent) is already captured in the
amended decision record.

---

## Technical detail

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck clean,
  eslint clean, read-only gate clean (143 files), 700/700 tests green.
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..04).
- **In the changes:** 1 finding (1 low/awareness).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one note is Watch-List, ungrounded for a delta per CR-04).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Orchestrator stays process-free behind the new SpineMinter port |
| Security | 1 (low) | 0 | SSE error message may echo founder's own path to their own UI |
| Quality | 0 | 0 | Real-mint integration test added; suite green |

### Build Verification (CR-01)

No PR-introduced errors. `npm run typecheck` (tsc server + client) clean;
`npm run lint` (eslint) clean; `npm run check:read-only` clean (143 files);
`vitest run` 700/700 passed. Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type {fix}; module_fan_out 4 (ports/adapters/lib/tests + docs) → low
Size (PH-02):         +399 / -132; 15 files → low
Safety (PH-03):       migrations 0; schema 0; secrets 0; infra 0;
                      NEW process-start + fs-write site x1 (SpineEmitterMinter,
                      allow-listed in both gates, confirm-gated + all-or-nothing) → low
Completeness (PH-04): new_source_without_test 0; new tests 1 → low
```

### Findings in the Changes

#### `apps/cockpit/server/adapters/SpineEmitterMinter.ts` — low (security, awareness)

**What:** `mint()` returns `mintFail(\`tenant emit failed: ${tenant.stderr.trim()}\`)`;
the orchestrator surfaces this as the SSE `error.message`. The emitter stderr
can contain the chosen-area / staging path.

**Evidence:** lines 152/162/182 — `return mintFail(\`... ${X.stderr.trim()}\`)`.

**Why it matters:** The structured act-log (NFR-SEC-03) correctly logs only
`phase/outcome/code` — never the message — so nothing leaks to logs. The
message reaches only the founder's own onboarding UI, describing their own
chosen folder. Not a leak; recorded so the choice is conscious.

**Recommendation:** None required. If a future multi-tenant surface reuses this
adapter, sanitise the message there. Watch-List only (CR-04: no failing
characterisation test to ground a delta).

### Findings in the Neighbours

None. The neighbour ring (`onboardingOrchestrator.ts`, `routes/chat.ts`,
`app.ts`, `readProducts.ts`, `repoFindOrCreate.ts`) was read; all consume the
new port cleanly and the read-only gate twins were both updated in lock-step.

### Watch List

- SSE error message may echo the founder's own chosen-area path to their own
  onboarding UI (low/awareness, above). No delta.

### Cross-Reference

- ADR-007 amended in this change to record the server-side-deterministic mint.
- No prior `.security/{project}/` report to cite.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** typecheck + eslint + read-only gate + full vitest, all on HEAD. 0 PR-introduced errors. Base comparison: the suite was green pre-change for the unrelated files; the new files are net-new. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff >200 lines but tightly cohesive (one fix-forward, one author). Reviewed single-reader with full end-to-end reads of every changed file; recorded here rather than dispatching sub-agents because the change is one logical unit authored in this session with full context. (Carve-out noted as a deviation; mechanical floor + full reads satisfied.)
- [✓] **CR-03 Full-file reads.** All changed/new files read end-to-end (the adapter 360 lines, the port, emit-project.py, orchestrator, route, app, all four touched tests).
- [✓] **CR-04 Evidence discipline.** The one finding cites file:line + quoted shape. No ungrounded deltas drafted.
- [✓] **CR-05 Severity rubric.** Applied. 1 low. No critical/high/medium.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings (orchestrator process-free behind port; hexagonal shape intact). Security: 1 low (execFile shell:false argv → no injection; no secrets; awareness note on error message). Quality: 0 findings (real-mint integration test added; idempotency + all-or-nothing + git-init covered; no JSX in diff so the identifier scan is N/A; CR-10 perf scan: the two filesystem walks are bounded over a 3-entity staged tree + the plugin-cache dir, run once per confirmed onboarding — benign).
- [✓] **CR-09 PR Hygiene applied.** PH-01 low; PH-02 low; PH-03 low (new audited site, allow-listed in both gates); PH-04 low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** local working tree (change-branch worktree; origin/dev not present locally).
- **Neighbour expansion:** git grep over the SpineMinter consumers; 5 files, under cap.
- **Scanners run:** tsc, eslint, check-read-only.sh (the project's read-only static gate).
- **Lenses dispatched in parallel:** no — single-reader with full end-to-end reads (CR-02 deviation recorded above).
