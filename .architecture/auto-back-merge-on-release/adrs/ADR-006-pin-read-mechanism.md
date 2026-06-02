---
id: ADR-006
spec: auto-back-merge-on-release
title: Reusable workflow reads the dev-sha-at-open pin via gh api commits/{SHA}/pulls + regex
status: accepted
date: 2026-06-02
relates_to: [FR-002, FR-003, NFR-001, MUC-001]
pairs_with: ADR-005
---

# ADR-006 — Pin-read mechanism (workflow side)

## Context

At robot-run time, the reusable workflow's back-merge step needs to
recover the `dev-sha-at-open` pin that `/sulis:release-train` wrote at
PR-open time (ADR-005). The workflow runs on `push: main`; the
triggering event is the merge of the release PR, which means by the
time the workflow fires:

- The PR is **closed/merged**, not open.
- The commit at `GITHUB_SHA` is the merge commit (or the squash-merged
  release commit, depending on how the founder merged).
- The workflow has no direct reference to the PR number — only the commit
  SHA.

The workflow must:

1. Find the PR whose merge produced this commit.
2. Read its body.
3. Extract the pin.
4. Fall through to PR path if any step fails (safe default per
   NFR-001).

Three plausible mechanisms (mirrored from HANDOFF_TO_SEA's options A/B/C):

- **A — `gh api repos/{owner}/{repo}/commits/{SHA}/pulls`** — returns the
  PR(s) associated with a commit. Standard GitHub REST API call. The PR
  body is in the response.
- **B — Embed the pin in the merge commit message** itself (release-train
  rewrites the PR title or commit message to include `dev-sha-at-open=<SHA>`).
  Workflow reads the commit message directly.
- **C — Write the pin to a file in the repo at PR-open time;** commit it.
  Workflow reads it from the file at workflow run time.

## Decision

**Option A: `gh api repos/${GITHUB_REPOSITORY}/commits/${GITHUB_SHA}/pulls`,
then regex over the returned `body` field.**

The back-merge step's pin-read snippet:

```bash
# Resolve the release PR associated with the merged commit.
# --jq selects the first PR's body field (a release commit should have
# exactly one associated PR).
PR_BODY=$(gh api \
  "repos/${GITHUB_REPOSITORY}/commits/${GITHUB_SHA}/pulls" \
  --jq '.[0].body' 2>/dev/null || echo "")

# Tight regex: 40-hex enclosed by the exact HTML comment wrapper (ADR-005).
DEV_SHA_PIN=$(echo "$PR_BODY" \
  | grep -oE '<!-- dev-sha-at-open: [a-f0-9]{40} -->' \
  | grep -oE '[a-f0-9]{40}' \
  | head -1 \
  || echo "")

if [ -z "$DEV_SHA_PIN" ]; then
  echo "back-merge: pin absent or malformed; safe-default to PR path"
  # Fall through to PR path (FR-003).
fi
```

Any failure mode — `gh api` returns empty (no associated PR), the body
has no pin (pre-FR-001 release, or PR drafted by hand), the regex
doesn't match (someone edited the PR body and broke the wrapper) — sets
`DEV_SHA_PIN=""`, which falls through to the PR path (NFR-001 safe
default).

## Rationale

- **CP-01 — the API exists for this purpose.** `GET /repos/{owner}/{repo}/commits/{SHA}/pulls`
  was added by GitHub specifically to look up PRs associated with a
  commit. Documented at
  https://docs.github.com/en/rest/commits/commits#list-pull-requests-associated-with-a-commit.
  Recommending the convention.
- **Decoupled write/read.** Release-train owns the pin's write
  semantics; the workflow owns the read semantics. They communicate
  through GitHub PR storage. Either side can change implementation
  details without touching the other, as long as the wire format
  (the HTML comment regex) is stable.
- **`GITHUB_TOKEN` already authorises the call.** The reusable workflow
  declares `permissions: contents: write, pull-requests: write`; the
  GH_TOKEN env var (set via the existing `secrets.GITHUB_TOKEN`)
  authenticates the `gh api` call. No new secrets needed.
- **Safe default on every failure path.** This is the load-bearing
  property — MUC-001 (force-push race) is prevented by making the
  workflow ALWAYS prefer the PR path when the pin can't be confirmed.
  Even a tampered PR body (MUC-001's worst case: a malicious edit to
  forge a stale pin to match the current dev) is bounded — the workflow
  would attempt a fast-forward, which git would reject if the SHAs no
  longer make a valid fast-forward.
- **No file artifact, no commit cleanup.** Option C's file-on-dev
  approach requires a follow-up to delete the file, and the deletion
  itself is a commit, which itself races. Option A leaves git state
  untouched.

## Alternatives considered

### Option B — Pin in the merge commit message

Rejected because:

- Squash-merge commit bodies are editable by the founder at merge time;
  if the founder edits the body, the pin is gone.
- Workflow would need to parse `git log -1 --format=%B` and regex from
  there, which is one extra surface for malformed input.
- The PR body is the existing source of truth for release context (the
  changelog preview, the dry-run output, the version bump description).
  Co-locating the pin there is conceptually correct.

### Option C — Commit the pin to a file in the repo at PR-open

Rejected because:

- A pin written to dev at PR-open time becomes part of dev's HEAD —
  which is exactly the SHA the pin is supposed to record. Self-reference
  paradox.
- Cleanup is non-trivial: the file must be removed in a follow-up
  commit, which has its own race.
- Adds a file to consumer repos. Violates the "no consumer-side file
  writes" principle (NFR-003 spirit).

### A variant — `gh pr list --search "<SHA>"` instead of the commits/{SHA}/pulls endpoint

Rejected: `gh pr list` is paginated; the search syntax for "PR that
merged this commit" is brittle; the dedicated endpoint exists for
exactly this lookup. Use the dedicated API.

## Consequences

- **For the workflow:** One bash block (~15 lines including the
  fall-through). Pure standard tooling (`gh`, `grep`, no extra deps).
- **For testing (FR-013 / FR-014):**
  - Clean-path test fixture: stub `gh api` to return a JSON object with
    a `body` containing the canonical HTML-comment line; assert the
    workflow's fast-forward branch runs.
  - Raced-path test fixture: stub `gh api` to return a body with a pin
    different from the current dev SHA; assert the PR-open branch runs.
  - Defensive-fallback fixture: stub `gh api` to return an empty array,
    or a body with no pin, or a body where the regex doesn't match.
    Assert the PR-open branch runs in every case (NFR-001 safe default).
- **For MUC-001 (tampering with PR body to forge a stale pin):** The
  attack would aim to make the robot fast-forward over uncommitted dev
  work. Mitigation: the fast-forward push (`git push origin main:dev`)
  is rejected by git if main is not a strict descendant of dev. So even
  a forged pin claiming "dev SHA == main parent's dev SHA" doesn't
  enable a destructive fast-forward — git refuses non-fast-forward
  pushes by default, and the workflow does not use `--force`. The
  PR-open fallback fires.
- **For NFR-002 (no force-push):** Unaffected by this ADR. The push is
  a plain `git push origin main:dev` with no force flags; the workflow
  YAML's static-scan check (NFR-002 verification) confirms.
- **For ADR-005 / ADR-006 pair:** The write side (ADR-005) and read
  side (ADR-006) must agree on the exact HTML-comment wrapper text and
  the regex. This is the contract; both ADRs cite the same canonical
  shape. Any future change to the wrapper text touches both sides in
  the same PR.
