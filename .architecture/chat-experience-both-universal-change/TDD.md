# Technical Design — chat parity + working↔finished signal (both chats)

> Change CH-9642DA · feat · Tier S
> Source spec: `.changes/feat-chat-experience-both-universal-change.SPEC.md`
> Signed visual contract (authoritative look-and-feel, 2026-06-27):
> `contracts/visual/chat-both-status.contract.md`
> Scenarios (acceptance bar): `.changes/feat-chat-experience-both-universal-change.scenarios.jsonld`

This is a compact TDD by design (Tier S, all three pillars well-covered). It
references the existing chat seam rather than re-deriving it. The visual
contract is signed and is **not re-opened** here — this TDD names the
*technical* concretions behind it.

---

## 1. What changes, in one paragraph

The universal (product-wide) chat renders agent turns through the **same
`TurnCard`** the in-change chat already ships (summary lead + "show the full
reply" + folded steps + safe markdown), instead of the current plain-text
`AssistantBlock` path. Both chats gain a single calm **status line** above the
message box — "Sulis is working…" while streaming, "Finished — over to you" on
completion — sharing one mutually-exclusive slot with the suggestion chips. That
same slot redesign **fixes the de-collision bug**: the in-flight bubbles and the
resumed note no longer crowd each other; the resumed note yields the slot the
instant a new turn starts. No new library, no new server endpoint, no new client
store, no raw colours.

The four design decisions are recorded as ADR-001..004; read those for the
"why". This document covers the three MECE-3 pillars.

---

## 2. Form — Structure

The existing seam is sound and is reused, not rebuilt:

- **State is owned by the hooks.** `useChatStream(changeId)` (in-change) and
  `useProductChat(scope)` (universal) are the single sources of truth (WPF-04).
  Components are pure renders of what the hook produced. **This change adds no
  state to the hooks** (ADR-002).
- **Turn rendering is a pure transform.** `groupTurns()` (`shared/groupTurns.ts`)
  turns a flat `TranscriptMessage[]` into `ConversationItem[]`; it is
  scope-agnostic, so the universal chat groups its product transcript exactly as
  `Chat.tsx` groups a change transcript. `TurnCard` renders one turn.

### 2.1 Components touched / added

| Component | File | Change |
|---|---|---|
| `ProductChat` | `components/ProductChat.tsx` | Group the durable transcript with `groupTurns()`; render one `TurnCard` per turn (user bubbles stay as today). The in-flight streamed reply still renders here. (ADR-001/003) |
| `AssistantBlock` | `components/AssistantBlock.tsx` | **Unchanged contract.** No longer the universal chat's assistant renderer; left intact for any other consumer. |
| `ChatStatusLine` (new) | `components/ChatStatusLine.tsx` | Shared presentational status line. Maps existing hook `state` + a "reply produced this session" latch → one of {chips, working, finished}. Owns the live region. (ADR-002) |
| `Composer` | `components/Composer.tsx` | Mount `ChatStatusLine` in the single row above the message box, in place of the chips. Resumed/interrupted/failed notes move to bands above the slot (de-collision). (ADR-002/004) |
| `ProductChatDock` | `components/ProductChatDock.tsx` | Mount the same `ChatStatusLine` in its composer's chips row. |

### 2.2 Dependency direction

Unchanged: components → hooks → `api/client`; `groupTurns` and `renderMarkdown`
are pure `lib`/`shared` utilities with no inward dependency. The new
`ChatStatusLine` depends only on the lifecycle *type* (a shared enum), not on
either hook — so it composes into both docks without coupling them.

---

## 3. Armor — Hardening (safety, theming, a11y, honest states)

- **Safe rendering invariant preserved.** All markdown goes through the audited
  `renderMarkdown` / `renderInlineMarkdown` (escape-before-emit, scheme
  allow-list). `TurnCard` already calls these; the universal chat inherits the
  invariant by reusing `TurnCard`. **User-typed messages stay verbatim** —
  `ChatMessage`'s user branch (`<pre><code>`) and `ProductChat`'s user rendering
  are untouched (spec non-goal).
- **No new dependency.** EP-03 honoured — one renderer, reused (ADR-001).
- **Tokens only, theme-aware.** Status-line colours use only contract-named,
  already-defined tokens (`--accent`, `--card`, `--bg-positive`,
  `--bg-positive-border`, `--foreground`, `--positive`); tints via `color-mix`
  over tokens. Coverage extended so the no-raw-colours characterisation test
  guards the new surfaces (ADR-004).
- **WCAG AA, decided at design time** (carried verbatim from the contract):
  working text 4.72:1 light / 5.91:1 dark; finished label is **neutral**
  `--foreground` with green only on the tick + tint (small green text would be
  3.3:1, below AA); working vs finished differ by icon (pulse vs tick) **and**
  wording, never colour alone; pulse + caret honour
  `prefers-reduced-motion: reduce`; the status line is
  `role="status" aria-live="polite"` so the working→finished transition is
  announced.
- **Honest lifecycle states preserved (load-bearing).** FR-19 (clear failure,
  never false "delivered"), FR-22 (interrupted partial kept), FR-26 (honest
  resumed indication) keep working. The status line never reads "Finished" on a
  `failed` or `interrupted` turn — those render their existing bands *above* the
  slot. ADR-002 keeps the hook state machines unchanged, so the existing
  FR-19/22/26 tests pass untouched.

---

## 4. Proof — Verification

**Harness:** Vitest + Testing Library, `apps/cockpit/client/src/tests/`.
**Discipline:** characterisation-first (EP-07 / Fowler) on each touched
component before behaviour change, then the new-behaviour tests. The DOM the
founder sees is the surface — no testing internal helpers in isolation.

| Acceptance / scenario | Verification artifact (concrete) |
|---|---|
| Universal reply is a summary card with a working "show full reply" (scenario `84N8…`) | `tests/ProductChat.turncard.test.tsx` — renders a product transcript, asserts `turn-card` + `turn-full-toggle`, clicks it, asserts `turn-full-text`. |
| Markdown + fenced code render as formatted HTML in both chats (scenario `MV89…`) | `tests/ProductChat.turncard.test.tsx` (universal: heading/list/`<pre><code>` present, no raw `**`/backticks) + existing `TurnCard` markdown coverage (in-change). |
| Status line working↔finished, mutually exclusive with chips (scenario `9ZN6…`) | `tests/ChatStatusLine.test.tsx` (unit: state → slot) + `tests/Composer.test.tsx` and `tests/ProductChatDock.states.test.tsx` (integration: chips↔working↔finished↔chips, never both). |
| New turn never buried under the resumed note (scenario `19VZ…`) | `tests/Composer.test.tsx` — send while resumed-note shown; assert the working line holds the slot and the resumed note is not in the slot. |
| No raw colour literals; light + dark | `tests/no-raw-colours.thread-chat.test.ts` (MODULES extended per ADR-004) stays green; `ProductChatDock.axe.test.tsx` hex guard retained. |
| Honest states preserved (FR-19/22/26) | Existing `Composer.test.tsx` cases pass **unchanged** (regression gate). |
| a11y of the status line | `ChatStatusLine` axe coverage + the existing `ProductChatDock.axe.test.tsx` / Composer axe case extend to the live region. |

No mocks for the rendering path — the renderer and `groupTurns` are real;
streams are driven by the existing injectable fake-stream pattern
(`Composer.test.tsx`'s `fakeStream`, `useProductChat`'s injectable funnels).

---

## 5. Verification Plan

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

1. **User-observable behaviour verified.** The universal chat shows summary
   cards (not raw text); both chats render markdown/code; the row above the box
   reads working→finished and is never shown alongside the chips; a new send is
   never buried under the resumed note. Light + dark both correct.
2. **Verification environment(s).** Local + CI, the existing cockpit-client
   Vitest project under `apps/cockpit/client/src/tests/`. No staging dependency.
3. **Bootstrap-from-zero.** A fresh clone at the merge SHA runs the
   cockpit-client test target green with no external service — all inputs are
   in-repo (renderer, `groupTurns`, injectable fakes).
4. **Per-integration strategy.** No new third-party platform touch (no
   GitHub/Stripe/email/cloud). All integrations are `existing`, in-app: the safe
   renderer, `groupTurns`, `useChatStream`/`useProductChat` via their injectable
   stream funnels. No Platform Contract required.
5. **Per-kind adapter (frontend).** Vitest + Testing Library specs exercising the
   rendered DOM; jest-axe for the a11y gate. Artifacts named in §4.
6. **Infrastructure needs surfaced (deferred).** None for this change. One
   recorded follow-on (out of scope): product-scoped generated summaries —
   need id `summary-endpoint-product-scope` (ADR-003).

Every WP's `verification:` is **Shape 1 — concrete** (a real Vitest spec lands
with the WP), except WP-001 (the visual-contract gate, `na: true`).

---

## 6. Sizing Report

- **Tier:** S computed (sFPC 5, ASR 5), confirmed. See `SIZING.md`.
- **TDD length:** ~150 lines — within the Tier S target; compact because all
  three pillars are well-covered and the seam is referenced, not re-derived.
- **ADRs:** 4 — each affects more than one component or rejects a viable
  alternative (reuse-vs-extract, derive-vs-new-state, fallback-vs-endpoint,
  colour-coverage). None duplicates an existing ADR (no `.context/` registry).
- **Restated authoritative sources:** none — the signed visual contract is
  referenced, not copied; the renderer's safety model is referenced, not
  re-explained.
- **Circuit breakers:** none triggered (length ≤ 1.5× target; ADRs ≤ tier max).
