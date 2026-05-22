# Mental model: how the SDK is organised

**Applies to:** sulis-execution v0.1.0

## The two axes

Per the agent-consumable SDK spec v0.2.0, every SDK has two independent
primitives:

1. **Schema axis** — what operations exist, what shapes their inputs and
   outputs take, what error categories are possible. Transport-agnostic.
2. **Transport axis** — how operations are invoked, how errors come back,
   how telemetry is conveyed. Schema-agnostic.

For this SDK:

- **Schema**: OpenAPI 3.1 at `sulis-execution.openapi.yaml` (38 operations,
  ~75 schemas). This is the source of truth.
- **Transport (default)**: Subprocess + JSON-on-stdout (v0.2.0 Part 4.3).
  The clients spawn the wpx-* CLI binaries; read JSON from stdout; map
  exit codes 0/1/2 to outcome categories.
- **Transport (LLM-facing)**: JSON-RPC over stdio / MCP (v0.2.0 Part 4.2).
  The MCP server wraps the same operations for LLM invocation.

Same operations; different wire. Pick the transport that matches who's
calling.

## Resource tree

The 38 operations are grouped into 10 resources:

```
client
├── pipeline          # wpx-pipeline    (1 op: run)
├── train             # wpx-train       (6 ops)
├── index             # wpx-index       (7 ops)
├── journal           # wpx-journal     (10 ops)
├── blocker           # wpx-blocker     (2 ops)
├── findings          # wpx-findings    (2 ops)
├── work_package      # wpx-wp          (2 ops)
├── worktree          # wpx-worktree    (2 ops)
├── lifecycle         # wpx-step12      (1 op: complete)
└── change            # sulis-change    (5 ops)
```

Resources are nouns; methods on resources are verbs (per the SDK spec's
naming convention).

## Sync vs async

Both shapes ship in both languages:

| Language | Sync class | Async class |
|---|---|---|
| Python | `SulisExecution` | `AsyncSulisExecution` |
| TypeScript | `SulisExecution` | `AsyncSulisExecution` |

Same resource tree, same method signatures — just await the async ones.

## What the SDK doesn't do

- **No retry logic.** The underlying tools are local filesystem + git
  operations. Transient retries that make sense for network APIs
  (429 / 503) don't apply. When something fails deterministically,
  retrying without addressing the cause just burns time. The caller
  (or the wpx-pipeline / wpx-train itself) decides when to retry.

- **No connection pooling.** Each operation spawns its own subprocess.
  Operations are seconds-to-minutes in duration; the process-spawn
  overhead is negligible.

- **No pagination.** No wpx operation paginates today. The list
  endpoints (queue_list, list_ready) return the full set; volumes are
  in tens, not thousands.

- **No streaming.** No wpx operation streams today. If `wpx-pipeline
  run` ever streams progress (rather than returning at completion),
  the streaming convention from the SDK spec applies; for v0.1.0,
  results are at-completion.

## See also

- [Error categories](error-categories.md)
- [Blocker is not an exception](blocker-not-exception.md)
- [Retry strategy](retry-strategy.md)
- [Field case conventions](field-case-conventions.md)
- The SDK spec at `../../../docs/research/agent-consumable-sdk-spec.md`
