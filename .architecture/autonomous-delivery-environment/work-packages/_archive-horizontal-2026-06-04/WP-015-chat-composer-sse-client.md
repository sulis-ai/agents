---
id: WP-015
title: "Two-way chat: composer + SSE stream client (the write/act surface)"
kind: frontend
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: surfaces

atomic_branch: yes
estimate: 9h
blast_radius: high        # the only client surface that acts on a session
primitive: EXPAND-Create
group: expand
visual_contract: WP-002
acceptance_criteria:
  - "The docked composer sends a message to the open change via POST /api/changes/:id/chat and renders the streamed reply live (FR-16/17); on complete it joins the conversation (FR-18)"
  - "Composer reflects session lifecycle states in plain English (FR-23): ready / agent-replying / waking-the-change-up (resuming|spawning) / couldn't-start"
  - "While a reply streams for THIS change, the send control is disabled/refused (FR-20); a mid-stream break shows 'reply was interrupted' and preserves the partial (FR-22)"
  - "An unreachable session shows a clear plain-English failure and does NOT show the message as delivered (FR-19, FR-N3)"
  - "On resume, an HONEST 'this change was resumed' indication is shown (NOT 'silently continued'); an incomplete step is shown as re-run, never as done (FR-26, FR-N5)"
  - "Acts ONLY on the open change's session (the request names this change); every other client surface stays read-only (FR-N1); consumes tokens.css only; matches the SIGNED visual contract (WP-002)"
test_plan:
  unit: []
  integration:
    - "apps/cockpit/client/src/tests/Composer.test.tsx (NEW) — states ready/replying/resuming/spawning/could-not-start (FR-23); send disabled mid-stream (FR-20); partial+interrupted on break (FR-22); unreachable failure not-delivered (FR-19); honest 'resumed' note (FR-26)"
    - "apps/cockpit/client/src/tests/useChatStream.test.tsx (NEW) — SSE event handling: state→chunk*→complete; error events map to the right plain-English state"
  verification:
    - "axe-core a11y on the chat dock + consent gate green"
    - "branch-ci green"
verification_gates: [unit, component, visual_diff, a11y, perf_budget]
verification:
  adapter: frontend
  artifact: "apps/cockpit/client/src/tests/Composer.test.tsx"

derived_from:
  - finding: "TDD §5 row 6 + §3.5; ADR-001 SSE client + ADR-005 docked chat; FR-16..23/26, FR-N1/N3/N5"
    found_in: .architecture/autonomous-delivery-environment/TDD.md
    severity_at_discovery: n/a
generated_by:
  activity: plan-work-run/2026-06-03T08:34:19Z
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by: { activity: null, result: null }

status: pending
depends_on: [WP-001, WP-002, WP-009, WP-012]   # relay endpoint (SSE contract) + thread shell to dock into

child_wps: []
kinds: null

# NFR-SEC constraints carried on the sensitive write/act path (client side):
security_constraints:
  - "The composer acts only on the open change — the POST names this change's id; it cannot target another (NFR-SEC-06 mirrored client-side; the server binding guard, WP-008, is the authority)"
  - "No other client surface gains a write; the client fetch-funnel inventory test still passes (FR-N1)"
  - "Resume/spawn surfaced honestly to the founder; never a fabricated completion (FR-26/FR-N5)"

verifies_scenario: "dna:scenario:YY4RJ7JS8KT55BS61BD0ER3ZNF"   # Talk to the agent about a change

rollback: |
  New Composer + useChatStream + consent-gate components, docked in the thread.
  Remove the dock + the POST funnel exception; the thread reverts to the
  read-only transcript Chat. Revert the commit. No read surface affected.
---

# Two-way chat: composer + SSE stream client (the write/act surface)

## Why

The headline surface and the only client that *acts on* a session (FR-16..26).
"It just works": the founder types and sends; the server resumes or spawns; the
reply streams back live. The client's job is to (a) send to the open change only,
(b) render lifecycle states honestly (FR-23), (c) enforce one-in-flight UX
(FR-20), (d) preserve partials on break (FR-22), (e) never show a message as
delivered when it wasn't (FR-19/FR-N3), and (f) surface resume + incomplete-step
honestly (FR-26/FR-N5). Per ADR-005 the composer is a persistent dock in the
thread — "driving is one glance from reading".

## What changes

- `apps/cockpit/client/src/components/Composer.tsx` (NEW, EXPAND-Create) — the docked composer: suggestion chips + free text + slash-command affordance; send button (the single filled accent); lifecycle state read-out; the consent gate for consequential downstream actions (AI-03, from the visual contract).
- `apps/cockpit/client/src/api/useChatStream.ts` (NEW) — opens the SSE stream to `POST /api/changes/:id/chat`; maps `ChatStreamEvent`s to live message + state; on drop, preserves partial + marks interrupted.
- ThreadView (WP-012) docks the Composer beneath the conversation; the read-only transcript Chat continues to render history.

## How

Consume WP-009's SSE relay (the `ChatStreamEvent` contract, WP-001). The POST
names the open change id — the client cannot target another; the server binding
guard (WP-008) is the authority. Honest resume note from `complete.resumed`.
Consume `tokens.css` only.

## Tests

`Composer.test.tsx` + `useChatStream.test.tsx` cover the six acceptance bullets:
FR-23 states, FR-20 disable, FR-22 partial+interrupted, FR-19 not-delivered,
FR-26 honest resumed note. axe-core on the dock + consent gate.

## Rollback

Remove the dock + the POST funnel exception; the thread reverts to the read-only
transcript Chat. No read surface affected. Revert the commit.
