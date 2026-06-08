# Code Review: WP-009 — Re-point the change-terminal launcher onto the cockpit-rendered terminal

> **Timestamp:** 2026-06-07T145703Z (ISO 8601 UTC)
> **Author:** WP-009 executor
> **Branch:** feat/wp-009-change-terminal-launcher-repoint → change/extend-interactive-terminal-sessions
> **Files changed:** 9
>
> **Outcome:** Ready to merge

---

## At a glance

This change does exactly one thing and does it cleanly: "open this change's
terminal" now opens the terminal *inside the cockpit* (the browser tab you
already have) instead of popping a separate Terminal window on your computer.
The old pop-a-window behaviour isn't deleted — it's kept as an off-by-default
fallback you can switch back on with a setting, with a recorded plan to remove
it once the in-cockpit terminal is proven. The build is clean, the new code has
tests, and nothing about the existing chat or the launcher's window-opening
internals changed. No issues that need attention.

## What to fix

No issues that need attention.

One minor thing for awareness (not worth changing now): in the launcher's new
"this path is switched off by default" branch, the empty file-path value passed
to the failure helper is a plain empty string while a couple of nearby callers
pass a path object. It behaves identically and reads fine — just a small
consistency note, not a fix.

## How this pull request is shaped

**Size — clean.** 466 lines across 9 files, all in service of the single
launcher re-point. Comfortable to review thoroughly.

**Scope — clean.** One concern: the launcher re-point. Frontend action + the
UI button that triggers it + the backend flag-gate on the old path + docs +
tests. No unrelated refactors mixed in.

**Safety — clean.** No database migrations, no schema/interface changes, no
infrastructure files, no secrets.

**Completeness — clean.** The one new source file ships with two new test
files; the backend flag-gate adds nine new test cases and updates the existing
launcher tests to opt into the now-gated window path.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high, 0 medium, 0 note — well-scoped, well-sized (CR-09 / PH-01..PH-04)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single low finding is below the delta threshold; recorded on the Watch List)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — WPF-02/03 honoured (typed port + injected deps) |
| Security | 0 | 0 | none — existing input validation intact; gate-at-attach unchanged |
| Quality | 1 | 0 | `_failed("")` vs `_failed(Path(...))` type-hint consistency (low) |

### Build Verification (CR-01)

No PR-introduced errors. `tsc --noEmit -p server && -p client` clean; `eslint
--ext .ts,.tsx` clean; `ruff check` clean on `_terminal_launcher.py` + tests.
Outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  concern: single (change-terminal launcher re-point)
  module_fan_out: 2 top-level areas (apps/cockpit, plugins/sulis/scripts)
  severity: low (one logical concern; cross-area is intrinsic to a launcher re-point)

Size (PH-02):
  lines_added: 466, lines_removed: 3, total: 469
  files_changed: 9
  severity: low

Safety (PH-03):
  migration_count: 0  schema_idl_count: 0  infra_files: 0  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0  (1 new source file, 2 new test files)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `plugins/sulis/scripts/_terminal_launcher.py:~503` — low (quality)

**Quoted text:**
```python
result = _failed(
    "the OS-window terminal launch is deprecated (WP-009); ...",
    "",  # no launch.sh written on the suppressed path
)
```

**Observation:** `_failed(error, script_path)` is type-hinted `script_path:
Path`, but the new Strangle-gate branch passes a plain `""`. `str("")` yields
`""` (the intended "no path" value — verified), so behaviour is correct and the
result dict is well-formed. The other two `_failed(...)` callers in this module
pass `Path(...)` / a `target` Path. This is a cosmetic type-hint inconsistency,
not a defect.

**Recommendation:** Acceptable as-is (`""` is the conventional empty-path
sentinel and the function stringifies it correctly). If tightened later, pass
`Path("")`-free or widen the hint to `Path | str`. Below the Hardening-Delta
threshold (no failing characterisation test — CR-04) → Watch List.

### Findings in the Neighbours

None. Neighbours examined: `ThreadTabs.tsx` (the `?tab=terminal` route target,
unchanged), `LiveTerminal.tsx` (mounts on the Terminal tab; its mount-open is
idempotent with the launcher's warm-open — verified consistent), `terminalBridge.ts`
(the `createTerminalBridge` factory the launcher reuses), `sulis-change` (the
other `launch_change_terminal` caller — now hits the default-off gate, handled
gracefully by its existing spawn-failure path; spawn tests green).

### Watch List

- `_terminal_launcher.py` `_failed("")` type-hint consistency (low, above).

### Cross-Reference

- Registered finding **SF-3c374c29** (advisory): ghost-button CSS duplicated
  between `ChangeCard.module.css .openTerminal` and `LiveTerminal.module.css
  .reconnect`. Out of WP-009 Contract scope (touches LiveTerminal CSS) —
  deferred to its own WP per EP-07. Not re-drafted here.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `tsc -p server && -p client`, `eslint`, `ruff check`. Base (change branch) and Head both run during Step 6; Head delta: 0 new errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff 469 lines / 9 files (>5 files → above carve-out). Lens analysis applied per-lens across all 9 files; no file delegated unread.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end during authoring + review: `_terminal_launcher.py` (full), `test_terminal_launcher.py` (full), `ChangeCard.tsx`, `Dashboard.tsx`, `launchChangeTerminal.ts`, both new test files, `ChangeCard.module.css`, `smoke_terminal_launcher.md`. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied: 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 none).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (WPF-02 typed port ✓, WPF-03 injected deps ✓, dependency direction ✓, no new singletons). Security: nothing surfaced (existing ULID/worktree/entry-command validation intact; no secrets; no injection surface added; gate-at-attach trust boundary unchanged; scanners not separately run — diff has no security-signal files). Quality: 1 finding + JSX-ident scan (`{change}`/`{openTerminal}` both in scope) + dead-surface (`changeTerminalPath` exported intentionally for WP-010 reuse — not dead) + contract-drift (open() encodes io_mode:"pty" per §2.13.5 — consistent) + test-coverage (new source has tests) + CR-10 perf (no loops/N+1 in new code).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low. PH-02 Size: low (469 lines / 9 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (tests present). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** git diff change/extend-interactive-terminal-sessions...HEAD (staged)
- **Neighbour expansion:** git grep + manual import trace (ChangeCard/Dashboard/ThreadTabs/LiveTerminal/terminalBridge/sulis-change)
- **Neighbour cap:** 6 of 6 considered; none excluded.
- **Scanners run:** tsc, eslint, ruff (mechanical floor). Gitleaks/Semgrep/Trivy not separately invoked — diff introduces no secret/dependency/infra signals.
- **Lenses:** applied by the reviewing agent across all 9 files (no sub-agent dispatch; single-session full-file coverage).
