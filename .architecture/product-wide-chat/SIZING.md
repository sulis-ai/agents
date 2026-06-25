# Sizing — product-wide-chat (CH-G3Y4RM)

> **Computed:** 2026-06-25 · **Mode:** greenfield-architecture (visual contract signed; no prior TDD/context/intelligence)
> **Source artifacts:** `.changes/create-product-wide-chat.SPEC.md`, `.changes/create-product-wide-chat.RECON.md`, signed visual contract.

## Functional complexity (sFPC)

| Element | Count | Items |
|---|---|---|
| ILF (internal stores owned) | 2 | per-product chat thread (product→thread keying); per-product agent choice |
| EIF (external systems consumed) | 0 net-new | session-manager daemon, thread store, start-from-intent, agy adapter — all already shipped/reused |
| EI (mutating ops) | 4 | post message to product thread; open session with picked provider; guarded agent switch; chat→card create |
| EO (derived outputs) | 2 | per-product transcript/history view; honest active-agent identity + status |
| EQ (simple retrieval) | 2 | resolve active product's thread on open; resolve provider on open |
| **sFPC total** | **~10** | |

## Architecturally-significant requirements (ASR)

| Category | Count | Items |
|---|---|---|
| NFRs | 3 | WCAG AA both themes; honest status (glyph+word, not colour); reduced-motion fallback |
| Integrations | 3 | daemon provider seam; thread store; start-from-intent change-create |
| MUCs (adversarial/guard) | 2 | guarded mid-run agent switch (AI-03); confirm gate before starting work (AI-03) |
| Cross-cutting policies | 2 | provider-on-open seam (replacing hardcode); per-product scope vocabulary |
| **ASR total** | **~10** | |

## Tier

| Axis | Value | Tier |
|---|---|---|
| sFPC | ~10 | S/M boundary |
| ASR | ~10 | M |
| **Confirmed tier** | | **M** (take the higher) |

Multiple bounded contexts? No — single context (cockpit chat). Not XL.

## Per-pillar coverage (no context index present)

| Pillar | Coverage | TDD treatment |
|---|---|---|
| Form | Uncovered (no INDEX.md) | Full M-tier section — but the change is overwhelmingly composition, so Form = reuse map, not re-derivation |
| Armor | Uncovered | M-tier section — the seams (daemon, thread store, change-start) already carry their own hardening; this change adds the provider-on-open + guard primitives |
| Proof | Uncovered | M-tier section — contract test on the new client↔server seam; a11y gates on frontend; integration test closing the seam |

## Notes

- This is a **composition** change. The TDD's job is to map reuse and name the four load-bearing decisions, not to invent a new system. Target length is proportionate to M-tier but trimmed because most building blocks ship already.
- **ADR count expected: 4** (chat-dock layout; per-product thread keying; provider-on-open wiring; chat→card path) — all are load-bearing cross-component decisions named explicitly in the spec's "Open questions for design".
- No External ADR Registry found → new ADRs start at ADR-001.
- Pre-write announcement waived: founder already signed the visual contract and the change is in active build; SEA proceeds to artifacts per the task instruction.
