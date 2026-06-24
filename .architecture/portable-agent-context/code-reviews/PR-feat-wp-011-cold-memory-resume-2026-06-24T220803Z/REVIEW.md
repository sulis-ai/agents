# Code Review: WP-011 — Cold-memory resume (regenerate summary on demand + keep memory fresh)

> **Timestamp:** 2026-06-24T220803Z (ISO 8601 UTC)
> **Author:** executor (CH-GJ9KQR WP-011)
> **Branch:** wp/create-portable-agent-context/wp-011-cold-memory-resume-on-demand-summary → change/create-portable-agent-context
> **Files changed:** 7 (3 source, 4 test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change makes the agent's "pick up where you left off" feature work the very
first time you resume — before anything has been saved to the durable store. It
also makes sure a very large saved note (the Working Set) can't blow past the
size limit on the context the agent receives. The change is well-scoped, reads
only through the existing data layer (no new files or services touched), and
comes with a real end-to-end test that drives the actual resume path, plus
focused unit tests. No build errors, nothing to fix.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 730 lines changed, but the bulk is tests and explanatory
comments; the actual logic change is about 120 lines across three files.

**Scope — clean.** A single concern: making rich-context resume robust to a
cold memory. The commit is one logical change.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets.

**Completeness — clean.** Four test files: a new end-to-end cold-memory resume
test, a large-Working-Set budget test, a genuinely-unrecoverable degrade test,
plus unit tests for the new helper. Two existing tests were converted to reflect
the new behaviour.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs)
> for engineers and for downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 high, 0 medium findings (CR-09 / PH-01..PH-04)
- **In the changes:** 1 finding (0 critical, 0 high, 0 medium, 1 low)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single low finding is an awareness note, not a delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (no new IO; dependency direction preserved) |
| Security | 0 | 0 | — (reads redacted store; logs no content) |
| Quality | 1 (low) | 0 | `_fit_participant_context` multi-large-value convergence (benign) |

### Build Verification (CR-01)

Mechanical baseline: `ruff check` + `ruff format --check` on the three changed
source files + four test files. Base: clean. Head: clean (1 unused-import error
fixed during Step 6 before review). No project-level mypy/pyright gate is
configured; mypy run advisorily on the two changed source modules surfaced no
errors in those files. **Build Verification empty.**

Raw outputs: `tool-outputs/ruff-check-head.log`, `tool-outputs/ruff-format-head.log`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 (_session_manager + its tests)
  severity: low

Size (PH-02):
  lines_added: 730, lines_removed: 37
  files_changed: 7 (3 source, 4 test)
  generated_ratio: 0.0
  severity: low (logic surface ~120 lines; remainder tests + docstrings)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (1 new test file + 3 modified test files)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `_session_manager/context_payload.py:161` — low (quality)

**What:** `_fit_participant_context`'s largest-first shrink loop, in the
contrived case of two or more equally-large string values, can take up to K
passes (K = number of context keys) where the `force progress` branch
(`keep_chars = len(value) - 1`) trims only one character per pass.

**Quoted text:**
```python
while fitted and _ctx_tokens(fitted) > max_tokens:
    biggest = max(fitted, key=lambda k: len(str(fitted[k])))
    ...
    if keep_chars >= len(value):
        keep_chars = len(value) - 1  # force progress
```

**Why it's benign:** `participant_context` carries at most a handful of keys in
practice — `working_set` (one string), `brain_entities` (a list, dropped
wholesale), plus small scalars like `change_id`. The single-large-string case
(the realistic one) converges in ONE pass because `keep_chars` is computed from
the remaining budget. The char-by-char path only triggers with multiple
similarly-sized large strings, which the assembler never produces. No hot-path
exposure (this runs at the resume/checkpoint boundary, not per-event).

**Recommendation:** None required. If `participant_context` ever grows to carry
many large strings, revisit to truncate proportionally rather than one-key-at-a-
time. Left on the Watch List, not drafted as a delta (no failing
characterisation test — CR-04).

### Findings in the Neighbours

None. The change reads through the existing `ThreadStore` port and the existing
`_compose_resume_brief` isolation envelope; no neighbour gaps exposed.

### Watch List

- `_fit_participant_context` multi-large-value convergence (above) — theoretical,
  no grounding test, no delta.

### Cross-Reference

- **Existing security report:** `.claude/agent-memory/sulis-security-reviewer/`
  (prior WP-009/010 reviews) — the ADV-1 participant_context-trim folded here
  originates from the WP-009 security review; this change resolves it.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `ruff format --check` on
  all 7 changed files. Base clean, head clean. mypy advisory (no project gate)
  on the 2 changed source modules — no errors in changed files. Coverage gap:
  no enforced type-check gate in repo (recorded).
- [✓] **CR-02 Dispatch shape.** Diff is 7 files / 730 lines but the logic surface
  is 3 source files (~120 lines); test + docstring lines dominate. Three lenses
  run directly against the focused source surface; each produced structured
  output.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end
  (context_payload.py, durable_sink.py, manager.py, all 4 test files). Unread: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line + quoted
  text; no delta drafted (no failing characterisation test → Watch List).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired
  (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — no new IO/fs/
  provider imports; dependency direction (MEA-01/WPB-01) preserved; Move 2
  isolation wrapper scoped + documented; cold-path has a contract/integration
  test. Security: nothing surfaced — reads redacted store via port, logs only the
  change ULID (no content/PII/secrets), ADV-1 trim reduces exposure. Quality: 1
  low finding + dead-surface (none) + contract-drift (the two converted tests
  pin the new contract) + test-coverage (new + converted tests cover the
  behaviour) + CR-10 perf (the one bounded loop reviewed, benign).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single concern). PH-02
  Size: low (logic ~120 lines). PH-03 Safety: none (0 migrations/schemas/secrets).
  PH-04 Completeness: none (tests present). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** `git diff change/create-portable-agent-context` (staged working tree)
- **Neighbour expansion:** git grep on touched symbols (`summarise_memory`,
  `regenerate_memory_content_from_store`, `checkpoint`, `assemble`) — callers
  confined to the changed files + their existing tests.
- **Neighbour cap:** not reached.
- **Scanners run:** ruff (check + format). mypy advisory.
- **Scanners unavailable:** Gitleaks / Semgrep / Trivy not invoked (no
  secret-shaped material, no new dependencies, no Dockerfile in the diff).
- **Lenses dispatched:** direct (focused source surface), all three produced output.
