---
id: WP-003
title: ProviderAdapter Protocol + Claude adapter #1
kind: backend
primitive: EXPAND-Create
group: expand
status: ready
dependsOn: [WP-002]
estimated_token_cost: { input: ~14k, output: ~11k }
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_claude_adapter.py"
---

## Context

Contract §2.4 (the only agent-specific surface). This is **EXPAND-Create** — we
author an adapter for a seam *we* own (the `ProviderAdapter` Protocol), satisfying
a port the domain defines. It is NOT a SUBSTITUTE-Wrap of the `claude` CLI: the
Stripe-rule discriminator (contract §2.4, MECE-3 MEA-01) — *"whose interface is
the public face of this code?"* — answers "mine" (the Protocol). The `claude` CLI
is *called by* `decode()`/`spawn_argv()`, not wrapped at the architecture level.

The `decode()` mapping rules are the shared asset reused from the cockpit's
`apps/cockpit/server/lib/streamJsonToEvents.ts` — **the rules, not the code**
(§2.4 note). They are reimplemented Python-side and stated in §2.3's mapping table.

Modules:
- `plugins/sulis/scripts/_session_manager/adapter.py` — the `ProviderAdapter` Protocol + `Capabilities`, `SessionSpec`.
- `plugins/sulis/scripts/_session_manager/adapters/claude.py` — the Claude adapter.

## Contract

```python
@dataclass(frozen=True)
class Capabilities:  supports_resume: bool; supports_tools: bool; supports_partial_streaming: bool

@dataclass(frozen=True)
class SessionSpec:   provider: str; cwd: str; resume_ref: str | None = None

class ProviderAdapter(Protocol):
    capabilities: Capabilities
    def spawn_argv(self, spec: SessionSpec) -> list[str]: ...
    def encode(self, command: str) -> bytes: ...
    def decode(self, line: bytes) -> Event | None: ...   # None = bookkeeping/init line
    def turn_complete(self, event: Event) -> bool: ...
```

Claude adapter behaviour (§2.4):
- `capabilities` = `Capabilities(supports_resume=True, supports_tools=True, supports_partial_streaming=True)`.
- `spawn_argv` → `['claude','-p','--input-format','stream-json','--output-format','stream-json','--include-partial-messages','--dangerously-skip-permissions', ...resume flags if spec.resume_ref...]`.
- `encode` → one NDJSON stream-json user-message line + `\n`.
- `decode` → maps one stdout line:
  - `stream_event` / `content_block_delta` → `Event(kind="chunk", text=...)`
  - `result` / `success` → `Event(kind="result", result=TurnResult(...))`
  - `result` / error or `is_error` → `Event(kind="error", error=EventError("expected"|"internal", code, msg))`
  - init / bookkeeping lines → `None`
  - unparseable line → raise `InternalError("DECODE_FAILED")`
- `turn_complete(event)` → `event.kind == "result"` from a `result/success`.

Note: `decode()` here produces an `Event` with `offset`/`key`/`turn` **unset or
placeholder** — the manager (WP-004) is what owns offsets/keys/turns and assigns
them on append. Decide the seam: `decode()` returns a partial Event (kind+payload),
manager fills offset/key/turn. Record that split in the docstring.

## Definition of Done

### Red (failing tests first)
Use **recorded real `claude` stream-json lines** as fixtures (capture once from
`claude -p --output-format stream-json`, store under
`tests/fixtures/session_manager/claude/`). No hand-mocked JSON shapes that drift
from the real CLI (MEA-09 spirit — fixtures are recorded reality).
- `test_spawn_argv_streaming_flags` — argv contains the stream-json flags; resume flag present iff `resume_ref` set.
- `test_spawn_argv_runs_in_cwd` — spec.cwd is honoured (the manager passes it to Popen; adapter just shapes argv — assert argv/cwd contract).
- `test_encode_is_ndjson_user_message` — `encode("hi")` is one valid stream-json user-message line ending in `\n`.
- `test_decode_chunk` — a recorded `content_block_delta` line → `Event(kind="chunk", text=...)`.
- `test_decode_result` — a recorded `result/success` line → `Event(kind="result", result=TurnResult with token counts + stop_reason)`.
- `test_decode_error` — a recorded error/`is_error` line → `Event(kind="error", error=...)` with the right category.
- `test_decode_bookkeeping_returns_none` — an init/system line → `None`.
- `test_decode_garbage_raises_internal` — non-JSON line → `InternalError("DECODE_FAILED")`.
- `test_turn_complete_true_only_on_result_success` — true for result/success, false for chunk/tool_use/error.
- `test_capabilities_claude_supports_resume` — the honest capability flags.

### Green
- Implement the Protocol and the Claude adapter. Boring line-by-line mapping;
  explicit dict-key access with clear errors, no reflection.

### Blue (refactor)
- The Protocol file imports only WP-002 types — confirm no manager/process import
  leaks in (the adapter must be testable with zero subprocess). Dependency inward.

## Notes
- This is the seam that guarantees Codex/Gemini are *one new file each* with zero
  change to the manager or consumers (ADR-001 consequence).
- Capturing the recorded `claude` fixtures here also seeds WP-008's stub set.
