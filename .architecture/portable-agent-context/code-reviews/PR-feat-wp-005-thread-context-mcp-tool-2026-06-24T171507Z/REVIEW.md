# Code Review: PR-feat-wp-005 — thread_context MCP discovery tool

> **Timestamp:** 2026-06-24T171507Z (ISO 8601 UTC)
> **Author:** autonomous executor (CH-GJ9KQR WP-005)
> **Branch:** wp/create-portable-agent-context/wp-005-thread-context-mcp-tool → change/create-portable-agent-context
> **Files changed:** 2
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the read-only "fetch the full conversation record on demand" tool
that a spawned agent uses to pull a thread's raw messages, memory, or summary. It is
clean: the build passes, the change is tightly scoped to two new files (the tool plus
its tests), and the tests cover the behaviour that matters — including that the tool
can never write, and can never read another piece of work's conversation. No issues
need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Well-shaped. One new capability, one new test file, nothing else touched. Every new
piece of behaviour has a matching test, and the change follows the existing pattern
the codebase already uses for this kind of tool (the safe web-fetch / scoped-file
tools), so it reads as a natural sibling rather than a one-off.

---

## Technical detail

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; both files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). ruff clean; mypy 0 errors on the changed module; 12 tests pass.
- **PR Hygiene:** 0 findings (PH-01 scope low, PH-02 size low, PH-03 safety none, PH-04 completeness none).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (no finding met the CR-04 failing-test bar).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — dependency direction correct (WPB-01) |
| Security | 0 | 0 | none — read-only, scope server-side |
| Quality | 0 | 0 | none — no CR-10 anti-patterns; full test coverage |

### Build Verification (CR-01)

Empty. `ruff check` passed on both new files; `mypy _thread_context_mcp.py` reported
zero errors attributed to the changed module. (mypy surfaces 12 errors via transitive
import of `_session_manager/manager.py` + `recovery.py` — these pre-exist on BASE,
are not PR-introduced, and live in files this PR does not touch. Neighbour-ring
exposure only; no delta.)

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):    commit_type_spread {feat}; module_fan_out 1  → severity low
Size (PH-02):     lines_added 644, removed 0, files 2          → severity low
Safety (PH-03):   migrations 0, schemas 0, secrets 0, infra 0  → severity none
Completeness:     new_source 1, new_tests 1, no api-without-schema → severity none
```

### Findings in the Changes

None.

**Architecture lens (WPB rubric):** nothing surfaced. Checks run: dependency-direction
(WPB-01 — module imports only the provider-neutral `thread_contract` contract: the
`ThreadStore` Protocol + error model; no transport, provider, or web-layer import);
contract-first conformance (CF-07 — the tool exposes the read half of the WP-001
contract and the test mirrors `test_safe_tools_mcp_contract.py`); no new singletons,
no circular imports, no domain→infrastructure reach-through. The lazy `_default_store`
ImportError fallback to the contract's `InMemoryThreadStore` is the documented ADR-002
hybrid binding until WP-002's durable adapter merges, with a narrow
`# type: ignore[import-not-found]` on the not-yet-present WP-002 import.

**Security lens:** nothing surfaced. Primitives checked: SEC-01..07 (access control,
injection, validation, SSRF, secrets). The tool is read-only by construction (closed
read enum `{get_thread, get_memory, get_messages}`; write-shaped ops fail-closed before
any store call). Scope is resolved server-side from `SULIS_CHANGE_ID` (never an agent
arg), so an agent cannot widen scope; a cross-change `thread_id` is refused
(THREAD_NOT_FOUND). Path-traversal is delegated to the contract's `validate_store_id`
(no direct path handling here). No secrets, no network, no eval/exec/subprocess.
Scanners: not separately run (no dependency/Dockerfile/IaC change in diff).

**Quality lens:** nothing surfaced.
1. Build Verification follow-up: none (CR-01 empty).
2. JSX/template scan: N/A (no TSX/JSX in diff).
3. Dead surface: none — every function is exercised by the tests or is the stdio `main()` entrypoint (mirrors the safe-tools pattern).
4. Contract drift: none — the read enum matches the `ThreadStore` Protocol read methods; result/error serialisation carries the contract's three-category model.
5. Test coverage: present and thorough — 12 tests cover one-tool enumeration, each read op's dispatch, read-only (no write op reachable), unknown-op fail-closed, cross-change refusal, three error categories serialising, launch-env scope resolution, denyable identity, production-default wiring. 94% line coverage on the new module (>90% gate); the 3 uncovered lines are the WP-002 import branch + the stdio `main()` entrypoint.
6. Style/readability: clean (ruff format + check pass).
7. Performance (CR-10): no anti-pattern matches. The only loop is a single bounded `[asdict(m) for m in messages]` serialisation pass over a `limit`-bounded slice — no N+1, no per-iteration IO.

### Findings in the Neighbours

None introduced. Note: the pre-existing mypy errors in `_session_manager/manager.py`
+ `recovery.py` are reachable via transitive import but were not introduced or touched
by this PR. Recommend a separate `/sulis:codebase-audit` if the team wants to size the
broader `_session_manager` type-annotation gap — out of scope for this WP.

### Watch List

- When WP-002's durable `LocalThreadStore` merges, the `_default_store` fallback branch
  becomes live; the integration WP (WP-007) should add the mock→real conformance drive
  that exercises it (already in WP-007's scope per the INDEX).

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for this change.
- Pattern suggesting full audit: `_session_manager` pre-existing mypy gaps (neighbour ring).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `mypy _thread_context_mcp.py`, `pytest`. HEAD: 0 PR-introduced errors. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Diff 644 lines / 2 files. Single-reader pass justified by file count (2 files, both authored + read end-to-end this session); the three lenses were run inline over a 2-file surface.
- [✓] **CR-03 Full-file reads.** Both changed files (>50 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All lens conclusions cite the construct (enum, env read, loop) they rest on; zero findings, so zero unevidenced claims.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; all files read end-to-end; all lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks listed. Security: 0 findings + primitives listed. Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 low; PH-02 low; PH-03 none; PH-04 none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git diff --cached change/create-portable-agent-context (staged, pre-commit).
- **Neighbour expansion:** transitive import scan; `_session_manager` reached but not modified.
- **Neighbour cap:** not hit (2-file diff).
- **Scanners run:** ruff, mypy, pytest. Gitleaks/Trivy/Semgrep not run (no dependency/IaC/secret-bearing change in diff).
- **Lenses dispatched:** inline (2-file surface), all three produced output.
