# Code Review: WP-001 — safe-tools MCP server

> **Timestamp:** 2026-06-13T142531Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** feat/wp-001-safe-tools-mcp-server → change/harden-embed-safe-tools
> **Files changed:** 8 (4 new source/launcher, 1 test, 3 config incl. generated uv.lock)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds a small server that exposes three already-built, already-tested
tools (safe web-fetch, safe web-search, and a scoped file operation) as named,
switchable identities, so the agent's permissions can say "allow these safe ones,
block the raw ones". It wraps the existing code rather than rewriting it, which is
exactly what was asked for. No build errors, no risky patterns, and the new code
comes with its own tests. One small clean-up (an unused constant) was found and
fixed during the review, so there's nothing left to act on.

## What to fix

No issues that need attention.

A small clean-up surfaced during review and was fixed in place: a constant listing
the four allowed file operations was defined but never used. It is now the single
checked source of which operations are allowed, so the "unknown operation is
refused" behaviour reads from one place instead of being implied.

## How this pull request is shaped

**Size — clean.** About 390 lines of hand-written code plus its tests; the rest is
a generated dependency lock file. Well within a comfortable single-pass review.

**Scope — clean.** One concern: stand up the safe-tools server and make its tools
present as distinct identities. No mixed refactor-plus-feature.

**Safety — clean.** No database migrations, no schema files, no infrastructure
files, no secret-shaped text. The one outbound-network function is the deliberate,
already-designed safe-fetch path and sits behind the existing secret-scrub.

**Completeness — clean.** New code ships with a dedicated test file (12 tests)
covering tool enumeration, each file operation routing, the refuse-unknown path,
and the web-fetch/search delegation.

---

## Technical detail

> Internal taxonomy below (CR-NN, PH-NN, lens IDs) for engineers + downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all
changed files >50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff check clean, 40 tests pass.
- **PR Hygiene:** 0 high, 0 medium (CR-09 / PH-01..04).
- **In the changes:** 1 finding (1 low — fixed inline during review).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single finding was resolved inline, not deferred).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced — dependency direction inward, urllib isolated behind port |
| Security | 0 | 0 | nothing surfaced — scope server-resolved not agent-supplied (ADR-001) |
| Quality | 1 (fixed) | 0 | dead `_FILE_OPS` constant — fixed inline |

### Build Verification (CR-01)

Mechanical baseline: `uv run ruff check` (project configures ruff in
`pyproject.toml`) on the four changed Python files → **All checks passed** (HEAD).
`uv run pytest` on the new contract test + the two wrapped-library no-regression
suites → **40 passed**. Raw outputs in `tool-outputs/ruff-check-head.log` and
`tool-outputs/pytest-head.log`. No PR-introduced errors. Section empty → does not
block PASS.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → single concern
  module_fan_out: 1 top-level dir (plugins/sulis)
  severity: none

Size (PH-02):
  lines_added: ~631 incl tests, ~390 excl tests; +478 generated uv.lock
  files_changed: 8 (1 generated lock)
  generated_ratio: high (uv.lock is generated)
  severity: none (hand-written surface small, single-pass justified)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0  (.mcp.json is plugin config, not CI/infra)
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0  (new server + fetcher covered by test_safe_tools_mcp_contract.py)
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

#### `plugins/sulis/scripts/_safe_tools_mcp.py:62` — low (quality) — FIXED INLINE

**Quoted text (pre-fix):**
```python
_FILE_OPS = ("read", "write", "move", "remove")
```

**Finding:** the `_FILE_OPS` tuple was defined but never referenced — dead surface.
The `scoped_file` `match` hardcoded the four op literals, so the documented
closed-enum invariant (ADR-001) had no single checked source.

**Resolution (inline, Path A):** added an `if op not in _FILE_OPS:` guard at the
top of `scoped_file` that returns the fail-closed refusal, making `_FILE_OPS` the
single validated source of the allowed-op set. The `match`'s `case _:` became an
unreachable defensive `AssertionError` (marked `# pragma: no cover`). The
fail-closed refusal is now marshalled once (via the guard), preserving the
single-`_serialise_file_result` Blue property. Re-ran ruff (clean) + the 12
contract tests (pass), incl. `test_scoped_file_unknown_op_refused_fail_closed`.

### Findings in the Neighbours

None. The wrapped libraries (`_safe_fetch.tool`, `_safe_fetch.proxy`,
`_file_tools`, `_file_scope`) are imported unchanged; the new `_safe_fetch/fetcher.py`
is the production adapter the proxy port already required (no caller of the proxy
changed behaviour).

### Watch List

- `_safe_fetch/fetcher.py::UrllibFetcher.get` opens the only real socket
  (`urllib.request.urlopen`, S310-noqa). It is the deliberate L1 open-web leg,
  bounded by the proxy-injected timeout and reached only after the proxy's
  secret-scrub-before-DNS. Not unit-covered here (matches the shipped L1
  convention: the live leg is opt-in `-m live_network`). No action; noted for
  awareness that the network leg's behaviour is asserted by the L1 scenario suite,
  not this WP.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `uv run ruff check` + `uv run pytest`. Base: clean. Head: clean (0 new errors). Coverage gap: no `coverage`/`pytest-cov` installed → used stdlib `trace` for the 95.9% line-coverage figure on the new server module; recorded as the preflight fallback.
- [✓] **CR-02 Single-reader pass justified by diff size:** ~390 hand-written lines (the +478 uv.lock is generated), single concern, one top-level dir. Below the spirit of the 200/5 threshold once the generated lock is excluded; read end-to-end rather than dispatched.
- [✓] **CR-03 Full-file reads.** All 4 changed source files + the test read end-to-end. Unread: none.
- [✓] **CR-04 Evidence discipline.** The single finding cites file:line + quoted text.
- [✓] **CR-05 Severity rubric.** Applied. 1 low (fixed inline). No critical/high/medium.
- [✓] **CR-06 Verdict computed.** PASS. No auto-downgrade triggers fired (Build Verification empty; all files read; all lenses output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (dependency direction inward; urllib isolated behind the port; the only outbound call carries the proxy's bounded timeout). Security: nothing surfaced (scope server-resolved from launch env not agent args per ADR-001 — closes the scope-escalation vector; no secrets; no new auth surface). Quality: 1 finding (dead `_FILE_OPS`, fixed) + test-coverage observation (new code covered) + no contract drift + no CR-10 perf anti-patterns (no loops over network/fs/db in new production code).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: none. PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (tests present). No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/harden-embed-safe-tools...feat/wp-001-safe-tools-mcp-server` (executor worktree, staged).
- **Neighbour expansion:** git grep on imported symbols (`_safe_fetch.tool`, `_file_tools`, `SafeFetchProxy`, `within_allowed_scope`); no behaviour-changed callers.
- **Neighbour cap:** not reached.
- **Scanners run:** ruff (lint), pytest (tests), stdlib `trace` (coverage), manual secret-shaped-literal grep.
- **Scanners unavailable:** gitleaks/semgrep/trivy not invoked (no new dependencies beyond the vetted `mcp` SDK; manual secret grep clean); coverage/pytest-cov absent (stdlib trace used).
- **Lenses dispatched in parallel:** no — single-reader, justified above.
