---
id: CH-GJ9KQR-WP-003
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: backend
primitive: expand-create
group: expand
title: ContextPayloadAssembler — tiered, vendor-neutral, budget-enforcing
status: pending
dependsOn: [CH-GJ9KQR-WP-001]
implements:
  - "spec:create-portable-agent-context#payload-fits-budget"
  - "spec:create-portable-agent-context#provider-agnostic-shape"
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_context_payload_assembler.py
prov:
  wasGeneratedBy: "engineering-architect:draft-architecture"
  source: "TDD.md§3.2, ADR-003"
estimatedTokenCost:
  input: ~13k
  output: ~9k
---

## Context
TDD §3.2 + ADR-003. The assembler is a **GENERATED ARTIFACT** — a pure
query/render component, no persistence of its own. It builds the rich
`ContextPayload` from the brief + Working Set + relevant brain entities + a
structured summary derived from the thread's message log (read via the
`ThreadStore` read ops). Relevance starts simple: the bound change's entities +
recency (spec non-goal: semantic retrieval).

## Contract
`assemble(thread_id, tier) -> ContextPayload` (WP-001 types). Tiers
lean/standard/full enforce a **hard token budget**; standard ships the
structured summary (ThreadMemory.exploration_journal + messages summary), never
the raw dump. The payload is vendor-neutral (no Claude-JSONL structure) and
carries the discovery pointer (ADR-005).

## Definition of Done
**Red** — `test_context_payload_assembler.py` failing: asserts each tier stays
within budget; standard tier carries the summary not the raw dump; payload
contains no Claude-JSONL-specific keys; the pointer is present.
**Green** — boring assembly from the named sources; tests pass.
**Blue** — depends inward only on the read ops + Working Set reader + brain
reader; no IO of its own; the summary generation is a separable function
(reused at checkpoint regeneration, WP-004).

## Verification
Shape 1 (concrete): `adapter: backend`,
`artifact: .../test_context_payload_assembler.py`.

## Acceptance Evidence

- Branch: wp/create-portable-agent-context/wp-003-context-payload-assembler (deleted post-merge)
- Completed: `2026-06-24T17:46:17Z` (Step 12 by calling session)
