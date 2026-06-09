# WP-005 — Redesigned change card: top line, step dots, single foot verdict

- **Sequence ID:** WP-005
- **dependsOn:** [WP-001]
- **kind:** frontend
- **primitive:** REORGANISE-Refactor (`ChangeCard`) + EXPAND-Create (`LivenessProbe`, `ChangeHealthBadge`, `WaitingOnYou`)
- **group:** reorganise
- **characterisation_test:** `client/src/tests/ChangeCard.test.tsx` (pins current card: handle, intent, slug, nav-on-click, aria-label)
- **Estimated token cost:** input ~20k / output ~10k
- **visual_contract:** production-approved (`MOCKUP.html` — `.card` markup)

## Context

TDD §1 (Client) + §5 + IDEAS.md Concern 2. The whole card redesign. Builds
against the WP-001 contract via the **contract mock** (WPF-03) — does **not**
wait on WP-002's producer. The card shape is the load-bearing rule: **one foot
verdict, waiting XOR health, never both** (TDD §5).

## Contract

`ChangeCard.tsx` renders, in this fixed reading order (identical every card):

1. `topLine`: `handle` (small, muted, mono, left) + `LivenessProbe` (right):
   probe dot + `.sr` state label + bare relative time (now / 12m / 6h / 1w).
   No state word visible; no "last active" prefix.
2. `steps`: slim `·N/6` step dots, `role="img" aria-label="Step N of 6"`.
3. `intent` (clamped), `slug`.
4. **Foot — exactly one branch:**
   `needsAttention.flagged ? <WaitingOnYou reason={…}/> : <ChangeHealthBadge health={…}/>`

New components:
- `LivenessProbe.tsx` — **four** states by fill/motion/shape:
  - working = filled + pulse (`now`),
  - live = solid filled steady,
  - idle = hollow/outline ring,
  - **unknown = a distinct dotted/ghost ring (FR-41)** — visually distinct from
    the hollow Idle dot, so the founder is never told "idle" when the truth is
    "can't tell".
  `.sr` label ("actively working" / "session live" / "idle, not running" /
  **"liveness unknown"**); dot `aria-hidden`. **working vs live** derived from
  `lastActivityAt` recency. **No-recency (FR-42):** when `lastActivityAt === null`
  the recency text is omitted / shown as "—" (never "now" or a bogus age); the
  probe still renders its liveness state. `prefers-reduced-motion` → static ring
  (no pulse), `.sr` label still names it (BR-14 / S-30).
- `ChangeHealthBadge.tsx` — word + shape, renders **all four** states (data
  drives which):
  - On track = check, Off track = triangle, Worth a look = dash (deferred input),
  - **Health unknown = a neutral shape + neutral word (FR-31)** — the honest
    "not enough signal yet" read, never styled as on-track or off-track.
  Thin 1px border; `.sr` reason appended; left-aligned, content-width (the quiet
  default). The unknown label wording follows the founder default ("Too early to
  tell", Q-5) — a string constant, swappable on confirmation.
- `WaitingOnYou.tsx` — full-width centered; triangle icon + bold "Waiting on
  you" + `why` (truncates first, never drops icon/label); 1.5px warning border.

Remove: the `StageBadge` from the card (the lane already says the stage); no top
banner; no left colour stripe.

## Definition of Done

### Red
- [ ] Characterisation `ChangeCard.test.tsx` pins current card → passes before.
- [ ] New tests (against the WP-001 contract mock):
  - `WaitingOnYou` and `ChangeHealthBadge` are **mutually exclusive** in the DOM
    — flagged card has no health node; unflagged card has no waiting node
    (**S-10, S-11**).
  - A non-flagged card **always** shows exactly one health badge, **including
    the `unknown` state** — a `health.state:"unknown"` change renders the neutral
    "Health unknown" badge (NOT on-track, NOT off-track) with its reason (**S-16**).
  - `LivenessProbe`: each of working / live / idle / **unknown** renders the
    right shape class + the right `.sr` label; the **unknown** shape is distinct
    from idle (**S-17**); reduced-motion drops the pulse and keeps the SR label
    (**S-30**).
  - **No-recency:** a `lastActivityAt:null` change renders recency as "—" /
    omitted, never "now" or a bogus age, and the probe still renders (**S-18**).
  - Reading order assertion (handle → probe → steps → intent → slug → foot).
  **All fail** (components absent).

### Green
- [ ] Card + three sub-components implemented; all Red tests pass.
- [ ] jest-axe on the card + each sub-component, in **light AND dark**, for
      **every content variant** — waiting / on-track / off-track / **unknown
      health** / **unknown liveness** / no-recency (**S-27**).
- [ ] Full handle on the card link's accessible name (`aria-label="Change CH-… :
      <intent>"`).

### Blue
- [ ] Single-branch foot (no two-sibling render of waiting + health).
- [ ] Tokens only — no literal colour; status tints ride `--bg-*` recipe; the
      unknown reads use neutral tokens (not the warning/success tints).
- [ ] `why` / health `reason` truncate first; icon + label never wrap-drop.
- [ ] The unknown-health label is one string constant (Q-5 default), swappable.

## Definition of Done — requirements & scenarios

- **Satisfies:** FR-20..FR-24, FR-31 (unknown health badge), FR-41 (unknown
  liveness shape), FR-42 (no-recency render); BR-1, BR-2, BR-3, BR-4, BR-13,
  BR-14; CS-2's reduced-motion strand; NFR-A11Y-1, NFR-A11Y-4, NFR-A11Y-7.
- **Makes pass:** **S-2** (waiting foot, component side), **S-3** (off-track
  badge), **S-4** (alive+staleness probe), **S-10** (waiting hides health),
  **S-11** (non-waiting shows health), **S-16** (health-unknown badge, render
  side), **S-17** (liveness-unknown distinct shape), **S-18** (no-recency),
  **S-27** (card axe across all variants, light+dark), **S-30** (reduced motion).

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/ChangeCard.test.tsx
```
