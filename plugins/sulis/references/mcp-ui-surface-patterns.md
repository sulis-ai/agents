# Host-rendered surface contract — choosing how a host renders your surface, and proving it's wired

> **What this is:** the decision rule + contract shape + constraints + the
> done-gate for any surface a **host application renders on your behalf via a
> protocol handshake** — not a page you serve and own. MCP-Apps (Claude / Cowork /
> Desktop / mobile) is the worked instance here; the same shape governs **OpenAI
> Apps SDK, figma-plugin host, and browser-extension host APIs** — each binds a
> surface into a host you don't control, so each is an instance of this contract.
> **The load-bearing point: which rendering path you pick is an ARCHITECTURE
> decision, not a styling one** — it's driven by *data-connection + durability*,
> not by how the surface looks. Picking wrong means a rebuild.
> **Severity:** the decision rule is MUST-apply when a change has a host-rendered
> surface; the constraints are MUST when building one; **the done-gate below
> (§ "Done = wired + legible") is a MUST that FAILS CLOSED** — a surface that
> serves but isn't bound + observed in the real host is a GAP, not "done."
> **Provenance:** grounded in the MCP Apps official spec (modelcontextprotocol.io,
> the 2026-01-26 extension) + the MCP base tool-metadata spec (2025-11-25) +
> MCP-UI (mcpui.dev) + the cowork-custom-ui critical-thinking analysis
> (2026-06-02) + the host-rendered-surface critical-thinking analysis (2026-06-04,
> spiral-converged). Confidence tiers + the open uncertainties are carried below —
> don't over-claim past them.

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

- **Resource:** `ui://…` scheme; `_meta.ui.resourceUri`; bundled HTML/CSS/JS
  (any framework or none — React/Vue/Svelte/Preact/Solid/vanilla starter
  templates exist). **MIME: accept the host's actual value, not just the one we
  wrote down** — `text/html;profile=mcp-app` (MCP-Apps), `text/html+skybridge`
  and `text/html+mcp` (OpenAI Apps SDK / Skybridge adapter) all occur in the
  wild. Pin the exact value from the host's SDK and verify it against the real
  host; a mismatch here is precisely why a served surface renders as text.
- **Channel:** rendered in a **sandboxed iframe** with **bidirectional JSON-RPC
  over `postMessage`** (the `ui/` method prefix) — this is the two-way tool
  channel back to your systems. The UI's actions are MCP tool calls; design them
  as the contract's operations (CF-03 error categories apply).
- **External assets:** allowed only via the **`_meta.ui.csp` allowlist**;
  declare it for any asset origin you load, or the sandbox CSP blocks it.
- **Extra capabilities** (camera / mic): via **`_meta.ui.permissions`**.

## Done = wired + legible (MUST — the fail-closed gate)

A host-rendered surface fails the same way every time: the HTML serves and looks
right, so it's signed off as "built" — but the host never received the protocol
signal that makes it render, so it narrates tool data as text. **A serving
endpoint, rendering HTML, or a passing unit test does NOT mean the surface is
done.** Two conditions, both MUST, or the surface is a GAP:

**1. Wired — the binding exists on BOTH sides of the seam, cited in code, and the
round-trip is observed in the real host.**
- **Server side:** the host-render binding is present — for MCP-Apps, the tool
  carries `_meta.ui.resourceUri` and the `ui://` resource is served with the
  host's accepted MIME (see above). Cite the file + function.
- **Client side:** the surface uses the host runtime, not local state — for
  MCP-Apps, the ext-apps client runtime (`app.connect`, `app.ontoolresult` to
  receive render-data, `app.callServerTool` so buttons call tools, `app.openLink`
  for deep-links). A surface whose buttons only flip local UI state is NOT wired.
  Cite the file + function.
- **Observed:** the round-trip has been seen render in the **real host** (or
  human-attested via `sulis-attest-scenario` when a machine can't drive it). A
  green unit test against a mock is not this observation.
- **Note (MCP-Apps today):** the ext-apps helpers are TypeScript-only — a Python
  (FastMCP) server must emit the `_meta.ui` binding + MIME by hand, and the card
  must bundle the ext-apps browser runtime. The proven POC is the reference.

**2. Legible — the surface carries its consumer-facing metadata, not just a
technical name.** The protocol already provides the slots (MCP base spec,
2025-11-25); defaulting to `name` only is a GAP:
- `name` — the technical identifier (what we default to).
- `title` — the **user-friendly display name** ("Weather Information Provider").
- `description` — the **one-sentence "what it does on the tin"**, which is *also*
  the model's **when-to-use** signal (the host reads it to decide when to invoke).
- `icons` — the **brand/icon** (`[{src, mimeType, sizes}]`); also at server level.
- **when-to-use** — there is no dedicated structured field; it lives in
  `description` today, or as custom `_meta`. **Source it from the brain's
  Scenario + Requirement entities** rather than free-typing it (the generator is
  tracked as follow-on work).

> **The one design-walk check:** a host-rendered / integration hop is **not
> "exists"** until its protocol binding is cited in code on **both** sides AND the
> round-trip is observed (or attested) in the real host AND it carries `title` +
> one-line `description` + `icon`. Anything less is a GAP that blocks design.

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
