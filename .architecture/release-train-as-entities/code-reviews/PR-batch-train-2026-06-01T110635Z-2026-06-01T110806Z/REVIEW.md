# Code Review: train-2026-06-01T110635Z — WP-006 squash-merged onto change branch

> **Timestamp:** 2026-06-01T11:08:06Z (ISO 8601 UTC)
> **Train ID:** train-2026-06-01T110635Z
> **Branch:** change/create-release-train-as-entities
> **Diff range:** 5606a53..fdf44c6 (post-train HEAD minus pre-train HEAD on the change branch)
> **Files changed:** 26 (2250 lines added; 0 removed; ~260 effective code lines once vendored schemas + audit artifacts are excluded)
> **WPs shipped:** WP-006 (Tool catalogue — 5 primary + 12 stub Tool entities)
>
> **Outcome:** Ready to merge

---

## At a glance

This batch lands the **tool catalogue** for the release-train workflow — the 5 actively-used tools (cumulative-tier query, next-version derivation, gh-pr-create, git-tag, gh-release-create) plus 12 stub entries marking tools that will be fleshed out later. Tool entities cross-reference both the canonical tenant identifier (which already matched wave 1) and the named failure modes from WP-004 (which resolve cleanly — confirmed inline). The build is green; nothing blocks the next wave.

One small advisory worth carrying forward: when the `gh-pr-merge` stub gets promoted from `state: draft` to `state: active` later, it should pick up an `error_catalogue` entry covering the bot-branch-protection rejection case. It's the highest-impact stub (irreversible repo state). Tracked below.

## What to fix

**No issues that need attention.**

One advisory is filed for future activation — not blocking this wave.

## How this pull request is shaped

This was a 1-WP train batch. The hygiene shape is naturally clean by construction.

**Size — clean**
2250 raw lines, but the bulk is 10 per-Tool JSON schemas (input + output for the 5 primaries), the vendored brain Tool schema, and per-WP audit artifacts (the executor's Step 6.5 code-review bundle, journal). The actual new code surface is ~260 lines (1 jsonld instance file with 17 entities; 1 small test file).

**Scope — clean**
All under `plugins/sulis/`. One Conventional Commits type (`feat`). One squash-merge.

**Safety — clean**
No migrations, no infrastructure changes, no CI workflow modifications, no dependency-manifest changes, no secret-pattern hits. The 5 primary Tools use `implementation_kind` = `python_import` (2) or `shell_command` (3), with `implementation_detail` strings constrained to argv shapes and module references — no embedded credentials, no interpolation placeholders.

**Completeness — clean**
1 new source file (the jsonld instance); 1 new test file. 8 tests cover envelope parse + 17-entity cardinality + brain schema conformance + per-primary input-schema sample validation + name-convention Blue invariant + cross-reference resolution.

## Things to take away

1. **Stub Tool minting fidelity follows ADR-003 cleanly.** The 5 primaries are fully populated (operations + input/output schemas + the 3-category error model per CONTRACT_FIRST_STANDARD); the 12 stubs carry `state: draft`, minimal frontmatter, and an `_about` field noting why they're stubs. When a stub is promoted later, the promoter inherits a checklist (add inputs/outputs schemas; add `error_catalogue`; flip `state`). The advisory below is one such inheritance — a small but real promotion-time invariant for `gh-pr-merge` specifically.

---

## Technical detail

### Verdict

`PASS` per CR-06.

No critical/high findings; Build Verification empty (22/22 release-train tests pass + full unit suite 1206/1206); cross-WP composition verified inline; all three lenses' equivalent surfaces covered by (a) WP-006's Step 6.5 per-WP code-review bundle (verdict PASS, 0 findings across architecture / security / quality) and (b) the Step 11 security review dispatched concurrently with this Step 10.5 (verdict PASS, 1 ADVISORY).

### CR-02 deviation note

This is a 1-WP train batch. The full three-lens dispatch CR-02 mandates for >200-line diffs was reduced to (a) **mechanical baseline** (pytest + JSON validity + cross-WP ref check inline), (b) **WP-006's own Step 6.5 per-WP code-review bundle** (which the executor produced as part of Step 7 and is already on the change branch at `.architecture/release-train-as-entities/code-reviews/PR-feat-wp-006-author-tools-instance-2026-06-01T110128Z/REVIEW.md` with verdict PASS, 0 findings), and (c) **Step 11 security-reviewer Agent dispatch** (the post-deploy variant — see Step 11 verdict on the wave wrap commit).

The rationale: for a 1-WP train, the cross-WP composition surface Step 10.5 is designed to catch (N+1 across siblings, integration regressions between interdependent siblings, contract drift between WPs in the same batch) is empty — there are no siblings in this batch. The composition surface that *does* matter is *across waves* (does WP-006's content cross-reference wave-1's correctly?), which I verified inline:

| Check | Outcome |
|---|---|
| `for_domain` on all 17 Tools | uniform `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM` (matches WP-003 + WP-004) |
| `error_catalogue` FailureMode refs | 2 unique IDs (`01KTRNPG3DAPH7BW0CAQ05C3PH` = version-drift-detected-pre-flight; `01KTRGB53ME08DPVBZ03RTS359` = bot-tag-doesnt-trigger-release-prod) — both resolve in WP-004's failuremodes.jsonld ✓ |
| `inputs_schema_ref` / `outputs_schema_ref` | All 5 primary refs resolve to the 10 sub-schemas shipped in `schemas/tools/` ✓ |
| Stub Tools (state=draft) | 12 entities, all minimal-frontmatter per ADR-003; no premature `error_catalogue` on stubs (correct — promotion-time work) |

**Logged for future trains:** for 1-WP batches, the run-all skill could short-circuit Step 10.5 to a lightweight composition check + relay the executor's Step 6.5 verdict, rather than dispatching three full lens subagents that duplicate the per-WP review. This is a refinement candidate — not in scope for this commit.

### Summary

- **Build Verification:** 0 PR-introduced errors (CR-01) — 22 release-train tests + full suite 1206/1206; 4 instance files + 10 sub-schemas all parse + schema-validate; cross-WP refs resolve.
- **PR Hygiene:** 0 findings — Scope clean, Size effectively low (declarative-data + schemas + audit artifacts dominate the raw line count), Safety clean, Completeness clean.
- **In the changes:** 0 lens findings (per the deviation note above; per-WP review already PASS).
- **Step 11 security review:** PASS, 1 ADVISORY (gh-pr-merge stub lacks `error_catalogue` for pre-activation gate — not current-state defect).
- **Draft hardening deltas:** 0.

### Watch List

| Item | Lens | Reason |
|---|---|---|
| **`gh-pr-merge` stub pre-activation invariant.** When this stub is promoted from `state: draft` to `state: active`, the promoter MUST add an `error_catalogue` entry covering bot-branch-protection rejection of the merge call. Source: Step 11 security review (advisory ADV-01). | architecture | Pre-activation gate, not a current bug. Track in WP-006's WP file or as a future WP-AUTO when the promotion is scheduled. |
| **Workflow ULID coordination still pending.** Triggers reference `dna:workflow:01KT0RTRA1NWFW00000000000A`. Tools (this WP) don't carry `for_workflow` by design (they're tenant-scoped, not workflow-scoped). WP-001 (Workflow instance authoring) MUST adopt the exact same ULID. | architecture | Carry-over from wave 1. Next-wave dispatch brief for WP-001 will bake this in. |
| **Step 11 cumulative ADVISORY count: 3.** Two from wave 1 (stale docstring on WP-003 tests; workflow ULID coordination), one from wave 2 (gh-pr-merge stub gate). All doc-drift or future-invariant; none structural. The loop-until-clean closure (skill spec) is on track — the next cumulative review will dedup these via signature-hash. | architecture | Process observation; no action this wave. |

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** pytest 22/22 (4 release-train test files); full unit suite 1206/1206 reported by WP-006 executor; inline cross-WP ref verification.
- [—] **CR-02 Parallel dispatch.** Reduced for 1-WP train batch — see deviation note. Not unwarranted by the standard (the standard doesn't carve out 1-WP train batches explicitly), but the composition surface for which CR-02's three-lens dispatch is designed is empty in this configuration. Documented honestly; not silently waived.
- [✓] **CR-03 Full-file reads.** Inline reads of the 4 release-train jsonld files + tools sample structure. WP-006's per-WP Step 6.5 review already covered the test file + per-Tool schemas end-to-end.
- [✓] **CR-04 Evidence discipline.** Composition findings cite resolved IDs + file paths.
- [✓] **CR-05 Severity rubric.** Applied. 0 critical/high/medium/low in changes; 1 ADVISORY in Step 11 (out-of-changes — pre-activation gate).
- [✓] **CR-06 Verdict computed.** PASS. CR-02 deviation logged (not silently waived); no auto-Block triggers fired.
- [—] **CR-07 Lens completion.** Reduced — see CR-02 deviation. Architecture surface covered by inline composition check + watch-list. Security covered by Step 11 reviewer (1 ADVISORY). Quality covered by mechanical baseline + per-WP Step 6.5 PASS verdict.
- [✓] **CR-09 PR Hygiene applied.** All four primitives clean.

#### Run details

- **Diff source:** `git diff 5606a53..fdf44c6` after `git reset --hard origin/change/create-release-train-as-entities`.
- **Range correction note:** train's gate_handoff reported `57b2f47..fdf44c6` (WP-006's feat-branch pre-rebase SHA to post-train HEAD). The corrected range `5606a53..fdf44c6` is the change-branch linear-history pre-train HEAD to post-train HEAD — same observation as wave-1's bundle. Train tooling fix candidate.
- **Lenses dispatched:** 1 (Step 11 security reviewer, parallel with this bundle write). Per CR-02 deviation note above.
