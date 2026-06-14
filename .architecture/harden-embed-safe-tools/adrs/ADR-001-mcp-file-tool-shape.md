---
id: ADR-001
title: One parameterised `scoped_file(op, …)` MCP tool, not four
status: accepted
change_id: 01KV0GW39Q522P6PMFTTXH9T2E
date: 2026-06-13
relates_to: SPEC §Phase 1 (item 1, "decide at design to avoid name-collision"), D8
---

# ADR-001 — One parameterised `scoped_file(op, …)` MCP tool, not four

## Context

Phase 1 exposes the four existing L2 file ops (`read_file` / `write_file` /
`move_file` / `remove_file`, in `_file_tools.py`) as MCP tools so they become
denyable tool identities (`mcp__sulis-safe-tools__…`). The SPEC and D8 flag a
**name-collision trap**: four MCP file tools (`read`, `write`, `move`,
`remove`) sitting next to the harness's own built-in `Read` / `Write` /
`Edit` tools bloat the selection surface with near-duplicate names — the
binding MCP constraint per D8 is **tool-selection accuracy**, which degrades
with similar-name families. The SPEC leaves the shape to design: one
parameterised tool OR four clearly-distinct tools.

## Decision

Expose **one** MCP tool, `scoped_file(op, path, content?, dst?)`, where `op`
is an enum `read | write | move | remove`. It dispatches to the matching
existing `_file_tools` function and returns the existing typed
`FileToolResult` serialised. The MCP server presents **three** tools total:
`safe_fetch`, `safe_search`, `scoped_file`.

## Rationale (the recommended convention)

- **Selection-accuracy is the binding constraint (D8).** One tool with an
  enum arg adds one entry to the selection surface, not four — and the name
  `scoped_file` shares no stem with the built-in `Read`/`Write`/`Edit`, so it
  does not compete with them for selection. This is the convention the D8
  criterion points at directly: MCP-ify only when it doesn't bloat selection.
- **The four ops are one cohesive contract.** They already share one
  resolver (`within_allowed_scope`), one result type (`FileToolResult`), and
  one fail-closed policy. A single parameterised tool mirrors the cohesion
  that already exists in the library; four tools would fragment one contract
  into four selection-surface entries for no behavioural gain.
- **Boring over clever.** The dispatch is an explicit `match op:` over a
  closed enum — no reflection, no string-keyed dynamic dispatch. The enum is
  validated against the four known operations; an unknown `op` is a
  fail-closed refusal (mirrors `_file_scope`'s `_OPERATIONS` guard).

## Alternatives considered

- **Four distinct MCP tools (`safe_read_file`, `safe_write_file`, …)** —
  REJECTED. Quadruples the file-op selection surface and invites confusion
  with the built-in `Read`/`Write`/`Edit`. Distinct names *reduce* the
  collision risk versus bare `read`/`write`, but they do not address the
  selection-bloat half of the D8 criterion. The cohesion argument also
  applies: four tools restate one contract four times.
- **1:1 MCP-ifying with the bare names `read`/`write`/`move`/`remove`** —
  REJECTED hardest. This is the exact name-collision trap D8 names — bare
  `read`/`write` collide head-on with the harness's file tools.
- **Folding the file ops into a generic `sulis_tool(name, args)` mega-tool** —
  REJECTED. Over-collapses: `safe_fetch`/`safe_search` are a different
  contract (a gateway return, not a `FileToolResult`) and belong as their own
  tools. One tool per cohesive contract is the right granularity.

## Consequences

- The MCP server (WP-001) marshals MCP JSON args → the existing `_file_tools`
  function signatures (which take `change_id`, `repo_root`, `roots`). The
  server resolves `change_id` + `repo_root` + the write-roots from the
  environment at call time (see ADR-004 / WP-003), not from the agent's args
  — the agent cannot widen its own scope by passing a different `change_id`.
- `scoped_file` is allowed in the agent allowlist as
  `mcp__sulis-safe-tools__scoped_file`; the built-in `Write`/`Edit` remain
  available but are governed by the PreToolUse hook (ADR-003) — the MCP tool
  is the *ergonomic, pre-scoped* path, the hook is the *backstop* on the
  built-ins.
