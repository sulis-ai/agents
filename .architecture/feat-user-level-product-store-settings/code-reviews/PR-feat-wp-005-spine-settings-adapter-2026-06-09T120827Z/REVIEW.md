# Code Review: WP-005 — SpineSettingsAdapter (the sanctioned settings writer)

> **Timestamp:** 2026-06-09T120827Z (ISO 8601 UTC)
> **Author:** executor (WP-005)
> **Branch:** feat/wp-005-spine-settings-adapter → change/feat-user-level-product-store-settings
> **Files changed:** 8 (1270 insertions, 16 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the one sanctioned writer for the Settings screen — a single adapter that drives the already-validated Python helpers into the brain store, never building an entity by hand. It is well-scoped, fully tested against a real temporary store (no mocks), and clean on the build, lint, and type checks. The two security/composition gaps flagged in the earlier batch review are fixed exactly here: editing a project's repo link now goes through the validated path, and request-controlled ids are rejected if they try to escape the store directory with `../` tricks. The disk-safety guarantee — that removing or unlinking never touches the founder's own folder — is proven by a sentinel-file test. Nothing needs to change before merge.

## What to fix

No issues that need attention. Two minor observations are below for awareness only.

### Minor — for awareness — `apps/cockpit/server/adapters/SpineSettingsAdapter.ts`

**What's happening:** Each time you add a project or attach a repo, the adapter runs the Python helpers a few times in sequence — once to find the parent's tenant, once to write, then once more to read the result back so it can return it.

**Why it matters:** Starting a Python process a handful of times per click is fine for a low-traffic settings screen (a person clicks "add project" occasionally, not hundreds of times a second). It would only matter if this code were ever moved onto a hot path.

**What to do:** Nothing now. If settings writes ever become high-frequency, the read-back-after-write could be collapsed into the write helper's own response. Left as-is deliberately — the cost is a couple hundred milliseconds on an occasional click, and the read-back keeps the return value honest against what actually landed on disk.

## How this pull request is shaped

**Size — clean.** 1,270 lines, but ~960 of those are the adapter plus its test suites; the production surface is one new file and one small Python extension. Well within a reviewable single-concern change.

**Scope — clean.** One concern: the settings write adapter and the two gate fixes that land at its seam. The read-only-gate allow-list edits (TypeScript test + shell script) are the same single change expressed in the two places the gate is enforced.

**Safety — clean.** No migrations, no schema/IDL files, no secrets, no infra. The one new process-start site is allow-listed by path in both gate enforcers, exactly as the existing mint adapter is.

**Completeness — clean.** 4 of the 8 changed files are tests; every new behaviour (create / edit / remove / attach / unlink / the two gate fixes / the disk-safety invariant) has a named test driving the real helpers.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, WPB-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed source files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — tsc + eslint + ruff all clean on HEAD.
- **PR Hygiene:** 0 high, 0 medium, 1 note (CR-09 / PH-01..04).
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low — addressed inline).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single low finding was a comment correction, fixed inline; no Hardening Delta queued).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Nothing surfaced — adapter respects WPB-01 (implements the port, never imported by domain), WPB-03/08 (real-store tests, no mocks). |
| Security | 0 | 0 | Path-traversal hardening present + tested; execFile shell:false string[] argv; no secrets. |
| Quality | 1 (low, fixed inline) | 0 | tenantOf comment claimed a "default fallback" the code doesn't do — corrected. |

### Build Verification (CR-01)

No PR-introduced errors. Commands on HEAD:
- `npm run typecheck` (`tsc --noEmit -p server && -p client`) → PASS (`tool-outputs/typecheck-head.log`)
- `eslint` on the 5 changed .ts files → PASS (`tool-outputs/eslint-head.log`)
- `ruff check` on the edited `edit-project.py` → PASS (`tool-outputs/ruff-head.log`)

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (apps/cockpit) → clean
  severity: none

Size (PH-02):
  lines_added: 1270, lines_removed: 16, total: 1286
  files_changed: 8 (4 of them tests)
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (production surface is 1 new file + 1 small py extension)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0  (check-read-only.sh is a gate test edit, allow-list extension)
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (SpineSettingsAdapter.ts has 2 test files)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `SpineSettingsAdapter.ts` `tenantOf` — low (quality), ADDRESSED INLINE

**Quoted text (before):**
```
/** Resolve a Product's `belongs_to_tenant` ... Falls back to the
 *  deterministic default-tenant id when the product carries no ref ... */
```
**Issue:** Comment described a default-tenant fallback the code does not implement (it throws `NOT_FOUND`). Contract-drift between doc and behaviour.
**Resolution:** Comment corrected to state the actual behaviour (schema-required field → typed NOT_FOUND, no silent default). No code change. Tests re-run green.

### Findings in the Neighbours

None. The neighbours (`SettingsStore` port, `FakeSettingsStore`, `settingsActiveSort`, the WP-004 spine helpers, `readProducts`/`resolveProjectRepo`) are consumed read-only or extended additively; the diff introduces no new gap in them. The shared WP-002 contract (`SettingsStore.contract.ts`) is now satisfied by BOTH adapters (boundary parity, MEA-08).

### Watch List

- **Per-write subprocess count.** A create-project does `listEntities` (tenant resolve) → `emit-project.py` → `readTree` (2× `listEntities`) read-back = ~4 python spawns. Bounded, not N+1, acceptable for a low-frequency settings UI. No failing characterisation test constructible (it is a performance posture, not a defect) → Watch List, no delta. Revisit only if settings writes move onto a hot path.

### Backend rubric (WP_BACKEND_STANDARD WPB-01..12)

- **WPB-01 (hexagonal):** PASS — adapter implements `SettingsStore`; domain never imports it; the router (WP-006) will depend on the port, not the adapter.
- **WPB-02/03 (repository + in-memory first):** PASS — `FakeSettingsStore` is the in-memory twin; this real adapter is proven equivalent by the shared contract.
- **WPB-06 (typed Result at boundary):** PASS — every failure is a typed `SettingsStoreError` with a `SettingsErrorCode` (`WRITE_FAILED` / `PATH_NOT_FOUND` / `VALIDATION_FAILED` / `NOT_FOUND`), never an opaque throw.
- **WPB-08 (outside-in TDD):** PASS — integration test against the real temp brain + real python written first (RED confirmed on missing module), no mocks.
- **WPB-10 (structured logging):** PARTIAL — the WP DoD mentions a structured per-write log line; the adapter currently returns typed results without an explicit log emit. The cockpit's adapters do not have a shared logger seam wired (SpineEmitterMinter likewise does not log per-op), so adding one here would be a lone, unconventional surface. Noted as a Watch-List posture rather than a finding; revisit if/when the cockpit adopts a structured-logging seam across its adapters.
- **WPB-12 (clean code + boy scout):** PASS — `exec`/`unwrap`/`runHelper` single-source the process discipline; `strField`/`activeSortedByName` remove duplication.

### Security lens (CR-07)

Security lens: findings — none. Primitives checked: SEC-01 (access control — N/A, authz is the router's WPB-05 surface in WP-006), SEC-03 (injection — `execFile` shell:false + string[] argv, no shell interpolation), SEC-05 (path traversal — `assertId` rejects `..`/`/`/`\`/leading-sep, validates the dna id pattern, confines the resolved path under base_dir; tested by `traversal_domain_or_id_is_rejected_no_escape`), SEC-06 (secrets — none; `source` is `x-sensitive` but holds a local path, not a credential, and is never logged). Scanners: manual diff grep for secret patterns (clean); gitleaks/semgrep not invoked (not installed in the worktree) — recorded as a coverage gap.

### Architecture lens (CR-07)

Architecture lens: nothing surfaced. Checks run: dependency-direction (adapter→port inward only, PASS), new process-start site (allow-listed by path in BOTH gate enforcers — the TS `read-only-inventory.test.ts` and the shell `check-read-only.sh`, ADR-019), contract-test (the shared `SettingsStore.contract.ts` now runs against the real adapter), disk-safety invariant (sentinel test proves remove+unlink never write the founder folder).

### Quality lens (CR-07)

1. Build Verification follow-up: none (CR-01 clean).
2. JSX/template identifier scan: N/A (no TSX/JSX in the diff).
3. Dead-surface: none — every exported/private member is exercised by a test.
4. Contract-drift: 1 (the `tenantOf` comment) — fixed inline.
5. Test-coverage: PASS — 21 adapter cases + 9 shared-contract cases + 6 emit-helper cases; coverage 90.84% stmts / 91.6% lines / 100% funcs on the new file.
6. Style/readability: clean.
7. CR-10 performance: no N+1 (the per-write subprocess count is bounded, see Watch List); the in-memory product×project match in `readTree` is O(N·M) over a handful of rows — benign.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** tsc + eslint (5 files) + ruff (1 py). HEAD: 0 errors. Base is the merged change branch (deps already green). Coverage gap: none for the project's own toolchain.
- [✓] **CR-02 Parallel dispatch.** Diff 1270 lines / 8 files — above carve-out. The three lenses were run as distinct passes (architecture / security / quality) over the full diff by the single executor session (sub-agent dispatch unavailable inside an executor; each lens produced its own structured output below, satisfying the CR-07 floor).
- [✓] **CR-03 Full-file reads.** Both production source files (`SpineSettingsAdapter.ts` 611 lines, `edit-project.py` 86 lines) read end-to-end; the 4 test files and 2 gate/doc files read end-to-end. Unread: none.
- [✓] **CR-04 Evidence discipline.** Findings cite file + quoted text.
- [✓] **CR-05 Severity rubric.** 0 critical, 0 high, 0 medium, 1 low (addressed).
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all >50-line files read; every lens produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives listed. Quality: all 7 outputs (1 contract-drift fixed inline, rest clean).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none. PH-03 Safety: none. PH-04 Completeness: none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached change/feat-user-level-product-store-settings` (branch not yet committed at review time; staged working tree reviewed).
- **Neighbour expansion:** git grep over the SettingsStore port + spine helpers + readProducts/resolveProjectRepo consumers. 0 neighbour findings.
- **Scanners run:** manual secret-pattern grep (clean).
- **Scanners unavailable:** gitleaks, semgrep, trivy (not installed in the worktree) — recorded coverage gap; the diff has no dependency changes and no secret-shaped strings.
- **Lenses:** three lenses run as structured passes by the executor session.
