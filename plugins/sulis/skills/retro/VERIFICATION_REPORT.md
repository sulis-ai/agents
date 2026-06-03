# VERIFICATION_REPORT — retro (add-skill v0.7.0, greenfield)

**Verdict: PASS.** Tier: STANDARD + founder-facing. Audience: founder-facing. Category: Founder Aggregator.

## Gate 1 — Find
- **Prior art (5+ checked):** `capture-lessons` (change-grain — issues+digest at ship), `resolve-lessons` (drains the backlog), `feedback` (OSS feedback), `review`/`code-review` (quality of a change). **None are session-grain** (a whole session, spanning changes, capturing friction/steers/missing-context). CC verdict: **VALIDATED**.
- **Could a reference cover it?** No — new workflow.
- **Primitives (5, fan-out ≤7, depth 1):** extract-steers · framework-friction · missing-context · open-probe · route. Independent + falsifiable; provenance = extracted from this project's own session-friction patterns + the founder's voice-note design.

## Gate 2 — Scope Lock
name `retro` · plugin `sulis` · audience **founder-facing** · category **Founder Aggregator** · trigger = the `description:` verbatim · standards: input REFERENTIAL_INTEGRITY, processing CRITICAL_THINKING (BI/AT for the steer-mine + self-attack), output CRITICAL_THINKING (SCQA/Pyramid) + TONE + COACHING + founder-facing-conventions · tier STANDARD · **tool stack: N/A — reflective/aggregator skill, not audit-pattern** (no Semgrep-class tools; its "tools" are TaskCreate + gh issues + capture-lessons + the idea-backlog — all real routing destinations) · related: capture-lessons/resolve-lessons/feedback · single mode.

## Gate 3 — Generate
`plugins/sulis/skills/retro/SKILL.md` parses (valid YAML frontmatter). Pyramid: leads with `## Conclusion`. `## When to invoke` + `## When NOT to invoke` are MECE (end-of-session vs mid-session/change-grain/feedback/status). `## Gotchas` (7, ≤ PD-02 fan-out, likelihood×impact ordered). Linguistic audit: zero prohibited terms. `## Vocabulary` present (5 terms). Per-section `> Standards:` headers on the operational acts. Progressive disclosure: points to capture-lessons/watchlist/standards, doesn't restate.

## Gate 4 — Evaluate (STANDARD)
| Dimension | Score | Threshold | Pass |
|---|---|---|---|
| ACCA | 5/5 | 3 | ✓ |
| Evidence grounding | 4/5 | 3 | ✓ |
| Structural coherence (Conclusion→acts→routing→gotchas) | 5/5 | 3 | ✓ |
| Honest uncertainty | 4/5 | 3 | ✓ |
| Codebase Referential Integrity | 5/5 | 5 | ✓ |

**Referential Integrity:** all cited entities resolve — `capture-lessons`, `resolve-lessons`, `feedback` (skills on disk); the watchlist `gh ... label:watching` (documented in agents/sulis.md); COACHING/TONE/founder-facing-conventions (on disk); `TaskCreate` (harness tool). The **`Lesson` entity is flagged NEW/not-yet-minted** — the brain-context route writes to the idea-backlog until then (explicitly flagged, not a hallucination).

## Gate 5 — Adversarial Review
- **Journaling-not-routing — PREVENTED.** The Conclusion + the routing table make disposition mandatory; "a finding with no disposition is lost" is gotcha #1.
- **MUC-F1 operator-jargon leak — PREVENTED.** Output is founder-facing; FE-06 cited; gotcha #3.
- **MUC-F4 number-of-items overwhelm — PREVENTED.** Gotcha #6: lead with the routed summary (counts per disposition), not a wall.
- **MUC-F5 source-of-truth false-positive — PREVENTED.** Findings route to real stores (tasks/issues/backlog); the brain-context slot writes to a real backlog until `Lesson` exists (gotcha #7), never a void.
- **Self-congratulation drift — PREVENTED.** Gotcha #2 + the discipline header keep "got right" short+factual.
- **Speculative findings — PREVENTED.** Act 1 (steers) is objective (user-said); gotcha #5 bans invented friction.
- **OPEN_RISK: brain-context findings sit in the backlog unread until the `Lesson` entity is minted** — they're captured (not lost) but not yet agent-loadable at decision-time. *revisit_by:* the `Lesson` mint (queued task). Acceptable: captured > lost; the upgrade is tracked.

≥3 MUC-F addressed (F1/F4/F5) + the audience-agnostic categories. All PREVENTED or OPEN_RISK with revisit-trigger.
