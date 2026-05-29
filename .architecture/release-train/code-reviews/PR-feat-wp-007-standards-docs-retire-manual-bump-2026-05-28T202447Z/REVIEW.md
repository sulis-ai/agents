# Code Review: WP-007 — Standards + docs + retire the manual bump

> **Timestamp:** 2026-05-28T202447Z (ISO 8601 UTC)
> **Author:** sulis executor (WP-007)
> **Branch:** feat/wp-007-standards-docs-retire-manual-bump → change/create-release-train
> **Files changed:** 2 (both documentation)
>
> **Outcome:** Ready to merge

---

## At a glance

This change updates two written documents — the git-workflow standard and the
`/sulis:change` help text — to describe the new release flow, where a version
number is worked out automatically from the small "release notes" each change
leaves behind, instead of being typed in by hand. There are no code changes, no
new files, and nothing that touches how the project builds or runs. One small
gap surfaced during review (the rewritten section briefly stopped mentioning
that promoting to production keeps the full history) and it has already been
fixed. Nothing else needs attention.

## What to fix

No issues that need attention. The one small gap found during review was fixed
on the spot.

## How this pull request is shaped

Small, single-purpose, documentation-only. Two files, ~115 changed lines, all
in Markdown. No database changes, no infrastructure or workflow files, no
secrets, and no new code that would need tests. This is exactly the shape a
documentation change should be — nothing to split, nothing missing.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01). Docs-only diff; no
  compiler/linter language signal applies to the changed `.md` files. The repo
  docs gate is Markdown link-integrity; the dedicated checker is absent on host,
  so the manual fallback ran (see `tool-outputs/mechanical-baseline.log`) —
  coverage gap recorded.
- **PR Hygiene:** 0 findings. Scope `none` (single `docs:` concern), Size `none`
  (115 lines / 2 files), Safety `none` (0 migrations / 0 schemas / 0 secrets /
  0 infra), Completeness `none` (no new source → no missing tests).
- **In the changes:** 1 finding (1 low) — resolved inline.
- **In the neighbours:** 0 findings.
- **Draft fixes:** 0 (the single finding was fixed inline, not deferred).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (resolved) | 0 | GIT-06 rewrite dropped the no-squash/preserve-history merge mechanic |
| Security | 0 | 0 | nothing surfaced |
| Quality | 0 | 0 | nothing surfaced |

### Build Verification (CR-01)

No PR-introduced errors. The diff changes two Markdown files only; there is no
TypeScript/Python/Go/Rust language signal on the changed files. The project's
docs gate is Markdown link-integrity (`branch-ci` runs docs lint on push). No
dedicated link-checker (`markdownlint` / `lychee`) is installed on host, so the
mechanical floor here is the manual link-integrity fallback run at executor
Step 6 and recorded in `tool-outputs/mechanical-baseline.log`. Coverage gap:
no automated markdown link-checker on host.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {docs}                   → clean
  module_fan_out: 1 top-level dir (plugins/)   → clean
  severity: none

Size (PH-02):
  lines_added: 93, lines_removed: 22, total: 115
  files_changed: 2
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (≤200 line band; ≤5 file band)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0          (NB: zero workflow files touched — see scope note)
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0   (docs-only; no new source)
  api_change_without_schema: false
  severity: none
```

> **Scope note (WP boundary).** WP-007 is explicitly DOCS-ONLY. It must not
> disable/delete/change `promote-dev-to-main.yml` or any workflow — the
> mechanism retires at go-live (next cycle, per `wp-006-config/RUNBOOK.md`).
> The diff touches zero `.github/workflows/*` files; confirmed.

### Findings in the Changes

#### `plugins/sulis/references/git-workflow-standard.md` — F-01, low (architecture / contract-completeness) — RESOLVED INLINE

**Quoted text (pre-fix, the removed original intro):**
```
Production releases occur by merging `dev` into `main`. This is a
**fast-forward merge** (or merge commit if fast-forward is not possible)
that **does not squash** — `main` preserves `dev`'s history of
individual WP squash-merges.
```

**What happened:** The GIT-06 rewrite replaced the original intro (which stated
the `dev → main` merge mechanic — not squashed, preserves dev's history) with
the release-train framing, and in doing so dropped that merge-mechanic detail.
The new prose described the *release ceremony* (PR → bot bumps + tags) but no
longer stated *how the merge itself behaves* on `dev → main`. The detail was
not represented elsewhere in the standard (the only other "preserves" hit at
~L736 is GIT-10's revert rationale, unrelated).

**Why it matters:** Low. It is a documentation-completeness gap, not a
correctness defect — a reader of the reworked GIT-06 would no longer learn that
promotion preserves dev's WP-squash history. Within scope of GIT-06.

**Resolution (inline, CR-03 re-run):** Restored a sentence in the GIT-06 intro:
*"The merge of the `dev → main` PR is not squashed — `main` preserves `dev`'s
history of individual WP squash-merges. The Action's bump + tag commit lands on
top of that preserved history."* Re-run surfaced zero remaining findings;
acceptance grep still holds; fences balanced; scope unchanged (2 docs).

### Findings in the Neighbours

None. The two changed files' referenced anchors were verified rather than
scanned as a ring: GIT-08/GIT-10/GIT-11 anchors exist; `/sulis:release-train`
skill exists (`plugins/sulis/skills/release-train/SKILL.md`); the referenced
`release-on-merge.yml` workflow exists and is **referenced only, not modified**;
ADR-001/ADR-004 live in the (un-tracked, branch-travelling) `.architecture/`
tree per the established convention.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none.
- **Existing security report:** none for this project.
- **Pattern suggesting full audit:** none — single-purpose docs change.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** Docs-only diff; no compiler/linter
  language signal on the changed `.md` files. Repo docs gate = markdown
  link-integrity; dedicated checker absent → manual fallback ran (Step 6),
  logged at `tool-outputs/mechanical-baseline.log`. Coverage gap recorded
  (no automated link-checker on host). 0 PR-introduced errors.
- [✓] **CR-02 Dispatch shape.** Single-reader pass justified by diff size:
  115 lines, 2 files (≤200 lines AND ≤5 files — within carve-out).
- [✓] **CR-03 Full-file reads.** The complete 177-line diff patch was read
  end-to-end before scoring; the inline fix re-verified. No sampling.
- [✓] **CR-04 Evidence discipline.** F-01 cites file + quoted text + resolution.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 1 low
  (resolved inline).
- [✓] **CR-06 Verdict computed.** Verdict: PASS. No critical/high in diff;
  Build Verification empty; full diff read; all three lenses produced output;
  the one low finding resolved inline → re-run zero findings. No auto-downgrade
  triggers fired.
- [✓] **CR-07 Lens completion.** Architecture: 1 finding (resolved) + anchor/
  cross-reference verification. Security: nothing surfaced — primitives N/A for
  a docs-only diff; secret-pattern scan clean. Quality: nothing surfaced —
  whitespace clean, fences balanced, table column-consistent, list renumbered,
  CR-10 N/A (no code), acceptance grep passes.
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single docs concern).
  PH-02 Size: none (115 lines / 2 files). PH-03 Safety: none (0 migrations /
  0 schemas / 0 secrets / 0 infra — and zero workflow files, per the WP's
  docs-only boundary). PH-04 Completeness: none (no new source). PH-03 high →
  auto-downgrade: did not fire.

#### Run details

- **Diff source:** `git diff origin/change/create-release-train` (working tree;
  commit created at executor Step 7 after this gate).
- **Neighbour expansion:** anchor + cross-reference verification (git grep /
  `test -f`); no symbol-graph ring needed for a docs diff.
- **Neighbour cap:** not reached.
- **Scanners run:** secret-pattern grep on added lines (clean). No
  Gitleaks/Semgrep/Trivy needed for a docs-only diff.
- **Scanners unavailable:** dedicated markdown link-checker (manual fallback
  used).
- **Lenses dispatched in parallel:** no (single-reader carve-out).
