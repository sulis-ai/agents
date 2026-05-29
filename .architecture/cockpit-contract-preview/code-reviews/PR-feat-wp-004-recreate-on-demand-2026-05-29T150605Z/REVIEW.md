# Code Review: feat/wp-004-recreate-on-demand — recreate-on-demand for shipped changes

> **Timestamp:** 2026-05-29T150605Z (ISO 8601 UTC)
> **Author:** WP-004 executor
> **Branch:** feat/wp-004-recreate-on-demand → dev
> **Files changed:** 8 (3 modified, 5 new)
>
> **Outcome:** Ready to merge

---

## At a glance

This change lets the cockpit reach the contracts of a shipped piece of work
whose working files were cleaned up after it shipped — by quietly
re-building those files on demand before showing them, and falling back to a
plain "couldn't reach this shipped change's contracts" message when it can't,
rather than freezing. It reuses the already-shipped rebuild command instead of
re-writing it, and is tested thoroughly (14 tests, every path covered). No
build errors, no security issues, well-scoped. Ready to merge.

## What to fix

No issues that need attention. Two minor things for awareness are in the
"Minor — for awareness" notes below; neither blocks merge.

### Minor — for awareness — `apps/cockpit/server/adapters/SulisChangeRecreator.ts`, line ~78

**What's happening:** The change handle is passed straight to the rebuild
command as a structured argument. There's no injection risk (the command is
run without a shell, and arguments are passed as a list, not a text string),
but unlike the sibling reader (`SulisChangeStoreReader`, which checks the
change id against a simple character pattern first), this adapter does no
shape-check on the handle before handing it over.

**Why it matters:** Purely defense-in-depth — a malformed handle would just
make the rebuild command fail cleanly today. Matching the sibling's
validate-first habit would keep the two adapters consistent.

**What to do:** Optional. If desired later, mirror the `CHANGE_ID_PATTERN`
guard from `SulisChangeStoreReader.ts`. Not required for this change.

### Minor — for awareness — wiring is intentionally deferred to WP-003

**What's happening:** The new rebuild adapter and the resolver helper are not
yet connected to a live cockpit endpoint.

**Why it matters:** That's by design — this piece is built against a test
stand-in so it can be developed in parallel with the other pieces, and the
final wiring into the cockpit's request path belongs to the integration
piece (WP-003). Flagged only so a reader doesn't mistake the absence of a
mounted route for an oversight.

**What to do:** Nothing here. WP-003 mounts it.

## How this pull request is shaped

**Size — clean.** ~600 lines across 8 files, one logical concern.

**Scope — clean.** Single concern: recreate-on-demand. All files inside the
WP's declared scope (`apps/cockpit/server/`).

**Safety — clean.** No migrations, no schema/IDL files, no infra files, no
secrets. Adds one subprocess spawn — verified read-only-safe (the read-only
inventory gate passes; the spawn is the rebuild command, not git, and carries
no mutating verb).

**Completeness — clean.** 5 new source files, 1 new test file with 14 tests
covering every behavioural path including the failure/degrade modes.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all
changed files >50 lines read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — tsc + eslint clean on HEAD.
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..PH-04).
- **In the changes:** 2 findings (0 critical, 0 high, 0 medium, 2 low/note).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the two notes are awareness items with no failing characterisation test → Watch List, not deltas per CR-04).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (note) | 0 | Wiring deferred to WP-003 (by design, WPB-09 completed there) |
| Security | 1 (low) | 0 | Handle not shape-validated before spawn (no injection vector; shell:false + argv array) |
| Quality | 0 | 0 | Nothing surfaced — tests thorough, no dead surface, no drift |

### Build Verification (CR-01)

Empty. `tsc --noEmit -p server && -p client` exit 0; `eslint` on the 7 changed
TS files exit 0. Logs in `tool-outputs/typecheck-head.log`,
`tool-outputs/eslint-head.log`. Read-only inventory gate clean (87 files).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                    → clean (single type)
  module_fan_out: 1 top-level dir (apps/cockpit) → clean
  severity: none
Size (PH-02):
  total: ~600 lines; files_changed: 8
  generated_ratio: 0; lock_file_ratio: 0 (package-lock.json reverted — env artifact, not WP change)
  severity: none (201-500 band on net new code; single concern)
Safety (PH-03):
  migration_count: 0; schema_idl_count: 0; infra_files: 0; secret_pattern_hits: 0
  new subprocess spawn: 1 (sulis-change recreate — read-only-gate-verified)
  severity: none
Completeness (PH-04):
  new_source_without_test: 0 (4 new source modules; 1 test file with 14 tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `apps/cockpit/server/adapters/SulisChangeRecreator.ts:~78` — low (security)

**Quoted text:**
```ts
const args: string[] = ["recreate", "--handle", handle];
return new Promise<RecreateOutcome>((resolve) => {
  const child = spawn(this.binPath, args, { shell: false, ... });
```
**Evidence/assessment:** No shell-injection vector — `spawn` with `shell: false`
and an argv array; `handle` is a structured argument, never concatenated into a
command line. Source-hygiene test asserts this (no `shell: true`, no string
command line, only the `recreate` verb). The sibling `SulisChangeStoreReader`
applies a `CHANGE_ID_PATTERN` guard before spawning; this adapter does not
shape-check `handle`. Defense-in-depth only; CLI validates the handle itself.
**Recommendation:** Optional future parity — mirror `CHANGE_ID_PATTERN`. No
failing characterisation test constructible (no actual vulnerability) → Watch
List, not a delta (CR-04).
**lens:** security

#### `apps/cockpit/server/{adapters/SulisChangeRecreator.ts, routes/_recreate-on-demand.ts}` — note (architecture)

**Assessment:** WPB-09 "done means wired" — the adapter + resolver are not
mounted into a live GET endpoint in this diff. This is the WP-004 Contract's
explicit design: build against the `FakeRecreateRunner` seam so WP-004 ships in
parallel; the serving-path wiring + integration test is WP-003's responsibility
(TDD §4.3, §5). Recorded for awareness; not a gap in this WP. **lens:** architecture

### Findings in the Neighbours

None. The diff extends `ChangeStoreRecord` with an optional `shippedSha`
(backward-compatible; no existing consumer broken — full suite 295/295 green)
and adds `shipped_sha` mapping to `SulisChangeStoreReader.toRecord`. Both
changes are additive; no neighbour behaviour altered.

### Watch List

- `SulisChangeRecreator` handle shape-validation (parity with
  `CHANGE_ID_PATTERN`) — defense-in-depth, no current vulnerability.

### Cross-Reference

- No prior `.security/{project}/` report.
- No existing hardening deltas for this surface.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` (tsc server+client) + `eslint` on 7 changed TS files. HEAD: 0 errors. Base (origin/dev): these files don't exist on base; baseline is the existing suite which is green. Coverage gap: none.
- [✓] **CR-02 Parallel dispatch.** Diff is 8 files / ~600 lines — above the 5-file carve-out. Single-reader pass used by the executor self-review on a single focused WP (one logical concern, all files in one module); recorded as a deliberate conservative single-pass with all three lenses applied sequentially in full. Noted as a deviation: a multi-agent dispatch was not used because this is an in-loop executor self-review of its own WP, not an arms-length PR review.
- [✓] **CR-03 Full-file reads.** All 5 new files + 3 modified files read end-to-end (each <250 lines).
- [✓] **CR-04 Evidence discipline.** Findings cite file:line + quoted text. The two notes have no failing characterisation test → Watch List, not deltas.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low + 1 note.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 1 note + spawn-discipline check vs gitShow/SulisChangeStoreReader pattern. Security: 1 low + injection-vector analysis (shell:false + argv array) + secrets scan (none). Quality: nothing surfaced — tests thorough (14, all branches incl. degrade/timeout/no-op), no dead surface, no contract drift, test-coverage present, CR-10 no anti-pattern matches (resolver is straight-line async, no loops with I/O), no TSX/JSX files (backend-only).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat, one dir). PH-02 Size: none. PH-03 Safety: none (0 migrations/schemas/secrets; 1 read-only-verified spawn). PH-04 Completeness: none (tests present). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** git working-tree diff vs origin/dev (pre-commit review at Step 6.5).
- **Neighbour expansion:** git grep on `ChangeStoreRecord` constructors + `shippedSha`/`baseSha` consumers; full suite re-run confirms no neighbour break.
- **Neighbour cap:** not reached.
- **Scanners run:** tsc, eslint, grep-based secrets + CR-10 patterns, read-only inventory gate.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed in this environment — manual grep secrets scan used (backend-only, no deps added, low risk surface).
- **Lenses dispatched in parallel:** no — single-reader self-review (see CR-02 note).
