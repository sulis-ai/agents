# ADR-017 — The `spawnBridge` port carries an optional `originEnv` third argument

- **Status:** accepted
- **Date:** 2026-06-07
- **Change:** CH-01KTHP · feat: live-origin-stamping
- **Deciders:** SEA
- **Extends:** ADR-013 (origin is stamped in the write paths), ADR-003
  (the cockpit is provably read-only)

## Context

`StreamJsonSessionBridge` injects its process-start through a port:

```ts
spawnBridge(argv: string[], cwd: string): BridgeChildHandle;
```

The production default that satisfies this port, `spawnClaudeBridge`, **already**
accepts a third `originEnv?: Record<string, string>` argument and merges it onto
the spawned child's env (delivered by #216). But the **port type drops the third
argument**, so the adapter can never pass it — the documented TODO at
`StreamJsonSessionBridge.ts`. The result: a web-chat session's commits carry no
`assisted` trailer and fall back to inferred origin.

This is a producer/consumer seam: the **relay** produces `originEnv`; the
**bridge port** consumes it and hands it to the spawn. CONTRACT_FIRST
(CF-01..CF-07) says pin the signature before either side is built.

## Decision

**Widen the port to carry an optional third argument**, identical in shape to the
production default it already wires:

```ts
spawnBridge(
  argv: string[],
  cwd: string,
  originEnv?: Record<string, string>,
): BridgeChildHandle;
```

`originEnv` is **optional**. The adapter passes it through to `spawnBridge` when
the relay supplies an assisted origin, and omits it otherwise. The pinned
contract is: *when `originEnv` is present, the spawned child's environment
carries those keys merged over the inherited env; when absent, the spawn is
byte-identical to today.*

## Why optional, not required

- The contract suite injects a **stubbed child** and does not compute origin;
  a required third arg would break every existing call site.
- The **concierge** and **onboarding/start-from-intent** routes ride the same
  bridge (FR-27) but are read-only / do not stamp assisted origin; they must keep
  calling `relay` without an origin.
- Optionality is the boring, backwards-compatible widening — the production
  default's signature is already exactly this shape, so the port is being made to
  *match reality*, not changed.

## Alternatives considered

- **A second, origin-aware bridge port — rejected.** A new process-start seam
  violates ADR-003 (one sanctioned spawn site) and the spec's "no second bridge"
  constraint.
- **Pass origin via a side channel (a field on `SessionResolution`, a closure) —
  rejected.** The env is what the spawned session's `prepare-commit-msg` hook
  reads; threading it as env to the spawn is the direct, established mechanism.
  A side channel would still have to become env at the spawn — extra indirection
  for no benefit.
- **Make the third arg required — rejected.** Breaks the stubbed-child contract
  suite and the read-only concierge/onboarding callers (see above).

## Consequences

- The bridge port type, the adapter's internal `spawnBridge(...)` call, and the
  `relay` signature that carries the origin to the adapter are the surface that
  changes. The production default `spawnClaudeBridge` is **unchanged** — it
  already has the parameter.
- Passing env to the already-sanctioned spawn is read-only from the cockpit's
  side (no file write, no git mutation, no new spawn site) — ADR-003 untouched;
  `check-read-only.sh` needs no change.
- The pinned signature is the contract WP that both the TS relay WP and the
  bridge-wiring WP depend on (WP-08.5 cross-kind decomposition).
