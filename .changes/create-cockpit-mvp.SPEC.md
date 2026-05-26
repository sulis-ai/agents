# Spec — read-only cockpit MVP

**Change:** CH-01KSJA · create

## Intent

A local web app that lets the founder review every in-flight change in
one place — see the threads, the chat history, the files, and the
diffs — without touching any running Claude session and without
editing anything. A read-only cockpit that gathers what already exists
(the change store, the worktrees on disk, the Claude Code session
transcripts) and renders it as one navigable surface.

The live chat / terminal bridge is explicitly a later change; the
stream-json spike has already validated the underlying mechanism but
nothing in this MVP depends on it.

## Scope

- **Dashboard landing view** — every open change shown as a card, with:
  the change handle + one-line intent, the stage it's at (recon →
  specify → design → implement → review → ship), last activity time,
  and an indicator showing whether a Claude session is currently
  running for that change.
- **Empty state on the dashboard** — when nothing is in flight, show
  clear instructions on how and when to start a change (i.e. how to
  run `/sulis:change start`).
- **Persistent left-hand sidebar** — every change listed as a
  clickable thread; visible from every view so the founder can jump
  between threads without going back to the dashboard.
- **Per-thread view: conversation history** — the full Claude Code
  session transcript for the change rendered as readable chat history
  (prompts + responses, in order).
- **Per-thread view: file browser** — the worktree's content tree
  rendered as an expandable folder/file tree on one side; clicking a
  file opens it in the viewer.
- **File viewer** — the file's current contents rendered formatted
  and read-only (Monaco editor in read-only mode).
- **Diff view** — toggle on any file between "current contents" and
  "diff vs the change's starting point" (the base_sha recorded when
  the change was started).
- **Copy filesystem path** — one click on any file copies its
  absolute filesystem path to the clipboard.
- **Code home** — the cockpit lives at `apps/cockpit/` in this repo,
  structured so it could be extracted to a standalone repo later
  without rework.

## Non-goals

- **No live chat / terminal bridge.** The cockpit never sends prompts
  to a running Claude process and never streams a live session. The
  bridge is a later piece of work; the stream-json spike validated it
  but nothing in this MVP depends on it.
- **No editing.** Every surface is read-only — the file viewer, the
  worktree browser, the transcripts.
- **No running the app or any tooling.** The cockpit does not launch,
  restart, or invoke anything outside its own process.
- **No claude-process management.** "Is there a session running for
  this change?" is the only signal needed; no PID management, no
  killing sessions, no attaching to log streams.
- **No deep-link / permalink URLs in MVP.** The copy action is
  filesystem-path only. Cockpit URLs that open a specific file are a
  later piece of work.
- **No multi-user / remote access.** Localhost only, single founder.

## Acceptance

A founder running the cockpit on their machine can do all of the
following without modifying anything on disk or touching any running
Claude process:

- Start the cockpit locally and open it in a browser.
- See a **dashboard** with every in-flight change as a card showing
  the change's stage, last activity time, "Claude session running"
  indicator, and one-line intent. If nothing is in flight, see clear
  instructions on how to start a change.
- See the **sidebar** of every change on every view; click any entry
  to open that change's thread.
- Inside a thread, read the **full conversation history** from the
  Claude Code session transcript — every prompt and response, in
  order, rendered readably.
- Inside a thread, browse the **worktree's file tree** — expand
  folders, click into files.
- Open a file in the **read-only viewer** with syntax-formatted
  rendering.
- **Toggle to diff view** on any file and see what changed vs the
  change's starting point.
- **Copy the absolute filesystem path** of any file to clipboard with
  one click.
- Confirm by inspection that the cockpit has not written to the
  change store, the worktrees, or the transcripts, and has not
  spawned or touched any Claude process.

## Constraints

- **Read-only across every data source.** The change store (via
  `_change_state.list_all_changes()`), the worktrees on disk, and the
  Claude Code session transcripts under `~/.claude/projects/` are all
  read; none are written.
- **Localhost only.** A React client and a small Node/Express server,
  both running on the founder's machine.
- **Code home is `apps/cockpit/` in this repo.** Structured so it can
  be lifted into a standalone repo later without rework — no
  cross-imports from the rest of the repo beyond the existing data
  layer interfaces (the change store reader, the transcript reader).
- **Must not touch any running `claude` process.** Detecting whether
  a session is running for a change is fine; sending signals, reading
  stdio, or modifying its state is not.
- **Standalone dependencies only.** Node + a browser. No new
  infrastructure (no database, no broker, no daemon) beyond what's
  needed to run a React/Express dev server.
- **Transcript-to-change association is a read-side concern of the
  cockpit.** The server figures out which transcript file belongs to
  which change by inspecting the project directory each transcript
  was recorded against and matching it to the change's worktree path.
  No new state is written to resolve this.
