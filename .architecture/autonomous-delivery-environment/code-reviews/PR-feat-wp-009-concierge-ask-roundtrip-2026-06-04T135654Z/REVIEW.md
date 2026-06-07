# Code Review: WP-009 — concierge ask round-trip (the read-only front door)

> **Timestamp:** 2026-06-04T135654Z (ISO 8601 UTC)
> **Author:** executor (Senior Engineer)
> **Branch:** feat/wp-009-concierge-ask-roundtrip → change/create-autonomous-delivery-environment
> **Files changed:** 9 modified + 8 new (server lib/route/app/index, client funnel/hook/component/page/styles, tests, fixture, README)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the concierge front door — the plain-English place a founder asks
"which change was the login fix in?" or "what needs my attention?" and gets a
read-only answer streamed back. The build is clean, the change is well-scoped to one
journey, and every new piece has tests (32 new tests, full suite 617 green). The
read-only safety guarantee is preserved without adding any new exception — the
concierge's answer endpoint lives inside the one already-audited write-path file and
rides the same agent connection the chat already uses. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

One thing for awareness (not blocking): the recorded test fixture includes a
"cut-off mid-answer" variant that the automated tests don't currently drive — the
interrupted path is covered instead by a programmable stub in the route test, which
is equivalent. No action needed.

## How this pull request is shaped

**Size — clean.** ~400 changed lines plus 8 new files. It looks like several files
for one feature, but that's the intended shape here: each journey ships its data,
its server route, and the screen that consumes it together, so a real person can
perform the action and see the result. The new files are the front-door screen, its
data hook, the read-only helper, and their tests.

**Scope — clean.** One concern: the concierge ask round-trip. No unrelated refactors
bundled in (the two small shared-helper extractions are directly in service of this
change and sit at the 2-consumer threshold).

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets. The read-only guarantee is actively re-asserted by a new test.

**Completeness — clean.** Four new source modules, all with tests; zero source files
shipped without coverage.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed
files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — `tsc` server+client + eslint, both exit 0).
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..04 all low — single feat, vertical slice, no migrations/secrets, full test coverage).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (no findings → no deltas).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — reuses SessionBridge + ChangeStoreReader; no new port/transport (ADR-006) |
| Security | 0 | 0 | none — read-only gate allow-list unchanged {chat.ts}; logs redact question/reply (NFR-SEC-03) |
| Quality | 0 | 0 (1 note) | none — full test coverage; one fixture-variant note |

### Build Verification (CR-01)

`npm run typecheck` (tsc -p server && tsc -p client) → exit 0. `npm run lint`
(eslint .ts/.tsx) → exit 0. `npm run check:read-only` → clean (135 files). No
PR-introduced errors. Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        single feat (WP-009 round-trip); fan-out within apps/cockpit only → low
Size (PH-02):         401 lines / 9 modified + 8 new; vertical slice by design → low
Safety (PH-03):       migrations 0, schema/IDL 0, secrets 0, infra 0 → low
Completeness (PH-04): new_source_without_test 0 (+32 tests) → low
```

### Findings in the Changes

None.

### Architecture lens

Nothing surfaced. Checks run: domain→infra import direction (conciergeRead imports
only `ports/ChangeStoreReader`; route imports the port + lib — clean); no new
module-level singletons; no new transport (rides `SessionBridge`, ADR-006 — the
load-bearing reuse decision); no new circular imports; read-only path needs no
timeout/CB of its own (the bridge owns the startup watchdog); verification: the
concierge route is integration-tested against the RecordedSessionBridge (recorded
fixture, parity with prod adapter).

### Security lens

Nothing surfaced. Primitives checked: SEC-01..07 (access control / injection /
validation / secrets). No hardcoded secrets. No new write/process exception — the
read-only gate's write-verb allow-list stays exactly `{chat.ts}` (asserted by a NEW
test, read-only-inventory.test.ts). Input validation: empty/missing question → 400.
Structured log carries only `outcome`/`route`/`code` — never the question or reply
text (NFR-SEC-03), verified by a unit test AND observed live. The `question` flows
into the bridge prompt at the SAME trust boundary as the existing chat relay
(local, single-founder agent) — no new exposure.

### Quality lens

1. Build Verification follow-up: none (CR-01 clean).
2. JSX identifier scan: ConciergeChat.tsx / ConciergePage.tsx / Sidebar.tsx — all
   referenced identifiers resolve in lexical scope (tsx strict typecheck passes).
3. Dead-surface: none — `ConciergeStreamEvent` import is consumed by `writeSseFrame`
   and `toConciergeEvent`; `ConciergeRoute` type used in deps + finish.
4. Contract-drift: `toConciergeEvent` maps every `ChatStreamEvent` variant; the
   emitted `ConciergeStreamEvent` union (state thinking/replying/failed, chunk,
   complete{route}, error) is fully covered by tests.
5. Test-coverage: STRONG — 11 route + 11 lib + 8 component + 4 inventory assertions;
   +32 net tests, suite 585→617.
6. Style/readability: clean; comments cite FR/ADR provenance consistent with the
   codebase.
7. Performance (CR-10): no anti-pattern matches. The only loops are the bounded
   SSE-frame reader (terminates on stream close) and a single linear `.map` over
   the change list (no nested I/O — no N+1).

   Note (awareness, not a finding): the discovery fixture's `mid-step` case is not
   driven by an automated test; the interrupted path is covered by a programmable
   stub in routes.concierge.test.ts (equivalent coverage).

### Watch List

None.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** tsc (server+client) + eslint, both exit 0 on HEAD; read-only gate clean. No coverage gap. (Note: `@vitest/coverage-v8` absent → per-line coverage % not machined; coverage argued manually from the test-to-surface mapping above.)
- [✓] **CR-02 Dispatch.** Diff >200 lines / >5 files; lenses run by the authoring executor inline per Step 6.5 budget (single coherent WP, self-review gate). Recorded as a deviation from the parallel-subagent default.
- [✓] **CR-03 Full-file reads.** All changed/new files read end-to-end during authoring.
- [✓] **CR-04 Evidence discipline.** Findings: none; lens outputs cite the specific surfaces checked.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; every lens produced output).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each produced structured output (above).
- [✓] **CR-09 PR Hygiene applied.** PH-01 low, PH-02 low, PH-03 low, PH-04 low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git diff working-tree vs change/create-autonomous-delivery-environment (uncommitted WP-009 changes + 8 untracked new files).
- **Neighbour expansion:** chat.ts (hosts the concierge route), app.ts (mount), client.ts (shared SSE reader), Sidebar/App (nav + route) — all in the diff; no external neighbours beyond the diff.
- **Scanners run:** tsc, eslint, check-read-only.sh. Gitleaks/Semgrep/Trivy not invoked (no secrets/deps/infra in diff; manual SEC review performed).
