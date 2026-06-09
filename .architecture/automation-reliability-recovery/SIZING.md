# SIZING — automation-reliability-recovery (provider-neutral reliability layer)

> Computed by `/sulis:draft-architecture` on 2026-06-08 from
> `.changes/feat-automation-reliability-recovery.SPEC.md` and the existing
> `plugins/sulis/scripts/_session_manager/` platform (back-integrated from
> main). Mode: **brownfield-with-spec** — extend the session-manager behind
> its existing `ProviderAdapter` seam. Subsequent SEA skills read this file
> rather than recomputing.

## Tier

| | Value |
|---|---|
| **sFPC** (simplified function point count) | ~5 (new surface only) |
| **ASR count** (architecturally-significant requirements) | ~9 |
| **Computed tier** | **M** (ASR-driven; take the higher of the two axes) |
| **Confirmed tier** | M |
| **Bounded contexts** | 1 (sits around the existing session lifecycle; no new context) |

### sFPC derivation (new surface only)

| Element | Count | Items |
|---|---|---|
| ILF (internal data) | 0 | Non-goal: no new durable store. Paused-run state persists *through* the existing log + messages store. |
| EIF (external interfaces) | 0 | Non-goal: no new outbound dependency. The layer **observes** the existing `events.py` error stream; it adds no new channel. |
| EI (mutating / inputs) | 2 | The recovery driver's retry-resubmit; the per-provider re-auth trigger. |
| EO (derived / outputs) | 2 | The classification verdict (recovery class); the re-login notification payload. |
| EQ (simple reads) | 1 | Read the retry-budget config (defaulted, structured for later per-run/per-provider). |
| **New total** | **~5** | EI + EO + EQ |

### ASR derivation

1 retry-budget policy (backoff + jitter + cap + reclassify-on-exhaustion)
+ 3 recovery-class definitions (transient-blip / dead-end / login-expired)
+ 1 pause/resume isolation (reuse ADR-002, never lose the run's place)
+ 1 provider-neutral seam constraint (classifier + policy depend on no adapter)
+ 1 observe-in-existing-stream (every action visible in `events.py`)
+ 1 no-new-error-stream / reuse error-code constants
+ 1 must-not-change turn-complete / one-in-flight semantics
= **~9**. ASR (not feature count) drives the tier: the weight is the
**recovery correctness around a live lifecycle** (no fabricated completion,
no lost place, no budget burned on a dead-end), not the line count.

## Per-pillar addressable scope

The session-manager already has a mature hexagonal core (ports/adapters,
dependency-inward), a three-category typed error model, an enforced state
machine, a restart-on-death lifecycle (the recovery-around-the-core
precedent), and a contract/fake/parity test discipline. We reference what
exists and fill only the gap this layer opens.

| Pillar | Coverage | What we do |
|---|---|---|
| **Form** | **Covered** (`events.py` vocabulary, `adapter.py` Protocol seam, `manager.py` composition root, `lifecycle.py` recovery-around-the-core pattern) | Reference the existing seam. Add a **provider-neutral classifier** (pure domain) + a **recovery driver** (mirrors `LifecycleManager`'s around-the-core shape) + a **thin additive method on the adapter Protocol** (detection + re-auth). No structural rework; no seam widening beyond the thin additions. |
| **Armor** | **Partially covered** (typed errors, state machine, restart-on-death lifecycle, recovery budget for *process* death) | Fill the gap: a **turn-level** retry policy (exponential backoff + jitter + ~10–15-min budget cap, then reclassify dead-end) — the AP-05/AP-06-class hardening applied to API-failure not just process-death; the pause→notify→resume flow for login-expired using ADR-002's resume; every action surfaced as an `error`/`result` Event (no new stream). |
| **Proof** | **Partially covered** (contract test + fake-vs-adapter parity + deterministic sleep-free maintenance tests) | Fill the gap: classifier truth-table tests (provider-neutral, no Claude dependency); a **fake clock** so backoff/budget are deterministic (no `sleep`); a recovery-driver test for each class; a Claude-adapter detection test for the 401/403→login-expired mapping; a pause/resume no-fabricated-completion test reusing the lifecycle's resume discipline. |

## File-count sanity check

`_session_manager/` is ~16 source modules, deeply layered (events → adapter
→ session → state → lifecycle/guards/maintenance → manager → socket_server).
The layering, not the count, justifies tier M. The reliability layer is
~2–3 new modules (classifier, recovery driver) + a thin additive method on
the existing adapter Protocol + a defaulted policy value object. Consistent
with the ASR-driven tier.

## Notes

- No `.context/{project}/INDEX.md` exists. The existing
  `.architecture/autonomous-delivery-environment/` ADRs (ADR-001..ADR-009)
  are referenced as **external prior art** — this change's ADRs start at
  ADR-001 in its own `adrs/` namespace and never renumber the ADE set.
  Especially load-bearing: ADE ADR-002 (session-bridge resume/spawn — the
  resume path this change reuses), ADR-003 (chat the single sanctioned
  write path), ADR-005 (one coherent surface — the re-login notification
  rides it).
- The one founder decision already made (retry policy = persistent
  exponential backoff with jitter, ~10–15-min cap) is recorded as ADR-002
  with the structure that lets it become a per-run/per-provider setting
  later without redesign.
- `founder_facing: false` — backend reliability layer; the re-login
  notification surfaces to the operator via the platform's existing message
  surface (ADE ADR-005), not a new screen.
