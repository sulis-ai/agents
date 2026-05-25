# Streaming roadmap (v0.3.0 — not yet implemented)

**Status:** Scoping doc / planning artifact. No code change yet.
**Targets:** sulis-execution SDK v0.3.0.
**Date:** 2026-05-22

## Why this exists

In v0.2.0, the SDK's transport (subprocess + JSON-on-stdout) is
synchronous: the CLI runs to completion, then emits a final JSON
envelope; the SDK reads it and returns. That works for short
operations but doesn't fit long-running ones.

Two long-running operations don't migrate to MCP in v0.2.0:

- `pipeline.run` (Steps 8-10 for one WP, 15-45 min wall time)
- `train.run` (Steps 8-10 for a batch, 20-60 min wall time)

The execution skills keep them as Bash invocations with
`run_in_background: true` and a 90-min timeout cap. The harness
notifies the calling session when the background Bash exits. That's
how we get long-wait behaviour today.

MCP tool calls are synchronous request/response. There's no
equivalent to `run_in_background` in v0.2.0's MCP integration. To
migrate the long-running ops to MCP, the SDK needs streaming with
progress notifications.

## What the MCP spec gives us

MCP 2025-06-18 supports **progress notifications** — a server can
emit `notifications/progress` messages mid-call. The Anthropic MCP
Python SDK exposes `Context.report_progress()` for this. So the
target shape is:

1. Client calls `pipeline_run` (or `train_run`)
2. Server streams `notifications/progress` events as steps complete
   (CI poll, rebase, merge, deploy poll, health check, smoke test)
3. Server emits the final result when done

The client sees: a stream of progress events, then the final typed
result.

## What needs to change (5 phases)

### Phase A — CLI tools emit NDJSON progress

**Files:** `plugins/sulis-execution/scripts/wpx-pipeline`,
`plugins/sulis-execution/scripts/wpx-train`.

Today the CLI tools emit one JSON envelope to stdout at completion.
For streaming, they need to emit NDJSON (newline-delimited JSON) —
one event per line — during execution, with the final result as the
last line.

Event shape (proposal):

```json
{"type": "progress", "step": "ci_poll", "elapsed_s": 30, "message": "Polling CI for feat/wp-001 (attempt 1 of 30)"}
{"type": "progress", "step": "rebase", "elapsed_s": 35, "message": "Rebasing onto origin/dev (no change since worktree creation)"}
{"type": "progress", "step": "merge", "elapsed_s": 40, "message": "Squash-merged to dev as abc123def"}
...
{"type": "result", "data": {"result": { ... }}, "ok": true}
```

Backward compatibility: a `--no-stream` flag preserves the v0.2.0
behaviour (single envelope at end). The existing skill Bash
invocations would explicitly set `--no-stream` until they migrate.

**Estimated effort:** 4-6 hours. Touches the main loops in both
tools; requires care around stdout buffering (line-buffered, flush
after each event).

### Phase B — Python SDK transport supports streaming

**Files:** `sdk/python/sulis_execution/transport.py`,
`sdk/python/sulis_execution/resources/pipeline.py`,
`sdk/python/sulis_execution/resources/train.py`.

Add a `Stream[T]` generic class (sync) and `AsyncStream[T]` (async)
that wraps a subprocess's stdout reader. The resource method becomes:

```python
def run_streaming(
    self, *, wp, branch, ...
) -> Stream[PipelineProgressEvent | PipelineResult]:
    proc = self._transport.spawn_streaming("wpx-pipeline", "run", params)
    return Stream(proc, event_type_union)
```

The caller iterates:

```python
for event in client.pipeline.run_streaming(...):
    if event.type == "progress":
        print(f"  [{event.step}] {event.message}")
    elif event.type == "result":
        final = event.data
```

The non-streaming `run()` method stays for callers who don't need
progress.

**Estimated effort:** 6-8 hours. Need async-stdout reading, event
type discrimination, error handling mid-stream, timeout semantics
(per-event vs total).

### Phase C — TypeScript SDK mirror

**Files:** `sdk/typescript/src/transport.ts`,
`sdk/typescript/src/resources/pipeline.ts`,
`sdk/typescript/src/resources/train.ts`.

Same shape as Python: streaming iterator over child process stdout
parsing NDJSON. Native async iterators (`for await`) make this
clean in TypeScript.

**Estimated effort:** 5-7 hours.

### Phase D — MCP server forwards progress to MCP notifications

**Files:** `sdk/mcp-server/sulis_execution_mcp/server.py`.

When the MCP server invokes a streaming tool, it reads the NDJSON
stream from the CLI subprocess and emits each `progress` event as
an MCP `notifications/progress` via `Context.report_progress()`. The
final `result` event becomes the tool's response.

The MCP tool's `description` field documents that the tool emits
progress events; LLM clients that don't handle progress notifications
gracefully degrade (they just see the final result).

**Estimated effort:** 3-4 hours. Mostly forwarding logic; the MCP
Python SDK does the heavy lifting for the protocol-level
notifications.

### Phase E — Skills migrate long-running ops to MCP

**Files:** `plugins/sulis/skills/run-all/SKILL.md`,
`plugins/sulis/skills/run-wp/SKILL.md`,
`plugins/sulis/references/lifecycle.md`.

Replace the `Bash(... wpx-train run ... run_in_background: true)`
patterns with MCP tool calls. The agent sees progress notifications
mid-call (the harness surfaces them); the calling session stays
responsive instead of being parked for 30+ minutes.

The Bash fallback stays for non-MCP sessions, but `lifecycle.md`'s
"MCP vs Bash" table loses its long-running carve-out.

**Estimated effort:** 2-3 hours. Mechanical extension of the Track B
pattern from this session.

## Total scope

Roughly **20-28 hours** of work across 5 phases. Probably 5-7
commits matching the per-phase pattern of prior SDK rollouts.

This is a real v0.3.0 effort, not a "one afternoon" item.

## Decision

Defer for now. Tracked as v0.3.0 of the SDK. Triggers for revisiting:

- The current `run_in_background` pattern hits a real limitation
  (e.g., the harness's 90-min cap blocks a legitimate long run)
- A consumer asks for streaming progress in production use
- We're touching the CLI tools anyway for an unrelated change and the
  marginal cost of adding NDJSON output is low

Until then, v0.2.0's split (short ops via MCP; long-running ops via
Bash + `run_in_background`) is the supported pattern.

## Open questions

These need answers before Phase A can start:

1. **NDJSON-vs-SSE format.** NDJSON is simpler and fits subprocess
   transport. SSE (Server-Sent Events) is the HTTP convention. For
   subprocess we should use NDJSON; for any future HTTP transport,
   SSE. The Python and TypeScript SDKs should abstract over both.

2. **Progress event schema.** Proposed shape above (`{type, step,
   elapsed_s, message}`); needs validation against the actual
   wpx-pipeline / wpx-train internals (what events are even meaningful
   to emit). May want to schemaize as part of the OpenAPI spec.

3. **Mid-stream cancellation.** If the caller wants to cancel a
   running pipeline (e.g., kill the deploy poll early), what's the
   shape? MCP doesn't have a standard cancellation mechanism yet
   (per the 2025-06-18 spec). Could be deferred until needed.

4. **Backward compatibility for the wpx-pipeline CLI.** Existing
   callers (CI scripts, the executor agent's fallback path) need
   the v0.2.0 behaviour (single JSON envelope at end). The `--no-stream`
   flag handles this. Confirm this is the right default
   (stream by default vs no-stream by default).

## See also

- [Mental model](mental-model.md) — current SDK structure
- [Retry strategy](retry-strategy.md) — adjacent "why this works the
  way it does"
- [SDK spec — Part 8 (Streaming)](../../../docs/research/agent-consumable-sdk-spec.md)
  — the universal SDK spec's treatment of streaming, which v0.3.0 will
  finally implement
- [SDK spec — Part 4.3 (Subprocess + JSON-on-stdout)](../../../docs/research/agent-consumable-sdk-spec.md)
  — current binding; the Phase A change extends this to NDJSON
