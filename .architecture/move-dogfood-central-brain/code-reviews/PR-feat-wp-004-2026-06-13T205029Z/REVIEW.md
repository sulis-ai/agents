# Code Review: feat/wp-004-remove-sulis-brain-pin — Remove Sulis's brain_location pin (the fork)

> **Timestamp:** 2026-06-13T205029Z (ISO 8601 UTC)
> **Author:** iainn
> **Branch:** feat/wp-004-remove-sulis-brain-pin → change/move-dogfood-central-brain
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change does one thing and does it cleanly: it removes the single line that pinned Sulis's own brain to a folder inside the repo, so Sulis now stores its captures in the same central place an installed user would. With that line gone, the safety test that was waiting for this moment now passes on its own, and the change correctly removes the "expected to fail" marker that was holding it in place. No build errors, no lint errors, nothing risky. There is nothing to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** Two files, 16 lines added, 43 removed. Small and focused.

**Scope — clean.** Every line serves the same single purpose: remove the pin and let the gated test go green.

**Safety — clean.** No database migrations, no schema files, no infrastructure changes, no secrets. The only configuration touched is the one line the work exists to remove.

**Completeness — clean.** No new source files needing tests; the change is a deletion that flips an existing, already-written test from "expected to fail" to "passing". The full unit suite (3054 tests) and the brain-integration tests all pass.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both changed files read end-to-end; all lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01 — ruff clean on BASE and HEAD; compileall OK)
- **PR Hygiene:** 0 findings (PH-01..PH-04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

Mechanical baseline ran ruff 0.15.14 on the changed Python file at both BASE and HEAD, plus `python3 -m compileall`.

- ruff BASE (`change/move-dogfood-central-brain` copy of the test file): `All checks passed!`
- ruff HEAD (working tree): `All checks passed!`
- compileall HEAD: OK

The notable risk for this change — that removing `import pytest` would leave an unused import or, conversely, that `pytest` was still referenced after the decorator was removed — is disproven: ruff's F401 (unused import) and F821 (undefined name) checks both pass on HEAD. `pytest` is no longer referenced in code (the surviving mention is a prose comment on line ~68). Fixtures `tmp_path` and `monkeypatch` are framework-injected and require no import.

No PR-introduced errors. Build Verification section is empty.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {delete}                 → single concern
  module_fan_out: 2 dirs (.sulis/, plugins/sulis/scripts/tests/unit/)
  severity: clean

Size (PH-02):
  lines_added: 16, lines_removed: 43, total: 59
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: clean (≤200 lines, ≤5 files)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: clean

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: clean (deletion flips an existing test to green; no new behaviour to cover)
```

### Findings in the Changes

None.

**Architecture lens:** nothing surfaced. Checks run — no new imports, no new module-level singletons, no new external calls, no dependency-direction changes. The diff only *removes* a config value and a test marker; the resolver (`_brain_location.py`) is untouched, so the precedence chain is unchanged (ADR-001). Verified the 11 precedence tests in `test_brain_location.py` still pass.

**Security lens:** nothing surfaced. Primitives checked — SEC (access control / injection / secrets exposure): no secrets added or removed; the removed line is a relative path constant, not a credential. SC (dependency CVEs): no dependency changes. No new logging, no new endpoints, no new external calls. The change narrows where Sulis writes its own captures (to the user-level settings home) — no new data exposure.

**Quality lens:**
1. Build Verification follow-up: no CR-01 findings to translate.
2. JSX/template identifier scan: N/A (no TSX/JSX/Vue/Svelte files).
3. Dead-surface: the `import pytest` removed was the only consumer of the import after the decorator deletion — correctly removed, no dead surface left behind.
4. Contract-drift: none. The test docstring was updated to present tense to match the now-green behaviour (prose accuracy, not a contract change).
5. Test-coverage observation: the change is itself driven by an existing test (`test_sulis_captures_resolve_central`), which transitions from xfail to pass. The strict-xfail safety worked exactly as designed — it forced this PR to delete the marker. Good test-first discipline.
6. Style/readability: clean. The replacement comment is a single accurate line pointing to ADR-001.
7. Performance procedural checks (CR-10): no anti-pattern matches — no loops, no DB/RPC/filesystem calls in the diff.

### Findings in the Neighbours

None. The one-hop neighbour is `_brain_location.py` (the resolver that reads the now-absent field). It is unchanged and already has explicit coverage for the absent-field fall-through (`test_absent_contract_field_falls_to_default` in `test_brain_location.py`), which passes. The resolver's docstring references `brain_location: .brain/instances` only as a generic escape-hatch *example* of the capability, not as an assertion about Sulis's own config — correct as-is.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none found under `.security/move-dogfood-central-brain/`
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` on the changed `.py` at BASE and HEAD; `python3 -m compileall`. Base: clean. Head: clean. Coverage gap: no type-checker configured for this stdlib-only tooling (per repo-contract `type_check: ""`); ruff covers F401/F821, the load-bearing checks for this diff.
- [✓] **CR-02 Single-reader pass justified by diff size: 59 lines, 2 files** (within the ≤200 line / ≤5 file carve-out).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (repo-contract.yml 62 lines; test file 82 lines post-edit). Unread files: none.
- [✓] **CR-04 Evidence discipline.** All observations cite file:line / quoted tool output. No findings to ground (clean diff).
- [✓] **CR-05 Severity rubric.** Applied — 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; both files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (+ rationale). Security: nothing surfaced (+ primitives checked). Quality: all of items 1–5 and 7 produced; 6 clean.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single delete concern). PH-02 Size: clean (59 lines / 2 files). PH-03 Safety: clean (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: clean (deletion flips existing test green). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff change/move-dogfood-central-brain` (working tree — branch has no commits yet at review time; reviewing staged+unstaged changes pre-commit per Step 6.5)
- **Neighbour expansion:** git grep / manual (resolver `_brain_location.py` is the sole one-hop neighbour)
- **Neighbour cap:** 1 of 1 considered, 0 excluded
- **Scanners run:** ruff 0.15.14 (lint); python compileall (syntax)
- **Scanners unavailable:** mypy/pyright not configured (stdlib-only tooling per plugin contract); Gitleaks/Semgrep/Trivy not run — diff has no secrets, no dependency changes, no new code surface to scan
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out
