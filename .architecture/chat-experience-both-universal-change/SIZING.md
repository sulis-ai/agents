# Sizing — chat-experience-both-universal-change (CH-9642DA)

> Computed: 2026-06-27 · Source: `.changes/feat-chat-experience-both-universal-change.SPEC.md`
> + the signed visual contract + grounded code reads of the touched components.

## Tier: S (confirmed)

A self-contained, single-app (cockpit client) frontend change. No new
persistence, no new outbound integration, no new API surface. It re-wires
three existing presentational components to an existing renderer and an
existing state machine, plus one new derived UI state and a CSS de-collision
fix.

## sFPC (simplified Function Point Count) — frontend equivalence

The IFPUG element model maps weakly to a pure-presentation frontend change;
we count the analogous units:

| Element | Count | What |
|---|---|---|
| ILF (internal stores) | 0 | No new client store; reuses `useChatStream` / `useProductChat`. |
| EIF (external reads) | 0 | No new outbound client. Reuses `renderMarkdown`, `groupTurns`, `useTurnSummaries`. |
| EI (inputs/mutations) | 1 | One new *derived* status state (working↔finished) read off the existing lifecycle. |
| EO (derived outputs) | 3 | Universal turn-card render; markdown render in universal chat; the shared status-line component. |
| EQ (retrievals) | 1 | First-sentences summary fallback path for the universal (product) scope. |
| **sFPC** | **5** | → Tier **S** (≤10). |

## ASR (Architecturally Significant Requirements)

| ASR | Source | Significant because |
|---|---|---|
| Reuse the one shared renderer (no new lib) | SPEC Constraints / EP-03 | Forecloses a whole dependency-and-sanitiser surface. |
| No raw colour literals (token-only, theme-aware) | SPEC Constraints | Enforced by an existing characterisation test that must stay green. |
| Honest lifecycle states preserved (FR-19/22/26) | SPEC Constraints | Load-bearing existing behaviour; the de-collision refactor must not regress it. |
| Frontend gate: WPs point at the signed visual contract | SPEC Constraints / #45·UXD-14 | Release gate. |
| Status line is a shared, mutually-exclusive-with-chips slot, a11y live region | Visual contract | Cross-chat shared vocabulary + WCAG AA. |
| **ASR count** | **5** | → Tier **S/M boundary**; the two-axis rule takes **S** (sFPC=5, low addressable scope). |

## Per-pillar addressable scope (from code reads; no `.context/` INDEX present)

| Pillar | Coverage | Action |
|---|---|---|
| Form (structure) | High — hexagonal-ish presentational split already exists (hook = state source of truth; components are pure renders). | Reference existing seam; one small new shared component. |
| Armor (resilience/a11y/security) | High — safe renderer audited; honest-state machine exists; axe tests exist. | Extend axe coverage to the new status line; preserve the safe-render invariant. |
| Proof (verification) | High — Vitest + Testing Library harness, per-component tests, a no-raw-colours characterisation test, axe tests. | Characterisation-first on each touched component, then behaviour tests. |

All three pillars are well-covered, which is *why* this is a compact TDD: it
references the existing seam rather than re-deriving it.

## Notes

- File-count sanity: ~6 source files touched + ~6–8 test files. Consistent
  with tier S.
- No `.context/{project}/INDEX.md` exists for this repo, so this sizing is
  computed from direct code reads, not from a context index.
