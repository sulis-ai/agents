---
id: WP-004
title: Append P-PLAT (Phase 10) to decompose-validation-rubric.md
status: pending
change_id: "01KT3X2M0JHFN583DKKV77W83C"
kind: methodology
primitive: extend
group: REINFORCE
sequence_id: WP-004
dependsOn: [WP-001]
blocks: [WP-005, WP-007]
estimated_token_cost:
  input: 4k
  output: 4k
tdd_section: "Form §component 6 (line 82); Canonical Identifiers §rubric-phase-id (lines 52-55); Armor A-7, A-8 (lines 140-141); FR-015; NFR-005, NFR-007; MUC-004, MUC-007"
adrs: [ADR-006, ADR-003]
verification:
  adapter: methodology
  artifact: tests/methodology/test_pplat_rubric.py::test_phase_pplat_present_and_complete
---

## Context

Appends a new phase — **`P-PLAT`**, numbered **Phase 10** — to
`plugins/sulis/references/decompose-validation-rubric.md`, immediately after
P-VER (Phase 9). P-PLAT is the **mechanical enforcement leg** of the
defence-in-depth gate (the prose in WP-003 is the friendly front leg). A
gated third-party touch with no referenced Platform Contract fails P-PLAT
**regardless of prose edits** — this is the control for MUC-004 (a weakened
prose gate cannot bypass the rubric).

**TDD reference:** Form component 6 (line 82) names this file and mandates
P-PLAT mirror P-VER. The rubric-phase id `P-PLAT` (cited by name, not
position) is locked in TDD §Canonical Identifiers lines 52-55. ADR-006 fixes
the placement (Phase 10, append after P-VER), the grandfather mechanism, and
the verdict semantics.

**Why this depends on WP-001.** P-PLAT's provenance + conformance checks
assert against the claim-entry schema and the harness-run-reference field
defined in the standard. Until the standard exists, P-PLAT has no schema to
enforce.

**Why this blocks WP-005.** `plan-work` (WP-005) emits the `platform:` /
`touch-class:` WP-frontmatter fields **so that P-PLAT can detect** which WP
set touches a gated third party (OAQ-4). The detection field's *meaning* is
specified by P-PLAT (this WP); `plan-work` *emits* it (WP-005). P-PLAT is the
authority on the field's semantics, so it lands first.

**Pre-Work Prior-Art Check:** the rubric already has P-VER (Phase 9, added by
the verification-by-design change) which solved every structural problem
P-PLAT faces — grandfathering by change `started_at`, a failure-mode table,
FE-readable remediation strings. P-PLAT **mirrors P-VER**; it does not invent
a new pattern. Respect-don't-restate: P-PLAT **references** P-VER's grandfather
mechanism + verdict semantics rather than restating them (ADR-006).

## Contract

### Files modified

- `plugins/sulis/references/decompose-validation-rubric.md` — EXTEND
  (new Phase 10; front-matter constant; summary-table + self-attestation rows;
  version history row).

### The `platform:` / `touch-class:` detection signal (OAQ-4)

P-PLAT detects a gated third-party touch via an **explicit WP-frontmatter
declaration** (not prose scanning — brittle, MUC-004-adjacent). This WP
**specifies** the field's meaning; WP-005 makes `plan-work` **emit** it:

```yaml
platform: "<lowercase-hyphenated platform slug>"   # e.g. github-actions
touch-class: "write | deploy | read-only"
```

- A WP set containing **any** WP with `touch-class: write` or `deploy` and a
  `platform:` value MUST reference a Platform Contract at
  `platform-contracts/<platform>.md`, or P-PLAT fails.
- `touch-class: read-only` → soft (advisory note, no fail) per ADR-001.

### New "Phase 10 — P-PLAT (Platform Contract)" section

Mirrors P-VER's structure exactly (ADR-006):

**Front matter — new field:**

```yaml
platform_contract_required_from: ""   # ISO-8601; filled by sulis-change finish at merge
```

**Grandfather sub-phase** (before any P-PLAT.NN check): read the candidate
change's `started_at` and compare against `platform_contract_required_from`;
changes started before the constant pass `PASS — grandfathered` (NFR-005).
Empty constant (pre-merge / dogfood) → run all checks against live artifacts.
References P-VER's grandfather mechanism rather than restating it.

**Failure-mode table** — one MUST row per contract-integrity control (TDD
Armor table A-1..A-8), each with a deterministic pass criterion:

| ID | Severity | Check | Pass criterion | MUC |
|---|---|---|---|---|
| **10.01** | MUST | Gated write/deploy touch ⇒ a referenced Platform Contract | WP-set scan: any `touch-class:write\|deploy` + `platform:X` ⇒ `platform-contracts/X.md` exists & is referenced | MUC-004 / FR-015 |
| **10.02** | MUST | Contract carries a harness-run reference | Front-matter `harness-run:` non-empty | MUC-007 / A-8 |
| **10.03** | MUST | Every `inferred:false` claim has source+quote+retrieval-date | Schema invariant scan | MUC-001 / A-1 |
| **10.04** | MUST | No `inferred:true` claim carries a `source` | Schema invariant scan | MUC-006 / A-4 |
| **10.05** | MUST | Every `load_bearing:true` claim has probe + probe-result (or justified `deferred:<id>`) | Schema invariant scan | MUC-005 / A-6 |
| **10.06** | MUST | `probe-result:confirmed` ⇒ non-empty `probe-evidence` | Schema invariant scan | MUC-005 / A-6 |
| **10.07** | SHOULD | Claims within freshness window (retrieval-date ≤ 180d on reuse) | Date compare; advisory flag | MUC-003 / A-5 |

**Verdict semantics:** any P-PLAT MUST failure collapses the verdict to
GAPS_FOUND with the FE-readable remediation: *"Platform Contract required at
`plugins/sulis/references/platform-contracts/<platform>.md`."* (ADR-006).

**Summary-table + self-attestation + version-history rows** extended for
Phase 10 (minor version bump; no re-versioning of existing phases — ADR-006).

## Definition of Done

### Red — Failing test written first

- [ ] `tests/methodology/test_pplat_rubric.py::test_phase_pplat_present_and_complete`
  asserts:
  - The rubric contains a `## Phase 10 — P-PLAT (Platform Contract)` header.
  - Rows for checks `10.01`..`10.07` present (regex count = 7).
  - Front matter contains `platform_contract_required_from:`.
  - The grandfather sub-phase prose cites ADR-006.
  - The self-attestation block has a P10 row.
- [ ] Initial run FAILS (the phase does not exist yet).

### Green — Implementation makes the test pass

- [ ] Extend the rubric with Phase 10 per the Contract section.
- [ ] All seven check rows present with IDs / severities / criteria.
- [ ] Grandfather sub-phase references P-VER's mechanism (does not restate).
- [ ] `platform:` / `touch-class:` detection signal documented as the input.
- [ ] Front-matter constant, summary-table row, self-attestation row, version
  row added.
- [ ] Red-phase test passes.

### Blue — Refactor + polish

- [ ] Each check row cross-links its source MUC + TDD §Armor row.
- [ ] Remediation strings FE-readable (FE-01..11).
- [ ] No restating of P-VER's grandfather or verdict prose — citation only.
- [ ] Phase 10 sits after Phase 9, before the anti-patterns section
  (ordering preserved).

## Sequence

- **Sequence ID:** WP-004
- **dependsOn:** WP-001 (P-PLAT enforces the schema the standard defines).
- **blocks:** WP-005 (`plan-work` emits the detection field P-PLAT consumes),
  WP-007 (P-PLAT fixtures assert against this phase).
- **Parallelisable with:** WP-002, WP-003 (disjoint file surface — this WP
  owns the rubric).

## Estimated Token Cost

- **Input:** ~4k (existing rubric + P-VER section for the mirror pattern +
  ADR-006 + ADR-003 + TDD Armor table).
- **Output:** ~4k (Phase 10 prose + table + rows).
- **Total:** ~8k.

## Notes

- **P-PLAT is prose, not Python.** This WP authors the rubric check spec; the
  fixture tests in WP-007 assert the prose contract. Mirrors WP-002 of the
  verification-by-design change.
- The `platform_contract_required_from:` constant is the only field
  `sulis-change finish` touches at merge time; everything else commits here.
- **Detection-field authority:** this WP owns the *meaning* of `platform:` /
  `touch-class:`; WP-005 owns *emitting* it from `plan-work`. Splitting authority
  from emission keeps P-PLAT (the consumer/enforcer) as the spec source.

## Verification Plan (per-WP)

- **Adapter:** `methodology` — **Shape 1 (concrete).**
- **Artifact:** `tests/methodology/test_pplat_rubric.py::test_phase_pplat_present_and_complete`.
- **Observable:** the rubric carries Phase 10 with seven checks, the front-matter
  constant, the grandfather sub-phase, and the FE-readable remediation. The
  fail/grandfather behaviour against synthetic WP sets is exercised in WP-007.
- **No resilience primitive:** methodology prose.
