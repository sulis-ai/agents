# Code Review: train-2026-06-01T112951Z — WP-002 squash-merged onto change branch

> **Timestamp:** 2026-06-01T11:32:28Z (ISO 8601 UTC)
> **Train ID:** train-2026-06-01T112951Z
> **Branch:** change/create-release-train-as-entities
> **Diff range:** 3e0336f..7dbd1f2 (post-train HEAD minus pre-train HEAD)
> **Files changed:** 8 / 1275 insertions
> **WPs shipped:** WP-002 (Steps catalogue — 15 Step entities = the release-train workflow body)
>
> **Outcome:** Ready to merge

---

## At a glance

This lands the **workflow body** — the 15 Steps that describe the release-train end-to-end, from recon through ship through tag-and-release. Each Step cross-references the right Tool (from WP-006) and the right FailureMode (from WP-004); composition is clean. The human-gate at Step 8 (founder confirmation before shipping) is preserved and explicitly flagged in the Step's `agent_instructions` as MUST-NOT-auto-execute (honouring the SRD's MUC-007). One small note: the executor's self-heal moved `for_workflow` to envelope level (the canonical Step schema's `unevaluatedProperties: false` rejected per-Step placement) — this is the right interpretation of the schema and tests cover it.

Nothing to fix. Ready for wave 4.

## What to fix

**No issues that need attention.**

## How this pull request is shaped

Single-WP train batch — hygiene shape is naturally clean.

- **Size**: 1275 lines / 8 files. Effective code surface ~180 lines (15 Step entities in one jsonld file + 10 tests + vendored schema + audit artifacts). Clean.
- **Scope**: All under `plugins/sulis/`. One Conventional Commits type. Clean.
- **Safety**: No migrations, no infrastructure changes, no dependency manifests, no CI workflow edits, no secret-pattern hits. Clean.
- **Completeness**: 1 source file (steps.jsonld), 1 test file (10 tests). 1:1 ratio. Tests cover parse + count + schema validation + tool_ref resolution + on_failure resolution + envelope-level canonical-ULID match + per-Step Blue invariants (kebab-case, Step 5 token budget, Step 8 human gate, I/O artifact consistency).

## Things to take away

1. **Schema-driven self-heal is a load-bearing pattern.** When the executor hit the Step schema's `unevaluatedProperties: false` rejecting per-Step `for_workflow`, it correctly interpreted the schema's signal — Steps belong to a workflow at envelope level, not per-Step — and moved the field accordingly, then updated the corresponding test. That's exactly the right shape for `kind: contract` work: the schema beats the WP-Contract sketch, and tests calibrate to the schema, not to the original prose. (Same pattern observed in WP-004's vocabulary reconciliation in wave 1.)

---

## Technical detail

### Verdict

`PASS` per CR-06.

### Summary

- **Build Verification (CR-01):** 0 errors. 27/27 release-train tests pass (10 new + 17 prior). Composition checks (cross-WP refs) inline:
  - 15/15 Step `tool_ref` values resolve to Tool IDs in tools.jsonld.
  - 7/7 unique FailureMode ULIDs in Step `on_failure` arrays resolve to IDs in failuremodes.jsonld.
  - Envelope `for_tenant` = `dna:tenant:6XBZ93FSHN5TRX8MCS5R66FNCM` (canonical).
  - Envelope `for_workflow` = `dna:workflow:01KT0RTRA1NWFW00000000000A` (canonical).
- **PR Hygiene (CR-09):** all four primitives clean.
- **In the changes:** 0 lens findings. WP-002's Step 6.5 per-WP review (`.architecture/release-train-as-entities/code-reviews/PR-feat-wp-002-author-steps-instance-2026-06-01T112503Z/REVIEW.md`) returned verdict PASS with 0 findings; this Step 10.5 review confirms via inline composition + dispatched Step 11 (also PASS, 0 findings).
- **Step 11 security verdict:** PASS, 0 findings, 0 advisories. Detailed checks: cross-WP refs resolve; envelope alignment correct; human-gate preserved; mechanism distribution {deterministic:13, probabilistic:1, human:1}; no embedded credentials/paths/injection placeholders.
- **Draft hardening deltas:** 0.

### CR-02 deviation note

Same deviation pattern as wave 2 (1-WP train batch): reduced from three-lens parallel dispatch to (a) mechanical baseline + inline composition + (b) WP-002's Step 6.5 per-WP review (verdict PASS, 0 findings) + (c) Step 11 security reviewer dispatch (verdict PASS, 0 findings). Documented honestly.

### Watch List

| Item | Reason |
|---|---|
| **Cumulative Step 11 ADVISORY count: 3** (stable across waves 1-3) — stale docstring on WP-003 tests; workflow ULID coordination (now resolved as canonical and used by all wave-3 cross-refs); gh-pr-merge stub pre-activation gate. None structural; all doc-drift or future-invariant. | Loop-until-clean is on track. |
| **Trigger schema vs Step schema asymmetry.** WP-003's Trigger entities carry `for_workflow` per-Trigger; WP-002's Step entities had to move `for_workflow` to envelope level (per schema). This is the brain schemas' own design choice — Trigger schema allows per-Trigger placement; Step schema doesn't. Not a finding; just a note for anyone reading the canonical files cold. | Documentation observation; no action. |

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] CR-01: 27/27 tests; inline composition checks all green.
- [—] CR-02: reduced for 1-WP train (see deviation note).
- [✓] CR-03: relevant files read end-to-end by inline check + Step 11 reviewer.
- [✓] CR-04: composition findings cite resolved IDs.
- [✓] CR-05: 0 findings in changes.
- [✓] CR-06: verdict PASS, no downgrades fired.
- [—] CR-07: reduced — see CR-02 deviation; Step 11 covered security surface.
- [✓] CR-09: PR Hygiene all primitives clean.

#### Run details

- **Diff source:** `git diff 3e0336f..7dbd1f2` after fetch + reset to origin.
- **Range correction note:** train's gate_handoff reported `dbd9eb7..7dbd1f2` (feat-branch pre-rebase SHA to post-train HEAD). The corrected range `3e0336f..7dbd1f2` is the change-branch linear-history range — same observation as waves 1+2.
- **Lenses dispatched:** 1 (Step 11 security reviewer).
