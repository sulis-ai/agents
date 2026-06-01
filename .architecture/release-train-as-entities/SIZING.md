# SIZING — release-train-as-entities

**Generated:** 2026-06-01
**Source SRD:** ../../.specifications/release-train-as-entities/SRD.md
**Source SRD mtime:** 2026-06-01 (committed today)

## Inputs

### sFPC (simplified Function Point Count)

| Category | Count | Items |
|---|---|---|
| **ILF** (domain-entity + data-store) | 6 | The 6 canonical entity-instance files at `plugins/sulis/instances/release-train/` — workflow.jsonld, steps.jsonld, triggers.jsonld, failuremodes.jsonld, projects.jsonld, tools.jsonld |
| **EIF** (integration) | 5 | brain executor (execute-workflow agent); brain entity store; release-on-merge.yml workflow; gh CLI; git CLI |
| **EI/EO/EQ** | 6 | UC-001 dry-run preview (EQ); UC-002 imperative ship (EI); UC-003 gap analysis (EQ); UC-004 fork-and-adapt (EQ — read-only); UC-005 new FailureMode mint (EI — write); UC-006 drift catch (EQ) |
| **Total** | **17** | |

### ASR (Architecturally Significant Requirements)

| Category | Count |
|---|---|
| NFRs | 10 |
| Integrations | 5 |
| MUCs | 11 |
| Cross-cutting policies | 4 (L13, L22, L26-27, L30) |
| **Total** | **30** |

### Pillar coverage

| Pillar | Status | Notes |
|---|---|---|
| Form | PARTIAL | Structural template (sync-narrative-docs) covers the shape; we add the drift-detector module + the dry-run skill extension |
| Armor | PARTIAL | Brain has FailureMode + execute-workflow's recovery_strategy dispatch; drift detector + token budget + Tool-existence check are new |
| Proof | UNCOVERED | New — drift-detector test discipline (canonical-vs-YAML fixtures); no prior pattern in this repo |

## Tier

**Tier: L** (taking the higher of sFPC-tier [M] and ASR-tier [L]).

## Targets

- TDD length: ≤ 400 lines (per Form/Armor PARTIAL — SRD did most of the heavy lifting)
- ADRs: 4 (Path A choice; annotation format; Tool minting fidelity; Project-instance authoring strategy)
- WPs (post-decompose): expect 8-12

## Decisions

- **No founder-facing surface.** SPEC.md frontmatter `founder_facing: false`. Visual contract NOT required (per UX_VISUAL_DESIGN_STANDARD's user-facing scope).
- **No new ServiceSpec.** The drift detector is a local Python script, not a service. The release-train Workflow's "contract" is the entity schemas (brain-owned).
- **Hand-authored Project + Tool instances.** L13 — n=1; no abstraction beyond what sulis-plugins needs.

## Computed by

`/sulis:draft-architecture .specifications/release-train-as-entities` (2026-06-01)
