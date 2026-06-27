# ADR-001 — Reuse `TurnCard` in the universal chat; do not extract a new shared renderer

> Status: accepted · 2026-06-27 · Change CH-9642DA · Tier S
> Decision owner: engineering-architect · Scope: Form (structure), EP-03 reuse

## Context

The spec asks the universal (product-wide) chat to adopt the in-change chat's
turn-summary-card treatment: a 2–3 sentence summary lead, a "show the full
reply" progressive-disclosure toggle, folded tool steps, and markdown/code
rendered through the one safe renderer. EP-03 ("check before building new")
requires that we extend or reuse an existing component before authoring a new
one, and extract a shared primitive only when two or more components implement
the same pattern.

Two components are in play:

- **In-change chat** — `Chat.tsx` groups its transcript with `groupTurns()` and
  renders one `TurnCard` per agent turn, fed by `useTurnSummaries(changeId)`.
- **Universal chat** — `ProductChat.tsx` renders each `TranscriptMessage`
  directly via `ChatMessage` → `AssistantBlock`, and `AssistantBlock` renders
  `kind: "text"` blocks as **plain text** (the gap the spec names).

## Options considered

1. **Render `TurnCard` directly in the universal chat** (reuse).
   `groupTurns()` is pure and transcript-shaped (`shared/groupTurns.ts`), so it
   already works on the product transcript. `ProductChat` groups its durable
   transcript and renders one `TurnCard` per turn, exactly as `Chat.tsx` does,
   keeping its own user-bubble rendering.
2. **Extract a new `<AssistantTurn>` primitive** shared between `TurnCard` and a
   rewritten `AssistantBlock`, then consume it in both chats.
3. **Add markdown rendering inside `AssistantBlock`** and leave the two chats
   structurally different (no card treatment in universal).

## Decision

**Option 1 — reuse `TurnCard` in the universal chat.**

`TurnCard` already *is* the shared summary-card-plus-safe-renderer primitive the
spec wants. It encapsulates the summary lead, the "show the full reply" toggle,
folded steps, and both `renderMarkdown` / `renderInlineMarkdown` calls. The
cross-group decision walk lands on **REUSE** (priority 1) before COMPOSE,
EXTEND, or CREATE. The universal durable transcript is grouped with the same
`groupTurns()` and rendered with the same `TurnCard`; `ProductChat` keeps
rendering user messages and the in-flight streamed reply itself.

Implementing the universal-chat wiring is therefore **REORGANISE/EXPAND on an
existing component**, not a new primitive. Option 3 is rejected because it
leaves the two chats divergent — the spec's explicit goal is parity. Option 2
(extract) is rejected under EP-03: a premature extraction over a single reuse
site adds an indirection layer with no second consumer to justify it. If a
third turn-rendering surface ever appears, *that* is the trigger to extract —
not now.

## Consequences

- `ProductChat` gains a `groupTurns()` pass and renders `TurnCard`s; the
  plain-text `AssistantBlock` path is no longer the universal chat's assistant
  renderer. `AssistantBlock` itself is left intact (still used wherever
  `ChatMessage` renders assistant blocks elsewhere — confirmed by its existing
  test) — we change *what ProductChat renders*, not `AssistantBlock`'s contract.
- One renderer, one vocabulary, both chats — satisfying the contract's CL-05.
- The in-change chat's `TurnCard` visuals are unchanged (spec non-goal honoured).
- A characterisation test on `ProductChat`/`ChatMessage` is required first
  (EP-07 / Fowler) to pin today's plain-text behaviour before the swap.
