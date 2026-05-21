# Why three error categories?

**Applies to:** sulis-execution v0.1.0

## The three categories

Per agent-consumable SDK spec v0.2.0 Part 3, every error fits exactly
one of three categories:

| Category | Class | Meaning | Recovery |
|---|---|---|---|
| `protocol` | `ProtocolError` | Transport failed; the operation never reached the CLI | Fix setup; retry |
| `expected` | `ExpectedError` | The CLI ran but reported a deterministic failure (validation, conflict, not-found) | Adjust inputs; don't retry same |
| `internal` | `InternalError` | The CLI crashed or produced an unexpected mode (bug) | Log; escalate; don't retry |

## Why not HTTP status codes?

The Anthropic SDK, OpenAI SDK, Stripe SDK, etc. all use HTTP-status-coded
error hierarchies: `BadRequestError(400)`, `NotFoundError(404)`,
`RateLimitError(429)`, etc.

That works because the transport is HTTP. The SDK can map status codes
directly to exception classes.

This SDK's transport is subprocess + JSON. The wire is exit codes 0/1/2,
not HTTP statuses. Forcing the same hierarchy here would be a category
error — there's no "401" for "wpx-pipeline rejected your arguments."

The three universal categories (Protocol / Expected / Internal) map
cleanly onto subprocess exit codes:

| Exit code | JSON envelope | Category |
|---|---|---|
| 0 | `ok: true` | Success (no exception) |
| 1 | `ok: true, outcome: blocker` | Success (no exception); inspect outcome |
| 1 | `ok: false, error: ...` | ExpectedError |
| 2 | (traceback on stderr) | InternalError |
| - (exec failed) | (no stdout) | ProtocolError |

And per the SDK spec, the same three categories also work for HTTP
(400-422 → Expected; 5xx → Internal; network failure → Protocol),
gRPC status codes, JSON-RPC error codes, library exceptions. Universal.

## When to catch what

```python
try:
    result = client.pipeline.run(...)
except ProtocolError:
    # Setup problem — investigate WPX_DIR, perms, binary existence
except ExpectedError:
    # CLI rejected the input — adjust the arguments
except InternalError:
    # CLI crashed — log + escalate; don't retry
```

The subclasses give finer granularity (BinaryNotFoundError under
Protocol, InvalidArgumentError under Expected, UnexpectedOutputError
under Internal). Catch by subclass when you need to handle a specific
case differently.

## Domain extensions

When domain logic needs more granularity than the canonical classes,
extend the right level:

```python
from sulis_execution import ConflictError  # canonical Expected subtype

class IndexStatusMismatchError(ConflictError):
    """Raised when `index.flip_status --expected X` finds status != X."""
```

The agent's mental model — "ConflictError means retry-after-refresh" —
ports across all wpx operations without each operation inventing its
own exception type.

## See also

- [Mental model](mental-model.md)
- [Blocker is not an exception](blocker-not-exception.md)
- [How to handle errors](../how-to/handle-errors.md)
