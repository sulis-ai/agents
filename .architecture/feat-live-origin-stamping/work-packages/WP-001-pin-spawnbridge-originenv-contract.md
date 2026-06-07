---
wp: WP-001
change_id: 01KTHP2NYQ1A3WHPJD75VP31NT
title: Pin the widened spawnBridge port contract (originEnv 3rd arg)
kind: backend
primitive: reinforce-document
group: reinforce
status: ready
dependsOn: []
estimated_token_cost: { input: ~12k, output: ~4k }
verification:
  adapter: backend
  artifact: apps/cockpit/server/tests/session-bridge.contract.test.ts
---

# WP-001 — Pin the widened `spawnBridge` port contract

## Context

TDD §2/§4, ADR-017. The producer/consumer seam between the relay (produces
`originEnv`) and the bridge port (consumes it, hands it to the one sanctioned
spawn). CONTRACT_FIRST: pin the signature before either side is built, so the TS
relay WP (WP-003/004) and the bridge-wiring WP (WP-002) share one source of truth.

## Contract (the thing this WP pins)

`apps/cockpit/server/ports/SessionBridge.ts` — `StreamJsonSessionBridgeOptions.spawnBridge`:

```ts
spawnBridge(
  argv: string[],
  cwd: string,
  originEnv?: Record<string, string>,   // NEW — optional; ADR-017
): BridgeChildHandle;
```

Behavioural contract (CF): *when `originEnv` is present, the spawned child's
environment carries those keys merged over the inherited env; when absent, the
spawn is byte-identical to today.* The third arg is **optional** so the stubbed-
child contract suite and the read-only concierge/onboarding callers keep working
unchanged.

This WP only changes the **type** + the contract test scaffolding and removes the
`TODO(deferred)` block describing the gap. The adapter's *call* to `spawnBridge`
with the env is WP-002.

## Definition of Done

### Red
- [ ] Add a contract-suite case in `session-bridge.contract.test.ts`: a stub
      `spawnBridge` records its third argument; drive `relay` with a resolution and
      an injected assisted `originEnv`; assert the stub received it as arg 3. With
      the port still 2-arg, this fails to type-check / the arg is dropped.
- [ ] Add the negative case: no origin → stub's third argument is `undefined`.

### Green
- [ ] Widen the `spawnBridge` type in `SessionBridge`-options to the 3-arg shape
      above (optional 3rd). Type-check passes. `spawnClaudeBridge` already matches.
- [ ] Remove the `TODO(deferred)` block at `StreamJsonSessionBridge.ts` (the gap it
      describes is now being closed) — replace with a one-line reference to ADR-017.

### Blue
- [ ] Confirm no other caller of `spawnBridge` breaks (concierge/onboarding/start
      ride `relay`, not `spawnBridge` directly — verify).
- [ ] `pnpm --filter cockpit typecheck` + `vitest run session-bridge.contract` green.
- [ ] `apps/cockpit/scripts/check-read-only.sh` still passes (no new gate change).
