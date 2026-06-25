# Sizing — portable-agent-context (CH-GJ9KQR)

> **Generated:** 2026-06-24 · **Mode:** brownfield-equivalent (derived from
> spec + recon + code probe; no SRD in `.specifications/`). **Tier: M
> (confirmed).**

## Functional complexity (sFPC)

Derived from the spec's 3-part scope + the code probe of
`plugins/sulis/scripts/_session_manager/` and `apps/cockpit/`.

| Element | Count | Items |
|---|---|---|
| **ILF** (internal stores) | 3 | (1) durable append-only message log store; (2) per-thread structured memory/payload snapshot (versioned); (3) the thread/session index record |
| **EIF** (outbound external) | 0 | None in scope — the platform communication-service call is **deferred/parked** (ADR-002); the Claude-transcript read is being **displaced**, not added |
| **EI** (mutating ops) | 2 | (1) append-message; (2) regenerate/checkpoint structured summary |
| **EO** (derived outputs) | 2 | (1) assemble tiered context payload (lean/standard/full); (2) generate structured summary |
| **EQ** (retrievals) | 3 | (1) get rich memory/payload; (2) get raw message log (full or slice — the discovery seam); (3) get thread record |

**sFPC = 3 + 0 + 2 + 2 + 3 = 10–11** → tier M lower bound.

## Architecturally-significant requirements (ASR)

| # | ASR | Source |
|---|---|---|
| 1 | Append-only + ordered integrity (audit record, never rewritten) | spec Constraints |
| 2 | Token-budget tiers — hard window constraint | spec Constraints / Acceptance |
| 3 | Provider-agnostic / vendor-neutral shape | spec Acceptance (load-bearing) |
| 4 | No secret leakage — honour existing anonymiser/redaction posture | spec Constraints |
| 5 | Structured summary freshly regenerated at checkpoint boundaries | spec Constraints |
| 6 | **Provider-independent resume** — works with provider transcript unavailable | spec Verification Plan (the key journey) |
| 7 | Contract-compatibility with the platform thread-sdk shape | Working Set platform finding |

**ASR count = 7** → tier M (6–15).

**Both axes agree: tier M.** File-count sanity check: the change touches ~2
new modules + the cockpit seam + a contract — consistent with tier M.

## Per-pillar addressable coverage

No `.context/{project}/INDEX.md` exists. Coverage assessed from the code probe.

| Pillar | Coverage | Consequence for TDD depth |
|---|---|---|
| **Form** | Partial | Reuse `events.Event` (provider-neutral vocab) + `ProviderAdapter` seam + brief injection. New: the durable store + assembler ports. Fill the gap. |
| **Armor** | Partial | Redaction posture (`_secret_patterns`) + `spawn_env` credential exclusion exist and are reused. New: at-rest integrity of the durable log + redaction-on-write. Fill the gap. |
| **Proof** | Uncovered (for the new surface) | The new store + assembler + discovery seam need fresh contract tests + the provider-independent-resume integration test. Full tier-M section. |

## Targets (tier M)

- TDD target ≈ 250–500 lines. ADRs expected: 4–6 (the brief mandates ≥4).
- Circuit breakers: flag if TDD > 750 lines or ADRs > 8.

## Decision

Tier **M**, confirmed. Author the TDD at tier-M depth; reference existing
seams (Respect-Don't-Restate) rather than re-deriving them.
