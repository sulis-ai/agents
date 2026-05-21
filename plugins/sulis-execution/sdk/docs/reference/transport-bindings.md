# Transport bindings

**Applies to:** sulis-execution v0.1.0

The SDK v0.1.0 ships two transport bindings, both backed by the same
underlying CLI binaries.

## Subprocess + JSON-on-stdout (v0.2.0 Part 4.3)

**Used by:** Python client (`SulisExecution` / `AsyncSulisExecution`),
TypeScript client (`SulisExecution` / `AsyncSulisExecution`).

| Concern | Implementation |
|---|---|
| Invocation | argv + env vars; reads stdout for JSON; exits 0/1/2 |
| ProtocolError | Exec failed (binary missing, perms, exec failure, timeout) |
| ExpectedError | Exit 1 + `{ok: false, error}` |
| InternalError | Exit 2 + traceback on stderr |
| Retries | Disabled (local; no transient failures) |
| Telemetry | stderr stream; PID + timestamp form correlation ID |
| Authentication | Inherited from process (parent process trusted) |
| Streaming | Not implemented in v0.1.0 (no streaming wpx operations) |

**Reference implementation:** the wpx-* CLI tools are explicitly named
in the SDK spec v0.2.0 Part 4.3 as the canonical example.

## JSON-RPC over stdio / MCP (v0.2.0 Part 4.2)

**Used by:** MCP server (`sulis-execution-mcp`).

| Concern | Implementation |
|---|---|
| Invocation | MCP `tools/call` per operation |
| ProtocolError → JSON-RPC | Transport disconnect → JSON-RPC transport error |
| ExpectedError → MCP | Exit 1 + `ok:false` → `isError: true` result content (LLM sees) |
| InternalError → JSON-RPC | Exit 2 → JSON-RPC -32603 (server error) |
| Tool listing | `tools/list` returns 38 tools at server startup |
| Tool descriptions | OpenAPI `description` verbatim (LLM-audience) |
| Input/output schemas | OpenAPI `requestBody` / `responses.200` schemas, resolved + flattened |

**Two-channel error model** (per MCP spec 2025-06-18):
- Protocol errors raise as JSON-RPC errors (caller's MCP client sees them)
- Tool-execution errors return as `isError: true` result content (LLM sees them)

The MCP server bridges wpx exit codes to these two channels in
`sulis_execution_mcp/server.py`.

## Bindings deferred to future versions

| Binding | Why deferred |
|---|---|
| HTTP / REST (Part 4.1) | No HTTP server needed for local ops; would be a new process to manage |
| gRPC / Protobuf (Part 4.5) | Wire-level advantages don't matter at wpx's scale (kilobytes, seconds-to-minutes) |
| Library / in-process (Part 4.4) | Would require pulling git + gh into the host process; a bigger refactor |

If a future use case requires HTTP (e.g., a remote orchestrator), the
OpenAPI spec stays the same; a new HTTP server target binds to it.

## See also

- [Mental model](../explanation/mental-model.md)
- [Error categories](../explanation/error-categories.md)
- The SDK spec at
  [`../../../docs/research/agent-consumable-sdk-spec.md`](../../../docs/research/agent-consumable-sdk-spec.md)
  (Parts 4.1–4.5 detail every transport binding)
