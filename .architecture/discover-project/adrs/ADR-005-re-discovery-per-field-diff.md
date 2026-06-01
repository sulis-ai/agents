---
id: ADR-005
title: Re-discovery — per-field diff with explicit approval
status: accepted
date: 2026-06-01
deciders: [iain]
resolves: SRD Open Question 5
---

## Context

UC-002 covers re-discovery: a consumer ran discovery six months ago,
their repo has evolved, they want to update their Project entity. The
re-discovery flag (`--update`) triggers this flow.

Three ways to handle re-discovery output:

1. **Bulk overwrite.** Re-run Detect + Infer + Ask + Mint as if
   first-time; overwrite the existing entity with the new one.
2. **Per-field diff with explicit approval.** Re-run Detect + Infer
   silently; produce a field-by-field diff (existing value vs proposed
   new value); for each changed field, ask the consumer to approve or
   reject; only approved changes are written.
3. **Smart merge with conflict markers.** Diff automatically; write a
   merged entity; embed `<<<<<<<`-style conflict markers where the
   merge is ambiguous; ask the consumer to resolve.

Bulk overwrite is fast but destructive — any value the consumer
customised after initial discovery (e.g., overrode an inferred deploy
target) would be silently re-overwritten if the next inference
re-disagrees. Smart-merge is too clever and introduces a third
artifact shape (conflict-marker-laden JSON-LD) that the schema
validator won't accept.

The marketplace's governance principle (release-train ADR-001) is
*founder owns mints*. Every change to a canonical entity should be
visible and approvable.

## Decision

**Adopt per-field diff with explicit approval.**

The `--update` flow:

1. Read the existing entity at `.sulis/projects/<slug>.jsonld`.
2. Run Detect + Infer normally (deterministic + probabilistic phases
   work the same as first-time).
3. Compose a "proposed entity" from Detect + Infer outputs.
4. Diff the proposed entity against the existing entity field-by-field
   (excluding metadata fields like `valid_from` that are expected to
   change every run).
5. For each field that differs, present the diff in the Ask phase
   (founder English):

   ```
   Field: deploy_target
     Existing:  github-release
     Proposed:  npm-publish
   Keep existing or apply proposed? [k/p]
   ```

6. Build the final entity from approved-proposed fields + preserved-
   existing fields.
7. Mint the final entity atomically (same write-to-tmp-then-rename as
   first-time).

Fields the consumer doesn't see at all (no diff) are unchanged from
the existing entity. Fields the consumer chooses to keep are preserved
verbatim. Fields the consumer chooses to apply use the newly-proposed
value.

Per NFR-003 (deterministic re-run), running `--update` twice in a row
on the same repo with the same approvals MUST produce a byte-identical
entity to the first run. No timestamp drift in metadata except where
the schema requires it.

## Options Considered

- **Per-field diff with explicit approval (CHOSEN).** Founder
  authorises every change. No silent drift. No destructive overwrite.
  The diff is the audit trail.
- **Bulk overwrite** — rejected. Destructive; loses consumer
  customisation; would force the consumer to re-make every override
  decision on every re-discovery run.
- **Smart merge with conflict markers** — rejected. Produces invalid
  JSON-LD (schema validator rejects); requires a second editing pass
  to resolve markers; too clever for what is essentially a small,
  flat data structure.

## Consequences

- **Positive:** Founder retains full control over the entity. Re-
  discovery becomes a safe operation — the worst case is keeping
  everything as-is, which is a no-op. The diff itself is a useful
  artifact (what changed in the repo since the last discovery).
- **Negative:** Re-discovery is slower than bulk overwrite — every
  changed field requires a human keystroke. Mitigated by the
  expectation that most re-discoveries are small (a new package
  manifest, a branch policy change) — typically <5 changed fields.
- **Neutral:** A future "--accept-all" flag could skip the per-field
  prompt for power users who explicitly trust the re-inference. Not in
  v1. Founder can flag if they want it.

## Composition

WP-005 (Ask phase) implements the diff presentation logic. WP-006
(Mint phase) composes the final entity from approved-proposed + kept-
existing fields. The atomic write is unchanged from first-time mint.

The diff format is the founder-facing surface. Per FE-01..FE-10, the
diff prompt MUST use field names from the founder-readable
Configuration Vocabulary (which already uses founder English from
release-train), MUST NOT surface internal taxonomy, MUST present one
field per prompt with a clear keep/apply binary choice.
