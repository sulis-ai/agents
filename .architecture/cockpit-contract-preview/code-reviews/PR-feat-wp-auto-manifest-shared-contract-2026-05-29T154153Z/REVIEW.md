# Code Review: feat/wp-auto-manifest-shared-contract — Shared contract manifest fix

> **Timestamp:** 2026-05-29T154153Z (ISO 8601 UTC)
> **Author:** Senior Engineer (executor, WP-AUTO-MANIFEST)
> **Branch:** feat/wp-auto-manifest-shared-contract → change/feat-cockpit-contract-preview
> **Files changed:** 6 (5 modified + 1 new test)
>
> **Outcome:** Ready to merge

---

## At a glance

This change fixes a wiring bug between the two contract preview renderers. They were
meant to write into one shared file so the cockpit could read both the data contract
and the visual contract from a single place — but they wrote to two differently-named
files, and one of them overwrote the other's contents. The fix points both renderers
at one filename and makes both of them add-to rather than overwrite. It is small,
well-tested, and changes nothing the founder sees on screen. No issues need attention.

## What to fix

No issues that need attention.

## How this pull request is shaped

Small and single-purpose: one bug fix across two sibling renderers and their tests,
31 added / 10 removed lines plus one new test file. Commit scope is a single `fix`.
A new test was added that reproduces the bug first and then proves it fixed — exactly
the right shape for a fix. Nothing about the shape raises a concern.

---

## Technical detail

> Below this point uses internal taxonomy for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; all changed
files read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01; ruff clean on all changed files)
- **PR Hygiene:** 0 findings (PH-01..04 all low — single `fix` scope, 6 files, no migrations/schemas/secrets, tests included)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

`ruff check` on `_render_ui.py`, `wpx-render-contract`, and the three test files:
**All checks passed!** (see `tool-outputs/ruff-head.log`). Base branch also clean on
these files. Zero PR-introduced errors.

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbours: `wpx-render-ui` (CLI wrapper, calls `_render_ui.render_ui` +
`write_manifest` — unchanged contract); the render test suites (updated in-diff).
WP-003 (cockpit-wiring) is the downstream consumer but does not yet hardcode either
filename, so the canonical-name choice introduces no neighbour breakage.

### Watch List

- **Read-modify-write merge block is now duplicated** across `wpx-render-contract`
  (`cmd_render`) and `_render_ui.py` (`write_manifest`) — two consumers of the same
  manifest-merge pattern. Extraction is deferred: the two live in separate executables
  (a standalone script vs an imported module) with different payload shapes, and a
  shared helper would require a new shared module crossing this WP's file boundary.
  No failing characterisation test grounds a delta → Watch List, not a delta.
  Recommend a follow-up WP if a third manifest consumer appears.

### Lens output

- **Architecture lens: nothing surfaced.** Checks run: no new infra→domain imports;
  no new module singletons; no new external/HTTP/DB calls (no timeout/CB applicable);
  no secrets; `.resolve()` parity strengthens the existing path-safety invariant
  (writes stay inside the resolved worktree root).
- **Security lens: nothing surfaced.** Primitives checked: SEC-01..07 (no auth /
  injection / SSRF / secrets surface in the diff), SC-01..04 (no dependency change).
  Manifest reads guard malformed input via `try/except (OSError, json.JSONDecodeError)`
  and pin `encoding="utf-8"`. No path traversal — writes anchored to resolved worktree.
- **Quality lens:** (1) Build Verification: clean. (2) JSX scan: n/a (no JSX/TSX/Vue/
  Svelte). (3) Dead surface: none. (4) Contract drift: the two renderers now converge
  on one manifest carrying both `data_contract` + `ui_contract`; the new composition
  test asserts both keys in both run orders. (5) Test coverage: new shared-merge
  behaviour covered by 2 new composition tests (both orders) + updated merge unit test;
  42 render tests green. (6) Style: comments clear, file-consistent. (7) CR-10
  performance: no anti-pattern matches — merge reads one file once, no loops with I/O,
  no O(N²).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `ruff check` on all 5 changed source/test files. Base: clean. Head: clean. Coverage gap: none.
- [✓] **CR-02 Single-reader pass justified by diff size: 41 changed lines + 93-line new test, 6 files** — within the ≤200-line / ≤5-modified-file carve-out (1 of the 6 is the new test file).
- [✓] **CR-03 Full-file reads.** All changed regions read end-to-end; `_render_ui.py` and `wpx-render-contract` merge blocks read in full. New 93-line test read in full.
- [✓] **CR-04 Evidence discipline.** No findings to evidence; Watch List item cites the two specific functions.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical / 0 high / 0 medium / 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade triggers fired (Build Verification empty; no unread files; all lenses produced output; no PH-03 high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced + checks listed. Security: nothing surfaced + primitives listed. Quality: all 7 outputs produced.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single `fix`, 1 module). PH-02 Size: low (41 lines + new test / 6 files). PH-03 Safety: low (0 migrations, 0 schemas, 0 secrets, 0 infra). PH-04 Completeness: low (tests included, no API change). No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** git diff dde80c46...working-tree (Step 7 not yet run; review of staged-to-commit diff)
- **Neighbour expansion:** git grep (manifest filename + render_ui/write_manifest callers); cap not reached
- **Scanners run:** ruff (configured Python linter). Gitleaks/Semgrep/Trivy: not applicable (no secrets/dep surface in diff)
- **kind:** backend → scored against WPB rubric (read-modify-write idempotence, defensive parse, path-safety) — conformant
