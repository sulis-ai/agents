# Sulis Execution

**The Work Package Executor for the Sulis AI marketplace.**

Each Work Package is an atomic operation. Nothing is "done" until the
code is implemented, tested, merged to `dev`, deployed to staging,
health-checked, and smoke-tested. The Executor handles all of that
for one WP. The Orchestrator walks the INDEX and dispatches Executors.

## Quick start

```bash
# Run one WP
/sulis-execution:run-wp WP-007

# Walk the whole INDEX
/sulis-execution:run-all

# Check status
/sulis-execution:status

# Retry a WP that was blocked by an external issue
/sulis-execution:retry WP-007
```

## What the Executor does

For one WP, the 10-step lifecycle:

1. Create a `git worktree` off `dev` HEAD; cut a feature branch.
2. Write the failing tests (Red).
3. Write the minimum code to make them pass (Green) — checks for
   internal prior art before writing new code.
4. Refactor (Blue) — mandatory; extracts shared primitives.
5. Lint / type-check / boring-code-standard checks.
6. Commit (Conventional Commits) + push branch (CI triggers).
7. Poll CI; on green, squash-merge directly to `dev` (no PR).
8. Trigger Sulis SDK deploy to staging.
9. Poll health-checks until healthy.
10. Smoke-test the deployed change; mark WP `done` in INDEX; clean up
    the worktree.

## Self-healing

When a step fails, the Executor runs an OODA loop:

- **Observe** the failure output verbatim.
- **Orient** by running Five Whys to a single root cause.
- **Decide** the minimum change inside scope.
- **Act** by applying the change and re-running the failed step.

Bounded retry per failure type (Lint 5, GREEN 3, CI 3, Deploy 3,
etc). Scope guard halts on out-of-scope causes (CI infra broken,
platform down, broader regression). Escalation goes via a structured
`BLOCKER-WP-NNN.md` record that the Orchestrator and Concierge read
to surface plain-English status to the founder.

See `plugins/srd/references/executor-loop-standard.md` for the full
spec.

## Git workflow

Direct merge to `dev` on CI green — **no PR ceremony**. Branch
protection on `dev` enforces the CI-green status check; the merge is
the action. `main` is the production-deploy marker; promotion is the
founder's separate ceremony via the Concierge.

See `plugins/srd/references/git-workflow-standard.md` for the full
spec.

## Working inside a change (CW-04, v0.12.0+)

Per the Change Work Standard at
`plugins/srd/references/change-work-standard.md`, every piece of work
is bounded by a **change** — a dedicated git branch + worktree. The
`sulis-change` tool provisions and tears down those workspaces.

### CLI

| Command | What it does |
|---------|-------------|
| `sulis-change start --slug X --primitive Y` | Create branch `change/{primitive}-{slug}` + worktree at `<repo-parent>/<repo-name>-change-{primitive}-{slug}/`. Writes metadata to `.changes/{primitive}-{slug}.yaml` on the change branch. |
| `sulis-change adopt --slug X --primitive Y` | Retrofit in-flight work (uncommitted / unpushed commits) into a change branch. Three modes: forward (default — leave already-pushed commits where they are), rewrite (destructive — relocates pushed commits; requires `--force`). |
| `sulis-change finish --slug X --primitive Y --merge OR --pr` | Rebase change onto dev, merge (or open PR), clean up worktree + branch. |
| `sulis-change list` | Enumerate active change branches with worktree + dirty state. |
| `sulis-change status --slug X --primitive Y` | One change's summary: SHA, ahead/behind base, worktree presence. |

### Two-level worktree hierarchy

```
~/repo                                ← main / dev tracked here
~/repo-change-create-payments         ← change worktree (CW-04 top)
  └── ~/repo-wp-001-schema            ← executor WP worktree (CW-04 inner)
  └── ~/repo-wp-002-handler           ← executor WP worktree (CW-04 inner)
```

The executor's WP worktree branches off the change branch, not `dev`.
The train ships WPs into the change branch. When the change is
verified end-to-end, `sulis-change finish` merges the change branch
into `dev` in one squash commit.

### Backward compatibility

When `/sulis-execution:run-wp` or `/sulis-execution:run-all` are
invoked **outside** a change worktree (directly on `dev`), the
`--base-branch` parameter defaults to `dev` and behaviour is identical
to v0.11.0. The change-bounded path is opt-in: activate it by running
`sulis-change start` before doing the work.

## What it's not

- It's not the architect (SEA designs).
- It's not the requirements analyst (SRD specifies).
- It's not the security reviewer (sulis-security audits).
- It's not the founder's product manager (the founder decides what
  the product is).

It's **the senior engineer**: takes a Work Package, ships it to dev
atomically. The Orchestrator and Concierge handle everything else.

## License

MIT — see `LICENSE` in the repo root.
