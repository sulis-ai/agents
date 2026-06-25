---
id: ADR-002
title: Do not mirror Claude-only pty behaviours (Remote Control, deterministic session-id pin) in the agy adapter
status: accepted
date: 2026-06-25
change: CH-M7WSQ4
---

# ADR-002 — The agy adapter mirrors the *shape*, not the Claude-specific behaviours

## Context

`InteractiveClaudePtyAdapter` carries two behaviours beyond the bare interactive
shape: (1) **Remote Control default-ON** (`--remote-control <handle>`, named after
the change), and (2) a **deterministic `--session-id <uuid>` pin** at first spawn
(derived from the change ULID via `_change_session.change_session_id`) so focus can
resume by the same derived id without scraping the id Claude assigned.

The spec says "mirror `InteractiveClaudePtyAdapter`". The Platform Contract (PC-001)
verified that **agy has neither `--remote-control` nor `--session-id`** — agy assigns
conversation ids itself and exposes resume only via `--conversation <id>` / `--continue`.

## Decision

The agy adapter mirrors the **structure** of the Claude pty adapter (the
`ProviderAdapter` Protocol; `_BASE_ARGV`; brief-as-trailing-positional read from the
CH-GJ9KQR sidecar; unused `encode`/`decode`/`turn_complete`; `classify_failure → None`)
but **does not** reproduce the two Claude-only behaviours:

- **No Remote Control fragment** — agy has no such flag.
- **No deterministic pre-spawn session-id pin** — agy has no `--session-id`. Resume
  maps to agy's own id model: `SessionSpec.resume_ref` set → `--conversation <ref>`;
  `--continue` is the documented most-recent fallback.

## Alternatives considered

- **Emulate the pinned-id pattern by deriving an id and passing it to
  `--conversation` on first spawn.** Rejected: `--conversation <id>` *resumes* an
  existing conversation; passing a never-before-seen derived id at first spawn is a
  resume of nothing and would either error or create an empty/confused conversation.
  agy's id is agy-owned; pinning is a Claude-only affordance. Faking it is exactly
  the "clever, magical, implicit" pattern the boring-code standard rejects.
- **Carry a no-op Remote Control knob for symmetry.** Rejected: dead surface. A flag
  the platform does not accept is a band-aid, not a feature.

## Consequences

- The agy adapter is **smaller** than the Claude one, honestly so. The Sizing Report
  reflects this — the difference is platform-driven, not a cut corner.
- Resume is by `resume_ref → --conversation`; the consumer supplies the agy
  conversation id it captured (where agy stores it is agy's concern; Phase 1 treats
  `resume_ref` as the opaque agy handle, already shape-guarded by `SessionSpec.__post_init__`).
- If agy later gains a pin/remote-control affordance, adding it is a follow-on WP,
  not a Phase-1 obligation.
