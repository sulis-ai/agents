# HANDOFF_TO_SEA — auto-back-merge-on-release

## Recommended next command

```
/sulis:draft-architecture .specifications/auto-back-merge-on-release/
```

## Design hints (don't re-design from scratch — these are founder-resolved)

The four key shape decisions are already settled. The TDD work is on the *how*, not the *what*.

### 1. Reusable workflow location

**Decision:** `plugins/sulis/templates/workflows/release-on-merge.yml`.

The current `.github/workflows/release-on-merge.yml` content (~280 lines) moves to this path with the addition of the back-merge step block. The file is declared as a reusable workflow:

```yaml
on:
  workflow_call:
    # Empty — no inputs required; everything is read from caller's git state.
permissions:
  contents: write
  pull-requests: write
```

### 2. Consumer shim shape

**Decision:** ~10 lines at the consumer's `.github/workflows/release-on-merge.yml`:

```yaml
name: release-on-merge
on:
  push:
    branches: [main]
permissions:
  contents: write
  pull-requests: write
jobs:
  release:
    uses: sulis-ai/agents/plugins/sulis/templates/workflows/release-on-merge.yml@sulis-v0.87.0
```

Replace the `@sulis-v0.87.0` tag with whatever version actually ships this change. Document `@dev` as opt-in always-track in the README; flag as risky.

### 3. The back-merge step insertion point

**Decision:** The back-merge step block goes AT THE END of the existing job, after the "Tag and push" step (currently the second-to-last step before the optional brain emission). It runs:

```bash
# 1. Read the dev-sha-at-open pin from the merged release PR body.
#    The current commit's PR is the head commit's associated PR. Use
#    gh api or gh pr view --json body to extract it.
#    Defensive default: if absent or malformed, set DEV_SHA_PIN=""

# 2. Read current dev SHA.
CURRENT_DEV=$(git ls-remote origin dev | cut -f1)

# 3. Decide path.
if [ -n "$DEV_SHA_PIN" ] && [ "$DEV_SHA_PIN" = "$CURRENT_DEV" ]; then
  # Clean path — fast-forward.
  if git push origin main:dev; then
    echo "back-merge: clean path, dev fast-forwarded to main"
    exit 0
  fi
  echo "back-merge: fast-forward push rejected, falling through to PR path"
fi

# 4. PR path (raced OR fast-forward rejected).
gh pr create \
  --base dev \
  --head main \
  --title "chore: back-integrate main → dev (post-release v${NEW_META})" \
  --body "Automatic back-integration after release v${NEW_META}. See GIT-12." \
  --label back-integrate
gh pr merge --auto --merge "$(gh pr view --json number -q .number)"
```

This is a sketch — SEA will tighten the bash, error handling, and idempotency.

### 4. Drift detection

**Decision:** Both `/sulis:release-train` and `/sulis:change start` get a shared helper. Possible location: `plugins/sulis/_lib/git_drift.py` or a bash helper at `plugins/sulis/scripts/drift_check.sh`. The check is one git command + one PR-list query:

```bash
git fetch origin
if ! git merge-base --is-ancestor origin/main origin/dev; then
  # Drifted. Check for open back-merge PRs.
  open_prs=$(gh pr list --base dev --label back-integrate --state open --json number)
  # Format error message based on open_prs.
  exit 1
fi
```

SEA decides whether this is a shared helper called from two skills, or duplicated by design with a comment pointing at the canonical implementation.

## Parked items / clarifications recorded in the spec

The change brief surfaced four open questions; my recommendations are:

1. **Pin shape (SemVer tag vs `@dev`):** Default to SemVer tag pin; document `@dev` as opt-in. Captured as NFR-008 and BR-03.
2. **Auto-merge or human review on raced PRs:** Auto-merge after CI green. The PR is a recovery from a race the robot caused, not a real change. Captured as FR-003 step 7.
3. **Drift check in `release-train` only or both `release-train` and `change start`:** Both. Defence in depth. Captured as FR-009 + FR-010.
4. **Backfill GIT-12 vs new version of git-workflow-standard.md:** Just add GIT-12. The existing GIT-01..11 are unchanged. Captured as FR-007.

## Two things SEA will need to make a call on (architecture-level)

### How to read the dev-sha-at-open pin

The pin is written by `/sulis:release-train` into the release PR body. The reusable workflow reads it AFTER the merge has happened — meaning the PR is no longer the merge candidate, and the workflow is firing on the post-merge commit. Options:

- **Option A (recommended):** Use `gh api repos/${GITHUB_REPOSITORY}/commits/${GITHUB_SHA}/pulls` to find the PR(s) whose merge produced this commit. Read their body. Grep for the pin line.
- **Option B:** Embed the pin in the merge commit message itself (release-train rewrites the PR title or commit message to include `dev-sha-at-open=<SHA>`).
- **Option C:** Write the pin to a file in the repo at PR-open time; commit it; read it from the file at workflow run time.

Option A is the most established pattern (GitHub provides the API for exactly this lookup). Option B couples release-train and the workflow more tightly. Option C is robust but produces a file we have to clean up.

### How `release-train` discovers the dev SHA at PR-open

`/sulis:release-train` opens the release PR; at the moment of opening, it should run `git rev-parse origin/dev` and inject `dev-sha-at-open: <SHA>` into the PR body. This is a small extension to the existing skill, but worth surfacing because SEA may want to add an ADR-style decision.

## Recommended follow-ons (out of scope here, named so they don't get lost)

1. **`/sulis:bootstrap-workflows` skill** — installs the shim file for fresh consumers. Triggered by `/sulis:discover-project` when the gap is detected (UC-004).
2. **Extension of `/sulis:discover-project`** — detect missing or stale shims; offer to invoke the bootstrap skill.
3. **Branch protection auto-setup** — depends on GitHub API access patterns we don't currently have.
4. **Canonical step annotation drift detector** — extend the existing drift catalogue to cover the new back-merge step. The current detector reads `# canonical:step:` annotations against `plugins/sulis/instances/release-train/steps.jsonld`; the back-merge steps will need entries there.
5. **Documentation of the manual recovery procedure for current consumers** (including the marketplace itself, which is in the drifted state right now per commit `d93517c`).

## Final read-order for the TDD

1. `GLOSSARY.md` — vocabulary lock (back-integration vs back-merge vs reusable workflow vs shim).
2. `PRIMITIVE_TREE.jsonld` — building blocks and their dependencies.
3. `SRD.md` — full behavioural spec.
4. `MISUSE_CASES.md` — adversarial coverage; the negative requirements are load-bearing.
5. `diagrams/sequence-diagrams.md` — SD-001 and SD-002 are the implementation contract.
6. `diagrams/process-flows.md` — PF-001 is the workflow logic; PF-002 is the drift detection logic.
7. `NFR.md` — measurable constraints. NFR-002 (no force-push) and NFR-006 (atomicity) are the load-bearing ones.

The Verification Plan section at the bottom of SRD.md will fold into the TDD as the test strategy.
