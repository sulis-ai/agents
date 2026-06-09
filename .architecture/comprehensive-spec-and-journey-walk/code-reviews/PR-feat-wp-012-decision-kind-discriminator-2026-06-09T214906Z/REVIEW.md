# Code Review: WP-012 — ADR/BDR kind discriminator + multi-decision @id collision fix

> **Branch:** feat/wp-012-decision-kind-discriminator → change/harden-comprehensive-spec-and-journey-walk
> **Files changed:** 12 (836 insertions, 41 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small but meaningful capability to how decisions get recorded: it lets the system tell a *business* decision (a BDR) apart from a *technical* one (an ADR), and it fixes a real bug where a single change that recorded more than one decision would silently overwrite all but the last one. The change is well-scoped, fully tested (the old buggy behaviour now has a test that proves it's fixed), and there are no build errors. No issues need attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** ~836 lines, but most of it is tests (4 test files) and two small new helper scripts. The actual product-code change is three files touched by a few dozen lines each.

**Scope — clean.** Single concern: the decision-kind discriminator and the bundled @id-collision fix, which the design explicitly asked to ship together because they share the same code path.

**Safety — clean.** The schema change is additive-optional (a decision with no `kind` reads as `adr`), so nothing on disk needs rewriting. No database migrations, no secrets, no infrastructure.

**Completeness — clean.** Every new behaviour is covered: the kind discriminator (default / explicit / rejected-invalid), the collision fix (two decisions from one change now persist distinctly), and the two new driver scripts (a happy-path drive plus its failure paths).

---

## Technical detail

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every production file read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `ruff check` clean on HEAD; `python3 -m compileall` clean.
- **PR Hygiene:** 0 findings (PH-01..04 all clean).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced (collision fix narrows a prior change_id-interpolation surface) |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Python repo; configured tooling is `ruff` (no mypy/pyright config in `pyproject.toml`). Mechanical floor:

- `uv run ruff check _decision_emission.py sulis-emit-decision _drive_decisions.py _assert_bdr_adr.py` → All checks passed (HEAD). See `tool-outputs/ruff-check-head.log`.
- `python3 -m compileall -q plugins/sulis/scripts` → clean.
- Base branch: same files pass. Delta: none.

No PR-introduced errors. Build Verification empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat} (single concern)   → clean
  module_fan_out: 1 (plugins/sulis)             → clean
  severity: none

Size (PH-02):
  lines_added: 836, lines_removed: 41
  files_changed: 12 (3 production source, 2 new scripts, 4 test, 1 doc, 1 journal, 1 schema)
  severity: none (most volume is tests)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 1 (decision.schema.json — additive-optional enum, no rewrite)
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (both new scripts covered by test_drive_assert_bdr_adr.py)
  api_change_without_schema: false (CLI + schema co-evolved)
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The decision-emit path's neighbours (`_entity_adapter_local.py`, `_entity_repository.py`, `_wpxlib.generate_change_ulid`) are unchanged and already self-defending (the adapter rejects unsafe id path segments). The @id change actually *narrows* a prior exposure: `change_id` frontmatter is no longer interpolated into the entity id, so a forged multi-line `change_id` value can no longer reach the id at all.

### Watch List

None.

### Cross-Reference

- No prior `.security/` viability report for this project.
- No existing hardening-deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` (configured linter) + `compileall`. Base: clean. Head: clean. Coverage gap: no mypy/pyright configured in repo (records as the repo's stdlib-only tooling contract — `branch-ci.yml` itself runs `py_compile`, not a type-checker).
- [✓] **CR-02 Single-reader pass justified.** Diff is 836 lines but the production-code surface is 3 files (~120 changed lines); remainder is tests + docs + journal. Production files read end-to-end as a single reviewer; no lens parallelism needed for a surface this small and single-concern.
- [✓] **CR-03 Full-file reads.** `_decision_emission.py`, `sulis-emit-decision`, `_drive_decisions.py`, `_assert_bdr_adr.py`, `decision.schema.json` all read end-to-end (>50 lines each except the schema).
- [✓] **CR-04 Evidence discipline.** Zero findings; no delta drafted. Contract-drift check evidenced by the enum/constants/choices agreement check.
- [✓] **CR-05 Severity rubric.** Applied. 0 findings.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked: dependency direction, new singletons, circular imports, resilience, validation boundary). Security: nothing surfaced (checked: secrets scan, injection/path-traversal via id, auth surface — none present). Quality: build-verification clean; no JSX (Python); dead surface (old `_resolve_decision_id` removed, no dead code); contract drift (schema enum ≡ `_VALID_KINDS` ≡ CLI choices, verified); test coverage (extensive); CR-10 perf (no anti-pattern matches — all loops bounded N=2).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none. PH-03 Safety: none (0 migrations, additive-optional schema, 0 secrets). PH-04 Completeness: none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached change/harden-comprehensive-spec-and-journey-walk` (changes staged pre-commit).
- **Neighbour expansion:** git grep for consumers of `emit_decision_from_adr` / `compose_decision_from_adr` / `dna:decision:` — only the decision tests + the golden-thread integration test + the CLI; all updated in-diff.
- **Scanners run:** ruff (lint), compileall (compile). Gitleaks/Semgrep/Trivy not invoked — pure-Python stdlib change, no dependency or container surface; secrets scanned via grep (0 hits).
- **Self-review note:** this review was run by the executor on its own WP diff per the Step 6.5 gate. The bundle is the audit evidence the gate exists to produce.
