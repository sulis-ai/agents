---
id: ADR-004
spec: auto-back-merge-on-release
title: GIT-12 appended after GIT-11; standard's calibration period unchanged
status: accepted
date: 2026-06-02
relates_to: [FR-007, FR-008]
---

# ADR-004 — GIT-12 rule placement in git-workflow-standard.md

## Context

The new rule "Auto-back-merge on release (MUST)" needs a home in
`plugins/sulis/references/git-workflow-standard.md`. The current standard
runs GIT-01 through GIT-11 with a calibration period of 90 days from
2026-05-16 (active until 2026-08-14). Adding GIT-12 raises three
ordering / versioning questions:

1. **Where does it sit in the file?** Three plausible positions: after
   GIT-06 (its conceptual neighbour — the release train); after GIT-11
   (sequential append); inserted between GIT-09 (no force-push) and
   GIT-10 (rollback) where it's structurally related to both.

2. **Does the standard's version bump?** The standard's frontmatter says
   `Version: 0.2.0`. Adding a rule could be a 0.2.1 patch (additive,
   non-breaking) or a 0.3.0 minor.

3. **Does the calibration window reset?** The current window covers
   GIT-01..GIT-11. A new rule arguably starts its own calibration.

## Decision

**Append GIT-12 after GIT-11.** Do not renumber existing rules. Do not
restructure the file's narrative around the new rule's conceptual
neighbours.

**Bump the standard's version to 0.3.0.** Additive minor change to a
codified standard.

**The standard's overall calibration window does NOT reset.** GIT-12 is
treated as in-window from its addition date forward. Per the standards
authorship rule, "New principles start at SHOULD with a 90-day
calibration note. Promotion to MUST requires evidence from 3+
executions."

GIT-12 ships as MUST despite being new, because the SRD's spec already
treats it as MUST (the workflow YAML enforces it; the drift gate
enforces it; the post-condition check enforces it). The marketplace's
own first release after this change is the n=1 execution. The two CI
fixtures (FR-013 / FR-014) are n=2 and n=3 — they are executions of the
mechanism in a deterministic test environment. Three executions before
the rule lands; the MUST-on-launch is grounded.

This rationale is documented in the GIT-12 section itself for audit.

## Rationale

- **CP-01 — established convention.** Standards documents in regulatory
  / compliance / engineering bodies (RFC series, NIST SP-800-*, ISO
  control families) almost universally append new sections rather than
  re-flow existing ones. The reader who has the existing numbering in
  muscle memory should not have to relearn it.
- **Cross-references stay stable.** External references in the marketplace
  to "GIT-06" or "GIT-09" remain valid. A renumbering would require
  finding and rewriting every cross-reference — high cost, zero benefit.
- **MUST-on-launch is defensible.** The standards rule of "SHOULD for 90
  days, then MUST" exists to surface real-world friction before locking
  the invariant. For GIT-12, the friction surfaces in CI tests + the
  marketplace dogfood, all of which run before the rule ships. The
  invariant is also enforced *by the workflow* — there's no aspect of
  GIT-12 that's "advisory" rather than "executable."
- **Bump to 0.3.0 follows SemVer for docs.** Additive but visible.
  Calibration history in the file should record the addition + the basis
  (three executions before launch).

## Alternatives considered

### A — Insert between GIT-09 (force-push) and GIT-10 (rollback)

Rejected: would renumber GIT-10 and GIT-11. The cost of finding and
fixing every "see GIT-10" / "see GIT-11" reference across all skills,
docs, and ADRs is non-trivial; the benefit (slightly tighter conceptual
grouping) is small.

### B — Backfill GIT-06 (release train) to encompass auto-back-merge

Rejected: the SRD's Out-of-Scope section explicitly says "Retroactively
rewriting `git-workflow-standard.md` to fold the GIT-12 invariant into
GIT-06 (the existing GIT-06 stays as-is; GIT-12 is additive)." Editing
GIT-06 in place would invalidate the calibration window for GIT-06
itself and risks regressions in the existing release-train references.

### C — Ship GIT-12 as SHOULD for 90 days, then promote

Rejected: GIT-12 is enforced by code (the workflow + the drift gate +
the post-condition check). There is no aspect of the rule that's
"opt-in" for those 90 days. The marketplace shipping a SHOULD-flagged
rule it actually treats as MUST is dishonest documentation. Better to
ship MUST with the executions named.

### D — Reset the standard's overall calibration window to 2026-06-02

Rejected: GIT-01..GIT-11 have been in calibration for the period they
have. Adding a new rule doesn't change what's been observed for the
existing ones. Mixing the windows would obscure each rule's actual
provenance.

## Consequences

- **For readers:** Standard now ends at GIT-12. Table of contents +
  intro list both gain the new entry. Existing cross-references (every
  `see GIT-NN`) remain valid.
- **For the standard's metadata:** Version moves to 0.3.0. Calibration
  note for GIT-12 is in-line in its section: "Promoted to MUST at launch
  based on three deterministic executions (CI regression tests +
  marketplace dogfood). Subsequent calibration tracked via release
  incidents over the standard 90-day window."
- **For the SRD's FR-007 / FR-008:** Both fully discharged by this ADR —
  FR-007 by the addition itself, FR-008 by the worked examples included
  with the rule.
- **For future rule additions:** Sets the convention: append, bump
  minor, document the basis for the initial severity in the rule's
  section. Future GIT-NN additions follow the same shape.
