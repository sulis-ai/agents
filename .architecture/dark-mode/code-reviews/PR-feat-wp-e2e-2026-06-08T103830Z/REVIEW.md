# Code Review: Cockpit e2e refit for the tabbed cockpit (#216 cleanup)

> **Timestamp:** 2026-06-08T103830Z (ISO 8601 UTC)
> **Author:** Senior Engineer (executor)
> **Branch:** fix-e2e-tabbed-cockpit → main
> **Files changed:** 4 (e2e specs + playwright config)
>
> **Outcome:** Ready to merge

---

## At a glance

These changes bring the cockpit's browser-driven (end-to-end) tests back in line
with the new tabbed cockpit that #216 introduced. The old tests still drove the
removed sidebar layout, so they would fail whenever the test browser was actually
available — they were only "passing" because the browser download tends to fail on
CI and the whole job gets skipped. The refit is clean: it preserves what each test
was checking, just expressed through the new navigation, and all the end-to-end
suites run green locally with a real browser. One self-review issue (a timing race
in the conversation check) was found and fixed before completion.

## What to fix

No issues that need attention. The one timing-race risk found during review was
fixed in place (see "Things to take away").

## How this pull request is shaped

**Size — clean.** 130 lines across 4 files. Small and focused.

**Scope — clean.** A single concern: realigning the end-to-end tests (and their
config) to the new UI. No source code changed — only tests.

**Safety — clean.** No database migrations, no schema/contract files, no
infrastructure or deployment files, no secrets.

**Completeness — clean.** This *is* test work. The change adapts existing tests to
the new UI rather than adding new untested source.

## Things to take away

1. **Asynchronous UI state needs retrying assertions, not one-shot reads.** The
   conversation now shows an AI-generated summary that arrives a moment after the
   page loads, which changes whether the "show full reply" control is present. The
   first version of the check read that control's presence once — a coin-flip
   against the background fetch. The fix wraps the expand-and-check in a retrying
   block so it converges no matter when the summary lands. When a test depends on
   something that loads in the background, prefer a retrying assertion over reading
   state a single time.

---

## Technical detail

> Internal taxonomy below (CR-NN, PH-NN, lens IDs) for engineers and downstream
> agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files read end-to-end; all three lenses produced output. No auto-downgrade
triggers fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `npm run lint` + `npm run typecheck` clean on HEAD; Playwright type-checks all specs at run time and every spec executed.
- **PR Hygiene:** all primitives `low` (CR-09 / PH-01..04).
- **In the changes:** 1 finding (medium, quality) — **fixed inline** during review; 0 remaining.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the one finding was fixed in place, not queued).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced (test-only diff) |
| Security | 0 | 0 | nothing surfaced (no auth/injection/secret surface) |
| Quality | 1 (fixed) | 0 | async race in summary-dependent assertion (resolved) |

### Build Verification (CR-01)

Empty. Mechanical baseline:
- `npm run lint` (eslint `--ext .ts,.tsx .`, includes `e2e/`) → exit 0.
- `npm run typecheck` (`tsc --noEmit -p server && -p client`) → exit 0.
- Playwright executes the specs through its own ts loader; all default + terminal + terminal-real suites ran (see Run details), confirming the specs type-check.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):     commit_type_spread {test}; module_fan_out 1 (apps/cockpit/e2e) → low
Size (PH-02):      +130 / -58, 4 files; generated_ratio 0; lock_file_ratio 0 → low
Safety (PH-03):    migrations 0; schema_idl 0; infra 0; secret_hits 0 → low
Completeness(PH-04): new_source_without_test 0 (diff is test-only) → low
```

No PH-03 high → no CR-06 auto-downgrade.

### Findings in the Changes

#### F-01 (medium, quality) — `apps/cockpit/e2e/happy-path.spec.ts` — RESOLVED INLINE

**What:** The conversation assertion used a one-shot `await fullToggle.count()` to
decide whether to expand the "show full reply" control. Whether that control exists
depends on the asynchronous, background Haiku turn-summary poll (`/api/changes/:id/turn-summaries`,
non-blocking, cache-first): with no generated summary the summary IS the verbatim
first sentences and the toggle is hidden; once a generated paraphrase lands, the
verbatim text moves behind the toggle. A single `count()` read races that poll — if
the summary landed between the check and the final `toContainText`, the verbatim
text would be behind a still-closed toggle and the assertion would time out.

**Quoted (pre-fix):**
```ts
const fullToggle = turn.getByTestId("turn-full-toggle");
if (await fullToggle.count()) {
  await fullToggle.click();
  await expect(turn.getByTestId("turn-full-text")).toBeVisible();
}
await expect(turn).toContainText("Here is what I changed.");
```

**Fix (applied):** retrying block that re-evaluates toggle presence + expansion each
iteration, idempotent against an already-expanded state, converging in both modes:
```ts
const fullToggle = turn.getByTestId("turn-full-toggle");
await expect(async () => {
  if ((await fullToggle.count()) > 0 && (await fullToggle.getAttribute("aria-expanded")) === "false") {
    await fullToggle.click();
  }
  await expect(turn).toContainText("Here is what I changed.");
}).toPass({ timeout: 15_000 });
```

Re-ran `happy-path` after the fix → 2/2 green.

### Findings in the Neighbours

None. The diff is test-only; the components it drives were verified to expose every
testid/param the specs reference (read end-to-end: WorkspaceShell, WorkspaceTopBar,
Board, ThreadView, ChangeNav, FilesPanel, FilePane, FileToolbar, FileTreeNode,
RenderedPreview, MonacoFile/Diff inner, Chat, TurnCard, CopyPathButton,
EmptyState, ChangeCard, LiveTerminal, Composer).

### Watch List

- **`live-terminal.spec.ts` harness proxy may be retired.** The spec's own header
  notes the WS→AF_UNIX proxy may be retired now that the real-server proof exists.
  Out of scope here; recorded for awareness.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run lint` (incl. e2e), `npm run typecheck`; both exit 0 on HEAD. Playwright executed all specs. Coverage gap: none.
- [✓] **CR-02 Dispatch.** Single-reader pass justified by diff size: 130 lines, 4 files (within ≤200 lines / ≤5 files carve-out).
- [✓] **CR-03 Full-file reads.** All 4 changed files read end-to-end; all neighbour components driven by the specs read end-to-end. Unread: none.
- [✓] **CR-04 Evidence discipline.** Finding F-01 cites file + quoted text (pre/post).
- [✓] **CR-05 Severity rubric.** 0 critical, 0 high, 1 medium (fixed), 0 low.
- [✓] **CR-06 Verdict computed.** PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (test-only). Security: nothing surfaced (no auth/injection/secret surface; no new deps). Quality: 1 finding (F-01, fixed) + JSX-ident scan N/A (no tsx/jsx) + dead-surface none + contract-drift none + test-coverage (diff is tests) + CR-10 perf no matches.
- [✓] **CR-09 PR Hygiene applied.** PH-01 low, PH-02 low, PH-03 low, PH-04 low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff HEAD` (uncommitted working tree) on `fix-e2e-tabbed-cockpit` (branch tip = origin/main `b6c65ea7`).
- **Neighbour expansion:** manual read of the components each spec drives (the testid surface).
- **Scanners run:** eslint, tsc. Security scanners (gitleaks/semgrep/trivy) not run — no security-relevant surface in a test-only diff; recorded as coverage note.
- **Local e2e observed:** `test:e2e` 3/3, `test:e2e:terminal` 4/4, `test:e2e:terminal-real` 5/5 (all green against a real Chromium).
