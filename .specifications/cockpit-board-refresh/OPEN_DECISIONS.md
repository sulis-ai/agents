# Cockpit Board Refresh — Founder-Owned Open Decisions

> These are the genuinely founder-owned calls — they can't be derived from the design +
> code. Everything else in the spec was derived. Each has a recommended default so the
> build can proceed if the founder doesn't want to weigh in; the founder confirms or
> overrides.

| ID | Decision | Recommended default | Why it's the founder's call |
|---|---|---|---|
| **Q-1** | The "Working" freshness window — how recently must a running session have moved to count as *Working* (pulsing, `now`) rather than a quiet *Live*? | **< 60s = Working** | It's a feel/perception threshold about what "actively moving" means on your board. |
| **Q-2** | Recency buckets — exact thresholds for `now` / `Nm` / `Nh` / `Nd` / `Nw`. | minutes < 60m, hours < 24h, days < 7d, then weeks | A presentation/voice call about how staleness reads at a glance. |
| **Q-3** | Empty-board call-to-action — now that the "Start something new" button exists, should it **replace** the CLI-string guide in the empty state, or sit beside it? | **Sit beside it** (button primary, CLI hint secondary) | A product/onboarding-voice choice about how a first-time founder is guided. |
| **Q-4** | Stale-data hint — when a poll fails, surface a quiet "updated Ns ago" / stale indicator, or stay silent and keep last-good data (current behaviour)? | **Stay silent, keep last-good** | A trust/UX call about whether to show the seams of polling. |
| **Q-5** | Health-unknown wording — the label for the new unknown-health badge. | "Too early to tell" (with reason underneath) | Founder voice; the exact words the board says about a change with no signal yet. |
| **Q-6** | Lane-overflow policy — at what card count (if any) does a lane switch from plain internal scroll to virtualisation/pagination? | **Plain scroll to 200, revisit if breached** | A scale/feel trade-off you may have a view on. |
| **Q-7** | Shipped-card recency wording (CS-5 / FR-56) — the exact phrasing for a shipped change's static recency. | **"shipped Nd ago"** (e.g. "shipped 3d ago") | Founder voice; the words the board uses to date an archived change. |

## Notes for the build plan

- None of Q-1..Q-6 block starting the net-new work; they parameterise it. The wire types,
  the server reads, the components, the lanes, the responsive layer, and the unknown-state
  handling can all be built with the recommended defaults and tuned on confirmation.
- The one **non-negotiable** that is *not* an open decision: the unknown/degraded states
  (FR-31, FR-41, FR-42) and never-throw-never-500 degradation (BR-11) are requirements, not
  options — they close the design's sharpest gap.
</content>
