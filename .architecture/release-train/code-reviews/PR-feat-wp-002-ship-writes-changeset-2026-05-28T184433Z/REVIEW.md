# Code Review: PR-feat-wp-002-ship-writes-changeset — `/sulis:change ship` writes a changeset

> **Timestamp:** 2026-05-28T184433Z (ISO 8601 UTC)
> **Author:** WP-002 executor
> **Branch:** feat/wp-002-ship-writes-changeset → change/create-release-train
> **Files changed:** 1
>
> **Outcome:** Ready to merge

---

## At a glance

This pull request adds one new step to the ship flow: every change now records a short "release note" of its own, automatically, before it lands. The change is a documentation edit to a single skill file — no code, no tests touched. It is well-scoped, reads cleanly, and the instructions it adds match the helper they call. Nothing needs attention before merge.

## What to fix

No issues that need attention.

## How this pull request is shaped

**Size — clean.** One file, about 90 lines changed, all of it prose and one worked example. Easy to read end-to-end.

**Scope — clean.** A single concern: add the release-note step to the ship flow, plus the two places that reference it (the closing report and the gotchas list). No mixing of unrelated work.

**Safety — clean.** No migrations, no schema changes, no secrets, no infrastructure files. The one worked example shows an operator command; it sets its own inputs and never reads untrusted data.

**Completeness — appropriate.** This is a documentation change to a skill body; its correctness is proven by the helper it calls (already tested) and by this change's own ship exercising the step for real. Adding unit tests for prose would be testing the words, not the behaviour — correctly skipped.

## Things to take away

(Omitted — the pull request is clean and well-shaped.)

---

## Technical detail

> Below this point the report uses internal taxonomy (CR-NN, PH-NN, lens IDs) for engineers and downstream agents.

### Verdict

`PASS` per CR-06. No critical/high in the diff; Build Verification empty; the single changed file was read end-to-end; all three lenses produced output. No auto-downgrade trigger fired.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01)
- **PR Hygiene:** 0 findings (CR-09 / PH-01..PH-04)
- **In the changes:** 0 findings
- **In the neighbours:** 0 findings
- **Draft fixes:** 0 (lens findings only — none surfaced)

| Lens | In changes | In neighbours | Top concern |
|---|---|---|---|
| Architecture | 0 | 0 | nothing surfaced — producer shells into the leaf `_changeset.py` per ADR-005; dependency direction correct |
| Security | 0 | 0 | nothing surfaced — `$TOUCHES_PLUGIN` / `$SCRIPTS_DIR` interpolations are step-controlled, not untrusted |
| Quality | 0 | 0 | nothing surfaced — documented `write_changeset` call matches the real signature exactly (no contract drift) |

### Build Verification (CR-01)

No build-affecting errors. The diff is a single Markdown skill body (`.md` only); no Python/TS/Go source touched. The project checks a skill-body edit *can* affect were run and are green:

- Manifest JSON validity — OK (`tool-outputs/manifests.log`)
- `compileall plugins/sulis/scripts` — OK (`tool-outputs/compileall.log`)
- Routing coverage gate (`sulis-route check`) — `passed: true`, `parse_failures: []` (`tool-outputs/routing-gate.json`)
- Fenced code-block balance — 36 fences (18 balanced blocks)

### PR Hygiene signal table (CR-09 — PH-06)

```
Scope (PH-01):
  commit_type_spread: {docs}                  → clean (single concern)
  module_fan_out: 1 file (skills/change)       → clean
  severity: none

Size (PH-02):
  lines_added: 76, lines_removed: 8, total: 84
  files_changed: 1
  generated_ratio: 0.0
  lock_file_ratio: 0.0
  severity: none (well under all bands)

Safety (PH-03):
  migration_count: 0
  schema_idl_count: 0
  infra_files: 0
  secret_pattern_hits: 0
  severity: none

Completeness (PH-04):
  new_source_without_test: 0 (no new source files)
  api_change_without_schema: false
  severity: none (kind:docs — prose edit; behaviour proven by _changeset.py unit suite + the live ship)
```

### Findings in the Changes

None.

### Findings in the Neighbours

None. Neighbour ring = the rest of `skills/change/SKILL.md` (steps 4.5, 4.6, 7, Gotchas) and the called leaf `_changeset.py`. The new step reuses the single existing `$SCRIPTS_DIR` resolver (verified: exactly one `find ~/.claude/plugins/cache` block in the file) and mirrors step 4.6's `python3 -c`/`$SCRIPTS_DIR` shell-out pattern — no new surface the neighbours did not already carry.

### Watch List

- The bash worked example interpolates `$TOUCHES_PLUGIN` (a step-controlled `True`/`False`) and `$SCRIPTS_DIR` into a `python3 -c` string. This is the established pattern across this skill (step 4.5 diff probe, step 4.6 capture, the `focus`/`rebase` launchers) and the inputs are not attacker-controlled, so it is not a finding. Noted only so a future reader knows the interpolation is deliberate and bounded. No delta (no failing characterisation test — and prose has none to ground one; CR-04).

### Cross-Reference

- **Existing Hardening Deltas covered:** none
- **Existing security report:** none for this project
- **Pattern suggesting full audit:** none

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** No compilable source in the diff (`.md` only). Skill-body-affecting project checks run: manifests OK, compileall OK, routing gate `passed:true`/`parse_failures:[]`. Coverage gap: none (no typechecker configured for this stdlib-only repo — recorded, not skipped silently).
- [✓] **CR-02 Single-reader pass justified by diff size: 84 lines, 1 file** (within the ≤200-line / ≤5-file carve-out).
- [✓] **CR-03 Full-file reads.** The single changed file was read end-to-end; the inserted region (lines 455-507), the step-7 report edit, and the Gotchas note all reviewed in full. Unread files: none.
- [✓] **CR-04 Evidence discipline.** No findings; the one Watch List note cites the interpolation site and explains why no delta (prose has no characterisation test to ground one).
- [✓] **CR-05 Severity rubric.** Applied. 0 critical, 0 high, 0 medium, 0 low.
- [✓] **CR-06 Verdict computed.** Verdict: PASS. Auto-downgrade triggers: none fired (Build Verification empty; file read end-to-end; all lenses produced output; PH-03 not high).
- [✓] **CR-07 Lens completion.** Architecture: nothing surfaced (checks: dependency direction, new singletons, secrets, new external calls — none introduced; the step is a producer shelling into the leaf helper per ADR-005). Security: nothing surfaced (checks: injection via the `$TOUCHES_PLUGIN`/`$SCRIPTS_DIR` interpolation — bounded/step-controlled; no secrets; no plain-HTTP). Quality: contract-drift check = documented `write_changeset(...)` + `tier_for_primitive(...)` calls match `_changeset.py` signatures exactly; test-coverage observation = kind:docs, behaviour proven by WP-001 unit suite + the live ship (correctly no new tests); founder-English / FE-09 consistency = the founder-facing prose leads with outcome and carries no `_changeset`/`SULIS_CHANGE_ID` mechanism narration (machinery confined to the bash fence, matching steps 4.5/4.6); style = clean. CR-10 perf = N/A (no executable hot path in the diff).
- [✓] **CR-09 PR Hygiene applied.** PH-01 Scope: none (single docs concern). PH-02 Size: none (84 lines / 1 file). PH-03 Safety: none (0 migrations / 0 schemas / 0 secrets / 0 infra). PH-04 Completeness: none (no new source; kind:docs). PH-03 high → CR-06 auto-downgrade fired: no.

#### Run details

- **Diff source:** `git diff origin/change/create-release-train...HEAD` (working tree; the WP-002 edit pre-commit)
- **Neighbour expansion:** git grep within `skills/change/SKILL.md` + the called `_changeset.py` leaf
- **Neighbour cap:** not reached (2 files considered)
- **Scanners run:** manifest validator, compileall, sulis-route routing gate (stdlib-only repo; no Gitleaks/Semgrep/Trivy configured — recorded as coverage gap, not a silent skip)
- **Scanners unavailable:** Gitleaks / Semgrep / Trivy (not part of this repo's toolchain). Mitigated: the diff contains no secrets, no dependencies, no Dockerfile — nothing those scanners would target.
- **Lenses dispatched in parallel:** no — single-reader pass per CR-02 carve-out (84 lines / 1 file)
