# ADR-001 — Adopt the platform Thread / Message / ThreadMemory model as the canonical shape

> **Status:** accepted · **Date:** 2026-06-24 · **Change:** CH-GJ9KQR
> **Decision-makers:** engineering-architect (per Working Set platform finding)

## Context

This change needs a vendor-neutral shape for (a) the raw message record and
(b) the rich context payload. The platform repo (`~/dev/repos/platform`,
`features/thread-sdk/` + `features/communication-service/`) **already defines
this model**, almost 1:1 with our spec's needs:

- **Thread** — platform/tenant-scoped, workspace-independent conversation unit
  (`id`, `platform_id`, `topic`, `activity_summary`, `created_at`,
  `updated_at`, `participant_count`).
- **ThreadParticipant** — `user | studio_agent` (+ `role`).
- **ThreadMemory** — 1:1 with Thread, **versioned**, `content` =
  **ThreadMemoryContent** (`messages[]` + `exploration_journal[]` +
  `participant_context{}`).
- **ThreadMessage** — `id`, `participant_id`, `participant_type`, `content`,
  `role ∈ {question, answer, observation, decision}`, `created_at`.
- **ExplorationJournalEntry** — `type ∈ {question, answer, pattern_detected,
  decision_captured}`, `content`, `created_at`, `participant_id`, `metadata`.

The mapping onto our spec is direct: our **raw message log = Messages**; our
**rich payload = ThreadMemory.content** (and the `exploration_journal` aligns
strikingly with the Working Set's why / decisions / patterns); our **discovery
seam = getThreadMemory / getThread**.

## Decision

**Adopt the platform thread-sdk model as the canonical shape for this change's
message log and context payload.** Our Sulis-owned types mirror the platform's
entity definitions field-for-field (names, enums, the
Thread→ThreadMemory→ThreadMessage/ExplorationJournalEntry containment), so the
two cannot diverge. The platform `ONTOLOGY.jsonld` at
`~/dev/repos/platform/features/thread-sdk/ONTOLOGY.jsonld` is the reference;
the cockpit's local contract conforms to it.

## Rejected alternatives

- **Fork a parallel Sulis-only thread model** (invent our own message/memory
  shape). Rejected per CP-01 (prefer the established internal prior-art
  convention) and EP-03 (check before building new): the platform already
  models this. A parallel model would drift, double the maintenance, and make
  the later sync (ADR-002 hybrid) a translation layer instead of a passthrough.
- **Reuse only the message shape, invent our own rich-payload shape.**
  Rejected: the platform's `ThreadMemoryContent` (messages + exploration
  journal + participant context) is exactly our rich payload, and its
  `exploration_journal` entry types map onto our Working Set crystallisation
  moments. Inventing a separate payload shape discards a 1:1 fit.

## Consequences

- Our types carry the platform's field names and enums verbatim. Where we add
  Sulis-specific context (e.g. a bound `change_id`, provider identity), it goes
  in `participant_context` / `metadata` (the platform's open-ended fields),
  never by renaming a platform field.
- A schema-consistency check (mirroring the platform's own XVC-05 risk
  mitigation) guards drift between our local types and the platform JSONLD.
- **Terminology:** we use **"thread"** (founder's call; also the platform's
  term) — never "session" in founder-facing surfaces or the new types. The
  cockpit's existing per-change PTY process keeps the name "session" internally
  (ADR-004 reconciles the two).
