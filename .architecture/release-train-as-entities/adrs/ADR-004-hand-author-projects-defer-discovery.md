---
id: ADR-004
title: Hand-author Project instances for the 4 marketplace plugins; defer `project-discovery` Workflow
status: accepted
date: 2026-06-01
deciders: [iain]
---

## Context

The release-train Workflow is per-Project (per DR-017 — `Workflow.for_project`).
Each marketplace plugin is one Project (per the brain's scenario-1
"monorepo-multi-product" instance — `sulis`, `sulis-brain`, `plugin-builder`,
`investor-coach` all belong to the `sulis-plugins-marketplace` Product).

For this change to deliver value, each plugin's Project entity instance
needs to exist with its actual values (source.path, version_files,
branch_policy, etc.).

Two ways to produce the 4 Project instances:

1. **Hand-author them.** Read the marketplace's current state (the
   plugin directories, the marketplace.json, the current branch policy)
   and write 4 JSON-LD entity instances by hand into
   `plugins/sulis/instances/release-train/projects.jsonld`.
2. **Build a `project-discovery` Workflow now.** A new Workflow that
   takes an operator through an interactive flow: detect-git-remote →
   parse-git-config → scan-for-version-files → infer-branch-policy →
   select-tag-format (human) → write-project-instance. The marketplace's
   4 Projects would be the first instances it produces.

L13 in the brain's lessons: **don't abstract on n=1.** The marketplace
is the first consumer. The variations (different branch policies,
different version files, different CI providers) don't exist yet.

The SRD names `project-discovery` as a sibling change deferred until
n=2 evidence (a second consumer forks the marketplace) OR until env-init
lands and shares the discovery primitive.

## Decision

**Hand-author the 4 Project instances for the marketplace plugins in
this change. Defer `project-discovery` to a sibling change.**

The 4 Project instances we'll author:

| Project | source.path | version_files | branch_policy |
|---|---|---|---|
| `sulis` | `plugins/sulis` | `["plugins/sulis/.claude-plugin/plugin.json", ".claude-plugin/marketplace.json"]` | `gitflow-dev-main` |
| `sulis-brain` | (cross-repo to sulis-plugins repo) | per the brain's scenario-1 fixture | `gitflow-dev-main` |
| `plugin-builder` | (cross-repo to sulis-plugins repo) | per scenario-1 fixture | `gitflow-dev-main` |
| `investor-coach` | `plugins/investor-coach` | `["plugins/investor-coach/.claude-plugin/plugin.json", ".claude-plugin/marketplace.json"]` | `gitflow-dev-main` |

The `sulis` Project is the marketplace-resident one; the other three
are referenced by their existing brain scenario-1 instances. (For
sulis-brain + plugin-builder which live in a different repo at
`sulis-plugins/plugins/`, we may need a duplicate-instance vs
cross-repo-reference call — flagged as a sub-question; not blocking.)

`project-discovery` becomes its own SRD + change when triggered.

## Options Considered

- **Hand-author 4 Project instances now (CHOSEN).** The values are
  observable from the repo; 4 instances at ~20 lines each is ~80 lines
  of focused authoring. The marketplace's Projects then serve as
  worked examples for future fork-consumers (referenced by the SRD's
  Configuration Vocabulary). Discovery is a known follow-up that
  doesn't block this change.
- **Build `project-discovery` Workflow now** — rejected per L13. n=1
  evidence; the abstraction isn't yet earned. The interactive flow
  itself would be ~10 Steps + ~5 FailureModes + new Tools (detect-git-
  remote, parse-git-config) — adding a workflow on top of a workflow.
  Risk that scope expands to also cover env-init, deploy-discovery,
  etc. before any of them have n=2 evidence.
- **Skip Project instances entirely; refer to scenario-1's existing
  fixtures** — rejected. The marketplace's actual Projects (especially
  `sulis` + `investor-coach`) aren't in scenario-1's fixture; only
  `plugin-builder` + `sulis-brain` are. We need at minimum to add
  `sulis` and `investor-coach` for the drift detector to validate
  Project ↔ marketplace.json coordination (MUC-008).

## Consequences

- **Positive:** Path A becomes self-contained — no upstream dependency
  on a discovery Workflow. The 4 Project instances are the worked
  examples that the SRD's Configuration Vocabulary section points to.
  L13 honoured. Discovery effort is correctly deferred until n=2.
- **Negative:** A future fork-consumer has to hand-author their own
  Project instance by reading the Configuration Vocabulary +
  cross-referencing the marketplace's instances. Manual but tractable.
  The discovery sibling closes this gap when it ships.
- **Neutral:** When `project-discovery` does ship, it'll regenerate
  these 4 Project instances + then move forward. Hand-authored
  instances are not throwaway; they're the templates discovery
  produces.

## Open sub-questions (flagged in TDD)

- **Cross-repo references.** `sulis-brain` and `plugin-builder` live
  in `sulis-plugins/plugins/`, not in this marketplace repo. Their
  Project instances exist in the brain's scenario-1 fixture. Should
  we duplicate the instances in the marketplace's release-train/
  directory, or reference them cross-repo via some convention? Defer
  to design pass review; sub-question, not load-bearing.
