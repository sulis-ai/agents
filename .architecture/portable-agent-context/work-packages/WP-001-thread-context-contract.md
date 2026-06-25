---
id: CH-GJ9KQR-WP-001
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: contract
primitive: expand-create
group: expand
title: Thread/Message/Memory + context-payload contract (schema + errors + stubs)
status: pending
dependsOn: []
implements:
  - "spec:create-portable-agent-context#provider-agnostic-shape"
contract_type: data
fixtures_created:
  - tests/fixtures/thread_context/sample_thread.json
  - tests/fixtures/thread_context/sample_memory.json
verification:
  adapter: contract
  artifact: plugins/sulis/scripts/tests/unit/test_thread_store_contract.py
prov:
  wasGeneratedBy: "engineering-architect:draft-architecture"
  source: "TDD.md§3.3, ADR-001, ADR-002, ADR-005"
estimatedTokenCost:
  input: ~12k
  output: ~6k
---

## Context
TDD §3.3. The thread/message/memory store is a producer↔consumer seam
(CONTRACT_FIRST CF-01, lightweight internal tier). This WP defines the contract
**before** any producer or consumer code — the schema layer, the three error
categories, the read/write operation surface, the payload schema, and stubs
with error + empty cases. Conforms field-for-field to the platform thread-sdk
ONTOLOGY (ADR-001).

## Contract (the deliverable)
- **Types** (ADR-001 shapes, vendor-neutral): `Thread`, `ThreadParticipant`,
  `ThreadMemory`, `ThreadMemoryContent`, `ThreadMessage`,
  `ExplorationJournalEntry`, plus the `ContextPayload` + tier enum
  (lean/standard/full) and the payload pointer (`thread_id` + raw-fetch
  affordance, ADR-005).
- **`ThreadStore` port** — write ops `append_message`, `put_memory`; read ops
  `get_thread`, `get_memory`, `get_messages(since?, limit?)`.
- **Errors** — reuse the three categories from `events.py`
  (Protocol/Expected/Internal); carry `PermissionError` for the future hosted
  binding (not enforced locally — ADR-002).
- **Pinned shared constant (CF-11):** the store root path convention
  `~/.sulis/changes/{change_id}/threads/` and the on-disk record filename
  scheme, pinned here so producer WPs reference it verbatim.
- **Stubs** — an in-memory `ThreadStore` adapter + sample fixtures covering
  happy / empty / error cases (CF-04).

## Definition of Done
**Red** — `test_thread_store_contract.py` written against the port,
**failing** (no adapter yet): asserts the read/write ops, the append-only
reject-rewrite case, the empty-thread case, and the three error categories.
**Green** — types + port + in-memory stub adapter make the contract test pass;
fixtures committed.
**Blue** — the contract types live in one module the producer + consumer + MCP
tool all import (no duplicate type definitions); the in-memory adapter is the
shared contract-test subject the real adapter (WP-002) will also run against.

## Verification
Shape 1 (concrete): `adapter: contract`,
`artifact: .../test_thread_store_contract.py`.

## Acceptance Evidence

- Branch: wp/create-portable-agent-context/wp-001-thread-context-contract (deleted post-merge)
- Completed: `2026-06-24T17:03:47Z` (Step 12 by calling session)
