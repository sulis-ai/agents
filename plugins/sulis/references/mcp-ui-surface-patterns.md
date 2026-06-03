# MCP-UI surface patterns — choosing how an AI-client surface renders

> **What this is:** the decision rule + contract shape + constraints for driving
> custom interactive UI inside an AI client (Claude / Cowork / Desktop / mobile).
> **The load-bearing point: which rendering path you pick is an ARCHITECTURE
> decision, not a styling one** — it's driven by *data-connection + durability*,
> not by how the surface looks. Picking wrong means a rebuild.
> **Severity:** the decision rule is MUST-apply when a change has an AI-client
> surface; the constraints are MUST when building one.
> **Provenance:** grounded in the MCP Apps official spec (modelcontextprotocol.io,
> the 2026-01-26 extension) + MCP-UI (mcpui.dev) + the cowork-custom-ui critical-
> thinking analysis (2026-06-02). Confidence tiers + the two open uncertainties
> are carried below — don't over-claim past them.

## The decision rule (MUST apply for any AI-client surface)

Three confirmed paths. Choose by **data-connection + durability**, not look:

| Path | When | Cost | Key limits |
|---|---|---|---|
| **Artifact** (native `jsx`/`html`/`svg`/`mermaid`/`md`/`pdf`) | The client *produces* a rich interactive output **in-session, no live back-end** | Zero infrastructure | **Ephemeral + session-scoped; NO persistent back-channel; React artifacts can't use localStorage/sessionStorage.** If it needs live data or reuse, you'll hit a wall + rebuild as an MCP App. |
| **MCP App** (`ui://` resource on an MCP server) | Building a **connector/product** users interact with **repeatedly, against live data, with actions routed back** to your systems | Server + infra | Sandboxed iframe; needs CSP allowlist for external assets |
| **MCP-UI `externalUrl`** (iframe to an existing web app) | You **already have a web app** to embed | Lowest rewrite | Reduced host integration; it's just your app in an iframe |

> **The single biggest reason to choose correctly:** Artifacts are ephemeral
> with no data back-channel; MCP Apps are durable + data-connected + tool-driven.
> If the experience needs live data or repeat use, an Artifact will hit a wall.

## The MCP-App contract shape (the seam — MUST when building one)

An MCP App is a **producer (server) ↔ consumer (client)** contract — treat it
contract-first (see `standards/CONTRACT_FIRST_STANDARD.md`):

- **Resource:** `ui://…` scheme; `_meta.ui.resourceUri`; mimeType
  `text/html;profile=mcp-app`; bundled HTML/CSS/JS (any framework or none —
  React/Vue/Svelte/Preact/Solid/vanilla starter templates exist).
- **Channel:** rendered in a **sandboxed iframe** with **bidirectional JSON-RPC
  over `postMessage`** (the `ui/` method prefix) — this is the two-way tool
  channel back to your systems. The UI's actions are MCP tool calls; design them
  as the contract's operations (CF-03 error categories apply).
- **External assets:** allowed only via the **`_meta.ui.csp` allowlist**;
  declare it for any asset origin you load, or the sandbox CSP blocks it.
- **Extra capabilities** (camera / mic): via **`_meta.ui.permissions`**.

## Constraints to build against (MUST)

- **Artifacts are ephemeral + storage-less.** No localStorage/sessionStorage in
  React artifacts; no persistence across sessions. Don't design state that
  outlives the session into an Artifact.
- **MCP-App UI runs sandboxed.** Plan asset origins + CSP up front; the data
  path is the `ui/` postMessage channel, not direct network from the iframe.
- **Framework-agnostic bundle.** Start from the official template; the bundle is
  self-contained HTML/CSS/JS.

## Safe assumptions + the two open uncertainties (don't over-claim)

- **Assume the iframe-HTML path.** MCP-UI's `remoteDom` (host renders with its
  own component library) is a content type with *varying* client support;
  Claude's support is **unconfirmed** in the official MCP Apps docs (which centre
  on HTML-in-iframe). Treat host-native-styled components as not-yet-available.
- **Cowork↔Claude-web parity is Medium-High, not certain.** Whether Cowork hosts
  MCP Apps at full parity with Claude web isn't fully confirmed. Falsification:
  a Cowork-specific connector doc restricting interactive UI to web only.

## Where this is applied (cite, don't restate)

- **`ux-designer`** — for an AI-client surface, the *surface type* (Artifact vs
  MCP App vs externalUrl) is part of the visual contract; an MCP-App mockup is
  the `ui://` bundled HTML rendered in a sandboxed iframe, not a standalone page.
- **`draft-architecture`** — the Artifact-vs-MCP-App choice is an **ADR** (it's
  architecture: live-data + reuse decide it, per the rule above).
- **`standards/WP_FRONTEND_STANDARD.md`** — the build patterns (sandboxed iframe,
  the `ui/` postMessage channel, CSP allowlist, no-localStorage-in-artifacts,
  framework-agnostic bundle).
- **`standards/CONTRACT_FIRST_STANDARD.md`** — the MCP-App `ui://` resource +
  `ui/` channel as a producer/consumer contract seam.

## Sources
- MCP Apps — official overview + the 2026-01-26 extension (modelcontextprotocol.io)
- MCP-UI — content types `rawHtml` / `externalUrl` / `remoteDom` (mcpui.dev)
- Claude Help Center — interactive connectors (Claude / Cowork / Desktop / iOS+Android support; Claude Code does not — no UI surface)
- cowork-custom-ui critical-thinking analysis (2026-06-02, spiral-converged)
