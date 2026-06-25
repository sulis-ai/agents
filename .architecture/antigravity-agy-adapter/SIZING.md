# Sizing — Antigravity (`agy`) provider adapter

> **Change:** CH-M7WSQ4 · **Project:** antigravity-agy-adapter
> **Computed:** 2026-06-25 · from the spec + recon (greenfield-on-existing-seam)

## Functional complexity

| Element | Count | Items |
|---|---|---|
| ILF (internal stores) | 0 | No new persistent store; resume handle rides the existing `SessionSpec`. |
| EIF (external integrations) | 1 | The `agy` CLI (Google Antigravity v1.0.11) — one new external process touch. |
| EI (mutating ops) | 1 | `spawn_argv` → launch an interactive agy session. |
| EO (deriving ops) | 1 | resume-handle → `--conversation`/`--continue` mapping. |
| EQ (retrieving ops) | 1 | capabilities query (`supports_resume` etc.). |
| **sFPC** | **4** | ILF 0 + EIF 1 + EI 1 + EO 1 + EQ 1 |

## Architecturally-significant requirements (ASR)

| ASR | Source | Note |
|---|---|---|
| One external platform integration | spec scope #1 | The agy CLI process touch. |
| Permission/sandbox posture (don't blanket `--dangerously-skip-permissions`) | spec constraint | A guardrail decision → Platform Contract + ADR. |
| Provider registration must be additive (Claude path byte-unchanged) | spec non-goal | Cross-cutting wiring constraint. |
| Pre-authenticated auth (Google Sign-In) precondition | spec constraint | Operational precondition, not code. |
| **ASR count** | **4** | |

## Tier

| | sFPC | ASR | Tier |
|---|---|---|---|
| Computed | 4 (≤10) | 4 (≤5) | **S** |

File-count sanity check: the change adds **one** source file + a registration edit. Consistent with tier S.

## Per-pillar addressable scope

| Pillar | Coverage | Action |
|---|---|---|
| **Form** | Fully covered | The `ProviderAdapter` Protocol + `SessionSpec`/`Capabilities` seam already exists (`adapter.py`, SESSION_MANAGER_CONTRACT §2.4). **Reference, don't restate** — the adapter is an EXPAND-Create against the owned port. |
| **Armor** | Partially covered | Permission/sandbox posture for agy is **new** (the one genuine hardening decision) → fill in the TDD + Platform Contract + ADR-003. Sidecar-read / no-shell-parse / ULID-validation primitives are inherited from the Claude pty path unchanged. |
| **Proof** | Partially covered | The pty conformance + argv-shape test posture exists (`test_claude_pty_adapter.py`); mirror it for agy, drive the real binary for read-only introspection, add a no-regression assertion on the Claude path. |

## Notes

- This is an EXPAND-Create (a new adapter for an owned port), **not** a SUBSTITUTE-Wrap of the agy CLI (the agy CLI is *called by* `spawn_argv`; the public face is the `ProviderAdapter` Protocol we own — §2.4 discriminator).
- The Claude pty adapter's richer behaviour (Remote Control default-ON, deterministic `--session-id` pinning via `_change_session`) is **deliberately NOT mirrored** for agy in Phase 1: agy has no `--remote-control` flag, and its conversation-id model is agy-owned (`--conversation <id>`), not a Sulis-derived UUID we can pin pre-spawn. Mirroring those would be speculative over-build. See TDD §Form and ADR-002.
- TDD target for tier S: ≤120 lines of substantive design (excluding the Platform Contract artifact, which is its own deliverable). ADR maximum for tier S: 3.
