# Local UI — a "changes-as-threads" cockpit for non-technical users

> Status: **brainstorm** (diverge → converge, research-grounded). Not yet a
> committed design. The recommendation at the end is what graduates into
> change(s).
>
> Method: Double Diamond. Sources at the foot.

---

## Why this brainstorm exists

A non-technical founder runs work through Sulis but lives at the command
line — `/sulis:dashboard`, `/sulis:change`, spawned terminals. They asked
for a **local UI** that lets a non-technical person:

- **view and navigate every change in flight**, switching between them;
- treat each change as a **thread** — its chat history + the prompts that
  drove it, alongside its files;
- **browse the worktree** (files + folders) for a change and **open/read**
  files;
- **copy a link** to a file;
- **review the files being created** — a read-only "dev check" (confirmed:
  *eyeball the code/files*, not run the app and not the automated checks);
- with **chat + terminal live inside it**, VS Code-shaped.

Open question they posed directly: *is there an open-source VS-Code-like
base to build on?*

---

## Diamond 1 — the problem space

### Discover

What the request actually decomposes into:

1. **A thread list** — every change, its stage, live-or-not. This already
   exists as data: `list_all_changes()` (the `/sulis:dashboard` read seam).
2. **Per-thread chat + prompts** — the conversation that drove the change.
   This already exists too: Claude Code stores session transcripts as JSONL
   under `~/.claude/projects/`; a change-bound session is identifiable.
3. **Per-thread files** — the change's worktree on disk (the global store
   already records `worktree_path`).
4. **A read-only file/diff viewer** — "what's in this file" and "what did
   this change touch."
5. **Copy-link to a file** — a deep link that reopens that file in the
   cockpit.
6. **A live terminal + live chat** — the hard part: not just *history*, but
   a running Sulis session embedded in the UI.

### Define (the core insight)

> The data layer already exists (the global change store + worktrees +
> session transcripts). What's missing is a **visual veneer** over it. And
> the audience is **non-technical** — so the frame is *not* "be VS Code"
> (an engineer's editing cockpit), it's a **thread-centric review surface**
> that borrows IDE components but hides IDE complexity.

The founder's own framing — *changes are threads* — is the right model: a
messaging-app shape (threads in a sidebar; each thread = chat + artifacts),
not a developer IDE shape.

---

## Diamond 2 — the solution space

### Develop (diverge — options)

#### Decision A — the tech base (the founder's OSS question)

- **A1 — Fork a browser VS Code** (`code-server` or Gitpod's
  `openvscode-server`). Faithful VS Code in a browser. *Pro:* instant
  full IDE. *Con:* it IS an engineer's IDE — wrong audience; we'd spend
  effort *hiding* features; some VS Code extensions (LiveShare, remote
  containers) are proprietary and unavailable in derivatives.
- **A2 — Build on Eclipse Theia.** An open (non-fork) IDE *framework*
  designed to be customised into your own product — detachable views,
  custom toolbars, AI-native. *Pro:* built for "make your own IDE";
  genuinely extensible. *Con:* still IDE-shaped and heavy; a big framework
  to learn for what is mostly a read/navigate surface.
- **A3 — Bespoke cockpit reusing IDE components.** Compose the proven
  pieces — **Monaco** (the editor that powers VS Code, run *read-only* for
  the file/diff viewer) + **xterm.js** (the terminal) + a file tree + a
  thread sidebar + a chat panel — into a purpose-built, non-technical UX.
  Prior art exists for exactly this combination (Monaco + xterm.js + tree).
  *Pro:* the UX is ours, tuned for non-technical users; reuse battle-tested
  components for the genuinely hard bits (editor, terminal). *Con:* we build
  the shell ourselves.

#### Decision B — the shell

- **B1 — Localhost web app.** A local server renders the cockpit in the
  browser. Simplest to build + iterate; nothing to install beyond the
  marketplace.
- **B2 — Tauri desktop app.** Rust backend + the OS's own webview. ~25×
  smaller than Electron, far less RAM, credible modern default for a new
  lightweight local app. *Pro:* "real app" feel, small, secure. *Con:* Rust
  toolchain; packaging.
- **B3 — Electron desktop app.** The mature, JS-all-the-way default. *Pro:*
  proven packaging/auto-update. *Con:* heavy (150MB+ baseline); growth
  plateaued vs Tauri.

#### Decision C — live vs read-only

- **C1 — Read-only first.** Thread list + chat *history* + file browser +
  read-only file/diff viewer + copy-link. Low risk; delivers the founder's
  core "view, navigate, review" ask immediately.
- **C2 — Live integration.** Embedded *running* terminal (xterm.js + a pty
  bridge) + live chat with the running Sulis session + switching between
  live sessions. High value, but bridging a live Claude Code agent session
  into a web UI is the genuinely uncertain, hard part.

### Deliver (converge — critical-thinking gates → recommendation)

Gates applied:

- **Assumption test.** "Non-technical users want an IDE." *False* — they
  want to view / navigate / review, not edit. → reject A1/A2 as the primary
  frame; choose **A3** (bespoke cockpit, IDE components inside).
- **Convention preference.** Reuse the actual VS Code components (Monaco,
  xterm.js) rather than bespoke editors/terminals; reuse the existing
  session transcripts rather than invent a chat store; reuse
  `list_all_changes()` (the dashboard seam) as the thread-list data source.
  Maximum reuse, minimum new surface.
- **Falsifiability / risk.** The live terminal + live chat bridge (C2) is
  the highest-uncertainty piece. It should be **de-risked with a prototype
  before committing** — exactly the disposable `--prototype` change flavour
  in the brainstorm-and-routing design. Prove the bridge throwaway-style;
  then build it for real.
- **Sequencing (anti over-build).** Read-only cockpit (C1) ships the core
  value fast and safely; live integration (C2) is a separate, later phase.

**Recommendation:**

1. **Bespoke "changes-as-threads" cockpit (A3)**, reusing Monaco (read-only
   file + diff viewer) + xterm.js (terminal) + a thread sidebar + a chat
   panel. Not a forked IDE — a review surface that borrows IDE parts.
2. **Localhost web app first (B1)**; revisit **Tauri (B2)** for a packaged
   "real app" once the shape is proven. (Web-first keeps iteration fast and
   avoids a toolchain commitment before the UX is validated.)
3. **Read-only first (C1).** MVP: thread sidebar from `list_all_changes()`
   → per thread: chat history (rendered from the session transcript) +
   worktree file browser + read-only Monaco file/diff viewer + copy-link.
   This is the founder's whole "view, navigate, review" ask, all read-only,
   all over data we already have.
4. **Live terminal + live chat (C2) as a later phase, prototype-first** —
   de-risk the session-bridge with a disposable prototype change before
   building it for real.

**Suggested sequencing (each its own change):**

1. Read-only cockpit MVP (thread list + chat history + file browser + diff
   viewer + copy-link). *Reuses the dashboard data layer entirely.*
2. *(Prototype)* spike the live-session bridge (xterm.js ↔ a running Sulis
   session) — throwaway, to prove feasibility + pick the transport.
3. Live terminal + live chat + live-thread switching, built on what the
   prototype proved.

---

## How it relates to what already exists

- **It's the GUI sibling of `/sulis:dashboard`.** The dashboard is the
  by-change view at the command line; this cockpit is the same view made
  visual, drillable, and file-aware. Same `list_all_changes()` seam.
- **`/sulis:inbox`** becomes the cockpit's "needs attention" surface.
- **Changes-as-threads** is the existing change model (branch + worktree +
  session) given a messaging-app skin.

The cockpit invents almost no new state — it reads the global store, the
worktrees, and the session transcripts.

---

## Open questions (resolve before / within the changes)

1. **Chat-history source.** Confirm the change-bound session's JSONL
   transcript is reliably locatable from the change record (map
   `SULIS_CHANGE_ID` / worktree path → the `~/.claude/projects/` session).
2. **Copy-link semantics.** A deep link that reopens a file in the cockpit
   (`localhost`/app deep link), a `file://` path, or a future shareable URL?
   (Lean: cockpit deep link for local; design it so a hosted URL can slot in
   later.)
3. **Diff baseline.** "What this change touched" = diff vs the change's base
   SHA (already recorded as `base_sha`). Confirm that's the right baseline
   for the non-technical "what changed" view.
4. **Web-first vs Tauri.** Start localhost-web (lean), or commit to Tauri up
   front for the packaged feel? (Lean: web first; Tauri once proven.)
5. **Is this `sulis`-plugin-hosted or a separate local app/repo?** A local
   UI is a different artifact class from skills/agents — may warrant its own
   home with the marketplace as its data source.

---

## Sources

OSS IDE bases:
- [Eclipse Theia vs OpenVSCode-Server — eclipse-theia discussion #13899](https://github.com/eclipse-theia/theia/discussions/13899)
- [Theia IDE — AI-Native Open-Source Cloud and Desktop IDE](https://theia-ide.org/)
- [Eclipse Theia and VS Code Differences Explained — Eclipse Foundation](https://blogs.eclipse.org/post/mike-milinkovich/eclipse-theia-and-vs-code-differences-explained)

Component reuse:
- [Monaco Editor — microsoft/monaco-editor](https://github.com/microsoft/monaco-editor)
- [simpIDE — browser IDE: xterm + monaco + treejs](https://github.com/zoutepopcorn/simpIDE)
- [online editor with terminal: react + xterm.js + monaco-editor](https://github.com/xughv/editor)

Desktop shell:
- [Tauri vs Electron 2026: bundle size, RAM, security — PkgPulse](https://www.pkgpulse.com/guides/electron-vs-tauri-2026)
- [Tauri in 2026 — DEV Community](https://dev.to/ottoaria/tauri-in-2026-build-cross-platform-desktop-apps-with-web-technologies-better-than-electron-11mo)

Internal precedent:
- `plugins/sulis/skills/dashboard/SKILL.md` — `list_all_changes()` read seam (the thread-list data source).
- `plugins/sulis/skills/inbox/SKILL.md` — the "needs attention" surface.
- `plugins/sulis/docs/brainstorm-and-routing-design.md` — the `--prototype` disposable-change flavour this brainstorm leans on to de-risk the live bridge.
- `plugins/sulis/docs/change-as-primitive-design.md` — the change = branch + worktree + session model the cockpit visualises.
