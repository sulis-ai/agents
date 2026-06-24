# ADR-005 — The discovery seam: an MCP tool for raw-on-demand, payload pointer for rich-by-default

> **Status:** accepted · **Date:** 2026-06-24 · **Change:** CH-GJ9KQR

## Context

Progressive disclosure (spec scope part 3): the agent receives the **rich
payload by default** and can **fetch the raw full message log on demand**. The
spec's open question asks whether the discovery seam is a **tool call** or a
**pointer in the payload**, and to **reconcile with the safe-tools MCP model**.

The codebase already has the answer's pattern: `_safe_tools_mcp.py` wraps
shipped Python libraries as **denyable MCP tool identities** — one
parameterised tool (`scoped_file(op, path, …)`) over a wrapped library, with
`change_id` / `repo_root` scoping injected server-side, returning a serialised
typed result. The agent reaches durable cockpit capability through MCP tools,
not ambient file reads.

## Decision

**Two complementary mechanisms, matching the rich-by-default / raw-on-demand
split:**

1. **Rich-by-default = a pointer in the payload (no tool call needed).** The
   assembled context payload (ADR-001 ThreadMemory.content, delivered via the
   brief argv per ADR-004) **carries the rich content inline** — the structured
   summary, the Working Set crystallisation, the relevant brain entities — plus
   a **pointer** (the thread id + the raw-fetch tool name) telling the agent
   *where* the raw record lives. No round-trip on the common path; the rich
   payload is already in the agent's context window.

2. **Raw-on-demand = an MCP tool, following the safe-tools pattern.** A new
   **`thread_context` MCP tool** (one parameterised tool, mirroring
   `scoped_file`'s shape) exposes the read-side of the thread store's contract
   (ADR-002) to the agent:
   - `thread_context(op="get_memory", thread_id)` → the rich ThreadMemory
     (the same payload, on demand).
   - `thread_context(op="get_messages", thread_id, since?, limit?)` → the raw,
     correctly-ordered message log (full or a slice).
   - `thread_context(op="get_thread", thread_id)` → the Thread record.

   The tool is **read-only** (the agent never writes the log — the session
   pump does, ADR-004), **scoped server-side** to the bound change's thread
   (the same `change_id` scoping `scoped_file` already injects), and returns
   the contract's three-category errors. It is a **denyable identity** (the
   founder can withhold it), exactly like the safe-tools.

## Rejected alternatives

- **Raw via ambient filesystem read** (point the agent at the store path and
  let it `cat`). Rejected: bypasses the contract + the change-scoping guard,
  re-introduces a provider/path-shaped coupling, and is not denyable. The
  safe-tools precedent exists precisely to route capability through tools.
- **Rich payload also fetched via a tool call** (no inline content). Rejected:
  forces a round-trip on every spawn for content we already own and can inject
  via the brief argv — defeats "rich by default keeps every call cheap."
- **Four separate raw-fetch tools** (one per operation). Rejected per the
  safe-tools ADR-001 reasoning: one parameterised `op` tool avoids the
  permission-surface explosion of four tool identities.

## Consequences

- The `thread_context` MCP tool is a **new denyable identity** registered the
  same way the safe-tools are; its three ops are the **read half of the
  thread-store contract** (ADR-002), so the tool and the local binding share
  one schema.
- The payload pointer is part of the **payload schema** (the contract WP):
  every assembled payload carries `thread_id` + the raw-fetch affordance.
- Because the tool exposes the contract's read operations (not a Claude-shaped
  surface), the **same tool works unchanged** when the store's transport later
  swaps to the hosted communication-service (ADR-002) — only the binding moves.
