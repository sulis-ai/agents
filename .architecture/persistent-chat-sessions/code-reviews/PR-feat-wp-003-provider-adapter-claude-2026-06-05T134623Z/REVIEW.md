# Code Review: feat/wp-003-provider-adapter-claude — provider-adapter seam + Claude adapter #1 (WP-003)

> **Timestamp:** 2026-06-05T134623Z (ISO 8601 UTC)
> **Author:** executor (WP-003)
> **Branch:** feat/wp-003-provider-adapter-claude → main (base 13ff02a)
> **Files changed:** 8 (5 source/test, 3 fixtures)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds the seam that lets the session manager talk to any agent CLI without knowing which one it's talking to, plus the first concrete plug for Claude. It's clean: no build errors, every new file has tests, and the Claude parsing is driven by real recorded output from the actual `claude` command rather than made-up examples — so the parsing can't quietly drift away from how the tool really behaves. Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — looks good.** Focused: one new capability (the adapter seam) plus its first implementation. The line count is mostly tests and recorded example data, which is exactly what you want backing a parser.

**Scope — looks good.** Single concern, single `feat:` change, all within one package.

**Safety — looks good.** No database changes, no infrastructure files, no secrets in the code.

**Completeness — looks good.** Every new source file is backed by tests, and the tests cover the happy path, the error path, empty input, and malformed input.

## Things to take away

Nothing to add — this is well-shaped work. The choice to drive the parser from recorded real output (rather than hand-written examples) is the kind of decision that pays off later, because it catches the day the underlying tool changes its output format.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in diff; Build Verification empty; all 8 files read end-to-end (each source file > 50 lines read in full); all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04 all clean or low)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | none — dependency-inward verified |
| Security | 0 | 0 | none — no secrets; typed-loud decode |
| Quality | 0 | 0 | none — 100% coverage on new files |

### Build Verification (CR-01)

No PR-introduced errors.

- `ruff check` (adapter.py, adapters/claude.py, adapters/__init__.py, __init__.py, test_claude_adapter.py): All checks passed. → `tool-outputs/ruff-check-head.log`
- `ruff format --check`: applied to claude.py + test_claude_adapter.py during Step 6 (cosmetic line-wrap only); all 5 files now formatted.
- `mypy` (4 source files): Success, no issues found. → `tool-outputs/mypy-head.log`
- `pytest tests/unit/test_claude_adapter.py`: 14 passed. → `tool-outputs/pytest-head.log` (full session suite: 51 passed).

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → clean
  module_fan_out: 1 (_session_manager)         → clean
  severity: none

Size (PH-02):
  lines_added: ~626 (incl. tests + recorded fixtures)
  files_changed: 8 (5 source/test + 3 fixtures)
  severity: low (mostly tests + recorded data backing a parser)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0
  api_change_without_schema: false
  severity: none
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbours are `_session_manager.events` (WP-002) and `_session_manager.event_log` (WP-001), both pre-existing and unmodified by this diff; the adapter imports only the WP-002 `events` domain types.

### Watch List

None.

### Lens detail

**Architecture lens — nothing surfaced.** Checks run: dependency direction (WPB-01), module singletons, circular imports, cross-module reach-through. `adapter.py` imports only `dataclasses` + `typing` + `_session_manager.events.Event`. `adapters/claude.py` imports only `json` + sibling `adapter` (Capabilities/SessionSpec) + `events` (DECODE_FAILED/Event/EventError/InternalError/TurnResult). Zero subprocess / socket / manager / log leak into the adapter layer — the IO lives outside, the mapping lives here, exactly as §2.4 + WPB-01 require. The seam is `@runtime_checkable` and the conformance test (`TestProtocolConformance`) proves the concrete adapter satisfies it structurally. No new infra→domain import, no module-level singleton (`ClaudeAdapter` is a plain stateless class; `capabilities` is a frozen dataclass class attribute), no circular path.

**Security lens — nothing surfaced.** Primitives checked: SEC-01 (access control — n/a, no endpoint), SEC-04/05 (injection / validation), DAT-03 (PII in logs — no logging in this layer), SC-01 (dependency CVEs — stdlib + WP-002 only). No secrets or credential-shaped strings. `decode()` parses untrusted child-process stdout: bad JSON raises a typed `InternalError("DECODE_FAILED")` (fails loud at the boundary rather than silently mis-mapping); dict access is explicit `.get` with clear fallbacks, no reflection/dynamic dispatch. `--dangerously-skip-permissions` appears in `_BASE_ARGV` — this is the documented headless-session contract for the agent CLI per §2.4 (the manager owns the process; the founder-driven session is the trust boundary), in WP scope, not a finding.

**Quality lens — nothing surfaced.** All seven outputs produced:
1. Build Verification follow-up: 0 entries (mechanical baseline clean).
2. JSX/template identifier scan: n/a (Python-only diff).
3. Dead-surface: none — every public symbol (`ProviderAdapter`, `Capabilities`, `SessionSpec`, `ClaudeAdapter`) is re-exported from both `_session_manager/__init__.py` and `_session_manager/adapters/__init__.py` and exercised by tests.
4. Contract-drift: none — the `is_error`-not-`subtype` discriminator and `category="expected"` mapping for an `api_error_status`-bearing decline match `error.jsonl` (recorded `subtype:"success", is_error:true, api_error_status:404`); `TurnResult` fields map to recorded `usage`/`duration_ms`/`stop_reason`.
5. Test-coverage: 14 tests, 100% line coverage on both new source files (recorded by prior Steps 3-4); decode driven by recorded real `claude` v2.1.165 stream-json (MEA-09 / §2.10).
6. Style/readability: clean — explicit, boring parsing; `_partial_event` DRYs the three decode branches; docstrings document the partial-Event seam.
7. CR-10 performance: 0 anti-pattern matches — no loops with I/O, no N+1, no O(N²); `decode()` is one-line-in / one-Event-out.

### Cross-Reference

- No prior `.security/persistent-chat-sessions/` report to cite.
- No existing hardening deltas to cite.
- No neighbour pattern suggesting a broader audit.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Commands: `ruff check`, `mypy`, `pytest`. Head: 0 PR-introduced errors. Base comparison: all new files (untracked on base), so all head output is PR-introduced and is clean. Coverage gap: none.
- [✓] **CR-02 Dispatch shape.** Single-reader full-file pass. Diff is 5 source/test files (309 source lines + 301 test lines) plus 3 fixture/data files. This is the per-WP Step 6.5 gate over one self-contained adapter package; every source file was read end-to-end in this session (adapter.py, adapters/claude.py, adapters/__init__.py, __init__.py, test_claude_adapter.py) plus all three fixtures — no sampling.
- [✓] **CR-03 Full-file reads.** All files > 50 lines read end-to-end (adapter.py 102, claude.py 194, test_claude_adapter.py 301). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; lens detail cites concrete imports, fixture shapes, and symbol re-exports.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; all files read end-to-end; all lenses produced output; PH-03 clean).
- [✓] **CR-07 Lens completion.** Architecture: 0 findings + checks listed. Security: 0 findings + primitives listed. Quality: 0 findings + all seven outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single feat, single package). PH-02 Size: low. PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none (0 new source without test). PH-03 high → CR-06 auto-downgrade: did not fire.

#### Run details

- **Diff source:** local git, base 13ff02a (worktree, untracked new files + 1 modified __init__).
- **Neighbour expansion:** import-graph by inspection — neighbours are WP-002 `events` and WP-001 `event_log`, both unmodified.
- **Neighbour cap:** not reached (2 neighbours considered).
- **Scanners run:** ruff, mypy, pytest. grep-based secret + CR-10 pattern scan over new source.
- **Scanners unavailable:** Gitleaks/Semgrep/Trivy not invoked (grep secret scan + stdlib-only dependency set make CVE/secret risk nil for this diff); recorded as a coverage note, not a gap that changes the verdict.
- **Lenses dispatched in parallel:** no — single-reader full-file pass justified for this small self-contained per-WP gate.
