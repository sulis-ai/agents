---
id: WP-CLINICS
title: Clinics-scheme submission flow (interaction contract)
kind: contract
contract_type: interaction
status: in_progress
# ── Exercise evidence (ADR-001) ──────────────────────────────────────────
# Empty at authoring time: the flow has NOT yet been exercised end-to-end
# over stub adapters, so the interaction-flow done-gate (CH-01KT9H) MUST
# refuse `flip-status --to done` until these three fields are recorded.
# The spike test (test_interaction_gate_clinics_spike.py) drives the live
# gate through block -> exercise-over-stubs -> release; it copies this card
# into a hermetic temp workspace and records evidence there, leaving this
# committed copy at empty-evidence so the block leg stays demonstrable.
exercised_at:
exercised_by:
exercised_attestation:
---

# WP-CLINICS — Clinics-scheme submission flow (interaction contract)

The real founder-facing interaction flow this change exists to gate. It is a
`contract_type: interaction` work package: a multi-step flow whose done-gate is
the exercised-flow predicate (`interaction_flow_exercised`), sibling to the
visual-contract gate. Phase 1 records this at SHOULD strength; the spike below
proves the live gate end-to-end over stubs.

## The flow (the steps the founder actually walks)

A clinic submission is worked end-to-end through the Capsule operator connector.
Each step is a distinct founder action; the whole sequence is what "exercised
end-to-end" means for this contract:

1. **process-documents** — ingest the incoming clinic submission documents.
2. **find-business** — locate candidate businesses for the submission.
3. **look-up-business** — pull the matched business's full record.
4. **score-risk** — compute the RAG risk score for the submission.
5. **rate-quote** — rate the quote against the scored risk.
6. **push-indication** — push the reviewed indication to HubSpot.
   (Operator-confirmed, never automatic.)

## Done-gate

This card cannot reach `done` until its flow has been exercised end-to-end over
**stub adapters** — evidenced `agent-observed` (an agent ran the flow over stubs
and recorded the transcript) or `human-attested` (a person ran it and attested,
with who + when). Recorded in the three ADR-001 evidence fields above. No live
Capsule / HubSpot / platform write occurs during exercise — the spike runs the
flow against the PATH-shim stub harness at `../stubs/clinics` (mirroring the
`gh-stubs` precedent).

## Exercise harness

`.architecture/interaction-flow-gate/spike/stubs/clinics` — a PATH-shim that
returns canned responses for each of the six steps and logs every invocation,
so the exercise run is deterministic, offline, and falsifiable (the invocation
log is the `agent-observed` attestation).
