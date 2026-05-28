---
id: ADR-002
title: Tier derived from the change primitive, not hand-set
status: accepted
change_id: 01KSQNPBPN7W74QVAZ25F79RNH
date: 2026-05-28
---

# ADR-002 — Tier derived from the change primitive, not hand-set

## Decision

**A changeset's release tier (`patch | minor | major`) is computed
deterministically from the change's primitive**, not chosen by hand at ship
time. The mapping lives in `_changeset.py::tier_for_primitive(primitive)`:

| Primitive(s) | Tier |
|---|---|
| `fix`, `chore`, `refactor`, `docs` | `patch` |
| `feat`, `create`, `extend`, `compose`, `reuse`, `strangle`, `wrap`, `harden`, `instrument` | `minor` |
| anything flagged **breaking** | `major` |
| `admin`, `docs-only` (changes outside `plugins/sulis/**`) | `None` → **no changeset written** |

An explicit `tier:` field in the changeset YAML **overrides** the computed value
for the rare exception (e.g. a `refactor` that is secretly breaking).

## Context

Every change already declares its primitive (the 22-primitive vocabulary in
`references/change-primitives.md`) when it is started via `/sulis:change start`.
The primitive is therefore a free, already-captured signal for the release tier.
Asking the agent (or founder) to *also* hand-pick a SemVer tier at ship time
introduces a second judgment call that can disagree with the primitive — and a
judgment call is exactly the kind of "step the flow relies on someone getting
right" that #66 is about removing.

## Alternatives considered

1. **Hand-set tier at ship time (rejected).** The agent picks `patch`/`minor`/
   `major` per ship. *Rejected because* it's a judgment call that can drift from
   the primitive, and it's precisely the discretionary step #66 wants to
   eliminate. Determinism removes the drift.

2. **Infer tier from the diff (rejected).** Parse the diff to guess
   breaking-ness. *Rejected because* it's unreliable (a one-line change can be
   breaking; a thousand-line change can be a pure patch) and far more complex
   than reading the already-declared primitive. Boring beats clever.

3. **Tier from primitive with an explicit override (CHOSEN).** Deterministic by
   default, with a documented escape hatch for the rare case the mapping is
   wrong. This is the minimum-surprise design: 99% of changes never touch the
   tier; the 1% set `tier:` explicitly and the override is visible in the
   changeset YAML (and editable on `dev` before the release PR, per the
   contract).

## Consequences

- **Positive:** the tier is free, deterministic, and auditable; no per-ship
  judgment call; the cumulative tier (`max` of all changesets) is a pure
  function of the batch.
- **Cost:** the mapping is a policy that must be kept current as the primitive
  vocabulary evolves; `tier_for_primitive` returns `None` for unknown primitives
  so a new primitive surfaces loudly (the writer can decide) rather than
  silently defaulting.
- **`None` is meaningful, not an error:** admin/docs-only changes write *no*
  changeset (they don't affect what consumers install), mirroring honest's
  decision table. WP-002 skips the changeset write when `tier_for_primitive`
  returns `None`.

## Related

- ADR-001 (the decoupling this tier policy serves), WP-001 (implements
  `tier_for_primitive` + `cumulative_tier`).
