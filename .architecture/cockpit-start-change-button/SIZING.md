# Sizing — cockpit-start-change-button

> Computed 2026-06-08 from the SPEC + the in-flight branch
> `change/create-change-owned-terminal-shared-session` (the real target — this
> feat builds on top of it, not on `main`). Read this instead of recomputing in
> downstream skills.

## What this change actually is

The hard parts already exist on the target branch: the `/start` route, the
`<StartFromIntent />` surface (hero question + intent box + proposal-as-confirm-
gate + started/error states), the `useStartFromIntent` lifecycle hook, the
server-side confirm-gated funnel (`streamStartFromIntent`), and the new
`WorkspaceTopBar`. **This change wires the front door into those pieces.** Three
thin new client seams:

1. A "Start something new" primary button in `WorkspaceTopBar` → navigates to
   `/start`.
2. A global `⌘N` / `⌘K` keydown handler that reaches the same `/start` flow.
3. Cold-start chips + welcome on the intent screen (the mockup shows them; the
   existing `<StartFromIntent />` has none yet).

## Functional complexity (sFPC)

| Element | Count | Items |
|---|---|---|
| ILF (internal data) | 0 | no new persisted data |
| EIF (external data) | 0 | reuses the existing start-from-intent funnel; no new external integration |
| EI (mutating ops) | 0 | the confirm-gated change-start already exists server-side; not touched |
| EO (deriving ops) | 0 | — |
| EQ (retrieving ops) | 0 | — |
| Client surfaces (sanity) | 3 | top-bar button, global key handler, cold-start chips/welcome |
| **sFPC** | **~3** | all client-side; no server/data elements |

## Architecturally significant requirements (ASR)

| ASR | Source | Note |
|---|---|---|
| One front door — a single primary action; everything else is an accelerant to the *same* flow, never a parallel one | SPEC Scope; JOURNEY "the one decision" | the load-bearing design constraint |
| ⌘N / ⌘K reaches the identical `/start` flow | SPEC; JOURNEY §1 | a small global keydown handler — new infra (no palette exists today) |
| Cold-start chips + soft welcome on the empty state | SPEC; JOURNEY §2; MOCKUP state 2 | new — the existing surface has no chips |
| Reuse the existing confirm-gated start path; do NOT build a parallel one | SPEC Constraints; SPEC Non-goals | satisfied by routing to `/start` + reusing `useStartFromIntent` |
| Keyboard reachability + visible focus; colour never the only signal | SPEC Acceptance; design a11y section | mostly inherited from the existing surface; the new button + chips must conform |
| Green "Start this work" button is AA-large only (3.30:1) — keep the label bold/16px+ or darken the green | SPEC Constraints; design flag | applies to the existing confirm button's styling |
| Display font (Satoshi) not loaded — headings render in Inter | SPEC Constraints; design flag | design-to-what's-loaded; not a code task beyond not assuming Satoshi |
| **ASR count** | **7** | mostly a11y + reuse constraints, not net-new architecture |

## Tier

- sFPC ~3 → tier S band; ASR 7 → tier M band (lower end). The framework says
  take the higher — but the higher number here is dominated by accessibility
  constraints already solved by the existing flow (focus, contrast, colour
  independence) and by two reuse constraints (one front door; no parallel path)
  that are satisfied by *routing*, not by new architecture. The only genuinely
  new architecture is one global keydown handler and one empty-state addition.
- **Tier: S.** A tier-S TDD that references the existing cockpit + the in-flight
  branch rather than restating them. Target: ~120–180 lines, 1–2 ADRs.
- File-count sanity check: the change adds ~1 small hook/handler + edits 2
  components (`WorkspaceTopBar`, `StartFromIntent`) + 1 CSS module + tests.
  Consistent with tier S. No mismatch.

## Per-pillar addressable coverage

| Pillar | Coverage | Action |
|---|---|---|
| Form | Strong — the cockpit's component/route shape, the `WorkspaceShell` → `WorkspaceTopBar` chrome, the `/start` route, the `useStartFromIntent` hook (the one source of truth for start state) are all established on the target branch. | Reuse. The button is a new control in an existing component; the key handler is a new tiny hook mounted in `WorkspaceShell`. No new layers. |
| Armor | Strong — resilience lives server-side in the existing funnel; the confirm gate is server-authoritative (`confirmToken`); the hook already projects a typed error + a never-a-dead-end retry. | Nothing to add. The front door carries no network of its own; it navigates. The error/retry path is inherited from `<StartFromIntent />`. |
| Proof | Strong — `StartFromIntent.test.tsx` exists; the cockpit uses React Testing Library + the injectable `streamStartFromIntent` fake. | Add component tests for the new button (renders, navigates, focus), the global key handler (⌘N/⌘K → `/start`, ignores when typing in an input), and the cold-start chips (render on empty, fill the box on click). No new test infra. |

## Confirmed

- Tier: **S** (computed at draft; the ASR count sits in the M band but is
  dominated by inherited a11y/reuse constraints, so S is the right effort).
- Target TDD length: ~120–180 lines. This TDD references the existing cockpit
  architecture and the in-flight branch rather than restating them.
