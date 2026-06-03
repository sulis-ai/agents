# Inspiration probe — Mobbin (CH-01KT50, Sulis app surface)

> UXD-15: **structure transfers, visuals do NOT.** Mined for layout, section
> ordering, density, and interaction beats only. Sulis's own tokens + identity
> (the experience fragments' system; the sunset mark) stay authoritative.
> **inspiration: Mobbin** — run from the main session's Mobbin MCP on 2026-06-03
> (the design-subagent runs had reported the MCP unavailable; this is the proper
> probe). Platform: web. Supersedes the earlier `inspiration: none`.

## Board (stage columns)
- **GitHub Projects** (c4b0e743, 401f3d2a, 65dd2c13) — cleanest, most neutral:
  **small coloured dot + stage name + count** per column header, neutral cards,
  "Add item" per column, a view-switcher (Backlog / Priority / Size / Table) +
  filter bar. Directly validates "just use colours" for stages = a dot per
  column header on an otherwise-neutral board.
- **Plane** (8efafc2b) — richer: collapse/expand per column, per-card metadata
  icons, board/table/calendar switch (more than we need).
- **Trello** (c6ccc5a7) — classic card board.

## Agent thread (closest analogues — this IS our product)
- **Replit Agent** (3d67780e, 76782202) — GOLD. Conversation = agent messages
  **interleaved with inline tool-action log lines** ("Edited db/schema.ts",
  "Executed npm run db:push", "Restarted Start application", "Took a
  screenshot") — SHOW THE WORK, not just chat (agentic AI-01). Plus a
  **"Checkpoint made … Rollback to here"** card (validates the founder's
  checkpoint-as-lineage idea), a **"Paused (waiting for your response)"** state,
  a docked composer, and a right tabbed panel (Progress/Console/…/Chat).
- **Lovable** (150f7186, 43a94ab5) — conversation left with **commit cards
  (Restore / Preview / View code)** + right a **file tree + read-only code** with
  a Preview toggle. Non-technical-founder-drives-agent-that-builds — our shape.
- **v0** (0e51be15) — conversation + **Preview/Code toggle**, **version history
  (Restore/View)**, GitHub sync (Pull/Push, branch).
- **Gemini Canvas** (d4f687a1) — conversation + a **Code/Preview artifact panel**
  (validates rendered↔raw + the right-hand artifact panel).
- **OpenAI Playground** (06c1057d, d93dceff) — minimal neutral USER/ASSISTANT
  labels (validates subtle/neutral sender differentiation, not brand colour).

## File explorer / IDE
- **GitHub Codespaces / VS Code web** (510732c4, 81856131) — canonical EXPLORER
  tree (folders/files) + open tabs + **README rendered preview** + source-control
  + status bar. Reference for the tree + rendered preview.
- **Lovable / v0** — read-only code + Preview toggle + version/restore.

## Dashboard / status
- **Jira** (c5cce2bb) — stat cards + Status-overview donut + Recent-activity feed.
- **ClickUp** (fe9658e0) / **Todoist** (1b82ccf2) / **Current** (257551ac) —
  clean neutral activity feeds. (We stay more restrained; the board IS our
  dashboard. An activity feed maps to a change's lineage.)

## Structural takeaways to adopt (visuals stay ours)
1. **Board:** GitHub-Projects dot-per-column header (coloured dot + name + count)
   on neutral columns; a view-switcher + filter bar.
2. **Thread:** Replit's **inline tool-action log** interleaved with the
   conversation (show the work) + **checkpoint / rollback** cards + a **"paused —
   waiting for you"** state; a **right-hand panel that toggles artifact views**
   (Preview/rendered · Files · Brain/entities) — the Lovable/v0/Gemini split.
3. **Explorer:** VS Code/Codespaces tree + a "Changed" source-control view +
   rendered/raw/diff preview (Lovable/v0 read-only + preview).
4. **Sender differentiation:** subtle/neutral (OpenAI/Gemini), never brand colour.
