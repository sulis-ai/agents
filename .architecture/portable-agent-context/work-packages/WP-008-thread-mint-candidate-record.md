---
id: CH-GJ9KQR-WP-008
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: docs
primitive: expand-create
group: expand
title: Capture the brain Thread entity as a mint CANDIDATE (do not mint)
status: pending
dependsOn: [CH-GJ9KQR-WP-001]
verification:
  na: true
  justification: "Docs-only — records a mint-candidate descriptor under .sulis-mint-requests/; no runtime behaviour, no test surface. The governed mint runs as a separate later step (ADR-003)."
prov:
  wasGeneratedBy: "engineering-architect:draft-architecture"
  source: "ADR-003"
estimatedTokenCost:
  input: ~6k
  output: ~3k
---

## Context
ADR-003. The brain Thread entity is captured as a **mint CANDIDATE now**,
governed-minted **later** (after this design settles the log schema AND the
failover consumer is real — do not mint ahead of use). This WP writes the
candidate descriptor only.

## Definition of Done
**Red/Green** (docs): a mint-candidate record under `.sulis-mint-requests/`
describing Thread as a sparse Activity-class entity (peer of lifecyclerun /
testrun), fields mirroring/referencing the platform Thread (ADR-001), provider
modelled via the existing `Tool` entity, `resumed_from` self-ref, and the
message-log **runtime-store reference** (never one node per message).
**Blue** — the candidate explicitly states it is NOT to be minted until the
two preconditions hold; cross-links ADR-003 and the WP-001 contract.

## Verification
Shape 3 (trivial carveout): `na: true` — docs-only, no runtime surface.

## Acceptance Evidence

- Branch: wp/create-portable-agent-context/wp-008-thread-mint-candidate-record (deleted post-merge)
- Completed: `2026-06-24T18:07:17Z` (Step 12 by calling session)
