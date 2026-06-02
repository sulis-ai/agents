---
id: ADR-005
spec: auto-back-merge-on-release
title: dev-sha-at-open pin is written as an HTML comment in the release PR body by /sulis:release-train
status: accepted
date: 2026-06-02
relates_to: [FR-001, NFR-001, MUC-001]
pairs_with: ADR-006
---

# ADR-005 — Pin-write mechanism (release-train side)

## Context

The reusable workflow distinguishes the clean release path from the
raced release path by comparing dev's current SHA at robot-run time
against a SHA snapshot recorded at release-PR-open time. The snapshot is
the **dev-sha-at-open pin**. NFR-001 + FR-001 specify the pin's
existence; ADR-006 specifies how the workflow reads it; this ADR
specifies how `/sulis:release-train` *writes* it.

Three sub-questions:

1. **Where in the PR is the pin stored?** Body text, title, label, or
   commit message.
2. **What format?** Plain key-value, JSON, HTML comment, code block.
3. **When is the pin captured?** Before drafting the body, or
   immediately before the `gh pr create` call.

The pin's properties matter:

- It must survive `gh pr view --json body` extraction (ADR-006's mechanism).
- It should NOT render visibly in the PR's GitHub UI — the founder
  reading the PR doesn't need to see a 40-char SHA mixed into the
  release notes.
- It must be machine-regexable with a tight signature so the workflow
  doesn't false-match on a similar string in the changelog (e.g., a
  changeset summary that happened to contain `dev-sha-at-open: <hex>`).

## Decision

**Embed the pin as an HTML comment at the bottom of the release PR
body**, in exactly this shape:

```html
<!-- dev-sha-at-open: 4974818f1c2d3e4a5b6c7d8e9f0a1b2c3d4e5f6a -->
```

Capture the SHA via `git rev-parse origin/dev` immediately before the
`gh pr create` call (after the body file is otherwise drafted, before
the create-PR command runs). Append the comment line to the body file:

```bash
# Step 5 of /sulis:release-train, just before gh pr create:
DEV_SHA=$(git rev-parse origin/dev)
echo "" >> "$BODY_FILE"
echo "<!-- dev-sha-at-open: ${DEV_SHA} -->" >> "$BODY_FILE"
gh pr create --base main --head dev \
  --title "$TITLE" \
  --body-file "$BODY_FILE" \
  $DRAFT_FLAG
```

The regex the workflow uses (ADR-006) is anchored:
`<!-- dev-sha-at-open: ([a-f0-9]{40}) -->`. Forty hex chars, exact
wrapper text. Cannot be falsely matched by a changeset summary or a
copy-pasted release-note line.

## Rationale

- **HTML comments don't render in GitHub.** The founder reading the PR
  in the GitHub UI sees the release notes; the pin is invisible. This
  matches FE (founder English) — internal mechanism stays internal.
- **`gh pr view --json body` returns the raw markdown including
  comments.** Verified against the GitHub REST API docs (the PR body is
  stored as raw markdown; comments are preserved on retrieval).
- **Tight regex prevents false-match.** The full wrapper `<!--
  dev-sha-at-open: <40-hex> -->` is exotic enough that no human-written
  release note would accidentally collide.
- **CP-01 — convention.** HTML-comment-as-machine-readable-metadata is the
  established pattern in PR bodies across the GitHub ecosystem
  (Dependabot's `compatibility-score` block, GitHub's own `Resolves
  #NN` parsing, Renovate's `<!-- renovate-* -->` blocks).
- **Atomicity with body drafting.** Capturing the SHA at body-write
  time, in the same skill invocation, makes the pin the founder-visible
  truth at PR-open time. If `git rev-parse origin/dev` is captured
  earlier (e.g., at skill startup) and the founder takes 20 minutes
  reviewing the dry-run before confirming, dev may have moved. The pin
  must be the SHA as-of the `gh pr create` call, not earlier.

## Alternatives considered

### A — Plain visible line in the body (e.g., `**dev-sha-at-open:** <SHA>`)

Rejected: clutters the founder-facing release notes with internal
mechanism. Violates FE: the founder shouldn't have to scroll past a
40-character hex string to see the changelog.

### B — Pin in the PR title (e.g., `release: sulis v0.78.0 [dev=<SHA>]`)

Rejected: titles have a length budget in many UIs; the existing title
pattern (`release: sulis v0.78.0 (minor)`) is already tight. Adding a
40-char SHA breaks the title's readability. Also: the existing release
workflow loop-guard pattern-matches on the title (PR #132 incident);
adding new title content risks new pattern-match regressions.

### C — Pin in a GitHub label (e.g., `dev-sha-4974818f...`)

Rejected: labels are limited to 50 characters, which fits a SHA, but
labels are not the conventional place to store machine metadata of
this shape. They're for discoverability, not data. Also: the workflow
already uses the `back-integrate` label for the raced PR; adding a
SHA-keyed label per release would clutter the label list.

### D — Pin in the merge commit message

Rejected: requires `/sulis:release-train` (which doesn't merge) and
the founder's manual merge action (which is a UI click, not editable)
to coordinate on a commit message. The squash-merge commit body could
in principle carry the pin, but founders editing the commit body at
merge time is friction. HTML-comment in the PR body is captured
automatically at PR-open and requires zero founder action.

### E — Pin in a separate file committed to the dev branch at PR-open

Rejected: produces a file that has to be cleaned up post-merge,
introduces a commit on dev that competes with the dev SHA the pin is
supposed to record (the pin would be obsolete the moment it's written),
and creates a separate change-of-state on dev that may itself drift.

## Consequences

- **For `/sulis:release-train`:** One bash snippet added before `gh pr
  create`. The dry-run output continues to elide the comment (the
  founder-facing preview doesn't need to display it; the dry-run mode
  can show the pin in the technical/raw register if requested, never
  in founder mode).
- **For the workflow (ADR-006):** Reads back exactly this format. The
  ADR-005 / ADR-006 pair is the contract.
- **For testing:** Unit test the body-write step: assert the comment is
  appended, the SHA matches `git rev-parse origin/dev`, the comment is
  literally at the end of the body. FR-001's acceptance criterion is
  directly verifiable.
- **For visibility (NFR-005):** Power-users running `gh pr view --json
  body` or curl-ing the API see the comment. Founders in the GitHub UI
  don't. Both populations get the information appropriate to them.
- **For consumer adoption (UC-003):** Consumers inherit this mechanism
  via the shim. Their releases use the same `/sulis:release-train`
  skill, so the pin gets written exactly the same way in their repos.
