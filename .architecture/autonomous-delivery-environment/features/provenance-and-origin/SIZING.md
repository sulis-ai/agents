# SIZING — Files diffs · Provenance · Change origin (feature set of CH-01KT50)

> Computed 2026-06-05 from the approved design artifacts
> (`contracts/visual/{files-redesign,brain-redesign,end-to-end-journey}`),
> the parent TDD, and the live `apps/cockpit/` code. Mode: **brownfield
> extension** of an existing tier-L change.

## Tier

| | Value |
|---|---|
| **sFPC** (new surface only) | ≈ 9 |
| **ASR count** | ≈ 7 |
| **Computed tier** | **L feature** within the tier-L change (S/M-sized on its own, but rides a tier-L safety surface) |
| **Confirmed tier** | L feature — the read-only-gate reconciliation + origin-stamping safety dominate the weight |
| **Bounded contexts** | 1 (the cockpit seam; the stamping write side rides the existing executor/relay paths) |

### sFPC derivation (new surface only)

| Element | Count | Items |
|---|---|---|
| ILF (internal data) | 0 | No new persistent store. Origin stamp is commit-trailer metadata (append-only, on the existing commit), not a cockpit store (NFR-DATA-01). |
| EIF (external interfaces) | 1 | The `OriginAttribution` port (git-log ↔ run ↔ conversation correlation) — one new domain-owned read seam. The numstat read reuses the existing git site (not a new EIF). |
| EI (mutating) | 0 (cockpit) / 2 (write side) | Cockpit-side: none. Write-side: the executor stamp + the relay stamp — counted on the write side, outside the cockpit. |
| EO (derived) | 3 | Files diff counts (numstat rollup), the Provenance digest+lenses projection, the Origin attribution. |
| EQ (simple reads) | 0 new | `…/changed` and `…/brain` are reused, not new. |
| **New total** | **9** | EIF(1) + EO(3) + write-side EI(2) + the 3 client lens surfaces counted as derived UI |

### ASR derivation

3 surfaces × cognitive-load governance (1 cross-cutting policy: CL-01..06 +
worded-status-never-colour-alone) + 1 integration (the origin correlation seam)
+ 2 negative/safety reqs (origin is honestly flagged inferred-vs-recorded;
stamping is non-fatal + adds no new write to the cockpit) + **1 load-bearing
ASR: the read-only-gate reconciliation** (the gate is currently RED; the set
cannot ship green without it) = **≈ 7**.

The architecturally-significant weight is **not** the feature count — it is
(a) keeping the read-only guarantee provable while three new reads land and the
gate is reconciled, and (b) the honesty discipline on inferred origin (never
present an inference as a recorded fact). That is why this rides the tier-L
safety surface rather than reading as a tier-S add.

## Per-pillar addressable scope (Respect-Don't-Restate)

| Pillar | Coverage in the existing change | This set |
|---|---|---|
| **Form** | Fully covered (hexagon, ports, the one git site, the seam) | Reference + the new `OriginAttribution` port + 3 projections |
| **Armor** | Fully covered (read-only gate, git timeout, fail-soft reads) | Reference + reconcile the currently-RED gate (ADR-015) + the honest-inference rule + the no-new-cockpit-write stamping (ADR-013) |
| **Proof** | Fully covered (supertest/Vitest/axe/contract-fake parity) | Reference + extend; one new contract test (OriginAttribution) shared by 2 adapters |

## Notes

- File-count sanity check: ~9 new source files + ~7 extended — consistent with
  an L feature, not an XL one. The reuse ratio is high (numstat extends one
  function; provenance projects an existing read; origin is one port + two
  adapters sharing one contract test).
- No circuit breaker tripped (TDD ≤ 1.5× target; ADRs within tier max; every
  section references rather than restates the parent).
