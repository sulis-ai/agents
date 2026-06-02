# Sequence Diagrams — auto-back-merge-on-release

## SD-001: Clean release path (UC-001)

%% Shows the happy-path interaction: founder merges the release PR, robot
%% bumps versions on main, then verifies the dev SHA pin still matches and
%% performs a fast-forward push of main → dev. No human in the loop after
%% the merge.

```mermaid
sequenceDiagram
    participant F as Founder
    participant GH as GitHub
    participant R as Release Robot
    participant Dev as origin/dev
    participant Main as origin/main

    Note over F,GH: /sulis:release-train opens release PR<br/>(pin: dev-sha-at-open=SHA_A)

    F->>GH: Merge release PR
    GH->>Main: push release commit
    activate Main
    GH->>R: trigger release-on-merge
    activate R

    R->>R: bump versions, delete changesets, build CHANGELOG
    R->>Main: commit + tag (vX.Y.Z) + push
    R->>R: read dev-sha-at-open from PR body (SHA_A)
    R->>Dev: git ls-remote origin dev
    Dev-->>R: current dev SHA = SHA_A (unchanged)

    Note over R,Dev: Clean path — fast-forward
    R->>Dev: git push origin main:dev
    Dev-->>R: ok (fast-forward succeeded)
    deactivate Main
    deactivate R

    Note over Dev,Main: Dev now equals Main
```

## SD-002: Raced release path (UC-002)

%% Shows the race: developer lands work on dev between PR open and robot
%% run. Robot detects the SHA mismatch, opens a back-merge PR instead of
%% force-pushing. PR auto-merges on CI green.

```mermaid
sequenceDiagram
    participant F as Founder
    participant D as Developer
    participant GH as GitHub
    participant R as Release Robot
    participant Dev as origin/dev
    participant Main as origin/main

    Note over F,GH: Release PR opened<br/>(pin: dev-sha-at-open=SHA_A)

    D->>Dev: merge feature work (dev advances to SHA_B)
    F->>GH: Merge release PR
    GH->>Main: push release commit
    activate Main
    GH->>R: trigger release-on-merge
    activate R

    R->>R: bump, tag, push (main now at vX.Y.Z)
    R->>R: read pin SHA_A
    R->>Dev: git ls-remote origin dev
    Dev-->>R: current dev SHA = SHA_B (moved!)

    Note over R,Dev: Raced — open PR, never force-push

    R->>GH: open PR (base=dev, head=main,<br/>title="chore: back-integrate main → dev (post-release vX.Y.Z)",<br/>label="back-integrate")
    GH-->>R: PR-N opened
    R->>GH: enable auto-merge on PR-N
    deactivate R

    Note over GH: CI runs on PR-N

    alt CI green
        GH->>Dev: auto-merge PR-N
        Note over Dev: Dev now contains main's release commit<br/>(via merge commit by github-actions[bot])
    else CI fails
        Note over GH,F: PR-N stays open; release-train drift check<br/>(UC-006) will block next release until merged
    end
    deactivate Main
```

## SD-003: Fork-consumer inherits via shim (UC-003)

%% Shows how a consumer's release flow becomes a back-merging one
%% transparently via the shim → reusable-workflow indirection. The consumer
%% installs the plugin update, adds the 10-line shim once, and from then on
%% every release auto-back-merges.

```mermaid
sequenceDiagram
    participant C as Consumer Maintainer
    participant CR as Consumer Repo
    participant PR as Plugin Repo<br/>(sulis-ai/agents)
    participant GA as GitHub Actions Runtime

    Note over C,PR: One-time setup
    C->>PR: install/update plugin to v0.87.0+
    C->>CR: add .github/workflows/release-on-merge.yml<br/>(10-line shim, uses: sulis-ai/agents/.../release-on-merge.yml@sulis-v0.87.0)

    Note over C,GA: Every subsequent release

    C->>CR: merge release PR
    CR->>GA: trigger workflows on push:main
    activate GA
    GA->>CR: load consumer shim
    CR->>GA: shim: `uses:` directive
    GA->>PR: fetch reusable workflow at @sulis-v0.87.0
    PR-->>GA: reusable workflow YAML
    GA->>GA: execute reusable workflow against consumer's repo state
    GA->>CR: bump, tag, push (main)
    GA->>CR: fast-forward OR open back-merge PR (per SD-001/SD-002)
    deactivate GA
```

## SD-004: Drift-detection refusal in /sulis:release-train (UC-006)

%% Shows the defensive check: if main is not an ancestor of dev, the
%% release-train skill refuses to draft a release PR and points at the
%% recovery procedure.

```mermaid
sequenceDiagram
    participant F as Founder
    participant S as /sulis:release-train
    participant Git as Local git

    F->>S: invoke
    activate S
    S->>Git: git fetch origin
    Git-->>S: refs updated
    S->>Git: git merge-base --is-ancestor origin/main origin/dev
    Git-->>S: exit 1 (main is NOT ancestor of dev)

    alt main is ancestor of dev (clean)
        S->>Git: compute next version, draft release PR
        Git-->>S: PR drafted
        S-->>F: release PR ready
    else main is NOT ancestor of dev (drifted)
        S->>Git: list back-merge PRs (label="back-integrate")
        Git-->>S: 0 or 1 open PRs
        S-->>F: REFUSE. "Dev is behind main. Recover per GIT-12.<br/>If a back-merge PR is open at #N, merge it first.<br/>Otherwise: git fetch && git merge --no-ff origin/main && git push origin dev"
    end
    deactivate S
```
