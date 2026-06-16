# Sizing — use-change-id-not-handle

> **Computed:** 2026-06-11 · **Mode:** brownfield (numbers derived from the
> resolution surface, not the whole repo) · **Scope:** change-identity
> resolution in `plugins/sulis/scripts/sulis-change`, `plugins/sulis/scripts/_wpxlib.py`,
> and `apps/cockpit/server/` recreate path.

## Tier: **S** (confirmed)

This is a focused `fix` to an existing, well-factored resolution surface. The
safe-matcher substrate (`_changes_matching_handle`, `_emit_ambiguous_match`,
`_select_change_id_refusing_conflict`) already exists from #101/#274; the work
extends it to the remaining two leaks (CLI `recreate` by id, cockpit passing
change_id) and reconciles one dead resolver rung. Not a new subsystem.

## sFPC (simplified Function Point Count)

| Element | Count | Notes |
|---|---|---|
| ILF (internal stores) | 1 | the change store (`~/.sulis/changes/{change_id}/`: `change.json` record + `state.json`) — already keyed by change_id |
| EIF (external systems) | 0 | no third-party platform (SPEC Constraints: internal git + local state + cockpit server + CLI only) |
| EI (mutating ops) | 3 | `recreate` (materialise worktree), `mark-shipped`, `nuke` |
| EO (derived outputs) | 1 | the disambiguation candidate list (handle + name + branch) |
| EQ (retrieval ops) | 2 | resolve-by-id helper; session binding lookup (focus) |
| **sFPC** | **7** | tier **S** (≤10) |

## ASR count (architecturally-significant requirements)

| ASR | Source | Inferred? |
|---|---|---|
| Resolve a change by its full id, never the non-unique handle | SPEC Scope 1 | documented |
| Destructive verbs (ship/nuke) must refuse rather than guess on collision | SPEC Scope 2 / Acceptance | documented |
| Reconcile mint (tail) vs lookup (head) mismatch | SPEC Scope 3 | documented |
| Disambiguation prompt on a genuinely ambiguous founder-typed handle | SPEC Scope 4 | documented |
| Backward-compatible resolution (unambiguous handle still resolves) | SPEC Constraints | documented |
| Regression coverage against the live 26-collision state | SPEC Scope 5 | documented |
| **ASR count** | **6** | tier **S** (≤5) → one over; take the higher signal but both land at/near S |

sFPC 7 → S, ASR 6 → boundary S/M. Take **S** — the change reuses an existing
resolution substrate rather than introducing new architecture. File-count sanity
check: ~6 source files touched, consistent with tier S.

## Per-pillar addressable coverage

| Pillar | Coverage | Action |
|---|---|---|
| **Form** | Partial | Hexagonal `RecreateRunner` port + `ChangeStoreReader` port already exist (cockpit), and the CLI has a clean resolver layer. The port's method signature (`recreate(handle)`) is the structural defect to correct → `recreate(changeId)`. Fill the gap; don't restate the architecture. |
| **Armor** | Partial | `changeHandleGuard` (shape-guard), bounded recreate timeout, spawn-not-exec, ambiguity-refusal already present. Gap: identity-by-non-unique-key. Fill. |
| **Proof** | Partial | `test_sulis_change_safe_resolution.py` (matcher unit tests), `recreate-on-demand.test.ts`, `contract` tests exist. Gap: no end-to-end colliding-handle regression across all four verbs; no cockpit-passes-id test; no `recreate --change-id` test. Fill. |

No `.context/{project}/INDEX.md` present, so Respect-Don't-Restate operates off
the in-repo TDDs/ADRs of sibling changes (the safe-resolution work is documented
in code comments citing #101/#274, not a standalone ADR registry). New ADRs for
this change start at ADR-001 (no External ADR Registry to collide with).

## Decided-by-default (journal)

- Tier S confirmed silently — convention (matches the focused-fix shape). No
  founder-facing consequence.
- TDD target ≈ 60–120 lines (tier S). Verification Plan section mandatory.
- ADR expectation: 1–2 (the `recreate(changeId)` port signature change is the
  one decision affecting both CLI and cockpit).
