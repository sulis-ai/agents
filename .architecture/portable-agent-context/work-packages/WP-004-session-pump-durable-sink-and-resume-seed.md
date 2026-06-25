---
id: CH-GJ9KQR-WP-004
change_id: "01KVX26BDXGJ9KQRJ11HACHMZV"
kind: backend
primitive: reinforce-instrument
group: reinforce
title: Session-pump durable-append sink + resume payload-seed
status: pending
dependsOn: [CH-GJ9KQR-WP-002, CH-GJ9KQR-WP-003]
characterisation_test: plugins/sulis/scripts/tests/unit/test_session_event_log.py
implements:
  - "spec:create-portable-agent-context#every-message-tracking"
  - "spec:create-portable-agent-context#resume-from-our-context"
verification:
  adapter: backend
  artifact: plugins/sulis/scripts/tests/integration/test_durable_append_sink.py
prov:
  wasGeneratedBy: "engineering-architect:draft-architecture"
  source: "TDD.md§3.1, ADR-004"
estimatedTokenCost:
  input: ~16k
  output: ~9k
---

## Context
TDD §3.1 + ADR-004. Wire the existing session pump's provider-neutral `Event`
stream into the durable `ThreadStore` as a **second sink** (the in-memory
`EventLog` stays as the live-tail/viewer log — unchanged). On spawn/resume, seed
the (re)spawned agent from the thread's assembled payload via the brief argv
(`SessionSpec.brief_change_id`), **without reading the provider transcript**.
This is **REINFORCE-Instrument** over the existing pump, not a rewrite —
characterisation test required (it touches the live append path).

## Contract
- Each decoded `Event` that carries founder/agent/tool content →
  `ThreadStore.append_message` (mapped onto `ThreadMessage`, reusing the
  existing decode — no second decode path).
- At checkpoint boundaries (Working Set crystallisation moments) →
  regenerate + `put_memory` (version bump), via the WP-003 summary function.
- On spawn/resume → assemble (WP-003) + deliver through the existing brief
  argv seam (ADR-004/005); a restarted PTY reuses the same thread
  (`resumed_from`, ADR-003).

## Definition of Done
**Red** — confirm the existing `test_session_event_log.py` characterisation
still passes (live-tail path unchanged); then `test_durable_append_sink.py`
failing: N messages exchanged → N durable records (order + role + time)
independent of `~/.claude/projects`.
**Green** — additive sink + seed; both the characterisation and new tests pass.
**Blue** — the live-tail path is byte-for-byte unchanged; the durable sink is a
clearly separated side-effect (no new decode); resume seed reuses the brief
seam, adds no new injection mechanism.

## Verification
Shape 1 (concrete): `adapter: backend`,
`artifact: .../test_durable_append_sink.py`.

## Acceptance Evidence

- Branch: wp/create-portable-agent-context/wp-004-session-pump-durable-sink-and-resume-seed (deleted post-merge)
- Completed: `2026-06-24T18:07:17Z` (Step 12 by calling session)
