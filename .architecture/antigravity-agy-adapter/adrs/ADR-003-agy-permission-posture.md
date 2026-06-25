---
id: ADR-003
title: agy runs under --sandbox by default; --dangerously-skip-permissions is opt-in only
status: accepted
date: 2026-06-25
change: CH-M7WSQ4
supersedes: none
---

# ADR-003 — The agy permission/sandbox posture (the Armor gate)

## Context

`agy` is a write/exec platform: it spawns an autonomous agent that edits files and
runs commands in the worktree. The spec is explicit: **do NOT blanket
`--dangerously-skip-permissions`; match the guardrail posture the Claude session
runs under**, with the exact flag set decided at design grounded in the Platform
Contract.

Observed Claude-path posture (`InteractiveClaudePtyAdapter._BASE_ARGV`): the Claude
adapter *does* pass `--dangerously-skip-permissions`, justified because a change
session runs unattended in an isolated git worktree (the worktree is the boundary)
and the Claude path is well-exercised. PC-001 confirmed agy ships a first-class
`--sandbox` flag (terminal restrictions) that the Claude CLI lacks.

## Decision

The agy adapter **defaults to `--sandbox` and does NOT pass
`--dangerously-skip-permissions`.** An opt-in env knob `SULIS_AGY_SKIP_PERMISSIONS`
(default-OFF; truthy turns ON) lets an operator who accepts the risk drop `--sandbox`
and pass `--dangerously-skip-permissions` instead.

The knob polarity is **default-OFF / opt-in** — the inverse of the Claude adapter's
default-ON Remote Control knob. A permission-*loosening* knob must be opt-in by
construction (a default-on loosening knob is a footgun).

## Rationale (why guarded, when Claude is not)

1. **Evidence asymmetry.** The Claude path has real-session operating history; agy is
   a brand-new, less-exercised integration. The conservative posture is correct until
   the failover capability (Phase 2) and real operation give us comparable evidence.
2. **Platform-native guardrail (CP-01).** agy ships `--sandbox`; using it is the
   boring, convention-aligned choice, not a bespoke wrapper.
3. **Blast radius.** An unattended auto-approve posture on a newer integration widens
   the blast radius beyond what Phase 1 warrants.

## Alternatives considered

- **Mirror the Claude posture exactly (`--dangerously-skip-permissions` default-on).**
  Rejected: the spec forbids blanket-skip, and the evidence asymmetry above makes the
  guarded default the right Phase-1 stance. The knob preserves the option for
  operators who want parity.
- **No `--sandbox`, no skip-permissions (let agy prompt interactively).** Rejected for
  the unattended change-session path: an agent that blocks on a permission prompt with
  no human attached hangs the session. `--sandbox` lets the agent proceed within
  restrictions without a blanket auto-approve — the right middle ground.

## Consequences

- Default agy spawns are sandboxed; the test posture asserts `--sandbox` present and
  `--dangerously-skip-permissions` absent by default, and the inverse when the knob is
  truthy.
- Revisit in Phase 2 once failover operation gives agy the operating history the
  Claude path has — promotion to skip-permissions-by-default would be a documented
  posture change, not a silent drift.
