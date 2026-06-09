---
id: WP-006
title: Add the comprehensive DESIGN.md template and always-comprehensive emitter
status: pending
sequence_id: WP-006
dependsOn: [WP-001, WP-003, WP-005]
blocks: [WP-009, WP-011]
estimated_token_cost:
  input: 9k
  output: 7k
tdd_section: 7.4 (requirements-templates/SKILL.md) + 6 (Target Structure)
adrs: [ADR-002]
primitive: create
group: expand
kind: docs
verification:
  adapter: methodology
  artifact: plugins/sulis/scripts/tests/test_drive_specify.py::test_lite_document_has_all_mandatory_sections
---

## Context

`requirements-templates/SKILL.md` carries SRD/UC/NFR/Verification-Plan templates
but no comprehensive DESIGN.md Target-Structure template — the Target Structure
(FR-11) has nothing to emit from. ADR-002 makes one structure, emitted always,
modelled on the canonical `entity-crud/DESIGN.md`. This WP creates the base
template (§1..§10 skeleton incl. the mandatory NFR section with measurable
targets, FR-06, and a contract-section skeleton stub) and wires the
always-comprehensive emitter that WP-005's severed path routes to. The STRIDE /
C4 / BDR / full-CF-10-contract sub-templates are layered on in P3 (WP-011); this
WP lands the structure and the always-on emission.

Advances DESIGN.md §6.5 hops A4/A5/T2 (GAP → WP) and the §7.4
`requirements-templates/SKILL.md` "Create" row.

## Contract

```text
# plugins/sulis/skills/requirements-templates/SKILL.md (this WP adds a section)
#   New: a comprehensive DESIGN.md Target-Structure template with headings for
#   §1 exec-summary, §2 problem-discovery, §3 stakeholders, §4 functional-
#   requirements, NFR (measurable), constraints, assumptions, dependencies,
#   threat-model (skeleton — filled by WP-011), §5 scope, §6 use-cases,
#   §7 solution-design (incl. an interface-contract skeleton stub),
#   verification-plan. Order fixed by the canonical (C-01). The
#   `## Verification Plan` heading is verbatim per C-02 / ADR-001.
# Emission: the specify/analyst path (WP-005) reads THIS template for every
#   change regardless of depth. Thin sections render "n/a — <justification>"
#   (NFR-R01), never dropped.
```

Invariants:
- The section set is identical across lite/standard/deep (SC-02, FR-02) — only
  interview-derived detail differs.
- Every mandatory section is present; an unpopulated one carries an explicit
  `n/a — <reason>` (SC-03, NFR-R01).
- The NFR section always carries measurable targets per category (SC-05, FR-06).
- The `## Verification Plan` heading is verbatim (C-02) so P-VER's regex anchors.
- Always-comprehensive cost at lite ≤ 1.6× legacy lite (NFR-02).

## Definition of Done

### Red — Failing tests written
- [ ] `test_drive_specify.py::test_lite_document_has_all_mandatory_sections` — drive `sample-user-facing` at lite; `_assert_doc_sections --require <all>` exits 0 (SC-01).
- [ ] `test_drive_specify.py::test_section_set_identical_across_depths` — lite/standard/deep ⇒ `_assert_same_section_set` exits 0 (SC-02).
- [ ] `test_drive_specify.py::test_unpopulated_section_marked_na` — `no-dependencies` fixture ⇒ `_assert_section_na --section dependencies` exits 0 (SC-03).
- [ ] `test_drive_specify.py::test_nfr_section_measurable` — `_assert_measurable_nfr --categories performance,security,reliability` exits 0 (SC-05).

### Green — Implementation makes tests pass
- [ ] The comprehensive template exists in `requirements-templates/SKILL.md` with §1..§10 in canonical order.
- [ ] The emitter produces all sections at lite, marking thin ones n/a.
- [ ] The NFR section template forces measurable targets.
- [ ] All four scenario assertions pass through `_drive_specify` (WP-001) + WP-003 inspectors.

### Blue — Refactor complete
- [ ] Section-skeleton fragments shared with the SRD/UC/NFR templates where they overlap (no duplicated heading definitions).
- [ ] No new behaviour in Blue.
- [ ] All tests still green.

## Sequence

- **dependsOn:** WP-001 (the driver), WP-003 (the section assertions), WP-005 (the severed path that routes here)
- **blocks:** WP-009 (the tool-walk draws operations from the contract skeleton this WP stubs), WP-011 (STRIDE/C4/contract sub-templates extend this base template)
- **Parallelisable with:** WP-007, WP-008 (P2 scenario-side WPs, different file scope)

## Estimated Token Cost

- **Input:** ~9k (this WP + the canonical structure + the existing templates)
- **Output:** ~7k (the template section + emitter wiring + verification through WP-001/003)
- **Total:** ~16k

## Notes

- This WP lands the base structure + always-on emission; the contract section is
  a *skeleton stub* here (so WP-009's walk has a target) and is filled to full
  CF-10 in WP-011. Keeping the skeleton here preserves contract-first ordering
  within the phase sequence (BDR-001).
- ADR-002: structure invariant, detail = f(intake). Depth must never be read to
  decide which sections exist.
