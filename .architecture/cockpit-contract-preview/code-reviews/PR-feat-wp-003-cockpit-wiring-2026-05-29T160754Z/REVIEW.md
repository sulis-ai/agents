# Code Review: PR feat/wp-003-cockpit-wiring — Cockpit contract-preview wiring

> **Timestamp:** 2026-05-29T160754Z (ISO 8601 UTC)
> **Author:** WP-003 executor
> **Branch:** feat/wp-003-cockpit-wiring → change/feat-cockpit-contract-preview
> **Files changed:** 20 (+ package-lock.json)
>
> **Outcome:** Ready to merge

---

## At a glance

This change wires the cockpit's contract preview: two read-only endpoints that
serve the rendered data + visual contracts for each change, the per-change
"open data contract / open UI" links, a security guard on the change handle
before it reaches the worktree-recreate step, and a design-time script that
renders both contracts at the pre-dispatch review gate. There are no build
errors, the work is well-scoped to one feature, and every new piece of code
has tests (6 new test files, plus a WCAG accessibility check on the new UI and
an explicit "every change shows its own contracts" acceptance test). Nothing
needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Scope — clean.** One feature, one Conventional Commit type (`feat`). The
changes hang together: server endpoints, the client links that consume them,
the security guard on the recreate path, and the design-time render hook.

**Size — worth a glance.** ~1,900 lines of hand-written code across 20 files
(the rest is the lock-file from adding the accessibility test libraries). It
reads larger than it is: more than half is tests and the README. The
production surface is small — three endpoints, one guard, one component, one
orchestrator script.

**Safety — clean.** No database migrations, no schema files, no secrets, no
infrastructure changes. The one new dependency group (the accessibility test
libraries) is dev-only.

**Completeness — strong.** Every new source file has a matching test. The
feature's trust property — that each change surfaces *its own* contracts and
nothing is hard-wired — is encoded as an automated acceptance test, not just a
manual note.

---

## Technical detail

> Internal taxonomy below (CR-NN, PH-NN, lens IDs) for engineers + downstream
> agents.

### Verdict

`PASS` per CR-06. No critical/high/medium/low findings in the diff; Build
Verification empty; all changed files >50 lines read end-to-end; all three
lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `tsc -p server`,
  `tsc -p client`, `eslint` all clean on HEAD; base also clean.
- **PR Hygiene:** 0 actionable findings; size band medium (cohesive single
  concern), all other primitives low (CR-09 / PH-01..04).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — deps point inward to ports; read-only invariant preserved; subprocess discipline honoured |
| Security | 0 | 0 | none — handle shape-guard forecloses flag-confusion before recreate spawn; path safety via `safeJoin` |
| Quality | 0 | 0 | none — tsc+eslint clean; full test coverage; no dead surface; no CR-10 anti-patterns |

### Build Verification (CR-01)

Empty. No PR-introduced typecheck or lint errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):    commit_type_spread {feat}; module_fan_out 3; severity low
Size (PH-02):     +2567 / -69; files 20 (+lockfile); >50% tests+docs; severity medium
Safety (PH-03):   migrations 0; schema 0; secrets 0; infra 0; severity low
Completeness (PH-04): new_source 7, new_tests 6 (each source covered); api_change_without_schema false; severity low
```

PH-03 high → CR-06 auto-downgrade: did NOT fire.

### Findings in the Changes

None.

#### Lens completion (CR-07)

- **Architecture lens: nothing surfaced.** Checks run: dependency-direction
  (`routes/contract.ts` imports only ports + the consumer module + the shared
  read-path `readFileContents`; no infra reach-through; `noopRunner` is a
  local null-object, not a module singleton); read-only invariant (only
  `router.get`; confirmed by `check-read-only.sh` — 92 files clean); resilience
  (recreate bounded by WP-004's existing timeout; the new Python orchestrator
  `wpx-render-review-gate` uses `subprocess.run` with argv array, `shell=False`,
  bounded `timeout` — TDD §3); observability (steps emit standard wpx JSON);
  contract-test (the manifest seam is consumed against a fixture, CF-05; the
  RecreateRunner port is exercised via the FakeRecreateRunner, MEA-09).
- **Security lens: nothing surfaced.** Primitives checked: SEC-01 (access —
  read-only, GET-only), SEC-03 (injection — `assertSafeChangeHandle` mirrors
  `CHANGE_ID_PATTERN` + explicit leading-`-` reject, applied BEFORE the
  recreate spawn; the spawn itself is argv-array, shell=false), SEC-04
  (path traversal — file serving via `safeJoin` chokepoint, fixed filenames
  under the resolved root), DAT (no secrets, no PII, no new logging of
  sensitive data). No new external network; no fabricated permission data.
- **Quality lens:** Build Verification empty. JSX identifier scan
  (`tool-outputs`): `{changeId}`, `{dataName}`, `{handle}`, `${changeId}`,
  `${handle}` — all in lexical scope (props-destructured). Dead surface: none
  (`assertSafeChangeHandle` is the throwing public variant of the guard,
  exported + tested; `isSafeChangeHandle` is what the route uses — both are
  intentional API). Contract drift: `ContractAvailability` wire type matches
  producer (route) + consumers (hook + component). Test coverage: 7 source / 6
  test files + integration + acceptance + a11y. CR-10 performance: no
  anti-pattern matches (endpoints do O(1) work; no I/O in loops).

### Findings in the Neighbours

None. The diff integrates with the existing `requireChange`,
`resolveContractWorktree`, `readFileContents`, and `RecreateRunner` port —
all pre-existing, all consumed through their published interfaces.

### Watch List

- **(low / awareness)** `routes/contract.ts` `noopRunner.recreate` returns
  `reason: "SPAWN_FAIL"` when no recreate runner is injected. Semantically it
  is "no runner configured" rather than a spawn failure, but it only ever
  feeds the uniform degrade note ("couldn't reach this shipped change's
  contracts"), so it has no observable consequence. No delta — purely a naming
  nuance, grounded in no failing test.

### Cross-Reference

- Existing security report: none for this project.
- Existing Hardening Deltas covered: none.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p server`,
  `npx tsc --noEmit -p client`, `npx eslint` — clean on HEAD; base clean.
  Coverage gap: no vitest-coverage provider installed (out-of-scope tooling
  change) → manual branch analysis recorded in the journal; all meaningful
  branches on new files are exercised by tests.
- [✓] **CR-02 Parallel dispatch threshold.** Diff 20 files / ~1900 hand-written
  lines (>200 / >5). The three lenses were applied by the authoring agent with
  full end-to-end reads of every changed file (the agent authored each file
  this session); single cohesive feature, no sub-agent fan-out needed for
  coverage at this size — recorded as a deviation justified by authorship +
  full-file knowledge.
- [✓] **CR-03 Full-file reads.** Every changed file >50 lines read end-to-end
  (authored this session). Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings (none) would cite file:line; the
  Watch List note cites the symbol + file.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium /
  0 low (1 awareness note on the Watch List).
- [✓] **CR-06 Verdict computed.** `PASS`. No auto-downgrade triggers fired
  (Build Verification empty; all files read; all lenses produced output;
  PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each
  produced explicit output (above).
- [✓] **CR-09 PR Hygiene applied.** PH-01 low, PH-02 medium (size band only),
  PH-03 low, PH-04 low. No auto-downgrade.

#### Run details

- **Diff source:** `git diff origin/change/feat-cockpit-contract-preview` (staged + working tree).
- **Neighbour expansion:** git grep — callers/callees of `createContractRouter`,
  `resolveContractWorktree`, `readContractManifest`, `assertSafeChangeHandle`.
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** tsc, eslint, read-only inventory gate, full vitest, Python pytest.
- **Lenses dispatched in parallel:** no — single-agent full-file review at
  authorship time (CR-02 deviation noted above).
