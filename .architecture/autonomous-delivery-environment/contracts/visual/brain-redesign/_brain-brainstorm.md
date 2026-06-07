# Brain view — three review directions

Review mockups (UNSIGNED). The founder compares these, picks one, then we
refine the chosen direction and run the #45 sign-off gate. All three render
inside the signed `chat-B2-tabbed-workspace` shell (top tab strip + the
change's left nav with **Brain** selected, full-width main), bound strictly to
the signed design instance (`apps/cockpit/client/src/tokens.css`): every colour
is a `var(--*)`, fonts loaded as the signed contract, Heroicons throughout,
stage palette tinting per entity-kind. UXD-15 (structure explored, identity
fixed). Cognitive load honoured (`cognitive-load.md`).

The question all three answer: **"what did the agent do, and can I trust it?"**
They differ in the *lens* they lead with.

## Realistic data (shared, from this change)
- 2 autonomous runs — Specify pass, Verify pass; both completed; ~88% confident.
- 49 requirements (must/should). 1 verified by a test; 48 awaiting verification.
- 13 scenarios · 2 designs · 4 decisions (incl. "Use short-lived tokens", "Store
  an audit trail") · 2 opportunities · 28 steps · 1 test run · 1 test result
  (outcome: **skip** — needs a sandbox key).
- Edges shown: requirement ←derived-from← opportunity · design →satisfies→
  requirements · design →references→ decisions · scenario →verifies→ requirements
  / →exercises→ design · testresult →of-run→ testrun, →verifies→ requirements.
- The trust signal in every direction: **"Test coverage is thin on the payments
  path"** + the agent's own self-critique ("a skipped test is not a passing test").

---

## A · The Run Log — `brain-A-run-log.html`
**Lens: execution trace.** Summary banner (did / covered / decided / flagged) +
a [Run log] / [Coverage map] toggle, then a vertical timeline of the agent's
runs. Each run is a card with a **worded** outcome + a **worded** confidence
chip; expand a run to its ordered steps; click a step to fill the right detail
rail — what it produced, the gap it flagged, its self-critique.
- **Strength:** answers "can I trust it?" most directly — the trace and the
  self-critique are front and centre; reads like reviewing someone's working.
- **Cost:** assumes the founder thinks in *runs/steps*; less good at "is every
  requirement covered?" (that's a derived count, not the spine).
- **CL:** one lens at a time; steps are progressive disclosure; ≤5 banner items.

## B · The Coverage Map — `brain-B-coverage-map.html`
**Lens: traceability.** Four columns — Why → What → How → Tested — each with a
live count pill. The requirements column is the one searchable list. Clicking a
requirement draws a **single focused trace** beneath the columns (that one
requirement + labelled edges to its reason / design+decision / test) — one thing
in focus, never an all-edges node-blob.
- **Strength:** answers "is everything reasoned, designed and tested?" at a
  glance; the 1-of-49 gap is unmissable; the labelled focused trace is the
  honest, low-load alternative to a graph.
- **Cost:** denser; the four-column model is a small thing to learn; more a
  *completeness auditor* than a *narrative*.
- **CL:** explicit labelled edges (not a tangle); search scopes the only long
  list; worded status chips, never colour-alone. (Recon/specify count-pill inks
  darkened to clear WCAG AA as text — see a11y note below.)

## C · Summary-first dashboard — `brain-C-summary-dashboard.html`
**Lens: digest, then doors.** Opens on four plain-English tiles (what it did ·
covered · decided · flagged — the flagged tile carries the gap + self-critique),
then two door-buttons (**See the run log** / **See the coverage map** = A and B)
and a quiet "Browse everything (119 items)" link. Also shows the **empty**
("no brain yet") and **loading** looks.
- **Strength:** lowest cognitive load; a non-technical founder gets the whole
  trust picture in ~10 seconds and chooses how deep to go. A and B become its
  two depths rather than competing front doors.
- **Cost:** one extra click to reach detail; on its own it's a summary, not a
  workspace — it *needs* A and/or B behind it.
- **CL:** strongest fit — recognition layer up front, recall behind doors; the
  two doors are the only primary actions; browse is subordinate.

---

## Recommendation

**Ship C as the Brain's front door, with A and B as its two doors —
build B next, A after.**

Rationale: the founder's job-to-be-done is *trust without reading code*, and the
summary-first dashboard delivers that in seconds while keeping the depth one
click away. It also resolves the A-vs-B tension: they aren't rival layouts, they
are the two ways to go deeper (the narrative lens and the completeness lens), so
C lets us keep both without forcing a single front door to do two jobs. Of the
two depths, **B (Coverage Map)** earns priority because the 1-of-49 coverage gap
is the single most important trust fact this change surfaces, and B makes it
impossible to miss; **A (Run Log)** is the natural follow-on for founders who
want to walk the agent's working.

If the founder wants a single screen and no doors, **B** is the stronger
standalone (completeness auditing beats narrative for the trust question); **A**
is the pick if they value the run-by-run narrative and self-critique most.

## a11y note (carried into whichever direction is chosen)
- Load-bearing text pairs clear WCAG AA (4.5:1+): accent-ink on accent tint
  5.88, attn-icon on amber 4.84, stage-ship on positive 4.79, white on primary
  5.17; body text 17.9, secondary text 7.8 on white card.
- Status is **worded** everywhere (Completed / Awaiting test / Tested / Not run /
  skipped), never colour-alone (WCAG 1.4.1).
- `#EDEAE3` (matte behind the frame) and `#fff` (only inside `color-mix()`
  anchors) are carried verbatim from the signed B2 shell — not product surfaces.
- AA-internal ink shades (`--accent-ink`, and in B `--recon-ink` / `--specify-ink`)
  are defined in `:root`, same hue family as their base stage tokens, darkened
  only enough to clear AA *as text*; fills/borders unchanged. Flagged **pending
  token regen** — these become named semantic tokens when the design instance
  next regenerates.

*Unsigned — no contract sign-off yet.*
