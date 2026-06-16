---
id: ADR-002
title: Python stdio MCP server on the plugin's own env, registered via `.mcp.json` command
status: accepted
change_id: 01KV0GW39Q522P6PMFTTXH9T2E
date: 2026-06-13
relates_to: SPEC §Phase 1, D6 (PACKAGING answered)
---

# ADR-002 — Python stdio MCP server on the plugin's own env, via a `.mcp.json` `command`

## Context

The safe tools wrap existing **Python** libraries (`_safe_fetch`,
`_file_tools`). They must be exposed as MCP tools so "allow-safe / deny-raw"
becomes expressible. The plugin already registers two MCP servers in
`plugins/sulis/.mcp.json`: `mobbin` (HTTP) and `playwright` (npx Node). The
question is how to package the Sulis safe-tools server. D6 answered the
packaging directly; this ADR records it.

## Decision

Ship a **Python stdio MCP server** in `plugins/sulis/scripts/` (module
`_safe_tools_mcp.py` + a thin launcher `sulis-safe-tools-mcp`), launched via a
`command` entry in `plugins/sulis/.mcp.json` that runs it on the plugin's own
Python env. Register it under the server name **`sulis-safe-tools`** so its
tools resolve as `mcp__sulis-safe-tools__{safe_fetch,safe_search,scoped_file}`.

Add the Python MCP SDK (`mcp>=1.0`) to `plugins/sulis/scripts/pyproject.toml`
runtime dependencies (it is not currently a dependency). The server imports
the existing tool functions and runs them over the stdio transport; it
reimplements **no** fetch/scope logic (ADR-001, D6 "wrap existing
libraries").

## Rationale (the recommended convention)

- **The libraries are Python; the established convention for a local
  Python MCP server is stdio over the official `mcp` SDK** (the same shape
  `plugin-builder create-tool` produces, and the precedent
  `sulis-execution-mcp` set). npx is the convention for *external Node*
  servers (playwright) — using it here would mean reimplementing the Python
  libraries in Node, the opposite of "wrap, don't reimplement."
- **stdio, not HTTP.** The server is a per-session child of the agent process,
  not a network service. stdio is the boring default for a co-located,
  plugin-shipped server — no port, no auth, no listener surface. (The `mobbin`
  HTTP entry is a remote third-party service; not a precedent for a local
  wrapper.)
- **Runs on the plugin's env** so it shares the exact dependency set the
  libraries already use (`detect-secrets`, `trafilatura`) — declared once in
  `pyproject.toml`, installed via `uv sync` like every other script dep
  (avoids the "missed dep in CI" class #112 already closed).
- **Versions with the plugin.** The `.mcp.json` entry ships in the plugin, so
  the server, the hook, and the CLIs all version together (SPEC §Constraints,
  distribution).

## Alternatives considered

- **npx / a Node MCP server** — REJECTED. Would require porting `_safe_fetch`
  + `_file_tools` to Node — a full reimplementation of shipped, tested Python,
  forbidden by D6 + the SPEC ("no logic reimplementation").
- **An HTTP MCP server** — REJECTED. Adds a listener, a port, and an auth
  surface for a co-located per-session wrapper. stdio is strictly simpler and
  is the convention for local servers.
- **Reusing/extending the prior `sulis-execution-mcp`** — REJECTED as the home
  (it is a separate concern), but ACCEPTED as the **precedent** that a
  Python/stdio Sulis MCP server is the sanctioned shape.

## Consequences

- `.mcp.json` gains a third server. The launcher resolves the plugin Python
  env (the same interpreter the `wpx-*`/`sulis-*` scripts run under) and
  `scripts/` on `sys.path` so the imports resolve.
- The server reads `change_id` / `repo_root` from its launch environment
  (set when the agent session is spawned) so `scoped_file` is pre-scoped to
  the running change without trusting agent-supplied args (ADR-001 / ADR-004).
- A new runtime dep (`mcp>=1.0`) lands in `pyproject.toml` + `uv.lock`; CI
  installs it via `uv sync --frozen`.
- **Honesty (A2, D6):** MCP identity makes the safe path *available + denyable*
  — it is NOT enforcement. A downstream consumer who registers the MCP server
  but does NOT load the plugin hook (Phase 2) gets only the availability half.
  Enforcement of the *unsafe* path is the hook (locus ii) + the sandbox
  (locus iii). The standard (Phase 5) states this; the server's module
  docstring repeats it.
