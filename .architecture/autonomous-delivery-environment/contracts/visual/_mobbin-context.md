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

## New surfaces — second probe (scope #7 concierge/onboarding + #8 multi-product)

### Conversational setup / connect-or-create a repo
- **Vercel** (03666e2e) — "Let's build something new": **Import Git Repository**
  (select namespace + search; Install GitHub app) **OR** Clone Template. The
  canonical import-or-template split.
- **Replit** (0ce51e8a) — "Create a new App": tabs *Create with Agent / Choose
  Template / **Import from GitHub*** (My Repositories list + From URL) +
  public/private.
- **Render** (6362a411) — "Connect a repository": repo list with **Connect**
  buttons + GitHub/GitLab/Bitbucket account connect + a Public Git URL option.
- **GitHub** (a373a95d) — "Import your project": clone URL + owner/name +
  public/private + Begin import (the **create-new** branch model).
- **v0** (fb3fd3fe) — Project Settings → Integrations → "Sign in with GitHub".
- **Takeaway:** the find-or-create branch is a proven shape — *connect existing
  (pick from list OR paste URL)* vs *create new (name + private/local)*. Sulis
  wraps it in the concierge conversation; underlying choices stay the same.

### Product / workspace switcher (multi-product, #8)
- **Fibery** (6a3f8982) — top-left workspace switcher (`Jsmobbin ▾`) + left-nav
  Spaces/Products; also a **⌘K command palette** ("Type to start search") — a
  concierge-navigation reference.
- **Zeplin** (c0da49ef) — workspace header switcher + projects grid + Create.
- **Dovetail** (7374d9ba) — account menu → "Switch workspaces"; workspace home
  with project cards; a "New → Project / Connect integrations" menu.
- **Jira** (a4c9f96b) — a scoped **Project dropdown** (recent + show-full-list)
  in the toolbar that scopes the view.
- **Takeaway:** top-left **active-Product switcher** (name + dropdown listing the
  Tenant's Products + "set up a new product"); switching re-scopes the board +
  the per-product views. The board is per-Product.
