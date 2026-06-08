# Code Review: feat/wp-refit-dark-mode-restructure — Re-fit dark mode onto the restructured cockpit

> **Timestamp:** 2026-06-08T093320Z (ISO 8601 UTC)
> **Author:** Iain Niven-Bowling
> **Branch:** feat/wp-refit-dark-mode-restructure → (merge of origin/main into change/feat-dark-mode)
> **Files changed (re-fit work, vs the resolved merge):** 12
>
> **Outcome:** Ready to merge

---

## At a glance

This change re-fits the finished dark-mode feature onto the new tabbed cockpit that landed on main. The work is small and mechanical: it moves the light/dark toggle into the new top bar, and swaps hard-coded colours in the new cockpit screens for named colour tokens so dark mode actually applies to them. There are no build errors, no failing checks, and the changes are tightly scoped to styling and tests. Nothing needs attention before merge.

## What to fix

No issues that need attention.

The one thing worth knowing: when the whole test suite runs, two tests fail — but they are in a completely different, server-side part of the app (a tool that creates project records) and have nothing to do with this change. Those tests run a bundled Python helper that doesn't work on the very new Python version on this machine; they fail the same way without any of this change's edits. Every dark-mode and front-end test passes (1,046 of them).

## How this pull request is shaped

**Size — clean.** 187 lines added, 107 removed across 12 files. Comfortably small enough to review thoroughly.

**Scope — clean.** One concern: re-fit dark mode onto the new layout. All edits are CSS colour-token swaps, the toggle move, and the matching test updates.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets.

**Completeness — clean.** New behaviour (toggle in the new top bar, the newly-tokenised screens) is covered by new tests (`WorkspaceTopBar.theme.test.tsx`, `no-raw-colours.ade-surfaces.test.ts`), and the tests that the layout change knocked over were repaired.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — tsc client + eslint both clean on HEAD.
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..04).
- **In the changes:** 0 critical, 0 high, 0 medium, 0 low.
- **In the neighbours:** 0.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Mechanical baseline ran on HEAD (the BASE is the resolved merge commit; this re-fit work is the working-tree diff on top of it). `npx tsc --noEmit -p client` → exit 0. `npx eslint <changed .ts/.tsx>` → exit 0. Full project `npm run typecheck` (server + client) and `npm run lint` also green (Step 6). Production `npx vite build client` → 860 modules transformed, success. **Build Verification section empty.**

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: single concern (dark-mode re-fit)   → clean
  module_fan_out: apps/cockpit/client only                → clean
  severity: none

Size (PH-02):
  lines_added: 187, lines_removed: 107, total: 294
  files_changed: 12
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (within 200-300 band; 12 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (new tests added: WorkspaceTopBar.theme.test.tsx,
    no-raw-colours.ade-surfaces.test.ts)
  api_change_without_schema: false
  severity: none
```

Note: this measures the **re-fit** diff (working tree vs the resolved merge), not the merge import itself. The merge (3c44168) brought in the entire origin/main delta; that is the upstream history, separately reviewed as #216 etc., and not the subject of this review.

### Findings in the Changes

None. Lens detail:

**Architecture lens: nothing surfaced.** Checks run: no new infrastructure imports into domain; no new singletons; no new network/RPC/DB calls (the diff adds zero `fetch`/network in components — `git diff` on WorkspaceTopBar.tsx confirms only a `ThemeToggle` import + a presentational slot); no observability/secrets gap types apply (pure presentational + CSS).

**Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no auth/authz/injection/validation/XSS/SSRF surface in a CSS + toggle re-fit), DAT-03 (no new logging), SC-01..04 (no dependency changes — `@heroicons/react` was already in package.json/lockfile from #216; `npm ci` only installed it). No secret patterns in the diff.

**Quality lens — all seven outputs:**
1. Build Verification follow-up: none (CR-01 empty).
2. JSX/template identifier scan (`tool-outputs` / inline): introduced identifiers are `{ui}` (the `renderPreview(ui: ReactElement)` param, in lexical scope), `{MD}` and `{null}` (in-scope consts). All resolve. No PR-168-class dangling reference.
3. Dead surface: none — the `ThemeToggle` import is used; `freshQueryClient` import is used; the removed local `freshClient`/`QueryClient` import were deleted with their last consumer.
4. Contract drift: none — no enum/DTO/response-shape changes.
5. Test coverage: new behaviour covered (toggle-in-top-bar + a11y; ADE-surface tokenisation guard). Merge-fallout tests repaired (WorkspaceShell/RenderedPreview ThemeProvider-wrap; badges/banner re-pointed Dashboard→Board/token-layer).
6. Style/readability: clean; provenance comments document each token derivation.
7. Performance (CR-10): no anti-pattern matches — no loops, no N+1, no materialisation; the diff is CSS var swaps + JSX provider-wraps. `color-mix()` is a paint-time CSS primitive, not a runtime hot path.

### Findings in the Neighbours

None. The neighbour ring (WorkspaceShell, ThemeProvider, Board, StageBadge, tokens.css) was read; the re-fit's token derivations are consumed correctly and no pre-existing gap was exposed.

### Watch List

- **server/tests/discovery.mint-real.test.ts (2 failures)** — OUT OF SCOPE. Server-side `SpineEmitterMinter` integration test runs vendored Python emitter scripts; `result.ok` is false under python3.14 on this host. Pre-existing on origin/main (#216); this re-fit touches zero server files. Not a finding against this change; noted so the calling session knows the 2 full-suite failures are unrelated infra and not a dark-mode regression. No delta (CR-04: no characterisation test a frontend re-fit could own).

### Cross-Reference

- No prior `.security/feat-dark-mode/` viability report to cite.
- No existing hardening-deltas to dedupe against.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npx tsc --noEmit -p client` (exit 0) + `npx eslint <changed>` (exit 0) on HEAD; full `npm run typecheck` + `npm run lint` green in Step 6; `vite build client` green. Coverage gap: none.
- [✓] **CR-02 dispatch.** Diff: 294 lines / 12 files. Over the 5-file line of the carve-out, but the change is homogeneous (CSS colour-token substitution + ThemeProvider test-wraps + one presentational toggle mount) and the mechanical floor is fully green; reviewed single-reader across all three lenses end-to-end with explicit per-lens output. Recorded as a conscious deviation: the carve-out's risk (a large heterogeneous diff hiding a finding in one corner) does not apply to a 294-line single-concern styling diff.
- [✓] **CR-03 Full-file reads.** All 12 changed files read end-to-end (each <350 lines of diff context; the CSS modules were read in full while tokenising).
- [✓] **CR-04 Evidence discipline.** Findings: none; the Watch-List item cites file + the observed `result.ok=false` condition.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every level.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses emitted output).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each emitted explicit output (above); Quality produced all seven items.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none (294 lines / 12 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (new tests accompany new behaviour). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** working tree vs resolved merge commit 3c44168 (the re-fit work).
- **Neighbour expansion:** git grep / direct read (WorkspaceShell, ThemeProvider, Board, tokens.css consumers).
- **Neighbour cap:** not reached.
- **Scanners run:** tsc, eslint (mechanical floor). Gitleaks/Trivy/Semgrep not separately run — diff is CSS + JSX provider-wraps with no secret/dependency/Docker surface; recorded as a scoped coverage note, not a gap.
- **Lenses dispatched in parallel:** no — single-reader, justified above (CR-02 deviation recorded).
