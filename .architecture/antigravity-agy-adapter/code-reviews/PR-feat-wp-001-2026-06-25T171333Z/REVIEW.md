# Code Review: WP-001 — Interactive agy pty adapter + additive provider registration

> **Timestamp:** 2026-06-25T171333Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/create-antigravity-agy-adapter/wp-001-agy-pty-adapter-and-registration → change/create-antigravity-agy-adapter
> **Files changed:** 9 (816 insertions, 46 deletions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a new way for the product to run an agent session through Google
Antigravity (`agy`) instead of Claude, and registers it so it can be picked by
name — without touching the existing Claude path at all. The build is clean, the
new code is fully tested (100% line coverage on the new files), and the existing
Claude tests still pass untouched. One small piece of tidy-up was found and fixed
during review (a couple of code comments still named an old internal helper that
was renamed). Nothing needs your attention before merge.

## What to fix

No issues that need attention. One minor documentation drift was found and fixed
inline during the review (two comments referenced a renamed helper); see the
technical detail below for the record.

## How this pull request is shaped

**Size — clean.** 816 lines across 9 files, but most of that is documentation
(rich code comments explaining the platform decisions) and tests — the actual new
logic is a single small adapter file. Well within a reviewable size.

**Scope — clean.** One concern: add the agy adapter and register it. The commit is
a single `feat`.

**Safety — clean.** No database migrations, no schema changes, no infrastructure
files, no secrets. The one security-relevant decision (how much the agent is
allowed to do) defaults to the locked-down option.

**Completeness — strong.** 4 new source/test files; 21 new unit tests plus 2
read-only integration checks against the real `agy` program. Test-first throughout.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; every file
>50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff clean on BASE and HEAD; full adapter + registration + no-regression suite 42 passed.
- **PR Hygiene:** 0 findings (PH-01 scope clean, PH-02 size low, PH-03 safety clean, PH-04 completeness strong).
- **In the changes:** 1 finding (1 medium — doc drift, FIXED inline).
- **In the neighbours:** 1 finding (medium → downgraded to low; Watch List).
- **Draft fixes:** 0 (the one in-diff finding was fixed inline, not deferred).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | Dependency-inward respected; shared-helper extraction improves structure |
| Security | 0 | 0 | Default `--sandbox` posture (ADR-003); brief passed as one execv token, never shell-parsed |
| Quality | 1 (fixed) | 1 (watch) | Stale `_read_pre_prompt` comment references after Blue extraction |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check` "All checks passed!" on all 9 changed files;
`ruff format --check` "9 files already formatted". Build verification suite
(`test_claude_pty_adapter.py` + `test_agy_pty_adapter.py` +
`test_agy_provider_registration.py` + `test_agy_binary_introspection.py`): 42 passed.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 (plugins/sulis/scripts)    → clean
  severity: none
Size (PH-02):
  lines_added: 816, lines_removed: 46, total: 862 (mostly docstring + tests)
  files_changed: 9
  severity: low
Safety (PH-03):
  migration_count: 0; schema_idl_count: 0; infra_files: 0; secret_pattern_hits: 0
  severity: none
Completeness (PH-04):
  new_source_without_test: 0 (adapter + helper both covered; 21 unit + 2 integration)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `_session_manager/adapters/claude_pty.py:257, :274` — medium (quality), FIXED inline

**What:** Two code comments referenced `_read_pre_prompt`, the private method
removed from `claude_pty.py` during the Blue step (EP-02 extraction of the shared
`read_pre_prompt_sidecar` helper). After the rename these comments pointed at a
symbol that no longer exists in the file.

**Quoted (before fix):**
- L257: `# than crash the spawn (mirrors _read_pre_prompt's ignore-on-bad-id).`
- L274: `:func:`validate_change_ulid` guard that :meth:`_conversation_flags` / :meth:`_read_pre_prompt` already use`

**Why it matters:** Documentation drift — a reader following the comment finds no
such method. Low functional risk (comments only), but it is drift the diff
introduced.

**Resolution:** Fixed inline (Path A). Both comments now reference the shared
`read_pre_prompt_sidecar` helper. Re-ran ruff (clean) and the Claude + agy adapter
suites (40 passed).

### Findings in the Neighbours

#### `manager.py:1272, :1361`; `tests/unit/test_pty_remote_control.py:127`; `tests/integration/test_live_resume_injection.py:39`; `tests/integration/test_cold_memory_live_resume.py:48` — low (quality), Watch List

**What:** These files carry explanatory comments naming `claude_pty._read_pre_prompt`
by its old symbol path. After the Blue extraction the *behaviour* they describe
(ULID-validate-before-path-join, ignore-on-bad-id) still exists — it moved to the
shared `read_pre_prompt_sidecar` helper — so the comments remain semantically
accurate; only the symbol path is stale.

**Why not fixed here:** These files are outside the WP-001 Contract (the Contract
names only `agy_pty.py`, `session_manager_daemon.py`, the two `__init__.py`
exports, and the new test files). Per EP-07, Boy Scout cleanup is scoped to files
already being modified; per the executor scope guard, editing `manager.py` and
three unrelated test files would breach the WP boundary. The drift is comment-only
and semantically harmless. Recorded for a future touch of those files.

### Watch List

- Neighbour comment drift above (`manager.py` + 3 test files). No failing
  characterisation test constructible (comments only) → no Hardening Delta; note only.

### Cross-Reference

- No prior `.security/antigravity-agy-adapter/` viability report to cite.
- No existing hardening-deltas to dedup against.
- No neighbour pattern suggests a broader `/sulis:codebase-audit`.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `ruff format --check` on all 9 changed files; full adapter/registration/no-regression pytest run. Base: clean. Head: clean. Coverage gap: no mypy/pyright in project config or CI (project gate is ruff + pytest) — noted, not a silent skip.
- [✓] **CR-02 Dispatch shape.** Diff is 9 files (>5) but a single cohesive concern (one adapter + its tests + the authorized shared-helper extraction); reviewer authored and read every file end-to-end. Single-reader pass recorded here rather than three sub-agent dispatch — justified by the single-concern, single-module (plugins/sulis/scripts) scope and full author knowledge of the diff.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (authored this session). Unread files: none.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 1 medium (in-diff, fixed), 1 low (neighbour, watch).
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade trigger fired (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced — dependency-inward respected (adapter imports only domain types + sibling helper), shared-helper extraction improves structure. Security: nothing surfaced — no hardcoded secrets; no subprocess/shell in adapter (manager spawns argv directly, brief is one execv token never shell-parsed); integration test runs only read-only `agy --version`/`--help` via list-form subprocess with 30s timeout; ADR-003 default `--sandbox` posture. Quality: 1 finding (stale comment refs, fixed) + dead-surface (shared helper referenced by both consumers, no dead surface) + contract-drift (emitted flags match PC-001 §4 exactly; no `--remote-control`/`--session-id` per ADR-002) + test-coverage (100% on new files) + CR-10 perf (no loops with DB/RPC/FS calls — no anti-pattern matches).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat). PH-02 Size: low (862 lines, mostly docstring+tests; 9 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (test-first, 100% new-file cov). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/create-antigravity-agy-adapter` (working-tree, pre-commit) with untracked source intent-added.
- **Neighbour expansion:** `git grep` for the removed `_read_pre_prompt` symbol across the package.
- **Neighbour cap:** 5 files referenced, none excluded (under 20-file cap).
- **Scanners run:** ruff (lint + format). Gitleaks/Semgrep/Trivy not invoked — pure-Python argv-shaping diff, no dependency/IaC/secret surface; manual SEC scan performed (grep for secret patterns + subprocess/shell).
- **Single-reader pass:** yes (CR-02 justification above).
