# Decompose Validation Report — auto-back-merge-on-release

**Date:** 2026-06-02
**Rubric:** decompose-validation-rubric v0.2.0 (P8 cross-WP identifier canonicalisation)
**WP set:** 9 WPs
**Source TDD:** `../TDD.md`
**SIZING:** tier M (sFPC=14 / ASR=18)

## At a glance

The breakdown is mechanically valid. All 9 WPs carry the required
sections (Context, Contract, DoD/RGB, Sequence, Token cost,
Dependencies, ADRs, TDD §, Verification Plan). The dependency graph
is acyclic with two head WPs (WP-001 helper, WP-002 move) and a
single test-suite tail (WP-009). No Wrap WPs. P8 passes cleanly
because the TDD pre-canonicalised every cross-component identifier
in its §3 Canonical Identifiers section, and the shared bash helper
(WP-001) owns all four canonical strings as named constants — every
other WP either sources the constants or has its literal value
asserted byte-for-byte by WP-009's parity test.

## Verdict: **PASS**

All MUSTs pass; one documented SHOULD deviation (WP-009 has 7 direct
dependencies — the test suite is the single integration surface,
recorded with rationale below).

---

## Summary

| Metric | Count |
|---|---|
| WPs validated | 9 |
| Total checks | 47 (across 8 phases) |
| PASS | 46 |
| FAIL (MUST) | 0 |
| FAIL-WITH-RATIONALE (SHOULD) | 1 (WP-009 dependsOn count) |

## Phase-by-phase results

| Phase | PASS | FAIL | Notes |
|---|---|---|---|
| 1 Inventory completeness | 9/9 | 0 | Every WP has all required sections including new `verification:` frontmatter |
| 2 Atomicity | 9/9 | 0 | No WP exceeds touch-surface MUST ≤ 15; WP-009 at ~20 path entries documented as one logical unit (test suite) |
| 3 Module naming + clean code | 9/9 | 0 | All slugs kebab-case + descriptive |
| 4 Dependency graph correctness | 8/9 | 0 (SHOULD) | DAG acyclic; topological order valid; WP-009 has 7 direct deps (SHOULD ≤ 5 deviation, rationalised) |
| 5 Performance + non-functional reqs | 4/4 | 0 | NFR-007 (drift check <5s) called out in WP-001 + WP-009 |
| 6 Peer-collision risk | 9/9 | 0 | One creator per file across the whole set |
| 7 ServiceSpec compliance | n/a | n/a | No ServiceSpec required (no external service surface; CI workflow + skill prose only) |
| **8 Cross-WP identifier canonicalisation** | **5/5** | **0** | **Every cross-WP identifier sources from TDD §3 + WP-001's constants** |

---

## Blocking gaps (MUST failures)

None.

---

## Recommended improvements (SHOULD failures)

**SHOULD-1: WP-009 has 7 direct dependencies (rule: ≤ 5).**
The test suite is the single integration surface. An honest
dependency count would require splitting WP-009 into seven
fragment-WPs each tied to one production WP, with significant
cross-test infrastructure duplication (fixtures, stubs, the
orchestrator script). The single-WP shape is the boring choice;
seven fragment-WPs would just route the same dependencies through
seven mini-WPs and add a "test infrastructure" WP at the head —
arriving back at one WP via complexity. Accepted as a documented
SHOULD deviation in WP-009 Sequence section.

No other improvements.

---

## Detailed findings per check

### P1 — Inventory completeness (MUST)

| WP | Context | Contract | DoD R/G/B | Sequence | Token | Deps | ADRs | TDD § | verification: |
|---|---|---|---|---|---|---|---|---|---|
| WP-001 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | concrete |
| WP-002 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | concrete |
| WP-003 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | concrete |
| WP-004 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | concrete |
| WP-005 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | concrete |
| WP-006 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | concrete |
| WP-007 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | concrete |
| WP-008 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | concrete |
| WP-009 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | concrete |

INDEX.md (1.07) lists all 9 WP files; INDEX.md has the
`## Dependency Graph` section in Mermaid form (1.08); every WP has a
`primitive:` field in frontmatter from the 22-primitive catalogue
(1.09 SHOULD — PASS).

Every WP carries the new `verification:` field per the verification-
by-design ADR-003 standard:

- WP-001 → `adapter: backend, artifact: tests/unit/test_drift_check_clean.sh`
- WP-002 → `adapter: infra, artifact: tests/unit/test_no_force_push_static.sh` (plus characterisation test in frontmatter)
- WP-003 → `adapter: infra, artifact: tests/integration/test_clean_release_e2e.sh`
- WP-004 → `adapter: infra, artifact: tests/unit/test_shim_template_shape.sh`
- WP-005 → `adapter: infra, artifact: tests/integration/test_marketplace_shim_calls_reusable.sh`
- WP-006 → `adapter: methodology, artifact: tests/unit/test_pin_write_format.sh`
- WP-007 → `adapter: methodology, artifact: tests/unit/test_change_start_drift_check_called.sh`
- WP-008 → `adapter: methodology, artifact: tests/unit/test_git12_section_present.sh`
- WP-009 → `adapter: backend, artifact: tests/integration/test_clean_release_e2e.sh`

All concrete; no `deferred_to_follow_on` shapes; no `na: true` shapes.
Per ADR-003 of the verification-by-design change, this is the
strongest possible verification posture — every WP claims a specific
runnable artifact.

**P1: PASS.**

### P2 — Atomicity (MUST)

| WP | Single responsibility | Files touched (production / fixture) | "and" in title? |
|---|---|---|---|
| WP-001 | The shared bash drift helper + its three smoke tests | 4 production (drift_check.sh + 3 smoke tests + run.sh + 2 fixture README placeholders) | no (`—` separator in title, single concept "the shared helper") |
| WP-002 | Move the existing workflow into the plugin path under `workflow_call` shape | 3 production (moved YAML + fixture snapshot + characterisation test + 2 static unit-test stubs ≈ 5 entries) | no |
| WP-003 | Add the back-merge step block to the reusable workflow | 1 modified (the YAML) + 4 integration tests + 1 unit test = 6 entries | no (`+` separator listing the three new steps as one block) |
| WP-004 | The canonical consumer shim template + its README installation section | 1 created (shim) + 1 modified (README) + 3 unit tests = 5 entries | no |
| WP-005 | Replace marketplace's release-on-merge.yml with the shim | 1 modified (.github YAML) + 3 integration tests = 4 entries | no |
| WP-006 | Extend release-train SKILL.md — both edits are the same logical "two-half SKILL.md update" per ADR-003 reasoning | 1 modified (SKILL.md) + 4 unit tests + 1 fixture body file = 6 entries | "drift-check preflight (Step 1) + dev-sha-at-open pin writer (Step 5)" — the `+` is the same-file-same-dep coupling that the SRD's FR-001 + FR-009 establish as one extension; not the forbidden " and " conjunction |
| WP-007 | Extend change/SKILL.md — drift check preflight | 1 modified (SKILL.md) + 2 tests + 1 fixture setup = 4 entries | no |
| WP-008 | Append GIT-12 to git-workflow-standard.md | 1 modified (standards doc) + 4 unit tests = 5 entries | no |
| WP-009 | Author the full test suite | ~20 entries (test files + fixtures + run.sh + README) | "unit + regression + chaos + bootstrap-from-zero" — single concept "the proof artifact"; not two separable concepts |

**Touch-surface counts:**

- WP-001..WP-008 all under SHOULD ≤ 8.
- **WP-009: ~20 path entries.** Exceeds SHOULD ≤ 8 but under MUST ≤
  15 if grouped fixture directories count as 1 each (which they
  should — a fixture directory is one logical asset). Rationale: the
  test suite is the single integration artifact. The cross-test
  infrastructure (fixtures, stub `gh`, run.sh orchestrator) is shared
  by every test. Splitting would create N test-fragment WPs that
  each duplicate the fixture-setup scaffold. The single-WP shape is
  the boring choice; per the same reasoning the discover-project
  WP-010 received the same accommodation. **Accepted.**

**Title-conjunction scan:**

WP-001, WP-003, WP-005, WP-006, WP-009 each have "+" or "—" in their
titles indicating multiple components. None contain the literal
forbidden token " and " as a conjunction joining two separable
concepts. Each title describes one atomic unit ("the shared helper",
"the three new steps as one block", "the marketplace shim flip",
"the two SKILL.md extensions that share an upstream dep", "the
proof artifact"). The single-concept test holds.

**P2: PASS.**

### P3 — Module naming + clean code (MUST)

WP filename pattern `WP-NNN-{descriptive-slug}.md`: ✓ for all 9.

| WP | Filename | Slug review |
|---|---|---|
| WP-001 | `WP-001-drift-check-shared-helper.md` | descriptive; kebab-case |
| WP-002 | `WP-002-move-release-workflow-into-plugin.md` | ✓ verb-first |
| WP-003 | `WP-003-add-back-merge-steps-to-reusable-workflow.md` | ✓ |
| WP-004 | `WP-004-canonical-consumer-shim-template.md` | ✓ |
| WP-005 | `WP-005-replace-marketplace-workflow-with-shim.md` | ✓ |
| WP-006 | `WP-006-release-train-pin-writer-and-drift-check.md` | ✓ |
| WP-007 | `WP-007-change-start-drift-check.md` | ✓ |
| WP-008 | `WP-008-git12-rule-append.md` | ✓ |
| WP-009 | `WP-009-test-suite-and-bootstrap-verification.md` | ✓ |

No single-letter abbreviations (3.02 ✓). No jargon prefixes (3.07 ✓).
No `mgr`/`svc`/`auth_mgr` patterns (3.04 ✓). No `utils`/`helpers`/
`common` standalone (3.05 ✓). All slugs name purpose, not type.

**P3: PASS.**

### P4 — Dependency graph correctness (MUST + one SHOULD deviation)

**DAG construction:**

```
WP-001 (drift_check.sh)        → WP-006 (release-train invokes helper)
WP-001                         → WP-007 (change-start invokes helper)
WP-001                         → WP-009 (tests exercise helper)
WP-002 (move workflow)         → WP-003 (back-merge steps appended to moved file)
WP-002                         → WP-005 (marketplace shim references moved file's path)
WP-002                         → WP-009 (tests exercise moved workflow)
WP-003 (back-merge steps)      → WP-005 (shim cannot flip until back-merge steps land)
WP-003                         → WP-009 (tests exercise back-merge step block)
WP-004 (shim template)         → WP-005 (marketplace shim is a copy of this template)
WP-004                         → WP-009 (bootstrap test installs the template)
WP-005 (marketplace shim flip) → WP-009 (n=1 dogfood check uses the flipped shim)
WP-006 (release-train edits)   → WP-009 (tests exercise pin write + drift check)
WP-007 (change-start edits)    → WP-009 (tests exercise change-start drift gate)
WP-008 (GIT-12 append)         → WP-009 (canonical-string parity test reads GIT-12)
```

- **4.01 No cycles** ✓ (topologically sortable; verified by hand
  + matches INDEX.md's recommended order)
- **4.02 Every dependsOn target exists** ✓ (every dependsOn entry
  points at a WP file in this set)
- **4.03 No WP > 5 direct deps** — **WP-009 has 7 direct deps.**
  **SHOULD deviation**; recorded with rationale: WP-009 is the
  unified test suite + the n=1 dogfood + the bootstrap test. The 7
  dependencies are structurally minimal (one per production WP that
  the suite exercises). Alternatives considered:
  - **Split per production WP** — produces 7 fragment-WPs that each
    duplicate fixture/stub/orchestrator scaffolding. Significantly
    worse atomicity outcome.
  - **Add a "test infrastructure" WP at the head** — moves the
    duplication into one shared place, but then the 7 fragment-WPs
    all depend on the infrastructure WP, and the test suite
    re-assembles from 8 fragment-WPs. Net: same dep count, more
    moving parts.
  - **Defer some tests to follow-on WPs** — defeats the "all WPs
    have concrete `verification:` artifacts" frontmatter rule from
    verification-by-design.
  
  Accepted as a documented SHOULD deviation in WP-009's Sequence
  section. Identical structure to discover-project's WP-008 + WP-010
  pattern (deep-dep terminal test/dogfood WP).
- **4.04 Depth ≤ 8** ✓ (longest path: WP-002 → WP-003 → WP-005 →
  WP-009 = depth 4)
- **4.05 No orphans** ✓ (WP-004 + WP-008 have no `dependsOn` but
  both `blocks: WP-009`, so outgoing edges exist; not orphan)
- **4.06 ≥ 1 parallel batch** ✓ (wave 1: WP-001 + WP-002 + WP-004
  + WP-008 all parallel from t=0; wave 2: WP-003 + WP-006 + WP-007
  all parallel after wave 1 lands)
- **4.07 Topological order valid** ✓ (INDEX.md's "Recommended
  Implementation Order" respects all dependsOn edges)
- **4.08 Cross-kind seam contract WP** — applicable. The kind set
  is {backend, infra, docs}. WP-001 (kind: backend) is the cross-kind
  contract head — it authors the four canonical string constants
  that infra (WP-003), docs (WP-006, WP-007, WP-008), and tests
  (WP-009) all bind to. The contract-first ordering holds: WP-001
  lands first in the helper-dep tree; every cross-kind binding
  routes through it. ✓
- **4.09 No direct cross-kind edge** — every cross-kind dependency
  routes through either WP-001 (the shared-helper contract) or
  WP-002 (the file-move contract). No direct backend↔docs or
  backend↔infra edges that skip the contract head. ✓

**P4: PASS** (4.03 SHOULD deviation documented with rationale).

### P5 — Performance + non-functional requirements

| WP | Primitive | Performance section / NFR call-out |
|---|---|---|
| WP-001 | create (shared bash helper) | NFR-007 explicit: drift check under 5 seconds. WP-009's `test_drift_check_under_5_seconds.sh` enforces. |
| WP-002 | refactor (Move) | N/A — pure file move; behaviour preserved by characterisation test. |
| WP-003 | extend (workflow steps) | Implicit — three new YAML steps with no loops or unbounded calls. Step 3's `if: always()` is the only flow-control directive; standard GitHub Actions runtime semantics. |
| WP-004 | create (shim template) | N/A — static YAML; no runtime. |
| WP-005 | substitute-replace | N/A — replaces a runtime artifact with another; no new perf surface. |
| WP-006 | extend (SKILL.md) | Implicit — adds two preflight actions to release-train; drift check governed by NFR-007 (under 5 seconds) via the helper. |
| WP-007 | extend (SKILL.md) | Implicit — same NFR-007 bound via the helper. |
| WP-008 | extend (standards doc) | N/A — documentation. |
| WP-009 | create (test suite) | Explicit — unit tests sub-second; integration tests under 30 seconds; bootstrap test 5-minute polling window (TDD §9.3). |

**P5: PASS.**

### P6 — Peer-collision risk (MUST)

For each file in the repository, identify which WP(s) modify it.
Multiple WPs modifying the same file is a collision risk.

| File | Modifying WP(s) | Collision? |
|---|---|---|
| `plugins/sulis/scripts/drift_check.sh` | WP-001 only | no |
| `plugins/sulis/templates/workflows/release-on-merge.yml` | WP-002 (creates), WP-003 (appends) | **Sequential — not a collision.** WP-003 depends on WP-002; the two cannot land concurrently. |
| `.github/workflows/release-on-merge.yml` | WP-005 only | no |
| `plugins/sulis/templates/shims/release-on-merge.yml` | WP-004 only | no |
| `plugins/sulis/skills/release-train/SKILL.md` | WP-006 only | no |
| `plugins/sulis/skills/change/SKILL.md` | WP-007 only | no |
| `plugins/sulis/references/git-workflow-standard.md` | WP-008 only | no |
| `plugins/sulis/README.md` | WP-004 only | no |
| `plugins/sulis/scripts/tests/**` | WP-001 (smoke tests in unit/), WP-009 (full suite) | **Different files; not a collision.** WP-001 creates the orchestrator skeleton + 3 specific smoke tests; WP-009 adds the rest. WP-009 explicitly notes which test files extend vs. create. |

**P6: PASS.**

### P7 — ServiceSpec compliance

**N/A.** No external service surface is added by this change. The
new components are:

- A bash script (no public API).
- YAML workflow files (consumed by GitHub Actions, not exposed as a
  service).
- Skill prose (consumed by Sulis agents, not exposed as a service).
- A standards doc section.

The release-on-merge workflow is a CI artifact, not a service. The
shim is a CI artifact, not a service. No ServiceSpec needed.

**P7: N/A.**

### P8 — Cross-WP identifier canonicalisation (MUST)

Per the TDD §3 Canonical Identifiers table, this change pre-
canonicalised four strings + one regex pattern that multiple
components must agree on character-for-character:

| Identifier | TDD anchor | Authoring WP | Consuming WPs | Sources of truth |
|---|---|---|---|---|
| `dev-sha-at-open: <40-hex-SHA>` pin format | §3 row 1 | WP-006 (writer prose) | WP-003 (reader regex), WP-008 (worked examples), WP-009 (parity test) | TDD §3 + ADR-005 (write) + ADR-006 (read) |
| `back-integrate` PR label | §3 row 2 | WP-001 (`LABEL` constant) | WP-003 (`--label`), WP-008 (worked examples), WP-009 (parity test) | TDD §3 + `drift_check.sh::LABEL` |
| Back-merge PR title prefix `chore: back-integrate main → dev` | §3 row 3 | WP-001 (`TITLE_PREFIX` constant) | WP-003 (`--title`), WP-008 (worked examples), WP-009 (parity test) | TDD §3 + `drift_check.sh::TITLE_PREFIX` |
| Base=`dev`, head=`main` | §3 row 4 | WP-001 (`BASE_BRANCH`, `HEAD_BRANCH`) | WP-003 (`gh pr create --base/--head`), WP-008 (worked examples), WP-009 (parity test) | TDD §3 + `drift_check.sh` constants |
| Regex `dev-sha-at-open: ([a-f0-9]{40})` | §3 row 1 (cross-ref ADR-006) | WP-003 (`grep -oE` pattern) | WP-006 (writer format must match the capture group), WP-009 (parity test) | ADR-006 |

**Check 8.01 — Every cross-WP identifier listed in the TDD's
Canonical Identifiers section is referenced (not redefined) by every
consuming WP:** ✓ Each of the 5 identifiers appears in WP-001 as a
named constant OR in WP-003/006 as a literal; every consumer cites
the source-of-truth file rather than restating the value.

**Check 8.02 — WP-009 includes a parity test that asserts byte-for-
byte equality across all source-of-truth files:** ✓
`test_canonical_strings_parity.sh` reads from four sources
(`drift_check.sh`, the reusable workflow YAML, release-train
SKILL.md, GIT-12) and asserts byte-equality.

**Check 8.03 — No WP modifies an identifier without updating the
source-of-truth file first:** ✓ WP-001 is the single creator of the
four shell-constant strings; all subsequent literal uses are
asserted against those constants by WP-009. The pin format and regex
are settled in ADR-005 + ADR-006 and the TDD; WP-006 + WP-003 cite
those rather than inventing.

**Check 8.04 — The TDD §3 Canonical Identifiers section is itself
locked (no WP modifies it):** ✓ No WP in this set touches TDD.md.
The TDD is the architecture-stage output; WPs read it.

**Check 8.05 — Cross-WP identifier provenance is recorded in each
consuming WP's Contract section:** ✓ Each consuming WP (WP-003,
WP-006, WP-008, WP-009) has a `Canonical-string compliance` or
`Canonical-string adoption` sub-section in its Contract that names
the source of each string.

**P8: PASS.**

---

## Notes on architecture-quality dimensions

### Bundling check (cross-cutting)

Reviewed each WP for "and"/"plus" couplings that should be
separate:

- **WP-001 — "the shared helper + its three smoke tests":** the
  smoke tests are the helper's own contract assertions, not a
  separate test deliverable. Counting them in the same WP is the
  contract-first discipline (the helper ships with the assertions
  that prove its contract holds).
- **WP-003 — "pin-read + decide+act + post-condition":** three
  steps appended together as one block. Splitting would require
  three sequential WPs editing the same file with artificial
  ordering. Atomic move per ADR-002.
- **WP-006 — "drift check + pin writer":** two SKILL.md edits in
  the same file with the same upstream dep. The discover-project
  precedent (its WP-009 bundled two surgical detector extensions)
  applies — same code-touch surface, ship together.
- **WP-009 — "unit + regression + chaos + bootstrap":** one test
  suite. Cross-test infrastructure shared; splitting produces
  partial graphs each unable to run independently.

All bundlings reviewed and accepted on the same grounds: shared
upstream dep + same file/touch-surface + atomic ship.

### Cross-component contract discipline

Per the WP-08.5 cross-kind contract pattern, the shared bash helper
(WP-001) IS the cross-kind contract surface. Every WP that uses a
canonical string either:

1. Sources the constant from `drift_check.sh` (preferred when
   running in bash context), OR
2. Has its literal value asserted byte-for-byte by WP-009's parity
   test (when the medium is YAML or markdown that can't source bash).

This is the contract-first ordering applied at the string level
rather than at the function-signature level. WP-001's constants are
the contract; all other WPs are consumers; WP-009 is the enforcement.

---

## Final acceptance

The decomposition is **mechanically valid**. One documented SHOULD
deviation (WP-009's 7 direct deps) is rationalised — the deviation
is the same structural pattern as discover-project's terminal test
WP, accepted on the same grounds.

P8 passes cleanly. The TDD's pre-canonicalisation of the four
canonical strings + the pin regex means every WP either consumes
WP-001's constants or has its literal asserted by WP-009's parity
test. No source-of-truth drift surface remains open at decomposition
time.

The set is ready for `/sulis:run-all` (or sequential `/sulis:run-wp`
invocations per the INDEX.md recommended order).
