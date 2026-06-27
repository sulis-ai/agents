# ADR-002 — The working↔finished status line derives from the existing lifecycle; it adds no new state

> Status: accepted · 2026-06-27 · Change CH-9642DA · Tier S
> Decision owner: engineering-architect · Scope: Form (state), Armor (a11y)

## Context

The visual contract adds one calm status line above the message box: it reads
"Sulis is working…" while a reply streams and "Finished — over to you" when the
turn completes, then returns to the suggestion chips once read. It must be
mutually exclusive with the chips, and it must be a live region
(`role="status" aria-live="polite"`). The status line ships in **both** chats —
the in-change `Composer` (driven by `useChatStream`) and the universal
`ProductChatDock` (driven by `useProductChat`).

Both hooks already expose the same lifecycle vocabulary:
`"ready" | "resuming" | "spawning" | "replying" | "interrupted" | "failed"`,
plus `isStreaming`. `useChatStream` is documented as the ONE source of truth for
chat state (WPF-04); the components own no chat state of their own.

The question: where does "Finished — over to you" come from? It is not a hook
state — the hook goes `replying → ready`, and `ready` is also the idle state.
"Finished" is the *transition* `replying → ready`, held until the founder's next
interaction.

## Options considered

1. **Add a `"finished"` member to `ChatLifecycle`** in both hooks.
2. **Derive a small presentational status enum in a shared component** from the
   hook's existing `state` + a "have we shown a reply this session" latch, with
   no change to the hook's state machine.
3. **Track the finished flag in component-local state** ad hoc in each dock.

## Decision

**Option 2 — derive the status in a shared presentational component, no hook
change.**

Add one small shared component (working name `ChatStatusLine`) that takes the
existing `state` (and whether a reply has been produced this session) and maps
it to one of three presentational slots:

- `working` — when `state === "replying"` (and during `resuming`/`spawning`,
  which are honest "waking up / starting" sub-states of working).
- `finished` — when the session has just completed a reply (`replying → ready`
  observed) and the founder has not yet acted. This is the only *new* derived
  bit; it is a presentational latch, not lifecycle state.
- `chips` — the idle/your-turn state, and the state once "finished" is dismissed
  by the founder's next interaction (the contract's "returns to the chips once
  read").

The component owns the latch; the hooks keep their single source of truth
(WPF-04) untouched. `interrupted` and `failed` continue to render their existing
honest bands **above** the slot (per the contract's de-collision section) — the
status line never claims "finished" on a broken or failed turn (preserves
FR-19/FR-22).

Option 1 is rejected: "finished" is a view concern (a held transition), not a
domain lifecycle state; pushing it into the hook would pollute the one source of
truth and force both hooks plus every existing hook test to absorb a state that
only the new line cares about. Option 3 is rejected: duplicating the latch in
two docks is the EP-03 anti-pattern this ADR exists to prevent — one shared
component, one definition of "finished", both chats (contract CL-05).

## Consequences

- One shared `ChatStatusLine` component, consumed by `Composer` and
  `ProductChatDock`. Each dock passes the hook's `state` + a "reply produced"
  signal; the component decides which slot shows.
- The slot is mutually exclusive by construction — it renders exactly one of
  {chips, working line, finished line}, never two.
- The live region (`role="status" aria-live="polite"`) lives in the shared
  component, so the working→finished announcement is identical in both chats and
  the existing axe coverage extends to it.
- No change to `useChatStream` / `useProductChat` state machines → the existing
  `useChatStream.test`, `useProductChat.test`, and the FR-19/22/26 Composer
  tests keep passing unchanged.
- The "finished → chips on next interaction" reset is a presentational event
  (focus/typing/sending or reading), defined once in the shared component.
