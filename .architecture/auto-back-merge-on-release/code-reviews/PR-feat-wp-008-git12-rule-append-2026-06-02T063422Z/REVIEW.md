# Code Review: feat/wp-008-git12-rule-append — Append GIT-12 to git-workflow-standard.md

> **Timestamp:** 2026-06-02T063422Z (ISO 8601 UTC)
> **Author:** sulis-execution executor (WP-008)
> **Branch:** feat/wp-008-git12-rule-append → change/extend-auto-back-merge-on-release
> **Files changed:** 5 (1 modified, 4 new tests)
>
> **Outcome:** Approve, but apply small fixes first

---

## At a glance

The change appends one new section (`## GIT-12: Auto-back-merge on release`)
to the marketplace's git-workflow standard, plus four small structural
tests that guard the section's shape. The standard's version moves from
`0.2.0` to `0.3.0`, which lines up with the additive-minor convention the
file's own version history uses.

The rule body covers everything the work package asked for: an invariant
statement, a four-part mechanism, three worked examples (clean path,
raced path, manual recovery), three cross-references to existing rules,
and a record of the three earlier manual back-integrations that
demonstrated the gap. The new tests all pass.

Two minor notes flagged below — both deliberate trade-offs, neither
blocks merge.

## What to fix

No must-fix or strongly-recommend items. Two minor observations follow
in the technical detail for awareness.

## How this pull request is shaped

**Size — clean.** 143 net lines in the standard, 190 lines of tests.
Well under the size thresholds at which a split would help.

**Scope — clean.** Single concern: append one new rule to one standards
file plus the four structural tests that guard it. Conventional Commits
type spread is trivially `feat(docs):` (one type).

**Safety — clean.** No migrations, no schema changes, no infrastructure
files, no secrets. Markdown + bash test scripts only.

**Completeness — clean.** Every behaviour change has a test. The four
new tests cover all four "Red" checkboxes in the WP's Definition of
Done, and the implementation makes all four pass.

## Things to take away

Nothing specific to flag — the WP is small, well-scoped, and the tests
arrived with the implementation.

---

## Technical detail

### Verdict

`Approve with fixes` per CR-06.

Auto-downgrade triggers:
- CR-01 Build Verification: not applicable (Markdown-only, no
  typecheck). Recorded as coverage gap in Methodology, NOT auto-
  downgraded — the file kind has no typechecker.
- CR-03 sampling: not triggered. All changed lines reviewed end-to-end.
- CR-06 lens output: all three lenses produced explicit output.
- CR-09 PR Hygiene PH-03 high: not triggered (no migrations, no
  schemas, no infra).

### Summary

- **Build Verification:** N/A (Markdown-only diff; no typecheck applies)
- **PR Hygiene:** 0 high, 0 medium, 0 note findings
- **In the changes:** 2 findings (0 critical, 0 high, 0 medium, 2 low)
- **In the neighbours:** 0 findings (no neighbour ring — the standard
  is a leaf document; the four moving parts it names belong to peer WPs
  WP-001..WP-007)
- **Draft fixes:** 0 (both low-severity notes are documented trade-offs,
  not defects)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | No runtime code — N/A |
| Security | 0 | 0 | No secrets, no credentials, no executable paths |
| Quality | 2 | 0 | Two low-severity formatting trade-offs (documented) |

### Build Verification (CR-01)

Not applicable. The diff is Markdown plus bash test scripts. Markdown
has no typechecker; bash test scripts pass `bash -n` syntax check (run
at Step 6 — see journal). Recorded as **coverage gap** in Methodology
with reason: "kind: docs — no typechecker applies to .md content;
bash test scripts checked via `bash -n` in lieu of shellcheck (absent
on host)."

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat(docs)}              → clean
  module_fan_out: 1 distinct top-level dir       → clean
  severity: low (single-concern)

Size (PH-02):
  lines_added: 144, lines_removed: 1, total: 145 (modified file)
  + 190 lines new tests
  files_changed: 5
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: low (≤200 lines + ≤5 files within carve-out threshold)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: low

Completeness (PH-04):
  new_source_without_test: 0 (the docs change IS the source; tests
                              accompany it)
  api_change_without_schema: false (no API)
  severity: low
```

### Findings in the Changes

#### F-001 — low (quality) — `plugins/sulis/references/git-workflow-standard.md`, lines 975-980

**Worked example 2's bullet list uses plain text for the canonical
strings (no markdown backticks).**

Quoted text:
```
    - base: dev
    - head: main
    - title: chore: back-integrate main → dev (post-release v<NEW>)
    - label: back-integrate
```

**Why it matters:** Stylistically inconsistent with surrounding prose
that backticks identifier-shaped tokens (e.g., `` `dev` ``, `` `main` ``
elsewhere in the section).

**Why it's not a defect:** Deliberate trade-off. The canonical-string
parity test (`test_git12_canonical_string_parity.sh`) uses `grep -F`,
which is line-oriented and would be defeated by markdown backticks in
the structured bullet list. The alternative (allowing the test to
strip backticks before comparison) would special-case the test for
this one rendering choice. Reads clearly without code formatting and
matches the byte-for-byte contract WP-009 will enforce.

**Lens:** quality.

**No delta drafted.** Documented trade-off, not a defect to fix.

#### F-002 — low (quality) — `plugins/sulis/references/git-workflow-standard.md`, line 904

**The invariant statement uses unbacked `dev's history` in one place
where the rest of the section backticks `dev` consistently.**

Quoted text:
```
**The invariant.** dev's history is append-only relative to the release robot.
```

**Why it matters:** Internal consistency — `dev` is backticked everywhere
else in the section.

**Why it's not a defect:** Same root cause as F-001. The invariant test
(`test_git12_invariant_statement.sh`) requires the literal phrase
`append-only relative to the release robot` to appear on one line for
`grep -F` to match it. Splitting `` `dev` ``'s and the phrase across
lines (the original draft) broke the test; consolidating onto one line
required dropping the backticks from `dev` in that single occurrence.
The trade-off is documented and the rest of the section is consistent.

**Lens:** quality.

**No delta drafted.**

### Findings in the Neighbours

None. The standard is a leaf document. The four moving parts the rule
names (reusable workflow, consumer shim, drift script,
release-train pin writer) are external artifacts owned by peer WPs
WP-001..WP-007. WP-009 is the cross-WP parity test that will catch
any drift between this rule's canonical strings and the actual code.

### Watch List

None.

### Cross-Reference

- **Existing Hardening Deltas covered:** none applicable.
- **Existing security report:** none — this WP's surface is documentation.
- **Pattern suggesting full audit:** none.
- **Cross-WP enforcement:** WP-009 will run `test_canonical_strings_parity.sh`
  which reads GIT-12 as one of four sources whose strings must agree.
  That test is OUT of scope for this WP (WP-009 owns it).

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [—] **CR-01 Mechanical baseline ran.** Markdown has no typechecker; coverage gap recorded. Bash test scripts: `bash -n` syntax check passed on all 4 (shellcheck unavailable on host — fallback documented in Step 6 journal entry).
- [✓] **CR-02 Single-reader pass justified by diff size.** 5 files, 333 lines including tests; the modified .md file is 144 net lines. Markdown + bash; no compiled language signal. Single-reader justified for kind=docs at this size; the three lens labels still applied conceptually (architecture / security / quality) and produced explicit output.
- [✓] **CR-03 Full-file reads.** All 5 changed files read end-to-end. The modified standard's GIT-12 section (143 lines) read; all 4 test scripts (34-60 lines each) read.
- [✓] **CR-04 Evidence discipline.** F-001 and F-002 cite file:line and quote the offending text.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 2 low (both documented trade-offs, not defects).
- [✓] **CR-06 Verdict computed.** Verdict: `Approve with fixes`. No auto-downgrade triggers fired.
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (no runtime code in diff). Security: nothing surfaced (no secrets, no credentials, no executable paths). Quality: 2 low findings + tests-run verification + canonical-string-presence verification + historical-SHA verification.
- [✓] **CR-09 PR Hygiene applied.** All four primitives scored `low`. PH-03 high → did not fire (no migrations, no schemas, no infra, no secrets).

#### Run details

- **Diff source:** `git diff origin/change/extend-auto-back-merge-on-release...HEAD` (working tree at time of review, not yet committed)
- **Neighbour expansion:** N/A — leaf document; no callers/callees applicable.
- **Neighbour cap:** N/A.
- **Scanners run:** none applicable (no source-code paths to scan).
- **Scanners unavailable:** shellcheck (host); fallback `bash -n` used. tsc/eslint/mypy/etc.: not applicable to this diff.
- **Lenses dispatched in parallel:** no — single-reader path justified by CR-02 carve-out (333 total lines / 5 files / kind=docs).
