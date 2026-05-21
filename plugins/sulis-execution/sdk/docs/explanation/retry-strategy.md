# Why retries are disabled

**Applies to:** sulis-execution v0.1.0

The SDK's transport (subprocess) has retries explicitly disabled.

## Why

Networked SDKs (Anthropic, OpenAI, Stripe) enable retries by default
because their transports have transient failure modes:
- 429 rate limit → retry after backoff
- 503 service unavailable → retry after Retry-After header
- Network reset / DNS failure → retry on connection

The sulis-execution SDK's transport spawns local CLI processes that
operate on the filesystem + invoke local git / gh tools. Failure modes
aren't transient:

| Subprocess failure | Retrying with same inputs → |
|---|---|
| Binary not found | Same failure |
| Permission denied | Same failure |
| CLI exits 1 with `ok:false` (bad input) | Same failure |
| CLI exits 2 (crash) | Same failure |
| CLI exits 1 with `outcome:blocker` (e.g., CI red) | Same failure (CI is still red) |

Retrying without addressing the cause burns time.

## What the caller does instead

The wpx-pipeline and wpx-train themselves have internal retry budgets
(e.g., wpx-pipeline retries `git rebase` up to N times if dev has
advanced; wpx-train retries the CI poll within a configurable cap).
Those retries happen INSIDE the CLI, not from the SDK.

When a failure surfaces back to the SDK, it's a terminal failure that
needs human / agent decision-making — not blind retry.

## When you might want retries anyway

If you're polling for an external state change (e.g., waiting for a CI
status webhook to land), wrap your own retry loop:

```python
import time
from sulis_execution import SulisExecution, ExpectedError

client = SulisExecution(repo_root='.', project='my-project')

for attempt in range(10):
    try:
        result = client.train.queue_list()
        if result.eligible_count > 0:
            break
    except ExpectedError:
        # Something's wrong with the input; don't retry
        raise
    time.sleep(60)
```

This is application-level retry; the SDK stays simple.

## See also

- [Mental model](mental-model.md)
- The SDK spec at `../../../docs/research/agent-consumable-sdk-spec.md`
  (Part 4.3 — subprocess binding's retry conventions)
