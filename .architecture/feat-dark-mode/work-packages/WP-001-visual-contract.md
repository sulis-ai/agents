---
id: WP-001
title: Dark-theme visual contract (founder sign-off gate)
kind: frontend
status: stub                # full WP body produced in the plan-work pass
change: CH-01KTHP
primitive: REINFORCE-Document
group: reinforce
dependsOn: []
estimated_token_cost: "input: ~3k / output: ~2k"
signed_off_at: "2026-06-07T19:10:00Z"
provenance: production-approved
verification:
  na: true
  justification: "Visual contract is a design-time sign-off artifact, not shipped code; its 'test' is founder approval of mockup/dark-theme.html. Implementation WPs that consume it carry concrete Vitest specs."
source: spec:feat-dark-mode#45 / UXD-14
---

# WP-001 (stub) — Dark-theme visual contract

> **This is a stub.** It exists so the visual-contract gate is tracked before
> the full Work Package decomposition (the `plan-work` pass). Do not implement
> from this file — it pins the contract and its sign-off, nothing more.

## Context

TDD §6 (the dark token set) + `mockup/dark-theme.html`. This WP is the
**visual contract** required because dark mode is a user-facing surface
(#45 / UXD-14): the founder signs off on *how it looks* before any
implementation WP touches `tokens.css` or the components.

## The contract (what the founder is approving)

`.architecture/feat-dark-mode/mockup/dark-theme.html` — a real-token,
self-contained mockup rendering the cockpit's actual surfaces (sidebar,
dashboard change-cards with stage badges, thread/chat panel, error/note
banners, and the dark code-viewer panel) using the **exact dark token
values** that will ship. The mockup's `:root[data-theme="dark"]` block is
the canonical source of those values; TDD §6 points here.

The mockup defaults to dark and has a working toggle so the founder can
compare dark ⇄ light side by side. Both states were rendered and visually
verified during blueprint authoring (dark + light full-page captures; the
code viewer correctly follows the theme in both).

## Definition of Done (sign-off, not code)

- [x] **Founder has viewed `mockup/dark-theme.html`** (rendered dark + light
      captures) and approved the dark palette across every surface shown.
- [x] No colour-change requests at sign-off — mockup approved as rendered.
- [x] Sign-off recorded on the change (frontmatter `signed_off_at` +
      `provenance: production-approved`) before the implementation WPs run.

## Downstream (for the plan-work pass — not this WP)

The implementation work this contract gates, to be decomposed next:

1. Add the dark token block to `tokens.css` (`:root[data-theme="dark"]`),
   copied verbatim from the approved mockup.
2. `ThemeProvider` + `useTheme()` + `resolveInitialTheme()` + root
   `data-theme` wiring (ADR-001).
3. `ThemeToggle` in the Shell top bar.
4. Monaco binding: `monacoThemeFor()` in both Monaco wrappers (ADR-002).
5. **Hardcoded-colour remediation** — the 32 non-token colour sites the
   audit found (TDD §2), so acceptance criterion 4 ("no raw hard-coded
   colours that ignore the theme") can pass. The mockup already proposes the
   stage-badge token pairings; this WP-set tokenises the rest.

Each of the above ships its own Vitest spec (all concrete; none deferred).
