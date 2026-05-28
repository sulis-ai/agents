---
founder_facing: false
status: SPEC — founder-directed (higher priority than #66 release-train)
---
# Spec — make autonomous run-all progress legible + trackable

**Change:** fix · founder-progress-legible
**Closes:** [#69](https://github.com/sulis-ai/agents/issues/69)
**Source:** founder, on reading a multi-hour autonomous run-all: "it's like
reading machine code… if you can't track what's going on, you're putting a
huge amount of faith in a multi-hour process."

## Root cause

The founder-English discipline exists (and `founder-english.md` Anchor case 5
*predicted this exact failure*) but is enforced only at discrete gates
(blocker / protection messages). It never reached the two highest-frequency
surfaces of an autonomous run:
1. The Bash `description` field — `run-all`'s own examples use raw WP IDs
   (`"Ship WP-AJ-FE-07 end-to-end"`), modelling the violation.
2. Per-wave / per-command prose — no instruction to translate, so under
   sustained orchestration the reason-then-translate split collapses.

And structurally: even translated, a 50-message scroll isn't *trackable*.
Trust needs a stable, glanceable frame, not a transcript.

## What this does — 4 layers (1/2/4 in this change; 3 is a follow-on)

**Layer 1 — translate the two leaking surfaces (MUST).** A "Founder progress
discipline" section in `run-all/SKILL.md`: every Bash `description` and every
progress line passes the FE-06 scan. Fix `run-all`'s own example descriptions
(`"Building the sign-up screen"`, not `"Ship WP-AJ-FE-07 end-to-end"`). Raw
command + output stay (unavoidable chrome); the *description* the founder
reads goes plain.

**Layer 2 — a fixed-shape progress frame at each wave boundary (MUST).** Not
per-command. A stable template the founder learns to read:
> *"Building your app — 28 of 54 pieces done (52%). Just finished: the
> sign-up + billing screens. Now building: the device-connection screen + 2
> background pieces. Next: the operator dashboard. Nothing needs you — I'll
> surface anything that does."*
Same frame every wave → the founder tracks the delta, not the mechanism.
Translate WP titles to founder terms; never emit WP/DC IDs or SHAs.

**Layer 4 — flip the autonomous-run default to founder-mode (MUST).** Default
to the frame + translated descriptions; the operator firehose is opt-in via
`--raw` / `/sulis:jargon on`. Wire into the dual-register the agent body
already defines.

**Layer 3 — a living progress view (FOLLOW-ON, out of scope here).** Extend
`/sulis:dashboard` (or a per-change PROGRESS.md `run-all` keeps current) to the
piece level so tracking leaves the chat entirely. Captured as the next slice.

## How we'll know it's done

- `run-all`'s example Bash descriptions + reporting are founder-English (no
  WP/DC IDs, SHAs, rule codes, mechanism narration).
- The skill mandates a wave-boundary progress frame in the fixed shape +
  founder-mode default; `--raw` documented as the opt-out.
- The agent body's execution-mode reinforces "every progress string passes
  FE-06" (it already says this for messages; extend the emphasis to the
  autonomous high-frequency surface).
- Review gate PASS; this change ships through the current flow.

## What to avoid

- Don't try to suppress the raw Bash command/output — that's harness chrome,
  unavoidable (and the founder accepts it). Fix the *description* + the prose.
- Don't bloat into layer 3 here — keep this slice to the prose discipline.
- **Collision note:** `change/create-release-train` (in flight) may also touch
  `run-all/SKILL.md` (the changeset-on-ship area). This change touches the
  *reporting/progress* area — different sections, additive. Whichever merges
  second rebases + keeps both (the #64-vs-#52 pattern).

## References

- `plugins/sulis/skills/run-all/SKILL.md` — dispatch + reporting (the edit)
- `plugins/sulis/references/founder-english.md` — FE-06, FE-09, Anchor case 5
- `plugins/sulis/agents/sulis.md` — execution-mode FE reinforcement
- #69 (closes), #66 (sibling release-train, lower priority)
