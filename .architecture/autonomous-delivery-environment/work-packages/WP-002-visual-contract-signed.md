---
# Identity (WP-01)
id: WP-002
title: "Visual contract: the one coherent surface (board → thread) — SIGNED OFF"
kind: contract
contract_type: visual
surface: sulis-app
source: feature
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
parent_phase: contract

# Scope (WP-02..04)
atomic_branch: yes
estimate: 0h            # the artifact already exists and is signed; this WP records the gate
blast_radius: medium    # every frontend surface WP depends on it (#45)
primitive: EXPAND-Create
group: expand

# The #45 visual-contract gate — carried from the signed artifact verbatim.
mockup: .architecture/autonomous-delivery-environment/contracts/visual/sulis-app.html
contract_ref: .architecture/autonomous-delivery-environment/contracts/visual/sulis-app.contract.md
signed_off_at: 2026-06-03T08:31:03Z
provenance: production-approved

acceptance_criteria:
  - "The visual contract at contracts/visual/sulis-app.contract.md carries signed_off_at AND provenance: production-approved — the #45 gate is satisfied (founder said 'yes, that's it')"
  - "The mockup renders board → thread, six surfaces, one shell, one token system, one state/empty/error pattern set, in light AND dark"
  - "WCAG 2.1 AA verified for every text + non-text pair, both themes (recorded in the contract)"
test_plan:
  unit: []
  integration: []
  verification:
    - "manual: founder sign-off recorded in the contract front matter (DS-07: AI-generated → human-reviewed → production-approved)"
verification_gates: [contract]
verification:
  na: true
  justification: "Visual contract is a signed design artifact, not running code. Its conformance is verified at frontend-WP build time (token consumption + axe-core) and by the founder sign-off already recorded; there is no test artifact this WP itself ships."

# Lineage (WP-06)
derived_from:
  - finding: "ADR-005 one coherent surface; SRD Design-stage constraints; the founder's 'lumpy → one coherent thing' mandate"
    found_in: .architecture/autonomous-delivery-environment/adrs/ADR-005-one-coherent-surface-board-thread-shell.md
    severity_at_discovery: n/a
generated_by:
  activity: design-stage-visual-pass/2026-06-03
  agent: sulis:engineering-architect
addresses_findings: []
invalidated_by:
  activity: null
  result: null

# Lifecycle (WP-07)
# status `done` — the artifact exists AND is signed off; the gate it guards is open.
status: done
depends_on: []

child_wps: []
kinds: null

rollback: |
  N/A — recording an already-signed design artifact. If the founder revokes
  sign-off, re-open the visual pass and reset signed_off_at + provenance to draft.
---

# Visual contract: the one coherent surface (board → thread) — SIGNED OFF

## Why

ADR-005 makes the whole surface — board, thread, chat, brain, previews, search —
**one coherent thing**, not six bolted-on features, and makes the founder's
sign-off of a real-token mockup the gate before any frontend build (#45). The
frontend surface WPs (WP-011..WP-015) each `dependsOn` this WP and reference it
via `visual_contract`, so they cannot start against an unsigned design.

## Status: the gate is open

The visual contract at
`contracts/visual/sulis-app.contract.md` is **signed off**:

- `signed_off_at: 2026-06-03T08:31:03Z`
- `provenance: production-approved`

The founder approved the vision-site-restrained, sunset-identity-worn-lightly
third pass ("yes, that's it"). Per WP-08.5 / #45 this WP is therefore `done`,
which is what unblocks the frontend WPs at write-time and at their done-transition.

## What it specifies (the frontend WPs consume this)

- **Board → thread** two-level IA; one shell.
- **One token system** — `apps/cockpit/client/src/tokens.css` only, no raw hex. Neutral-dominant, single warm accent (`#C24A2E` light / `#F0A830` dark).
- **One stage scale** — neutral columns; the current column/stage takes the single accent hairline. The `StageBadge` palette is reused, not re-invented.
- **One state-pattern set** — loading skeleton, empty, error+retry, server-down — designed once, reused everywhere.
- **Chat as a persistent dock** in the thread; suggestion chips + free text + slash commands; Pause/Stop run-controls; the consent gate for consequential downstream actions (AI-03).
- **WCAG 2.1 AA** verified across both themes (tables in the contract).

## Follow-up (recorded, not blocking this gate)

`tokens.css` is the stale v4.2.0 slice and must be regenerated to the
neutral-dominant + single-accent set before build. The signed mockup is the
authoritative colour source until then. (Tracked as the existing token-refresh
task; WP-011 picks it up as its first step.)

## Rollback

N/A — this records an already-signed artifact.
