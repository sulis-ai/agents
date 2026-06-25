# ADR-004 — How a thread relates to the cockpit's existing session model

> **Status:** accepted · **Date:** 2026-06-24 · **Change:** CH-GJ9KQR

## Context

The cockpit already has a "session" concept, and it is **not** the platform's
Thread:

- The **session-manager daemon** (`plugins/sulis/scripts/_session_manager/`)
  spawns a **per-CHANGE interactive `claude` PTY** in the change's worktree. It
  is **change-keyed** (`open(key=change_id)`), tied to a live OS process, and
  carries an **in-memory** `EventLog` (a `deque`; not durable — confirmed at
  `manager.py:286`, `EventLog()` with no persistence). The session **is the
  live process**: it dies, restarts (reusing the same in-memory log + key), and
  ends with the process.

- A platform-style **Thread** (ADR-001) is **workspace-independent,
  platform-scoped, multi-participant, and durable.** It outlives any one
  process.

These are different things at different lifetimes. The change must reconcile
them explicitly rather than overload one word.

## Decision

**A thread is the durable conversation record; the cockpit session (PTY
process) is the live process that writes into it.**

- **Thread = the durable record.** It owns the append-only message log and the
  versioned ThreadMemory. It survives process death, restart, crash-resume, and
  (later) a provider switch. It is keyed by the bound change (today, one thread
  per change — the same key the session-manager already uses), with the schema
  permitting more than one thread per change later if needed.

- **Session (PTY process) = the live writer.** When the session-manager spawns
  or restarts the per-change `claude` PTY, that process **appends each
  prompt/message to the bound thread's durable log** and **updates the thread's
  ThreadMemory** at checkpoint boundaries. The session's existing in-memory
  `EventLog` stays as-is for **live-tail / viewer fan-out** (its current job);
  the new durable thread store is the **authoritative persisted record** the
  in-memory log mirrors into.

- **The existing `events.Event` vocabulary is the bridge.** The session's
  stdout pump already decodes provider output into provider-neutral `Event`s
  (`chunk` / `tool_use` / `result` / `error`). The new durable append is fed
  from that same Event stream — one neutral vocabulary, two sinks (the
  in-memory live log + the durable thread log). No second decode path.

- **Restart / resume reuses the same Thread.** The session-manager's
  "restart-is-not-a-new-key" invariant (§2.7) maps cleanly: a restarted PTY
  binds to the **same** thread and continues its log. **Resume from our context
  (the load-bearing journey)** seeds a fresh PTY from the thread's ThreadMemory
  payload via the brief/`SessionSpec` argv seam — **without** reading the
  provider's transcript.

## Rejected alternatives

- **Make "session" and "thread" the same object.** Rejected: their lifetimes
  differ (process-bound vs durable) and their participant models differ
  (one process vs multi-participant). Overloading one word is the ambiguity
  this ADR exists to remove. We keep "session" for the live PTY process
  (internal) and "thread" for the durable record (founder-facing + new types).
- **Persist by making the in-memory `EventLog` durable in place.** Rejected:
  the in-memory log is tuned for live-tail follow semantics (offset cursors,
  follower condition variables, retention eviction) — bolting durability onto
  it conflates two concerns. The durable thread store is a separate, append-
  only persistence surface; the in-memory log mirrors into it. (This is a Form
  separation, not a wrap.)

## Consequences

- One thread per change today (same key as the session). The thread record
  carries `resumed_from` (ADR-003) to chain a resumed PTY to its predecessor.
- The session-manager gains a **durable-append side-effect** on its existing
  Event append path (a new sink), and a **payload-seed read** on spawn/resume.
  Both are additive to the existing pump; the live-tail path is unchanged.
- Founder-facing language and the new types say **"thread"**; the
  session-manager's internal code keeps "session" for the process. The mapping
  is recorded here so the two never get conflated in review.
