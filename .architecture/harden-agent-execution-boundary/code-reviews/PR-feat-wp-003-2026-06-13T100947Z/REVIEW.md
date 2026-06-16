# Code Review: PR-feat-wp-003 — L1 safe-fetch tool + spawn-env wiring + egress scenarios

> **Timestamp:** 2026-06-13T100947Z (ISO 8601 UTC)
> **Author:** autonomous executor (WP-003)
> **Branch:** feat/wp-003-l1-tool-spawn-wiring-and-egress-scenarios → change/harden-agent-execution-boundary
> **Files changed:** 8 (3 production source, 1 config, 4 test/test-harness)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the agent's safe web-fetch tool, keeps secrets out of the agent's environment when its session starts, and proves three safety scenarios with honest tests. The review found one real gap — the secret-exclusion rule missed a few credential names (like AWS access keys) that don't follow the usual naming pattern — and it has been fixed in place with tests. Nothing else needs attention; there are no build errors and every new file has tests.

## What to fix

No issues that need attention. The one finding was fixed during the review (see below).

### Worth fixing (already fixed) — `_session_manager/spawn_env.py`

**What's happening:** The control that keeps secrets out of the agent's environment recognised secret variables by their name ending (`*_KEY`, `*_SECRET`, `*_TOKEN`, `*_PASSWORD`). A few common credential names don't end that way — `AWS_ACCESS_KEY_ID` ends in `ID`, `GOOGLE_APPLICATION_CREDENTIALS` ends in `CREDENTIALS`, and `SSH_AUTH_SOCK` is a path to the SSH key agent — so they would have been handed to the agent's web-fetch environment.

**Why it matters:** Keeping the secret out of that environment is the *primary* protection here (the secret-scrubbing on outbound requests is a second layer on top). A credential that slips through the primary layer leans entirely on the backup, which by design can miss novel secret shapes.

**What to do:** Done — an explicit short list of these well-known credential names now sits alongside the name-ending rule, with tests covering each. Extend the list as new credential variables appear.

## How this pull request is shaped

**Size — worth a glance.** 856 lines across 8 files, but the bulk is tests and documentation. The actual production code change is small (~55 lines across three files: the new tool, the new spawn-environment policy, and a minimal edit to the process-spawn path).

**Scope — clean.** Single concern: the L1 safe-fetch tool plus its spawn wiring and scenario tests.

**Safety — clean.** No database migrations, no schema changes, no infrastructure files, no secrets committed (the test fixtures use a synthetic `pat_`-shaped pattern so they can't trip secret scanners).

**Completeness — clean.** Every new source file has a dedicated test, written test-first.

---

## Technical detail

### Verdict

`PASS` per CR-06. No critical/high/medium findings remain in the diff after the inline fix; Build Verification empty; all files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** size medium (test/doc-heavy; production delta small), scope/safety/completeness low (CR-09 / PH-01..04)
- **In the changes:** 1 finding (0 critical, 0 high, 1 medium — fixed inline)
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (the single finding was fixed inline within the WP's scope, not deferred to a delta)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — tool is dependency-inward; spawn_env is pure |
| Security | 1 (fixed) | 0 | credential-name exclusion coverage gap (F-01) |
| Quality | 0 | 0 | none — full test coverage, no CR-10 matches |

### Build Verification (CR-01)

Mechanical baseline: `ruff check` (configured linter) + `python -m py_compile` (CI lint gate) on the changed files. 0 PR-introduced errors on HEAD. `tool-outputs/ruff-head.log` carries the raw output. Full L1 + spawn suite: 70 passed, 1 deselected (opt-in live-network leg).

### Findings in the Changes

#### F-01 — `_session_manager/spawn_env.py` — medium (security) — FIXED INLINE

**Rule:** SEC secrets-exposure (the Rule-of-Two primary control, SPEC §L1(d) / ADR-001).

**Evidence (pre-fix):** `is_credential_var` matched only the suffix set `(KEY, SECRET, TOKEN, PASSWORD, PASSWD)`. A probe showed `AWS_ACCESS_KEY_ID`, `GOOGLE_APPLICATION_CREDENTIALS`, and `SSH_AUTH_SOCK` returned `False` (passed through into the child fetch-path env).

**Why it matters:** The credential exclusion is the *primary* L1 control; the outbound secret scrub (WP-002) is explicitly defence-in-depth on top and is format-based (can miss novel shapes). A credential leaking past the primary control weakens the layering ADR-001 relies on.

**Resolution:** Added `_CREDENTIAL_EXACT_NAMES` (a boring, explicit whole-name allowlist of well-known credential variables, CP-01) consulted before the suffix rule, plus parametrized + dedicated `child_spawn_env` exclusion tests. Re-ran: 32 passed. 1 self-heal iteration (within the 3-iteration Step 6.5 budget).

### Findings in the Neighbours

None. The only modified neighbour is `manager._spawn_process`; the edit is `env=self._child_env()` on the two existing `Popen` calls plus an extracted helper — the pipe/pty branch logic is untouched and the real-spawn contract + eviction suites re-run green (characterisation preserved).

### Watch List

- **L1 is a door, not the only door (by design, ADR-001).** No production code in this change denies a raw socket; the only-door guarantee is the deferred `l3-os-egress-denial`. This is the intended, documented boundary — not a finding. The egress scenarios assert the proxy-correctness half under a test-only shim that simulates L3, and their docstrings say so.

### Cross-Reference

- Prior L1 review bundles: `PR-feat-wp-001-*`, `PR-feat-wp-002-*` (ports + proxy). This WP composes on them; no duplicate findings.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` + `python -m py_compile` on changed files. Base: clean. Head: 0 new errors. No coverage gap (ruff is the configured linter; no mypy/pyright config present).
- [—] **CR-02 Parallel dispatch.** Single-reader pass: production source delta is ~55 lines across 3 files (the 856-line total is test + docstring heavy, one cohesive WP). Recorded as the carve-out justification; the security lens was applied with extra conservatism given the WP is a security control.
- [✓] **CR-03 Full-file reads.** All changed files read end-to-end (tool.py, spawn_env.py, manager edit, _no_egress_shim.py, all three test files).
- [✓] **CR-04 Evidence discipline.** F-01 cites file + the probe evidence + quoted suffix set.
- [✓] **CR-05 Severity rubric.** F-01 = medium (test/operational-gap class for a primary control with a defence-in-depth backstop; not exploitable-now because the WP-002 scrub still covers catalogued shapes).
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; no unread files; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: dependency direction, singletons, circular imports, timeouts, observability). Security: 1 finding (F-01, fixed); scanners n/a (no new deps/Dockerfile); no hardcoded secrets. Quality: no dead surface, no contract drift, CR-10 no anti-pattern matches, test coverage complete.
- [✓] **CR-09 PR Hygiene applied.** Scope low (single `feat`). Size medium (856 lines, test/doc-heavy; production delta small). Safety low (0 migrations/schemas/secrets/infra). Completeness low (every new source file has a test). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git diff change/harden-agent-execution-boundary...HEAD (untracked new files added with `git add -N`)
- **Neighbour expansion:** git grep on `_spawn_process` / `child_spawn_env` / `PROXY_ENDPOINT_ENV`; 0 neighbour findings
- **Scanners run:** ruff, py_compile, pytest
- **Scanners unavailable:** gitleaks/semgrep/trivy not invoked (no new dependencies, no Dockerfile, no IaC in the diff; secret check done by inspection — fixtures use synthetic `pat_` shape)
- **Lenses dispatched in parallel:** no — single-reader carve-out (see CR-02)
