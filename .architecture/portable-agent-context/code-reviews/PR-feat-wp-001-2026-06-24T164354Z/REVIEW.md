# Code Review: WP-001 — Thread/Message/Memory + context-payload contract

> **Timestamp:** 2026-06-24T164354Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/expand-create/wp-001-thread-context-contract → change/create-portable-agent-context
> **Files changed:** 4
>
> **Outcome:** Ready to merge

---

## At a glance

This change defines the shared agreement for how threads, messages, and conversation
memory are shaped and stored — the foundation the next several pieces of work build on.
The review ran twice: the first pass surfaced a handful of things worth tightening; all
were fixed, and the second pass came back clean. No build errors, every new behaviour is
tested (39 tests), and the change is well-scoped to a single concern.

## What to fix

No issues that need attention. Everything raised in the first review pass was addressed
and re-verified.

The first pass flagged, and the author fixed:
- A "no memory yet" lookup was returning the same signal as "no such thread" — they're now
  distinct, so later code can tell the two apart.
- The convention for where thread files live could, in theory, be fed an unsafe name that
  escaped its folder — the convention now rejects unsafe names up front, so every piece of
  work that uses it inherits that protection.
- The shared test was claiming to also exercise the real (future) storage adapter but
  wasn't actually wired to do so — it now is, through a single extension point.
- A few smaller test gaps (a memory-version safeguard, an empty-role message, a combined
  filter case) were filled in.

## How this pull request is shaped

Single, well-defined concern (a contract). 973 lines across 4 files — mostly the contract
module, its test, and two example data files. No database migrations, no schema changes, no
secrets, no infrastructure. New code ships with its tests. Nothing here suggests it should
be split.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files
read end-to-end; all three lenses produced output across two iterations.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff check clean, mypy 0 errors in `thread_contract.py`, 39 tests pass.
- **PR Hygiene:** scope clean (single contract WP), size 973 lines / 4 files, safety clean (0 migrations / 0 schema / 0 secrets / 0 infra), completeness clean (new source ships with tests).
- **In the changes:** 0 unresolved. Iteration 1 surfaced 2 medium + 6 low; all resolved inline. Iteration 2 surfaced 1 new low (version-guard test depth) + a docstring-accuracy note; both resolved inline.
- **In the neighbours:** 0.
- **Draft fixes:** 0 (all findings fixed inline; no remediation WPs, no exceptions).

| Lens | In changes | Top concern (resolved) |
|---|---|---|
| Architecture | 0 open | contract test now parameterised over the store subject (WP-002 extension seam); put_memory version-monotonicity guard added |
| Security | 0 open | path-traversal: `validate_store_id` (`^[A-Za-z0-9_-]+$`) on store-root + filename helpers |
| Quality | 0 open | `get_memory` now raises `MEMORY_NOT_FOUND` (was dead); `STALE_MEMORY_VERSION`/`INVALID_ID` raised+tested |

### Resolution log (CR-05 / inline-fix Path A, 2 iterations within budget)

**Iteration 1 (8 findings, all in-scope, all fixed inline):**
- MEDIUM (quality+arch dedup): `get_memory` emitted `THREAD_NOT_FOUND` for a missing-memory miss; `MEMORY_NOT_FOUND` was dead → now raises `MEMORY_NOT_FOUND`; test added.
- MEDIUM (arch): contract test not parameterised over the store subject → `store` fixture (`params=[InMemoryThreadStore]`) + `test_store_subject_conforms_to_the_port` (isinstance vs runtime-checkable port).
- MEDIUM (arch): `put_memory` no version-monotonicity guard → raises `STALE_MEMORY_VERSION` on stale/equal version; test added.
- LOW (security): path traversal via `change_id`/`thread_id` → `validate_store_id` regex guard on all path/filename helpers; parametrized traversal-rejection test.
- LOW (quality): no `isinstance(store, ThreadStore)` conformance assertion → added.
- LOW (quality): `role=None` untested → added.
- LOW (quality): `since`+`limit` composition untested → added (discriminating assertion).
- LOW (quality): `ContextPayload` default pointer wiring untested → added.

**Iteration 2 (1 new low + 1 note, both fixed inline):**
- LOW (arch): version-guard test didn't cover strictly-lower version or assert unchanged-state after a rejected put → strengthened (`version=5`, reject equal, reject lower, assert stored unchanged, accept forward).
- NOTE (arch): fixture docstring over-claimed "without touching any test body" → softened to name the fixture as the single WP-002 extension seam (durable adapter needs a factory for its store root).

**Out-of-scope / forward-looking (not WP-001 defects, recorded for WP-002):**
- O(N²) duplicate-id scan in the in-memory stub's `append_message` — benign for a test stub at conversation cadence; WP-002's durable `.jsonl` adapter must rely on offset-monotonic + file append semantics, not a full-log rescan.
- WP-002's durable adapter must expose the off-port `put_thread` setup method and route on-disk paths through `validate_store_id` to inherit the traversal guard.
- `re.match` + `$` tolerates a trailing newline; cannot enable traversal (separators/dots already rejected); `re.fullmatch`/`\Z` is the cleaner idiom (informational).

### Methodology — Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check (changed files): 0 errors. mypy (`thread_contract.py`): 0 errors (12 reported errors are pre-existing in `manager.py`, confirmed on base, out of scope). pytest: 39 passed. Coverage gap: pytest-cov absent → manual coverage analysis (recorded in journal preflight).
- [✓] **CR-02 Parallel dispatch used.** Three lenses dispatched concurrently as sub-agents, both iterations. Diff: 973 lines / 4 files (above carve-out threshold → parallel required).
- [✓] **CR-03 Full-file reads.** Both >50-line changed files read end-to-end by every lens; author authored them.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 2 medium (resolved), 7 low (resolved).
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each produced structured output across 2 iterations, ending with explicit "prior findings resolved, nothing new surfaced".
- [✓] **CR-09 PR Hygiene applied.** Scope: clean (single contract WP). Size: 973 lines / 4 files. Safety: 0 migrations / 0 schema / 0 secrets / 0 infra. Completeness: new source ships with tests. No PH-03 high → no auto-downgrade.

#### Run details
- **Diff source:** `git diff --cached change/create-portable-agent-context` (new files staged).
- **Neighbour expansion:** `_session_manager/events.py` (the only import target) reviewed; dependency-direction confirmed one-way.
- **Scanners:** ruff, mypy (project-configured); manual secret/PII scan of module + fixtures.
- **Lenses dispatched in parallel:** yes (2 iterations).
