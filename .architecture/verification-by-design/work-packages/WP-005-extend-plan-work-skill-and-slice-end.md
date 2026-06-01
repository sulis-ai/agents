---
id: WP-005
title: Extend plan-work SKILL.md — per-WP verification: frontmatter enforcement + slice-end deferred-needs auto-draft
status: pending
change_id: 01KT2BPBFESCCDY8F7Y5M8RN4R
kind: docs
primitive: extend
group: EXPAND
sequence_id: WP-005
dependsOn: [WP-001, WP-002]
blocks: [WP-008]
estimated_token_cost:
  input: 5k
  output: 4k
tdd_section: Form §plan-work row (line 133); Form §slice-end row (line 138); FR-005, FR-011, FR-012, FR-013, FR-015
adrs: [ADR-003, ADR-005]
verification:
  adapter: methodology
  artifact: tests/methodology/p_ver/fixtures/test_plan_work_skill_enforces_verification_field.py::test_enforcement_section_present
---

## Context

Extends `plugins/sulis/skills/plan-work/SKILL.md` (537 LOC pre-change)
in **two related but distinct ways** that share an upstream dependency
(WP-001 canonical, WP-002 rubric) and therefore ship in one WP:

1. **Per-WP `verification:` frontmatter enforcement** (FR-005, FR-013,
   ADR-003) — every WP emitted by `/sulis:plan-work` after this change
   carries the field in one of three shapes.
2. **Slice-end review extension for deferred-needs auto-draft**
   (FR-011, FR-012, ADR-005) — the existing slice-end review pattern
   gains a deferred-needs scan + idempotent auto-draft when 2+ designs
   flag the same canonical identifier.

**Why one WP, not two?** Both extensions live in `plan-work/SKILL.md`
(or in a closely-coupled slice-end reference file the SKILL.md cites).
Both depend on WP-001 + WP-002. Splitting them would create artificial
sequencing (must finish #1 before #2 can land in the same file). The
SRD couples them via FR-013 + FR-015 — the behavioural test ledger reads
from the WP's `verification:` field, which the slice-end review then
aggregates.

**Pre-Work Prior-Art Check (explicit deferral from TDD §Ambiguity Resolved):**
the TDD records "the exact reference standard file [for slice-end
review extension] TBD during WP-005". Execution MUST do this check
first:

- `grep -rn "slice-end" plugins/sulis/references/` to locate the existing
  prose for the pattern.
- If existing reference file: extend in place.
- If no dedicated file: extend `plugins/sulis/skills/lifecycle.md` (lines
  1909, 1949, 1989, 1997 per TDD).

The slice-end extension is small (≈ 30-40 LOC) — co-locating with the
existing prose is the boring choice.

## Contract

### Files modified

- `plugins/sulis/skills/plan-work/SKILL.md` — EXTEND (537 LOC pre)
- `plugins/sulis/skills/lifecycle.md` OR existing slice-end reference (TBD
  per Prior-Art Check during execution) — EXTEND

### plan-work SKILL.md sections added / modified

**Extension to the "What a Work Package Contains" section** (≈ 15 LOC):

- New row in the required-fields list: `verification:` (structured YAML
  map per ADR-003 — three shapes).
- Reference to ADR-003 + `VERIFICATION_QUESTIONS.md` for the adapter
  enumeration.

**Extension to the "Workflow" section** (≈ 30 LOC):

- New step: "Step 4d — Set the `verification:` field per WP".
- Per-WP, the skill MUST:
  - Read the change's `kind:` from the change record.
  - Apply the adapter from `VERIFICATION_QUESTIONS.md` matching the kind.
  - Set the field to one of:
    - Shape 1 (concrete): `adapter: <kind>, artifact: <test-path>`.
    - Shape 2 (deferred): `adapter: <kind>, deferred-to-follow-on: <canonical-need-id>`.
    - Shape 3 (trivial carveout): `na: true, justification: <≥30-char justification>`.
- The skill MUST NOT emit a WP with an empty / missing / malformed
  `verification:` field (P-VER failure mode 8 would otherwise fire).

**Extension to the "INDEX.md Structure" section** (≈ 10 LOC):

- Adapter Distribution table — per-adapter count across the WP set
  (mirrors the existing Primitive + Kind distribution tables).

**Cross-reference to WP-Standard:** the standard's `WP-04 Test plan`
field already exists; this WP adds the `verification:` frontmatter field
as the machine-readable seam between WP and ledger (FR-015).

### slice-end review extension sections added / modified

**Extension to the existing slice-end review prose** (≈ 30-40 LOC):

- New scan: at slice-end, walk every change in the slice's
  `.architecture/` tree, extract `deferred-to-follow-on:` values from
  every WP's `verification:` field plus deferred entries in every SRD's
  "Infrastructure needs surfaced (deferred)" subsection.
- Tally by canonical need identifier.
- For each identifier flagged by ≥ 2 changes: auto-draft a follow-on
  change at `.specifications/{identifier}/HANDOFF_TO_SEA.md` (skeleton)
  — idempotent: if the file already exists, skip.
- For singletons: surface to the founder as a one-line "deferred need
  X flagged by change Y — defer further or draft now?" prompt.
- Reference behavioural test ledger (FR-015) at
  `.specifications/{change}/verification-ledger.md` — the slice-end
  review reads the ledger to flag orphan rows (claim with neither
  artifact nor deferred-to-follow-on).

## Definition of Done

### Red — Failing tests written first

- [ ] `tests/methodology/p_ver/fixtures/test_plan_work_skill_enforces_verification_field.py::test_enforcement_section_present` exists and asserts:
  - `plugins/sulis/skills/plan-work/SKILL.md` contains the literal string `verification:` in a context naming it as a required frontmatter field.
  - The skill cites `plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md`.
  - The skill cites `ADR-003` for the three-shape schema.
  - The skill workflow contains a step instructing the agent to set the field per the adapter table.
- [ ] `tests/methodology/p_ver/fixtures/test_slice_end_scans_deferred_needs.py::test_scan_section_present` exists and asserts:
  - The chosen slice-end reference file contains a deferred-needs scan section.
  - The section cites `FR-011` (canonical identifier) + `FR-012` (auto-draft trigger) + `ADR-005` (timing).
  - The section explicitly names the 2+ threshold for auto-draft + the singleton-surface behaviour.
- [ ] Initial runs of both tests FAIL.

### Green — Implementation makes tests pass

- [ ] Extend `plugins/sulis/skills/plan-work/SKILL.md` per the Contract.
- [ ] Locate slice-end reference per Prior-Art Check; extend with the deferred-needs scan section.
- [ ] Citations to canonical + ADR-003 + ADR-005 present.
- [ ] Three-shape schema (per ADR-003) documented in plan-work SKILL.md.
- [ ] Idempotency requirement explicit in the slice-end scan section.
- [ ] Both tests from Red phase pass.

### Blue — Refactor + polish

- [ ] plan-work SKILL.md edits stay within its existing structure (no new top-level sections without strong justification).
- [ ] Slice-end extension is co-located with existing prose; new section heading is descriptive (e.g., "Slice-end deferred-needs scan").
- [ ] WP-Standard cross-reference added where the `verification:` field is described (link to WP-04 Test plan).
- [ ] Cross-reference to FR-015 behavioural test ledger.
- [ ] No inline duplication of question text or adapter table content — cite only.

## Sequence

- **Sequence ID:** WP-005
- **dependsOn:** WP-001 (canonical exists), WP-002 (rubric P-VER exists — the skill's enforcement is checked by P-VER failure mode 8)
- **blocks:** WP-008 (E2E test dispatches the updated skill against a fixture TDD)
- **Parallelisable with:** WP-003, WP-004, WP-006, WP-007 (different files)

## Estimated Token Cost

- **Input:** ~5k (plan-work SKILL.md + slice-end prose + ADR-003 + ADR-005 + WP-Standard)
- **Output:** ~4k (≈ 80 LOC plan-work + ≈ 40 LOC slice-end)
- **Total:** ~9k

## Notes

- **Why this WP is co-located (justification recorded for P2 atomicity):**
  the plan-work-skill change and the slice-end change are tightly coupled
  via the `deferred-to-follow-on:` field. Splitting would either (a)
  duplicate the field documentation across two WPs (drift risk) or (b)
  force WP-005a to ship a half-enforced field that WP-005b later
  finishes. Single WP, single responsibility ("design-side enforcement
  of the verification field").
- **Behavioural test ledger location** (per TDD §Open Architecture
  Questions item 3) defaults to
  `.specifications/{change}/verification-ledger.md` (per FR-015).
  Cross-change linkage convention TBD — this WP records the default;
  cross-change usage if it arises is a future change.
- **No inline duplication anywhere.** The three-shape schema is described
  in ADR-003; this WP cites ADR-003, not copies it.
