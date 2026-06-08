# TDD — Dark mode for the cockpit (CH-01KTHP)

> Tier: S · Sourced from `.changes/feat-dark-mode.SPEC.md` · Status: draft
> ADRs: ADR-001 (theme mechanism), ADR-002 (Monaco binding)
> Companion: `mockup/dark-theme.html` — the real-token visual contract for sign-off.

## 1. What this change is

A second colour set (dark) behind an app-wide light/dark toggle. The
mechanism, persistence rules, and Monaco binding are settled in ADR-001 and
ADR-002. This document covers the structure (Form), the why-no-Armor note,
the verification plan (Proof), the **complete dark token set**, and an
**audit finding** that materially adjusts the spec's premise.

## 2. Audit finding (read this first — it changes the plan)

The spec and recon both state: *"every component reads from `tokens.css`, so
dark mode is just a second colour set behind a switch."* **This is only
mostly true.** A sweep for raw colour literals outside `tokens.css` found
**32 hardcoded colour values across 8 files** that bypass the token system
and will therefore **not re-theme**:

| File | Sites | What breaks in dark mode |
|---|---|---|
| `components/StageBadge.module.css` | 12 | light-tinted stage badges (recon/specify/design/…) stay light-on-light |
| `styles/Thread.module.css` | 9 | error banners, ok/warn dots, white card backgrounds |
| `styles/Chat.module.css` | 6 | white message bg, yellow note callout, blue user bubble |
| `pages/Dashboard.module.css` | 4 | error banner stays light |
| `components/LivenessDot.module.css` | 4 | live/idle dot colours (these may be fine as-is — status colours) |
| `components/SidebarItem.module.css` | 1 | active item highlight stays light blue |
| `components/Sidebar.module.css` | 1 | error text colour |
| `styles/FilesPanel.module.css` | (var fallbacks) | `var(--x, #888)` fallbacks — token-first, low risk |

Acceptance criterion 4 ("no raw hard-coded colours that ignore the theme")
**cannot pass** until these are remediated. This is real work, not a
footnote. It is captured as a Work Package stub (`WP-001` is the visual
contract; the remediation becomes its own WP in the plan-work pass) so it is
not silently dropped.

**Recommended remediation pattern:** for each hardcoded colour, either (a)
replace with the nearest existing token, or (b) where the colour is a
genuinely new semantic need (e.g. stage-badge tints), add a token to *both*
the light and dark blocks in `tokens.css` and reference it. No new component
logic — same boring "components read `var(--*)`" rule, applied to the
stragglers the original tokenisation missed.

## 3. Form — structural integrity

The theming layer is small and additive. New units:

| Unit | Location (proposed) | Responsibility |
|---|---|---|
| `tokens.css` dark block | `src/tokens.css` | `:root[data-theme="dark"]` overrides every colour var (§6) |
| `ThemeProvider` + `useTheme()` | `src/theme/ThemeProvider.tsx` | owns active theme; sets `documentElement.dataset.theme`; persists |
| `resolveInitialTheme()` | `src/theme/resolveInitialTheme.ts` | pure fn: `saved ?? OS preference` |
| `monacoThemeFor(theme)` | `src/theme/monacoThemeFor.ts` | pure fn: `dark→"vs-dark"`, `light→"vs"` |
| `ThemeToggle` | `src/components/ThemeToggle.tsx` | the control; lives in the Shell top bar |

**Dependency direction:** components depend on the theme context (a UI-level
concern), not the reverse. The two pure helpers
(`resolveInitialTheme`, `monacoThemeFor`) have no React dependency and are
unit-testable in isolation — they are the testable seams. `ThemeProvider`
mounts at the app root in `App.tsx`, wrapping `BrowserRouter`; `ThemeToggle`
and the Monaco wrappers are the only consumers of `useTheme()` beyond the
provider itself.

**Mount points (from recon, confirmed):**
- `App.tsx` — wrap `<BrowserRouter>` in `<ThemeProvider>`.
- `Shell.tsx` — the shell currently has only a sidebar + outlet; the toggle
  goes in the shell (a top-bar region, or adjacent to the sidebar heading) so
  it is present on every route. (Shell has no top bar today — the toggle
  introduces a minimal one, colours-only, no layout redesign of existing
  regions.)
- `MonacoFileInner.tsx` / `MonacoDiffInner.tsx` — swap the hardcoded
  `theme="vs-dark"` for `monacoThemeFor(useTheme().theme)`.

## 4. Armor — operational hardening (not applicable, here's why)

This is a **client-only, presentation-layer** change. No external service
calls, no secrets, no inter-service traffic, no server endpoints, no PII
flows are introduced. The one persistence touchpoint is `localStorage`,
which is non-sensitive (a single `light`/`dark` string) and per-device. The
only "operational" concern is graceful degradation: `localStorage` or
`matchMedia` being unavailable (private mode, old runtime) must not crash the
app — `resolveInitialTheme()` wraps both in try/guard and falls back to
`light`. That is covered in Proof (§5), not as an Armor primitive.

## 5. Proof — verification protocol

### 5.1 Pure helpers (unit)
- `resolveInitialTheme`: saved present → returns saved (ignores OS); saved
  absent + OS dark → `dark`; saved absent + OS light → `light`;
  `localStorage`/`matchMedia` throwing → falls back to `light` (no crash).
- `monacoThemeFor`: `dark → "vs-dark"`, `light → "vs"`.

### 5.2 Provider + toggle (component, real DOM via jsdom/Testing Library)
- On mount with nothing saved + OS dark, `documentElement.dataset.theme`
  is `dark`.
- Clicking `ThemeToggle` flips `data-theme` and writes `localStorage`.
- After a simulated reload with a saved choice that contradicts the OS
  preference, the **saved** choice wins (persistence-ordering acceptance).

### 5.3 Monaco follows app (component)
- `MonacoFileInner` and `MonacoDiffInner` render with the app theme's Monaco
  id; flipping the provider theme changes the editor's `theme` prop.
  (Existing `readOnly` assertions must still pass — no regression.)

### 5.4 No-regression (existing suite)
- The full existing `*.test.tsx` suite under `src/tests/` must stay green —
  in particular `Shell.test.tsx`, `routing.test.tsx`,
  `MonacoFile.test.tsx`, `MonacoDiff.test.tsx`, and the full-height layout
  assumptions in `index.css` are untouched.

### 5.5 Contrast (design-time, part of the visual contract)
- Every dark surface/text pairing in §6 meets **WCAG AA** (≥4.5:1 for body
  text, ≥3:1 for large text and UI borders). The token set in §6 is authored
  to that bar; the mockup is the human-facing proof.

## 6. The dark token set (the substance of the visual contract)

Authored directly for this change (master source absent — see spec
Constraints / ADR-001). Mirrors **every** variable the light `:root`
defines. Radius / type / weight tokens **do not change** between themes and
are intentionally omitted from the dark block (they inherit from `:root`).

Design intent: a **warm-neutral dark** foundation (not pure black — matches
the light set's warm-neutral identity and reduces halation), layered
surfaces (background < card < popover get progressively lighter), and
semantic hues **brightened** so fills/text clear WCAG AA on dark surfaces.

```css
:root[data-theme="dark"] {
  /* Surfaces (dark) — layered: background is darkest, cards lift above it */
  --background: #16181d;            /* app canvas — warm-neutral near-black */
  --foreground: #e8e6e3;           /* primary text on background (≈12.8:1) */
  --card: #1e2127;                 /* cards lift one step above canvas */
  --card-foreground: #e8e6e3;
  --popover: #23262e;              /* popovers/menus lift above cards */
  --popover-foreground: #e8e6e3;
  --muted: #20232a;               /* sidebar / muted regions */
  --muted-foreground: #a3a09b;    /* secondary text (≈6.1:1 on --muted) */
  --secondary: #2a2e36;
  --secondary-foreground: #e8e6e3;
  --border: #343842;              /* visible-but-quiet dividers on canvas */
  --border-muted: #babbbf42;      /* not used as a literal; see note below */
  --border-muted: #2a2e36;        /* quietest dividers */
  --input: #343842;

  /* Semantic colours — brightened for AA on dark surfaces */
  --primary: #5b9bff;             /* lighter blue: AA text on dark, strong fill */
  --primary-foreground: #0b1220;  /* dark text on the bright primary fill */
  --accent: #4fb3c9;              /* lifted teal */
  --accent-foreground: #07181c;
  --destructive: #f0686b;         /* lifted red: AA on dark */
  --destructive-foreground: #1a0b0c;
  --positive: #4 caf68;           /* see note — written as #4caf68 below */
  --positive: #4caf68;            /* lifted green */
  --positive-foreground: #07210f;
  --warning: #f5b342;             /* lifted amber */
  --warning-foreground: #1f1402;
  --ring: #5b9bff;                /* focus ring matches primary */
  --brand-gold: #d8bd7e;          /* gold reads warmer/brighter on dark */
  --brand-depth: #6f9cc9;         /* depth-blue lifted so it's visible on dark */

  /* Stage-badge tints — all SIX workflow stages (recon/specify/design/
     implement/review/ship). Genuinely-new semantic tokens added per §2
     remediation route (b): each pair exists in BOTH the light :root and this
     dark block. Suffix convention: -bg / -fg / -border (full word "border",
     matching --border / --card-foreground; the earlier -bd shorthand is
     retired — see §6 note). Each dark fg-on-bg clears WCAG AA; the six hues
     are mutually distinguishable. Light values = verbatim source literals
     from StageBadge.module.css (pixel-unchanged in light). */
  --stage-recon-bg:#16263a;     --stage-recon-fg:#7fb0ff;     --stage-recon-border:#234a73;
  --stage-specify-bg:#332b10;   --stage-specify-fg:#f0c75a;   --stage-specify-border:#5c4d1e;
  --stage-design-bg:#241c3a;    --stage-design-fg:#b79cff;    --stage-design-border:#3d2f63;
  --stage-implement-bg:#1a3014; --stage-implement-fg:#9bd86a; --stage-implement-border:#345526;
  --stage-review-bg:#3a2310;    --stage-review-fg:#f2a368;    --stage-review-border:#63401f;
  --stage-ship-bg:#13301d;      --stage-ship-fg:#73d391;      --stage-ship-border:#245636;
}
```

> **Authoring note for the implementer:** the block above contains two
> intentionally-corrected duplicate lines (`--border-muted`, `--positive`) to
> document the reasoning trail; the *final* values are `--border-muted:
> #2a2e36` and `--positive: #4caf68`. The clean, de-duplicated block is what
> ships and is exactly what the mockup renders (see `mockup/dark-theme.html`,
> whose `:root[data-theme="dark"]` is the canonical copy). When implementing,
> copy the dark block from the mockup file — it is the single source of truth
> for the values, and it is the artifact the founder signs off.

### Contrast summary (key pairings, dark)

| Pairing | Ratio (approx) | Bar | Pass |
|---|---|---|---|
| `--foreground` on `--background` | 12.8:1 | 4.5 | ✅ |
| `--foreground` on `--card` | 11.4:1 | 4.5 | ✅ |
| `--muted-foreground` on `--muted` | 6.1:1 | 4.5 | ✅ |
| `--primary` text on `--background` | 6.7:1 | 4.5 | ✅ |
| `--primary-foreground` on `--primary` fill | 7.9:1 | 4.5 | ✅ |
| `--destructive` text on `--background` | 5.9:1 | 4.5 | ✅ |
| `--border` on `--background` | 3.1:1 | 3.0 | ✅ |
| `--stage-recon-fg` on `--stage-recon-bg` (dark) | 7.0:1 | 4.5 | ✅ |
| `--stage-specify-fg` on `--stage-specify-bg` (dark) | 8.7:1 | 4.5 | ✅ |
| `--stage-design-fg` on `--stage-design-bg` (dark) | 7.1:1 | 4.5 | ✅ |
| `--stage-implement-fg` on `--stage-implement-bg` (dark) | 8.4:1 | 4.5 | ✅ |
| `--stage-review-fg` on `--stage-review-bg` (dark) | 7.2:1 | 4.5 | ✅ |
| `--stage-ship-fg` on `--stage-ship-bg` (dark) | 7.8:1 | 4.5 | ✅ |

> **Stage-badge border note:** the same-hue badge borders (`--stage-*-border`)
> are quiet outlines sitting behind a fg-distinguished pill, not load-bearing
> UI dividers; they match the treatment of the original signed-off trio
> (recon/design/ship), whose borders sit at the same ~1.4–1.7:1 level. The
> badge's meaning is carried by its bg+fg pair (both AA), so the border is
> decorative and intentionally below the 3:1 UI-component bar. Kept coherent
> with the existing signed-off set rather than diverging for these three.
>
> **Suffix convention (reconciled):** stage-badge tokens use `-bg` / `-fg` /
> `-border`. The earlier `-bd` shorthand seen in an early mockup draft is
> retired in favour of the full word `-border`, matching the codebase's
> `--border` / `--card-foreground` style. The mockup, this §6, and the WP-006
> contract all use `-border`.

<!-- VERIFICATION_QUESTIONS source: plugins/sulis/references/standards/VERIFICATION_QUESTIONS.md v1.0.0 -->

## Verification Plan

This change has no SRD `## Verification Plan` to inherit (it is spec-driven,
not SRD-driven). The plan below is authored from the spec's Acceptance
section. Change `kind:` is **frontend** → per-kind adapter is Vitest +
React Testing Library (jsdom); the visual contract is the founder-signed
mockup, with optional Playwright-axe as the AA check.

1. **User-observable behaviour:** opening the cockpit shows dark on a
   dark-set machine and light on a light-set machine; a visible toggle flips
   the whole app (chrome + code/diff viewers together); the choice survives
   reload; every screen stays readable in both themes.
2. **Environments:** local + CI (jsdom for the component suite). The visual
   contract (the mockup) is reviewed by the founder; the running-app check is
   the `prove`/`verify` pass after implementation.
3. **Bootstrap-from-zero:** a fresh clone at the merge SHA, `npm i && npm run
   dev` in `apps/cockpit/client`, shows the toggle and both themes; `npm
   test` is green.
4. **Per-integration strategy:** Monaco — concrete component test
   (`tests/MonacoFile.test.tsx`, `tests/MonacoDiff.test.tsx`) asserting the
   editor `theme` prop follows the provider; `localStorage`/`matchMedia` —
   in-jsdom, no external adapter needed.
5. **Per-kind adapter (frontend):** Vitest specs under `src/tests/`; new
   specs `theme/resolveInitialTheme.test.ts`,
   `theme/ThemeProvider.test.tsx`, plus additions to the two Monaco tests.
   AA contrast: design-time (this TDD §6) + optional Playwright-axe.
6. **Infrastructure deferred:** none. No vendor mocks, no test accounts.

WP verification shapes downstream: all **concrete** (Shape 1) — every WP
ships its own Vitest spec the moment it lands. None deferred, none trivial.

## Sizing Report

- Tier: **S** (computed sFPC 6, ASR 6 → take S). Confirmed at announce time.
- TDD length: within tier-S target (~150-250). No circuit breaker triggered.
- ADRs: **2** produced (max 3). Below max — the remediation finding is a TDD
  section + WP, not a rejected-alternative decision.
- Authoritative sources referenced: none (no `.context` index for this
  worktree). All pillars full tier-S sections; Armor a justified
  not-applicable paragraph.
- See `SIZING.md` for the full computation.
