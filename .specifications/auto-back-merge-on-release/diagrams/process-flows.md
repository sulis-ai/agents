# Process Flow Diagrams — auto-back-merge-on-release

## PF-001: Release robot decision flow (UC-001 + UC-002 combined)

%% This is the entire decision tree inside the reusable workflow's
%% back-merge step. It runs AFTER the existing bump+tag+push-main steps
%% succeed. It's the inserted unit between today's "tag and push" step and
%% the end of the job.

```mermaid
flowchart TD
    A([release-on-merge has<br/>finished bump+tag+push to main]) --> B[Read dev-sha-at-open<br/>from release PR body]
    B --> C{Pin present and<br/>well-formed?}
    C -->|No| D[Default to PR path<br/>safe fallback]
    C -->|Yes| E[git ls-remote origin dev]
    E --> F{Current dev SHA<br/>== pin?}
    F -->|Yes| G[git push origin main:dev<br/>fast-forward]
    G --> H{Push succeeded?}
    H -->|Yes| I([Clean path complete:<br/>dev = main])
    H -->|No, branch protection| D
    F -->|No, dev moved| D

    D --> J[Open PR base=dev head=main<br/>title chore: back-integrate<br/>label back-integrate]
    J --> K{PR opened?}
    K -->|Yes| L[Enable auto-merge on PR]
    L --> M([Raced path complete:<br/>PR will merge when CI green])
    K -->|No| N([FAIL workflow:<br/>bump succeeded but back-merge could not.<br/>Surface in job log; alert founder])
```

## PF-002: Drift detection in /sulis:release-train (UC-006)

%% Defensive check fired before any release-PR drafting work. The same
%% pattern fires in /sulis:change start (UC-006 secondary trigger).

```mermaid
flowchart TD
    A([Founder invokes<br/>/sulis:release-train]) --> B[git fetch origin]
    B --> C{Fetch succeeded?}
    C -->|No| D([Refuse: network error.<br/>Retry after fetch works])
    C -->|Yes| E[git merge-base --is-ancestor<br/>origin/main origin/dev]
    E --> F{Main is ancestor<br/>of dev?}
    F -->|Yes, clean| G[Proceed: compute next<br/>version, draft release PR]
    G --> H([Release PR drafted;<br/>founder reviews and merges])
    F -->|No, drifted| I[List PRs labelled back-integrate]
    I --> J{Any open<br/>back-merge PR?}
    J -->|Yes| K([Refuse: 'Back-merge PR #N is open;<br/>merge it first, then retry.'])
    J -->|No| L([Refuse: 'Dev is behind main.<br/>This happens if a release shipped<br/>without back-integration.<br/>Recover per GIT-12 manual procedure.'])
```

## PF-003: Manual recovery procedure (UC-005)

%% The procedure documented in GIT-12 worked examples, for use by consumers
%% who are already in the drifted state. Mirrors the three back-integration
%% commits in the marketplace's history.

```mermaid
flowchart TD
    A([Consumer in drifted state]) --> B[git fetch origin]
    B --> C[git checkout dev]
    C --> D[git pull origin dev]
    D --> E[git merge --no-ff origin/main]
    E --> F{Merge clean?}
    F -->|Yes| G[git commit with message<br/>'chore: back-integrate origin/main into dev']
    F -->|No, conflict| H[Resolve conflicts manually:<br/>prefer main for plugin.json,<br/>marketplace.json, CHANGELOG.md;<br/>preserve dev for everything else]
    H --> G
    G --> I[git push origin dev]
    I --> J([Drift resolved.<br/>Shim handles future releases.])
```
