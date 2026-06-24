# Code Review: PR feat/wp-004 — Session-pump durable-append sink + resume payload-seed

> **Timestamp:** 2026-06-24T175555Z (ISO 8601 UTC)
> **Author:** autonomous executor (CH-GJ9KQR-WP-004)
> **Branch:** wp/create-portable-agent-context/wp-004-session-pump-durable-sink-and-resume-seed → change/create-portable-agent-context
> **Files changed:** 2 (1 source, 1 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the wiring that lets a conversation be picked back up from our own
saved record instead of relying on the AI provider's transcript files. It is small,
focused, well-tested, and builds cleanly on the three pieces already merged (the
durable store, the context assembler, and the shared contract). There are no build
errors and nothing that needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 432 lines across 2 files (one new module, one new test file). Easy
to review thoroughly.

**Scope — clean.** A single concern: wire the existing live session as the durable
writer, and seed a resumed session from our own store.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets. The change adds no new network surface; it reuses the existing
secret-scrubbing-on-save behaviour so nothing sensitive lands on disk.

**Completeness — clean.** The new behaviour ships with 11 tests that run against the
real saved-record store and the real context assembler (no stand-ins), plus a
confirmation that the existing live-view behaviour is byte-for-byte unchanged.

---

## Technical detail

> Below this point the report uses internal taxonomy for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01; ruff check + format clean)
- **PR Hygiene:** 0 findings (PH-01..04 all clean / low)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Configured linter: `ruff` (per `pyproject.toml`). HEAD run on the two changed files:
`All checks passed!`; `ruff format --check`: both files formatted. No type-checker is
configured in this project (ruff is the lint+format gate) — recorded as a coverage
note, not a gap, since the project has no mypy/pyright config. Test suite: 26 passed
(11 new + 15 characterisation). Raw output: `tool-outputs/ruff-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 → severity none
Size (PH-02):         lines_added 432, files_changed 2 → severity low
Safety (PH-03):       migrations 0, schemas 0, infra 0, secrets 0 → severity none
Completeness (PH-04): new_source_without_test 0 (1 source + 1 test) → severity none
```

### Findings in the Changes

**Architecture lens: nothing surfaced.** Checks run: dependency direction (WPB-01/
MEA-01 — `durable_sink` imports only `events`, `thread_contract`, `context_payload`;
no provider/subprocess/web import — confirmed inward-only); no new module singletons;
no circular imports; reuse-first (EP-03 — reuses WP-003 `summarise_memory` and the
WP-002 `LocalThreadStore`, no second decode path per ADR-004); resilience (no new
network call — local FS only per TDD §4, so timeout/circuit-breaker are N/A in scope);
observability (degraded appends logged with `exc_info` + counted); proof (contract
test drives the real store + real assembler, no behaviour mocks — the `_BoomStore` is
a deliberate failure-injection stub for the isolation assertion, MEA-09 compliant).

**Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no new
access-control surface; read/write split owned by the contract), DAT-03 (redaction-
on-write reused from the durable store — `test_secret_in_event_text_is_redacted_on_
durable_write` confirms a token-shaped secret never reaches the `.jsonl` bytes),
secrets (no plaintext token/key/password patterns in the diff). No new network
surface (ADR-002 local binding). Store is change-scoped (id validated by the
contract's `validate_store_id`, inherited from WP-002).

**Quality lens (all 7 outputs):**
1. Build Verification follow-up: none (CR-01 clean).
2. JSX/template identifier scan: N/A (no TSX/JSX/Vue/Svelte files).
3. Dead-surface: none — every symbol in `durable_sink.py` is referenced (public API:
   `DurableAppendSink`, `seed_payload_for_resume`; helpers all used).
4. Contract-drift: none — uses `thread_contract` types verbatim (`ThreadMessage`,
   `ThreadMemory`, `ContextPayload`, `MessageRole`, `PayloadTier`); roles are members
   of `MESSAGE_ROLES`.
5. Test-coverage: 11 tests for new behaviour; 98% line coverage on `durable_sink.py`
   (1 missed line is an unreachable defensive `return ""` fallthrough in
   `_content_for_event`, only reached if a `tool_use` Event had `tool=None`, which the
   `events.Event` constructor forbids).
6. Style/readability: clean — descriptive names, comprehensive docstrings citing
   ADR-004/005 + WP-002/003.
7. Performance (CR-10): no anti-pattern matches. The only loop in the impl
   (`checkpoint` reads messages then summarises) is a single store read + a pure
   in-memory summarise; no N+1, no per-iteration IO.

### Findings in the Neighbours

None. The change is wired via the existing `on_event` registered-callback seam
(the same seam `manager._attach_recovery` and the turn-guard fan-out already use);
`session.py` and `event_log.py` are byte-for-byte unchanged (git status confirms no
modification). No neighbour code is altered or newly coupled.

### Watch List

- The manager-side wiring of `DurableAppendSink.as_event_observer()` onto
  `session.on_event` (and the `checkpoint()` call at Working Set crystallisation
  boundaries) is the integration seam WP-007 closes end-to-end. This WP delivers the
  sink + seed as wired-by-contract building blocks; the live composition-root wiring +
  the provider-independent-resume drive land in WP-007 per the INDEX dependency graph.
  Not a finding — a scope boundary recorded for the integration reviewer.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Command: `ruff check` + `ruff format --check`
  (configured linter per pyproject.toml). Head: 0 errors, formatted. No type-checker
  configured (coverage note, not a gap — no mypy/pyright in project config).
- [✓] **CR-02 Dispatch shape.** Diff 432 lines / 2 files. Single-reader pass: both
  files authored + read end-to-end this session; 2-file diff with one source module is
  within practical single-reader scope. Recorded per carve-out note.
- [✓] **CR-03 Full-file reads.** Both changed files >50 lines read end-to-end
  (durable_sink.py 270 lines; test file 290 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings (none) would cite file:line; lens
  no-finding entries list checks run.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired
  (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed.
  Security: nothing surfaced + primitives listed. Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: low (432 lines /
  2 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04
  Completeness: none (source + test). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** git working tree vs change/create-portable-agent-context (new files)
- **Neighbour expansion:** git grep on the `on_event` seam; session.py/event_log.py
  confirmed unchanged
- **Neighbour cap:** not reached (0 neighbours altered)
- **Scanners run:** ruff (lint+format); manual grep for secret patterns + CR-10 perf
- **Scanners unavailable:** no type-checker configured; no Gitleaks/Semgrep/Trivy in
  this project's toolchain (manual pattern grep used for the secrets primitive)
- **Lenses dispatched:** single-reader (2-file diff)
