---
id: CH-GJ9KQR-WP-006
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: frontend
primitive: substitute-strangle
group: substitute
title: Cockpit raw-view reads the Sulis store (strangle transcript-file read)
status: pending
dependsOn: [CH-GJ9KQR-WP-002, CH-GJ9KQR-WP-004]
removal_plan:
  target: "After the durable store is proven across a full thread lifecycle; remove locateTranscripts from the raw-read path. Target: follow-on change once provider-independent resume has run green in production. Tracked, not scheduled in this change."
implements:
  - "spec:create-portable-agent-context#every-message-tracking"
verification:
  adapter: frontend
  artifact: apps/cockpit/client/src/api/useTranscript.test.ts
prov:
  wasGeneratedBy: "engineering-architect:draft-architecture"
  source: "RECON.md (useTranscript/locateTranscripts), ADR-002"
estimatedTokenCost:
  input: ~12k
  output: ~8k
---

## Context
RECON + TDD §3.1. Today the cockpit raw view (`useTranscript` →
`/api/changes/:id/transcript` → `locateTranscripts` → Claude's
`~/.claude/projects` JSONL) is **provider-locked**. Re-point the raw read at the
durable `ThreadStore` (`get_messages`) so the cockpit reads **our** store, not
the provider's transcript. **SUBSTITUTE-Strangle** — the transcript-file read
is gradually replaced; `removal_plan` records the deletion milestone (a
Strangle without a recorded removal is wrapper rot — this WP records one).

This WP is **optional for the change's core acceptance** (the agent's
discovery seam is WP-005); it closes the cockpit-UI lock-in. If sequencing
pressure, it can land in the follow-on per the removal plan.

## Contract
The `/transcript` route's data source moves from `locateTranscripts` to the
`ThreadStore.get_messages` read op (same `TranscriptMessage[]` wire shape — the
store's `ThreadMessage` maps to it). Behaviour-preserving for the UI.

## Definition of Done
**Red** — `useTranscript.test.ts` driving the store-backed read path, failing.
**Green** — route reads the store; the rich view (`groupTurns`) and raw view
render from our records.
**Blue** — `locateTranscripts` stays only on the Claude-resume convenience
path (per spec non-goal: don't rip out Claude resume), with the removal-plan
note for the raw-read path.

## Verification
Shape 1 (concrete): `adapter: frontend`, `artifact: .../useTranscript.test.ts`.

## Acceptance Evidence

- Branch: wp/create-portable-agent-context/wp-006-cockpit-raw-view-repoint (deleted post-merge)
- Completed: `2026-06-24T18:50:48Z` (Step 12 by calling session)
