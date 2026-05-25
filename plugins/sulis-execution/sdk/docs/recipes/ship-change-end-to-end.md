# Recipe: Ship a change end-to-end

**Applies to:** sulis-execution v0.1.0

A change is the unit of work per CW-01..CW-08. This recipe walks
through the full lifecycle: start → work → finish.

## The flow

1. Start the change (creates branch + worktree)
2. Do the work (outside the SDK — could be SRD/SEA/executors)
3. Verify ahead/behind
4. Finish (rebase + merge + cleanup)

## Python implementation

```python
from sulis_execution import (
    SulisExecution,
    ExpectedError,
)

client = SulisExecution(
    repo_root='/path/to/repo',
    project='my-project',  # not used by change ops; required for the client
)

# 1. Start
try:
    started = client.change.start(
        slug='introduce-payments',
        primitive='create',
    )
    print(f"Branch: {started.branch}")
    print(f"Worktree: {started.worktree_path}")
except ExpectedError as e:
    if 'branch_already_exists' in (e.code or ''):
        print("Change already exists — try `adopt` instead")
    else:
        raise

# 2. Do the work
# (External: SRD, SEA, executors run in the worktree. The SDK has
# no opinion here.)

# 3. Verify
status = client.change.status(slug='introduce-payments', primitive='create')
print(f"Ahead of base: {status.ahead_of_base} commits")
print(f"Behind base:   {status.behind_base} commits")

if status.ahead_of_base == 0:
    print("No commits on the change branch yet; not ready to finish")
    exit(0)

# 4. Finish (squash-merge to dev)
finished = client.change.finish(
    slug='introduce-payments',
    primitive='create',
    merge=True,    # squash-merge to dev
)
print(f"Outcome: {finished.outcome.mode}")
print(f"Cleanup: worktree_removed={finished.cleanup['worktree_removed']}, "
      f"branch_deleted={finished.cleanup['branch_deleted']}")

# Alternative: open a PR instead of merging
# finished = client.change.finish(slug='...', primitive='...', pr=True)
# print(f"PR URL: {finished.outcome.pr_url}")
```

## TypeScript implementation

```typescript
import { SulisExecution, ExpectedError } from '@sulis-ai/execution';

const client = new SulisExecution({
  repoRoot: '/path/to/repo',
  project: 'my-project',
});

try {
  const started = client.change.start({
    slug: 'introduce-payments',
    primitive: 'create',
  });
  console.log(`Branch: ${started.branch}`);
  console.log(`Worktree: ${started.worktree_path}`);

  // ... do work ...

  const status = client.change.status({
    slug: 'introduce-payments',
    primitive: 'create',
  });
  if (status.ahead_of_base && status.ahead_of_base > 0) {
    const finished = client.change.finish({
      slug: 'introduce-payments',
      primitive: 'create',
      merge: true,
    });
    console.log(`Outcome: ${finished.outcome.mode}`);
  }
} catch (err) {
  if (err instanceof ExpectedError && err.code === 'branch_already_exists') {
    console.log('Change already exists — try adopt');
  } else {
    throw err;
  }
}
```

## What this recipe demonstrates

- `change.start` for greenfield change branches
- Error code matching (`e.code == 'branch_already_exists'`)
- `change.status` for ahead/behind inspection
- `change.finish --merge` for squash-merge + cleanup
- The merge-vs-pr fork (mutually exclusive)

## See also

- [Operations catalogue](../reference/operations.md)
- The Change Work Standard (CW-01..CW-08) at
  `../../../../sulis/references/change-work-standard.md`
