# WP-011 — Degraded / partial card: per-field render + quiet notice, board unaffected

- **Sequence ID:** WP-011
- **dependsOn:** [WP-002, WP-005]
- **kind:** frontend
- **primitive:** EXPAND-Create (degraded-notice element) + REORGANISE-Refactor (`ChangeCard` per-field composition)
- **group:** expand
- **characterisation_test:** `client/src/tests/ChangeCard.test.tsx` (WP-005's; re-asserts the card still renders + links before adding the degraded composition)
- **Estimated token cost:** input ~13k / output ~5k
- **visual_contract:** production-approved (`MOCKUP.html` — degraded card + quiet notice)

## Context

SRD §7c CS-4. The **card-level composition** of the already-specified field-level
unknown reads (FR-31 / FR-41 / FR-42, built in WP-005; produced best-effort in
WP-002). When a change's record is malformed or partial, the card renders
**per-field** — readable fields normal, unreadable ones as their unknown read —
**still renders and still links**, shows a **quiet fixed-string notice**, and
**never breaks the lane or 500s the board**. This is the rendering contract that
makes WP-002's never-throw discipline **visible and usable** on the card.

## Contract

- **Per-field degraded render (FR-54).** Each readable field renders normally;
  each unreadable field falls to its **unknown** read — health → "Health unknown"
  (FR-31), liveness → the distinct unknown shape (FR-41), recency → "—" (FR-42).
  A single card can be in several unknown reads at once and remain usable. The
  card **MUST still render and still link** to `/c/:changeId`.
- **Degraded notice (FR-55).** A quiet, **fixed-string** notice ("some details
  couldn't be read") from the enumerable set (FR-32 / MUC-3) — **never** echoing
  malformed content. The notice is reinforcement (the per-field unknown reads
  carry the primary signal, BR-3) and is **`aria`-announced** so it isn't
  colour-/placement-alone.
- **Board unaffected (BR-26 / EF-2 / NFR-DEGRADE-2 — MUST).** A degraded card
  degrades **independently**: the rest of the board renders normally; the feed
  returns 200 with best-effort fields (the server half is WP-002 / S-21 / S-23 /
  S-24; this WP is the **card render** of those rows). The gone-worktree extreme
  (EF-5) renders all-unknown reads, not-flagged attention, **still a linking
  card**.
- **Composition (SRD §7c precedence).** Degraded is additive to the content
  reads; if the card is **also** shipped (CS-5, WP-012), shipped wins the
  foot/probe treatment while unreadable *identity* fields still fall to unknown +
  the degraded notice.

## Definition of Done

### Red
- [ ] `client/src/tests/ChangeCard.degraded.test.tsx` (against the WP-001
      contract mock, seeding a partial/malformed row):
  - readable fields render normally; unreadable ones render as unknown reads
    (health-unknown / liveness-unknown shape / recency "—");
  - the card **still links** to `/c/:id`;
  - the quiet fixed-string "some details couldn't be read" notice renders and is
    `aria`-announced; it never contains seeded markup/secret text;
  - rendered in a multi-card board, **every other card renders normally** (the
    degraded card never drops a sibling or breaks the lane).
  (**S-35**) **Fails** (no card-level degraded composition yet).

### Green
- [ ] Per-field degraded composition + quiet notice implemented; test passes.
- [ ] jest-axe on the degraded card, light + dark.

### Blue
- [ ] Notice string from the fixed set (grep: no interpolation of row content).
- [ ] Reuses the WP-005 unknown reads (no second "Health unknown" / unknown-probe
      implementation — EP-03).
- [ ] Tokens only; neutral tokens for the unknown reads + notice.

## Definition of Done — requirements & scenarios

- **Satisfies:** CS-4 (FR-54, FR-55, BR-26), EF-2, EF-5 (card side), MUC-1 (card
  render side); NFR-DEGRADE-2, NFR-A11Y-1, NFR-A11Y-4.
- **Makes pass:** **S-35** (degraded card renders per-field and the board is
  unaffected — render side; the server-200 side is WP-002 / S-21·S-23·S-24).

## verification

```
adapter: frontend
artifact: apps/cockpit/client/src/tests/ChangeCard.degraded.test.tsx
```
