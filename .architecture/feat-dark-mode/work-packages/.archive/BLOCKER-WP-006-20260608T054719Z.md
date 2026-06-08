# BLOCKER-WP-006: Signed-off mockup covers only 3 of 6 stage badges — specify/implement/review have no dark token pairing

> Created: 2026-06-07T21:38:51Z by sulis-execution executor
> Scope: WP-006
> Step: 1.5
> Trigger: scope-guard

## Failure observation (verbatim)

```
SCOPE-GUARD FIRED AT STEP 1.5 (plan review) — upstream visual-contract gap.

WP-006's contract requires tokenising the dashboard change-card surface so it
re-themes correctly in dark mode. The test it must ship
(tests/no-raw-colours.badges.test.ts, per DoD Red) asserts ZERO raw colour
literals remain across the WHOLE of StageBadge.module.css — and the DoD Blue
asserts light-mode rendered colour is pixel-UNCHANGED (baseline regression).

apps/cockpit/client/src/components/StageBadge.module.css has SIX raw-literal
workflow-stage badges (all six are real, rendered, user-visible — confirmed in
StageBadge.tsx STAGE_CLASS over the WorkflowStage enum):

  .recon     background:#f1f8ff color:var(--primary)  border:#c8e1ff
  .specify   background:#fff5b1 color:#735c0f         border:#ffd33d
  .design    background:#e6e6fa color:#4b0082         border:#c5c5e6
  .implement background:#e1ffe1 color:#22863a         border:#c0e6c0
  .review    background:#fff0e6 color:#c04a00         border:#ffd0b0
  .ship      background:#d4edda color:#155724         border:#a5d6a7

The signed-off visual contract (.architecture/feat-dark-mode/mockup/
dark-theme.html — the founder-approved source of truth per TDD section 6 /
WPF-11) provides dark+light stage-badge token PAIRINGS for ONLY THREE stages:

  --stage-recon-bg/-fg/-bd   (light + dark)
  --stage-design-bg/-fg/-bd  (light + dark)
  --stage-ship-bg/-fg/-bd    (light + dark)

Verified absent from the mockup (grep -niE 'specify|implement|review'
returns no matches, exit 1): NO signed-off dark values exist for
.specify, .implement, .review.

Secondary mismatch in the same contract:
  Token-name suffix: WP context (line 53) prescribes `--stage-recon-border`;
  the signed-off mockup uses `--stage-recon-bd`. The mockup is the value
  source of truth but the WP text names a different suffix — ambiguous which
  the test/CSS should reference.

Why this cannot be self-healed in-scope:
- Route (b) of the TDD section 2 remediation pattern (add a token pair to both
  blocks) requires DARK colour values for specify/implement/review. Those are
  user-observable colour choices on a user-facing surface that MUST clear
  WCAG AA (TDD sections 5.5/6) and MUST be founder-signed (UXD-14 / WPF-11).
  The executor inventing them = authoring unsigned visual-contract values =
  exactly the L-13 failure WPF-11 forbids ("Building a surface against an
  unsigned mockup").
- Route (a) (replace with nearest existing token) changes the LIGHT rendered
  colour for those 3 stages, violating the DoD Blue pixel-unchanged baseline
  assertion the same WP demands.

So the WP Contract (zero raw literals across all 6 stages AND light pixels
unchanged) is unsatisfiable against the current signed-off mockup, which
covers only 3 of the 6 stages the component renders.

```

## Five Whys trace

1. **Why WP-006 cannot be implemented as specified** → its test (no-raw-colours across all of StageBadge.module.css) plus its Blue baseline (light pixels unchanged) cannot both be satisfied for stages specify/implement/review
2. **Why those 3 stages can't be tokenised cleanly** → route (b) needs dark values that don't exist in any signed-off artifact; route (a) changes their light appearance, breaking the unchanged-light baseline
3. **Why no dark values exist for them** → the founder-signed mockup (dark-theme.html) provides stage-badge token pairings for only 3 of the 6 rendered stages — recon, design, ship; specify/implement/review are absent
4. **Why the mockup covers only 3 stages** → WP-001's visual contract / TDD section 6 demoed 3 stage badges as exemplars and never enumerated dark pairings for the full six-stage WorkflowStage enum the component actually renders
5. **Why this is upstream, not fixable here** → the mockup is the founder-signed visual contract (an upstream artifact); authoring the 3 missing dark stage pairings requires WCAG-AA design + founder sign-off (UXD-14 / WPF-11), which is SEA/visual-contract scope, not the executor's — and the executor must not change the light values either

## Root cause

Founder-signed visual contract (mockup/dark-theme.html) provides dark stage-badge token pairings for only recon/design/ship; StageBadge.module.css renders 6 stages — specify/implement/review have no signed-off dark values, and the WP forbids changing their light values.

## Scope verdict

- [ ] in-scope (executor could fix; budget exhausted)
- [x] out-of-scope (scope guard fired)
- [ ] indeterminate (Five Whys non-convergence)

Reason: The mockup is the upstream founder-signed visual contract; authoring the 3 missing dark stage pairings requires WCAG-AA design + founder sign-off (UXD-14 / WPF-11), which is visual-contract / SEA scope, not the executor's. Route (a) reuse-existing-token would change the light appearance the WP requires kept pixel-unchanged.

## Plain-English summary (for the concierge / founder)

The dashboard shows a coloured status pill for each stage of a change: Recon, Specify, Design, Implement, Review, Ship. The approved dark-mode design only picked new dark colours for three of them (Recon, Design, Ship). The other three (Specify, Implement, Review) have no approved dark colour, so this task can't finish them without either inventing colours nobody signed off on, or changing how they look in light mode (which the task explicitly forbids). It needs the approved dark-mode design extended to cover all six stage pills before this can be built.

## Suggested next step

Extend the signed-off visual contract (.architecture/feat-dark-mode/mockup/dark-theme.html) with WCAG-AA dark+light token pairings for the three missing stages — --stage-specify-*, --stage-implement-*, --stage-review-* — get founder sign-off, and reconcile the token-name suffix (WP says -border, mockup uses -bd; pick one). Then re-dispatch WP-006 via /sulis:retry WP-006. (This is a SEA + visual-contract task, not an executor fix.)
