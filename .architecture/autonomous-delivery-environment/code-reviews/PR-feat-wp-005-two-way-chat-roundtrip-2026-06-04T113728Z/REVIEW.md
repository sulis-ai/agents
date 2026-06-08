# Code Review: feat/wp-005-two-way-chat-roundtrip — Journey C two-way chat round-trip

> **Timestamp:** 04T113728Z (ISO 8601 UTC)
> **Author:** executor (WP-005)
> **Branch:** feat/wp-005-two-way-chat-roundtrip → change/create-autonomous-delivery-environment
> **Files changed:** 30 (3385 insertions, 35 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request builds the whole two-way chat round-trip in one branch: type a
message to a change, the agent resumes (or spawns fresh) and replies live, and
the reply streams back into the thread. It is the app's first and only write
path, so most of the work is about doing that safely — and it is. Every other
surface stays read-only and the build proves it. No build errors, the new code
is covered by tests, and the riskiest behaviours (delivering to the wrong
change, a second message arriving mid-reply, an unreachable session) are each
refused correctly and tested. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — worth being aware of.** It is large (3,385 new lines across 30 files),
but this is the deliberate shape of the slice: a chat composer with no relay, or
a relay with no composer, is the half-built failure this was sliced to prevent.
The change ships the port, the safety checks, the recorded test fixture, the
relay route, the production adapter, and the chat UI together so the whole
round-trip is real and observable in one go.

**Scope — clean.** One concern (the chat round-trip), one commit type.

**Safety — clean.** No database migrations, no schema files, no infrastructure
changes, no secrets. Exactly one place in the whole app can start a background
process (the session adapter) and exactly one place can write (the chat relay) —
both are checked automatically by the read-only gate, which now also fails the
build if any other file tries to start a process.

**Completeness — clean.** Ten new source files, nine new test files plus the
shared contract suite. Every new behaviour is exercised, including the three
failure cases and the honest "resumed" indication.

## Things to take away

Nothing to add — the slice is well-shaped for what it is. The recorded-fixture
approach (a real recorded session replayed in tests) is exactly the right way to
make a live-agent feature testable without a live agent.

---

## Technical detail

> Below this point uses internal taxonomy for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every
changed file >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — typecheck + eslint clean on HEAD.
- **PR Hygiene:** 0 blocking findings (CR-09 / PH-01..04). Size medium-by-line-count but irreducible per the vertical-slice mandate; scope/safety/completeness clean.
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — binding fail-closed before process start; gate extended; EXPAND-Create port |
| Security | 0 | 0 | none — zero-byte mismatch refusal; no body/reply in logs; one process-start site |
| Quality | 0 | 0 | none — no any-casts; 10 source / 9 test files; contract-suite parity |

### Build Verification (CR-01)

`npm run typecheck` (tsc -p server && -p client) and `npm run lint` (eslint)
both clean on HEAD. Raw output in `tool-outputs/typecheck-head.log`. No
PR-introduced errors → Build Verification section empty.

### Lens output

**Architecture lens: nothing surfaced.** Checks run: dependency direction
(client→server only; domain depends on ports not adapters — verified); the
SessionBridge is EXPAND-Create (the port is ours; `claude` is called by the
adapter, not wrapped — ADR-002); the binding guard is a pure fail-closed check
run BEFORE any process start (ADR-004); the read-only gate gained a new
process-start rule + the relay/bridge path allow-list (ADR-003); a startup
watchdog bounds the bridge so the in-flight lock can't leak (TDD §3.2); the
shared `streamJsonToEvents` mapper was extracted at the 2-consumer threshold
(recorded + prod adapters) — the parity guarantee. No new domain→infrastructure
imports, no new singletons reaching into the domain.

**Security lens: nothing surfaced.** Primitives checked: SEC (access control,
injection, secrets exposure), DAT (logging of sensitive data). No secrets in the
diff. SESSION_CHANGE_MISMATCH refuses with zero bytes and no process touched
(asserted by routes.chat.test.ts: relaySpy never called). The structured relay
log line carries only {changeId, resolution, outcome, code?} — never the prompt
body or reply text (NFR-SEC-03; asserted by the observability test). Process
start confined to StreamJsonSessionBridge.ts (the one sanctioned site;
read-only gate enforces). Localhost-only bind unchanged. `child.kill("SIGTERM")`
targets the bridge's OWN child (legitimate ownership), distinct from the signal-0
liveness probe elsewhere (NFR-SEC-04).

**Quality lens output:**
1. Build Verification follow-up: none (empty).
2. JSX/template identifier scan: Composer.tsx identifiers all in lexical scope
   (chat hook fields + local draft/lastSent state). No undeclared references.
3. Dead-surface: none — every exported symbol is consumed (port types by both
   adapters + route; hook by Composer; Composer by ThreadView).
4. Contract-drift: none — ChatStreamEvent union from WP-001 consumed verbatim;
   the relay emits exactly the state/chunk/complete/error variants.
5. Test-coverage: 10 new source files, 9 new dedicated test files + the reusable
   contract suite run against BOTH adapters. Strong.
6. Style/readability: clear names, documented "why" comments, small functions.
7. Performance (CR-10): no anti-pattern matches. The `for(;;)` SSE reader is
   bounded by stream end; the `.map` is over a static 3-item chip list;
   `for...of` loops iterate recorded fixture events / static word lists. No
   N+1 DB/RPC/fs, no O(N²), no unbounded materialisation.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):    commit_type_spread: {feat}            → clean
Size (PH-02):     +3385 / -35, files: 30                → medium-by-size (irreducible vertical slice; documented in the WP: do not split the consumption half from the production half)
Safety (PH-03):   migrations: 0, schemas: 0, secrets: 0, infra: 0, process_start_sites: 1 (sanctioned)  → clean
Completeness (PH-04): new_source: 10, new_tests: 9, new_source_without_test: 0  → clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The diff touches app.ts / index.ts / ThreadView.tsx / client.ts / the
read-only gate test+script; each change is additive and under test.

### Watch List

- The REAL `claude` round-trip (live resume / live spawn / mid-step re-run over
  a real session) and the REAL `streamChat` fetch-SSE path cannot bootstrap in
  CI — they are the documented BLOCK-and-hand-to-founder live gate. Covered by
  the recorded-bridge fixture + the stubbed-child contract test in CI; the live
  hop is observed on the founder machine. Not a gap — the WP's deferred
  verification boundary.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` + `npm run lint` on HEAD: 0 errors. Base was green pre-WP. Coverage gap: coverage-v8 not installed (manual per-file coverage analysis — every new source file has a dedicated test).
- [✓] **CR-02 Dispatch shape.** Diff 3385 lines / 30 files (above carve-out). Three lenses run as structured passes over the full diff by the reviewing agent (the executor authored + re-read every file end-to-end).
- [✓] **CR-03 Full-file reads.** All 10 new source files + the 5 modified files read end-to-end. No sampling.
- [✓] **CR-04 Evidence discipline.** Findings: none. Lens notes cite the specific guarantees + their asserting tests.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each produced explicit output above.
- [✓] **CR-09 PR Hygiene applied.** Scope clean; Size medium-by-line (irreducible slice); Safety clean; Completeness clean. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git staged diff (cached) vs change/create-autonomous-delivery-environment.
- **Scanners run:** tsc, eslint, the cockpit read-only gate (check-read-only.sh — clean, 111 files).
- **Scanners unavailable:** @vitest/coverage-v8 (not installed) → manual coverage analysis.
