# Code Review: WP-003 — Hide soft-deleted entities across the brain read paths

> **Timestamp:** 2026-06-09T104731Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-003)
> **Branch:** feat/wp-003-sys-status-read-filter → change/feat-user-level-product-store-settings
> **Files changed:** 5 (2 source, 2 test, 1 new source)
>
> **Outcome:** Ready to merge

---

## At a glance

This change makes removed products and projects actually disappear from the cockpit. Until now, "removing" an entity marked it deleted on disk but the read code still showed it — so a removed product would keep appearing in the switcher and a removed project would still hand back its repo. This adds a single small rule that hides anything marked deleted, purged, or archived, while leaving older entities that have no status untouched.

There are no build errors, the change is well-scoped to the two read paths it was meant to touch, and every new behaviour is covered by a test. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Small and focused: 5 files, ~135 lines, mostly tests.

**Scope — clean.** One concern (hide removed entities on read), one commit type (a hardening change). Touches only the two read libraries named in the work package plus their tests, and one new shared helper that both use.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets. The change is read-only and narrows what's shown — it never deletes a file or writes to disk, which is exactly the guarantee the design asked for.

**Completeness — clean.** New behaviour ships with tests. The deleted/purged/archived cases, the "older entity with no status still shows" case, and the removed-project case are all covered, and the original behaviour was pinned with a characterisation test first before the change went in.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). `tsc --noEmit -p server` exit 0; `eslint` exit 0.
- **PR Hygiene:** 0 findings. Scope/Size/Safety/Completeness all clean (CR-09 / PH-01..PH-04).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (pure read-side predicate; no new I/O, no new dependency direction) |
| Security | 0 | 0 | — (read-only; narrows visibility; fixed allowlist Set, no user-controlled matching) |
| Quality | 0 | 0 | — (new behaviour fully tested; no perf anti-pattern; no contract drift) |

### Build Verification (CR-01)

None. `tsc --noEmit -p server` → exit 0. `eslint` on all 5 changed files → exit 0. Logs in `tool-outputs/`.

### Findings in the Changes

None.

#### Architecture lens — nothing surfaced

Checks run: dependency direction (no domain→infrastructure import added; the new `isActiveStatus.ts` is a pure function with zero infrastructure deps); module-level singletons (none added); new external/HTTP/DB calls (none — the filter sits inside the pre-existing on-disk `readEntitiesOfKind` loop, structure unchanged); resilience primitives (n/a — no new I/O introduced, so no new timeout/circuit-breaker required); verification (new behaviour tested against real on-disk fixtures, not mocks — WPB-03/08 satisfied). EP-03 reuse: the status predicate lives once and is consumed by both libs (2-consumer threshold met by extraction, not duplication).

#### Security lens — nothing surfaced

Primitives checked: SEC-01..07 (access control / auth / injection / validation / SSRF / secrets), SC-01..04 (dependency CVEs). No new dependency added (no lockfile change). No new auth surface. No injection vector — `sys_status` is compared against a fixed `ReadonlySet<string>` allowlist, no regex/eval/user-controlled matcher. No secrets in the diff. The change is read-only and *reduces* exposure (soft-deleted entities are now hidden), a security-positive.

#### Quality lens — all outputs produced

1. **Build Verification follow-up:** none (baseline clean).
2. **JSX/template identifier scan:** n/a (no TSX/JSX/Vue/Svelte files in the diff).
3. **Dead-surface:** none. `isActiveStatus` is imported and used in both `readProducts.ts` and `resolveProjectRepo.ts`; `IMPLICIT_PRODUCT_ID` (newly imported into the test) is referenced.
4. **Contract-drift:** none. The removed-status set `{deleted, purged, archived}` is the exact complement of the schema/ADR-020 `sys_status` enum `{active, archived, deleted, purged}` — `active` is kept, every removed value is hidden. A legacy entity with no `sys_status` is treated active (absence ≠ deleted), matching the WP Contract invariant.
5. **Test-coverage:** present. 116 insertions across the two test files cover deleted/purged/archived hiding, missing-status-active, removed-project-resolves-null, and the characterisation pin→invert. New file `isActiveStatus.ts` fully exercised (all three branches: removed string, active string, non-string/absent).
6. **Style/readability:** clean. Descriptive names (`isActiveStatus`, `REMOVED_STATUSES`), "why" comments citing ADR-020, no TODO/FIXME introduced.
7. **Performance procedural checks (CR-10):** no anti-pattern matches. No new loop or per-iteration I/O introduced; the predicate is an in-memory check inside an existing fail-soft directory walk.

### Findings in the Neighbours

None. Neighbours considered: `productScope.ts` (consumes the product roll-up), `brainFs.ts` (provides the shared fs helpers), `routes.products.ts` (calls `readProducts`), `startFromIntent.ts` (`ResolvedProject` type). All exercised by the regression run (35/35 green across `readProducts`, `resolveProjectRepo`, `productScope`, `routes.products`, `readBrain`). No pre-existing gap exposed by this diff.

### Watch List

- The two `readEntitiesOfKind` helpers (one in `readProducts.ts`, one in `resolveProjectRepo.ts`) are near-duplicates that pre-date this WP. This WP correctly added the *status filter* to both via the shared predicate rather than deepening the duplication. Extracting the shared directory-walk helper itself would touch `brainFs`'s seam and is out of this WP's Contract scope — noted for a future reuse pass, no delta.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none found under `.security/{project}/`.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `npx tsc --noEmit -p server`; `npx eslint <5 changed files>`. Head: 0 errors both. Base is the unchanged read paths (no `sys_status` filter); delta introduces no errors. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 135 lines, 5 files** (≤200 lines AND ≤5 files — within carve-out).
- [✓] **CR-03 Full-file reads.** All 5 changed files read end-to-end this session (3 are >50 lines: `readProducts.ts`, `resolveProjectRepo.ts`, `readProducts.test.ts`). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings; each lens "nothing surfaced" entry lists the checks run.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all >50-line files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives listed. Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (1 concern, 1 commit type, 2 dirs). PH-02 Size: clean (135 lines / 5 files). PH-03 Safety: clean (migrations 0, schemas 0, secrets 0, infra 0). PH-04 Completeness: clean (new source has tests). PH-03 high → CR-06 auto-downgrade: not fired.

#### Run details

- **Diff source:** `git diff change/feat-user-level-product-store-settings` (working tree, pre-commit at Step 6.5) + untracked `isActiveStatus.ts`.
- **Neighbour expansion:** git grep on `readProducts` / `resolveProjectRepo` / `isActiveStatus` consumers.
- **Neighbour cap:** 4 of 4 considered, 0 excluded.
- **Scanners run:** tsc, eslint. Gitleaks/Semgrep/Trivy not run (no new dependency, no secret-shaped content, no Dockerfile — signals absent; recorded as scoped coverage, not a gap).
- **Lens dispatch:** single-reader (carve-out).
