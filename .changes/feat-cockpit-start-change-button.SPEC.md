---
founder_facing: true
---
# Spec — "Start something new" entry point + start-a-change flow

**Change:** CH-01KTMF · feat

## Intent
Give the founder one obvious way, from inside the cockpit, to start a new
piece of work — a "Start something new" entry point that opens an
intent-first start-a-change flow and, once the change is created, hands the
founder into the change's existing workspace. Design signed off (see
`.design/cockpit-start-change-button/SIGNOFF.md`).

## Scope
- **One front door.** A single, unmistakable "Start something new" button in
  the cockpit's top-bar chrome. ⌘K reaches the same flow (an accelerant, not
  a second door).
- **Intent screen.** Opens on "What do you want to do?" — one free-text box.
  No name field, no work-type picker. Example chips + a soft welcome for the
  cold-start/empty state.
- **Light clarify.** One or two short, skippable questions with a "Step 1 of
  N" stepper.
- **Confirm-before-start gate.** A summary card (what it'll do; that a fresh
  separate workspace is created) and one "Start this work" button. Nothing
  changes until pressed.
- **Start + recovery.** An honest "Starting…" state; a plain-language retry /
  rename if it can't start. Never a dead end.
- **Hand-off.** On success the change exists (branch + worktree, at Recon) and
  the founder lands in the existing change workspace.
- Real cockpit design tokens throughout.

## Non-goals
- **The in-change experience is NOT touched.** The coaching chat, the terminal
  behaviour, the stage bar, and the files view inside an existing change stay
  exactly as they are — out of scope, not redesigned.
- No new server capability beyond what the start-from-intent flow already
  needs (reuse the existing confirm-gated start path; do not build a parallel
  one).
- Not changing how a change is created mechanically (branch/worktree/Recon) —
  only adding the GUI front door to it.

## Acceptance
- The "Start something new" button is visible in the cockpit top bar and is
  the single, obvious primary action for starting work; ⌘K opens the same flow.
- Clicking it opens the intent screen; a first-timer with no changes sees the
  cold-start help (chips / welcome), not an empty wall.
- Describing an intent → a short clarify → a confirm card → "Start this work"
  creates a new change (branch + worktree, at Recon) and lands the founder in
  that change's existing workspace.
- "Start this work" is the only point at which anything is created — before it,
  nothing is changed.
- A failed start shows a plain-language retry/rename, not a dead end.
- The flow is keyboard-reachable with visible focus; colour is never the only
  signal.

## Constraints
- **Depends on the chat + terminal work landing first.** The new top-bar
  chrome, the start-a-change screen, and the start-from-intent flow live on the
  in-flight chat+terminal branch — not on `main` today. This feat builds on
  top of that work and lands after it; it can't be built against `main` as-is.
- **Reuse, don't rebuild.** Wire the front door into the existing
  start-from-intent flow and its server-side confirm gate; don't create a
  second start path.
- **Accessibility flags carried from design:** keep the green "Start this work"
  label bold/16px+ or darken the green (AA-large only at 3.30:1); the display
  font (Satoshi) isn't loaded in the cockpit today, so headings render in Inter
  — design to what's actually loaded.
- Real design tokens only; no invented colours/spacing.
