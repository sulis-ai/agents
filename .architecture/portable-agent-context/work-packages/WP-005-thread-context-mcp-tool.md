---
id: CH-GJ9KQR-WP-005
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: backend
primitive: expand-create
group: expand
title: thread_context MCP discovery tool (read-only, change-scoped, denyable)
status: pending
dependsOn: [CH-GJ9KQR-WP-001]
implements:
  - "spec:create-portable-agent-context#raw-on-demand"
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/unit/test_thread_context_mcp_contract.py
prov:
  wasGeneratedBy: "engineering-architect:draft-architecture"
  source: "ADR-005, TDD.md§3.1"
estimatedTokenCost:
  input: ~11k
  output: ~7k
---

## Context
ADR-005. The raw-on-demand half of the discovery seam: a new `thread_context`
MCP tool, following the `_safe_tools_mcp.py` pattern (one parameterised,
denyable, change-scoped tool over a wrapped library). **EXPAND-Create** — the
public face is the read surface of the WP-001 contract; the store is *called by*
the tool.

## Contract
`thread_context(op, thread_id, since?, limit?) -> dict`, `op ∈ {get_thread,
get_memory, get_messages}` — the contract read ops only (read-only; the agent
never writes). Change-scoped server-side (cannot read another change's thread).
Returns the three-category errors. Registered as a denyable identity.

## Definition of Done
**Red** — `test_thread_context_mcp_contract.py` (mirrors
`test_safe_tools_mcp_contract.py`) failing: ops match the contract read
surface; read-only (no write op exists); a cross-change `thread_id` is refused
(ExpectedError); three error categories serialise correctly.
**Green** — wrap the WP-001 read ops; conformance test passes.
**Blue** — one parameterised tool (not three identities); shares the contract
read schema with the store (no duplicate op definitions).

## Verification
Shape 1 (concrete): `adapter: backend`,
`artifact: .../test_thread_context_mcp_contract.py`.

## Acceptance Evidence

- Branch: wp/create-portable-agent-context/wp-005-thread-context-mcp-tool (deleted post-merge)
- Completed: `2026-06-24T17:46:18Z` (Step 12 by calling session)
