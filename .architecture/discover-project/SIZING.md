# SIZING — discover-project

**Generated:** 2026-06-01
**Source SRD:** ../../.specifications/discover-project/SRD.md
**Source SRD mtime:** 2026-06-01 (committed today)
**Computed by:** `/sulis:draft-architecture .specifications/discover-project/` (autonomous SEA dispatch)

## Inputs

### sFPC (simplified Function Point Count)

| Category | Count | Items |
|---|---|---|
| **ILF** (domain-entity + data-store) | 5 | New canonical entity-instance files at `plugins/sulis/instances/discover-project/` — workflow.jsonld, steps.jsonld, triggers.jsonld, failuremodes.jsonld, tools.jsonld. Project entity already exists (foundation primitive, consumed). |
| **EIF** (integration) | 4 | git CLI (`git remote get-url`, `git rev-parse`); local filesystem (manifests, CI workflows, repo-contract); LLM provider (Infer phase); drift detector (existing tool from release-train, invoked from Verify phase) |
| **EI/EO/EQ** | 6 | UC-001 first-time setup (EI — writes Project entity); UC-002 re-discovery diff (EI — selectively writes); UC-003 monorepo scoped mint (EI); UC-004 non-git error path (EQ — read+exit); UC-005 cancellation cleanup (EI — atomic rollback); UC-006 LLM override (EI — records override before mint) |
| **Total** | **15** | |

### ASR (Architecturally Significant Requirements)

| Category | Count |
|---|---|
| NFRs | 6 (NFR-001 wall-time, NFR-002 token budget, NFR-003 deterministic re-run, NFR-004 path safety, NFR-005 drift visibility, NFR-006 graceful degradation under no LLM) |
| Integrations | 4 (git, filesystem, LLM, drift detector) |
| MUCs | 8 (MUC-001..MUC-008 — all have System Response REQUIRED fields) |
| Cross-cutting policies | 3 (path safety NFR-004 + atomic write semantics; ULID canonicalisation per P8 rubric; consumer-tenant-as-cross-tenant-boundary at the drift detector) |
| **Total** | **21** | |

### Tier table

| Tier | sFPC range | ASR range | This change |
|---|---|---|---|
| S | ≤10 | ≤5 | — |
| M | 11-30 | 6-15 | sFPC=15 → M |
| L | 31-80 | 16-40 | ASR=21 → L |
| XL | 80+ | 40+ | — |

**Take the higher tier when they disagree.** sFPC=15 → M; ASR=21 → L. **Tier = L** (driven by ASR — discovery has many integration/safety/MUC concerns relative to its modest feature-point count).

Smaller than release-train-as-entities (sFPC=17, ASR=30, L) by a meaningful margin: discover-project has fewer canonical entities (5 vs 6 — no `projects.jsonld` to author here), fewer NFRs (6 vs 10), fewer FailureModes (8 vs 11 MUCs). Same tier classification, lower end of the band.

### Pillar coverage

| Pillar | Status | Reasoning |
|---|---|---|
| Form | PARTIAL | Path A pattern + canonical-entity-instance shape inherited from `release-train-as-entities`. Reference, don't restate. New Form content: phase shape (5 deterministic-probabilistic-deterministic phases), the slug/tenant derivation port, and the consumer-vs-marketplace ownership boundary. |
| Armor | PARTIAL | Brain ships FailureMode + recovery_strategy dispatch; drift detector + token budget enforcement already exist (from release-train). New Armor content: atomic write semantics for the Mint step (write-to-tmp-then-rename), LLM-unavailable degradation path (NFR-006), the consumer-tenant cross-boundary check at the drift detector. |
| Proof | PARTIAL | Drift-detector test discipline established by `release-train-as-entities` test parity. New Proof content: 4 fixture consuming repos (empty, populated, monorepo, pre-existing-Project); LLM mock pattern for Infer phase tests; idempotent-cancellation test pattern. |

## Tier verdict

**Tier: L** (computed; not overridden)

## Targets

- **TDD length:** ≤ 400 lines (Form/Armor/Proof all PARTIAL — substantial reference to release-train; new content focused)
- **ADRs:** 6 expected (5 explicitly named in the dispatch + 1 for the consumer-vs-marketplace tenant boundary semantics if it doesn't fold into ADR-002)
- **Expected WPs (post-decompose):** 8-10 (smaller than release-train's 11; discovery has one less entity file and reuses existing tools more aggressively)

## Decisions

- **No founder-facing visual surface.** The skill is a CLI/agent skill; no UI. UX_VISUAL_DESIGN_STANDARD does not apply.
- **No new ServiceSpec.** The discovery skill is a local skill invocation, not a service. Tools it uses (entity-emitter, drift-detector) already have schemas in their parent contexts. New Tools (git-read, tenant-derivation if elevated) get JSON Schemas in `plugins/sulis/instances/discover-project/schemas/tools/`.
- **Path A continuity.** Same canonical-as-spec pattern. Drift detector validates the skill conforms to `workflow.jsonld` + `steps.jsonld`. Annotation format inherited unchanged (ADR-002 of release-train-as-entities).
- **Reuse over re-author.** Entity-emitter from feedback-log task #58 is the load-bearing reuse. Drift detector from `7d666df extend: tighten-drift-gate` is invoked, not re-implemented. Read tool from the agent harness is wrapped only if a typed schema is required.

## Computed by

`/sulis:draft-architecture .specifications/discover-project/` (autonomous SEA dispatch, 2026-06-01).

This file is the source of truth for sizing decisions. Subsequent skills (`/sulis:plan-work`, `/sulis:verify-architecture`) read it rather than recomputing.
