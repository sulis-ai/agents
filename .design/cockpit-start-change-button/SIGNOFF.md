# Design sign-off — "Start something new" journey

**Signed off by the founder: yes** (2026-06-08).

## Scope (agreed)
The design covers **the way in only** — the entry point + the start-a-change
flow — and hands off into the **existing in-change experience, which is NOT
redesigned** (out of scope; the founder likes it as-is).

## The approved journey
1. **One front door** — a single "Start something new" button in the workspace
   chrome; ⌘K is the accelerant to the same flow (not a parallel door).
2. **Intent-first** — "What do you want to do?", one free-text box, example
   chips for the cold-start/empty state. No name field, no work-type picker.
3. **Light clarify** — one or two short, skippable questions with a stepper.
4. **Confirm-before-start gate** — a summary card + one "Start this work"
   button; "nothing changes until you start."
5. **Starting… / error** — honest progress + plain retry, never a dead end.
6. **Hand-off** — change created → founder lands in the **existing change
   workspace (coaching chat, terminal, stages, files)**, unchanged.

## Honest build flags carried from the design
- Display font (Satoshi / `--font-display`) isn't loaded in the cockpit today —
  headings render in Inter (what the founder actually sees).
- The green "Start" button is AA-large only (3.30:1) — keep the label bold/16px+
  or darken the green at build.

## Artifacts
- `MOCKUP.html` — real-token mockup of states 1–6 (the start flow).
- `JOURNEY.md` — the journey in plain English + Mobbin citations.
- `INSPIRATION.md` — the curated Mobbin reference board.
