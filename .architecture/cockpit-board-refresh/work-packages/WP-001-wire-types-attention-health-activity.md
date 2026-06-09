# WP-001 — Widen the `Change` wire type: attention + health + last-activity

- **Sequence ID:** WP-001
- **dependsOn:** []
- **kind:** backend (shared contract)
- **primitive:** EXPAND-Create (new types) + REORGANISE-Refactor (extract `NeedsAttention`)
- **group:** expand
- **Estimated token cost:** input ~12k / output ~3k
- **visual_contract:** n/a (no visual surface)

## Context

TDD §1 (Shared) + ADR-002. The board card needs three reads not on the feed
today. This WP lands the **contract** for them in `apps/cockpit/shared/api-types.ts`
so every producer and consumer imports the same shapes (CF-02). Type-only file;
no runtime code.

## Contract

Add to `api-types.ts`:

```ts
/** Lifted from ChangeStatus.needsAttention — one shape, two callers (CF-02). */
export interface NeedsAttention {
  flagged: boolean;
  reason: "blocked" | "waiting-on-decision" | "stopped-mid-reply" | null;
}

/** "unknown" is first-class — a fresh/degraded change must read honestly, not
 *  masquerade as on-track (FR-31). "worth-a-look" stays deferred (ADR-001). */
export type ChangeHealthState = "on-track" | "off-track" | "worth-a-look" | "unknown";

export interface ChangeHealth {
  state: ChangeHealthState;   // producer emits on/off-track + unknown now; worth-a-look deferred (ADR-001/FR-31)
  reason: string;             // plain-English shape from a fixed set, never reply body (NFR-SEC-03/FR-32)
}
```

- Refactor `ChangeStatus.needsAttention` to reference `NeedsAttention` (no shape
  change — same fields).
- Add to `interface Change`:
  - `needsAttention: NeedsAttention;`
  - `health: ChangeHealth;`  // `state` may be `"unknown"` (FR-31)
  - `lastActivityAt: string | null;`  // ISO 8601 UTC; `null` ⇒ no-recency (FR-42); drives relative time + working/live split
  - `liveness: Liveness;`  // existing union running / not-running / **unknown** (FR-41) — confirm `unknown` is present; the probe renders it distinctly

## Definition of Done

### Red
- [ ] `Change` consumers that destructure the new fields fail to typecheck until
      producers set them (the compiler is the failing test here). Add a
      `client/src/tests/contract-links.test.ts` assertion (or extend it) that
      the new fields exist on `Change` and `ChangeHealthState` has **all four**
      members (`on-track`, `off-track`, `worth-a-look`, **`unknown`**).
- [ ] Assert `Liveness` carries the `unknown` member (the probe's distinct
      unknown shape, FR-41, depends on it) and `lastActivityAt` is nullable
      (no-recency, FR-42).

### Green
- [ ] Types added; `ChangeStatus.needsAttention` now references `NeedsAttention`.
- [ ] `tsc` clean across `apps/cockpit` (workspace deps built first — WPF-14).

### Blue
- [ ] No duplicate `{ flagged, reason }` shape remains (grep: it appears only in
      `NeedsAttention`).
- [ ] JSDoc on each new field names its source-of-truth ADR / FR.

## Definition of Done — requirements & scenarios

- **Satisfies:** the wire contract behind FR-30, FR-31 (`unknown` health state),
  FR-40, FR-41 (`unknown` liveness), FR-42 (nullable `lastActivityAt`); CF-02
  (one `NeedsAttention` shape).
- **Makes pass (contributes the type the test asserts against):** S-16, S-17,
  S-18, S-19 (the unknown states can only be expressed because the wire carries
  them) — fully driven green downstream in WP-002 / WP-005 / WP-009.

## verification

```
adapter: backend
artifact: apps/cockpit/client/src/tests/contract-links.test.ts
```
