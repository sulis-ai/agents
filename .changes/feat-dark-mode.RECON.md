# Recon — feat-dark-mode

Stage 0 completed at: 2026-06-07T18:44:07Z

This marker file's existence indicates that `/sulis:recon` has been run
for this change. The spawned Sulis's stage-inference uses this file to
distinguish "post-recon" from "pre-spawn stub only".

## What's already here (recon findings)

- **Cockpit UI**: `apps/cockpit/client` — React + Vite + CSS Modules.
- **Design tokens already exist**: `client/src/tokens.css` — a `:root`
  block of flat CSS custom properties (light surfaces only). Components
  reference `var(--*)` only, never raw hex. This is the foundation a
  dark set drops into: override the same vars under a theme selector.
- **The "jar" already exists today**: Monaco is hardcoded `theme="vs-dark"`
  in BOTH `MonacoFileInner.tsx` and `MonacoDiffInner.tsx` — dark code in
  a light app right now. The toggle must make Monaco follow the active theme.
- **No theme state / toggle exists yet** — only the two Monaco hardcodes
  reference "theme". Work to add: dark token set, theme state/provider,
  toggle control (likely in `layouts/Shell.tsx` top bar), Monaco following.
- **Token source note**: tokens.css says "regenerate from the design
  instance"; the referenced `studios/product/design/DESIGN_TOKENS.json`
  is NOT present in this worktree — dark tokens likely hand-authored or
  the instance located first. (design-source question, not a blocker)
- **Arrival check**: `main` does not require branch-ci (advisory CI on
  this repo). Affects the ship gate later, not this work.

See `plugins/sulis/agents/sulis.md` "Change context" for stage-inference.
