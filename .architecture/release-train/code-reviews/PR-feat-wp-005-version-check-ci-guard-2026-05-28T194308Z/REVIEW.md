# Code Review: PR-feat-wp-005-version-check-ci-guard — version-check.yml CI guard (advisory-first)

> **Timestamp:** 2026-05-28T194308Z (ISO 8601 UTC)
> **Author:** WP-005 executor
> **Branch:** feat/wp-005-version-check-ci-guard → change/create-release-train
> **Files changed:** 1
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds one new automated check that fires when someone changes the
plugin. The check looks for a small "what-changed" note (a changeset) and, if it's
missing, prints a friendly warning — but it deliberately does **not** block anything
this round. That warn-only behaviour is the whole point: blocking now would lock the
team out of the next release, because there are already some older changes on the line
with no notes attached. The check is clean, well-scoped, and self-documenting.

One small thing was found and fixed during review: the check was reading GitHub's
event data straight into a shell command. That's a habit worth avoiding even when the
data is safe, and the rest of the project already does it the safer way — so the fix
just brings this file in line. After the fix, nothing else was flagged.

## What to fix

No issues that need attention. The one item found during review was fixed in place
before this report was written.

## How this pull request is shaped

**Size — clean.** One file, ~150 lines. Easy to review thoroughly.

**Scope — clean.** A single new check, one purpose. No mixing of unrelated work.

**Safety — clean.** No database changes, no secrets, no risky configuration. It is a
new automation file, and it cannot block any merge this round by design.

**Completeness — clean.** This is an automation file rather than product code, so the
right kind of proof is "does the check behave as intended?" rather than unit tests.
That was verified two ways: by reading through the logic, and by running the exact
shell steps to confirm a missing note produces a warning and lets the build pass
(rather than failing it).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high/medium/low remaining in the diff; Build Verification
empty; the single file was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all clean)
- **In the changes:** 0 findings remaining (1 low addressed inline before report-write)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single finding was fixed inline, not deferred to a delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced — bounded timeout, pinned action, no secrets, no unbounded calls |
| Security | 0 (1 fixed) | 0 | event-context interpolation into shell (SEC-02) — fixed inline via env-passing |
| Quality | 0 | 0 | nothing surfaced — no CR-10 anti-patterns; advisory-semantics verified |

### Build Verification (CR-01)

Mechanical floor for a GitHub Actions workflow (no tsc/eslint/mypy applicable):

- `python3 -c "import yaml; yaml.safe_load(...)"` on HEAD → parses clean (BASE has no
  such file; entire file is PR-introduced).
- `bash -n` on every `run:` step body → all 3 clean (Resolve base ref / Changeset-presence
  guard / Version-sync check).

PR-introduced errors: **0**. Section empty → no CR-06 Block downgrade.

Coverage gap: `actionlint` and `shellcheck` not installed on the runner. Mitigated by
`bash -n` syntax-checking each run-step body. The repo contract is stdlib-only tooling
(branch-ci.yml's lint is likewise `python3 -c yaml`), so this matches the established
mechanical floor for this codebase.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean (single concern)
  module_fan_out: 1 top-level dir (.github/)   → clean
  severity: none

Size (PH-02):
  lines_added: 156, lines_removed: 0, total: 156
  files_changed: 1
  severity: none (single small file)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 1 (.github/workflows/version-check.yml — the subject)
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (kind:infra — verification gate is workflow-lint +
    advisory-semantics assertion per the WP DoD, not unit tests)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

**F-01 — `.github/workflows/version-check.yml`, step "Resolve base ref" — low (security + quality), ADDRESSED INLINE**

- **Primitive:** SEC-02 (GHA script-injection class).
- **Quoted text (pre-fix):**
  ```bash
  if [ "${{ github.event_name }}" = "pull_request" ]; then
    BASE="${{ github.event.pull_request.base.sha }}"
  ...
    BASE="${{ github.event.before }}"
  ```
- **Assessment:** All three interpolated values are GitHub-controlled and shape-constrained
  (an enum and two 40-char hex SHAs), so this is **not** an exploitable injection vector —
  the script-injection-vulnerable fields are attacker-controlled free text (PR title,
  branch name, commit message), none of which are used here. However, interpolating
  `${{ }}` directly into a `run:` body drifts from the repo's established GHA convention:
  `release-on-merge.yml` passes context through `env:` and references `$VAR` in bash. The
  advisory-guard step in this same file already does it correctly (`env: BASE: ...`).
- **Resolution (CP-01 — default to the established convention):** Moved all three values
  to a step-level `env:` block (`EVENT_NAME`, `PR_BASE_SHA`, `PUSH_BEFORE_SHA`) and
  referenced them as shell variables. Post-fix scan confirms **zero** `${{ }}` expansion
  inside any `run:` script body. Behaviour unchanged — advisory guard still exits 0 on a
  missing changeset; BASE still resolves for both triggers.

### Findings in the Neighbours

Nothing surfaced. The workflow is a leaf automation file; its "neighbours" are the
manifests it reads read-only (`plugin.json`, `marketplace.json`) and the sibling
workflow it mirrors (`release-on-merge.yml`). No pre-existing gaps exposed.

### Watch List

- **Advisory→required promotion is intentionally deferred.** The single `exit 0`
  carries a `TODO(deferred)` marker pointing at ADR-006. This is by design (the WP's
  whole point), not a gap. When promotion happens (a later founder-gated cycle), the
  re-review should confirm version-check is simultaneously added to `main`'s required
  status checks (WP-006 territory).

### Cross-Reference

- **Governing ADR:** `.architecture/release-train/adrs/ADR-006-version-check-advisory-first.md`
  — the advisory-first decision the workflow header encodes.
- **Sibling workflow:** `.github/workflows/release-on-merge.yml` — source of the
  version-sync `jq` pattern and the env-passing convention F-01 was aligned to.
- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** YAML safe_load (HEAD: clean); `bash -n` on all
  3 run-step bodies (clean). No tsc/eslint/mypy applicable to a GHA YAML file. Coverage
  gap: actionlint/shellcheck absent → mitigated by bash -n + stdlib-only repo contract.
  Base: file absent (all PR-introduced). Head: 0 errors.
- [✓] **CR-02 Single-reader pass justified by diff size: 156 lines, 1 file** (within the
  ≤200-line AND ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** The single 156-line file read end-to-end (twice — once
  pre-fix, once post-fix). Unread files: none.
- [✓] **CR-04 Evidence discipline.** F-01 cites file:step and quoted text.
- [✓] **CR-05 Severity rubric.** Applied. F-01 = low (convention drift, non-exploitable);
  no critical/high/medium.
- [✓] **CR-06 Verdict computed.** PASS. Auto-downgrade triggers: none fired (Build
  Verification empty; file read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: timeout bound,
  pinned action, no secrets, no unbounded external calls). Security: 1 finding (SEC-02,
  fixed inline) — primitives checked SEC-02/SEC-06; no scanners available, manual
  injection-surface read performed. Quality: 0 findings + CR-10 performance scan (no
  anti-pattern matches) + test-coverage observation (kind:infra advisory-semantics
  assertion is the gate).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat, 1 dir). PH-02 Size:
  none (156 lines / 1 file). PH-03 Safety: none (0 migrations/schemas/secrets; 1 infra
  file = the subject). PH-04 Completeness: none (kind:infra). No PH-03 high → no CR-06
  auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached` on feat/wp-005-version-check-ci-guard vs
  origin/change/create-release-train (staged, pre-commit).
- **Neighbour expansion:** manual (read-only manifest consumers + sibling workflow); 0
  findings.
- **Neighbour cap:** not reached (3 considered, 0 excluded).
- **Scanners run:** none available (gitleaks/trivy/semgrep/actionlint/shellcheck absent).
- **Scanners unavailable:** actionlint, shellcheck, gitleaks, trivy, semgrep — coverage
  gap recorded; mitigated by YAML parse + bash -n + manual injection-surface read.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out.
