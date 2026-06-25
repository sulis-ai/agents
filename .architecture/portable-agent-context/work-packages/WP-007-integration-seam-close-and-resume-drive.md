---
id: CH-GJ9KQR-WP-007
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: composite
primitive: expand-create
group: expand
title: Integration — swap mock→real, conformance check, provider-independent-resume drive
status: pending
dependsOn: [CH-GJ9KQR-WP-002, CH-GJ9KQR-WP-003, CH-GJ9KQR-WP-004, CH-GJ9KQR-WP-005]
composite_of: [CH-GJ9KQR-WP-002, CH-GJ9KQR-WP-003, CH-GJ9KQR-WP-004, CH-GJ9KQR-WP-005]
implements:
  - "spec:create-portable-agent-context#resume-from-our-context"
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/integration/test_provider_independent_resume.py
prov:
  wasGeneratedBy: "engineering-architect:draft-architecture"
  source: "TDD.md§5, CONTRACT_FIRST CF-07/CF-12"
estimatedTokenCost:
  input: ~14k
  output: ~8k
---

## Context
TDD §5 + CONTRACT_FIRST CF-07/CF-12. The seam-close WP: swap the in-memory stub
for the real `ThreadStore` adapter everywhere, run the conformance check, and
drive the **load-bearing journey** — provider-independent resume — over the
real saved record (CF-12: real-data acceptance at seam-close, not deferred to
ship).

## Definition of Done
**Red** — `test_provider_independent_resume.py` failing: run a thread, capture
decisions, end it, **make the provider transcript unavailable**
(delete/rename the `~/.claude/projects` JSONL), resume → assert the agent comes
back with the rich payload (brief + Working Set + relevant entities + summary)
and the raw log is intact and correctly ordered from **our** store.
**Green** — all producer/consumer WPs wired to the real adapter; the resume
drive and the MCP-tool conformance pass; budget + vendor-neutral assertions hold
end-to-end.
**Blue** — confirm no remaining mock on any integration path (MEA-09); the
in-memory adapter is used only as the shared contract-test subject; the
seam-close gate reads the covering Scenario verdict.

## Verification
Shape 1 (concrete): `adapter: backend`,
`artifact: .../test_provider_independent_resume.py`. Seam-close (CF-12) over the
change's provider-independent-resume Scenario.

> Note from WP-005 security review (ADVISORY ADV-1, fold in here): the
> thread_context MCP tool is built + denyable but NOT yet wired live. This
> integration WP MUST add (a) the `sulis-thread-context` server to
> `plugins/sulis/.mcp.json` + its launcher entry (mirror `sulis-safe-tools`),
> and (b) the matching permission entry (`mcp__sulis-thread-context__*`) in
> settings so the founder's allow/deny surface actually covers it. Until then
> the read-only raw-discovery tool isn't deployed.

> Notes from WP-004 security review (fold into the integration wiring):
> - ADV-1: call `checkpoint()` OFF the live event hot path (at Working Set
>   crystallisation boundaries), never inside the on_event observer fan-out —
>   a checkpoint error must not stall the live pump.
> - ADV-2 (real functional gap): on resume, reseed the sink's `_next_order`
>   from the store high-water mark (`get_messages(...)[-1].order + 1`).
>   A fresh sink defaults `_next_order=0`; over a non-empty thread that makes
>   EVERY append fail OUT_OF_ORDER_WRITE (silently counted as degraded_appends).
>   The resume drive MUST cover this (append after resume lands at the right order).

## Acceptance Evidence

- Branch: wp/create-portable-agent-context/wp-007-integration-seam-close-and-resume-drive (deleted post-merge)
- Completed: `2026-06-24T18:50:48Z` (Step 12 by calling session)

## Post-merge correction (CH-GJ9KQR remediation, 2026-06-24)

> A `/sulis:prove` consumer-level reality check found that this WP's drive
> (`test_provider_independent_resume.py`) exercises the assembler **directly** —
> it constructs `DurableAppendSink` / `ContextPayloadAssembler` and calls
> `seed_payload_for_resume` itself, never going through `SessionManager`. It
> proved the **component**, not the **live path**. The headline capability
> ("Resume recovers rich context from OUR store") is built as components but
> NOT connected into the live system: `seed_payload_for_resume` and
> `ContextPayloadAssembler` are referenced ONLY in tests; the live
> `manager._respawn` / `_attach_durable_sink` only reseed the order counter and
> never assemble or inject the payload.
>
> This WP's test is retained as a valid **component-level contract test**. The
> **live-path acceptance** for the headline capability moves to **WP-009**
> (live assemble→inject resume wiring with real Working Set + brain readers),
> whose Red MUST drive the real `SessionManager` spawn/resume path and observe
> the rich payload reaching the brief with REAL Working Set + brain content.
> **WP-010** closes the related OpenAI-key redaction blind spot on the
> store-write surface.
