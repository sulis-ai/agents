# Code Review: WP-006 — the closing integration proof for the verification substrate

> **Timestamp:** 2026-06-08T231422Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** feat/wp-006-integration-bundle-carries → change/feat-verification-substrate
> **Files changed:** 1 (new test file, 339 lines)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one end-to-end test that proves the whole verification substrate
hangs together — a freshly-authored scenario goes through the real author → save →
load → run path, and the test checks that the new "isolation" and "verdict-invariant"
settings survive the round-trip and that a browser-driven step is correctly treated as
the deterministic ("scripted") kind. It is test-only: no product code changed. The
build is clean (linter, formatter, and type-checker all pass) and the test genuinely
bites — it was confirmed to fail if the underlying behaviour regresses, so it is real
coverage, not a rubber stamp. Nothing needs attention before merge.

## What to fix

No issues that need attention.

One thing worth knowing (already captured, no action needed for this change): while
writing the test I found that the shared building-block definition for tools doesn't
yet list "browser" as a recognised driver kind, even though the running code does. That
mismatch belongs to the earlier browser-integration piece of work, not this one, so it
has been logged as a separate finding and the test works around it cleanly. No fix is
owed here.

## How this pull request is shaped

**Size — clean.** One new file, 339 lines, single concern.

**Scope — clean.** A single `test:` change, one module. Nothing mixed in.

**Safety — clean.** No migrations, no schema/IDL changes, no infrastructure files,
no secrets.

**Completeness — clean.** This change *is* a test; there is no untested new
production code (there is no new production code at all).

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the single
changed file (339 lines) was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (one related gap registered as SF-164c3e5f — out of this WP's scope)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — drives via the public `run_scenario` seam + real adapter |
| Security | 0 | 0 | none — injected fake transports, no secrets, no real external calls |
| Quality | 0 | 0 | none — ruff/mypy clean, the change is itself a test |

### Build Verification (CR-01)

Mechanical baseline run on HEAD (the project's configured linter is `ruff`; the
project is stdlib-only scripts with no mypy/tsc in the gate):

- `ruff check tests/integration/test_substrate_bundle_e2e.py` → All checks passed (exit 0)
- `ruff format --check …` → already formatted (exit 0)
- `mypy --ignore-missing-imports …` → Success, no issues (advisory; not in the project gate)

Raw outputs in `tool-outputs/`. No PR-introduced errors. Build Verification section
empty → no CR-06 auto-downgrade.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {test}; module_fan_out 1            → clean
Size (PH-02):         lines +339 / -0; files 1                              → clean
Safety (PH-03):       migrations 0; schemas 0; infra 0; secrets 0           → clean
Completeness (PH-04): new_source_without_test 0 (the file IS a test)        → clean
```

No PH-03 high → no CR-06 auto-downgrade rule 4.

### Findings in the Changes

None.

Lens notes (CR-07 completion output):

- **Architecture lens: nothing surfaced.** Checks run: dependency-direction (the test
  imports only the public substrate seams — `assemble_scenario_graph`,
  `LocalFileEntityAdapter`, `load_scenario_journey`, `run_scenario`,
  `format_founder_summary` — and never reaches into infrastructure internals); no new
  singletons; no circular imports; the injected `browser`/`run` transports follow the
  established test seam (parity with main's own browser unit tests). The test uses the
  REAL adapter + REAL vendored schema for the round-trip (MEA-09 — no schema mock) and
  the REAL saved_record for the invariant (ADR-003 — no record mock).
- **Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no auth surface,
  no injection — the one subprocess cmd is the literal `true`; the browser transport is
  an injected fake; no `file://`/SSRF surface), DAT-03 (no secret-shaped strings — scan
  clean). No real external calls; no Playwright import fires (verified in a fresh
  interpreter: `playwright` never enters `sys.modules`).
- **Quality lens:** (1) Build Verification follow-up: none. (2) JSX/template scan: N/A
  (Python). (3) Dead surface: none — every helper (`_author_substrate_bundle`,
  `_scripted_tool`, `_emit_bundle_with_new_fields`, `_fake_browser`, `_fake_run`) is
  referenced; both tests call the shared builders. (4) Contract drift: none — the test
  asserts the documented `AcceptanceResult` fields (`tiers`, `isolation_rung`,
  `invariant_result`, `verdict`, `steps`). (5) Test-coverage observation: the change is
  itself the integration test; it bites (proven: tier assertion fails when
  `SCRIPTED_KINDS` lacks `browser`; invariant assertion fails on saved_record mismatch).
  (6) Style: clean, descriptive names, thorough module docstring explaining the seam
  choices. (7) CR-10 performance: no anti-pattern matches — the only loops
  (lines 179/181) are bounded in-memory iterations over a freshly-authored bundle's
  steps/workflows during test setup; `foundation.save` writes to a temp store, not a
  hot path.

### Findings in the Neighbours

None. The test consumes existing substrate modules read-only; it introduces no new
caller/callee coupling that exposes a pre-existing gap. (The tool-schema enum gap is a
contract artifact gap, registered as SF-164c3e5f, owned by WP-007 — surfaced once, not
re-listed per site.)

### Watch List

- SF-164c3e5f — the vendored `foundation/tool.schema.json` `implementation_kind` enum
  lacks `browser`, out of sync with the runtime `IMPLEMENTATION_KINDS`. No
  failing-characterisation-test delta drafted here because the fix is a schema/contract
  edit owned by WP-007's reconciliation scope, not this test-only WP. Captured in the
  findings register; auto-drafted as WP-AUTO-164c3e5f.

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for this project.
- Registered finding: SF-164c3e5f (`.security/verification-substrate/findings/`).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `ruff format --check` (the
  project's configured linter; stdlib-only scripts, no tsc/mypy in the gate) + advisory
  `mypy --ignore-missing-imports`. HEAD: 0 errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Single-reader pass. Diff is 339 lines in 1 file. This
  is above the 200-line carve-out line but is a single self-contained test module with
  no production code and no neighbour ring to fan out across; the file was read
  end-to-end (authored + lint + review in one reader). Recorded here per CR-02.
- [✓] **CR-03 Full-file reads.** The one changed file (339 lines) read end-to-end.
  Unread files: none.
- [✓] **CR-04 Evidence discipline.** Findings: none; lens notes cite the specific
  symbols/lines examined.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired
  (Build Verification empty; file read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each produced
  explicit output above (all "nothing surfaced" with checks enumerated).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: clean (339/1).
  PH-03 Safety: clean (0/0/0/0). PH-04 Completeness: clean (the file is a test). No
  PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git working tree vs `change/feat-verification-substrate` (new untracked file).
- **Neighbour expansion:** none required — test-only, no production symbols changed.
- **Neighbour cap:** N/A.
- **Scanners run:** ruff (lint+format), mypy (advisory), manual secret-pattern grep, CR-10 loop scan.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not installed in this environment — manual grep substitute used for the (zero) secret surface; noted as a coverage substitution, not a gap (no secret-bearing surface exists in a test that injects fakes).
- **Single-reader pass:** yes (justified above).
