# Cockpit Board Refresh — Sizing

> **Date:** 2026-06-09
> **Mode:** Brownfield (refresh of an existing, well-structured cockpit board).
> **Source of numbers:** code (`apps/cockpit/`) + the signed-off design
> (`.design/cockpit-board-refresh/`), not an SRD.
> **Confidence note:** ASRs are inferred from the design's NFR text
> (accessibility, responsive, reduced-motion) + observed token/observability
> conventions in the codebase — flagged inferred, not SRD-confirmed.

## Functional complexity — sFPC

| Element | Items | Count |
|---|---|---|
| ILF (data stores changed) | enriched `Change` wire shape; `tokens.css` dark block | 2 |
| EIF (external/outbound reads) | CI/test-state read; rigor-for-stage artifact read (worktree files) | 2 |
| EI (mutating ops) | none — board is read-only; start button navigates (no mutation) | 0 |
| EO (derived outputs) | `needsAttention` onto feed; `health` verdict; liveness "working" sub-state | 3 |
| EQ (simple retrieves) | board feed read; lane render | 2 |
| **sFPC** | | **9** |

sFPC 9 → tier **S** band (≤10).

## Architecturally-significant requirements — ASR

| ASR source | Items | Count |
|---|---|---|
| NFRs (inferred from design) | WCAG AA light+dark; reduced-motion; touch ≥44px; keyboard/focus preserved | 4 |
| Integrations | CI test-state; rigor-for-stage artifacts | 2 |
| MUCs | none | 0 |
| Cross-cutting policies | 3 responsive breakpoints; dark elevation token system; read-only observability discipline | 3 |
| Hard data constraints | health verdict must be honestly server-derived (no client invention) | 1 |
| **ASR** | | **10** |

ASR 10 → tier **M** band (6-15).

## Tier decision

sFPC says S, ASR says M. **Take the higher → tier M.** The board-refresh's
weight is in its *cross-cutting* requirements (accessibility, responsive,
dark-mode elevation), not in new data or operations — exactly what ASR
captures and sFPC under-counts. No multiple bounded contexts → not XL.

**File-count sanity check:** the change touches ~8-10 source files in one
app (`apps/cockpit/`). Consistent with tier M; no mismatch to surface.

## Per-pillar coverage (addressable scope)

| Pillar | Coverage | Consequence for the TDD |
|---|---|---|
| **Form** | **Fully covered.** Ports & adapters, component tiers, the typed-client seam, `ChangeStoreReader`, the six-column board IA — all established and documented in prior cockpit TDDs (ADR-005/008/009). | 1-line reference + only the *new* components named. No re-derivation of hexagonal structure. |
| **Armor** | **Mostly covered, narrow gap.** Board is read-only (no new external mutating calls, no new secrets, no new service-to-service traffic). Observability discipline (no reply-body leakage, NFR-SEC-03) is established. **Gap:** the new rigor-for-stage / CI-state reads are filesystem reads that must stay best-effort + read-only like `detectOpenBlocker`. | Fill the gap (best-effort read discipline); reference the rest. |
| **Proof** | **Partially covered.** The contract-test + in-memory-adapter + jest-axe/Playwright-axe discipline is established (WPF-06/10). **Gap:** new derivations (`health`, enriched feed, `working` sub-state) need their own pure-function tests + the card/lane need fresh axe coverage in light AND dark. | Fill the per-derivation + per-surface test gaps; reference the discipline. |

## Targets (tier M, scope-shrunk)

- **TDD target:** ~250-400 lines (tier M baseline), shrunk by full Form
  coverage toward the lower end. Circuit breaker fires if >1.5× (>600).
- **ADR target:** 3-5 new ADRs (tier M). Numbering starts fresh — this
  project (`cockpit-board-refresh`) has no prior External ADR Registry of
  its own; sibling change-folders keep independent ADR sequences.
- **WP target:** atomic; one logical change each. Expect ~7-9.

## Confirmation

Tier **M** computed; per-pillar coverage as above. Awaiting no override —
the founder's instruction was "keep it proportionate", which this honours
(reference the covered Form pillar; only write the deltas).
