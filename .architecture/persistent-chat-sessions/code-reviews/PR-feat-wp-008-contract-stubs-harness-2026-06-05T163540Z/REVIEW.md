# Code Review: WP-008 — Contract-stub fixtures (§2.10) + contract-test harness

> **Timestamp:** 2026-06-05T163540Z (ISO 8601 UTC)
> **Author:** executor (WP-008)
> **Branch:** feat/wp-008-contract-stubs-harness → change/refactor-persistent-chat-sessions
> **Files changed:** 11 (635 insertions, 0 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the conformance test suite that proves the session manager
behaves the way its contract promises — seven recorded scenarios driven against
the real manager, no fakes of the manager's own moving parts. It is test code
and recorded fixtures only; it touches no production behaviour. The build is
clean, every scenario passes, and the suite is well-shaped (each test reads as
the scenario it proves, not the setup around it). Nothing needs attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 635 added lines across 11 files, all of it test code and
recorded fixtures. Large for a single file (the harness is ~515 lines) but that
is one cohesive suite of nine scenario tests plus a shared replay child — not
mixed concerns.

**Scope — clean.** A single concern: the contract-conformance suite. One commit
type (`test:`).

**Safety — clean.** No migrations, no schema/IDL files, no infrastructure files,
no secret patterns. The only non-test edit is registering a pytest marker in
`pyproject.toml`.

**Completeness — clean.** This *is* the test work; it adds 1 test module + 8
recorded fixtures + a fixtures README. No source-without-test gap.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the
one changed file >50 lines (the harness) read end-to-end; all lenses produced
output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — ruff check + ruff format clean)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — MEA-09 satisfied (real manager, recorded fixtures, no internal mocks) |
| Security | 0 | 0 | None — test-only diff, no auth/IO/secret surface |
| Quality | 0 | 0 | None — suite green, well-factored, lint clean |

### Build Verification (CR-01)

Mechanical baseline: `ruff check` + `ruff format --check` on the new test
module — both clean (see `tool-outputs/`). No typechecker configured for this
stdlib-only scripts package (mypy/pyright absent from pyproject); coverage gap
noted. The suite itself is the strongest mechanical check: 9/9 contract tests
pass against the real manager.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread: {test}; module_fan_out: 1 (tests/)        → clean
Size (PH-02):        lines_added: 635, removed: 0, files: 11; generated_ratio: 0    → note (single cohesive suite)
Safety (PH-03):      migrations: 0; schema_idl: 0; infra: 0; secret_hits: 0         → clean
Completeness (PH-04): new_source_without_test: 0 (this IS the test WP)              → clean
```

### Findings in the Changes

None.

### Architecture lens

Nothing surfaced. Checks run: dependency-direction (test imports only the public
`_session_manager` surface + the real `ClaudeAdapter`); contract-test gap (this
IS the contract suite — §2.10 #1..#7 each have a test); mock discipline (MEA-09 —
the real `SessionManager` is driven; the only fixture-specific code is the replay
child, which replays *recorded reality* over a real subprocess, decoded by the
real adapter — no mock of the manager's own internals). The `_running_manager`
helper is the correct extraction at the 2-consumer threshold (EP-03).

### Security lens

Nothing surfaced. Primitives checked: SEC-01..07 (no auth/access/injection
surface — test-only), SC (no new dependencies — stdlib + existing pytest). The
SPAWN_FAILED test points argv at a non-existent path string — a deliberate,
contained Popen-failure probe, not an injection vector.

### Quality lens

1. **Build Verification follow-up:** none (CR-01 clean).
2. **JSX/template scan:** N/A (no TSX/JSX/Vue/Svelte in diff).
3. **Dead-surface:** none — `_manager_for` was replaced by `_running_manager`
   at Blue (no dangling references; confirmed via grep). All imports used
   (`OffsetEvictedError`, `NO_SESSION`, `SPAWN_FAILED`, `ExpectedError`,
   `ProtocolError`).
4. **Contract-drift:** none — the suite asserts exactly the §2.3 event kinds
   and §2.9 error codes the manager emits.
5. **Test-coverage observation:** this is the test WP; 9 scenario tests added.
6. **Style/readability:** the harness is long (~515 lines) but every test is a
   few lines of scenario over shared plumbing — readable. Docstrings cite the
   precise contract section per test.
7. **Performance procedural checks (CR-10):** no anti-pattern matches. The two
   `for ev in mgr.read(..., follow=True)` loops are the contract's iterator-read
   API being consumed as designed (event collectors with bounded waits), not
   N+1 IO.

### Watch List

- The OFFSET_EVICTED stub sets `session.log._max_events` directly (a private
  attribute) because the manager exposes no retention-cap tuning knob. This is
  the documented forced-cap path (change INDEX: "proven via a forced-cap test")
  and matches how the WP-001 unit tests exercise eviction; it is a test-only
  reach, grounded in the §2.5 contract. No action — noted for awareness only.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `ruff format --check` on the new module — clean. No mypy/pyright configured (stdlib-only package) → coverage gap noted, mitigated by 9/9 passing contract tests.
- [✓] **CR-02 Dispatch shape.** Diff is 635 lines but test-only and single-concern; reviewed directly with full-file read of the one substantive file. Recorded as a justified single-reader pass for a test-only WP.
- [✓] **CR-03 Full-file reads.** The harness (`test_session_manager_contract.py`, ~515 lines) read end-to-end; fixtures are recorded data.
- [✓] **CR-04 Evidence discipline.** Findings (none) would cite file:line; Watch List item cites the private-attr reach with its contract grounding.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired.
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each produced explicit output above.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: note (cohesive suite). PH-03 Safety: clean. PH-04 Completeness: clean. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached change/refactor-persistent-chat-sessions`
- **Neighbour expansion:** the manager package (`_session_manager/*`) — the suite's subject; reviewed for the contract-conformance relationship, no new gaps exposed.
- **Scanners run:** ruff (check + format).
- **Scanners unavailable:** mypy/pyright (not configured), gitleaks/semgrep/trivy (test-only diff, no security surface).
