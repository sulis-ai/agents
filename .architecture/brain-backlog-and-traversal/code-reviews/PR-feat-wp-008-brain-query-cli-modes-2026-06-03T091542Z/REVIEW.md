# Code Review: PR-feat-wp-008-brain-query-cli-modes — Add --open/--roadmap/--done/--by-type/--by-state to sulis-brain-query

> **Timestamp:** 2026-06-03T091542Z (ISO 8601 UTC)
> **Author:** WP-008 executor
> **Branch:** feat/wp-008-brain-query-cli-modes → change/create-brain-backlog-and-traversal
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds five new query shortcuts to the existing `sulis-brain-query` command — "what's open", "what's on the roadmap", "what's done", plus two composable filters by type and state. The work is well-scoped: it reuses the shared query helpers added in the prior package rather than re-inventing the rules for what counts as "open" or "done", the output format is identical to the existing commands, and every new shortcut is covered by tests. No build errors, no issues that need attention before merge.

## What to fix

No issues that need attention.

One thing worth being aware of (not a blocker): the "open" and "done" shortcuts ask the data store the same question once per status they care about — for example "done" looks for finished items and verified items as two separate passes over the same folder. With today's small data sizes this is instant. If the store ever grows very large, this is the kind of thing to revisit, but the underlying query layer is already designed to be swapped out for something faster at that point without touching this command.

## How this pull request is shaped

**Size — clean.** Small and focused: ~100 lines of new command logic plus one new test file. Easy to review thoroughly.

**Scope — clean.** Single concern: surfacing existing query capabilities through the command line. One `feat:` change.

**Safety — clean.** No database migrations, no schema/contract files, no infrastructure changes, no secrets.

**Completeness — clean.** New behaviour ships with a new test file covering all five modes, the empty-store case, the mutual-exclusion guard, and a regression check that the existing modes still behave.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both changed files read end-to-end; all three lenses produced output. No auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high, 0 medium, 0 note (CR-09 / PH-01..PH-04 all clean)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single low finding is benign-in-context per CR-10; recorded on the Watch List, no delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (consumes the WP-007 read seam; ADR-006 single-source honoured) |
| Security | 0 | 0 | — |
| Quality | 1 (low) | 0 | Repeated per-state full-tree walk in `--open`/`--done` (CR-10, benign at documented N) |

### Build Verification (CR-01)

None. `ruff check` clean on both BASE and HEAD; `py_compile` clean on HEAD. Repo CI lint profile is `ruff check` + `py_compile` (branch-ci.yml: "lint = manifest JSON validity + py_compile"); `ruff format` is not a repo gate (the pre-existing CLI also "would reformat", confirming format is not enforced). Raw logs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 top-level dir (plugins/)   → clean
  severity: none

Size (PH-02):
  lines_added: ~101 (CLI) + ~190 (new test); lines_removed: 0
  files_changed: 2
  generated_ratio: 0
  lock_file_ratio: 0
  severity: none (within carve-out)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (CLI change ships with test_brain_query_cli_modes.py)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `plugins/sulis/scripts/sulis-brain-query:184-204` — low (quality, CR-10 pattern "repeated invariant scan in loop")

**Quoted text:**
```python
def _find_in_states(finder, base_dir: Path, domain: str, states) -> list[dict]:
    return [
        inst
        for state in sorted(states)
        for inst in finder(base_dir, domain=domain, state=state)
    ]
```
Each `finder(base_dir, domain=…, state=state)` call (`find_requirements` / `find_opportunities`) re-walks the entire entity-type subtree (`_find_typed` → `find_entities` → `iter_entities`). So `--done` walks the `requirement/` dir twice (`_DONE_REQUIREMENT_STATES = {implemented, verified}`); `--open` walks `requirement/` once + `opportunity/` once.

**Why it's low / benign-in-context (CR-10 downgrade):** The multiplier is a fixed small constant (`_DONE` = 2 states; `_OPEN_*` = 1 each), not data-dependent. `_brain_query.py` documents N < 200 instances today (acceptable to N < ~5000) and the flat-file walk as the deliberate "boring choice" with a documented swap-behind-the-signature plan when N hurts. At N=200 with a 2× constant the cost is sub-millisecond. The single-walk fix would require a set-membership predicate (`state in STATES`), but the WP-007 seam only exposes a single-`state=` kwarg (ADR-006); widening it is a WP-007 seam change, out of scope for WP-008, and unjustified at current N. Computing the open/done set inside the CLI to do one walk would re-derive the state→view mapping the CLI is explicitly forbidden from owning (ADR-006). **No delta; Watch List.**

### Findings in the Neighbours

None. The neighbour ring (`_brain_query.py` — the seam the CLI calls into) is unchanged by this diff and already covered by `tests/unit/test_brain_query_views.py`.

### Watch List

- **Repeated per-state full-tree walk** (above). Theoretical at current N; the seam's documented impl-swap is the right place to address it if N grows. No failing characterisation test constructible at current N (perf is sub-threshold), so per CR-04 it stays a note, not a delta.

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this project
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check` + `py_compile` (the repo's configured lint profile per branch-ci.yml). BASE: 0 errors. HEAD: 0 errors. Coverage gap: none. `ruff format` intentionally excluded — not a repo gate.
- [✓] **CR-02 Single-reader pass justified by diff size:** ~101 lines (CLI) / 2 files, within the ≤200-line / ≤5-file carve-out. Both files read end-to-end.
- [✓] **CR-03 Full-file reads.** Both changed files (`sulis-brain-query` 233 lines, `test_brain_query_cli_modes.py` ~196 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line and quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks run: domain→infra imports, singletons, circular imports, ADR-006 single-source mapping, --roadmap base-dir resolution). Security: nothing surfaced (primitives checked: SEC-01..07 access/injection/validation/secrets — input is argparse-constrained `--by-type` choices + equality-only `--by-state`; no eval/path-traversal/network/DB). Quality: 1 low finding + dead-surface scan (none) + contract-drift scan (envelope matches; count==len in every branch) + test-coverage observation (fully tested) + CR-10 perf scan (1 benign match documented).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat, 1 top dir). PH-02 Size: none (~291 lines/2 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (new behaviour tested). PH-03 high → CR-06 auto-downgrade: not triggered.

#### Run details

- **Diff source:** `git diff change/create-brain-backlog-and-traversal` (worktree) + untracked new test file
- **Neighbour expansion:** manual (git grep) — the only callee is `_brain_query.py` (unchanged)
- **Neighbour cap:** 1 of 1 considered, 0 excluded
- **Scanners run:** ruff, py_compile (the repo-configured floor); no JS/secret scanners applicable (pure Python, no secrets surface)
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not run — no applicable signals in a pure-Python read-CLI diff with no secrets/deps/containers
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (diff under threshold)
