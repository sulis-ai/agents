# Code Review: WP-003 — Frontend per-product chat dock

> **Timestamp:** 2026-06-25T215537Z (ISO 8601 UTC)
> **Author:** executor (autonomous)
> **Branch:** wp/create-product-wide-chat/wp-003-frontend-chat-dock → change/create-product-wide-chat
> **Files changed:** 17 (1927 insertions, 2 deletions)
>
> **Outcome:** Needs changes before merge → (resolved inline; re-review PASS)

---

## At a glance

This pull request builds the per-product chat dock — the right-docked, collapsible chat that switches with the product, with the Claude/Antigravity agent picker and the talk-to-start-a-card flow. The build is clean (no type or lint errors), the accessibility gate is met, and it reuses the shared menu and the shared active-product state exactly as the design asked.

One real gap was found: the chat could create a card ("Start work") but the plain "send a message and get a reply" path was built behind the scenes and never connected to the box you type in — and the hint said "Enter to send" with nothing wired to Enter. That has been fixed, along with two smaller robustness issues in how the agent choice is remembered.

## What to fix

(All items below were fixed inline in this same change; re-review found nothing remaining.)

### Must fix — the chat could not actually send a message

**What's happening:** The dock had a "Start work" button (which creates a change card) but no way to just send a chat message and see the reply stream back, even though that machinery was fully built and the box said "Enter to send".

**Why it matters:** Sending a message is the core of a chat. Without it, the streamed-reply area could never appear in the real app.

**What to do (done):** Wired the typing box to send on Enter (Shift+Enter for a newline) and added an explicit Send button next to Start work, both driving the existing send path.

### Worth fixing — the agent choice could stick to the wrong product

**What's happening:** When you picked Claude or Antigravity, that choice was remembered optimistically but never cleared — so after the conversation reloaded, or after you switched to a different product, it could keep showing the previous choice.

**Why it matters:** The picker must honestly name the agent actually running this product's chat (that is an explicit product principle). A stale choice breaks that honesty.

**What to do (done):** The remembered choice now resets when a product's conversation reloads and when you switch products, so the picker always reflects the real running agent.

### Worth fixing — a failed agent switch was silent

**What's happening:** If saving the agent switch failed on the server, the error went nowhere and the picker kept showing the un-saved choice.

**What to do (done):** A failed switch now rolls back the optimistic choice instead of leaving it stranded.

### Minor — keyboard focus + tidy-ups

The starter chips now show a focus outline when tabbed to; a couple of unused/near-unused bits were removed or made robust.

## How this pull request is shaped

**Size — worth being aware of.** ~1,900 lines across 17 files. That is large, but it is one coherent surface (the dock) built against one contract, which is why the design kept it as a single piece of work. Seven of the files are the feature; six are tests; the rest are small shared helpers.

**Scope — clean.** One feature, one type of change. No migrations, no schema changes, no infrastructure, no secrets.

**Completeness — good.** Seven new source files, six new test files. New behaviour ships with tests.

---

## Technical detail

### Verdict

`Request changes` (F-01 high in diff) at review time → **all findings resolved inline** → re-review `PASS`.

### Summary

- **Build Verification:** 0 PR-introduced errors (typecheck clean, lint clean) — CR-01.
- **PR Hygiene:** size medium (one-surface WP, deliberate), scope/safety/completeness clean — CR-09.
- **In the changes:** 7 findings (0 critical, 1 high, 2 medium, 4 low).
- **In the neighbours:** 0.
- **Draft fixes:** 0 deltas queued — all findings fixed inline within the WP (Path A).

| Lens | In changes | Top concern |
|---|---|---|
| Architecture | F-01, F-03 | chat.send relay unwired; switchProvider no error handling |
| Quality | F-01, F-02, F-05, F-06, F-07 | unwired send; pendingProvider shadow bug |
| Security + A11y | F-04 | clean security; .chip focus ring missing (WPF-13 parity) |

### Build Verification (CR-01)

No PR-introduced errors. `npm run typecheck` clean on HEAD; `npm run lint` clean on HEAD. Read-only gate + fetch-inventory gate green.

### Findings in the Changes

- **F-01 (high, architecture + quality)** `ProductChatDock.tsx` — `useProductChat.send` built + unit-tested but never invoked by the dock; textarea has no Enter handler despite the "Enter to send" hint; only `startWork` (chat→card) is wired. The `ProductChat` streamed-reply block is unreachable in the running app. **Fix:** add an Enter/Shift+Enter handler + an explicit Send button driving `chat.send(draft)`; add a dock-level send test.
- **F-02 (medium, quality)** `useProductChat.ts` — `pendingProvider` optimistic state never resets and is not keyed by scope; shadows the real provider after refetch and carries across product switches. **Fix:** reset `pendingProvider` on thread reload / scope change (effect keyed on scope + dataUpdatedAt).
- **F-03 (medium, architecture)** `useProductChat.ts` — `switchProvider` has no try/catch; a failed PUT becomes an unhandled rejection with un-rolled-back optimistic state. **Fix:** try/catch, roll back `pendingProvider` on failure.
- **F-04 (low, a11y)** `ProductChatDock.module.css` — `.chip` lacks `:focus-visible` ring (WCAG 2.4.7; parity with every other control). **Fix:** add focus-visible outline.
- **F-05 (low, quality)** `providerName.ts` — `providerName()` accessor is dead code (both consumers index `PROVIDER_NAME` directly). **Fix:** remove the accessor.
- **F-06 (low, quality)** `ProductChatDock.tsx` — `headerGlyph` computed only to feed a hidden, unasserted span. **Fix:** drop the unused span + the glyph from the memo.
- **F-07 (low, quality)** `ProductChatDock.tsx` — `useStartFromIntent` return not memoized so the propose effect runs every render (masked by the null-reset guard); `cardProductId` not reset in `handleSwitch` (masked by callers re-setting). **Fix:** reset `cardProductId` in `handleSwitch` to make the invariant explicit (the effect guard already prevents double-fire; memoizing the upstream hook is out of this WP's file scope, noted on Watch List).

### Findings in the Neighbours

None.

### Watch List

- `useStartFromIntent` returns a fresh object each render (not memoized). This WP's propose effect is safe (null-reset guard prevents re-fire), but memoizing that hook's return is a robustness improvement in a file outside this WP's scope — left for a future touch of `useStartFromIntent.ts`.

### Methodology

#### Code Review Standard self-attestation (CR-08)

- [✓] **CR-01 Mechanical baseline ran.** `npm run typecheck` + `npm run lint` on HEAD: both clean (0 PR-introduced errors). Secret-pattern grep: none. JSX identifier scan: all resolve in scope.
- [✓] **CR-02 Parallel dispatch used.** 3 lenses dispatched concurrently (architecture / quality / security+a11y). Diff 1927 lines / 17 files — above carve-out, parallel required.
- [✓] **CR-03 Full-file reads.** All changed files >50 lines read end-to-end by the assigned lens.
- [✓] **CR-04 Evidence discipline.** All findings cite file + quoted text.
- [✓] **CR-05 Severity rubric.** Applied — 1 high, 2 medium, 4 low; no neighbour findings.
- [✓] **CR-06 Verdict computed.** Request changes (1 high in diff) → resolved inline → PASS on re-review.
- [✓] **CR-07 Lens completion.** Architecture: F-01, F-03 + clean categories enumerated. Security: nothing surfaced (XSS/URL/secrets/SSRF all clean). Quality: F-01,02,05,06,07 + jsx scan + dead-surface + contract-drift + test-coverage. A11y: F-04 + WPF-13 gate substantially met.
- [✓] **CR-09 PR Hygiene applied.** Scope low, Size medium (one-surface WP), Safety none, Completeness none. No PH-03 high → no auto-downgrade.

#### Run details

- **Diff source:** staged `git diff --cached change/create-product-wide-chat`
- **Neighbour expansion:** git grep (ProductControl callers, fetch funnel, useActiveProduct); 0 neighbour findings
- **Lenses dispatched in parallel:** yes (3 sub-agents)
