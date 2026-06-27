# Visual contract — chat parity + working↔finished signal (both chats)

```yaml
kind: contract
contract_type: visual
surface: chat-both-universal-and-in-change
mockup: chat-both-status.html
inspiration: _mobbin-context.md   # named-product (Mobbin search_screens not exposed this session); structural only
continuous_with: ../../../autonomous-delivery-environment/contracts/visual/chat-redesign/chat-B2-tabbed-workspace.html  # signed Turn-Cards direction
signed_off_at: 2026-06-27         # founder: "Let's press ahead with that design and approach." — the #45 gate cleared
provenance: production-approved   # signed off; this is now the visual source of truth
```

## What this contract covers

Three pieces the founder asked for, brought to one surface:

1. **Turn-summary cards in the universal chat.** The universal (product-wide)
   chat adopts the exact turn card the in-change chat already ships (summary
   lead + rendered body + “show the full reply” + folded steps). Reuses the
   signed chat-B2 card and the one shared `renderMarkdown.ts` (EP-03).
2. **Markdown + code rendered everywhere.** Agent replies render markdown and
   fenced/inline code as formatted HTML in both chats, through the one safe
   renderer. User-typed messages stay verbatim (unchanged on purpose).
3. **A clear “where things stand” signal in BOTH chats** — the centerpiece.

## The status-signal decision (lead the sign-off here)

**Recommended: an explicit, named status line anchored to the conversation —
“Sulis is working…” → “Finished — over to you”.** The ambient caret (the quiet
“pulse only, no words” option) is kept as live texture during streaming but is
NOT the load-bearing cue, because “done” as the mere absence of a pulse cannot
tell the founder it’s *their* move after they look away — which is the exact pain
they named. The named line makes “finished” a positive, visible event. Kept to
one quiet line it costs almost no chrome (CL-01). One component, one vocabulary,
both chats (CL-05).

## Tokens consumed (real, from tokens.css v4.2.0 — no invented hex)

- working line: `--accent` text + a 9%/28% `--accent`-over-`--card` tile.
- finished line: the **signed status-tint pattern** — `--bg-positive` /
  `--bg-positive-border` with a **neutral `--foreground` label** and the green
  carried only by the `--positive` tick (graphical).
- card: `--card` / `--border` / `--foreground` / `--text-secondary` /
  `--bg-muted` / `--border-muted` / brand-spectrum avatar; `--font-sans` (Inter),
  `--font-mono` (JetBrains Mono).

## Accessibility (decided at design time — WCAG 2.1 AA)

- Contrast (measured): working text 4.72:1 light / 5.91:1 dark — **AA text**.
- **Why the finished label is neutral, not green:** `--positive` as small text on
  white is 3.3:1 (below AA-text). So the words use near-black/near-white text and
  the green rides the tick + tint only — AA-safe, and consistent with the token
  system’s own documented status-tint rule (tokens.css lines 41–49).
- Colour-independence: working vs finished differ by icon (pulse vs tick) and
  wording, never by colour alone (WCAG 1.4.1).
- Motion: pulse + caret both honour `prefers-reduced-motion: reduce`.
- Live region: each status line is `role="status" aria-live="polite"` so a
  screen reader announces the working→finished transition.

## Bottom-dock refinements (founder requests, folded into the same mockup)

Both live in the strip just above the message box (`Composer.tsx` bottom block /
`Composer.module.css`). Tokens mirrored verbatim from `Composer.module.css`.

1. **Status line moves to the conventional spot — above the input.** The
   working↔finished line now occupies the single row directly above the
   composer card, *in place of* the suggestion chips. **Recommended coexistence:
   one shared slot, mutually exclusive.** Idle / your-turn → the three suggestion
   chips. On send → that same row becomes “Sulis is working…”. On complete → it
   reads “Finished — over to you”, then returns to the chips once read. The
   keyboard-hint footer stays inside the composer card (unchanged).

2. **De-collision fix (the reported overlap bug).** Root cause: the in-flight
   user/agent bubbles stack above a crowded bottom strip that *also* held the
   `resumedNote` + chips with tight gaps, so a fresh streaming reply read as
   buried under “This change was resumed…”. Fix: the resumed note lives **only**
   in the single status slot and **only** when state is `ready`/your-turn; the
   instant a new turn starts (`state !== "ready"`), the working line takes the
   slot and the resumed note is gone — not stacked. Interrupted/failed notes
   render as their own band *above* the slot (paired with the preserved partial),
   never inside it. One row, one thing at a time.

## Continuity

Card, neutral user bubble, avatar, and every colour/font are lifted verbatim
from the founder-signed chat-B2 Turn-Cards contract and `tokens.css`. This
contract adds ONE new thing — the conversation-anchored working↔finished line —
and brings the universal chat up to the card treatment already approved.
```
