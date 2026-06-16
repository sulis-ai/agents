---
id: WP-001
change_id: 01KV0GW39Q522P6PMFTTXH9T2E
title: safe-tools MCP server — wrap safe_fetch/safe_search/scoped_file as denyable MCP identities
kind: backend
primitive: create
group: expand
status: pending
dependsOn: []
blocks: []
scenarios: [SC-E1]
verification:
  adapter: backend
  artifact: "plugins/sulis/scripts/tests/unit/test_safe_tools_mcp_contract.py"
token_cost: { input: ~11k, output: ~9k }
---

# WP-001 — safe-tools MCP server

## Context

TDD §Form (new components) + ADR-001 (one `scoped_file`) + ADR-002 (Python
stdio, `.mcp.json` `command`). Exposes the shipped L1 + L2 functions as
denyable MCP tool identities so "allow-safe / deny-raw" becomes expressible.
**Wraps; reimplements nothing** (D6). Independent of the other tracks at t=0;
uses the resolver only at *call* time (the resolver lands in WP-002 but the
server can be built + contract-tested against a tmp-tree scope without it on
the critical path — the agent-scope wiring reads it once available).

## Contract

- **New:** `scripts/_safe_tools_mcp.py` — a Python stdio MCP server (official
  `mcp` SDK) registering exactly three tools:
  - `safe_fetch(url: str, format: str = "markdown") -> str` → calls
    `_safe_fetch.tool.safe_fetch` with the production gateway; returns the
    framed `FetchResult.content`.
  - `safe_search(query: str) -> str` → calls `_safe_fetch.tool.safe_search`.
  - `scoped_file(op: str, path: str, content: str | None = None, dst: str | None = None) -> dict`
    — `op ∈ {read,write,move,remove}` (closed enum; unknown op → fail-closed
    refusal). Dispatches via explicit `match` to the matching `_file_tools`
    function; serialises `FileToolResult` (`ok`, `reason`, `payload`).
    `change_id` + `repo_root` come from the **launch environment**, never from
    agent args (ADR-001).
- **New:** `scripts/sulis-safe-tools-mcp` — thin launcher (resolves the plugin
  Python env + `scripts/` on `sys.path`, runs the server over stdio).
- **Modified:** `plugins/sulis/.mcp.json` — add server `sulis-safe-tools` with
  a `command` entry (NOT npx).
- **Modified:** `plugins/sulis/scripts/pyproject.toml` + `uv.lock` — add
  `mcp>=1.0` to runtime deps; `uv sync` regenerates the lock.

## Definition of Done

### Red
- [ ] `test_safe_tools_mcp_contract.py::test_three_tools_enumerate` — start the
      server (in-process), list tools; assert exactly `safe_fetch`,
      `safe_search`, `scoped_file` with correct param schemas. **Fails** (no
      server yet).
- [ ] `::test_scoped_file_dispatches_each_op` — each op routes to the right
      `_file_tools` function (assert via a tmp tree + spy/real call), unknown
      op refused fail-closed.
- [ ] `::test_safe_fetch_delegates_to_gateway` — `safe_fetch`/`safe_search`
      call the wrapped tool against a `FakeGateway` (reuse the prior L1
      contract fake); no network, no reimplemented logic.

### Green
- [ ] Implement `_safe_tools_mcp.py` + launcher; register in `.mcp.json`; add
      `mcp>=1.0` + `uv sync`. Boring code: explicit `match op`, no reflection,
      no dynamic dispatch. All Red tests pass. **SC-E1 satisfied.**

### Blue
- [ ] Module docstring states the honesty boundary (ADR-002 A2: MCP identity =
      availability, NOT enforcement). Extract no duplicate marshalling — one
      serialise helper for `FileToolResult`. Confirm the server imports the
      existing functions unchanged (grep: no `urllib`/`requests`/scope logic in
      the new module).
