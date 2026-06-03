# Glossary — Sulis app: drive a change from the app

The locked vocabulary for this specification. All artifacts use the preferred terms.

| Term | Definition | Also known as | NOT the same as |
|---|---|---|---|
| **Change** | A unit of work, modelled as a navigable lifecycle thread. The core primitive of the whole product. | — | A file (Cursor's unit); a pull request |
| **Board** | The landing view: every in-flight change shown as cards in columns, one column per stage. | Kanban, landing | The sidebar (a flat list, exists already) |
| **Stage** | Where a change sits in its lifecycle: recon → specify → design → implement → review → ship. | Lifecycle stage | "Status" (a plain-English read-out, see below) |
| **Thread** | One change's detail view inside the app: stage track, status, brain, files, chat. | Change thread, per-change view | The conversation alone (one part of the thread) |
| **Conversation** | The chronological chat history (founder prompts + agent replies) for a change. | Transcript, chat history | The "status" read-out |
| **Status** | The plain-English "what's happening" read-out for a change, computed at read-time. | Progress read-out | A periodically auto-published checkpoint (a non-goal here) |
| **Session** | A running `claude` process for a specific change. | Agent session | The change (data); the conversation (its output) |
| **Liveness** | Whether a change's session is currently running. Detected by a side-effect-free probe. | Running indicator | Reachability for chat (a stricter check) |
| **Brain** | The entities and workflows the agent has created for a change. | — | The conversation; the worktree files |
| **Entity** | One brain item (e.g. a requirement, a workflow step) with content. | Brain item | A file |
| **Worktree** | The on-disk folder of files for a change, kept tucked away under `~/.sulis/changes/`. | — | The change record |
| **Rendered preview** | A file (e.g. `.md`, `.html`) shown the way it is meant to look, not as raw source. | Preview | The raw source view (its toggle) |
| **The seam** | The single API boundary the app reaches all its data through; never the filesystem directly from the client. | Data seam, API boundary | A cloud service (the seam can later be served from the cloud, but is not one now) |
| **Relay** | The server path that delivers a founder's message to a session and streams the reply back. The app's only sanctioned write path (it includes the resume/spawn it triggers). | Chat relay | A read endpoint |
| **Resume** | Restarting a change's most recent (closed) session from its persisted conversation transcript, so the agent wakes with full prior memory. A built-in capability, not invented here. | Resume session | Spawn (which starts a brand-new session) |
| **Spawn** | Starting a fresh session for a change that has never had one, grounded in the change's saved context (CONTEXT.md / manifest / stage / prior decisions) so the agent re-reads the change before acting. | Spawn session | Resume (which restarts an existing session) |
| **Recoverable state** | What a resumed session can restore: the persisted transcript + the worktree files on disk + the brain entities the session created. A step interrupted mid-action at close is re-run, not magically continued. | — | A live in-memory session (lost at close) |
| **Needs attention** | A change that is blocked, waiting on a founder decision, or whose agent stopped mid-reply. An idle-but-fine change is not flagged. | — | "Not running" (a liveness state) |
