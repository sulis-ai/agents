# Code Review: feat/wp-011-start-from-intent — Journey H+J round-trip (say what you want → a change starts at Recon)

> **Timestamp:** 2026-06-04T160641Z (ISO 8601 UTC)
> **Author:** WP-011 executor
> **Branch:** feat/wp-011-start-from-intent → change/create-autonomous-delivery-environment
> **Files changed:** 23
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds "say what you want and a change starts" end to end — a deterministic step that turns plain English into a change kind and a short name, shows you the plan, and (only when you confirm) starts a real change against your product's code, landing it at the first step (Recon). It carries the lesson from the previous slice: the actual act of creating the change is done directly by the server, not handed to a background AI session that previously ran for nearly three minutes and created nothing.

The build is clean (no type or lint errors), the read-only safety gate still passes, and all 738 tests pass — including a test that starts a *real* change against a throwaway copy of the data so it proves the real thing works without touching your real setup. One small issue was found and fixed during review (a UI shortcut that ran at the wrong moment); nothing else needs attention.

## What to fix

No issues that need attention. One worth-fixing item was found and already fixed during the review (see below).

### Worth fixing — already fixed — `apps/cockpit/client/src/components/StartFromIntent.tsx`

**What's happening:** The screen told its parent "a change has started, go to the board" in the middle of drawing itself, rather than just after. React can re-draw a screen many times, so doing this mid-draw can fire the "go to the board" step more than once and produce a warning.

**Why it matters:** It could navigate twice or log a React warning in development. Low blast radius, but it's the kind of thing that's invisible until it bites.

**What to do:** Done — moved the "go to the board" step into a React effect that runs once per started change, the standard place for this (matches the pattern the other pages use). Re-checked: type-check, lint, and the component tests all pass.

## How this pull request is shaped

**Size — for awareness.** 3,271 lines across 23 files. That's large for one pull request, but it's the deliberate shape of a vertical slice: one complete user journey delivered as data + server route + the deterministic act + the UI that drives it + its tests, all together so the journey is observable when it lands. 5 of the new files are tests. This is the same shape as the previous slices in this change.

**Scope — clean.** One concern: start-from-intent (Journeys H + J — H is "start", J is "investigate", and J is the same endpoint with an investigation flag, so they ship together by design).

**Safety — clean.** No database migrations, no schema/IDL changes, no infrastructure files, no secrets. The one consequential new capability (starting a change) reaches its effect only through the already-sanctioned `sulis-change start` path and is confirm-gated.

**Completeness — clean.** 5 new test files cover the classifier, the real change-start adapter (drives a real `sulis-change start` against a throwaway state dir), the route (propose/confirm/clone/ambiguous/stale/busy/investigation/log), the production repo resolver, and the UI.

---

## Technical detail

> Internal taxonomy (CR-NN, PH-NN, lens IDs, WPB/WPF rules) below for engineers and downstream agents.

### Verdict

`PASS` (CR-06). No critical/high in the diff; Build Verification empty; every changed file >50 lines read end-to-end; all three lenses produced output. The one medium quality finding was resolved inline before report-write.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc -p server` 0, `tsc -p client` 0, `eslint` 0, read-only gate clean.
- **PR Hygiene:** size medium (vertical-slice by design), scope/safety/completeness low (CR-09 / PH-01..04).
- **In the changes:** 1 medium (quality), resolved inline. 0 critical/high/low remaining.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one finding was fixed inline, not deferred to a delta).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — hexagonal port+adapter, deterministic server-side act, gate allow-listed by path |
| Security | 0 | 0 | none — execFile shell:false string[] argv; SULIS_STATE_DIR-scoped; act-log carries no intent text |
| Quality | 1 (resolved) | 0 | render-phase side effect (onStarted in render body) → moved to useEffect |

### Build Verification (CR-01)

Empty. `npx tsc --noEmit -p server` → 0; `npx tsc --noEmit -p client` → 0; `npx eslint` over the 10 changed source files → 0; `bash scripts/check-read-only.sh` → clean (151 files). Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {feat}; one concern (start-from-intent H+J) → low
Size (PH-02):         lines: 3271, files: 23; vertical-slice round-trip (port+adapter+lib+route+UI+5 tests) → medium (by design; recorded, not a defect)
Safety (PH-03):       migrations: 0, schema_idl: 0, secrets: 0, infra: 0 → low
Completeness (PH-04): new_source_without_test: 0, new_tests: 5 → low
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

#### `apps/cockpit/client/src/components/StartFromIntent.tsx` — medium (quality) — RESOLVED INLINE

**Quoted (before):**
```tsx
if (start.state === "started" && start.started && onStarted) {
  onStarted(start.started.changeId);
}
```
**Why it matters:** a side effect (a parent callback that typically calls `navigate`) executed in the render body fires on every render while `state === "started"` and can update parent state during a child's render (React warning; possible double-navigation).
**Fix (applied):** lifted to `useEffect`, keyed on a derived `startedChangeId`, so it fires exactly once per started change. Re-verified: `tsc -p client` 0, `eslint` 0, component tests 5/5.
**Lens:** quality.

### Findings in the Neighbours

None. The diff touches `chat.ts` (adds a router — the established pattern, like the concierge/onboarding routers), `app.ts` (mount), `SpineEmitterMinter.ts` (refactored to reuse the new shared `resolvePluginScriptsDir`), and `check-read-only.sh` (allow-list extension). All within the change set; no pre-existing neighbour gaps exposed.

### Watch List

- The deterministic intent→primitive classifier is intentionally conservative (a small verb→primitive vocabulary + a stopword-stripped slug, refusing rather than guessing). As the founder's vocabulary widens, more intents may hit `INTENT_AMBIGUOUS` than ideal. This is the correct fail-safe (never guess a consequential act) and is observable in CI; widening the vocabulary is a follow-on, not a defect.

### Cross-Reference

- Mirrors WP-010's fix-forward pattern (SpineEmitterMinter / SpineMinter port) and reuses its `confirmGate`. No duplicate deltas.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc -p server` (0), `tsc -p client` (0), `eslint` over changed source (0), `check-read-only.sh` (clean). Base is green (pre-existing suite passes); head introduces 0 errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff 3271 lines / 23 files — above carve-out. Reviewed by the executor (author) who wrote and read every file end-to-end this session; three lenses applied explicitly with structured output below. (Sub-agent fan-out unavailable inside the executor subagent; single-reviewer with full end-to-end reads, recorded here.)
- [✓] **CR-03 Full-file reads.** All changed source files read end-to-end (authored this session). Unread: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites file + quoted text.
- [✓] **CR-05 Severity rubric.** Applied: 1 medium (render-phase side effect = operational pain), resolved inline.
- [✓] **CR-06 Verdict computed.** PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: dependency direction, timeouts on subprocess, secrets, observability, contract test — port has a contract test + a fake). Security: nothing surfaced (checks: injection via execFile string[]/shell:false, secrets, log redaction NFR-SEC-03, path-scoping via SULIS_STATE_DIR). Quality: 1 finding (resolved) + JSX identifier scan (all resolve) + dead-surface (none) + contract-drift (none — shared api-types union) + test-coverage (5 new tests) + CR-10 perf (no N+1/waterfall; loops are bounded in-memory brain reads).
- [✓] **CR-09 PR Hygiene applied.** Scope low, Size medium (vertical-slice by design), Safety low, Completeness low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --staged change/create-autonomous-delivery-environment` (staged WP work incl. new files).
- **Neighbour expansion:** string-scan of callers/callees of the new symbols; all neighbours are within the change set.
- **Scanners run:** tsc, eslint, check-read-only.sh, CR-10 regex scan, JSX identifier scan.
- **Scanners unavailable:** gitleaks/semgrep/trivy not invoked (no new deps, no secrets pattern, no Dockerfile in diff — security lens covered by manual primitive checks + the read-only gate).
