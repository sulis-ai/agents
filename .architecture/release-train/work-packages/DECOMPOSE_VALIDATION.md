# Decompose Validation — release-train

> **Change:** CH-01KSQN · create · Closes #66
> **Source:** `.changes/release-train.SPEC.md` (Option B, founder-chosen) + the
>   WP-001 batch code-review (PR-1fd6d60-2026-05-28T171158Z) + the founder's
>   "cover all 22 primitives" decision + the WP-002/003/004 batch code-review
>   (PR-e858389-2026-05-28T191515Z)
> **WP set:** WP-001..WP-009 + INDEX.md (7 spec pieces 1:1 → WP-001..WP-007;
>   WP-008 is the keystone remediation from PR-1fd6d60; WP-009 is the batch-defect
>   remediation from PR-e858389)
> **Standard:** WORK_PACKAGE_STANDARD v1.1.0 (WP-01..WP-11), CONTRACT_FIRST,
> the spec's "Bootstrapping sequence (MUST)".

This document proves the 9-WP set (a) covers all 7 spec pieces 1:1 plus the two
code-review-driven remediations, (b) honours the spec's bootstrapping order (with
WP-008 as Round 1.5 and WP-009 as Round 2.5), (c) is MECE (no overlap, no gap),
and (d) each WP is atomic + test-first.

---

## 1. Coverage — every spec piece maps to exactly one WP

| Spec piece | What the spec requires | WP | Covered? |
|---|---|---|---|
| **WP-1** | Changeset data model + helper (`_changeset.py`) + `.changesets/README.md` contract; unit-test EVERY function (`tier_for_primitive`, `cumulative_tier`, `next_version`, triple-key filename, `write_changeset`, `read_changesets`) | **WP-001** | ✅ — keystone; all six functions named + unit-tested; contract authored |
| **WP-2** | Ship writes a changeset before the merge (sibling of 4.6); remove the manual bump; skip for admin/docs-only (tier=None) | **WP-002** | ✅ — new step 4.7; writes via `_changeset`; skips on `None`; manual-bump expectation removed (resolved per TDD "Ambiguity" #1) |
| **WP-3** | `release-on-merge.yml` GHA: read changesets; none→exit 0; cumulative tier→next version; bump plugin.json + marketplace (sulis entry + metadata.version); assemble CHANGELOG; `git rm`; commit as bot; tag `v<marketplace-version>`; push; VERSION_DRIFT + post-bump verification guards | **WP-003** | ✅ — all nine steps + all three guards; three-value bump per ADR-003 |
| **WP-4** | `/sulis:release-train` skill: reads changesets + `origin/main..origin/dev`; cumulative tier + expected version; drafts PR body + CHANGELOG preview; opens dev→main PR; read-only on origin; `--dry-run` (default) + `--draft`; no-changesets valid; aborts on VERSION_DRIFT + existing open PR | **WP-004** | ✅ — full workflow; read-only; both flags; both aborts; no-changesets path |
| **WP-5** | `version-check.yml` CI guard: plugin diff must carry ≥1 changeset; ADVISORY-FIRST (warn, exit 0) this cycle; promotion to required is a separate later step | **WP-005** | ✅ — advisory/warn-only; advisory-this-cycle stated in WP + workflow; promotion deferred to founder-gated later cycle |
| **WP-6** | `main` branch protection: require dev→main PR + checks; `enforce_admins: false`; applied via `gh api`; record exact config; FOUNDER-GATED (pause + show config); verify bot push on a throwaway | **WP-006** | ✅ — founder-gated pause; exact config recorded; throwaway bot-push verification; lands with WP-003 |
| **WP-7** | Standards + docs: ceremony is changeset → release-train → GHA bump; update ship docs + lifecycle; remove manual-bump expectations going forward; cross-link #66; note this change's own ship is still a manual bump | **WP-007** | ✅ — git-workflow-standard + ship docs updated; #66 cross-linked; one-last-manual-bump carve-out stated |

**All 7 spec pieces are covered, one WP each. No spec piece is split across WPs;
no WP covers more than one spec piece. The mapping is 1:1 and onto.**

### 1a. WP-008 — the keystone remediation (NOT a spec piece; from the code-review)

| Origin | What it requires | WP | Covered? |
|---|---|---|---|
| **Code-review PR-1fd6d60 + founder decision** | Complete `_PRIMITIVE_TIER` for all 22 primitives (founder: cover all 22 so every code-altering change gets versioned); reject newline/`:` injection in the raw scalar fields at `_dump_changeset`; document the cross-language parser grammar in `.changesets/README.md`; close the low-hanging doc/test correctness items (CR-WP001-01..04) | **WP-008** | ✅ — all four fixes named with falsifiable acceptance criteria + test-first DoD; finalises the contract WP-002/003/004 conform to |

WP-008 does not overlap any spec piece — it remediates the *merged* WP-001
keystone after the batch code-review surfaced that 13 of the 22 primitives
resolved to `None` (reproducing #66's invisibility for a different primitive set),
that the raw scalar fields permitted a cross-reader tier forgery, and that the
parser grammar the WP-003 bash reader must match lived only in Python. It is a
bounded, test-first remediation — not a redesign.

### 1b. WP-009 — the batch-defect remediation (NOT a spec piece; from the code-review)

| Origin | What it requires | WP | Covered? |
|---|---|---|---|
| **Code-review PR-e858389 (WP-002/003/004 batch gate)** | CR-BATCH-01 (critical): the ship step never writes a changeset — `write_changeset('.changesets', …)` passes a `str`; the keystone calls `.mkdir()` → `AttributeError`; `dev` accumulates none (the #66 invisibility behind a runtime crash). CR-BATCH-02 (high): the Action loop-guard expression won't load — a double-quoted literal inside `${{ }}` is rejected by GitHub Actions at expression evaluation while YAML lint passes. | **WP-009** | ✅ — **closes both batch-gate findings**: harden the keystone to accept `str \| Path` (coerce `Path()` at entry of `write_changeset` + `read_changesets`, with a test proving a `str` dir round-trips, and the producer end-to-end proven); single-quote the GHA loop-guard literal (actionlint or documented manual expression check). Also corrects the WP-002 spec example (the origin of the `str` bug). |

WP-009 does not overlap any spec piece — it forward-fixes two defects in the
*merged* WP-002 + WP-003 (both on `change/create-release-train`, gate-blocked,
nothing shipped to `main`). It is a bounded, test-first remediation — not a
redesign — and is a **release blocker** for this change (the producer crashes on
every ship until FIX 1 lands) while gating no remaining WP.

---

## 2. Bootstrapping order — the spec's MUST sequence is honoured

The spec's "Bootstrapping sequence (MUST — avoids self-lockout)" maps onto the
WP dependency graph + recommended order:

| Spec bootstrapping step | WP realisation | Honoured? |
|---|---|---|
| 1. Ship WP-1+WP-2+WP-3 first (writer + GHA) BEFORE enforcement | Round 1 (WP-001 keystone) → Round 2 (WP-002 writer + WP-003 authority). WP-005 (enforcement) is deliberately LATER (Round 4). | ✅ |
| 2. Ship WP-4 (release-train skill) — releases can be cut | Round 2 includes WP-004 (depends only on WP-001). | ✅ |
| 3. Ship WP-5 **advisory** (warn-only); promote to required only next cycle | WP-005 is advisory/exit-0 (ADR-006); `depends_on: [WP-004]` puts it AFTER the train is live + producing changesets; promotion is a separate later founder-gated WP. | ✅ |
| 4. WP-6 (main protection) lands with WP-3; verify the bot push on a throwaway | WP-006 `depends_on: [WP-003]` (lands with it); founder-gated pause + throwaway bot-push verification in its Blue. | ✅ |
| 5. This change ships through the OLD flow (manual bump, last time); the NEXT release uses the train | Stated in INDEX (recommended order) + WP-002 Notes + WP-007 acceptance criteria + the carve-out. WP-007 does NOT block this change's own manual-bump ship. | ✅ |

**Round 1.5 inserted — the remediation precedes the consumers.** WP-008
`depends_on: [WP-001]` and `blocks: [WP-002, WP-003, WP-004]`. The three consumers
now `depends_on: [WP-001, WP-008]`, so they conform to the *finalised* contract
(full tier map + documented format rules), never the pre-remediation keystone.
This strengthens bootstrapping step 1: the "writer + authority" that ships before
enforcement is built on a contract where no code-altering primitive resolves to
`None` and where the bash reader has a written grammar to match.

**The dependency graph cannot violate the bootstrapping order:** WP-005
(enforcement) has a hard `dependsOn` edge to WP-004 → WP-008 → WP-001, so
enforcement can never land before the finalised keystone + writer + authority +
skill. The self-lockout the spec forbids is structurally impossible given these
edges; WP-008 adds a node on that chain without changing its direction.

---

## 3. MECE check (no overlap, no gap)

- **Mutually exclusive (no overlap):** the file scopes are disjoint —
  WP-001 (`_changeset.py` + its test + `.changesets/README.md`),
  WP-002 (`skills/change/SKILL.md` step), WP-003 (`release-on-merge.yml`),
  WP-004 (`skills/release-train/SKILL.md`), WP-005 (`version-check.yml`),
  WP-006 (`gh api` config, no repo file), WP-007 (`git-workflow-standard.md` +
  surrounding ship-doc prose). WP-008 re-touches WP-001's three files
  (`_changeset.py`, its test, `.changesets/README.md`) — this is **temporal, not
  parallel** overlap: WP-001 is merged before WP-008 starts (Round 1 → Round 1.5),
  so there is no concurrent-edit conflict. WP-008 owns the *finalised* state of
  the keystone; no other WP touches those three files. The only shared *read*
  touch is the *contract* (`.changesets/README.md`), which WP-008 finalises and
  WP-002/003/004 reference — the CONTRACT_FIRST seam, not a scope overlap.
- **Collectively exhaustive (no gap):** §1 shows all 7 spec pieces are covered.
  The "How we'll know it's done" criteria from the spec all map to WP acceptance
  criteria (changeset written + accumulated → WP-002; release PR with right
  version + CHANGELOG → WP-004; GHA bump verified on a real cut → WP-003;
  version-check guards plugin diffs → WP-005; `_changeset.py` fully unit-tested →
  WP-001). The "What to avoid" items map to guards: required-before-writer-live →
  WP-005 advisory (ADR-006); GHA bump without guards → WP-003 VERSION_DRIFT +
  post-bump verification; two bump authorities → ADR-004 (one authority) +
  WP-007 (retire the manual bump from docs).

---

## 4. Per-WP atomicity + test-first (WP-02, WP-03, WP-04 rubric)

| WP | One-branch / one-engineer? | Falsifiable acceptance criteria? | Test-first (Red→Green→Blue)? |
|---|---|---|---|
| WP-001 | ✅ one module + one test file + one README | ✅ exact function behaviours + named tests | ✅ 13 named unit tests written first; full RGB; Blue extracts the tier-order constant |
| WP-008 | ✅ the same module + test + README, edited in place after WP-001 merges (temporal, not concurrent) | ✅ all 22 primitives non-None; named tiers for the 13 new; newline/`:` guard; README rules section; doc-drift conformance test | ✅ ~10 new tests written first (full-22 coverage, newly-mapped tiers, injection rejection, README-table conformance) → Green (13 dict entries + guard + README rules) → Blue (single-source the 22-vocabulary; confirm docstring/comment now true) |
| WP-002 | ✅ one SKILL.md step | ✅ step exists, calls `write_changeset`, skips on `None`, no bump | ✅ surrogate Red (no step before) → Green (add step) → Blue (framing/no-dup resolver); live proof = this change's own ship |
| WP-003 | ✅ one workflow file | ✅ nine steps + three guards + three-value bump + tag rule | ✅ post-bump verification authored as the assertion first; verified on a real cut |
| WP-004 | ✅ one SKILL.md | ✅ read-only, both flags, both aborts, no-changesets path | ✅ surrogate Red → Green (reuse WP-001) → Blue (single-source the version math); safe `--dry-run` live check |
| WP-005 | ✅ one workflow file | ✅ advisory/exit-0 semantics explicit | ✅ inverse Red (missing changeset must exit 0) → Green → Blue (no exit-1 path; TODO(deferred) at the promotion site) |
| WP-006 | ✅ one config application | ✅ exact `gh api` config + bot-push verified | ✅ pre-flight capture (rollback baseline) → founder-gated apply → throwaway bot-push verification |
| WP-007 | ✅ docs edits in two files | ✅ grep: no normal-release doc hand-picks a version; #66 cross-linked | ✅ grep-Red (manual-bump language present) → Green (edits) → Blue (grep confirms none remains) |
| WP-009 | ✅ one module (+ one test) + one workflow line + the WP-002 spec example | ✅ keystone accepts `str` or `Path` (str-dir round-trip test); existing 50 stay green; producer end-to-end writes a changeset with no AttributeError; GHA literal single-quoted + prefix still exact | ✅ Red (str-dir test fails with AttributeError) → Green (one `Path()` coercion per function + single-quote the literal) → Blue (one idiom both functions; spec + snippet agree) |

Each WP is independently mergeable on a single branch with a single engineer
holding the whole change in their head (WP-02). Each lists falsifiable
acceptance criteria (WP-03) and a test plan with a verification gate (WP-04).
The keystone (WP-001) unit-tests **every** function per the spec.

---

## 5. Lineage + identity completeness (WP-01, WP-06)

- Every WP carries `change_id: 01KSQNPBPN7W74QVAZ25F79RNH` (WORK_PACKAGE_STANDARD
  v1.1.0).
- Every WP carries `id`, `title`, `kind`, `source`, `primitive`, `group`,
  `status: pending`, `depends_on`, `blocks`, `rollback`, and a `derived_from`
  pointing at the spec piece + `generated_by` (this draft-architecture run).
- The INDEX header is the canonical `| ID | Title | Primitive | Status | Depends
  On | Blocks |` signature (header lint passes — ID first, no duplicate `kind`
  column).

---

## Verdict

**PASS.** The 9-WP set covers all 7 spec pieces 1:1 plus the two code-review-driven
remediations (WP-008 keystone tier coverage + hardening; WP-009 batch-defect
remediation), honours the spec's MUST bootstrapping sequence (and makes
self-lockout structurally impossible via the dependency edges), is MECE on file
scope + spec coverage (WP-008's re-touch of the keystone files is temporal, not
concurrent — Round 1 merges before Round 1.5 starts; WP-009 re-touches the keystone
+ its test + the GHA + the WP-002 spec after Round 2 merges — again temporal, not
concurrent), and each WP is atomic + test-first with falsifiable acceptance
criteria. The CONTRACT_FIRST keystone (WP-001) lands first and is finalised by
WP-008 (Round 1.5) before its consumers (WP-002/003/004) dispatch; the founder gate
(WP-006) and advisory-first guard (WP-005) are explicitly encoded per ADR-006. The
founder's "cover all 22 primitives" decision is realised in WP-008 FIX 1 — no
code-altering primitive resolves to `None`, closing the #66-class invisibility for
the 13 previously-unmapped primitives. **WP-009 closes the two batch-gate findings
from PR-e858389** — the `str`/`Path` producer crash (CR-BATCH-01, critical) and the
non-loading Action loop-guard literal (CR-BATCH-02, high) — by forward-fixing the
merged WP-002 + WP-003 in place (nothing reached `main`); it is a release blocker
for this change yet gates no remaining WP.
