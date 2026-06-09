# Handover — Comprehensive Spec & Two-Surface Journey Walk

**Change:** CH-CQRWWR (`01KTPWDWJ7CQRWWRGPQEQ22P1M`) · primitive `harden`
**Completeness verdict:** PASS (eight perspectives + P-VER clean)

## Summary

Everything an engineering architect needs to design the implementation of this
methodology change: make the comprehensive design document always-produced
(depth sizes only the interview), add a tool-surface journey walk beside the
existing UI one, derive verifiable scenarios from every use-case flow on both
surfaces, add a UC-flow-coverage gate, and round out the document with an
always-on STRIDE threat model, C4 architecture-at-levels, and BDRs alongside ADRs.

## Key Decisions

1. **Depth is decoupled from doc-existence.** Depth sizes the interview only.
   The comprehensive document is always produced. This is the headline correction
   (FR-01..FR-04). Why: the current behaviour makes small changes ship thin specs
   with no flows, NFRs, or threat model — exactly where bugs hide.
2. **The canonical target is `features/entity-crud/DESIGN.md`.** The mandatory
   section set (FR-11) is taken from it, not invented. The Sulis `TDD.md` shape is
   restructured toward it.
3. **Tool EXISTS requires the ServiceSpec binding.** A serving interface without a
   binding is a GAP (FR-09). This generalises the MCP-Apps "looks-built-but-isn't-
   wired" lesson to the whole tool surface.
4. **Coverage is flow-level.** The UC-flow-coverage gate enumerates every
   main/alternate/exception flow and demands a covering scenario or a recorded
   out-of-scope decision (FR-12). It is a companion to #103 (scenario-required) and
   #86 (journey-coverage), not a replacement.
5. **Reuse the #98 substrate for tool driving.** No new driver mechanism (FR-14).
6. **BDR is a distinct record type from ADR.** Business/product decisions get
   BDRs; technical decisions get ADRs (FR-17).

## Assumptions (validation + impact)

| ID | Assumption | Validate by | Impact if false |
|----|------------|-------------|-----------------|
| A-01 | entity-crud/DESIGN.md is the target shape | Confirm with founder | FR-11 section set wrong |
| A-02 | #98 drives tool calls already | Confirmed in code (`driver_for_step`, `http_call`) | FR-14 needs new driver |
| A-03 | every behavioural change has UI or tool surface, else exempt | Exemption path from #85 | mis-fire on edge change |
| A-04 | always-comprehensive cost is bounded | Measure SC token cost (NFR-02) | always-on too expensive |

## Known Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Cost backlash — lite changes feel heavy, founders avoid specify | Medium | High | NFR-02 bounded cost; keep the interview small at lite; degrade detail not section existence (NFR-R01) |
| Tool-walk theatre — bindings cited but stale/wrong | Medium | Medium | Real-drive scenario (NFR-S03) is the backstop; SC-09 catches serving-but-unbound |
| Gate fatigue — three overlapping coverage gates confuse | Medium | Medium | Keep gate logic distinct but report a single founder-facing verdict |

## Recommended Implementation Sequence

1. **Phase 1 first (decouple depth).** Lowest risk, highest value. Reword the
   depth proposal (`_specify_classifier.py` `_DEPTH_PHRASE`/`_DEPTH_ALT`), remove
   doc-thinness gating in `specify/SKILL.md`, restructure the TDD template toward
   the comprehensive shape (`requirements-templates/SKILL.md`). Verify with
   SC-01..SC-05.
2. **Phase 3 next (round out the doc).** Add the always-on STRIDE section, C4
   architecture-at-levels generator, and BDR template — these are additive
   template/skill work on the now-always-produced document. Verify SC-15..SC-17.
3. **Phase 2 last (two-surface walk + gate).** Highest integration surface:
   extend `draft-architecture/SKILL.md` step 8.5 to a second table, add the
   ServiceSpec-binding bar, extend `_verify_scenario_coverage.py` with the
   UC-flow + surface dimension, and build the fixture/harness scripts the
   scenarios assume. Verify SC-06..SC-14.

The verification-harness scripts referenced by the scenarios file
(`_drive_specify.py`, `_assert_doc_sections.py`, `_verify_uc_flow_coverage.py`,
`_assert_walk_table.py`, etc.) do not exist yet — they are the drivable shape the
scenarios assume and should be created as WPs alongside Phase 2.

## Artifact Reading Order

1. `GLOSSARY.md` — locked vocabulary (depth vs doc-existence; the two surfaces;
   the three gates; ADR vs BDR).
2. `SRD.md` — full behavioural spec: FR-01..FR-17, UC-01..UC-06 with flows,
   negative requirements §6.1, scenario derivation matrix §7, Verification Plan.
3. `MISUSE_CASES.md` — the bypasses the change closes + system responses.
4. `diagrams/` — process-flows (the decoupled flow + gate), sequence (two-surface
   walk + real drive), state (hop + flow-coverage lifecycles),
   architecture-at-levels (the C4 deliverable demonstrated).
5. `NFR.md` — measurable constraints.
6. `.changes/harden-comprehensive-spec-and-journey-walk.scenarios.jsonld` — the 17
   drivable scenarios (15 tool, 2 UI), each verifiable, covering every UC flow.
7. `COMPLETENESS_REPORT.md` — the PASS verdict + deferred infra needs.

## Deferred to SEA

See `EXPLORATION_JOURNAL.md` § Deferred to SEA for the exact file list. The
engineering architect designs the edits to: `specify/SKILL.md`,
`_specify_classifier.py`, `draft-architecture/SKILL.md`, `requirements-analyst.md`,
`requirements-templates/SKILL.md`, `_verify_scenario_coverage.py`,
`scenarios/SKILL.md`, plus the new verification-harness scripts.

## Recommended Next Step

```
/sulis:draft-architecture .specifications/comprehensive-spec-and-journey-walk/
```

SEA will read `SRD.md`, `NFR.md`, `MISUSE_CASES.md`, the `diagrams/`, the
scenarios file, and the `## Deferred to SEA` journal section, then produce the
Technical Design Document, ADRs (and now BDRs), and atomic Work Packages with
Red-Green-Blue Definitions of Done. The hardening requirements from the
adversarial sweep flow into Hardening Deltas.
