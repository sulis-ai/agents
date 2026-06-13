# ADR-005 — The L1 no-egress scenarios confine the process *in the test harness*; SC-L2.5 asserts the bypass

> **Status:** accepted
> **Date:** 2026-06-13
> **Change:** CH-E22SX6 · harden
> **Affects:** SC-L1.2, SC-L1.4, SC-L2.5 test design; the threat-model docstrings

## Context

Two scenarios assert properties that the production code of this phase does
**not** enforce (per ADR-001): SC-L1.2 (no raw egress) and SC-L1.4
(injection can't act → no egress). The wall that enforces them is L3,
deferred. And SC-L2.5 deliberately asserts that the file-tool guardrail
**does not** stop a subprocess. If the tests are written naively they will
either (a) be impossible to make green without L3, or (b) be green
dishonestly. The SPEC demands the tests be **honest about what they
confine**.

## Decision

**Confine the process inside the test harness with a portable
no-raw-egress shim, prove the control L1 owns under that confinement, and
name L3 as the production owner in the test's own docstring. For SC-L2.5,
assert the bypass succeeds and document L3 ownership.**

1. **Portable no-egress shim (test-only).** A pytest fixture installs a
   process-local block on raw outbound sockets — a `socket.socket` /
   `socket.create_connection` monkeypatch that raises for any destination
   except the proxy's loopback endpoint. Pure Python, identical on
   macOS/Linux/Windows (Constraint: portable; no `sandbox-exec`, which is
   macOS-only and belongs to L3's own scenarios SC-L3.1/3.2). The shim
   *simulates* L3's OS denial so the L1 proxy-correctness half can be
   asserted now.

2. **SC-L1.2 under the shim.** With the shim active: assert a direct
   `create_connection` to an arbitrary host **raises/refuses**, and the
   proxy's loopback connection **succeeds** and reaches the network on the
   agent's behalf. The test proves: *given* egress is denied (the L3
   precondition), the proxy is the working door and a bypass fails. The
   docstring states: "the egress denial here is simulated by a test shim;
   in production it is owned by L3 (`l3-os-egress-denial`), not by L1."

3. **SC-L1.4 under the shim.** Fetch a page whose body carries an injection,
   returned framed as untrusted data (ADR-003). Assert **zero** outbound
   connections to the attacker host occur after the content is returned —
   the payload is in the data channel and the shim records no egress beyond
   the sanctioned proxy fetch. Same docstring honesty.

4. **SC-L2.5 asserts the bypass (the honest boundary).** Run
   `bash -c 'cat <out-of-scope-path>'` and assert the read **succeeds** — the
   file-tool was bypassed entirely. The test's assertion is the *bypass
   itself*, plus a docstring naming L3 (the OS sandbox) as the owner of the
   confinement L2 structurally cannot provide. No false sense of security:
   the test exists to *prove the limit is real and known*.

## Alternatives considered

- **Use `sandbox-exec` / bubblewrap in the L1 tests (rejected here).** That
  is real OS confinement — it *is* L3, and it is per-OS (not portable, fails
  the L1 byte-identical constraint). It belongs to SC-L3.1/3.2, this change's
  follow-on. Using it for L1 would conflate the layers and make L1's CI
  OS-specific.
- **Skip SC-L1.2 / SC-L1.4 until L3 (rejected).** The proxy-correctness half
  (door works, bypass-of-door fails when egress denied) is real, valuable,
  and testable now. Skipping loses regression cover on the proxy itself.
- **Assert SC-L1.2 with no confinement and claim it passes (rejected).**
  Dishonest green — the exact failure the SPEC forbids.

## Consequences

- SC-L1.2 and SC-L1.4 are automated and green now, with docstrings that draw
  the L1/L3 line explicitly. A reader of the test knows precisely what is
  controlled by L1 and what is borrowed from a (simulated) L3.
- SC-L2.5 is automated and green now, asserting the documented limit.
- A deferred-need is recorded: **`l3-os-egress-denial`** (and the per-OS
  sandbox scenarios SC-L3.1/3.2) — the production replacement for the test
  shim. The L1 proxy is already the allow-listed egress that sandbox will
  permit, so no L1 rework is implied — only the wall is added around it.
- The test shim is clearly marked test-only and never importable by
  production code (lives under `tests/`), so it cannot be mistaken for an
  enforcement mechanism.
