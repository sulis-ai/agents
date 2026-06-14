# ADR-001 — L1 builds the safe door now; L3 makes it the only door later

> **Status:** accepted
> **Date:** 2026-06-13
> **Change:** CH-E22SX6 · harden
> **Affects:** L1 (proxy + safe-fetch tool), the L1 scenario tests, the L3 follow-on scope

## Context

The SPEC's L1 acceptance includes *"the agent has **no raw outbound
socket**; the proxy is the only door"* (SC-L1.2 — no raw egress). That
property — actually denying the agent process the ability to open an
arbitrary socket — **cannot be enforced in pure userland**. A Python
program cannot remove its own (or a child's) ability to call `socket()`.
Removing raw egress requires an OS-level network policy: a Seatbelt
`(deny network*)` profile on macOS, seccomp/network-namespace on Linux,
AppContainer/WSL2 on Windows — and that *is* L3, which this change defers.

If we pretend L1 enforces no-egress, every L1 scenario test that "passes"
in CI is dishonest: nothing stopped the raw socket, so SC-L1.2 would be
green by assertion, not by control. The SPEC is explicit that this is the
exact failure mode to avoid ("not silently green").

## Decision

**Split L1 into what it BUILDS now and what its PRODUCTION ENFORCEMENT
depends on, and make the tests honest about the seam.**

**L1 builds now (all buildable + testable in userland):**

1. The **proxy service** — an out-of-process fetch/search gateway.
2. The **safe-fetch / safe-search tool** the agent calls (the only
   sanctioned outbound path the agent is *told about*).
3. **Content-as-untrusted-data framing** (spotlighting) on returned content
   (ADR-003).
4. **Outbound secret-scrub** before DNS resolution (ADR-002).
5. The **Rule-of-Two secret-exclusion** — secrets are configured out of the
   fetch path's scope.

Until L3 lands, **the proxy is the safe *door*, not yet the *only* door.**
L1 in this phase is, operationally, a **guardrail of the same class as
L2**: it makes the safe path available and the unsafe path
unattractive/unconfigured, but a hijacked process can still open a raw
socket. The wall is L3's job.

**L1's production enforcement depends on L3** — explicitly recorded as the
follow-on. The proxy is on L3's critical path anyway (the sandbox profile
allow-lists the proxy as the one permitted egress), so building it now is
not wasted (SPEC non-goal: "the proxy is on the critical path of that
future anyway").

**The scenario tests confine the process *in the test harness* (ADR-005),
not in production**, and the test names + docstrings say so. SC-L1.2 runs
the fetch under a test-local no-raw-egress shim and asserts the shim
refuses a direct connect while the proxy connect succeeds — proving the
*proxy half* (the door works; bypass-of-the-door fails when egress is
denied). The test asserts the **control L1 owns** (a correct proxy that is
the sanctioned path) under the **confinement L3 will own** (the egress
denial), and the docstring names L3 as the owner of the production
denial.

## Alternatives considered

- **Claim L1 enforces no-egress in userland (rejected).** Impossible; would
  make SC-L1.2 a false green. This is precisely the "no false sense of
  security" failure the SPEC's throughline forbids.
- **Defer all of L1 until L3 is built (rejected).** The proxy, scrub,
  data-framing, and Rule-of-Two are universal, OS-independent, and testable
  now; they remove the *exfil channel's content* even before the socket is
  walled. Deferring loses the no-regret value and the L3 critical-path
  prep. CP — ship the boring buildable part now.
- **Build a userland egress interceptor (monkeypatch `socket`) and call it
  the wall (rejected).** A monkeypatch is bypassable by any subprocess and
  by `ctypes`; it would be a band-aid masquerading as a wall. We use exactly
  this technique **only inside the test harness** (ADR-005) where its job is
  to *simulate* L3's denial, never shipped as production enforcement.

## Consequences

- The L1 WPs deliver a real, tested proxy + tool + scrub + framing now;
  SC-L1.1, .3, .4 are fully proven in userland; SC-L1.2 is proven *as the
  proxy-correctness half* under test-harness confinement.
- A clear deferred-need is recorded: **`l3-os-egress-denial`** — the OS
  sandbox that makes the proxy the only door. Until it lands, the
  threat-model doc states plainly that L1 is a door, not yet a wall.
- No production code claims to deny raw egress. The honest boundary is in
  the threat-model docstring and the SC-L1.2 test name.
