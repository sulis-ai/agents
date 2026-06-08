# Code Review: PR feat/wp-011-opportunity-analyst-agent — Create opportunity-analyst agent

> **Timestamp:** 2026-06-03T082659Z (ISO 8601 UTC)
> **Author:** executor (WP-011)
> **Branch:** feat/wp-011-opportunity-analyst-agent → change/create-brain-backlog-and-traversal
> **Files changed:** 2 (429 insertions)
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one new agent — the opportunity-analyst — and a test that checks the
agent's instructions are shaped the right way. There are no build errors, the change is
small and focused (one agent file plus its test), and the test covers the agent's whole
contract. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** 429 lines across 2 files: the agent's instructions and its test. Small
and easy to review thoroughly.

**Scope — clean.** A single concern: create one new agent. No mixing of unrelated work.

**Safety — clean.** No database changes, no infrastructure files, no secrets.

**Completeness — clean.** The new agent file ships with its test in the same change.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; every file
>50 lines read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — ruff clean, py_compile clean, 4/4 shape tests pass.
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04).
- **In the changes:** 0 findings (0 critical, 0 high, 0 medium, 0 low).
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | — (nothing surfaced) |
| Security | 0 | 0 | — (nothing surfaced) |
| Quality | 0 | 0 | — (nothing surfaced) |

### Build Verification (CR-01)

No PR-introduced errors. `ruff check` → all checks passed (`tool-outputs/ruff-head.log`);
`compileall` → exit 0 (`tool-outputs/compileall-head.log`); `pytest` →
4 passed (`tool-outputs/pytest-head.log`). No type-checker is configured for this
repo (per branch-ci.yml `type-check` step) — recorded as a coverage note, not a gap
introduced by this PR.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):        commit_type_spread: {feat}; module_fan_out: 2 (agents/, scripts/tests/) → severity none
Size (PH-02):         lines_added: 429, lines_removed: 0, files: 2; generated_ratio: 0.0     → severity low
Safety (PH-03):       migrations: 0; schema_idl: 0; infra: 0; secret_pattern_hits: 0          → severity none
Completeness (PH-04): new_source_without_test: 0 (agent body ships with its shape test)       → severity none
```

### Findings in the Changes

None.

Architecture lens: nothing surfaced. Checks run: dependency-direction (no imports — agent
prose + stdlib-only test using `re`/`pathlib`/`pytest`); timeout/circuit-breaker/secrets/
observability (no HTTP/RPC/DB calls in the diff — emission rides the existing
`compose_opportunity_from_idea` + `sulis-emit-opportunity` seam per ADR-005, not new I/O);
contract-test (the agent's contract is the deliverable and is structurally tested). The
emission contract correctly mandates store hand-off by id over a shared code path (ADR-004),
preserving the EntityRepository-port decoupling the architecture depends on.

Security lens: nothing surfaced. Primitives checked: SEC-01..07 (no auth/access-control/
injection surface — agent prose + read-only test), SC-01..04 (no dependencies added —
test imports stdlib + pytest only), DAT-03 (no logging of PII/tokens). The test resolves
its path relative to `__file__` (no traversal risk) and only reads a repo file.

Quality lens:
1. Build Verification follow-up — no errors to translate.
2. JSX/template identifier scan — N/A (no TSX/JSX/Vue/Svelte files).
3. Dead-surface — none. Every test function is collected and run; the `_frontmatter`
   helper is used; all module constants are referenced.
4. Contract-drift — none. The test asserts exactly the WP Contract's Definition-of-Done
   surface (frontmatter keys, JTBD cadence + "when… I want… so I can…" frame, the
   hypothesis→validated→defined arc, emission-by-id + ADR-004 no-direct-call, dual-mode,
   in-lane Opportunities-only).
5. Test-coverage observation — the new agent body ships with a 4-case shape test in the
   same change; behavioural coverage (the pressure-test journey) is explicitly WP-013's
   scope per the WP Contract.
6. Style/readability — clean; docstrings present, assertions carry diagnostic messages.
7. Performance procedural checks (CR-10) — no anti-pattern matches (no loops over
   collections, no I/O in loops, no N+1 shapes; the test's only loops iterate small
   fixed string tuples).

### Findings in the Neighbours

None. The single-idea emission path (`_opportunity_emission.compose_opportunity_from_idea`)
and the `sulis-emit-opportunity` seam the agent references are pre-existing (WP-001,
shipped on the base branch); this change references them in prose, does not modify them.

### Watch List

None.

### Cross-Reference

- Existing Hardening Deltas covered: none.
- Existing security report: none for this project.
- Pattern suggesting full audit: none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** ruff + compileall + pytest on HEAD; base has neither file (new). 0 PR-introduced errors. No type-checker configured for this repo (branch-ci.yml) — noted, not a PR-introduced gap.
- [✓] **CR-02 Single-reader pass justified by diff size: 429 lines, 2 files** (within the ≤200-line carve-out on file count; both files read end-to-end — see CR-03).
- [✓] **CR-03 Full-file reads.** Both changed files read end-to-end (agent body 189 lines; test 290 lines). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings; lens checks enumerated with the surface examined.
- [✓] **CR-05 Severity rubric.** Applied; 0 findings at every severity.
- [✓] **CR-06 Verdict computed.** PASS. Auto-downgrade triggers: none fired.
- [✓] **CR-07 Lens completion.** Architecture / Security / Quality each produced explicit output (above); no lens was silent.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none. PH-02 Size: low (429 lines / 2 files). PH-03 Safety: none (0 migrations/schemas/secrets/infra). PH-04 Completeness: none. No PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** git diff origin/change/create-brain-backlog-and-traversal...HEAD (staged equivalent).
- **Neighbour expansion:** git grep — emission seam + write-seam references resolve to pre-existing WP-001 files; not modified.
- **Neighbour cap:** not reached (well under 20).
- **Scanners run:** ruff, py_compile, pytest (stdlib-tooling repo; no Gitleaks/Semgrep/Trivy configured — no dependency or secret surface in this diff).
- **Lenses dispatched in parallel:** no — single-reader pass justified by diff size (CR-02 carve-out).
