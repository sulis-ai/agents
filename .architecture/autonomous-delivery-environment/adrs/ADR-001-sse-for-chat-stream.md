# ADR-001 — Server-Sent Events (SSE) for the chat reply stream

- **Status:** accepted
- **Date:** 2026-06-03
- **Change:** CH-01KT50 · autonomous-delivery-environment
- **Deciders:** SEA (confirms the SRD's decided-by-default)

## Context

The chat (FR-16..FR-26) needs the agent's reply to stream back to the
browser token-by-token (FR-17, NFR-PERF-02: first chunk ≤ 2s, ≤ 250ms
inter-chunk). The data flows **one way** for the streamed phase: server →
client. The founder's prompt is a single up-front request, not an
ongoing duplex conversation at the transport layer. The SRD recorded SSE
as the convention-preferred default and left the door open to WebSockets
"if the bridge requires bidirectional framing".

## Decision

**Use Server-Sent Events (SSE) over a long-lived `GET`-shaped stream for
the reply, with the founder's prompt delivered as the request that opens
the stream.** SSE is the established IETF/WHATWG convention
(`text/event-stream`, the `EventSource` semantics) for one-way
server→client token streaming over HTTP. It is the same shape OpenAI,
Anthropic's own SDK transport, and most LLM chat UIs use for token
streaming.

Concretely: the relay endpoint accepts the prompt and the named change,
then holds the connection open and emits framed events
(`chunk`, `state`, `complete`, `error`) until the reply ends. This maps
cleanly onto the stream-json events the bridge already produces
(`stream_event` deltas → `chunk`; lifecycle → `state`;
`result/success` → `complete`).

**Transport-shape note vs. the read-only gate:** the existing gate
forbids `app.post/put/patch/delete`. The relay is a write/act path
(ADR-003) and is the *one* sanctioned exception — its HTTP method is an
implementation detail the gate's allow-list names explicitly, not a
reason to disguise it as a GET. See ADR-003 for how the gate is extended.

## Alternatives considered

- **WebSockets (rejected for now).** Full duplex. Rejected because the
  reply stream is one-way; WebSockets add framing, upgrade handshake,
  heartbeat/reconnect machinery, and a second protocol surface for no
  benefit at this shape. The prior `claude-code-chat-ui` spike used
  socket.io and the lesson recorded in `local-ui-design.md` was that the
  transport was never the hard part — the Claude integration was. We keep
  the simpler transport. *Reconsider only if* the bridge later needs
  mid-reply client→server signalling (e.g. interrupt/cancel as a framed
  message rather than closing the connection).
- **Long-poll / chunked JSON (rejected).** Re-implements SSE badly; no
  `EventSource` reconnect semantics; worse founder-perceived latency.
- **Plain non-streamed request/response (rejected).** Violates FR-17 /
  NFR-PERF-02 — the founder would stare at a spinner for the whole reply.

## Consequences

- The client uses `EventSource` (or a `fetch`-reader equivalent when the
  prompt body must accompany the open — see the data contract for the
  exact shape) and renders `chunk` events into the live message.
- Interrupt (FR-22) is "close the connection"; the server detects the
  drop, preserves the partial, marks it interrupted (NFR-REL-02).
- The relay sets `Cache-Control: no-cache`, `Connection: keep-alive`,
  `Content-Type: text/event-stream`, and disables response buffering.
- One-in-flight (FR-20 / NFR-REL-03) is enforced server-side by a
  per-change lock, independent of transport.
