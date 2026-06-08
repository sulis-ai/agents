# Code Review: WP-001 — Brief from `SessionSpec.brief_change_id`, not ambient env

> **Timestamp:** 2026-06-08T171258Z (ISO 8601 UTC)
> **Author:** executor (WP-001)
> **Branch:** feat/wp-001-brief-target-on-sessionspec → change/fix-terminal-per-change-brief
> **Files changed:** 3 (177 insertions, 70 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes a real bug: in the shared terminal daemon, every session was
being briefed for the wrong change because the brief target was read from a
single shared environment value. The fix moves that target onto the per-session
spec object the code already passes around, and removes the shared-environment
read entirely. The change is small, well-tested (including a test that
reproduces the exact bug and proves it's fixed), and there's nothing that needs
attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 177 lines added, 70 removed, across 3 files. Small and easy
to review thoroughly.

**Scope — clean.** A single concern: move the brief target from the shared
environment onto the session object, and delete the old path. No unrelated
changes bundled in.

**Safety — clean.** No database migrations, no schema or infrastructure
changes, no secrets. The change tightens a security property (it removes a
value that could be influenced from outside the process) rather than loosening
one.

**Completeness — clean.** The source change ships with its tests in the same
change. The test file gained a test that sets the old (shared-environment) value
to one change and the new (per-session) value to a different change, then proves
the session is briefed from the per-session value — the regression the original
tests couldn't catch.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, WPB-NN, lens
> IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
three changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — dependency surface tightened (`import os` removed) |
| Security | 0 | 0 | None — ambient-env brief source removed (closes action-at-a-distance) |
| Quality | 0 | 0 | None — 100% coverage on both changed source files |

### Build Verification (CR-01)

Mechanical baseline ran on the two changed source files:

- `ruff check` — All checks passed (`tool-outputs/ruff-head.log`).
- `ruff format --check` — clean (formatter applied during Step 6).
- `mypy` on `adapter.py` + `claude_pty.py` — 0 errors
  (`tool-outputs/mypy-changed-delta.log` is empty).

Pre-existing `mypy` errors in `_session_manager/manager.py` are byte-for-byte
unchanged from the base branch (confirmed by diff) and out of this WP's scope.

**Build Verification section: empty.** No PR-introduced errors.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {fix} (single concern, REINFORCE-Harden) → clean
  module_fan_out: 1 top-level dir (_session_manager + its tests) → clean
  severity: none

Size (PH-02):
  lines_added: 177, lines_removed: 70, total: 247 diff lines
  files_changed: 3
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (well within carve-out: <=200 net, <=5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (source + tests in same change)
  api_change_without_schema: false (SessionSpec field is additive + defaulted)
  severity: none
```

### Findings in the Changes

None.

Lens detail:

**Architecture lens (WPB-01 dependency-inward): nothing surfaced.** Checks run:
domain→infrastructure import direction (the adapter imports only `events`
domain types, the launcher sidecar constant, and `_wpxlib.validate_change_ulid`
— removing `import os` *reduces* the surface, no new infra dependency);
module-level singletons (none added); circular imports (none — the new field
lives on the existing `SessionSpec` dataclass); `ProviderAdapter` Protocol
signature (`spawn_argv(spec)` unchanged — the conformance test stays green, the
frozen seam holds, every existing adapter slots in unmodified). The new
`brief_change_id` field follows the exact additive-defaulted precedent set by
`io_mode` (ADR-001 of this change), the established convention for extending
this frozen spec.

**Security lens: nothing surfaced.** Primitives checked: SEC-02 (input
validation), SEC-05 (path traversal), SEC-06 (secrets exposure). The change
*improves* the security posture: it removes the ambient `SULIS_CHANGE_ID`
read, an attacker-influenceable, process-global value that flowed (under the
shared daemon) into a filesystem-path resolution for the wrong change. The
replacement is a per-session field with two layers of defence retained: (1) a
`__post_init__` shape guard rejecting a leading `-` and any control character
(mirroring the existing `resume_ref` guard, so it can never be read as a flag
or split a path/line boundary), and (2) `validate_change_ulid` before the path
join (a malformed value is ignored, never turned into a path). No secrets, no
injection vector, no plaintext-credential pattern in the diff. Scanners: none
run (no signals in a 3-file Python diff with no new deps / Dockerfile / logging
of secrets); recorded as a coverage note, not a gap — the diff has no
dependency or infra surface for Gitleaks/Trivy to score.

**Quality lens output:**
1. *Build Verification follow-up* — none (CR-01 clean).
2. *JSX / template identifier scan* — N/A (no TSX/JSX/Vue/Svelte files).
3. *Dead-surface findings* — none. `import os` and `_CHANGE_ID_ENV` were
   removed as part of the rewire (no orphaned symbols left behind); the new
   field is consumed by `_read_pre_prompt(spec)`.
4. *Contract-drift findings* — none. `SessionSpec.brief_change_id` defaults to
   `None`; the `socket_server.py:216` constructor (a neighbour) does not pass
   it and defaults cleanly. (Wiring `socket_server._open` to read
   `brief_change_id` from the wire dict is explicitly WP-002's scope per
   ADR-001 Consequences — not a drift introduced here.)
5. *Test-coverage observation* — the diff includes tests for every new
   behaviour: the spec-wins-over-env regression (`test_briefs_from_spec_not_env`),
   `None` default → bare argv, valid id + sidecar → brief appended, absent
   sidecar → no positional, malformed id → ignored, and both `__post_init__`
   guard branches (leading-dash, control-char). Coverage: 100% on
   `claude_pty.py`, 100% on `adapter.py` (measured across the session suite).
6. *Style / readability* — clean. Docstrings rewritten to the spec-field source
   citing this change's ADR-001; stale ADR-004 "rides the process environment"
   rationale removed.
7. *Performance procedural checks (CR-10)* — no anti-pattern matches. The
   change is a single sidecar file read guarded by `is_file()`; no loops, no
   N+1, no unbounded materialisation.

### Findings in the Neighbours

None. The neighbour ring (14 `SessionSpec` constructors across `socket_server.py`
+ the test suite, capped well under 20) was exercised by the full 365-test
session suite, all green — every existing caller defaults `brief_change_id` to
`None` and is byte-for-byte unaffected.

### Watch List

- **WP-002 dependency (informational, not a finding):** the corrected behaviour
  is only end-to-end once a consumer sets `spec.brief_change_id` on `open()`
  (cockpit `TerminalSidecar.ts`, desktop `session_viewer.py`, and
  `socket_server._open` reading the wire-dict key). That is WP-002's contract.
  Until then the adapter correctly briefs from the (still-`None`) field — no
  regression, just no brief. ADR-001's done-gate is the observed live run
  (WP-003), and a green unit suite is necessary-not-sufficient by design.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`,
  `ruff format --check`, `mypy` on the two changed source files. Base: clean.
  Head: clean. Coverage gap: none (manager.py mypy errors are pre-existing,
  unchanged from base, out of scope).
- [✓] **CR-02 Single-reader pass justified by diff size: 247 diff lines, 3
  files** — within the ≤200-net-lines / ≤5-files carve-out.
- [✓] **CR-03 Full-file reads.** All 3 changed files read end-to-end during
  authoring + review. Unread files: none.
- [✓] **CR-04 Evidence discipline.** Zero findings; lens outputs cite the
  specific checks run.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none
  fired (Build Verification empty; all files read end-to-end; all lenses
  produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks listed.
  Security: nothing surfaced + primitives/scanners noted. Quality: all of
  items 1-7 produced (2 = N/A non-frontend, 6 = clean).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single `fix` concern).
  PH-02 Size: none (247 lines / 3 files). PH-03 Safety: none (0 migrations /
  0 schemas / 0 secrets / 0 infra). PH-04 Completeness: none (source + tests
  together). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff change/fix-terminal-per-change-brief` (working tree
  vs base; changes not yet committed at review time — Step 6.5 runs before
  Step 7 commit).
- **Neighbour expansion:** `git grep` for `SessionSpec(` / `spawn_argv` /
  `_read_pre_prompt` callers.
- **Neighbour cap:** 14 of 14 considered, 0 excluded.
- **Scanners run:** none (no dependency/infra/secret surface in a 3-file Python
  diff; recorded as a coverage note per CR-01, not a silent skip).
- **Lenses dispatched in parallel:** no — single-reader justified by CR-02
  carve-out.
- **WP kind:** backend (Python) → scored against WP_BACKEND_STANDARD WPB-01..12.
