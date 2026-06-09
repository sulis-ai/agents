# Sizing — Comprehensive Spec & Two-Surface Journey Walk

**Change:** CH-CQRWWR · primitive `harden` · slug `comprehensive-spec-and-journey-walk`
**Computed:** 2026-06-09 (brownfield equivalence — from code + SRD)
**Mode:** brownfield (extends existing specify/design machinery)

## Functional complexity (sFPC)

| Element | Count | Source |
|---------|-------|--------|
| ILF (data stores) | 3 | brain instance store (scenario/workflow/design/decision); `.changes/{stem}.scenarios.jsonld`; the comprehensive design document artifact |
| EIF (outbound) | 2 | #98 substrate drivers (`http_call` / `subprocess` clients); brain query reads |
| EI (mutating ops) | 4 | two-surface walk producer; scenario authoring (+ surface tag); doc emitter; contract-section emitter |
| EO (deriving ops) | 4 | `proposal_sentence`; UI walk table; tool walk table; contract→walk subset projection |
| EQ (retrieving ops) | 4 | `classify_depth`; UC-flow-coverage gate; scenario-required gate read; journey-coverage gate read |
| **sFPC** | **17** | tier M on the functional axis |

## Architecturally-significant requirements (ASR)

| Category | Count |
|----------|-------|
| NFRs (NFR-01..05, S01..S04, R01..R02, D01..D03) | 14 |
| Integrations (#98 substrate, #85 walk, #103 gate, #86 gate, brain store) | 5 |
| MUCs (MUC-01..07) | 7 |
| Cross-cutting policies (3-gate composition, founder-English FE-01..10, contract-first CF-01..12, two-surface walk) | 4 |
| Hard constraints (C-01..C-06) | 6 |
| **ASR** | **36** | tier L on the ASR axis |

## Tier decision

- sFPC 17 → tier **M**
- ASR 36 → tier **L**
- Multiple bounded contexts touched (specify stage / design stage / gate layer / scenario substrate / brain) → leans **XL**

**Take the higher tier where they disagree → tier L** (the bounded-context
signal is real but most contexts are *extended*, not net-new — the existing
substrate carries the structural weight). Confirmed tier: **L**.

## Per-pillar coverage (addressable scope)

| Pillar | Coverage | Disposition |
|--------|----------|-------------|
| **Form** (structure) | Substantially covered — the specify→design→gate pipeline, the brain port, the #98 substrate, the #85 walk all exist | Fill the gaps: the two-surface walk producer, the surface-tagged scenario authoring, the comprehensive-doc structure |
| **Armor** (hardening) | Methodology change — "Armor" maps to the *gates* (fail-closed coverage, fail-closed binding, contract-subset). #103/#86 exist; UC-flow-coverage + contract-subset are new | Fill the gaps: UC-flow-coverage gate, contract-subset assertion |
| **Proof** (verification) | The #98 substrate + scenario authoring + verifiability gate exist and are reused (FR-14, no new driver) | Fill the gaps: surface tag on scenarios; the fixture harness scripts |

Because most pillars are substantially covered, the design **references**
the existing mechanisms (Respect-Don't-Restate) and concentrates new prose on
the deltas. Target length for tier L with this coverage: ~600-900 lines of
design doc (the doc itself is the dogfood artifact, so it carries the full
target structure even where sections are short).

## Notes

- ASRs are mostly *documented* (SRD + NFR.md), not inferred — high confidence.
- File count sanity check: 8 named source files + ~6 new fixture/gate scripts =
  ~14 files. Consistent with tier L (no generated-code skew).
- No circuit breakers triggered at design time.
