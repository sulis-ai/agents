# Getting Started with the Python SDK

**Applies to:** sulis-execution v0.1.0
**Time:** ~10 minutes
**You'll need:** Python 3.10+, pip, the underlying wpx-* CLI tools on PATH

## What you'll learn

By the end of this tutorial, you'll have:

1. Installed the Python SDK
2. Made your first call (queue-list)
3. Handled both success and failure outcomes
4. Understood the difference between "blocker outcomes" and exceptions

## 1. Install

From a checkout of the marketplace:

```bash
pip install -e plugins/sulis-execution/sdk/python/
```

For testing setup:

```bash
pip install -e "plugins/sulis-execution/sdk/python/[test]"
```

Confirm the install:

```python
import sulis_execution
print(sulis_execution.__version__)  # 0.1.0
```

## 2. Construct a client

```python
from sulis_execution import SulisExecution

client = SulisExecution(
    repo_root='.',           # your repo root
    project='my-project',    # resolves .architecture/my-project/ paths
)
```

The client doesn't connect to anything at construction time — it just
records configuration. CLI binaries are looked up on first use (via
WPX_DIR env var or PATH).

If your wpx-* binaries live somewhere non-standard:

```python
client = SulisExecution(
    repo_root='.',
    project='my-project',
    wpx_dir='/Users/me/Documents/repos/agents/plugins/sulis-execution/scripts',
)
```

## 3. Your first call

Let's check what's queued for the next train:

```python
result = client.train.queue_list()
print(f"Eligible WPs: {result.eligible_count}")
for entry in result.eligible:
    print(f"  - {entry.wp}: {entry.reason}")
```

The result is a Pydantic v2 model. Field names match the wire format
(`snake_case`). You get autocomplete, validation, and `.model_dump()`
for free.

## 4. The blocker contract

The most important thing to know about this SDK: **`outcome: blocker`
is NOT an exception**.

```python
result = client.pipeline.run(
    wp='WP-001',
    branch='feat/wp-001-introduce-payments',
    dev_sha_at_creation='abc123def',
    deploy_workflow='Deploy to Dev',
    staging_url='https://staging.example.com',
    smoke_cmd='curl -sf https://staging.example.com/health',
)

# If the pipeline runs but reports a deterministic failure
# (CI red, deploy timed out, smoke failed), result.outcome is "blocker"
# and the SDK returns it as a normal result.
if result.outcome == 'blocker':
    print(f"Pipeline reported blocker: {result.blocker_reason}")
    # Your job: write a BLOCKER record, escalate, retry later, etc.
elif result.outcome == 'success':
    print(f"Shipped to {result.deploy_url}")
```

Exceptions are reserved for cases where the SDK couldn't return a
meaningful result:

```python
from sulis_execution import ExpectedError, InternalError, BinaryNotFoundError

try:
    result = client.index.flip_status(
        wp='WP-001', to='done', expected='in_progress'
    )
except ExpectedError as e:
    # The CLI rejected the input (e.g., status wasn't in_progress)
    print(f"Cannot flip: {e.message}")
    print(f"Context: {e.context}")
except InternalError as e:
    # The CLI crashed (bug in the underlying tool)
    print(f"CLI crashed: {e.message}")
except BinaryNotFoundError as e:
    # The wpx-* binary isn't on PATH and wpx_dir isn't set right
    print(f"Setup problem: {e.message}")
```

## 5. Async variant

For concurrent calls, use `AsyncSulisExecution`:

```python
import asyncio
from sulis_execution import AsyncSulisExecution

async def main():
    client = AsyncSulisExecution(repo_root='.', project='my-project')

    # Concurrently check three things
    eligibility, status, doctor = await asyncio.gather(
        client.train.queue_list(),
        client.train.status(),
        client.train.doctor(),
    )
    print(f"{eligibility.eligible_count} eligible, "
          f"trigger: {status.trigger_state}, "
          f"{doctor.issue_count} issues")

asyncio.run(main())
```

## What's next

- [How to handle errors](../../how-to/handle-errors.md) — full error
  hierarchy + when to catch which class
- [How to mock for testing](../../how-to/mock-for-testing.md) —
  using fake CLI binaries in tests
- [Error categories explained](../../explanation/error-categories.md)
  — why three categories, not HTTP status codes
- [Blocker outcomes explained](../../explanation/blocker-not-exception.md)
  — the contract behind why blocker is a result

## Failure modes to plan for

- **BinaryNotFoundError**: the wpx-* binary couldn't be located. Set
  `WPX_DIR` env or pass `wpx_dir=...` to the client.
- **ExpectedError**: the operation reached the CLI but reported a
  deterministic failure. Inspect `e.message` and `e.context.code`.
- **InternalError**: the CLI crashed (bug). Inspect stderr via
  `e.context['stderr_tail']`.
- **Pipeline/train outcome=blocker**: NOT an exception. Inspect
  `result.outcome` and `result.blocker_reason`.
