---
id: WP-002
title: Shared provider-neutral event vocabulary + three-category errors
kind: backend
primitive: EXPAND-Create
group: expand
status: ready
dependsOn: []
estimated_token_cost: { input: ~8k, output: ~6k }
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_session_event_types.py"
---

## Context

Contract §2.3 (event vocabulary) and §2.9 (three-category errors). These are the
shared types every layer speaks — the manager, both consumers, and every adapter
only ever see these four event kinds and three error categories. Defining them
once, frozen, is the Form invariant that keeps providers swappable.

Module: `plugins/sulis/scripts/_session_manager/events.py`.

## Contract

Frozen dataclasses, exactly per §2.3:

```python
@dataclass(frozen=True)
class ToolUse:        name: str; input_summary: str
@dataclass(frozen=True)
class TurnResult:     input_tokens: int; output_tokens: int; duration_ms: int; stop_reason: str
@dataclass(frozen=True)
class EventError:     category: Literal["protocol","expected","internal"]; code: str; message: str

@dataclass(frozen=True)
class Event:
    offset: int
    key: str
    turn: int
    kind: Literal["chunk","tool_use","result","error"]
    text: str | None = None
    tool: ToolUse | None = None
    result: TurnResult | None = None
    error: EventError | None = None
```

Three-category error model (§2.9) as exceptions for the in-process binding:

```python
class SessionError(Exception): category: str; code: str       # base
class ProtocolError(SessionError): category = "protocol"      # SPAWN_FAILED, STDIN_BROKEN, SOCKET_CLOSED
class ExpectedError(SessionError): category = "expected"      # NO_SESSION, UNKNOWN_PROVIDER, CWD_NOT_FOUND, OFFSET_EVICTED, SESSION_DISABLED
class InternalError(SessionError): category = "internal"      # DECODE_FAILED, LOG_CORRUPT
```

Each carries a `code` (the §2.9 code constants) and a message. The `code`
constants live as module-level string constants so call sites don't typo them.

## Definition of Done

### Red (failing tests first)
- `test_event_kind_payload_consistency` — a `chunk` Event must carry `text` and
  not `result`/`tool`/`error`; a `result` carries `result`; etc. (constructor or
  a `__post_init__` validator rejects mismatched payloads → InternalError/`DECODE_FAILED` is the boundary, but type-level mismatch is a programmer error).
- `test_event_is_frozen` — mutation raises (immutability is the multi-viewer safety property).
- `test_error_categories_exhaustive` — every §2.9 code maps to exactly one of the three exception classes; the category string matches.
- `test_error_codes_are_constants` — the code constants exist and are the §2.9 strings (guards against typos drifting from the contract).
- `test_event_error_roundtrips_to_event` — an `EventError` can be wrapped into an `Event(kind="error")` (the log carries failures as events too, §2.9).

### Green
- Plain frozen dataclasses; explicit `Literal` types; no dynamic field magic.
- A small `__post_init__` payload-shape check (boring, explicit) so a malformed
  Event fails loudly at construction, not three layers later.

### Blue (refactor)
- If WP-003's `decode()` needs a constructor helper (e.g. `Event.chunk(...)`),
  add named factory classmethods here rather than scattering kwargs — but only
  when the second call site exists.

## Notes
- These types are re-exported from `_session_manager/__init__.py` as the public
  vocabulary.
- The §2.3 mapping table to the cockpit's `ChatStreamEvent` is a Phase-2 concern
  (socket client maps it); Phase 1 only needs the Python-side types.
