# ADR-003 — Chat is the single sanctioned write path; everything else stays read-only

- **Status:** accepted
- **Date:** 2026-06-03
- **Change:** CH-01KT50 · autonomous-delivery-environment
- **Deciders:** SEA

## Context

Today the cockpit is statically provable read-only: `check-read-only.sh`
(MVP WP-016) plus `read-only-inventory.test.ts` and the client fetch-funnel
test forbid filesystem writes, `git` mutation verbs, non-zero process
signals, and `app.post/put/patch/delete`. This is the load-bearing safety
guarantee (MVP ADR-003) and a key part of why a non-technical founder can
trust the app.

The chat introduces the app's **first write/act path**. Two things become
"writes" that the current gate forbids:

1. an HTTP mutation verb on the relay endpoint, and
2. a **process start** — resume/spawn launches a `claude` session
   (a far more consequential side effect than any file write).

The negative requirements (FR-N1..N5) and NFR-ARCH-02 / NFR-SEC-05/06 say:
the relay (including the resume/spawn it triggers) is the **only**
sanctioned write path; every other route stays read-only; reading any
surface must start no session.

## Decision

**Extend the read-only gate to allow-list exactly the chat relay module
(and the SessionBridge adapter it calls), and nothing else.** The gate
keeps failing on:

- any process start (`spawn`/`exec` of a session) **outside** the
  named relay/bridge files;
- any non-zero `process.kill` anywhere (liveness stays signal-0, FR-N4 /
  NFR-SEC-04);
- any filesystem write, `git` mutation verb, or `app.post/put/patch/delete`
  anywhere **outside** the relay route file.

The allow-list is a **file path + rule pairing**, not a blanket waiver:
the relay file may register one mutation route and the bridge file may
start a process; no other file may do either. New rule added to the gate:
**"process start outside the sanctioned relay/bridge"** (parallel to the
existing "non-zero signal" rule).

The session-to-change binding guard (ADR-004) runs *before* any process is
started or any prompt delivered, so even the sanctioned path cannot touch
the wrong change's session (FR-N2 / NFR-SEC-06).

## Alternatives considered

- **Drop the static gate, rely on review (rejected).** The gate is the
  reason the read-only guarantee can't silently regress. Keeping it and
  narrowing the allow-list is strictly safer than removing it.
- **A blanket "writes allowed in server/" waiver (rejected).** Would let
  any future route gain a mutation undetected. The whole value is that the
  *one* exception is named and everything else still fails the gate.
- **A separate write-service process (rejected — over-build).** The slice
  is local, single-founder; a second process adds operational surface for
  no safety gain over a path-scoped allow-list.

## Consequences

- `check-read-only.sh` gains: (a) the relay route file in the
  `app.post`-exception set, (b) the bridge file in a new process-start
  exception set, (c) a new rule that flags process starts elsewhere.
- `read-only-inventory.test.ts` gains a parallel assertion: exactly one
  module may start a process; loading any read surface starts none
  (NFR-SEC-05 — a test asserts no `claude` process spawns on read).
- FR-N1's acceptance ("the gate's only sanctioned write path is the chat
  relay") becomes a literal, runnable check.
- The founder-trust property survives the first write path: the app is
  still *provably* read-only everywhere except one explicitly-audited seam.
