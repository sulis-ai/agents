# Sizing — harden-agent-execution-boundary (L1 + L2)

> Computed at draft-architecture. Subsequent skills read this rather than
> recompute. Refresh if SPEC scenarios or scope change.

## Inputs

Brownfield-equivalence basis (code + SPEC). Only L1 + L2 are in scope; L3 is
deferred and excluded from this count.

## sFPC (simplified Function Point Count)

| Element | Count | Items |
|---|---|---|
| ILF (internal data) | 2 | the per-change allowlist (scope-resolver state); the proxy egress-audit record |
| EIF (external interfaces) | 1 | the open web (the proxy's outbound leg) |
| EI (mutating ops) | 4 | file-tool write / move / remove + proxy fetch (state-changing on disk / network) |
| EO (deriving ops) | 4 | scrub-decision, scope-decision, data-framing wrap, allowlist resolution |
| EQ (retrieving ops) | 2 | file-tool read; proxy search/fetch read-back |
| **sFPC** | **13** | → tier **M** band (11–30) |

## ASR count (architecturally significant requirements)

| Source | Count | Items |
|---|---|---|
| NFRs | 3 | cross-platform byte-identical (L1+L2); canonical-path resolution; preserve local loop / open-web research |
| Integrations | 2 | agent → proxy; file-tool → scope-resolver |
| In-scope scenarios as ASRs | 9 | SC-L1.1–1.4, SC-L2.1–2.5 |
| Cross-cutting policies | 1 | fail-closed default (both layers) |
| **ASR** | **10** | → tier **M** band (6–15) |

## Tier

**M** (sFPC 13 → M; ASR 10 → M; agree). One bounded context (the agent
execution boundary). Two independent sub-components (L1, L2) buildable in
parallel.

## Per-pillar coverage (from existing code)

| Pillar | Coverage | Consequence for the TDD |
|---|---|---|
| **Form** | Partial — `_session_manager` adapter/manager seam exists; `_worktree_safety` scope-guard pattern exists; `_anonymiser` scrub patterns exist. No proxy, no scoped file-tool surface. | Fill the gap: new proxy module + new file-tool module + scope-resolver extension; reference the existing seam/pattern, do not restate. |
| **Armor** | Partial — secret-scrub patterns exist (`_anonymiser`); private-IP scrub exists. No egress mediation, no fail-closed file surface. | Extract the scrub primitive; add fail-closed policy at both layers. |
| **Proof** | Good — `test_worktree_safety.py` (example + hypothesis property) is the template for L2; `_anonymiser` has a mature test suite for the scrub patterns. | Mirror the worktree-safety test shape for L2; add honest-confinement harness for L1. |

## File-count sanity check

`_session_manager/` ≈ 20 files; `scripts/` large. The change adds ~3 new
modules + extends 1. sFPC/ASR (tier M) is the driver, not file count — no
mismatch to surface.

## Decision

Tier **M**. TDD target ≈ 250–400 lines. ADR target: 4–6 (5 produced — each
locks a decision affecting >1 component or rejecting a viable alternative).

> **Confirmed by:** {founder/orchestrator at pre-write announcement}
