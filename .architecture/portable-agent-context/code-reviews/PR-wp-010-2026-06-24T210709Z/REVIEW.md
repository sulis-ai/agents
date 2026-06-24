# Code Review: WP-010 — Scrub modern OpenAI API keys on write to the thread store

> **Timestamp:** 2026-06-24T210709Z (ISO 8601 UTC)
> **Author:** executor (WP-010)
> **Branch:** wp/create-portable-agent-context/wp-010-openai-key-detector-pattern → change/create-portable-agent-context
> **Files changed:** 5 (137 added, 3 removed)
>
> **Outcome:** Ready to merge

---

## At a glance

This change closes a real gap: before it, an OpenAI API key pasted into an agent
conversation was being saved to disk in plain text, because the secret-detector
did not recognise OpenAI's key shapes. The change teaches the detector both the
modern (`sk-proj-…`) and legacy (`sk-…`) OpenAI key formats, and proves the fix
reaches the place where conversations are saved. The build is clean, the change
is well-scoped to one file plus its tests, and it ships with nine new tests
(five proving keys are now caught, four proving ordinary text is not mistaken
for a key). No issues need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Clean across the board. Single concern (add OpenAI key detection), one source
file touched plus its three test files, no database migrations, no new
dependencies, and the new behaviour is covered by tests. This is exactly the
shape a small, well-targeted change should have.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all
changed files read end-to-end; all lenses produced output. No auto-downgrade
trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (PH-01..04 all clean)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — single-source catalogue entry, two consumers inherit |
| Security | 0 | 0 | none — ReDoS-safe, length-floored, no false positives |
| Quality | 0 | 0 | none — DRY, fully tested, in-file docs current |

### Build Verification (CR-01)

Mechanical baseline (the project's CI lint gate is `py_compile`; `ruff check`
is also available and run):

- `ruff check` on the 5 changed files → All checks passed.
- `py_compile` on the 5 changed files → OK.
- `pytest -k "anonymis or secret or thread_store"` → 224 passed, 2 skipped.

No PR-introduced errors. Section empty → does not block PASS.

> Note: a separate set of `test_session_manager_host` / `test_session_viewer` /
> `test_daemon_pidfile` integration tests fail in this worktree with
> `OSError: AF_UNIX path too long`. Confirmed pre-existing: they fail identically
> on the base branch `change/create-portable-agent-context` and are an artifact
> of the long worktree path exceeding the macOS 104-char UNIX-socket limit. Not
> introduced by this diff (which touches only `_secret_patterns.py` /
> `_anonymiser.py` + secret tests); out of scope.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread {feat}; module_fan_out 1 dir  → clean
Size (PH-02):         137 lines / 5 files (single-reader carve-out)    → clean
Safety (PH-03):       migrations 0; schemas 0; infra 0; secrets 0      → clean
Completeness (PH-04): new source ships with 9 new tests               → clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The two consumers of the catalogue (`find_secrets`/`find_catalogue_secrets`
→ the store's `_scrub`; and `_anonymiser`'s redact passes) were both inspected;
the new pattern integrates via the existing single-source mechanism (the
`_REGEX_CATALOGUE` list and the named-pattern import) with no change to their
control flow.

### Watch List

- The legacy `sk-[A-Za-z0-9]{40,}` alternative will, by design, also match the
  value of an `OPENAI_API_KEY=sk-…` assignment that the `env-secret` pattern
  already spans — producing two hits (`env-secret` + `openai-key`) over the
  overlapping region. This is the intended fail-closed posture (both the redact
  and refuse consumers act on any hit), verified not to break the store's
  scrub. No action; recorded for awareness.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `py_compile` (the CI
  lint gate per `branch-ci.yml`) + targeted pytest. Base: clean. Head: clean.
  Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 137 lines, 5 files**
  (≤200 lines AND ≤5 files — within the carve-out).
- [✓] **CR-03 Full-file reads.** Full staged diff read end-to-end; both
  consumer modules (`_secret_patterns.py`, `_anonymiser.py`) read around the
  touched symbols.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; the Watch List
  item cites the specific alternation and the verified behaviour.
- [✓] **CR-05 Severity rubric.** Applied — 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade trigger fired
  (Build Verification empty; all files read; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (single-source
  catalogue entry; no dependency-direction / singleton / circular-import
  introduction; no new external dep — CP-01 boring choice honoured). Security:
  nothing surfaced (ReDoS check — 100k-char input scanned in 0.14s, linear;
  length-floors verified at 19/20 and 39/40 boundaries; no false positive on
  `sk-` prose, git SHA, ULID, UUID, kebab-case slug; fail-closed over-match
  acceptable). Quality: nothing surfaced (reuses existing `_replace_long_token`
  replacer — no duplication; 9 new tests cover positive + negative; in-file
  docstring + category comment updated; no dead surface; no contract drift).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean. PH-02 Size: clean
  (137 lines / 5 files). PH-03 Safety: clean (0 migrations / 0 schemas /
  0 secrets / 0 infra). PH-04 Completeness: clean (tests shipped). No PH-03
  high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff --cached` (staged change vs HEAD == base tip)
- **Neighbour expansion:** git grep over `_OPENAI_KEY` / `openai-key` consumers
- **Neighbour cap:** 2 of 2 consumers inspected; none excluded
- **Scanners run:** ruff, py_compile, pytest (the project's available toolchain)
- **Scanners unavailable:** gitleaks / semgrep / trivy not installed in this
  worktree — coverage gap noted; the change adds no dependency and no infra, so
  SC/INF primitives have no diff signal to scan
- **Lenses dispatched in parallel:** no — single-reader carve-out (CR-02)
