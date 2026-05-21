# How to handle errors

**Applies to:** sulis-execution v0.1.0
**Languages:** Python, TypeScript

## The error model in one sentence

Three categories of exception (Protocol / Expected / Internal) plus a
special "blocker outcome" pattern that is NOT an exception.

## Decision flow

```
Did the SDK return a result?
├── Yes
│   └── Check result.outcome
│       ├── "success" → ship it
│       ├── "blocker" → log + escalate; do NOT retry blindly
│       └── "not_triggered" (train only) → benign; try later
└── No (exception raised)
    └── Which class?
        ├── ProtocolError → transport failed (binary missing, perms)
        ├── ExpectedError → CLI rejected your input
        └── InternalError → CLI crashed (bug)
```

## Python — catching the right class

```python
from sulis_execution import (
    SulisExecution,
    ExpectedError,
    InternalError,
    ProtocolError,
    BinaryNotFoundError,        # subclass of ProtocolError
    InvalidArgumentError,       # subclass of ExpectedError
    UnexpectedOutputError,      # subclass of InternalError
)

client = SulisExecution(repo_root='.', project='my-project')

try:
    result = client.pipeline.run(
        wp='WP-001',
        branch='feat/wp-001-x',
        dev_sha_at_creation='abc123',
        deploy_workflow='Deploy to Dev',
    )

    # "blocker" is a normal result, NOT an exception
    if result.outcome == 'blocker':
        notify_team(f"Pipeline blocker for WP-001: {result.blocker_reason}")
        raise SystemExit(1)

    print(f"Shipped to {result.deploy_url}")

except BinaryNotFoundError as e:
    # The wpx-* binary isn't on PATH; setup problem
    print(f"Configure WPX_DIR or pass wpx_dir to the client: {e.message}")

except ExpectedError as e:
    # CLI rejected the input — bad WP ID, wrong status, etc.
    print(f"Cannot run: {e.message}")
    print(f"Error code: {e.code}")
    print(f"Full context: {e.context}")

except InternalError as e:
    # CLI crashed — bug in the underlying tool
    print(f"Bug in CLI: {e.message}")
    print(f"Stderr tail: {e.context.get('stderr_tail')}")
    log_to_sentry(e)
```

## TypeScript — catching the right class

```typescript
import {
  SulisExecution,
  ExpectedError,
  InternalError,
  BinaryNotFoundError,
} from '@sulis-ai/execution';

const client = new SulisExecution({ repoRoot: '.', project: 'my-project' });

try {
  const result = client.pipeline.run({
    wp: 'WP-001',
    branch: 'feat/wp-001-x',
    dev_sha_at_creation: 'abc123',
    deploy_workflow: 'Deploy to Dev',
  });

  if (result.outcome === 'blocker') {
    notifyTeam(`Pipeline blocker: ${result.blocker_reason}`);
    process.exit(1);
  }
} catch (err) {
  if (err instanceof BinaryNotFoundError) {
    console.error(`Setup: ${err.message}`);
  } else if (err instanceof ExpectedError) {
    console.error(`Bad input: ${err.message}`);
  } else if (err instanceof InternalError) {
    console.error(`CLI crashed: ${err.message}`);
  } else {
    throw err;
  }
}
```

## Why "blocker" isn't an exception

The pipeline running successfully but reporting a deterministic
failure (CI red, deploy timed out, smoke failed) is different from
the SDK being unable to invoke the operation at all.

A blocker outcome means: "I ran your pipeline; the result is that
things didn't go well." That's still a return value the caller can
inspect — not a thrown exception.

An exception means: "I couldn't return a meaningful result for you."

This distinction matters because retry logic differs:
- Blocker: don't retry blindly; the underlying cause hasn't changed
- ProtocolError: investigate setup; retry only after fixing
- ExpectedError: adjust inputs; retrying with same inputs = same result
- InternalError: bug; log + escalate; don't retry

See [Error categories explained](../explanation/error-categories.md)
for the full design rationale.

## Common error codes (Expected)

| `error.code` | Meaning | Recovery |
|---|---|---|
| `wp_not_found` | WP isn't in INDEX.md | Add it first, or check the WP ID |
| `status_mismatch` | flip-status's `expected` didn't match actual | Refresh INDEX state; retry |
| `blocker_already_exists` | wpx-blocker write without --force | Use --force or archive first |
| `invalid_severity` | findings.register got a bad severity | Use CRITICAL / CONCERN / ADVISORY |
| `branch_already_exists` | sulis-change start on an existing branch | Use a different slug |

## See also

- [Error categories explained](../explanation/error-categories.md)
- [Blocker is not an exception](../explanation/blocker-not-exception.md)
- [Troubleshooting](../troubleshooting/)
