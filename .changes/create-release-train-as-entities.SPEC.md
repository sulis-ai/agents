---
founder_facing: false
---

# Spec — Encode release-train as canonical entities

**Change:** CH-01KSZ4 · `change/create-release-train-as-entities` · primitive: create
**Execution path:** Path A — canonical-as-spec, imperative-as-implementation, drift-detector as the bridge

## Intent

Encode the marketplace's release pipeline (today: imperative
`release-on-merge.yml` + skill prose in `/sulis:release-train`) as
canonical **Workflow + Step + Trigger + FailureMode + Project + Tool**
entities in the brain. Path A: the canonical is the **specification of
truth**; `release-on-merge.yml` is the **implementation that conforms**;
a **drift detector** is the structural bridge.

One outcome: *deterministic, cost-effective, reliable execution of
release workflows.* Definition declarative + queryable + gap-checkable.
Imperative path stays zero-token; dry-run preview is token-budgeted.

Per L26/L27, the deliverable is not a custom skill or runtime — it's a
canonical Workflow instance + the drift detector + a small skill
extension for the dry-run mode.

## Acceptance (summary)

- Project + Workflow + Step + Tool + Trigger + FailureMode instances
  authored at `plugins/sulis/instances/release-train/`
- Drift detector (FR-015) runs in `branch-ci.yml`; catches deliberate
  divergence in a test fixture
- `/sulis:release-train --dry-run` walks the canonical via
  `/sulis-brain:execute-workflow` within the NFR-001 token budget
- Today's three latent defects (CH-01KSYZ YAML parse, CH-01KSZ1
  loop-guard, GH-token tag trigger) represented as named FailureModes
- Configuration Vocabulary section in the SRD complete +
  cross-referenced from marketplace plugin README
- "Future: discovery sibling" section names the deferred work

## Depends on

- **sulis-brain v0.9.0+** (foundation v0.6.0): Project entity (DR-016),
  Workflow.for_project (DR-017), Tool.implementation_kind=workflow_dispatch
  (DR-018), LifecycleRun v2.1.0 (DR-013), DerivedArtifact (DR-019),
  execute-workflow agent (DR-015), sync-narrative-docs as structural
  template (DR-020)

## Out of scope (explicit)

- ae_task_executor's coercive prompt style ("EXECUTE THIS NOW")
- `marketplace-release` Workflow with `workflow_dispatch` composition
  (deferred to v2; requires Path C deterministic runner)
- LifecycleRun emission at imperative-Step boundaries (deferred to v2)
- Cross-tenant Tool catalogue lifting (revisit at n=2)
- Autonomous-mode runtime (platform LangGraph; separate work)
- `project-discovery` Workflow (sibling change; deferred until n=2 or
  env-init sibling lands)

## Full SRD

See `.specifications/release-train-as-entities/SRD.md` for:

- 6 Use Cases (UC-001..UC-006)
- 16 Functional Requirements (8 active + 4 deferred + new FR-015
  drift-detector + FR-016 Configuration Vocabulary)
- 10 Non-Functional Requirements (token cost, determinism, cycle
  tolerance, replay, failure isolation, observability, branch-policy
  portability, Tool reuse, audit artifacts, probabilistic-step budget)
- 11 Misuse Cases (MUC-001..MUC-011, including new MUC-009 silent
  drift, MUC-010 fork-consumer Project authoring, MUC-011 abstracting
  on n=1)
- **Configuration Vocabulary section** — authoritative list of every
  Project field + state_contract variable for fork-consumer reference
- **Future: discovery sibling** — `project-discovery` Workflow sketch
- Glossary
- 5 Open Questions (drift annotation format, Tool minting fidelity,
  token-cost baseline, DerivedArtifact adoption, composition cycle docs)

## Next stage

Design pass — `/sulis:draft-architecture` against this SPEC will
produce:

- TDD.md (structural design)
- ADRs:
  - drift-detector annotation format (sidecar vs inline)
  - Tool minting fidelity strategy
  - dry-run skill extension shape
  - state_contract vs Project field placement
- Work Package decomposition
- Mermaid diagrams (release-train-flow, drift-detector-flow,
  failuremode-recovery)
- ServiceSpec manifests (per CONTRACT_FIRST_STANDARD CF-10)
