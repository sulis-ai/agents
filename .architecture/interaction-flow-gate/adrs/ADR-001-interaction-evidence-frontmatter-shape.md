# ADR-001 — Interaction-flow evidence frontmatter shape

> Status: accepted · change_id: 01KT9HJMZC4731H0TAVW1E5QCD · Tier S

## Context

The interaction-flow done-gate must read, from a work package's frontmatter,
whether the WP's multi-step flow was exercised end-to-end over stub adapters —
and refuse `flip-status --to done` until it was. The visual-contract gate
(`#45 / UXD-14`) already solves the analogous problem with two frontmatter
fields:

- `signed_off_at:` — an ISO-8601 timestamp (the *when*)
- `provenance: production-approved` — a controlled token (the *what kind of evidence*)

The interaction gate has one extra dimension the visual gate does not: the
spec mandates **two sources of evidence** — `agent-observed` (the agent ran
the flow over stubs and recorded it) or `human-attested` (a person ran it and
attested, with who + when). We must choose the field names and the validity
rule.

## Decision

Stay symmetric with the visual gate. An interaction-contract WP records three
frontmatter fields:

| Field | Meaning | Mirrors |
|---|---|---|
| `exercised_at:` | ISO-8601 timestamp the flow was exercised end-to-end over stubs | `signed_off_at:` |
| `exercised_by:` | source of evidence — exactly `agent-observed` **or** `human-attested` | (new dimension) |
| `exercised_attestation:` | free-text: for `human-attested`, who attested + a one-line note; for `agent-observed`, a pointer to the recorded observation (e.g. the stub-run transcript path) | (new dimension, plays the role `provenance` plays for visual) |

The predicate `interaction_flow_exercised(fm)` returns `None` (pass) iff:

1. `exercised_at` is a non-empty string, **and**
2. `exercised_by` is exactly one of the two controlled tokens
   (`agent-observed` / `human-attested`, case-insensitive), **and**
3. `exercised_attestation` is non-empty (so neither source can pass with a
   bare timestamp and no record of *who/what* exercised it).

Any other state — empty timestamp, unknown/blank source token, missing
attestation — returns a founder-readable error string, exactly as
`visual_contract_signed_off` does. The error names the missing field and the
gate (mirroring the visual gate's message style).

## Rationale

- **Symmetry is the brief.** The spec's first constraint is "mirror the
  visual-contract gate, don't reinvent it." `exercised_at` ↔ `signed_off_at`,
  and a controlled token playing the `provenance` role, keeps the two gates
  legible side-by-side and lets a reviewer learn one and know both.
- **Two sources, one predicate.** Both `agent-observed` and `human-attested`
  are *valid* evidence (the spec says either satisfies the gate), so they sit
  on the same axis (`exercised_by`) rather than as separate fields. The
  predicate does not privilege one over the other — unlike the visual gate,
  where only `production-approved` passes.
- **Attestation is mandatory for both.** A bare `exercised_at: <timestamp>`
  with no record of *who* or *what* exercised the flow would let the gate be
  satisfied by a comment-out. Requiring `exercised_attestation` keeps the
  evidence falsifiable: an agent run points at its transcript; a human names
  themselves.

## Alternatives considered

- **Reuse `signed_off_at` / `provenance` verbatim with new provenance tokens
  (`agent-observed` / `human-attested`).** Rejected: `signed_off_at` reads as
  a human sign-off; overloading it for an agent-observed run muddies the
  visual gate's semantics and risks a WP being mis-read as visually signed
  off. Distinct field names keep the two gates independent.
- **A single structured `evidence:` block (nested mapping).** Rejected:
  `read_frontmatter` / the WP-table chokepoint treat frontmatter as flat
  scalar/list values (see `_cells_from_frontmatter`); a nested mapping would
  need new parsing the visual gate didn't, violating "don't reinvent." Flat
  scalars match the existing machinery.
- **Boolean `exercised: true` only.** Rejected: drops who/when, which the
  spec's acceptance criterion explicitly requires ("recorded with who +
  when"). A boolean is the green-but-unfalsifiable shape this gate exists to
  prevent.

## Consequences

- The interaction predicate lives beside `visual_contract_signed_off` in
  `_wpxlib.py` and is unit-tested in the same symmetric style.
- The clinics-scheme spike records `exercised_by: agent-observed` after the
  stub run (or `human-attested` if a person runs it), demonstrating both
  branches reach `done`.
