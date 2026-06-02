# Data Flow Diagram — auto-back-merge-on-release

%% Shows where the release-and-back-merge data flows: from the changesets +
%% dev SHA pin, through the reusable workflow, into bumped version files and
%% the dev branch HEAD.

```mermaid
flowchart LR
    Changesets[(`.changesets/*.yaml`<br/>pending changes)]
    PluginJson[(plugin.json<br/>marketplace.json<br/>CHANGELOG.md)]
    ReleasePR[(release PR body<br/>contains dev-sha-at-open pin)]
    DevSHA[(origin/dev<br/>current HEAD)]
    Workflow[Reusable workflow<br/>release-on-merge.yml]
    MainBranch[(origin/main)]
    BackMergePR[(back-integrate PR<br/>base=dev head=main)]
    DevBranch[(origin/dev<br/>updated HEAD)]
    DriftCheck[Drift detection<br/>/sulis:release-train +<br/>/sulis:change start]
    BotIdentity[(GITHUB_TOKEN<br/>github-actions bot identity)]

    Changesets -->|cumulative tier + next version| Workflow
    PluginJson -->|current version| Workflow
    Workflow -->|bumped values| PluginJson
    BotIdentity -->|auth| Workflow

    ReleasePR -->|SHA_A pin line| Workflow
    DevSHA -->|current SHA via ls-remote| Workflow

    Workflow -->|release commit + tag| MainBranch
    Workflow -->|fast-forward push when SHA matches| DevBranch
    Workflow -->|PR open when SHA differs| BackMergePR
    BackMergePR -->|auto-merge on CI green| DevBranch

    MainBranch -->|merge-base check| DriftCheck
    DevBranch -->|merge-base check| DriftCheck
    BackMergePR -->|label search| DriftCheck
    DriftCheck -->|refuse if drifted| ReleasePR
```

Notes:

- The `dev-sha-at-open` pin in the release PR body is the only piece of data
  flowing from `/sulis:release-train` to the reusable workflow that controls
  the clean-vs-raced decision. Everything else flows through git refs.
- The drift detection (right side of the diagram) is a read-only consumer
  of git state. It does not write back; it refuses or proceeds.
- `BotIdentity` (GITHUB_TOKEN) is the single auth credential the workflow
  needs. Its scope (`contents: write, pull-requests: write`) is what
  enables both the fast-forward push and the PR open.
