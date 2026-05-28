# Code Review: PR-feat-wp-004-release-train-skill — /sulis:release-train skill

> **Timestamp:** 2026-05-28T184815Z
> **Author:** WP-004 executor
> **Branch:** feat/wp-004-release-train-skill → change/create-release-train
> **Files changed:** 1
>
> **Outcome:** Ready to merge

---

## At a glance

This change adds one new skill file — the `/sulis:release-train` command that
previews and opens the release pull request. It is documentation (a skill body),
not running code, and it is deliberately read-only: it can only ever open one
pull request, never change a version or commit anything. There are no build
errors, the change is tightly scoped to a single file, and the version-preview
logic correctly reuses the proven shared helper rather than re-doing the maths.
Nothing needs fixing before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

Clean across the board — one new file, one purpose (add the release-train
skill), no database changes, no infrastructure changes, no secrets. The skill
is documentation, so there are no new tests expected: the version maths it
drives is already covered by the existing changeset-helper test suite.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the
single changed file was read end-to-end; all three lenses produced output.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). Changed file is
  Markdown; no typechecker/linter applies to a SKILL.md body. Both embedded
  `python3 -c` snippets parse as valid Python and were exercised end-to-end
  during the WP's Step 3 + Step 5 dry-run (manifest computed correctly).
- **PR Hygiene:** 0 findings (all primitives `note`/clean) (CR-09 / PH-01..04).
- **In the changes:** 0 findings.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0.

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | None — skill has no resilience surface of its own; single-bump-authority preserved (read-only) |
| Security | 0 | 0 | None — no secrets, no injection surface, read-only-bar-the-PR |
| Quality | 0 | 0 | None — no contract drift; references real `_changeset` public functions; ADR-003 three-value+tag match verified |

### Build Verification (CR-01)

No PR-introduced errors. The changed file `plugins/sulis/skills/release-train/SKILL.md`
is Markdown. CR-01 mechanical floor satisfied by: (a) Markdown file kind → no
tsc/eslint/mypy/ruff applies; (b) embedded `python3 -c` snippets validated as
syntactically valid Python (`tool-outputs/py-snippet-check.log`); (c) the same
snippets ran successfully producing the correct release manifest during the WP's
Step 3 GREEN proof and Step 5 acceptance dry-run.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {docs}                   → clean
  module_fan_out: 1 dir (plugins/sulis/skills/release-train)
  severity: note

Size (PH-02):
  lines_added: 437, lines_removed: 0, total: 437
  files_changed: 1
  severity: note (single non-code documentation file)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: note

Completeness (PH-04):
  new_source_without_test: 0 (SKILL.md is docs; computation proven by WP-001 suite per WP DoD)
  api_change_without_schema: false
  severity: note
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. The only neighbour is `plugins/sulis/scripts/_changeset.py` (the helper the
skill reads through). The skill references its public functions `read_changesets`,
`cumulative_tier`, `next_version` — all three exist and carry the contract the
skill depends on. No new gaps exposed.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none.
- **Pattern suggesting full audit:** none.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Changed file is Markdown — no
  typecheck/lint command applies. Embedded Python snippets validated
  (`tool-outputs/py-snippet-check.log`: 2 blocks, both parse OK) and proven by
  the WP's own Step 3/Step 5 dry-run. Coverage gap: none (the only "code" is the
  embedded snippet, which was both parsed and executed).
- [✓] **CR-02 Single-reader pass justified by diff size:** 1 file, 437 lines, a
  single non-code documentation file (SKILL.md). The 200-line threshold is a
  proxy for multi-file/code complexity; a single Markdown skill body read
  end-to-end carries no parallel-dispatch benefit.
- [✓] **CR-03 Full-file reads.** The one changed file was read end-to-end
  (authored + re-verified section by section). Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings, so no evidence citations
  required; lens checks recorded above.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No auto-downgrade trigger fired
  (Build Verification empty; full-file read; all three lenses produced output).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (a SKILL.md has
  no HTTP/DB/RPC call of its own; the single-bump-authority architectural
  invariant is preserved — the skill is read-only, the GHA owns the bump).
  Security: nothing surfaced (primitives SEC-01..07, SC-01..04 checked; no
  secrets, no command-injection surface; read-only-bar-the-PR confirmed by
  grepping for git commit/push/add, jq-write, write_changeset, --no-verify —
  none present in command blocks). Quality: nothing surfaced (no contract
  drift — references real `_changeset` public functions; ADR-003 three-value +
  tag-from-metadata + CHANGELOG-from-plugin match verified; all `gh` flags
  valid; 0 TODO/FIXME).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: note (1 module, docs only).
  PH-02 Size: note (1 file / 437 lines, single doc). PH-03 Safety: note (0
  migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: note (0
  source-without-test; docs WP, computation proven by WP-001 per WP DoD). No
  PH-03 high → no CR-06 auto-downgrade.

#### Run details

- **Diff source:** `git diff change/create-release-train...HEAD` (+ staged new file)
- **Neighbour expansion:** git grep — 1 neighbour (`_changeset.py`), within cap.
- **Neighbour cap:** 1 of 1 considered, 0 excluded.
- **Scanners run:** manual secret-pattern grep; embedded-Python AST parse.
- **Scanners unavailable:** gitleaks/semgrep/trivy not invoked (no code surface
  warranting them on a single read-only Markdown file; manual SEC grep covers
  the secret/injection primitives applicable here).
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out
  (1 file, documentation).
