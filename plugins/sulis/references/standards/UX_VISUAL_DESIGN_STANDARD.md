# UX & Visual Design Standard

> **Sulis-local v0.1.0 (2026-05-26).** The opinionated doctrine for the
> **visual contract** — the design-time artifact a frontend builds against,
> the way `CONTRACT_FIRST_STANDARD.md` defines the *data* contract. Design is
> agreed **before** the build, like the API is. This standard governs the
> *structure and discipline* of the visual contract; the **brand and visual
> identity values** (the actual look) are **founder-owned** and produced via
> the design flow — see the carve-out below.

<!-- summary -->
A frontend builds against two contracts: the **data** contract (what flows)
and the **visual** contract (what it looks like and how it behaves). This
standard defines the visual contract: **design tokens** as the single source
of visual truth (three tiers), a **visual + interaction spec** (component
variants/states, focus, the three UI states, the structural profile),
**accessibility decided at design time** (WCAG AA), **agentic-interface UX**
for AI surfaces, and **UI voice & tone**. The visual contract is produced at
design time and the frontend WPs depend on it (parallel to contract-first).
The brand/identity values are the founder's call.
<!-- detail -->

## Severity convention

`MUST` — non-negotiable. `SHOULD` — default; deviation needs a rationale.
`MAY` — judgement.

## The model

| | Data contract | Visual contract |
|---|---|---|
| **Standard** | `CONTRACT_FIRST_STANDARD.md` | this one |
| **Defines** | operations + types + errors | tokens + components + interaction + UX patterns |
| **Form** | OpenAPI / JSON Schema | design tokens + a visual/interaction spec ("HIG") |
| **Frontend builds against it** | typed client + mock (WPF-02/03) | tokens + component specs (WPF-06/07) |

Both are **design-time artifacts**; both precede the frontend build; the
frontend conforms to both.

## Relationship to existing standards (reference, don't restate)

- `WP_FRONTEND_STANDARD.md` — **implements** this. WPF-07 (tokens), WPF-06
  (a11y), WPF-12 (agentic UX) build to this contract.
- `CONTRACT_FIRST_STANDARD.md` — the **data**-contract sibling. Same
  "design before build" discipline, different axis.
- `TONE_STANDARD.md` — owns voice/vocabulary; UXD-05 (UI voice) applies it to
  microcopy. Honest-confidence (UXD-04 / AI-07) is the same principle.

## The requirements

### UXD-01 — Design tokens are the single source of visual truth · MUST

All visual values live in **design tokens**, in three tiers: **primitive**
(raw values — never used directly), **semantic** (context-meaningful — what
components use), **component** (component-specific overrides). Components
consume semantic/component tiers; never primitives, never hardcoded
hex/px. Tokens carry **theming** (light/dark) and **pre-validated contrast**.

> **Anti-pattern:** hardcoded colours/spacing in components; a palette that
> lives only in someone's head or a Figma file with no token export.

### UXD-02 — A visual + interaction spec · MUST

A spec (a "HIG" — human interface guidelines) defines, for each component:
**variants, sizes, states** (default/hover/active/disabled/focus), **focus
management** (tab order, trapping, restoration), and the **three UI states**
(loading / empty / error). It also defines the **structural profile**:
navigation pattern, layout (e.g. contained max-width), density, and elevation
strategy (borders vs shadows). The frontend implements to this spec.

> **Anti-pattern:** components designed ad hoc per page; inconsistent focus
> behaviour; no defined loading/empty/error treatment; every screen inventing
> its own spacing.

### UXD-03 — Accessibility is decided at design time (WCAG 2.1 AA) · MUST

WCAG AA is built into the **design**, not retrofitted (retrofitting costs
3–10× more). At design time: token colour pairs meet contrast (**4.5:1** text,
**3:1** large/non-text), information is **never conveyed by colour alone**,
**focus is visible**, interactive elements are **keyboard-operable**, and
components carry **name/role/value**. The frontend then *verifies* this
(WPF-06: jest-axe / Playwright-axe).

> **Anti-pattern:** picking brand colours that fail contrast, then "fixing
> a11y" in code; focus styling stripped for aesthetics; meaning carried only
> by red/green.

### UXD-04 — Agentic-interface UX (for AI surfaces) · MUST for AI features

AI / chat / autonomous surfaces follow seven evidence-based principles:

- **MUST:** **outcome-oriented** (chat coordinates; purpose-built UI delivers
  the work, not a chat transcript); **human-in-the-loop gates** (explicit
  approval before consequential actions; start/pause/stop on autonomous ops);
  **failure recovery** (change approach after repeated failure; acknowledge +
  explain + offer an alternative); **transparency through structure** (source
  attribution, honest-confidence vocabulary, label AI-generated content).
- **SHOULD:** **dual-mode input** (suggestion chips + free text + slash
  commands); **progressive autonomy** (earn trust; confidence indicators);
  **category-organised discovery** (group capabilities by intent, not flat
  lists — for 5+ capabilities).

> **In practice (the cockpit):** chat is the entry point; the dashboard +
> file/diff views do the real work (outcome-oriented); destructive actions
> (nuke, ship) prompt first (human-in-the-loop); honest confidence, no false
> certainty (transparency).
> **Anti-pattern:** the whole product is a chat box; an agent takes a
> consequential action with no confirmation; "I'm absolutely certain."

### UXD-05 — UI voice & tone (content design) · SHOULD

Microcopy is design. Error messages, empty states, and confirmation dialogs
follow **tone-by-severity** (info / warning / error / critical) and the
project's voice (`TONE_STANDARD.md`). Plain, specific, honest — say what
happened and what to do next.

> **Anti-pattern:** `Error: undefined`; jokey copy on a critical failure; a
> blank empty state with no guidance.

### UXD-06 — Responsive + structural consistency · SHOULD

Define the responsive approach (mobile-first, or explicit breakpoints) and the
structural profile **once**, and apply it consistently. Navigation, layout,
and density are decisions made in the contract, not per-screen.

### UXD-07 — The visual contract precedes the frontend build · MUST

Like contract-first for data: the visual contract (tokens + spec + UX
patterns) is a **design-time artifact** the frontend WPs depend on. For
cross-kind work, the visual contract is defined alongside the data contract
during design, and frontend WPs `dependsOn` it.

> **Anti-pattern:** building components first and "extracting a design system
> later"; the design and the build drifting because neither is the source of
> truth.

---

## Founder-owned: brand & visual identity (the carve-out)

This standard governs the **structure and discipline** of the visual contract.
It does **not** prescribe the **brand or visual identity** — the actual colour
palette, typography, logo, imagery, motion, and overall look-and-feel. Those
are **founder-owned product decisions** (brand is a CEO call), produced through
the **design flow** (the `design-system` / `sulis-design` tooling, which emits
the tokens, `DESIGN.md`, and a visual preview), not invented by this standard
or by an executor.

So: this standard says *"you will have semantic tokens with AA-validated
contrast"* (discipline); it does **not** say *"the primary colour is blue"*
(identity). The identity is the conversation to have, and its output *populates*
the token tiers this standard requires.

---

## Tooling (governs vs produces)

This standard **governs**; existing tooling **produces** the artifacts:

- `design-system` skill — generates `DESIGN.md` + a visual preview + token
  exports (CSS/JSON) from a URL or repo.
- `sulis-design` flow — the founder-facing "design the brand / make it look
  right" path.

The standard is the contract; the tools fill it in with the founder's identity.

---

## Provenance

Consolidated from the reviewed design documents (2026-05-26):

- platform `FRONTEND_BEST_PRACTICES.md` — token-based component classes,
  semantic markup, the three UI states (UXD-01/02/05).
- platform `.claude/skills/frontend-development/SKILL.md` — the three-tier
  token system + the HIG/structural-profile references (UXD-01/02).
- platform `accessibility-wcag-aa.md` — WCAG 2.1 AA baseline, enforced at
  design time per DS-02 (UXD-03). Essentials inlined; sourced to W3C WCAG 2.1.
- platform `agentic-interface.md` v1.0.0 — the seven AI-surface principles
  (UXD-04), sourced to NN/g, Microsoft HAX (CHI 2019), Material Design 3,
  LangChain, ACM IUI. Names + severities inlined; cited as the fuller
  treatment.

**Brand/identity values are excluded by design** (the founder-owned carve-out).
External platform standards' essentials are inlined for self-containment.

---

## Version history

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-05-26 | Initial sulis-local definition. The visual contract (sibling to the data contract). 7 requirements (UXD-01..07): tokens, visual/interaction spec, design-time WCAG AA, agentic-interface UX, UI voice, responsive/structural, design-before-build. Brand/visual-identity values explicitly carved out as founder-owned (produced via the design flow). SHOULD-tier items carry 90-day calibration. |
