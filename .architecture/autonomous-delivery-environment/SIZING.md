# SIZING — autonomous-delivery-environment (the Sulis app: drive a change)

> Computed by `/sulis:draft-architecture` on 2026-06-03 from the SRD/NFR
> artifacts at `.specifications/autonomous-delivery-environment/` and the
> existing codebase at `apps/cockpit/`. Mode: **brownfield-with-spec**
> (extend an existing app). Subsequent SEA skills read this file rather
> than recomputing.

## Tier

| | Value |
|---|---|
| **sFPC** (simplified function point count) | 12 original + ~7 expanded ≈ 19 (new surface) |
| **ASR count** (architecturally-significant requirements) | 26 original + ~12 expanded ≈ 38 |
| **Computed tier** | **L** (driven by ASR; still below the XL threshold) |
| **Confirmed tier** | L (re-confirmed after the concierge / discovery / multi-product expansion) |
| **Bounded contexts** | 1 (the Sulis app reaching one data seam; the expansion rides the existing seam + bridge) |

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

### ASR delta — expanded scope (concierge / discovery / multi-product)

The expansion adds ~12 ASRs and ~7 sFPC, keeping the change tier-L (not XL —
still one bounded context, all riding the existing seam + bridge):

- **6 NFR-DISC policies** (bounded search, idempotent mint, validated-emitter
  writes, confirm gate, concierge containment, durable config) — each a
  cross-cutting safety policy on the two new consequential acts.
- **6 negative requirements** (FR-N6..N11) — confirm-before-consequential,
  bounded search, concierge-coordinates-only, all-activity-in-a-change,
  no-dangling-repo-config, no-partial-config.
- **4 new integrations** — the headless discovery agent (reuses the bridge),
  the discovery skills, repo find-or-create (`git`), and the
  Project→Product server-side roll-up.

The expansion is weighted by **reuse**: the bridge (ADR-002), the discovery
skills, the spine emitters, the classifier, and the confirm discipline all
already exist — the new work is orchestration + Product-scoping, not new
infrastructure. 4 new ADRs (006–009) record the reuse decisions and the one
founder-owned call (repo-create location).

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
