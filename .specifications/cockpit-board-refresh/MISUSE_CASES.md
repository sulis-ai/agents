# Cockpit Board Refresh — Misuse / Abuse Cases

> Scope note: the cockpit is a **single-founder, localhost, read-only** tool. This change
> adds **no auth surface, no write path, no external call**. So the classic abuse surface
> (spoofing, privilege escalation, injection into a write) does not apply here. The real
> abuse surface is **bad or pathological data from the change store** and **scale**, plus
> **content leakage** through the new derived `reason` strings. Each misuse case names the
> abusive condition and the **required system response** (the negative requirement).

## MUC-1 — Malformed feed row

- **Abusive condition:** a change record with a garbage stage, missing required fields, or a
  malformed `session.json` (the same shape `probeLiveness` already guards against).
- **Targets:** UC-1 (open board), the feed enrichment, every derived read.
- **Flow:** the feed lists the bad record; one of the new reads (`computeHealth` /
  `readRigorForStage` / `readTestsState` / recency) hits the malformed input.
- **System response (REQUIRED):** the read MUST resolve the malformed input to a safe
  **unknown** default and MUST NOT throw. The row renders with unknown reads; the feed
  returns 200; the other rows are unaffected (BR-11 / NFR-DEGRADE-1). The board MUST NEVER
  500 because one record is malformed.
- **Related NFRs:** NFR-DEGRADE-1, NFR-DEGRADE-2.

## MUC-2 — Pathological change count

- **Abusive condition:** hundreds of in-flight changes, or hundreds in a single lane.
- **Targets:** the server enrichment fan-out; the lane render.
- **Flow:** the enrichment runs a per-record derivation across the whole set; a lane tries
  to render hundreds of cards.
- **System response (REQUIRED):** the per-record fan-out MUST stay inside the existing
  bounded `Promise.all` over the in-flight set — **no new unbounded loop** (A-1). The feed
  MUST return within NFR-PERF-3. The lane's internal scroll MUST absorb the count (NFR-PERF-2);
  the header count MUST reflect the true total. If a lane ever exceeds the virtualisation
  threshold (Q-6), it MAY virtualise — but MUST NOT block the feed.
- **Related NFRs:** NFR-PERF-2, NFR-PERF-3.

## MUC-3 — `reason` text leaking change content

- **Abusive condition:** a change whose transcript / created-entity content contains markup,
  secrets, or attacker-shaped text.
- **Targets:** the new `health.reason` and the surfaced attention `reason`.
- **Flow:** a naive implementation interpolates change content into the reason string shown
  on the board.
- **System response (REQUIRED):** health/attention `reason` MUST be drawn from a **fixed,
  enumerable set** of plain-English strings ("tests failing", "no design recorded", "no
  tests run yet", "waiting on a decision", "blocked", "stopped mid-reply"). It MUST NEVER be
  interpolated from transcript or reply body (FR-32 / A-2). No change content reaches the
  board feed.
- **Related NFRs:** NFR-SEC-2.

## MUC-4 — Path escape via a worktree read

- **Abusive condition:** a worktree containing a symlink or `..` path that, if followed,
  would read outside the change's own worktree.
- **Targets:** `readRigorForStage`, `readTestsState` (the new filesystem reads).
- **Flow:** a read joins an attacker-influenced path and follows it out of the worktree.
- **System response (REQUIRED):** the new reads MUST stay within the change's own worktree
  (reuse `safeJoin`'s containment discipline), MUST be read-only (no write, no process
  spawn), and MUST fail-soft to an unknown read on any containment violation rather than
  reading the escaped path.
- **Related NFRs:** NFR-SEC-1, NFR-SEC-3.

## MUC-5 — Stale liveness masquerading as truth

- **Abusive condition:** a stale `session.json` whose recorded pid has been **reused** by an
  unrelated process (a PID-reuse hazard).
- **Targets:** UC-4 (liveness read).
- **Flow:** the signal-0 probe sees the reused pid as "alive" and the card claims "Live".
- **System response (REQUIRED):** this is an **accepted, pre-existing limitation** of the
  signal-0 probe (`probeLiveness.ts` / ADR-005), not introduced by this change. The required
  posture is honesty about uncertainty: where liveness cannot be trusted (no/malformed
  session record), the probe renders the **distinct unknown shape** (FR-41), not a confident
  "Live". This change MUST NOT make liveness *appear more certain* than the underlying probe
  supports — i.e. it MUST surface `unknown` as unknown, never collapse it to Idle or Live.
- **Disposition:** accepted-as-risk (inherited from ADR-005); the new requirement is only
  that the unknown state is rendered honestly.

## Pre-mortem — top failure scenarios if this shipped as-designed-only

The design drew only the healthy ends. The three most likely "6-months-live, post-incident"
failures, each converted into a requirement already in the SRD:

1. **A fresh Recon change reads "On track" with nothing behind it** → false reassurance.
   → FR-31 (health-unknown), BR-12 (Recon has no required artifact, so only tests pull it
   down; absent tests ⇒ unknown, not on-track).
2. **A change with a gone worktree 500s the whole board** → the founder loses the board over
   one bad record. → BR-11 / NFR-DEGRADE-1 (never-throw, never-500).
3. **The probe says "Idle" when the truth is "we can't tell"** → the founder mis-triages a
   change that may actually be running. → FR-41 (liveness-unknown distinct shape).
</content>
