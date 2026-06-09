# ADR-004 — Resolve a closing seam to its covering Scenarios through the requirement bridge

- **Status:** accepted
- **Change:** CH-01KTP7 (`feat` · `seam-dod-gate`)
- **Date:** 2026-06-09

## Context

Once ADR-001 fixes the gate unit as the seam, the gate must turn a closing seam
into the set of Scenarios to drive. The obvious shape — "look up the Scenario
attached to this seam" — does not exist in the data model. Two facts from the
code:

1. **WP frontmatter does not carry the requirement ids a WP implements.** A WP
   carries `kind`, `dependsOn`, `status`, and a `verification` block
   (adapter + artifact) — but not `implements: [dna:requirement:…]`.
2. **Scenarios key cleanly to requirements and a journey.** Every Scenario
   carries `verifies: [dna:requirement:…]` and `journey: dna:workflow:…`
   (confirmed in this repo's `*.scenarios.jsonld`). `_brain_query` already has
   `find_scenarios_verifying(requirement_id)` and
   `find_scenarios_for_journey(journey_id)`.

So there is no direct seam→Scenario edge, but there is a clean
requirement→Scenario edge.

## Decision

**Resolve seam → requirements → Scenarios.** The bridge is the requirement set
the seam implements; from there, the existing `find_scenarios_verifying` query
yields the covering Scenarios. Two resolution sources for step 1 (requirements
the seam implements), in priority order:

1. **The contract WP's `implements:` field** — `[dna:requirement:…]`, read
   directly. This is the clean path; the WP-standard amendment (SHOULD) adds this
   field to contract WPs so `/sulis:plan-work` populates it going forward.
2. **Fallback — the change's Scenario set filtered by journey.** Where the
   contract WP names a journey (or the change authored Scenarios at specify),
   enumerate `find_scenarios_for_journey(journey)` and treat Scenarios whose
   `verifies` requirements intersect the seam's requirements as covering. Keeps
   legacy decompositions (no `implements:` field) working.

The covering-Scenario set then feeds `sulis-verify-acceptance --scenario <id>`
per Scenario, and the per-Scenario verdicts fold through the **reused**
`_acceptance_gate.gate_decision`.

## Why (the recommendation, lead position)

- **Build only on existing queries.** `find_scenarios_verifying` and
  `find_scenarios_for_journey` already exist and are the same primitives
  `_verify_scenario_coverage` uses. No new traversal mechanism, no new brain
  schema — the boring, established path in this codebase.
- **Scenarios are requirement-keyed by design**, so the requirement is the
  natural join column. Trying to force a seam id onto Scenarios would fight the
  data model (and ADR-001 already rejected the Scenario-as-unit framing).
- **The `implements:` field is a small, additive WP-standard change** that makes
  the clean path first-class without breaking older WPs (SHOULD + fallback).

## Alternatives considered

- **Add a `seam` field to Scenarios and key directly.** **Rejected:** Scenarios
  don't tile seams 1:1 (ADR-001); a seam field would be a lie for any Scenario
  spanning multiple seams, and a schema change to the brain for a mapping that
  doesn't hold.
- **Parse the WP's `verification.artifact` test path to infer requirements.**
  **Rejected:** brittle string inference over file paths; the artifact is a test
  location, not a requirement claim. The `implements:` field states the claim
  explicitly.
- **Require `implements:` as MUST on every contract WP now.** **Rejected:**
  breaks existing contract WPs and forces a backfill before the gate works at
  all. SHOULD + journey-filtered fallback is correct now and clean forward.

## Consequences

- `WORK_PACKAGE_STANDARD.md` gains the contract-WP `implements:` field (SHOULD).
- `_seam_close_gate` reads `implements:` when present, falls back to
  journey-filtered Scenario intersection otherwise.
- A seam whose requirements have **no** covering Scenario at all is a real,
  detectable outcome → blocked (ADR-005).
- Open question carried to `/sulis:plan-work`: whether to backfill `implements:`
  onto existing contract WPs or rely on the fallback (TDD §Open questions).
