---
id: ADR-001
title: Decouple integration from release via changesets
status: accepted
change_id: 01KSQNPBPN7W74QVAZ25F79RNH
date: 2026-05-28
closes: 66
---

# ADR-001 — Decouple integration from release via changesets

## Decision

**Integration (landing a change on `dev`) and release (bumping versions,
assembling the CHANGELOG, tagging) are separated into two distinct acts.** Each
change writes a **changeset** — a small `.changesets/*.yaml` file recording its
*intent and tier but no version number*. Changes accumulate on `dev`, each
carrying a changeset. A separate, on-demand release step batches the accumulated
changesets into one deterministic, bot-driven version bump on merge to `main`.

This is the founder-chosen direction (Option B in
`.changes/release-train.SPEC.md`) and the root fix for #66.

## Context

`/sulis:change ship` couples integration with release and leaves the release
half to agent discipline: there is no mandated, enforced bump step. The
consequences are recorded in the linked issues:

- **Unlabelled ships (#52, #59, #53):** three features in a row landed on `dev`
  with no version bump and no CHANGELOG entry — invisible to the release record.
- **Version-collision (#64 vs #52):** two concurrent changes both targeting the
  same next-version collided.

The same failure class as the lesson-capture gap (fixed in v0.76.0 as ship step
4.6): a process step the flow relied on the agent to *remember* rather than
*enforcing*.

## Alternatives considered

1. **Per-change bump as a required ship step (rejected).** Add a mandated step
   to `/sulis:change ship` that bumps SemVer + appends a CHANGELOG line, gated so
   the merge can't proceed without it. *Rejected because* it keeps
   one-change-one-release and therefore keeps the #64-vs-#52 version-collision
   race — two changes shipping near-simultaneously both compute the same next
   version and clash on the bump. It's the cheapest option but doesn't fix the
   conflict class.

2. **Manual bump remains, better-documented (rejected).** Keep the human/agent
   bump but write firmer docs. *Rejected because* #66's whole point is that a
   step the flow *relies on someone remembering* will eventually be forgotten —
   documentation does not enforce.

3. **Changeset-based release-train (CHOSEN).** Decouple the two halves. Each
   change writes a changeset; a release-train batches them into one bump. This
   eliminates the per-change bump race entirely (the bump happens once, for the
   whole batch, deterministically) and gives a clean, batched release cadence.
   It is the established convention in the wider ecosystem (the Changesets tool;
   honest-claude's `/contribute` + `/release-train`), so downstream agents and
   humans pattern-match it.

## Consequences

- **Positive:** the bump becomes deterministic and enforced; the version race is
  structurally impossible (one batched bump); the release record can never
  silently lose a feature (every plugin-affecting change carries a changeset).
- **Cost:** a new artifact type (`.changesets/*.yaml`) and a new on-demand step
  (`/sulis:release-train`) to learn. Mitigated by mirroring the honest-claude
  shape the team already references.
- **Generalises #41 / L-08** (hoist-shared-primitive): the changeset model is the
  general "intent fragment accumulated then batched" primitive.

## Related

- ADR-002 (tier from primitive), ADR-004 (the GHA as bump authority),
  ADR-005 (the changeset contract).
