# Getting Started with the TypeScript SDK

**Applies to:** sulis-execution v0.1.0 (`@sulis-ai/execution`)
**Time:** ~10 minutes
**You'll need:** Node.js 18+, npm, the underlying wpx-* CLI tools on PATH

## What you'll learn

1. Installing the TypeScript SDK
2. Making your first call (queue-list)
3. Handling errors with the canonical hierarchy
4. The async-only model (no sync variant)

## 1. Install

From a checkout of the marketplace:

```bash
cd plugins/sulis-execution/sdk/typescript
npm install
npm run build
```

Then link it into your own project:

```bash
npm link
cd /your/project
npm link @sulis-ai/execution
```

Or import directly from the build output for one-off use.

## 2. Construct a client

```typescript
import { SulisExecution } from '@sulis-ai/execution';

const client = new SulisExecution({
  repoRoot: '.',
  project: 'my-project',
});
```

If your wpx-* binaries live somewhere non-standard:

```typescript
const client = new SulisExecution({
  repoRoot: '.',
  project: 'my-project',
  wpxDir: '/Users/me/Documents/repos/agents/plugins/sulis-execution/scripts',
});
```

## 3. Your first call

```typescript
const result = client.train.queueList();
console.log(`Eligible: ${result.eligible_count}`);
for (const entry of result.eligible) {
  console.log(`  - ${entry.wp}: ${entry.reason}`);
}
```

Note the field names: `eligible_count` is `snake_case` because it's
preserved from the wire format. This is the parity rule with Python
— TypeScript does NOT auto-camelCase response fields. Method names
ARE `camelCase` (TS idiom): `queueList`, `flipStatus`, `recordPostdeploy`.

## 4. Sync + async

The TypeScript SDK ships sync (`SulisExecution`) using `spawnSync`
under the hood, AND async (`AsyncSulisExecution`) using a Promise
wrapper around `spawn`:

```typescript
import { AsyncSulisExecution } from '@sulis-ai/execution';

const client = new AsyncSulisExecution({
  repoRoot: '.',
  project: 'my-project',
});

const [eligibility, status, doctor] = await Promise.all([
  client.train.queueList(),
  client.train.status(),
  client.train.doctor(),
]);

console.log(
  `${eligibility.eligible_count} eligible, ` +
  `trigger: ${status.trigger_state}, ` +
  `${doctor.issue_count} issues`,
);
```

## 5. The blocker contract

Just as in Python: `outcome: blocker` is NOT an exception. It's part of
a successful operation's result.

```typescript
const result = await client.pipeline.run({
  wp: 'WP-001',
  branch: 'feat/wp-001-introduce-payments',
  dev_sha_at_creation: 'abc123def',
  deploy_workflow: 'Deploy to Dev',
  staging_url: 'https://staging.example.com',
  smoke_cmd: 'curl -sf https://staging.example.com/health',
});

if (result.outcome === 'blocker') {
  console.log(`Pipeline blocker: ${result.blocker_reason}`);
} else if (result.outcome === 'success') {
  console.log(`Shipped to ${result.deploy_url}`);
}
```

## 6. Exceptions

```typescript
import { ExpectedError, InternalError, BinaryNotFoundError } from '@sulis-ai/execution';

try {
  await client.index.flipStatus({
    wp: 'WP-001',
    to: 'done',
    expected: 'in_progress',
  });
} catch (err) {
  if (err instanceof ExpectedError) {
    console.log(`Cannot flip: ${err.message}`);
  } else if (err instanceof InternalError) {
    console.log(`CLI crashed: ${err.message}`);
  } else if (err instanceof BinaryNotFoundError) {
    console.log(`Setup: ${err.message}`);
  } else {
    throw err;
  }
}
```

Class names are identical to Python per the parity contract.

## What's next

- [How to handle errors](../../how-to/handle-errors.md)
- [Configuring the client](../../how-to/configure-client.md)
- [Error categories explained](../../explanation/error-categories.md)

## Failure modes to plan for

Same as Python — see [getting-started Python](../python/getting-started.md)
for the full list.
