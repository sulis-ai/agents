# Code Review: WP-002 — Library reads plugin-relative; captures central

> **Branch:** feat/wp-002-library-read-plugin-relative → change/move-dogfood-central-brain
> **Files changed:** 2 (`_scenario_graph_load.py`, `tests/unit/test_scenario_graph_load.py`)
> **Outcome:** Ready to merge (after the two small fixes below, which have been applied)

---

## At a glance

This change makes the shipped "library" of building blocks (the workflows, steps and
tools that come with the plugin) load from where the plugin is installed, while the
captured records (your scenarios) keep loading from your central store. The change is
well-scoped — one module and its tests — with thorough test coverage including the
fresh-install case.

Two small things came up in review and both were fixed in place: the older tests
needed to explicitly opt out of the shipped library so they stay isolated, and a small
efficiency tidy in how the file readers are created. After the fixes, all tests pass.

## What to fix

No issues remain that need attention — both findings below were fixed inline during review.

### Worth fixing (applied) — older tests should stay isolated from the shipped library

**What was happening:** The existing round-trip tests built their own complete copy of
the data in a throwaway folder and read it back. After this change, those reads would
also quietly consult the real shipped library as a fallback.

**Why it mattered:** Tests are most useful when each one is self-contained. A test that
silently leans on the real shipped data can pass or fail for reasons that have nothing
to do with what it's checking.

**What was done:** The older tests now explicitly say "use only this folder" — the same
opt-out the new behaviour already supports.

### Minor (applied) — build the file readers once, not per item

**What was happening:** When resolving the tools a journey uses, the code created a fresh
pair of file readers for every tool.

**Why it mattered:** Harmless at today's scale, but wasteful for journeys with many tools.

**What was done:** The two readers are now created once per load and reused.

## How this pull request is shaped

Small, single-purpose, and tested. Size: 252 lines across 2 files. One concern (the
library/captures read split). No database migrations, no schema changes, no secrets, no
infrastructure files. New behaviour ships with five new tests. Nothing here warrants a
split.

---

## Technical detail

### Verdict

`PASS` (CR-06). No critical/high remaining in the diff; Build Verification empty; both
changed files read end-to-end; all three lenses produced output. The two findings raised
were addressed inline (Path A) and the suite re-run green.

### Summary

- **Build Verification:** 0 PR-introduced errors (ruff clean, py_compile OK, mypy clean on changed file).
- **PR Hygiene:** scope low (single concern, `extend`); size note (252/2); safety low (0 migrations/schemas/secrets/infra); completeness low (source + 5 tests).
- **In the changes:** 2 findings (0 critical, 1 high, 1 medium-low) — both fixed inline.
- **Draft fixes:** 0 (resolved inline, no remediation WP needed).

| Lens | In changes | Top concern |
|---|---|---|
| Architecture | 1 (high) | TestLoadFromStore relied on default LIBRARY_ROOT → test isolation. FIXED. |
| Security | 0 | Path traversal mitigated by adapter `_reject_unsafe_segment`; local-fs only; no secrets. |
| Quality | 1 (medium-low, CR-10) | N+1 adapter construction in tool loop. FIXED (adapters built once, reused). |

### Build Verification (CR-01)

Empty. `ruff check` on both changed files: all checks passed. `python3 -m py_compile`
on the module: OK. `mypy _scenario_graph_load.py`: no errors in the changed file
(pre-existing mypy gaps in `_entity_repository.py` / `_entity_adapter_local.py` are
out of scope — unchanged dependency files; mypy is not a CI gate for this repo).

### Findings in the Changes

#### F-01 `tests/unit/test_scenario_graph_load.py` (TestLoadFromStore) — high (architecture) — RESOLVED

The four `TestLoadFromStore` cases called `load_scenario_journey(base, scenario_id)`,
which after this change defaults `library_root=LIBRARY_ROOT` (the real repo
`.brain/instances`). Those cases emit a complete single-root brain to `tmp_path` and
intend a single-root read; the new default made the real shipped library a silent
fallback. They pass today only because test step names are seed-namespaced (no
collision) and the assertions check exact step-set equality — fragile isolation.

**Resolution (inline):** the four cases now pass `library_root=None`, restoring strict
single-root isolation and exercising the historical contract. A class docstring documents
why. The library/captures split is covered separately by `TestLibraryCapturesSplit`.

#### F-02 `_scenario_graph_load.py` `_find_foundation_entity` + tool loop — medium-low (quality, CR-10) — RESOLVED

`_find_foundation_entity` constructed a fresh `LocalFileEntityAdapter` (captures, and
optionally library) on every call, and it is called once per tool in the resolution loop
— a repeated-construction / N+1 shape.

**Resolution (inline):** `_find_foundation_entity` now takes pre-built adapters.
`load_scenario_journey` constructs the captures + library foundation adapters once and
reuses them across the workflow lookup and every tool lookup. Behaviour unchanged
(captures-win precedence preserved); tests green.

### Watch List

- The `library_root: Path | None = LIBRARY_ROOT` default couples callers to the
  plugin-relative path. This is intentional per the WP Contract ("existing callers
  automatically get the split") and safe (`LIBRARY_ROOT` is `Final[Path]`, immutable).
  No action.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff check (clean), py_compile (OK), mypy on changed file (clean). 0 PR-introduced errors. Coverage gap: typecheck "none configured" per repo CI; ruff used as the lint floor.
- [✓] **CR-02 Parallel dispatch used.** Three lenses (architecture/security/quality) dispatched concurrently as sub-agents. Diff 252 lines / 2 files (> 200-line threshold → parallel required).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end by each lens.
- [✓] **CR-04 Evidence discipline.** Findings cite file + symbol + quoted context.
- [✓] **CR-05 Severity rubric.** 1 high, 1 medium-low. No inflation.
- [✓] **CR-06 Verdict computed.** PASS after inline resolution of both findings. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 1 finding. Security: nothing surfaced (SEC path-traversal/secrets/SSRF checked; local-fs reads, adapter-guarded). Quality: dead-surface (none), contract-drift (default-param assessed safe), test-coverage (5 tests, excellent), style (clean), CR-10 perf (1 finding, fixed).
- [✓] **CR-09 PR Hygiene applied.** Scope low; Size note; Safety low; Completeness low. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/move-dogfood-central-brain` (working tree; commit made at Step 7).
- **Neighbour expansion:** callers `sulis-verify-acceptance`, `sulis-attest-scenario`, `test_substrate_bundle_e2e.py` — all use the default and verified green.
- **Lenses dispatched in parallel:** yes.
- **Findings resolution:** 2 inline fixes; 0 remediation WPs; 0 exceptions. Suite re-run: 11 passed, 97% coverage on the changed module.
