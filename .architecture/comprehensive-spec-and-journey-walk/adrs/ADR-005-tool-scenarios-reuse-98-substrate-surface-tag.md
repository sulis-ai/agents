---
title: Tool scenarios reuse the #98 substrate; add only a surface tag
status: accepted
kind: adr
---

# ADR-005 — Tool scenarios reuse the #98 substrate; add only a `surface` tag

## Context

FR-10 requires verifiable scenarios derived from every UC flow for BOTH
surfaces: UI scenarios drive the screen, tool scenarios drive the real
MCP/SDK/API call end-to-end (observed-or-blocked). FR-14 requires tool-surface
scenarios to be driven via the existing #98 verification substrate (scripted
`http_call`/`subprocess` + agent-step tiers) — explicitly NO new mechanism.
NFR-S03 requires no green tool scenario without a real driven round-trip;
NFR-R02 requires an undrivable tool scenario to be recorded deferred, not
dropped. NFR-05 requires stable scenario IDs from the same seed.

A-02 is confirmed: `sulis-verify-acceptance` `driver_for_step` already resolves
`http_call`/`subprocess`/agent-step drivers (lines 48–60). But
`assemble_scenario_graph` (`_scenario_authoring.py` lines 51–60) has no
first-class `surface` parameter — per-step `mechanism`/`tool_ref` distinguish
*driver type* but not *which consumer surface* the scenario belongs to.

## Decision

Reuse the #98 substrate wholesale for driving (FR-14 — no new driver) and add
**only** a first-class `surface ∈ {ui, tool}` parameter to
`assemble_scenario_graph`. The surface tag lets the UC-flow-coverage gate and
the read-only scenarios report (`scenarios/SKILL.md`) distinguish the two
surfaces (FR-10, UC-05 2a where one flow yields scenarios on both). The tag is
additive and optional (absent ⇒ `ui`, the current single-surface default), so
existing scenarios are unaffected and `seed` stability (NFR-05) is preserved.
Driving, observed-or-blocked verdicts, and the undrivable-⇒-deferred path
(NFR-R02) all come from the existing substrate unchanged.

## Options Considered

- **Reuse #98; add only a `surface` tag (CHOSEN).** Honours FR-14 literally;
  minimal additive change; preserves ID stability and existing scenarios.
- **A parallel tool-scenario driver** — rejected: violates FR-14 outright; two
  driver mechanisms drift; the observed-or-blocked + TestResult evidence model
  would fork.
- **Infer surface from the per-step driver type** — rejected: a `subprocess`
  step can serve a UI scenario (driving a CLI that renders a screen) and an
  agent-step can serve a tool scenario; driver type ≠ surface, so inference is
  wrong. A first-class tag is the honest representation.

## Consequences

- **Positive:** zero new driver code; the real-drive backstop (NFR-S03) and
  deferred-not-dropped path (NFR-R02) are inherited; surface is now queryable
  for the gate and the report.
- **Negative:** a schema/authoring change to add the tag; the dev-tier real
  endpoint is a deferred infra need (`tool-drive-sandbox`) so some tool
  scenarios are attested locally until the sandbox lands.
- **Neutral:** the `surface` default of `ui` means the migration is a no-op for
  existing scenarios.
