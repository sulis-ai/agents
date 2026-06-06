---
id: WP-P08
title: "Agree the change-origin shapes + the origin seam (contract)"
kind: contract
contract_type: data
feature: provenance-and-origin
change_id: 01KT500K2JTE2EGW6TPPQ4D4VN
primitive: EXPAND-Create
group: expand
estimate: 3h
blast_radius: low
dependsOn: [WP-P01]
adr: [ADR-012, ADR-013]
verification:
  adapter: backend
  na: true
  justification: "Contract WP — defines the Origin shapes + the OriginAttribution port + stubs; conformance verified by P09/P10/P13 against these examples and the shared contract test (CF-07)."
estimated_token_cost: { input: "~20k", output: "~14k" }
status: pending
---

## Context
The contract-first seam for Slice 2 (CF-01/02/03). Defines the `Origin` wire
shapes, the **`OriginAttribution` port** (ADR-012), the three-category errors,
and stubs — before any implementation — so the inferred adapter (P09), the
frontend (P10), and the recorded adapter (P13) build against one agreed contract.

## Contract (the shapes + port this WP pins)
```ts
type Origin =
  | { kind: "autonomous"; run: { runId: string; workflow: string | null; outcome: string }; confidence: number | null; attribution: Attribution }
  | { kind: "assisted"; conversation: { conversationId: string; turn: number; summary: string | null }; attribution: Attribution }
  | { kind: "unknown"; attribution: Attribution };
type Attribution = "inferred" | "recorded";   // the honesty flag — ALWAYS present (TDD §3.3)

interface OriginView {            // GET /api/changes/:id/origin (+ ?path=)
  changeId: string;
  path: string | null;            // null = change-level origin
  origin: Origin;
}
```
**Port (ADR-012):** `OriginAttribution { originFor(change, path?): Promise<Origin> }`
— domain-owned; two adapters (`InferredOriginAttribution`, `RecordedOriginAttribution`)
satisfy **one** contract test.

**Errors (CF-03):** `NOT_FOUND` (unknown change). `unknown` is **not** an error —
it's a valid `Origin.kind` (honest "Origin-unknown"). Recorded **overrides**
inferred (ADR-012) — pinned as the route-level precedence rule.

**Stamp metadata (ADR-013, for P12/P13):** the commit trailer shape
`Sulis-Origin: autonomous; run=<ulid>; confidence=<0..1>` /
`Sulis-Origin: assisted; conversation=<id>; turn=<n>`; sidecar fallback
`.sulis/origin/<sha>.json` mirrors the same fields.

## Stubs (CF-04 — happy + empty + error)
- autonomous+inferred (a commit in a run window); assisted+inferred (a commit near a turn); unknown; autonomous+recorded (a stamped commit); `NOT_FOUND`.

## Definition of Done
### Red
- [ ] `shared/api-types.ts` lacks `Origin`/`OriginView`; a reference fails type-check.
### Green
- [ ] `openapi.yaml` + `shared/api-types.ts` carry `Origin`/`OriginView` + the five stubs; `tsc` + openapi-lint pass.
- [ ] `ports/OriginAttribution.ts` declares the port; the contract-test skeleton exists (shared by P09/P13).
### Blue
- [ ] `attribution` is non-optional on every `Origin` variant (the honesty flag can't be forgotten — TDD §3.3).
- [ ] The trailer/sidecar shape is pinned as a shared constant for P12/P13 (CF-11).
- [ ] Recorded-overrides-inferred precedence recorded in the openapi description (ADR-012).
