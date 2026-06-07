# Work Packages — autonomous-delivery-environment (CH-01KT50)

> **Change:** `create-autonomous-delivery-environment` · `change_id: 01KT500K2JTE2EGW6TPPQ4D4VN`
> **Derived — do not hand-edit.** Regenerated from `WP-*.md` frontmatter.
> **Decomposition:** VERTICAL SLICES — each WP is one COMPLETE, OBSERVABLE user round-trip.
> **Re-sliced 2026-06-04** from 27 horizontal layers to 11 vertical round-trips.

## Why this plan is vertical, not horizontal

The previous plan sliced **horizontally**: separate route WPs, separate UI WPs,
and ONE integration+acceptance WP at the very end. That let the **consumption
half** of a flow go missing until the end — an outside-in walk against
`apps/cockpit` confirmed every NEW capability's consumption half was entirely
unbuilt (no chat send/stream route, no concierge/onboarding/search/products
routes; `Chat.tsx` was read-only). Work got called "done" on green pipelines
and passing per-piece reviews while the **real user round-trip was never
observed**.

This plan makes that impossible. **Each slice (WP-003..011) delivers a complete
round-trip for one journey: data + server route + (bridge, where needed) + the
UI that consumes it, together** — so a real person can perform the action and
SEE the outcome. No WP ships a route without its consuming UI, or a UI without
its backing route/bridge.

## The observed-acceptance gate (MUST on every slice)

Every journey slice's Definition of Done is: **"run the real cockpit app,
perform the journey's first action, and OBSERVE the journey's observable
result"** — mapped to that journey's stored verification scenario. **Green CI,
green deploy, and a green from-graph scenario run are explicitly NOT
sufficient.** The from-graph `sulis-verify-acceptance --scenario` run sits *on
top of* the human observation, never instead of it.

Three slices have an irreducibly-human/third-party hop named as a
**BLOCK-and-hand-to-founder** step (driving a real `claude` session): the
two-way chat (WP-005), the concierge (WP-009), and the cold-start onboarding +
start-from-intent (WP-010/011). Everything else is fully observable by running
the local app.

## Shape

**11 WPs: 2 foundation (1 data contract · 1 signed visual contract) + 9 vertical
journey round-trips.**

The 9 round-trips map 1:1 (or 2:1 where two journeys share a surface) to the 11
stored verification scenarios A–K.

**Founder-locked decisions baked into the slices:** repo create defaults
**local-only** (`git init`, confirm-gated, no GitHub publish unless separately
confirmed, no dangling config on failure — WP-010); **one Product per
onboarding conversation** (WP-010); Product icon = **neutral two-letter tile**
(no logo upload this slice — WP-010).

---

## Foundations (build first; not journey round-trips)

- **WP-001** — Shared data contract: the full api-types seam (reads + chat + products + discovery) (contract, 5h) · dep none · `pending`
- **WP-002** — Signed visual contract: the one coherent surface (the #45 gate) (contract) · `done` · SIGNED `2026-06-03T08:31:03Z` · `provenance: production-approved`

> WP-001 merges the two prior horizontal contract WPs into one foundation so
> every vertical slice has the full wire seam from the start. WP-002 is the
> SIGNED visual contract (#45 gate already open), covering every surface incl.
> the concierge, onboarding, product switcher, and per-product board.

## ▶ Ready to start now (no unmet deps) — 1

- **WP-001** — Shared data contract (foundation). The moment it lands, **WP-003**
  (the first round-trip) unblocks.

## The vertical-slice queue (ordered: thinnest-fully-observable first, then dependency + risk)

Each line is **"journey X round-trip: open → action → observed result"**.

| # | Slice | Journey round-trip | Scenario | Observed-acceptance | Live hop? |
|---|---|---|---|---|---|
| **WP-003** | Board READ | open the app → (just open it) → SEE your real in-flight changes by stage | A `Y6Z1…TDHS` | drive the app, see the board render real changes | none — fully local |
| **WP-004** | Status | open a change → (click it) → SEE its stage track + plain-English status | B `1PB2…YP06` | drive the app, open a change, see stage + status | none — fully local |
| **WP-005** | Two-way chat | type a message → (send) → SEE the agent resume/spawn and reply live | C `YY4R…3ZNF` | recorded stream in CI **+ live reply on the founder machine** | **BLOCK-and-hand-to-founder: real `claude`** |
| **WP-006** | Brain + previews | open a change → (open Brain / a doc) → SEE created entities grouped + a doc rendered | F `65JX…6XH` · E `00VX…6YH` | drive the app, see grouped brain + rendered doc | none — fully local |
| **WP-007** | Search | type/filter → (type a term) → SEE the board narrow to matching changes | D `CP3M…FJ80` | drive the app, watch the board narrow | none — fully local |
| **WP-008** | Product switch | pick another Product → (select it) → SEE the board re-scope to it | K `PENDING-MINT` | drive the app with 2 Products, watch it re-scope | none — fully local |
| **WP-009** | Concierge ask | ask a question → (ask) → SEE a read-only answer about your world | I `PENDING-MINT` | recorded answer in CI **+ live answer on the founder machine** | **BLOCK-and-hand-to-founder: real `claude`** |
| **WP-010** | Onboarding | empty graph → (have the setup conversation, confirm) → SEE a real graph minted | G `PENDING-MINT` | recorded flow in CI **+ real mint on the founder machine** | **BLOCK-and-hand-to-founder: real `claude` + `git`** |
| **WP-011** | Start-from-intent (+investigation) | say what you want → (confirm) → SEE a change start at Recon | H `PENDING-MINT` · J `PENDING-MINT` | recorded start in CI **+ real change start on the founder machine** | **BLOCK-and-hand-to-founder: real `claude` + `git` + `sulis-change start`** |

### Which slice is FIRST and why it is the thinnest fully-observable one

**WP-003 (the per-product Board READ round-trip) is FIRST.** It proves the
vertical pattern end-to-end with the **least external dependency**: open the app,
see real in-flight changes for the active Product. It needs no live `claude`, no
recorded fixture for a human to see the result, no third-party hop — seed a real
change, run the local app, and the board renders it. It is a refactor of an
existing read surface (Dashboard → stage-column Board) plus a thin read-scope
helper, so it is the lowest-risk, most-observable seam to establish the pattern
every later slice reuses (data → route → UI in one branch, observed by driving).

### Why the two-way chat is sequenced early (WP-005)

It is the **highest-risk consumption half** — the app's first write/act path, and
the surface where the earlier attempt churned (the interactive-TUI/pty path is
explicitly rejected; this uses headless `claude -p` stream-json). It is sequenced
right after the thread shell it docks into (WP-004), before the lower-risk read
slices (brain, search), so the riskiest round-trip is proven early rather than
discovered broken at the end.

---

## Dependency graph

```
WP-002 (visual contract, SIGNED, done) ─────────────────┐ (#45 gate — covers every surface)
                                                         │
WP-001 (shared data contract) ──┬─ WP-003 (Board READ, A) ───────────────┐
                                │        │                                │
                                │        ├─ WP-004 (Status, B) ───┬────────┤
                                │        │        │               │        │
                                │        │        ├─ WP-005 (Two-way chat, C) ◀─ docks into the shell
                                │        │        │        │                    │
                                │        │        ├─ WP-006 (Brain+previews, F+E)
                                │        │        │                              │
                                │        └─ WP-007 (Search, D) ◀── 003,004      │
                                │                  │                             │
                                │   WP-008 (Product switch, K) ◀── 003,006,007  │
                                │                                                │
                                │   WP-009 (Concierge ask, I) ◀── 005           │
                                │   WP-010 (Onboarding, G) ◀── 005              │
                                │   WP-011 (Start-from-intent, H+J) ◀── 003,005,009,010
                                └────────────────────────────────────────────────┘
```

(All journey slices also depend on WP-001 + WP-002.)

## Suggested execution waves

| Wave | WPs | Why |
|---|---|---|
| 0 | WP-002 (done) | The signed visual contract; #45 gate open |
| 1 | **WP-001** | The full data seam; unblocks the first slice |
| 2 | **WP-003** | The thinnest fully-observable round-trip — proves the vertical pattern (board READ, A) |
| 3 | **WP-004** | Thread shell + status (B); the spine chat/brain dock into |
| 4 | **WP-005** | Two-way chat (C) — highest-risk consumption half, early; includes the first live BLOCK-and-hand-to-founder |
| 5 | WP-006, WP-007 | Brain+previews (F+E) and Search (D) — lower-risk reads, parallel after the shell |
| 6 | **WP-008** | Product switch (K) — promotes the trivial scope to the full roll-up; re-scopes board+brain+search |
| 7 | **WP-009** | Concierge ask (I) — reuses the chat composer; live BLOCK-and-hand-to-founder |
| 8 | **WP-010** | Onboarding (G) — cold-start mint; live BLOCK-and-hand-to-founder; carries all three locked decisions |
| 9 | **WP-011** | Start-from-intent + investigation (H+J) — reuses the confirm gate + concierge offer; live BLOCK-and-hand-to-founder |

Each slice is **independently observable before the next starts** — the wave
order is the recommended path, but any slice whose deps are `done` can be driven
and observed on its own.

## Scenario linkage (from-graph verification, ON TOP OF the observed round-trip)

The six ORIGINAL scenarios A–F are minted and linked. The five NEW scenarios
G–K are **not yet minted** — author them (`sulis-author-scenario` in the specify
step) and backfill each `dna:scenario:<ULID>` into the delivering WP's
`verifies_scenario` + `observed_acceptance.scenario` (currently
`PENDING-MINT:<letter>`).

| Scenario | Status | Delivering slice |
|---|---|---|
| A — See everything in flight (board) | minted `Y6Z1EJPF6GY1BAQ96WGA86TDHS` | WP-003 |
| B — Understand where a change is (status) | minted `1PB20WWQY89W9GTE9HKS45YP06` | WP-004 |
| C — Talk to the agent (two-way chat) | minted `YY4RJ7JS8KT55BS61BD0ER3ZNF` | WP-005 |
| D — Find a change (search) | minted `CP3MAX93563W45W7D547T5FJ80` | WP-007 |
| E — Read a document rendered (previews) | minted `00VX23T9WP4T6W7XXN39FMT6YH` | WP-006 |
| F — See what the agent has created (brain) | minted `65JX0VABSE53NJJCVP8NQRTMXH` | WP-006 |
| **G — Set up by talking (onboarding)** | PENDING-MINT | WP-010 |
| **H — Start from intent** | PENDING-MINT | WP-011 |
| **I — Concierge ask** | PENDING-MINT | WP-009 |
| **J — Investigation → change** | PENDING-MINT | WP-011 |
| **K — Switch the active Product** | PENDING-MINT | WP-008 |

## Deferred infrastructure needs (each ships WITH the slice that needs it)

Per the re-slice, fixtures land inside their journey slice — not in a separate
end-of-plan integration WP — so each round-trip is observable when it lands.

| Fixture | Needed by slice |
|---|---|
| `recording-bridge-claude-session` (live/resume/spawn/mid-step) | WP-005 (chat) |
| `seed-brain-entities-fixture` | WP-006 (brain) |
| `recording-bridge-discovery-session` | WP-009 (concierge), WP-010 (onboarding), WP-011 (start) |
| `fixture-project-directory` (+ already-minted variant) | WP-010 (onboarding) |
| `fixture-repo-create-target` (+ failing variant) | WP-010 (onboarding) |
| `fixture-local-repo-for-clone` (+ broken variant) | WP-011 (start-from-intent) |

## Status legend

`pending` ready · `done` merged/closed · `blocked` waiting on a dep.
Visual-contract WP-002 carries the founder sign-off (#45) so every UI half can
proceed.

## Provenance

The 27 prior horizontal WPs are archived verbatim under
`_archive-horizontal-2026-06-04/` for reference. Their contracts are preserved
inside the vertical slices (each slice's `derived_from` records which horizontal
WPs it folds).
