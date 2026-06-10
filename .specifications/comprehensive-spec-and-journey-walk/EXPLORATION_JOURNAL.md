# Exploration Journal — Comprehensive Spec & Two-Surface Journey Walk

**Change:** CH-CQRWWR (`01KTPWDWJ7CQRWWRGPQEQ22P1M`) · primitive `harden`
**Date:** 2026-06-09
**Mode:** Direct authoring from a settled brief — scope fully decided across a prior design conversation + canonical research. No facilitation interview was run (the brief explicitly instructed: do not re-interview).

## Intent Triage

The brief is a settled specification request for a methodology change to the
Sulis marketplace. Substantive statements classified:

| Statement | Bucket |
|-----------|--------|
| "depth must size only how much context is gathered; the comprehensive doc is ALWAYS produced" | Business intent (SRD) |
| "comprehensive doc always contains use-cases-with-flows + NFR + personas + scope + problem-discovery" | Specification fragment (SRD) |
| "extend the journey walk to a second surface: the API/SDK/MCP tool journey" | Specification fragment (SRD) |
| "derive verifiable scenarios from the use-case flows for both surfaces" | Specification fragment (SRD) |
| "add a UC-flow-coverage gate" | Specification fragment (SRD) |
| "STRIDE threat model section, C4 architecture-at-levels, BDR alongside ADR" | Specification fragment (SRD) |
| File paths in play (`_specify_classifier.py`, `draft-architecture/SKILL.md`, etc.) | Architecture context — recorded for SEA, not designed here |

Outcome: predominantly business intent + specification fragments. Proceeded with
direct SRD authoring. The named files are recorded under Deferred to SEA so the
engineering architect designs the actual edits.

## Context Index

Greenfield-for-this-spec (no `.context/` index for this change). The grounding
came from reading the canonical target (`features/entity-crud/DESIGN.md`), the
product-development studio standards, and the existing Sulis artifacts being
restructured.

## Grounding read (Prior-Art Findings)

| Artifact | What it grounds |
|----------|-----------------|
| `features/entity-crud/DESIGN.md` (platform) | The comprehensive-doc target structure (FR-11). Confirmed: always carries §1–§7 + ADRs + migration/rollback/security/performance. |
| `methodology/studios/.../STANDARDS.md` (platform) | Always-on artifact discipline — every feature MUST produce the design artifact set before the gate. |
| `_specify_classifier.py` | Current backwards behaviour: depth phrase says "three lines" vs "flows drawn out" — depth currently gates doc thinness. This is what FR-03/FR-04 correct. |
| `draft-architecture/SKILL.md` step 8.5 | Existing single-surface (UI) journey walk (#85). Confirmed EXISTS/planned-WP/GAP + the sharper host-rendered bar. FR-08 extends it to the tool surface. |
| `_verify_scenario_coverage.py` | Existing journey-scenario coverage gate. Confirmed it has no UC-flow dimension and no surface dimension — FR-12 adds the flow dimension. |
| `sulis-verify-acceptance` / `_scenario_authoring.py` (#98) | Confirmed `http_call` + `subprocess` drivers + agent-step tiers already drive tool calls. Confirms assumption A-02. |
| `CONTRACT_FIRST_STANDARD.md` (CF-01..CF-12) | Grounds FR-18/FR-19. CF-01/CF-05: contract authored first, producer + consumer build to it in parallel. CF-10: the founder-reviewable dimensions (auth, audience, plain-language guide, error fixes) the contract must carry beyond the schema. CF-03: three error categories. Already the doctrine for cross-kind seams; the amendment makes the contract a first-class section of the always-on document and ties the tool walk to it. |
| `entity-crud/DESIGN.md` §7.9 (Client Data Integration / Endpoint Mapping) | Confirms where the interface contract sits in the canonical Solution Design — operations + request/response types + transforms, inside §7. FR-18 places the contract section at §7.x. |

## Domain Claims

- Depth and doc-existence are currently coupled; decoupling them is the core fix.
- A behavioural change can have two consumer surfaces (human UI, machine tool); both deserve the outside-in proof.
- Every UC flow is a verifiable unit; coverage must be flow-level, not just scenario-existence-level.
- Business decisions are a distinct record type from technical decisions (BDR vs ADR).
- Phase 2 is fundamentally the producer/consumer tool seam; the **interface contract** is the artifact that seam is built around, so it must be a first-class, always-on part of the comprehensive design document — not discovered at integration time. (FR-18, FR-19; grounds in CONTRACT_FIRST_STANDARD CF-01/CF-05/CF-10.)
- The contract (the AGREEMENT) is distinct from the ServiceSpec binding (the WIRING): the spec previously had only the binding (FR-09, the EXISTS bar); the contract artifact itself was missing as a doc section. This amendment closes that gap.

## Disambiguation Decisions (Phase 3.5)

Locked in GLOSSARY.md. Key resolutions:
- **Depth** vs **doc-existence** — explicitly NOT the same; decoupling them is the change.
- **UI surface** vs **tool surface** — same system, two consumers; both walked.
- **Journey walk** vs **verifiable scenario** — walk = design-time classification; scenario = drivable artifact.
- **UC-flow-coverage gate** vs **scenario-required (#103)** vs **journey-coverage (#86)** — three distinct, companion gates.
- **EXISTS (UI)** vs **EXISTS (tool)** — tool EXISTS additionally requires the ServiceSpec binding.
- **ADR** vs **BDR** — technical vs business decision record.

## Adversarial Sweep (Phase 3.6)

The "attackers" are bypasses of the discipline. Six misuse cases authored
(MUC-01..MUC-06): skip-use-cases, false-EXISTS, happy-path-only, silent-flow-drop,
one-surface-walk, fake-green-tool-scenario. Each maps to a negative requirement
(NR-01..NR-06) and a system response in MISUSE_CASES.md. STRIDE-lite run over the
methodology (Spoofing=false-EXISTS, Tampering=silent-flow-drop, Repudiation=no-BDR,
DoS=too-slow-so-skipped, EoP=skip-design-stage). Pre-mortem: cost backlash,
tool-walk theatre, gate fatigue — recorded in MISUSE_CASES.md and HANDOVER risks.

**Amendment (contract-first, 2026-06-09):** Added MUC-07 (contract-as-afterthought)
— a tool surface designed with no reviewable interface contract, or a schema-only
contract integratable-but-not-reviewable (missing the CF-10 founder-facing
dimensions). System response: FR-18 (mandatory contract section with all four
CF-10 dimensions) + FR-19 (contract-first for cross-kind seams; walk operations ⊆
contract) + NR-07/NR-08; the design stage does not complete without it. Added a
4th pre-mortem scenario (hollow contracts — letter without substance; the Lovable
Test / decompose-validation P7 is the substantive bar).

## Verification Answers (Phase 3)

- **How will we know it works?** Drive specify/design/gate on a fixture change; assert the comprehensive document's section set, both journey-walk tables, a scenario per flow, and a covered/gaps verdict that responds correctly to a deliberately uncovered fixture.
- **Kind:** methodology. Verified by driving the stage on a fixture and asserting produced artifacts + gate verdicts.
- **Environments:** local/CI for structure + gate logic; dev tier for a real tool-surface drive.
- **Bootstrap-from-zero:** create a fixture change, run specify at lite from zero intake, assert the full document is produced.
- **Deferred infra:** `tool-drive-sandbox`, `methodology-fixture-change`.

## Deferred to SEA

Architecture/implementation context the engineering architect will design (do not
re-design here):

- `plugins/sulis/skills/specify/SKILL.md` — reword depth proposal; remove doc-thinness gating.
- `plugins/sulis/scripts/_specify_classifier.py` — keep deterministic; depth = gather-effort only; the `_DEPTH_PHRASE`/`_DEPTH_ALT` wording must stop implying doc thinness (FR-04).
- `plugins/sulis/skills/draft-architecture/SKILL.md` — step 8.5 extended to a two-surface walk (UI table + tool table); tool EXISTS requires ServiceSpec binding.
- `plugins/sulis/agents/requirements-analyst.md` — always-comprehensive document regardless of depth path.
- `plugins/sulis/skills/requirements-templates/SKILL.md` — restructure the TDD template toward the comprehensive DESIGN.md shape; add STRIDE, C4-levels, BDR templates.
- `plugins/sulis/scripts/_verify_scenario_coverage.py` — add UC-flow + both-surface coverage dimension (the existing journey-scenario coverage stays).
- `plugins/sulis/skills/scenarios/SKILL.md` — surface the tool-surface scenarios + UC-flow coverage in the read-only report.
- The fixture scripts referenced by the scenarios (`_drive_specify.py`, `_assert_doc_sections.py`, `_verify_uc_flow_coverage.py`, `_assert_interface_contract.py`, `_assert_walk_subset_of_contract.py`, etc.) are SEA-to-create test harness scripts — they are the drivable shape the scenarios assume, to be built as WPs.
- `plugins/sulis/skills/requirements-templates/SKILL.md` / `draft-architecture/SKILL.md` — add the interface-contract / ServiceSpec section to the comprehensive DESIGN.md target structure (§7.x), mandatory for tool-surface changes, carrying the CF-10 dimensions; wire the tool-surface walk to draw operations from it (FR-18, FR-19). Ground in `CONTRACT_FIRST_STANDARD.md` CF-01/CF-05/CF-10 and the platform's `architecture/SERVICE_SPECIFICATION.md` shape.

## Assumption Register

| ID | Assumption | Status | Evidence |
|----|------------|--------|----------|
| A-01 | entity-crud/DESIGN.md is the agreed target shape | active | brief named it; read + confirmed |
| A-02 | #98 substrate already drives tool calls | active (confirmed) | `driver_for_step`, `http_call` in sulis-verify-acceptance |
| A-03 | every behavioural change has UI or tool surface, else exempt | active | #85 exemption path retained |
| A-04 | always-comprehensive doc cost is bounded | active | bounded by NFR-02; degrade detail not existence (NFR-R01) |

## Triage Trace

No founder-facing questions emitted (settled brief, no interview). All decisions
taken from the brief + canonical research. Section structure taken by convention
from the canonical target (CP-01: established internal convention).
