---
founder_facing: false
status: BUILT (conversions + heuristic) + SCOPED (gate spike) — closes #71's mechanical part
---
# Spec — decide, don't interrogate the founder on engineering-internal calls

**Change:** fix · decide-dont-interrogate
**Closes:** [#71](https://github.com/sulis-ai/agents/issues/71) (mechanical part)
**Source:** founder, after Sulis asked engineering-internal questions four
times in one session — "how would a non-technical founder know?"

## What this change does (built)

The mechanical sweep result: two skills *hardcoded* a founder confirmation of
a deterministically-computed engineering quantity. Both converted to
**decide-and-report**:

1. **`/sulis:specify` Step 3** — was *"echo the proposal, let the founder
   confirm or override … 'Sound right?'"* + *"never run a mode without the
   founder's confirmation."* Now: the agent decides the classified depth,
   announces it in one plain sentence, runs it; the founder can redirect
   after. Only a *deep* spec (a ~20-min session) gets a one-line non-blocking
   heads-up (real time cost). Conclusion + Gotchas reframed to match.
2. **`/sulis:draft-architecture` step 3** — was *"Proceed, override the tier,
   or stop? Wait for the user response"* with raw sFPC/ASR put to the founder.
   Now: write the sFPC/ASR breakdown into `SIZING.md` (artifact + `--raw`
   carry the numbers); announce only what the tier *means* (build size) in
   plain English; proceed; founder can redirect the size after.
3. **Agent body — the HOW-vs-WHAT test (MUST).** A one-line guard before any
   founder question: *is this about how it's built (yours → decide + report)
   or what the product is (theirs → ask)?* The prose lever for the
   *improvised* asks (operator-split, version-bump-location).

Untouched (correctly founder-owned): ship / nuke / scope / risk confirmations.

## What this change scopes (NOT built — the gate spike, the structural fix)

The HOW-vs-WHAT heuristic is prose, and prose degrades under the same load
that's eroding the judgment now. The durable backstop is a **headless-Claude
founder-question gate**, scoped here for a follow-on spike:

- **Mechanism:** a Claude Code `Stop` hook. On each turn whose audience is the
  founder, it pipes the turn's founder-facing output to a fast headless
  `claude -p` with a single-purpose gate prompt: *"Does this ask the founder
  an engineering-internal (HOW) question, or use un-translated jargon?"* On a
  hit it returns `{"decision":"block","reason":"…"}` → the agent must
  decide-and-report / re-translate **before the founder sees it**. A
  `PreToolUse` hook on `AskUserQuestion` is a cheaper complement for
  structured questions.
- **Why it works where prose doesn't:** a separate, fresh, single-purpose
  check doesn't degrade under the main agent's load. And the `Stop` hook sees
  **free-text** output — which is what the improvised over-asks actually were
  (not `AskUserQuestion` calls).
- **Spike deliverables:** the hook script + the gate prompt + a measurement
  run (latency + token cost per founder-facing turn). **Validate before
  adopting.** Scope the hook to founder-mode + turns that address the founder
  (most autonomous turns are pure tool calls), and use Haiku for the gate, to
  bound cost.
- **Honest caveat:** real per-turn overhead; needs the measurement to justify
  default-on. Carried as the #71 structural follow-on, not shipped blind.

## How we'll know it's done (this change)

- specify + draft-architecture no longer block on a computed-quantity confirm;
  both announce + proceed; redirect-after documented.
- The agent body carries the HOW-vs-WHAT test (MUST).
- Review gate PASS. The gate spike is a separate, measured change.

## References

- `plugins/sulis/skills/specify/SKILL.md`, `…/draft-architecture/SKILL.md`
- `plugins/sulis/agents/sulis.md` — Inference Over Interrogation (FE-11)
- `plugins/sulis/references/founder-english.md` — FE-06/FE-09, Anchor case 5
- #71 (closes mechanical part), #69 (sibling: progress-legibility)
