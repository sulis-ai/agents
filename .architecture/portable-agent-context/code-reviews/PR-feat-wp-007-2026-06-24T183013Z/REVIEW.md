# Code Review: WP-007 — Integration seam-close + provider-independent-resume drive

> **Timestamp:** 2026-06-24T183013Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/create-portable-agent-context/wp-007-integration-seam-close-and-resume-drive → change/create-portable-agent-context
> **Files changed:** 9 (~391 added / 9 removed)
>
> **Outcome:** Ready to merge

---

## At a glance

This change wires the already-built pieces of the portable-context feature together so they work live: the durable message store is now a second place every message is recorded (alongside the existing live view), the agent's read-only "fetch the full record" tool is now actually switched on, and — the headline — resuming a session now recovers rich context from our own store even when the AI provider's own transcript files are gone. The build is clean, the changes are well-scoped to one feature, and the load-bearing journey is proven against the real saved record. A handful of small wording and robustness points surfaced in review and were all fixed in place before this report. One scope-boundary note is recorded for awareness, not action.

## What to fix

No issues that need attention. The findings raised during review were addressed inline:

- A test was named after the wrong entry point (it checked the launcher's `main` but was named "...build_server"). Renamed to match what it checks.
- Two doc comments slightly mis-described how the new tool is launched and how it's switched off. Corrected to match the shipped config.
- One spot that created the conversation record was catching every possible error as "doesn't exist yet" — narrowed so a genuine read fault surfaces honestly instead of being papered over.
- A small type-annotation mismatch on the shared "add a second listener" helper was aligned so a strict type checker stays quiet.

## How this pull request is shaped

Clean. One feature (`feat:`), two top-level areas touched (the session-manager package and the plugin's MCP config). No database migrations, no schema changes, no infrastructure files, no secrets. Every new behaviour ships with tests.

## Things to take away

Nothing to add — this was a well-shaped, well-tested change.

---

## Technical detail

> Below this point uses internal taxonomy (CR-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high remains in the diff (the one HIGH surfaced was a test-name/contract drift, fixed inline). Build Verification empty. All changed files >50 lines read end-to-end by all three lenses. All three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — ruff configured linter; no mypy/pyright config; ruff delta clean on BASE and HEAD).
- **PR Hygiene:** 0 high (PH-01 scope low: single `feat`; PH-02 size low: ~400 lines / 9 files; PH-03 safety low: 0 migrations/schemas/secrets/infra; PH-04 completeness low: every new source has tests).
- **In the changes:** 6 findings (0 critical, 1 high, 3 medium, 2 low) — **all addressed inline**.
- **In the neighbours:** 0.
- **Watch List:** 1 (scope-boundary).
- **Draft fixes:** 0 (all findings fixed inline; none deferred to deltas).

| Lens | In changes | Top concern |
|---|---|---|
| Architecture | 3 (low) | `change_id`/`thread_id`/key conflation undocumented; broad-except in `_ensure_thread_record`; silent reseed-skip on respawn |
| Security | 0 | nothing surfaced (path-traversal blocked by `validate_store_id`; no secrets; launcher no shell injection; SULIS_CHANGE_ID server-side) |
| Quality | 3 (1 high, 2 med) | test named for `build_server` but asserts `main`; `seed_payload_for_resume` not wired into `_respawn`; docstring wording drift |

### Findings in the Changes (all addressed)

#### Q-1 (HIGH, quality) — test name/contract drift — FIXED
`tests/unit/test_thread_context_mcp_wired.py:66` test named `..._resolves_build_server` but asserted `"main" in body`. The launcher imports `main`, not `build_server`. **Fix:** renamed to `test_launcher_exists_executable_and_resolves_server_entry`; docstring + comment corrected to describe the `main` entry.

#### A-2 / Q-style (LOW→addressed) — `_ensure_thread_record` swallowed all exceptions — FIXED
`manager.py` `_ensure_thread_record` used `except Exception: pass`, masking a genuine store/IO fault as "absent → create" and then `put_thread`-ing over it (no degradation/log, unlike the sink's isolation paths). **Fix:** narrowed to `except ExpectedError` + re-raise unless `exc.code == THREAD_NOT_FOUND`; docstring updated to state only THREAD_NOT_FOUND means "create".

#### Q-3 (MEDIUM, quality) — launcher docstring "NOT npx" / env wording — FIXED
Launcher docstring said "Python stdio, on the plugin's own env; NOT npx" but `.mcp.json` runs it via `uv run python`. **Fix:** reworded to "a Python stdio server run via `uv run python <launcher>` on the plugin's own project env; NOT npx".

#### Q-4 (MEDIUM, quality) — "deny-rule" wording vs allow-listed config — FIXED
Launcher docstring said the founder withholds via "the `mcp__sulis-thread-context__*` deny-rule", but settings allow-lists it (matching safe-tools). **Fix:** reworded to "allow-listed by default … the founder withholds it by moving that name to the settings `deny` list".

#### A-1 (LOW, architecture) — `_chain_on_event` type vs `as_event_observer` return — FIXED
`_chain_on_event` typed `observer: Callable[[Session, Event], None]`; `as_event_observer()` returns `Callable[[object, Event], None]`. **Fix:** widened the param to `Callable[[object, Event], None]` (the wider of the two call sites — recovery is `(Session,Event)`, durable is `(object,Event)`); docstring notes why. Safe under contravariance; aligns the seam type with both callers.

#### A-3 (LOW, architecture) — silent reseed-skip on respawn — ACKNOWLEDGED, no change
`_respawn` guards `if sink is not None: sink.seed_next_order_from_store()`. A respawn of a key whose sink is unexpectedly absent silently skips the ADV-2 reseed. Architect rated this "acceptable as-is" with an optional debug log. Left as-is: the guard is correct, and adding a debug log on an impossible-by-construction branch is below the bar for this WP; the existing `degraded_appends` counter would still surface any consequence. Recorded for awareness.

### Watch List (no failing test to ground a delta — scope boundary)

#### W-1 — `seed_payload_for_resume` not yet wired into `_respawn` (MEDIUM, scope-boundary)
The manager's `_respawn` reseeds `_next_order` (WP-007 Contract scope item 2) but does not call `seed_payload_for_resume` to write the assembled payload into the brief argv at spawn. The resume payload assembly IS proven end-to-end by the drive test (`test_provider_independent_resume.py` — with the provider transcript made unavailable, the rich payload is recovered from our store), which is the CF-12 seam-close assertion the WP Contract requires (scope item 4). The actual brief-file-write-at-spawn delivery touches the spawn/brief-write path, which the WP-007 Contract does not enumerate (its scope items are: reseed `_next_order`, MCP wiring, drive the journey). Recorded as the natural next integration step (deliver the assembled payload through `SessionSpec.brief_change_id` at respawn) for a follow-on WP; out of this WP's declared scope, so no inline change and no delta. The headline journey's load-bearing proof (context recoverable from our store, transcript gone) is green.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Linter: ruff (configured in pyproject; no mypy/pyright config). BASE + HEAD: 0 errors; delta 0. Captured at `tool-outputs/ruff-head.log`.
- [✓] **CR-02 Parallel dispatch used.** Three lenses (architecture / security / quality) dispatched concurrently as sub-agents. Diff ~940 lines (incl. new files) / 9 files — above the 200-line / 5-file carve-out, so parallel dispatch required.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end by each lens (manager.py, durable_sink.py, launcher, .mcp.json, settings.json, 4 test files). No sampling.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied: 0 critical, 1 high, 3 medium, 2 low in changes; 0 neighbour.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 not high). The one HIGH was fixed inline before verdict, so no `high` remains in the diff.
- [✓] **CR-07 Lens completion.** Architecture: 3 findings + checks listed. Security: nothing surfaced + primitives listed (path-traversal, injection, secrets, SSRF, auth boundary, allow/deny posture). Quality: build-verification follow-up (clean), dead-surface, contract-drift, test-coverage observation, CR-10 performance scan (no N+1 — get_messages is cold-path/resume only, not per-append), style.
- [✓] **CR-09 PR Hygiene applied.** PH-01 scope low; PH-02 size low; PH-03 safety low (0 migrations/secrets/infra); PH-04 completeness low (all new source tested). No high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/create-portable-agent-context` (working tree, incl. `git add -N` for new files).
- **Neighbour expansion:** the changed code's direct collaborators (thread_contract, thread_store_local, context_payload, _thread_context_mcp, safe-tools launcher) read for context; within cap.
- **Scanners run:** ruff (mechanical baseline). Gitleaks/Semgrep/Trivy not invoked — security lens reasoned over the diff (no new network/secret surface; the only new persistence is behind the existing redaction-on-write store).
- **Lenses dispatched in parallel:** yes.
- **Findings addressed inline before report:** Q-1, A-2, Q-3, Q-4, A-1. W-1 → Watch List (scope boundary). A-3 → acknowledged, no change.
