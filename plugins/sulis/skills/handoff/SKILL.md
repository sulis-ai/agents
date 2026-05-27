---
name: handoff
description: "Records the hand-off note when passing you to a specialist."
user_invocable: true
---

# /sulis:handoff — Specialist Handoff

When invoked, the concierge is about to hand off to a specialist agent
(via a recommended slash command). This skill writes the handoff context
note to `.sulis/{project}/JOURNEY.md` and to a dedicated handoff
file the specialist can read.

## Workflow

1. **Identify the specialist being invoked.** Required input: the slash
   command being recommended (e.g. `claude --agent requirements-analyst`, `/sulis:draft-architecture`,
   `/sulis:codebase-assess`).
2. **Write a handoff context file** at
   `.sulis/{project}/handoffs/HANDOFF-{NN}-to-{specialist}.md` with:

   ```markdown
   # Handoff #{NN} — Concierge → {specialist}

   > Created: {ISO-8601}
   > Founder audience score: Novice (default) | Intermediate | Experienced
   > Concierge journey phase at handoff: {phase number — plain-English label}

   ## Goal
   {plain-English statement of what the founder is building, from JOURNEY.md}

   ## What exists
   {brief list of artifacts already produced, with paths}

   ## What the specialist should produce
   {expected output artifacts at expected paths}

   ## Founder non-technical context (MUST)
   The founder is non-technical by default. Apply Novice audience score
   (per AAF-04). Translate output into plain English. The concierge will
   re-translate on return — but specialists should still apply AAF-01..AAF-09
   internally rather than relying on the concierge filter.

   ## Decisions already captured
   {decisions from JOURNEY.md ## Decisions section}
   ```

3. **Update JOURNEY.md** with:
   - New entry in `## Phase History` showing the handoff timestamp +
     specialist name.
   - `## Next Action` updated to "Founder is running `/{specialist:command}`;
     returning here when complete."

4. **Surface the handoff to the founder in plain English** (action-then-
   report shape, AAF-08 compliant):

   > *"Now [plain-English description of what the specialist does].
   > Run this command when you're ready:*
   >
   > *`/{specialist:command}`*
   >
   > *I've written a context note for them so they know who they're
   > talking to. When they're done, come back here and I'll read what
   > they produced and continue."*

## When to use

- Phase 2 → 3 transition (handoff to SRD analyst).
- Phase 3 → 4 transition (handoff to SEA blueprint).
- Phase 4 → 5 transition (handoff to executor).
- Phase 5 → 6 transition (handoff to SEA verify).
- Phase 6 → 7 transition (handoff to sulis-security).
- Branch routes in Phase 1 (handoff to IDC / sulis-design / sulis-strategy).

## Composition

- Handoff context files persist across sessions; specialists can read
  them via the standard "look for `.sulis/{project}/handoffs/` if it
  exists" pattern.
- Specialists that have been updated (post-v1.12.0) check for handoff
  context files at session start and apply the audience score they find.
- v0.2 (next commit) will allow handoffs to spawn the specialist
  directly via Agent tool rather than requiring the founder to type the
  slash command.
