---
id: ADR-003
spec: auto-back-merge-on-release
title: Drift detection fires in both /sulis:release-train and /sulis:change start, via a shared bash helper
status: accepted
date: 2026-06-02
relates_to: [FR-009, FR-010, UC-006, MUC-003, NFR-007]
---

# ADR-003 — Drift detection in both entry-point skills

## Context

Drift (origin/main not an ancestor of origin/dev) is the gap this change
exists to prevent. The reusable workflow + back-merge step closes the
window automatically on every release. But the historical incidents
(`0e85c24`, `8612834`, `d93517c`) prove the auto-mechanism can also fail
silently — a maintainer pushes directly to main (MUC-003), a consumer
breaks their shim (MUC-004), branch protection blocks a fast-forward
(MUC-002) and the raced-path PR sits open uncommented (MUC-007).

Defence in depth says: detect drift at every entry point that would
otherwise compound the gap. The two entry points that matter are:

- `/sulis:release-train` — if invoked against a drifted dev, it would
  compute next-version against stale state and the resulting release PR
  would itself be drifted.
- `/sulis:change start` — if invoked against a drifted dev, the new
  change branch starts from a stale base, and any subsequent ship merges
  back into the same drifted dev. Multiplies the gap.

The check itself is one git command (`git merge-base --is-ancestor
origin/main origin/dev`) + one GitHub API call to enumerate open
back-integrate PRs (for the error message composition). NFR-007 requires
it to complete in under 5 seconds, deterministically.

The question: where does the check logic live? Three options:

- **Shared helper called from two skills.** One source of truth.
- **Copy-pasted in two skills with a comment pointing at the canonical
  implementation.** Easier to read inline; risks drift between the two
  copies over time.
- **Move the check into a Python helper inside the existing
  `wpx-preflight` script.** The existing helper has related work
  (protection-status etc.), so it would be natural — but then
  `wpx-preflight` is a Python script and the workflow ALSO needs the
  check (for FR-011 post-condition), and the workflow can't easily call
  Python.

## Decision

Implement drift detection as a **shared bash helper** at
`plugins/sulis/scripts/drift_check.sh`. Both skills call it; the
workflow's post-condition step (FR-011) calls it too where applicable.

```bash
# plugins/sulis/scripts/drift_check.sh — boring, three responsibilities.
#  1. git fetch origin (callers may skip via --no-fetch)
#  2. is-ancestor check
#  3. compose error message (back-merge PR open vs not)
#
# Exit codes:
#   0 — clean (main is ancestor of dev)
#   1 — drifted (with stderr error message naming the recovery path)
#   2 — fetch failed (transient — caller can retry)
```

Callers:

- `/sulis:release-train` invokes it as Step 1 (after path resolution).
- `/sulis:change start` invokes it as the first preflight before branch
  creation.
- The reusable workflow's FR-011 post-condition check invokes the same
  helper to verify atomicity ("dev fast-forwarded" vs "PR open").

The helper is bash, not Python, because:

- It must run in three contexts: two skill bash snippets and one CI
  workflow step.
- It must be portable to fork-consumer repos that don't install Python.
- The logic is one git command and one `gh` call. Python would be over-
  engineering.

## Rationale

- **Defence in depth.** MUC-003 (manual operator bypass) is exactly the
  case a single check site cannot catch. If only `/sulis:release-train`
  has the check, a developer running `/sulis:change start` against drifted
  dev compounds the gap silently. Both skills must refuse.
- **Shared source of truth.** Two copy-pasted checks drift over time
  (the marketplace has a documented incident — the loop-guard regression
  that skipped PR #132 on 2026-05-31). One helper, two callers.
- **Boring code over clever code.** Bash + one git command + one gh API
  call. No abstraction, no factory, no class. The helper is ~40 lines.
- **CP-01 — convention.** The marketplace's existing `wpx-*` helpers are
  exactly this shape: a small executable script with a clear contract,
  callable from skills and from CI. `drift_check.sh` follows the same
  pattern.
- **NFR-007 budget.** `git merge-base --is-ancestor` is O(log N); the gh
  API call is one HTTP round trip. Both well under the 5s budget.

## Alternatives considered

### A — Drift check only in `/sulis:release-train`

Rejected: MUC-003 unhandled. A bypass on main combined with normal
`/sulis:change start` invocations multiplies the gap. The cost of adding
the same check in `change start` is one bash call.

### B — Two copy-pasted implementations with cross-reference comments

Rejected: the marketplace already has a documented incident (the
release-on-merge loop-guard pattern-match regression) where two
copy-pasted checks drifted and one was wrong. EP-03 / Boy-Scout says
extract the shared primitive when two implementations of the same
pattern exist. One helper, two callers, both correct.

### C — Move the check into `wpx-preflight` (the existing Python helper)

Rejected: introduces a Python dependency in the workflow runtime where
none currently exists for this check, and complicates the dual-skill
call sites (which would have to spawn a python subprocess for a one-line
git command). `wpx-preflight` does protection-status checks and is
Python because those benefit from richer logic; drift detection
doesn't.

### D — Make the check a pre-commit hook on dev

Rejected: pre-commit hooks fire on the developer's machine, not at skill
invocation time. They don't catch the case where dev was drifted by a
robot or by a push from a different repo clone. Wrong tool for the
threat model.

## Consequences

- **For both skills:** Each gains one bash call before its real work.
  Refusal path uses the helper's stderr message verbatim (FR-009 spells
  the message structure).
- **For the workflow:** FR-011's post-condition step calls the helper to
  verify atomicity. Same exit-code semantics.
- **For maintenance:** Future changes to the drift check (e.g., adding
  a `--strict` mode that checks `.changesets/` consistency) happen in
  one place.
- **For testing:** The helper has its own unit tests (FR-013 / FR-014
  exercise its paths). Skill-level tests mock the helper's exit code
  rather than mocking git itself.
