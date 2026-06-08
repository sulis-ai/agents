---
name: cockpit-read-only-invariant
description: The Sulis app (apps/cockpit) is strictly read-only, enforced by a static gate; two-way chat is its first sanctioned write path
metadata:
  type: project
---

The Sulis app at `apps/cockpit/` was built strictly read-only: the Express
server is GET-only by construction, and `apps/cockpit/scripts/check-read-only.sh`
statically fails the build if any route gains a `.post/.put/.patch/.delete`
handler, a filesystem-mutating call, a mutating git verb, or a non-zero process
signal. Liveness is a side-effect-free signal-0 probe (ADR-005, `probeLiveness.ts`).

**Why:** the app's value-add is legibility for a non-technical founder without
risk of corrupting running work. The read-only guarantee is "a guarantee, not a
convention."

**How to apply:** the two-way chat capability (CH-01KT50) is the FIRST sanctioned
write path. Any SRD/design work on this app must treat the chat relay as the single
allow-listed mutation in `check-read-only.sh` and keep every other surface (board,
thread, brain, previews, diff) failing the gate on any mutation. Reuse the existing
ports pattern (ChangeStoreReader, RecreateRunner) and the design-system VIEWER /
contract-preview renderers rather than building new ones (EP-03).
