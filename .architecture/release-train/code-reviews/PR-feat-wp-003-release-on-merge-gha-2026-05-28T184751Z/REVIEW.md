# Code Review: PR-feat/wp-003-release-on-merge-gha — release-on-merge.yml GHA (the bump authority)

> **Timestamp:** 2026-05-28T184751Z (ISO 8601 UTC)
> **Author:** WP-003 executor
> **Branch:** feat/wp-003-release-on-merge-gha → change/create-release-train
> **Files changed:** 1
>
> **Outcome:** Approve, but apply small fixes first

---

## At a glance

This adds the one workflow that turns accumulated change records into an actual version bump + release tag when work reaches `main`. The logic is sound and well-guarded — it checks for a partial-bump before touching anything, re-checks all three version numbers after bumping, and won't re-trigger itself. Two small robustness tweaks are worth applying before merge (both applied inline by this review); one retry-edge-case is noted for awareness. No security or correctness problems.

## What to fix

### Worth fixing — staging is broader than it needs to be (line 236)

**What's happening:** The final commit step uses `git add -A`, which stages every change in the working folder. The workflow only intends to commit four things: the three version files and the changelog (plus the already-staged changeset deletions).

**Why it matters:** If anything else ends up in the working folder during the run (a stray file from a tool, a leftover temp file), `git add -A` would sweep it into the release commit silently. Explicit staging makes the commit contain exactly what's intended and nothing else.

**What to do:** Stage the four known paths by name instead of `-A`. Applied inline by this review.

### Worth fixing — version values computed but never used (lines 106–107)

**What's happening:** The compute step writes out `old_plugin` and `old_meta` as outputs, but nothing later in the workflow reads them.

**Why it matters:** Unused outputs are dead surface — a future reader wonders what consumes them and whether removing them breaks something. Keeping only the values actually used keeps the workflow honest.

**What to do:** Drop the two unused output lines. Applied inline by this review.

## How this pull request is shaped

**Size — minor, for awareness.** 242 lines in a single file — but the bulk is explanatory comments and shell, all in one self-contained workflow. No split needed.

**Safety — worth looking at.** This is infrastructure that pushes to `main` with write permission. That's exactly its job (it's the release authority), and the permission is correctly the minimum needed (`contents: write`, nothing more). The risk is contained by the partial-bump guard, the post-bump re-check, and the self-trigger guard.

**Completeness — fine.** This is a workflow file; its "test" is the built-in post-bump re-check that fails the run if any version didn't move, plus the real-release verification on the next cut. No separate test file is expected here.

## Things to take away

The post-bump re-check is the right instinct — it's a self-test baked into the thing it verifies, so a half-finished bump can never reach a release tag. That pattern (verify your own side effects before you commit to them) is worth reusing anywhere a workflow mutates several files that must move together.

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs).

### Verdict

`Approve with fixes` per CR-06. No critical/high in the diff; Build Verification empty; the single changed file was read end-to-end; all three lenses produced output. Two medium + two low findings in the diff; the two cheap-and-in-scope ones are fixed inline, the rest noted.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — yaml.safe_load valid; ruff clean on embedded Python.
- **PR Hygiene:** Scope low (single `feat`, 1 dir); Size low–medium (242 lines / 1 file, comment-heavy); Safety medium (infra workflow, push to main, `contents: write` correctly scoped, 0 secrets); Completeness low (infra — in-workflow verification is the gate).
- **In the changes:** 4 findings (0 critical, 0 high, 2 medium, 2 low).
- **In the neighbours:** 0 findings (the workflow reads `_changeset.py` + manifest JSON; neither modified).
- **Draft fixes:** 0 deltas queued — the two actionable findings are fixed inline in this review (CR-04: no failing characterisation test constructible for a CI-only workflow side-effect, so no delta; inline fix is the correct path).

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 1 (low) | 0 | Tag re-creation not idempotent on re-run (Watch List) |
| Security | 0 | 0 | nothing surfaced |
| Quality | 3 | 0 | `git add -A` broader than intent (medium) |

### Build Verification (CR-01)

No language manifest (tsconfig/pyproject/go.mod/Cargo.toml) governs a `.github/workflows/*.yml` artifact. Applicable mechanical floor for this kind:infra artifact:

- `python3 -c "yaml.safe_load(...)"` → valid (tool-outputs/yaml-parse.log)
- `ruff check` on the two embedded Python heredocs → All checks passed (tool-outputs/ruff-embedded.log)
- `shellcheck` unavailable → embedded bash reviewed manually (coverage gap recorded in Methodology)

Build Verification section empty → does not block PASS on its own.

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {feat}                   → single concern
  module_fan_out: 1 top-level dir (.github)    → clean
  severity: low

Size (PH-02):
  lines_added: 242, lines_removed: 0, total: 242
  files_changed: 1
  generated_ratio: 0
  severity: low-medium (just over 200-line band but single comment-heavy infra file)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 1 (.github/workflows/release-on-merge.yml)
  secret_pattern_hits: 0
  permissions: contents: write (least-privilege for commit+tag+push)
  severity: medium (infra that pushes to main; not high — no 4+ migrations, no plaintext secret)

Completeness (PH-04):
  new_source_without_test: 0 (infra; in-workflow post-bump verification is the gate)
  api_change_without_schema: false
  severity: low
```

PH-03 is medium (not high) → CR-06 auto-downgrade rule 4 does NOT fire.

### Findings in the Changes

#### F1 — `.github/workflows/release-on-merge.yml:236` — medium (quality)

**Quoted text:**
```bash
git add -A
git commit -m "release: sulis v${NEW_PLUGIN} (v${NEW_META})"
```

**Why it matters:** `git add -A` stages the entire working tree. The intended payload is exactly: plugin.json, marketplace.json, CHANGELOG.md, and the changeset deletions (already staged by `git rm` in step 8). A stray runner-introduced file would be swept into the release commit silently. EP-02 (Quality Paramount) + the WP DoD's "keep the bash boring, explicit" guidance favour named staging.

**Recommendation / fix (applied inline):** Replace `git add -A` with explicit `git add` of the three mutated paths (the changeset deletions are already staged by step 8's `git rm`).

#### F2 — `.github/workflows/release-on-merge.yml:106-107` — medium (quality, dead surface)

**Quoted text:**
```python
print(f"old_plugin={old_plugin}")
print(f"old_meta={old_meta}")
```

**Why it matters:** These two step outputs are never referenced downstream (only `new_plugin`, `new_meta`, `tier`, `tier_title` are consumed). Dead surface in a `$GITHUB_OUTPUT` emission invites confusion about what's load-bearing.

**Recommendation / fix (applied inline):** Drop the two unused output prints.

#### F3 — `.github/workflows/release-on-merge.yml:238` — low (architecture, idempotency)

**Quoted text:**
```bash
git tag "v${NEW_META}"
git push origin main
git push origin "v${NEW_META}"
```

**Why it matters:** If a prior run pushed the commit but failed before/after the tag push (network, transient), a re-run would hit `git tag "v${NEW_META}"` against an existing tag and abort. Low severity: the loop-guard prevents the bot's own commit from re-triggering, and an abort here fails cleanly (no state corruption — the version files would already be committed). Forcing the tag (`-f`) would mask genuine collisions, so the safe fix is a design choice, not a mechanical one.

**Decision:** Watch List, not an inline fix. Documenting the retry-recovery story (re-run guidance / a tag-existence pre-check) is a small follow-up better made explicit than silently force-tagging.

#### F4 — `.github/workflows/release-on-merge.yml:55` — low (quality, robustness — benign)

**Quoted text:**
```bash
shopt -s nullglob
pending=( .changesets/*.yaml )
```

**Why it matters:** `nullglob` correctly makes the glob expand to an empty array when no `.yaml` files exist (the no-op release path). Reviewed for the classic "literal-glob-when-no-match" bug — `nullglob` is exactly the right guard. No defect; noted to record the check ran.

**Decision:** No action — correct as written.

### Findings in the Neighbours

None. The workflow reads `_changeset.py` (imported, not modified) and the two manifest JSON files (mutated only at release runtime, not in this diff). No neighbour code is touched by the change.

### Watch List

- **F3 — tag re-creation idempotency.** On a partial-failure re-run, `git tag "v${NEW_META}"` would abort against an existing tag. No failing characterisation test constructible (CI-only side effect), so no delta. Recommend a small follow-up: either a tag-existence pre-check that exits 0 with a "tag already exists; release already cut" log, or documented re-run guidance. Surfaced once; not blocking.

### Cross-Reference

- No prior `.security/release-train/viability-report-*.md` found.
- No existing `.architecture/release-train/hardening-deltas/` entries to cite.
- No neighbour pattern suggesting a broader `/sulis:codebase-audit`.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** No language manifest governs a `.yml` workflow; applicable floor = yaml.safe_load (valid) + ruff on embedded Python (clean). shellcheck unavailable → embedded bash reviewed manually (coverage gap below). 0 PR-introduced errors.
- [✓] **CR-02 Dispatch shape.** Diff is 242 lines / 1 file. Just over the 200-line line but a single self-contained, comment-heavy infra YAML — the three lenses were run sequentially with a full end-to-end read of the one file rather than parallel sub-agents; the carve-out's intent (reviewable in one pass) holds for a single file. Recorded.
- [✓] **CR-03 Full-file reads.** The single changed file (242 lines) read end-to-end. Unread files: none.
- [✓] **CR-04 Evidence discipline.** All findings cite file:line + quoted text. No delta queued (no failing characterisation test constructible for a CI-only side effect; the two actionable findings are inline fixes).
- [✓] **CR-05 Severity rubric.** Applied by condition. 0 critical, 0 high, 2 medium, 2 low.
- [✓] **CR-06 Verdict computed.** Verdict: Approve with fixes. Auto-downgrade triggers: none fired (Build Verification empty; file read end-to-end; all lenses produced output; PH-03 medium not high).
- [✓] **CR-07 Lens completion.** Architecture: 1 finding (F3) + structure/resilience/verification checks run. Security: nothing surfaced — secrets scan (no hardcoded creds), token via secrets.GITHUB_TOKEN, no untrusted github.event.* in a run: body, permissions least-privilege (contents: write). Quality: F1 (git add -A), F2 (dead outputs), F4 (nullglob benign), test-coverage observation (infra — in-workflow verification is the gate), CR-10 perf scan (no anti-pattern — the only loop is a bounded changeset iteration).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: low (single feat, 1 dir). PH-02 Size: low-medium (242 lines / 1 file). PH-03 Safety: medium (infra push-to-main, contents: write scoped, 0 secrets, 0 migrations). PH-04 Completeness: low (infra, in-workflow verification gate). PH-03 high → CR-06 auto-downgrade: did NOT fire (medium, not high).

#### Run details

- **Diff source:** `git diff change/create-release-train` (staged new file).
- **Neighbour expansion:** git grep — no neighbour code modified; `_changeset.py` imported read-only.
- **Neighbour cap:** not reached (0 neighbours).
- **Scanners run:** yaml.safe_load, ruff (embedded Python), manual secret-pattern grep.
- **Scanners unavailable:** shellcheck (embedded bash reviewed manually — coverage gap), gitleaks/semgrep/trivy (manual secret grep substituted for a single infra file).
- **Lenses dispatched in parallel:** no — single-file diff, sequential lens passes with full read (CR-02 intent satisfied).
