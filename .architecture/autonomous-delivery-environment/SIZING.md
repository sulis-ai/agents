# SIZING — autonomous-delivery-environment (the Sulis app: drive a change)

> Computed by `/sulis:draft-architecture` on 2026-06-03 from the SRD/NFR
> artifacts at `.specifications/autonomous-delivery-environment/` and the
> existing codebase at `apps/cockpit/`. Mode: **brownfield-with-spec**
> (extend an existing app). Subsequent SEA skills read this file rather
> than recomputing.

## Tier

| | Value |
|---|---|
| **sFPC** (simplified function point count) | 12 (new surface) |
| **ASR count** (architecturally-significant requirements) | 26 |
| **Computed tier** | **L** (driven by ASR) |
| **Confirmed tier** | L |
| **Bounded contexts** | 1 (the Sulis app reaching one data seam) |

### sFPC derivation (new surface only)

| Element | Count | Items |
|---|---|---|
| ILF (internal data) | 0 | NFR-DATA-01: no new persistent store. Chat exchanges land in the existing transcript model. |
| EIF (external interfaces) | 1 | The Claude session bridge (stream-json over the SessionBridge port) — the one new outbound dependency. |
| EI (external inputs / mutating) | 1 | Chat relay send (the app's first and only write path). |
| EO (external outputs / derived) | 5 | Board (stage-grouped), read-time stage status, brain-entities view, search results over content, rendered preview. |
| EQ (external inquiries / simple reads) | 5 | Reused existing reads (changes, transcript, tree, file, diff, contract) — counted as covered, not new. |
| **New total** | **12** | EI + EIF + EO (the genuinely new surface) |

### ASR derivation

19 NFRs + 1 new integration (session bridge) + 5 negative requirements
(FR-N1..N5, each a MUST-NOT safety policy) + 1 cross-cutting policy
(the single-sanctioned-write-path read-only gate extension) = **26**.

The architecturally-significant weight of this change is **not** its
feature count — it is the safety surface around the first write path
(session binding, resume/spawn isolation, no-silent-loss, partial-reply
preservation, no-fabricated-completion). That is why ASR drives the tier
to L while sFPC alone would read M.

## Per-pillar addressable scope

The cockpit already has a mature hexagonal architecture, a read-only gate,
and a contract/adapter/fake test discipline. We reference what exists and
fill only the gaps the new write path opens.

| Pillar | Coverage | What we do |
|---|---|---|
| **Form** | **Covered** (ports/adapters/seam established; `ChangeStoreReader`, `RecreateRunner`, shared wire types) | Reference the existing seam. Add **one new port** (`SessionBridge`) and its adapter; add new read projections behind the existing port pattern. No structural rework. |
| **Armor** | **Partially covered** (localhost bind, signal-0 liveness probe, read-only gate, typed error envelope all exist) | Fill the gap the write path opens: session-to-change binding guard, resume/spawn isolation, one-in-flight lock, timeouts on the bridge, structured no-body logging, read-only-gate extension to allow-list exactly the relay. |
| **Proof** | **Partially covered** (contract test + fake-vs-adapter parity + supertest route tests + Vitest component tests + axe e2e all exist) | Fill the gap: a **recorded-bridge fixture** (live / resume / spawn / mid-step) so the relay + session resolution are testable in CI without a live agent; chat component tests; the read-only-gate test extension. |

## File-count sanity check

`apps/cockpit/` is ~90 source files (excluding node_modules), deeply
layered (ports → adapters → routes → lib; client api-hooks → components →
pages → layouts). The layering, not the count, justifies tier L. No
generated-code inflation. Consistent with the ASR-driven tier.

## Notes

- No `.context/{project}/INDEX.md` exists; the existing cockpit ADRs
  (ADR-001..ADR-008) are referenced verbatim from source comments as
  **external prior art** — new ADRs for this change start at ADR-001 in
  this change's own `adrs/` namespace and never renumber the cockpit MVP set.
- The SRD already encodes most engineering-internal defaults under
  `## Assumptions & decided-by-default` (SSE transport, error envelope,
  resume-vs-spawn is the app's call, read-only-gate extension, code home).
  The TDD honours these and records the load-bearing ones as ADRs.
