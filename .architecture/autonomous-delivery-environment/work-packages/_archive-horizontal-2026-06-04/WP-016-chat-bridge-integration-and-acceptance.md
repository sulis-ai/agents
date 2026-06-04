---
id: WP-016
title: "Integration: chat bridge end-to-end (mock→real) + a11y/visual sweep + from-graph acceptance"
kind: composite
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: integration

atomic_branch: yes
estimate: 6h
blast_radius: medium
primitive: REINFORCE-Test
group: reinforce
acceptance_criteria:
  - "CF-07 conformance: the relay (WP-009) is swapped from RecordedSessionBridge to the real StreamJsonSessionBridge (WP-010) and the live chat path is exercised end-to-end on the founder machine (real resume + real spawn + mid-step) — the path CI cannot bootstrap"
  - "The six emitted verification scenarios run from the brain graph (sulis-verify-acceptance --scenario <id>) and pass: board / status / chat / search / previews / brain"
  - "axe-core a11y passes on every new surface in both light and dark; the built surface matches the SIGNED visual contract (WP-002) — token consumption, no raw hex"
  - "Full read-only gate green WITH the chat path live: exactly one module starts a process; reads start none (FR-N1, NFR-SEC-05)"
test_plan:
  unit: []
  integration:
    - "manual (founder machine): real claude resume + spawn + mid-step via StreamJsonSessionBridge through POST /api/changes/:id/chat"
    - "sulis-verify-acceptance --scenario for all six scenario ids (from-graph)"
    - "apps/cockpit/e2e/*.spec.ts (EXTEND) — axe-core sweep across board + thread + chat + brain + previews + search, light + dark"
  verification:
    - "all six from-graph scenarios pass"
    - "bash apps/cockpit/scripts/check-read-only.sh exits 0 with the chat path present"
    - "branch-ci green"
verification_gates: [composite]
verification:
  adapter: backend
  deferred-to-follow-on: recording-bridge-claude-session
  # this WP IS the resolution of the deferred live path: mock→real swap + manual founder-machine run.

derived_from:
  - finding: "WP-08.5 integration child (CF-07); TDD §4 Proof + §9 verification plan; SPEC 'How we'll know it's done' (six from-graph scenarios)"
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-009, WP-010, WP-011, WP-012, WP-013, WP-014, WP-015]

child_wps: []
kinds: null

infrastructure_needs:
  - id: recording-bridge-claude-session
    why: "CI conformance runs against the recorded fixture; the real live path is the manual founder-machine swap this WP performs"

verifies_scenario:
  - "dna:scenario:Y6Z1EJPF6GY1BAQ96WGA86TDHS"   # See everything in flight at a glance (board)
  - "dna:scenario:1PB20WWQY89W9GTE9HKS45YP06"   # Understand where a change is (status)
  - "dna:scenario:YY4RJ7JS8KT55BS61BD0ER3ZNF"   # Talk to the agent about a change (chat)
  - "dna:scenario:CP3MAX93563W45W7D547T5FJ80"   # Find a change (search)
  - "dna:scenario:00VX23T9WP4T6W7XXN39FMT6YH"   # Read a document rendered (previews)
  - "dna:scenario:65JX0VABSE53NJJCVP8NQRTMXH"   # See what the agent has created (brain)

rollback: |
  Verification + integration WP — no new product code beyond the mock→real
  wiring selection (already in WP-010's index.ts). If the live path fails,
  the relay can fall back to the recorded fixture in non-prod; revert the
  index.ts selection. The six scenarios + the read-only gate stay as the
  acceptance record.
---

# Integration: chat bridge end-to-end (mock→real) + a11y/visual sweep + from-graph acceptance

## Why

The contract-first integration child (WP-08.5 / CF-07): swap the recorded bridge
for the real `StreamJsonSessionBridge` and prove the **live** chat path that CI
cannot bootstrap — real resume, real spawn, mid-step re-run — on the founder
machine. It also runs the six emitted verification scenarios **straight from the
brain graph**, which is the SPEC's "how we'll know it's done", and sweeps a11y +
the signed visual contract across every new surface in both themes.

This is the last WP: it depends on the relay, the prod adapter, and all five
surfaces.

## What this does

1. **mock→real swap (CF-07).** Wire `StreamJsonSessionBridge` (WP-010) into the relay (WP-009) in production and run the live path end-to-end on the founder machine across the four cases (live / resume / spawn / mid-step).
2. **from-graph acceptance.** `sulis-verify-acceptance --scenario <id>` for all six scenarios — no hand-built test bundle (the testable-state loop this change road-tests).
3. **a11y + visual sweep.** axe-core across board, thread, chat, brain, previews, search in light + dark; confirm token consumption against the signed visual contract (WP-002).
4. **read-only gate with chat live.** Confirm the gate stays green with the one sanctioned write path present — exactly one process-start site; reads start none.

## Scenario linkage (from-graph verification)

| Scenario id | Plain English | Verified-by surface WP |
|---|---|---|
| Y6Z1EJPF6GY1BAQ96WGA86TDHS | See everything in flight at a glance | WP-011 |
| 1PB20WWQY89W9GTE9HKS45YP06 | Understand where a change is | WP-012 / WP-003 |
| YY4RJ7JS8KT55BS61BD0ER3ZNF | Talk to the agent about a change | WP-015 / WP-009 |
| CP3MAX93563W45W7D547T5FJ80 | Find a change | WP-014 / WP-005 |
| 00VX23T9WP4T6W7XXN39FMT6YH | Read a document rendered | WP-013 |
| 65JX0VABSE53NJJCVP8NQRTMXH | See what the agent has created | WP-013 / WP-004 |

## Rollback

No new product code beyond the index.ts adapter selection (in WP-010). Revert
that selection to fall back to the recorded fixture in non-prod. The six
scenarios + the read-only gate are the acceptance record.
