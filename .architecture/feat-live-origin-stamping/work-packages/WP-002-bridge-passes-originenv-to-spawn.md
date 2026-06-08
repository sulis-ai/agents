---
wp: WP-002
change_id: 01KTHP2NYQ1A3WHPJD75VP31NT
title: Bridge adapter passes originEnv through to the spawn
kind: backend
primitive: expand-create
group: expand
status: ready
dependsOn: [WP-001]
estimated_token_cost: { input: ~12k, output: ~4k }
verification:
  adapter: backend
  artifact: apps/cockpit/server/tests/session-bridge.contract.test.ts
---

# WP-002 — Bridge adapter passes `originEnv` through to the spawn

## Context

TDD §2/§5 (component 2), ADR-017. With the port widened (WP-001), the adapter must
actually carry the assisted `originEnv` from `relay` to the injected `spawnBridge`.
EXPAND-Create wiring — the public face stays the `SessionBridge` port; the CLI is
*called by* the adapter (no wrap, no new spawn site, ADR-003).

## Contract

`StreamJsonSessionBridge.relay` accepts the assisted origin for the relayed
session (carried from the relay route, WP-003) and forwards it as the third
argument to `this.opts.spawnBridge(argv, cwd, originEnv)`. When no origin is
supplied, the call omits the third argument (byte-identical to today).

The exact mechanism by which `relay` receives the origin (a new optional param on
`relay`, or via the resolution) is pinned in WP-003's contract; this WP consumes
whatever WP-003 pins and threads it to the spawn. Keep the change minimal: the
adapter neither computes nor formats origin — it only forwards.

## Definition of Done

### Red
- [ ] Extend the WP-001 contract case so the assisted `originEnv` flows the full
      path: relay route → `relay` → injected `spawnBridge` arg 3. Assert the stub
      child sees the exact `{ SULIS_ORIGIN: "assisted; conversation=…; turn=…" }`.
      Fails until the adapter forwards it.

### Green
- [ ] In `relay`, forward the supplied `originEnv` to `spawnBridge`; omit when absent.
- [ ] No new spawn site; the only process start remains `spawnClaudeBridge` (the
      injected default). `spawnClaudeBridge` is unchanged (already accepts the arg).

### Blue
- [ ] `vitest run session-bridge` green (contract + streamjson + recorded suites).
- [ ] `check-read-only.sh` passes — confirm the adapter is still the single
      allow-listed spawn site and no new write/git/http appears.
- [ ] Typecheck green; no `any` on the origin path (boring, explicit types).
