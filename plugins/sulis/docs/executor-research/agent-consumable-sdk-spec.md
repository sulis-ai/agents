# Agent-Consumable SDK Specification

**Version:** 0.3.0 (added monorepo install-graph section to Part 9)
**Date:** 2026-05-22
**Status:** Specification — implementation reference for agents building Sulis SDKs
**Audience:** Agents tasked with building or extending a Sulis-marketplace SDK
**Standards applied:** CP-01 (Convention Preference), the Critical Thinking Standard
(MECE / PG / BI / SI / CC / FR / HU / AT / OI)

---

## What an agent calling a tool actually needs (OI — outside-in opening)

Before any conventions, the outside-in question: what does an agent calling a tool
through an SDK actually need?

1. **A typed operation surface.** The agent needs to know what operations exist,
   what shapes their inputs take, what shapes their outputs take. Without types,
   the agent guesses; guesses are wrong; loops happen.
2. **A typed error model.** When something fails, the agent needs to know whether
   to retry, give up, or escalate. A single string isn't enough.
3. **Deterministic invocation.** Same inputs, same call → same behaviour. No
   hidden state in the SDK itself.
4. **A way to learn the surface at runtime.** Documentation, schemas, tool
   descriptions — readable by the LLM at decision time, not just authored
   ahead of time.
5. **Predictable degradation.** When the transport stutters (network, process
   crash, file lock), the SDK degrades the same way every time.

Notice none of these mention HTTP. They're all transport-agnostic. The transport
(HTTP, MCP-over-stdio, subprocess, library call) is one of several ways to
satisfy these needs — but the needs themselves are universal.

This spec is organised around those five needs and the two structural primitives
that satisfy them: the **schema layer** (operations + types + errors) and the
**transport binding** (how operations are invoked, how errors come back, how
telemetry is conveyed).

---

## Scope and Boundaries (HU + CC honesty disclosure)

This spec covers the design and conventions for SDKs that:

- Expose a typed operation surface to agents (LLMs, scripts, other tools)
- Are generated from a source-of-truth schema, not hand-written
- Ship in at least two languages (Python + TypeScript baseline)
- Need to handle errors, retries, telemetry, and authentication in a consistent way

This spec does **not** cover:

- Server-side API design (this is the *client* SDK perspective)
- Database migration tooling (different concern, different conventions)
- Configuration management (env vars, secret rotation) beyond the SDK layer
- Build tooling (CI, release automation) — handled by other marketplace standards

**Confidence tiers per major claim** (CC):

| Claim | Tier | Reasoning |
|---|---|---|
| The schema/transport split applies universally | SUPPORTED | Smithy (AWS), gRPC, GraphQL all separate schema from transport; the pattern is industry-established |
| The outcome-category error model applies universally | SUPPORTED | Generalised from Python's exception hierarchy + gRPC's status canonical codes + JSON-RPC's error codes + POSIX exit codes |
| Pydantic v2 for Python responses (when responses are JSON-shaped) | SUPPORTED | Stainless-generated SDKs + dataclasses-json + msgspec all converge; not universal because binary wire formats use different decoders |
| `snake_case` field preservation when wire is JSON | SUPPORTED for JSON wire | Anthropic, OpenAI, Stripe, GitHub Octokit; **CONTRADICTED** for binary wire (Protobuf has no case) |
| OpenAPI 3.1 as the schema language for HTTP transports | VALIDATED | Industry-standard; multi-codegen support |
| OpenAPI 3.1 as the schema language for non-HTTP transports | EMERGING | Possible (Smithy supports protocol-agnostic), but the dominant non-HTTP IDLs are Protobuf, GraphQL SDL, Avro, native language types |
| MCP-over-stdio as the right transport for LLM-facing local tools | SUPPORTED | Anthropic's design choice; growing ecosystem; canonical for agent tooling |
| 2-retry-with-exponential-backoff default for networked transports | SUPPORTED | Anthropic + OpenAI + Stripe + Twilio; **NOT APPLICABLE** for local transports (subprocess, library) |

---

## TL;DR (PP — pyramid)

**Conclusion:** Build SDKs from a two-axis source of truth — a transport-agnostic
schema layer (operations + types + errors-as-categories) and an explicit transport
binding (HTTP, JSON-RPC, subprocess, library, …). Generate Python (Pydantic v2
when shapes are JSON-based) and TypeScript (typed interfaces) clients from the
schema. Map each transport's native error vocabulary onto a universal three-
category error model (Protocol / Expected / Internal). Adopt a deeper MCP-over-stdio
transport binding for LLM-facing tools.

**Three supporting legs:**

1. **Separation of concerns:** Operation/type/error definitions are transport-agnostic
   and reusable; transport bindings are interchangeable. Same operations can ship
   over HTTP for remote API access and over MCP for LLM invocation.
2. **Outcome-category errors port across transports:** Three categories (Protocol /
   Expected / Internal) work for HTTP statuses, subprocess exit codes, JSON-RPC
   error codes, and language exceptions. Agents handle errors the same way regardless
   of transport.
3. **Language parity is real but bounded:** Python and TypeScript clients keep
   identical resource trees, identical error class names, identical wire-format
   field case. They differ in async model (Python has sync + async; TS is async-only)
   and runtime validation (Python uses Pydantic; TS trusts the wire).

**What changed from v0.1.0:** The previous spec was HTTP-shaped. It conflated
transport (HTTP) with schema (OpenAPI 3.1), tied the error hierarchy to HTTP status
codes, and presented HTTP-specific patterns as universal. v0.2.0 separates the axes,
makes errors transport-agnostic, elevates MCP from a codegen target to a transport
peer, and adds per-transport bindings for HTTP, JSON-RPC, subprocess, and library
calls (with briefer notes on gRPC, GraphQL, WebSocket, database driver, and
message queue transports).

---

## Part 1 — The two axes (PG — primitive grounding)

An SDK has two independent primitives. They were conflated in v0.1.0; this version
keeps them separate.

| Axis | Defines | Examples |
|---|---|---|
| **Schema axis** | What operations exist, what shapes inputs/outputs take, what error categories exist | OpenAPI 3.1, Protobuf, GraphQL SDL, Smithy, JSON Schema alone, language-native types |
| **Transport axis** | How operations are invoked, how errors come back, how telemetry is conveyed | HTTP, gRPC, JSON-RPC, MCP-over-stdio, subprocess, library, WebSocket, message queue, database protocol |

**Independence test (PG-02):** Can you change the transport without changing the
operation set? Yes — Smithy demonstrates this with `@http` / `@protobuf` / `@awsQuery`
protocol bindings. Can you change the operation set without touching the transport?
Yes — adding a new operation doesn't require switching from HTTP to gRPC.

**Irreducibility check (PG-04):** Could schema and transport collapse into one
primitive? OpenAPI 3.1 conflates them by tying schemas to HTTP paths/verbs/responses.
But Smithy, GraphQL, and gRPC all keep them separate. The convergence on separation
is the evidence: these are two primitives at the same level of analysis.

**Level of analysis:** This is the *SDK specification* level. At lower levels
(within HTTP, within gRPC), the schema axis splits further (e.g., URL paths vs JSON
bodies in HTTP). At higher levels (API portfolio management), the transport axis
splits further (versioning policy, deprecation timelines). This spec stays at the
SDK level.

---

## Part 2 — The schema layer (transport-agnostic)

An SDK's operations and types are described in a schema language. The schema language
is chosen to fit the transport — but the *operations themselves* are transport-agnostic.

### 2.1 What the schema layer defines

| Concept | Required? | Description |
|---|---|---|
| **Operations** | MUST | Named units of behaviour. `pipelineRun`, `messagesCreate`, `userListByOrg`. |
| **Input types** | MUST | Shape of each operation's input. |
| **Output types** | MUST | Shape of each operation's success result. |
| **Error categories** | MUST | The three universal categories (Protocol / Expected / Internal) plus any domain errors. |
| **Operation metadata** | MUST | Description, summary, deprecation status. The description is the LLM-facing prompt when this surface is exposed via MCP. |
| **Versioning** | SHOULD | Operations and types have version numbers; deprecations carry forward warnings. |
| **Authentication declarations** | SHOULD | Which operations require auth; what auth scheme(s). Bound to transport in Part 4. |
| **Pagination declarations** | SHOULD | Which operations return collections; how to iterate. |
| **Streaming declarations** | SHOULD | Which operations stream output; which accept streamed input. |

### 2.2 Schema languages — established options

Per CP-01, the agent picks a schema language matching the transport. Multiple
languages are established conventions; the spec doesn't mandate one.

| Schema language | Established for | Codegen ecosystem |
|---|---|---|
| **OpenAPI 3.1** | HTTP/REST (validated); also usable for adjacent transports | openapi-python-client, openapi-typescript, openapi-generator |
| **Protobuf (proto3)** | gRPC; also wire-format for many high-performance APIs | `protoc` + per-language plugins (`protoc-gen-go`, etc.); buf |
| **GraphQL SDL** | GraphQL APIs | graphql-codegen |
| **Smithy IDL** | Protocol-agnostic; AWS's IDL | Smithy CLI; multi-protocol bindings (HTTP, gRPC, MQTT, RPC) |
| **JSON Schema (alone)** | Any transport carrying JSON; standard for MCP tool inputs/outputs | ajv (validation), pydantic (Python), zod (TypeScript) |
| **AsyncAPI 3.0** | Message-driven APIs (Kafka, NATS, MQTT, WebSocket) | asyncapi-generator |
| **Language-native types** | Library/in-process SDKs | None needed; the language *is* the schema |

### 2.3 Schema authoring conventions (apply across languages)

These hold regardless of which schema language you pick:

- **Operations are nouns + verbs:** `messagesCreate`, `userList`, not `create` /
  `getThings`. Camel- or snake-case per language convention.
- **Required fields are explicit.** Don't rely on default "optional unless stated."
- **Discriminated unions for polymorphic shapes.** Tagged unions with a `type`
  discriminator. Sum types in the generated language.
- **Descriptions are LLM-facing.** Write operation descriptions for an LLM as the
  audience. Lead with intent, list inputs by name, name common outcomes, mention
  failure modes.
- **Versioning is additive within a major version.** Adding optional fields and new
  operations doesn't break consumers; renaming or removing requires a major bump.

### 2.4 When you don't have a schema language at all

For library/in-process SDKs, the schema language is the host language's type
system itself (TypedDict, Pydantic models in Python; interfaces + types in
TypeScript). This works but loses portability — you can't cross-generate clients
in other languages without re-authoring the types.

For wpx today, the schema language is implicit: dataclasses in `_wpxlib.py`
plus the CLI argument tables. The migration path is to lift those into an
explicit schema (any of the above) so cross-language client generation becomes
mechanical.

---

## Part 3 — The error model: outcome categories (transport-agnostic)

Three universal error categories, applicable across all transports. Each transport
maps its native error vocabulary onto these three.

### 3.1 The three categories

| Category | Meaning | Recovery |
|---|---|---|
| **ProtocolError** | The transport itself failed before the operation could run. Network down, process crashed before starting, MCP server unreachable, file locked. | Caller decides — usually retry with backoff if the transport supports it; otherwise escalate. |
| **ExpectedError** | The operation reached the implementation but returned a deterministic failure. Validation error, not-found, conflict, business-rule violation. | Caller adjusts inputs or escalates. Retrying with same inputs will produce the same error. |
| **InternalError** | The operation crashed or produced an unexpected failure mode. Bug in the implementation; should not happen. | Caller logs and escalates; usually don't retry. |

These three are MECE: every failure can be classified into exactly one category.

### 3.2 Mapping per transport

Each transport binds its native error vocabulary onto the three categories.

| Transport | ProtocolError | ExpectedError | InternalError |
|---|---|---|---|
| **HTTP** | Network failure, DNS, TLS, connection refused, HTTP 502/503/504 | HTTP 400, 401, 403, 404, 409, 422, 429 | HTTP 500, 501 |
| **JSON-RPC (incl. MCP)** | Transport disconnected, server didn't respond | JSON-RPC error codes -32600..-32603 (parse / invalid request / method not found / invalid params); tool result with `isError: true` | JSON-RPC code -32000..-32099 (server error); uncaught exception |
| **Subprocess (e.g. wpx)** | Exec failed (binary not found, permission denied) | Exit code 1 + structured `{ok: false, error}` JSON | Exit code 2 + traceback on stderr |
| **gRPC** | Channel closed, `UNAVAILABLE`, `DEADLINE_EXCEEDED`, network errors | `INVALID_ARGUMENT`, `NOT_FOUND`, `ALREADY_EXISTS`, `PERMISSION_DENIED`, `FAILED_PRECONDITION`, `RESOURCE_EXHAUSTED` | `INTERNAL`, `UNKNOWN`, `DATA_LOSS` |
| **GraphQL** | Network failure, schema mismatch | `errors[]` with categorisation in extensions | Partial data with `errors[]` containing internal-server-error |
| **Library (in-process)** | N/A (no transport) | Domain-specific exceptions: `ValueError`, `NotFoundError`, `ConflictError` | `RuntimeError`, uncaught exceptions, `AssertionError` |
| **WebSocket** | Connection closed, ping timeout | Application-level error message | Server-side crash, protocol violation |
| **Database driver** | `OperationalError`, connection lost | `IntegrityError`, `ProgrammingError` (your SQL), constraint violations | `InternalError`, driver crash |
| **Message queue** | Broker unreachable, partition lost | Message rejected, schema validation failure | Consumer crash, dead-letter |

### 3.3 The Python class hierarchy (consistent across transports)

```
{SDKName}Error (base)
├── ProtocolError
│   ├── ConnectionError      # transport-level connection failure
│   ├── TimeoutError         # transport-level timeout
│   └── TransportError       # other transport-level
├── ExpectedError
│   ├── ValidationError      # input shape wrong
│   ├── AuthenticationError  # not authenticated
│   ├── PermissionError      # authenticated but not authorised
│   ├── NotFoundError        # resource doesn't exist
│   ├── ConflictError        # resource conflict / idempotency mismatch
│   ├── RateLimitError       # too many requests
│   └── BusinessError        # domain-specific (extend with subclasses)
└── InternalError
    ├── ServerError          # the remote service crashed
    └── UnexpectedError      # we got something we couldn't categorise
```

The TypeScript class hierarchy mirrors this exactly with identical class names.

### 3.4 Domain errors extend the canonical hierarchy

If your domain has business-logic errors that don't fit the seven `ExpectedError`
subtypes cleanly, define them as further subclasses:

```python
class IdempotencyKeyMismatchError(ConflictError):
    """Raised when an Idempotency-Key is reused with a different request body."""

class SubscriptionExpiredError(PermissionError):
    """Raised when a request requires an active subscription."""
```

Don't invent a parallel hierarchy. Extending the canonical one preserves the
agent's mental model across all SDKs in the marketplace.

### 3.5 Error fields (same across categories)

Every error exposes:

| Field | Type | Notes |
|---|---|---|
| `message` | string | Human-readable |
| `category` | enum | `protocol` / `expected` / `internal` |
| `transport_code` | string | The transport's native code (HTTP status, exit code, gRPC status, etc.) |
| `correlation_id` | string | Request ID for HTTP; PID + timestamp for subprocess; trace ID for gRPC; null for library |
| `body` | object | Parsed structured detail when available |
| `code` | string | Domain-specific code if present |

### 3.6 Why this works (AT — adversarial check)

**Could it fail?** Yes, in two ways:

1. **A transport with no failure mode that fits ProtocolError.** Library calls,
   for instance. The `ProtocolError` category exists but is never raised for
   library SDKs. This is intentional — the category is reserved for transport
   failures and stays empty when there's no transport. Agents that handle
   `ProtocolError` consistently still work; library SDKs simply never need
   that branch.

2. **A transport with failure modes that span categories.** WebSocket close
   codes are tricky — code 1006 (abnormal closure) is Protocol; code 1008
   (policy violation) is Expected; code 1011 (internal error) is Internal.
   The mapping table in 3.2 captures this; per-transport binding sections in
   Part 4 elaborate.

---

## Part 4 — Transport bindings

Per-transport sections. Each binding specifies how operations are invoked, how
errors are surfaced and mapped, how retries work (if at all), how telemetry is
conveyed, and how authentication is handled.

### 4.1 HTTP / REST

| Concern | Convention |
|---|---|
| **Invocation** | HTTP request to a path + verb; JSON request body for POST/PUT/PATCH; query params for GET/DELETE. |
| **Schema language** | OpenAPI 3.1 (or Smithy with `@http` binding) |
| **ProtocolError** | Network failure, DNS, TLS, 502/503/504 |
| **ExpectedError** | 400, 401, 403, 404, 409, 422, 429 |
| **InternalError** | 500, 501 |
| **Retries** | Enabled by default. `max_retries=2`. Exponential backoff. Honours `Retry-After` and `Retry-After-Ms` headers. Retries on 408, 409, 429, 5xx — and ProtocolError. |
| **Telemetry vehicle** | Headers. Outbound: `x-{vendor}-arch`, `x-{vendor}-lang`, `x-{vendor}-version`, `x-{vendor}-retry-count`. Inbound: `request-id` surfaced on errors. |
| **Authentication** | Bearer token in `Authorization` header; OAuth 2.1; API key in header; mutual TLS. |
| **Idempotency** | `Idempotency-Key` header. Caller sends a UUID; server deduplicates. |
| **Streaming** | Server-Sent Events (SSE) or chunked HTTP. |
| **Pagination** | Cursor or page+limit query params. Per-endpoint declaration. |

**Sources cited (independent):**
- [RFC 7231 — HTTP/1.1 Semantics and Content](https://datatracker.ietf.org/doc/html/rfc7231)
- [OpenAPI Initiative — OpenAPI 3.1.0 spec](https://spec.openapis.org/oas/v3.1.0)
- [Anthropic Python SDK error handling](https://github.com/anthropics/anthropic-sdk-python)
- [Stripe API conventions](https://stripe.com/docs/api/errors)
- [Twilio SDK retry policy](https://www.twilio.com/docs/usage/troubleshooting/error-codes)

### 4.2 JSON-RPC (including MCP-over-stdio)

| Concern | Convention |
|---|---|
| **Invocation** | JSON-RPC 2.0 request object (`{jsonrpc: "2.0", method, params, id}`); response with `result` or `error`. |
| **Schema language** | JSON Schema for params and result. MCP's tool advertisement uses `inputSchema` + `outputSchema` (both JSON Schema). |
| **ProtocolError** | Transport disconnected; server didn't respond within timeout; JSON parse failure. |
| **ExpectedError** | JSON-RPC error codes -32700 (parse error), -32600 (invalid request), -32601 (method not found), -32602 (invalid params), -32603 (internal error). MCP tool results with `isError: true`. |
| **InternalError** | JSON-RPC codes -32000 to -32099 (server-implementer-defined errors); uncaught server exception. |
| **Retries** | Not enabled by default for stdio transport (no transient transport failures expected). Enabled when JSON-RPC runs over HTTP. |
| **Telemetry vehicle** | JSON-RPC notifications (`method` without `id`). Server pushes log events; client consumes structurally. |
| **Authentication** | Transport-dependent: stdio inherits process auth (the parent process is trusted); HTTP/WebSocket transports apply HTTP/WebSocket auth conventions. |
| **Idempotency** | Use the `id` field as a sentinel; servers MAY deduplicate by ID. |
| **Streaming** | MCP supports streaming via progress notifications. JSON-RPC over HTTP can use chunked HTTP or SSE for streaming results. |
| **Pagination** | MCP `tools/list` uses `cursor` + `nextCursor`. Application-defined for tool results. |

**Special note: MCP is the canonical agent-facing transport for local tools.**
MCP advertises tools via `tools/list` (with name, title, description, inputSchema,
outputSchema, annotations) and invokes them via `tools/call`. The two error
channels (JSON-RPC protocol errors vs `isError: true` result content) map cleanly
onto the three categories: protocol-error code -32600/-32601/-32602 → `ExpectedError`
(invalid request); -32603 / -32000..-32099 → `InternalError`; transport disconnect →
`ProtocolError`; `isError: true` in result content → `ExpectedError` with the
error text in the content body.

**Sources cited (independent):**
- [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification)
- [Model Context Protocol — overview](https://modelcontextprotocol.io/)
- [MCP spec, tools (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [Language Server Protocol error conventions](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#errorCodes)

### 4.3 Subprocess + JSON-on-stdout (the wpx pattern)

| Concern | Convention |
|---|---|
| **Invocation** | Process invoked with argv + optional stdin; reads stdout for JSON result; exits with code 0/1/2. |
| **Schema language** | JSON Schema for input (argv → JSON) and output (stdout JSON). |
| **ProtocolError** | Exec failed (binary not found, permission denied); process killed by signal; no JSON produced on stdout. |
| **ExpectedError** | Exit code 1 with JSON `{ok: false, error: "...", context: {...}}` on stdout. |
| **InternalError** | Exit code 2 with traceback on stderr. |
| **Retries** | Disabled by default. Local processes don't have transient transport failures. Caller decides per-operation. |
| **Telemetry vehicle** | stderr stream. Structured log lines (`[ISO-8601] message`). PID + timestamp form correlation ID. |
| **Authentication** | Inherited from process — the calling process is trusted. For finer scope: pass auth via env vars or short-lived tokens in argv. |
| **Idempotency** | Application-level. Inputs are deterministic by construction (argv is a function of caller). |
| **Streaming** | Line-delimited JSON on stdout (one event per line, newline-terminated). |
| **Pagination** | N/A typically; if needed, application-defined and rare for subprocess tools. |

**Sources cited (independent):**
- POSIX exit code conventions (sysexits.h)
- [The Twelve-Factor App — section XI Logs](https://12factor.net/logs)
- jq's JSON-stdout output pattern
- AWS CLI's structured output pattern
- The wpx-* tools in this marketplace as the established pattern

**The wpx-* tools are the reference implementation** of this transport binding.
The error model maps directly: exit code 1 + `{ok: false}` = ExpectedError;
exit code 2 + traceback = InternalError; binary not found / permission denied
= ProtocolError.

### 4.4 Library (in-process function calls)

| Concern | Convention |
|---|---|
| **Invocation** | Direct function call in the host language. No serialisation. |
| **Schema language** | Host language's type system (Python TypedDict / Pydantic; TS interfaces). |
| **ProtocolError** | Not applicable. The category exists in the hierarchy but is never raised. |
| **ExpectedError** | Domain exceptions raised: `ValidationError`, `NotFoundError`, `ConflictError`, etc. |
| **InternalError** | Uncaught exceptions; `RuntimeError`, `AssertionError`. |
| **Retries** | Not applicable. No transient failures. |
| **Telemetry vehicle** | Structured logging (e.g. Python's `logging` module; pino in Node). |
| **Authentication** | Inherited from process. The library is trusted by virtue of being imported. |
| **Idempotency** | Application-level; the library doesn't deduplicate. |
| **Streaming** | Generators/iterators in Python; async iterators in TypeScript. |
| **Pagination** | Iterator-based, lazy. Caller iterates; library fetches under the hood. |

**Sources cited (independent):**
- The Python `requests` library (canonical in-process SDK)
- pydantic v2 + the Pydantic ecosystem
- The standard library `subprocess` module's error model
- npm-style library conventions (no auth, no retries, no transport)
- Numpy, Pandas as library SDKs for data

**Library SDKs are NOT "agent-consumable" in the same sense as the other
transports** — they're not invocable by an LLM from outside the host language.
But they are still SDKs in the broader sense and this spec covers them so the
schema/transport split stays universal.

### 4.5 gRPC / Protobuf

| Concern | Convention |
|---|---|
| **Invocation** | Binary Protobuf-encoded request over HTTP/2; binary response. |
| **Schema language** | Protobuf 3 (proto3). Service definitions in `.proto` files. |
| **ProtocolError** | Channel closed, `UNAVAILABLE`, `DEADLINE_EXCEEDED`, certificate errors. |
| **ExpectedError** | gRPC status codes: `INVALID_ARGUMENT`, `NOT_FOUND`, `ALREADY_EXISTS`, `PERMISSION_DENIED`, `FAILED_PRECONDITION`, `OUT_OF_RANGE`, `RESOURCE_EXHAUSTED`, `UNAUTHENTICATED`. |
| **InternalError** | `INTERNAL`, `UNKNOWN`, `DATA_LOSS`. |
| **Retries** | Enabled by default for idempotent operations; retries `UNAVAILABLE`, `DEADLINE_EXCEEDED`. |
| **Telemetry vehicle** | gRPC metadata (headers/trailers); OpenTelemetry trace context standard. |
| **Authentication** | Token via metadata; mTLS at channel level; ALTS (Google's transport-level auth). |
| **Idempotency** | Application-level. gRPC doesn't provide a built-in idempotency key. |
| **Streaming** | Server-stream / client-stream / bidirectional-stream as first-class. |
| **Pagination** | Application-defined; commonly cursor-style. |

**Sources cited (independent):**
- [gRPC documentation](https://grpc.io/docs/)
- [gRPC Status canonical codes](https://grpc.github.io/grpc/core/md_doc_statuscodes.html)
- [Buf — modern Protobuf tooling](https://buf.build/)
- [ConnectRPC — gRPC-compatible alternative](https://connectrpc.com/)

**Wire-format note:** gRPC's wire is binary Protobuf. The "snake_case preserved
from wire" rule from HTTP doesn't apply — Protobuf has no case at the wire level
(it's tag-numbered fields). The generated language convention takes over:
`snake_case` in Python (proto convention); `camelCase` in TypeScript.

### 4.6 GraphQL

| Concern | Convention |
|---|---|
| **Invocation** | HTTP POST with a query/mutation string in the request body. |
| **Schema language** | GraphQL SDL. |
| **ProtocolError** | HTTP-level (4.1). |
| **ExpectedError** | `errors[]` array in response with `extensions.code` (UNAUTHENTICATED / FORBIDDEN / NOT_FOUND / BAD_USER_INPUT). |
| **InternalError** | `errors[]` array with `extensions.code = INTERNAL_SERVER_ERROR`; partial data may still be returned. |
| **Retries** | Per-operation; idempotent queries can retry, mutations should not. |
| **Telemetry vehicle** | HTTP headers (per 4.1) + optionally trace context in request body. |
| **Authentication** | HTTP-level (Bearer, cookie). |
| **Idempotency** | Application-level via mutation key. |
| **Streaming** | GraphQL Subscriptions over WebSocket. |
| **Pagination** | Connection/edge convention (Relay-style). |

**Sources cited:**
- [GraphQL specification](https://spec.graphql.org/)
- [The GraphQL Error spec](https://spec.graphql.org/October2021/#sec-Errors)
- [Apollo conventions](https://www.apollographql.com/docs/apollo-server/data/errors/)

### 4.7 WebSocket / bidirectional streaming

| Concern | Convention |
|---|---|
| **Invocation** | Long-lived connection; messages flow both ways. |
| **Schema language** | AsyncAPI 3.0 (for typed messages); JSON Schema for individual message bodies. |
| **ProtocolError** | Close codes 1006 (abnormal closure), 1011 (server error during handshake), 1015 (TLS failure). |
| **ExpectedError** | Close codes 1008 (policy violation), 1003 (unsupported data). Application-level error messages. |
| **InternalError** | Close code 1011 from server. |
| **Retries** | Reconnect with backoff on disconnect. |
| **Telemetry vehicle** | Initial HTTP upgrade headers carry telemetry; subsequent in-message metadata. |
| **Authentication** | HTTP upgrade auth (Bearer, cookie); token in first message. |
| **Idempotency** | Application-level. |
| **Streaming** | Native — that's the point. |
| **Pagination** | Less common; typically streamed continuously. |

**Sources cited:**
- [RFC 6455 — The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [AsyncAPI specification](https://www.asyncapi.com/)

### 4.8 Database driver / message queue (briefer)

These are SDK-shaped but rarely "agent-consumable" — they're typically wrapped by
higher-level libraries. Still worth noting:

**Database driver** (PEP 249, JDBC, ADO.NET pattern):
- Connection-based; cursor-based result iteration
- ProtocolError: connection lost, driver crash
- ExpectedError: `IntegrityError`, `ProgrammingError`, constraint violations
- InternalError: driver internal panic
- Standard interface: `connect()` → `cursor()` → `execute()` → `fetch()`

**Message queue** (Kafka, NATS, RabbitMQ, MQTT):
- Topics, partitions, consumer groups
- AsyncAPI for typed schemas
- ProtocolError: broker unreachable, partition lost
- ExpectedError: message rejected (schema validation)
- InternalError: consumer crash → message goes to dead-letter
- Retries: built-in dead-letter + redelivery semantics

---

## Part 5 — Per-language conventions

Per-language conventions transcend transport in most respects (Pydantic v2 is
Pydantic v2 whether the wire is HTTP or gRPC). Where transport matters,
explicit notes.

### 5.1 Python

| Concern | Convention | Transport notes |
|---|---|---|
| **Type validation** | Pydantic v2 models for JSON-shaped responses. msgspec or dataclasses for binary or performance-critical cases. | Binary wire (Protobuf) uses generated Pydantic-from-proto adapters or native protobuf classes. |
| **Naming (fields)** | `snake_case` for fields when wire is JSON. Preserved from wire. | Binary wire has no case — generator converts to language idiom (`snake_case`). |
| **Naming (methods)** | `snake_case` always. | Across all transports. |
| **Naming (classes)** | `PascalCase` always. | Across all transports. |
| **Sync + async** | Both sync (`MySDK`) and async (`AsyncMySDK`) clients exported. | Library SDKs may be sync-only if the operations are CPU-bound and not I/O-bound. |
| **HTTP client** | `httpx` for HTTP transports. | N/A for non-HTTP. Subprocess uses `subprocess`; gRPC uses `grpc.aio`. |
| **Retries** | Built-in for networked transports. Disabled for local. | Per Part 4. |

### 5.2 TypeScript

| Concern | Convention | Transport notes |
|---|---|---|
| **Type validation** | Generated `.d.ts` interfaces. Runtime validation via Zod only when explicitly needed (e.g., crossing trust boundaries). | Binary wire uses generated TypeScript from proto. |
| **Naming (fields)** | `snake_case` for response fields when wire is JSON. Preserved from wire — do not auto-camelCase. | Binary wire generator emits language-idiomatic case. |
| **Naming (methods)** | `camelCase` always. | Across all transports. |
| **Naming (classes)** | `PascalCase` always. | Across all transports. |
| **Sync + async** | Async-only. Promise-returning. | Library SDKs follow Promise convention even for synchronous-by-nature operations. |
| **HTTP client** | Native `fetch`. Avoid axios. | N/A for non-HTTP. Subprocess uses `child_process`; gRPC uses `@grpc/grpc-js`. |
| **Retries** | Built-in for networked transports. Disabled for local. | Per Part 4. |

### 5.3 Per-language patterns that DON'T transcend transport

A small set of conventions need transport-specific tweaks:

- **`with_raw_response` / `withResponse`** (raw access escape hatch) — works
  naturally for HTTP/REST; awkward for library calls (you already have the
  response); meaningful for gRPC if you want the metadata; meaningless for
  subprocess (the raw response is the JSON on stdout).
- **`extra_headers` / `headers` parameter** — meaningful for HTTP, gRPC,
  WebSocket; not meaningful for subprocess (no headers), library (no transport),
  or MCP-over-stdio (different mechanism).
- **`timeout` per-call** — meaningful for any transport with bounded
  duration. Library calls expose timeout only if the operation is genuinely
  long-running.

---

## Part 6 — Python ↔ TypeScript parity contract

| Concern | Python | TypeScript |
|---|---|---|
| **Field case (JSON wire)** | snake_case (preserved from wire) | snake_case (preserved from wire) |
| **Field case (binary wire)** | snake_case (language idiom) | camelCase (language idiom) — generator converts |
| **Method names** | snake_case | camelCase — identical when single-word |
| **Resource names** | snake_case | camelCase — identical when single-word |
| **Class names** | PascalCase | PascalCase |
| **Sync/async** | Both clients | Async-only |
| **Pagination** | `SyncPage[T]` + `AsyncPage[T]` | Single `Page<T>` |
| **Error class names** | Identical across languages | Identical across languages |
| **Error category enum** | Identical values | Identical values |
| **Resource tree shape** | Identical structure | Identical structure |
| **Runtime validation** | Pydantic v2 when JSON | None by default; Zod only if needed |

**Key principle (unchanged from v0.1.0):** for JSON-wire transports, preserve
wire-format field case. Don't auto-camelCase JSON in TypeScript. For binary-wire
transports, the wire has no case; the language idiom takes over.

---

## Part 7 — Authentication (per-transport)

The spec previously punted on auth. Here it isn't punted.

| Transport | Conventions |
|---|---|
| **HTTP** | Bearer token in `Authorization`; API key in header; OAuth 2.1 + PKCE; mutual TLS for service-to-service. |
| **JSON-RPC / MCP-over-stdio** | Inherited process auth; for HTTP/WebSocket transports of JSON-RPC, HTTP/WebSocket conventions apply. |
| **Subprocess** | Inherited process auth (parent process trusted); short-lived tokens via env var or argv. |
| **Library** | Inherited process auth. No additional layer. |
| **gRPC** | Token in metadata; mTLS; ALTS (Google internal); per-channel and per-call credentials. |
| **GraphQL** | HTTP-level. |
| **WebSocket** | HTTP upgrade headers; first-message token. |
| **Database driver** | Connection string with credentials; mTLS to database; short-lived rotated credentials (e.g., Vault). |
| **Message queue** | SASL, mTLS, OAuth (per broker). |

**SDK responsibility:** the SDK exposes an `auth` parameter at client
construction; the auth value is bound to the transport's native auth carrier.
The SDK does NOT design auth schemes — it follows the transport's established
convention.

---

## Part 8 — Streaming, batching, long-running operations

### 8.1 Streaming

| Transport | Mechanism |
|---|---|
| HTTP | Server-Sent Events (SSE); chunked transfer encoding |
| gRPC | Native server/client/bidi streams |
| GraphQL | Subscriptions via WebSocket |
| JSON-RPC / MCP | Progress notifications |
| Subprocess | Line-delimited JSON (NDJSON) on stdout |
| Library | Generators (Python) / async iterators (TypeScript) |
| WebSocket | Native bidirectional messages |

Generated SDKs expose streaming via a higher-level helper (per language):

- Python: `Stream[T]` / `AsyncStream[T]` iterator + a context-manager wrapper
- TypeScript: `for await` over the result

### 8.2 Batching

Batching is application-level. The spec doesn't define a universal batching
convention because the established conventions diverge across transports:

- HTTP: batch endpoints (e.g., Anthropic's `/v1/messages/batches`)
- gRPC: client-stream RPC
- Message queue: producer batches multiple messages
- Subprocess: input as argv array or stdin newline-delimited

### 8.3 Long-running operations

Three established patterns:

- **Polling:** caller invokes `start`, gets an operation handle, polls `status`. Common in HTTP. wpx-pipeline's structured-result-on-completion approach is a variant.
- **Callbacks/webhooks:** the server invokes the client at completion. Requires the client to be reachable, which limits applicability.
- **Streaming progress:** server pushes intermediate events; client consumes until terminal event. MCP supports this via progress notifications; gRPC native; SSE-based.

The SDK exposes whichever is appropriate per operation; agents don't need to
know which mechanism is used as long as they get a typed `OperationResult` at
the end.

---

## Part 9 — Generation pipeline (per-transport)

| Transport | Schema → Python | Schema → TypeScript |
|---|---|---|
| HTTP / REST | `openapi-python-client` (Pydantic v2 + httpx) | `openapi-typescript` (types) + hand-written fetch wrapper |
| JSON-RPC / MCP | MCP Python SDK (Anthropic) — register tools by hand reading the schema | MCP TypeScript SDK (Anthropic) — same |
| Subprocess | Hand-author the wrapper (reading the schema for invocation + parse rules) | Same |
| gRPC | `protoc-gen-python_grpc` / `betterproto` | `protoc-gen-ts` / `connect-es` |
| GraphQL | `ariadne-codegen` (Python); `graphql-codegen` (TypeScript) | `graphql-codegen` |
| WebSocket / AsyncAPI | `asyncapi-generator` (multi-language) | `asyncapi-generator` |
| Library | Hand-author; the host language *is* the schema | Hand-author |

For each transport, choose the codegen that matches the schema language. None
of the open-source options listed above is a commercial codegen service.

### Self-contained alternative

If the build pipeline shouldn't depend on any external codegen tool at all, the
agent hand-authors all three outputs (Python client, TS client, optional MCP
server) by following Parts 2-7 as a checklist. This is more work but
reproducible from this spec alone.

### Monorepo install graphs

When an SDK ships **multiple co-located packages** that share a repo
(typically `python/` + `mcp/`, sometimes `typescript/` too), the
inter-package install graph is a recurring source of brittleness. Two
anti-patterns observed in production SDKs:

**Anti-pattern 1 — relative `file:` dependency.** `mcp/pyproject.toml`
declares:

```toml
dependencies = [
    "mcp >= 1.0.0",
    "my-sdk @ file:../python",        # broken outside mcp/
]
```

pip resolves `file:` URIs against **the shell's current working directory
at install time**, NOT against the pyproject.toml's location. `pip install
-e mcp/` from inside `mcp/` works; `pip install -e my-sdk/mcp` from one
level up hits `No such file or directory: my-sdk/python`. The error is
cryptic and CWD-dependent — easy to ship, hard to diagnose.

**Anti-pattern 2 — relative LICENSE / README references.** `license = { file
= "../../../LICENSE" }` in a deeply nested pyproject.toml. setuptools
refuses to read files outside the package root during editable installs
(security boundary), so even when the relative path is technically correct
the editable install fails. The wheel build (which copies the file in)
succeeds, masking the bug in CI until a real user runs `pip install -e .`.

#### Two valid conventions

Pick exactly one. Document the choice prominently in the repo README.
Don't mix them — that hands every consumer a worse install experience than
they'd get from either convention alone.

**(a) Standalone packages with documented install order.** Each member
package is self-contained — no inter-package `file:` references in
`dependencies`. Runtime coupling is import-time only (e.g. `mcp/server.py`
imports `my-sdk` at load time, but pip's resolver doesn't see this). The
README documents the install order:

```bash
cd my-sdk/python && pip install -e .
cd ../mcp        && pip install -e .
```

Pros: works in any environment that has pip. No tooling dependency on
consumers. Robust against CWD.

Cons: two commands instead of one. Developers re-typing `cd ..` for every
fresh checkout.

**(b) Workspace pyproject (uv / pdm).** A top-level pyproject at the SDK
repo root declares each member as a workspace member and lists them as
dependencies of the workspace root. `[tool.uv.sources]` maps the
inter-package coupling to the local workspace path so resolution doesn't
attempt PyPI:

```toml
# my-sdk/pyproject.toml (workspace root)
[project]
name = "my-sdk-workspace"
dependencies = ["my-sdk", "my-sdk-mcp"]

[tool.uv.workspace]
members = ["python", "mcp"]

[tool.uv.sources]
my-sdk     = { workspace = true }
my-sdk-mcp = { workspace = true }
```

```bash
cd my-sdk && uv sync   # single command installs everything
```

Pros: one command. Reproducible via `uv.lock`. Same shape uv ships for
Anthropic's first-party Python projects.

Cons: requires consumers to have uv (or pdm equivalent) installed. v0.0.x
of uv's workspace support shipped in 2025 but has matured fast — by 2026
it's the convention for Python monorepos.

#### The "both worlds" pattern (recommended for SDKs with broad reach)

Many published SDKs offer BOTH paths:
- Workspace pyproject for the developer-experience recommended path
- Standalone member packages so pip-only consumers still get a working install

The trade-off: pyproject files exist at three levels (workspace root + each
member) instead of two. The workspace root carries the meta-coordination;
each member stays independently installable. This is the pattern
plugin-builder uses (v0.2.0+) — `uv sync` is the recommended developer
path, two-step pip install is the fallback.

#### Validation hook

Rubric check **4.01a — Editable install succeeds in a clean venv** (added
in validation rubric v0.2.0) catches the brittle-install class of bug
mechanically. Every SDK author MUST run it before merging any pyproject
change. CI integration:

```yaml
- name: Probe editable install in a clean venv
  run: |
    python -m venv /tmp/probe
    /tmp/probe/bin/pip install -e ./python
    /tmp/probe/bin/pip install -e ./mcp     # if mcp/ ships
    /tmp/probe/bin/python -c "from my_sdk_mcp import server; assert server.TOOL_REGISTRY"
```

The probe MUST run from the SDK repo root (not from inside `python/` or
`mcp/`) — that's the consumer-facing entry point, and the CWD where
relative-`file:` anti-patterns will fail.

---

## Part 10 — Telemetry (per-transport)

Five universal needs (the OI list from the top):

1. **Correlation ID per operation** — so a failure can be traced to its origin
2. **Outbound metadata** — what client / language / version made the call
3. **Inbound metadata** — what server / version handled it
4. **Latency measurement** — how long the operation took
5. **Audit log** — when and what was called (separate from full request logs)

Per-transport vehicle:

| Transport | Correlation | Outbound metadata | Inbound metadata | Latency | Audit |
|---|---|---|---|---|---|
| HTTP | `request-id` header | Headers | Headers | Client + server timing headers | Server-side log |
| JSON-RPC / MCP | JSON-RPC `id` field | Notifications | Notifications | Wall-clock | Server log + audit notification |
| Subprocess | PID + timestamp | argv (debugger) + stderr (runtime) | stderr | Wall-clock | Process log |
| Library | Trace context | Logging structured fields | Logging structured fields | Internal timing | Application log |
| gRPC | Metadata | Metadata | Metadata | OpenTelemetry | Server log |

**Convention:** every operation's success and failure produces a correlation
ID. Errors expose it as `error.correlation_id`. Logs include it. Server-side
debugging starts from the correlation ID.

---

## Part 11 — Adversarial Testing pass (AT)

Each section above gets a "where would this fail?" check.

### Part 1 — The two axes

**Could the axes overlap in practice?**

- **Streaming.** Streaming is partially a schema concern (the operation
  declares it streams) and partially a transport concern (how it streams).
  Resolution: streaming declarations live on the schema layer; the binding
  in Part 4 spells out how each transport implements them.
- **Authentication.** Auth is partially schema (which operations need it)
  and partially transport (how the credential is sent). Resolution: same as
  streaming — declaration on schema, implementation on transport.

### Part 3 — The error model

**Could the three categories be insufficient?**

- **Yes, for fine-grained recovery.** An agent that wants to distinguish
  "retry now" from "retry after exponential backoff" from "do not retry"
  needs more than three categories. Resolution: the subclasses in 3.3 give
  this granularity; the three top-level categories give the broad routing.
- **Partial successes.** An operation that succeeds partially (some sub-tasks
  failed) doesn't cleanly fit. Resolution: model partial success as a
  successful result with a `failures[]` field in the output. Don't try to
  use the error hierarchy for partial outcomes.

### Part 4 — Transport bindings

**Could the binding table be wrong for a transport?**

- **Yes — categorisation calls are judgement-based.** The mapping of
  HTTP 409 to `ExpectedError` is a choice; some teams would map 409 to
  `ConflictError` directly without the intermediate category. Resolution:
  the binding table is a recommended default; teams can adjust per-operation
  with documented rationale.

### Part 5 — Per-language conventions

**Could the parity contract be wrong?**

- **Yes — `snake_case` preserved from wire conflicts with TypeScript idiom.**
  Some TypeScript codebases will refuse to allow snake_case fields. Resolution:
  the parity contract serves the agent (mental model consistency); local
  style overrides are deviations to be documented, not corrections.

### Part 11 — This section itself

**Could the AT pass be insufficient?**

Yes — each adversarial check above is illustrative, not exhaustive. The spec
is calibrated as VALIDATED for HTTP, SUPPORTED for JSON-RPC/subprocess,
EMERGING for gRPC/GraphQL/WebSocket in cross-language SDK terms. The Part 11
checks above demonstrate the AT discipline; production use of the spec needs
ongoing checks against real failures.

---

## Part 12 — Falsifiability criteria (FR)

The spec is in calibration. Stop / pivot / re-evaluate conditions:

**STOP applying this spec if:**

- After 6 months of use across at least 3 transports, no Sulis SDK can
  successfully be built from it without significant hand-authoring beyond
  the schema layer
- The outcome-category error model proves unable to map a real transport's
  errors (counter-example surfaces that genuinely doesn't fit Protocol /
  Expected / Internal)
- Multiple agents independently report that the schema/transport split
  causes more confusion than the conflated v0.1.0 model would have

**PIVOT if:**

- One transport binding (Part 4) routinely needs its own error sub-categories
  that pollute the top-level hierarchy
- The `request-id` style correlation pattern doesn't work for one transport,
  forcing a parallel correlation scheme
- The Python+TS parity contract proves untenable for a specific transport
  (e.g., gRPC) — accept that language-divergence is correct for that case

**RE-EVALUATE if:**

- A widely-adopted external standard emerges that subsumes this (e.g., an
  industry-standard "agent SDK manifest" format)
- The MCP transport changes its protocol in a way that affects how SDKs bind
  to it
- A new schema language emerges that handles transport-agnosticism cleaner
  than Smithy/OpenAPI

### Pre-mortem

If this spec fails after the calibration period, the most likely reasons:

1. **Schema/transport split is too abstract.** Agents trying to apply it
   struggle to identify which axis a concern belongs to (especially for
   cross-cutting concerns like streaming and auth). Mitigation: the
   per-transport binding sections (Part 4) make the split concrete.
2. **The outcome-category error model doesn't fit one transport cleanly.**
   Most likely candidate: an asynchronous queue where errors arrive minutes
   after the operation. Mitigation: that's a "long-running operation" case
   and the model still applies — the error category is captured at
   completion.
3. **Per-transport bindings (Part 4) drift over time.** As transports
   evolve (HTTP/3, MCP 2026-XX-XX, gRPC-Web), the bindings need updates.
   Without a mechanism to keep them current, the spec becomes outdated.
   Mitigation: each binding lists "Sources cited" with URLs so updates have
   a starting point.
4. **The Python/TypeScript parity contract conflicts with language-native
   ergonomics** more often than expected. Resolution: the contract is a
   default; conscious deviations are allowed with documented rationale.

---

## Part 13 — Quality checklist

Before shipping a generated SDK from this spec, verify:

### Schema layer
- [ ] Every operation has a unique name, description (written for an LLM
      audience), input type, output type
- [ ] Required fields are explicit
- [ ] Discriminated unions use a `discriminator` field
- [ ] Streaming and pagination are declared per-operation
- [ ] Auth requirements are declared per-operation

### Error model
- [ ] Three universal categories (Protocol / Expected / Internal) preserved
- [ ] Transport-specific errors mapped onto the three (see Part 3.2 table)
- [ ] Domain errors extend canonical subclasses
- [ ] Every error exposes `message`, `category`, `transport_code`,
      `correlation_id`, `body`, `code`

### Transport binding (per Part 4)
- [ ] Invocation mechanics documented
- [ ] Retry policy chosen (enabled / disabled / per-operation)
- [ ] Telemetry vehicle chosen (headers / stderr / notifications / etc.)
- [ ] Authentication scheme chosen
- [ ] Streaming approach (if applicable) chosen

### Python client
- [ ] Pydantic v2 (for JSON wire) or appropriate decoder (for binary wire)
- [ ] Both sync + async clients exported
- [ ] Keyword-only method arguments
- [ ] Field case preserved from wire (or language idiom for binary wire)
- [ ] Per-method `extra_headers` / `timeout` parameters (transport-dependent)
- [ ] `.with_raw_response.method(...)` available where transport supports it

### TypeScript client
- [ ] Generated `.d.ts` interfaces for every response shape
- [ ] Async-only methods (Promise-returning)
- [ ] camelCase methods; case-preserved fields when JSON wire
- [ ] Per-method `options?: RequestOptions` parameter
- [ ] `.withResponse()` available where transport supports it

### Parity
- [ ] Resource tree shape identical between languages
- [ ] Error class names identical
- [ ] Error category enum values identical
- [ ] Field case identical (snake_case for JSON wire; appropriate per language for binary)
- [ ] Telemetry headers/fields stamped on every request

### Falsifiability & quality
- [ ] Spec includes confidence calibration (CC) per major claim
- [ ] At least one independent source per transport binding (BI)
- [ ] AT pass documented (Part 11 equivalents for each section)
- [ ] FR criteria documented (Part 12 equivalent)

---

## Sources (per-transport, independent — BI + SI compliance)

### Schema languages
- [OpenAPI 3.1 specification](https://spec.openapis.org/oas/v3.1.0) — HTTP
- [Protobuf 3 language spec](https://protobuf.dev/programming-guides/proto3/) — gRPC
- [GraphQL specification](https://spec.graphql.org/) — GraphQL
- [Smithy IDL](https://smithy.io/) — multi-protocol, AWS
- [JSON Schema Draft 2020-12](https://json-schema.org/draft/2020-12) — universal
- [AsyncAPI 3.0](https://www.asyncapi.com/docs/reference/specification/v3.0.0) — async/message-driven

### HTTP transport
- [RFC 7231 — HTTP/1.1 Semantics and Content](https://datatracker.ietf.org/doc/html/rfc7231)
- [anthropic-sdk-python](https://github.com/anthropics/anthropic-sdk-python)
- [openai-python](https://github.com/openai/openai-python)
- [Stripe API conventions](https://stripe.com/docs/api/errors)
- [Twilio SDK retry policy](https://www.twilio.com/docs/usage/troubleshooting/error-codes)
- [GitHub Octokit](https://github.com/octokit)

### JSON-RPC / MCP transport
- [JSON-RPC 2.0 specification](https://www.jsonrpc.org/specification)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP spec, tools (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [Language Server Protocol error codes](https://microsoft.github.io/language-server-protocol/specifications/lsp/3.17/specification/#errorCodes)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)

### Subprocess transport
- POSIX exit codes (`sysexits.h`)
- [The Twelve-Factor App — Logs](https://12factor.net/logs)
- [jq](https://stedolan.github.io/jq/) — JSON-stdout pattern
- AWS CLI — `--output json` convention
- The wpx-* tools in this marketplace

### gRPC transport
- [gRPC documentation](https://grpc.io/docs/)
- [gRPC Status canonical codes](https://grpc.github.io/grpc/core/md_doc_statuscodes.html)
- [Buf — modern Protobuf tooling](https://buf.build/)
- [ConnectRPC](https://connectrpc.com/)

### GraphQL transport
- [GraphQL specification](https://spec.graphql.org/)
- [Apollo conventions](https://www.apollographql.com/docs/apollo-server/data/errors/)
- [graphql-codegen](https://the-guild.dev/graphql/codegen)

### WebSocket transport
- [RFC 6455 — The WebSocket Protocol](https://datatracker.ietf.org/doc/html/rfc6455)
- [AsyncAPI for WebSocket](https://www.asyncapi.com/docs/reference/specification/v3.0.0)

### Library transport / patterns
- [PEP 249 — Python DB-API](https://peps.python.org/pep-0249/) — database driver pattern
- [JDBC](https://docs.oracle.com/javase/8/docs/technotes/guides/jdbc/) — same pattern, Java
- [Numpy](https://numpy.org/), [Pandas](https://pandas.pydata.org/) — library SDK conventions
- [pydantic v2](https://docs.pydantic.dev/2.0/)

### Cross-cutting / methodology
- [OpenTelemetry](https://opentelemetry.io/) — observability standard
- [The Sulis Critical Thinking Standard](../../../platform/methodology/standards/CRITICAL_THINKING_STANDARD.md)
- [Sulis Convention Preference Standard (CP-01)](../../../sulis/references/convention-preference-standard.md)

---

## Version history

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-05-21 | Initial spec. HTTP-shaped throughout. Treated MCP as a codegen target alongside Python and TypeScript. Single Anthropic+OpenAI source baseline. |
| 0.2.0 | 2026-05-21 | Universal restructure following CTS-based gap analysis. Schema/transport split made explicit (PG). Per-transport bindings (HTTP / JSON-RPC / subprocess / library / gRPC / GraphQL / WebSocket / database / message queue) with independent sources cited per transport (BI + SI). Error model rebased on three outcome categories (Protocol / Expected / Internal) with per-transport mapping. MCP elevated from codegen target to transport peer. Authentication, streaming, batching, long-running operations added. Adversarial Testing pass (Part 11), Falsifiability criteria (Part 12), and Confidence Calibration disclosure (top of spec) added per CTS requirements. Quality checklist (Part 13) expanded to cover schema, error, transport-binding, language, and parity axes. |
| 0.3.0 | 2026-05-22 | Added "Monorepo install graphs" subsection to Part 9. Two anti-patterns documented (relative `file:` deps; relative LICENSE/README paths) — both observed in production SDKs that passed the v0.2.0 rubric but broke for first-time users. Two valid conventions specified: (a) standalone packages with documented install order, (b) workspace pyproject (uv / pdm), plus the "both worlds" pattern. Cross-references rubric check 4.01a (Editable install succeeds in a clean venv). Surfaced from independent failures in `bids/complai/adapters/ukri` and `plugin-builder` — both hit the same gap, signal-strength for adding to the spec itself. |
