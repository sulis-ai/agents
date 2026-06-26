# Code Review: PR wp-005-optional-detect-secrets — make detect_secrets import optional

> **Timestamp:** 2026-06-25T232207Z (ISO 8601 UTC)
> **Author:** executor (Sulis)
> **Branch:** wp/create-product-wide-chat/wp-005-optional-detect-secrets → change/create-product-wide-chat
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes a crash. The chat feature was failing whenever a chat message
was saved on a machine that didn't have one particular optional secret-scanning
library installed — the save would blow up with "chat turn append failed". The
fix makes that library optional: if it's there, nothing changes; if it's not,
the chat save still scrubs out real keys (using the built-in pattern list) and
never crashes. The change is small (two files), well-tested (four new tests that
reproduce the exact missing-library condition), and the build is clean.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small, single-concern, and tested. It does one thing — make an optional
dependency genuinely optional — and ships the tests that prove the broken case
is now handled. Nothing to flag on size, scope, safety, or completeness.

## Things to take away

Nothing specific — this is a clean, well-shaped fix.

---

## Technical detail

> Internal taxonomy below for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both
changed files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — `py_compile` clean, `ruff check` clean.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean).
- **In the changes:** 0 findings.
- **In the neighbours:** 1 finding (medium, awareness — downgraded; not a blocker).
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — change improves availability (graceful degradation) |
| Security | 0 | 1 | outbound-scrub detection narrows to catalogue when detect_secrets absent (awareness; strictly an improvement over the prior crash) |
| Quality | 0 | 0 | none — tests included, signature unchanged |

### Build Verification (CR-01)

No PR-introduced errors. `python3 -m compileall` clean on both changed files;
`ruff check` reports "All checks passed!". Raw outputs in `tool-outputs/`.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):       commit_type_spread: {fix}; module_fan_out: 1 → clean
Size (PH-02):        lines +146/-5 (151 total); files 2 → clean
Safety (PH-03):      migrations 0; schemas 0; secrets 0; infra 0 → clean
Completeness (PH-04): new_source_without_test 0; tests_added 4 → clean
```

### Findings in the Changes

None.

### Findings in the Neighbours

#### `_safe_fetch/proxy.py` + `_session_manager/thread_store_local.py` — medium (security, awareness)

**What:** Both consumers call `find_secrets`. After this change, when
`detect_secrets` is unavailable the outbound-scrub union degrades to the
in-house catalogue alone, narrowing the detection surface (the catalogue does
not cover bare AWS access-key ids, generic high-entropy bearer tokens, etc.,
which detect-secrets' AWSKeyDetector / entropy plugins catch).

**Why it is not a blocker / not a regression:** In every environment that
previously *worked*, `detect_secrets` was importable, so the L1 safe-fetch proxy
(`_safe_fetch/proxy.py`) sees the FULL union exactly as before — byte-for-byte
unchanged. The degradation path is reachable only where the module is absent
(the cockpit plain-`python3` chat-scrub), and in that environment the prior
behaviour was a hard crash at import. So the change strictly improves
availability without weakening any environment that previously functioned. The
catalogue still redacts the real provider key shapes (Stripe `sk_live_`, GitHub
`ghp_`, env-var assignments, OpenAI keys, private IPs).

**Recommendation (awareness, no delta):** For stronger runtime redaction the
cockpit could invoke the chat-append under the uv environment so `detect_secrets`
is present. The graceful-degradation-to-catalogue posture is the correct
robustness default regardless. Recorded in the WP journal per the task note.

### Watch List

- Cockpit chat-append currently runs under plain `python3`. If the platform
  later wants the full detect-secrets union on the chat-scrub path (not just the
  catalogue), run the append under the uv env. No failing characterisation test
  grounds this as a delta — it is an operational choice, not a code gap.

### Cross-Reference

- No existing security report under `.security/create-product-wide-chat/`.
- No existing hardening deltas covered.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `python3 -m compileall` + `uv run ruff check` (the repo's CI lint gate is py_compile per `branch-ci.yml`; ruff check additionally clean). Base + Head: 0 errors. Coverage gap: no mypy configured in `pyproject.toml` (recorded; not enforced by repo CI).
- [✓] **CR-02 Single-reader pass justified by diff size: 151 lines, 2 files** (within the ≤200 line / ≤5 file carve-out).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (`_secret_patterns.py` 367 lines; test file 300 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** The one neighbour finding cites file paths + the exact degradation behaviour.
- [✓] **CR-05 Severity rubric.** 0 critical, 0 high, 0 medium (in changes); 1 medium awareness in neighbours.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checked dependency-direction, singletons, resilience posture — change is itself a resilience/availability improvement). Security: 1 neighbour awareness finding (checked SEC secrets-exposure on the scrub seam; the degradation is fail-safe — catalogue still redacts). Quality: 0 findings + tests-included observation (4 new tests) + signature-unchanged (no contract drift) + CR-10 perf scan (no anti-pattern matches; the new early-return is a fast-path, no loops added).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: clean (single `fix`, one module). PH-02 Size: clean (151 lines / 2 files). PH-03 Safety: clean (0 migrations/schemas/secrets/infra). PH-04 Completeness: clean (4 tests added, 0 new source without test). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff --cached change/create-product-wide-chat`
- **Neighbour expansion:** `git grep` for `find_secrets` callers — 2 consumers (`_safe_fetch/proxy.py`, `_session_manager/thread_store_local.py`).
- **Neighbour cap:** 2 of 2 considered, 0 excluded.
- **Scanners run:** py_compile, ruff check, pytest (122 unit tests green incl. the 4 new + all scrub/anonymiser/thread-store consumers).
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (Python-only logic change, no new dependencies/infra; secret-pattern hits in diff: 0 — fixtures are assembled-at-runtime, push-safe).
- **Single-reader pass:** yes (size carve-out).
