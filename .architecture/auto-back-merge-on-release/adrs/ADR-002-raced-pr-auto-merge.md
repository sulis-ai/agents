---
id: ADR-002
spec: auto-back-merge-on-release
title: Raced back-merge PRs auto-merge after CI green; no human review gate
status: accepted
date: 2026-06-02
relates_to: [FR-003, UC-002, MUC-007]
---

# ADR-002 — Auto-merge raced back-merge PRs

## Context

UC-002 (raced release path) produces a PR with base=`dev`, head=`main`,
opened by `github-actions[bot]`. The question: should this PR sit waiting
for human review, or should it auto-merge once CI is green?

The PR contains exactly the content of `main` — which is the release the
founder already merged moments earlier. There is no new code, no new
decision, and no new risk that wasn't already accepted at the moment the
release PR merged. The only thing the back-merge PR exists to do is move
dev's pointer forward to include that already-shipped content.

MUC-007 (open back-merge PR left to rot) is the load-bearing concern with
the alternative (require human review): a forgotten PR causes drift to
persist, and the next release-train invocation refuses (FR-009) — but the
founder must still go back and merge the dead PR.

## Decision

**Enable auto-merge on every raced back-merge PR** at the moment of
opening it. The PR merges automatically once branch-protection's required
checks pass on it.

The workflow:
1. Opens the PR.
2. Enables auto-merge via `gh pr merge --auto --merge <PR-number>` (regular
   merge, not squash — preserves the existing history of dev that already
   diverged from main).
3. Exits success. The PR is the deliverable; its eventual merge is the
   responsibility of GitHub's auto-merge mechanism + branch protection.

If CI fails, the PR stays open. The next `/sulis:release-train` invocation
detects drift (FR-009), enumerates the open `back-integrate`-labelled PR,
and refuses with a directive to fix the PR's CI failure first (UC-006).

## Rationale

- **The PR is not a review gate; it's a recovery artifact.** Reviewing it
  would mean reviewing the release itself, which already happened at the
  upstream release PR. Asking a human to review the same diff twice
  produces no signal.
- **Auto-merge is the established convention** for bot-authored
  mechanical-recovery PRs. Renovate / Dependabot / Mend / Snyk all default
  to auto-merge for PRs whose content is mechanically derived from
  upstream state. CP-01 — recommend the convention.
- **MUC-007 mitigation.** Auto-merge collapses the human-attention window
  for drift to zero in the green-CI case. Drift persists only on CI
  failure, which is detectable and recoverable (FR-009 surfaces it).
- **Atomicity (NFR-006).** The workflow's success criterion is "main bumped
  AND (dev fast-forwarded OR back-merge PR open)." Auto-merge does NOT
  change the workflow's success criterion — the PR being *open* is success.
  CI-pass-then-merge happens asynchronously after the workflow exits.

## Alternatives considered

### A — Open the PR; require human merge

Rejected: produces MUC-007 in its worst form. Every raced release would
queue a PR awaiting attention. With multiple consumer repos, this
multiplies across the ecosystem. The PR contains nothing reviewable that
wasn't already reviewed; the human cost is pure tax.

### B — Auto-merge after a delay (e.g., 1 hour for owners to catch issues)

Rejected: solves a problem we don't have. The release PR upstream already
had its review window. A 1-hour delay just defers MUC-007 by an hour
without changing the underlying ergonomics. Adds workflow complexity (a
follow-up job that runs at the delayed time) for no real benefit.

### C — Open as draft; require manual conversion

Rejected: same MUC-007 problem as Alternative A.

### D — Open with auto-merge, but only if the diff is "trivial" (no new
files, no large changes)

Rejected: the diff IS the release, which by definition just changed every
file the release touched. The heuristic would either always-trigger (in
which case it's no different from auto-merge) or sometimes-block (in
which case it's another MUC-007 trigger).

## Consequences

- **For founders:** A raced release feels identical to a clean release.
  The PR appears, CI runs, merge happens, dev catches up. No human
  intervention required in the green-CI case.
- **For CI:** The back-merge PR runs the same `branch-ci.yml` as any
  other dev PR. If a release just shipped successfully, the back-merge PR
  re-running the same checks is high-confidence-green.
- **For branch protection on dev:** `dev` MUST allow `github-actions[bot]`
  to merge PRs (it already does, since this is the existing merge path).
  `dev` MUST require CI-green status (existing branch protection setting).
  No new branch-protection settings introduced.
- **For visibility (NFR-004):** The back-merge merge commit appears on
  `dev`'s history authored by `github-actions[bot]` with the title from
  FR-003 — fully audit-visible.
- **For the CI-failure path:** When CI on the back-merge PR fails, the
  workflow does NOT retry. The PR sits open; FR-009's drift check surfaces
  it on the next release-train invocation; the founder fixes the CI
  failure and re-runs the PR (or manually merges if appropriate). This is
  the load-bearing fallback for the "auto-merge isn't always safe" case.
