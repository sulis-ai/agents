# ADR-006 — The concierge rides the existing bridge and coordinates only

- **Status:** accepted
- **Date:** 2026-06-04
- **Change:** CH-01KT50 · autonomous-delivery-environment
- **Deciders:** SEA

## Context

The expanded scope adds a **concierge** front door (FR-33, FR-34, FR-N8,
FR-N9, NFR-DISC-05), modelled on the `sulis:sulis` agent. The founder can
ask plain-English questions about their world ("which change was I doing the
login fix in?", "what needs my attention?"), be set up from cold start
(UC-07), and start work from intent (UC-08). The load-bearing rule is
**containment**: the concierge *coordinates only — it never does the work
itself* (FR-N8). Even an *investigation* is real activity and must be
contained in a change, never run inline in the concierge turn (FR-N9).

Two temptations to reject up front:

1. Build the concierge as a **new bespoke agent transport** parallel to the
   two-way chat bridge.
2. Let the concierge **do small bits of work inline** ("just a quick look")
   when the founder asks an exploratory question.

Both break established discipline. The first violates EP-03 (reuse, don't
reinvent) and the seam principle (one sanctioned write path). The second
violates the change-is-the-unit-of-everything principle from the product
ladder and FR-N9.

## Decision

**The concierge is the same headless stream-json bridge as the two-way chat
(ADR-002), driven without a visible terminal, with exactly two direct
consequential acts and everything else read-only or delegated into a
change.**

- **Transport:** the concierge rides `SessionBridge` (ADR-002) — no second
  bridge, no parallel relay (FR-27). It is `claude -p` over the same
  stream-json path the chat relay already proved. This is **EXPAND-Reuse**,
  not a new port.
- **Read path (FR-33):** navigation / status / Q&A reads the change store +
  brain **through the seam, read-only** — the same data and the same
  `ChangeStoreReader` + brain-read projections the board and thread already
  use. Zero writes, zero mints, zero session starts, zero signals
  (NFR-DISC-05). This is the concierge form of the read-only discipline
  (FR-N1 / NFR-SEC-05) extended to the front door.
- **Exactly two consequential acts:** on the founder's confirmation, the
  concierge may (a) **mint setup entities** (FR-28, via the discovery flow,
  ADR-007) and (b) **create a change** (FR-29 / FR-34, via
  `sulis-change start`). Both sit behind the FR-N6 confirm gate
  (NFR-DISC-04). No third consequential act exists.
- **Investigation is a change, not an inline action (FR-34 / FR-N9):** when
  the founder asks the concierge to investigate / explore / look into
  something, the concierge resolves it to an **investigation change**
  (primitive + slug) and — on confirm — runs `sulis-change start` so the
  exploring happens inside that change's own session (UC-06). The concierge
  performs no build, edit, or exploration work in its own turn.

The read-only gate (ADR-003) treats the concierge like every other surface:
the **only** write paths reachable from a concierge code path are the FR-28
mint and the FR-29 change start; any other mutation, worktree write,
build/run, or process start from a concierge path fails the gate.

## Alternatives considered

- **A second, bespoke concierge transport (rejected).** Violates EP-03 and
  the seam principle; doubles the safety surface to audit. The bridge that
  already carries the chat carries the concierge.
- **Let the concierge do "quick" work inline (rejected).** Inline work is
  un-audited, has no lineage / worktree / brain, and can't evolve into a
  build without a hand-off. FR-N9 makes the change the unit of *all* real
  activity, including investigation — precisely so nothing is lost.
- **Make the concierge a third write path with its own gate exception
  (rejected).** The mint and the change-start are already the discovery
  flow's two acts (ADR-007); the concierge reuses them rather than adding a
  new gate carve-out.

## Consequences

- No new transport: the concierge is wiring over `SessionBridge` +
  read-projections that already exist after the chat slice.
- A new read-only test asserts the concierge navigation / status / Q&A path
  performs zero writes / mints / session-starts / signals (FR-33 / FR-N8 /
  NFR-DISC-05), mirroring the board's read-only assertion.
- A containment test asserts an investigation request results in a change
  (after confirm) and **not** in inline investigation work (FR-34 / FR-N9).
- The read-only gate gains no new file-level exception for the concierge —
  it reaches consequence only through the already-sanctioned discovery-mint
  and change-start paths.
