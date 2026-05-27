# Brand Proposal Standard

<!-- summary -->

This standard governs the case where a founder has no existing brand —
no URL, no style guide, no logo, no design system — and the
`/investor-coach:brand-discovery` skill must propose a basic brand kit so the deck
and financial dashboard can be produced.

Ten rules (BP-01 through BP-10) translate the ambiguous brief
"professional, modern, crisp" into falsifiable, verifiable constraints
on palette, typography, spacing, contrast, and logo treatment. The
proposed kit is always founder-approved before adoption; this standard
prevents the plugin from silently inventing visual identity.

The standard rests on three commitments:

1. **Falsifiable adjectives.** "Professional", "modern", and "crisp" are
   defined as a set of measurable constraints (palette saturation,
   typeface category, spacing unit ratios) — not aesthetic taste.
2. **No bundled fonts.** Per founder direction, the proposal uses only
   system-stack typefaces or fonts the founder supplies. The plugin
   does not ship custom fonts.
3. **Founder approves.** The proposal is presented, justified, and
   confirmed before `BRAND.md` is written `page-build-ready: true`. The
   founder can iterate before adoption.

A proposed brand kit satisfies the standard when all MUST rules pass and
the founder has signed off in writing (an explicit "approved" entry in
`EXPLORATION_JOURNAL.md`).

<!-- detail -->

> **Version:** 1.0.0
> **Status:** Active

---

## Provenance

This standard synthesises:

- Brand Identity Standard (`brand-standard.md`, BR-NN) — the upstream
  extraction format
- Visual Design Standard (`visual-design-standard.md`, VD-NN) — what
  proposed tokens must enable
- WCAG 2.2 AA contrast requirements
- Practitioner knowledge from design systems work and founder feedback
  on auto-generated identity

This is practitioner knowledge consolidated from design-systems
methodology and accessibility standards. The accessibility minimums are
peer-reviewed.

---

## Severity Convention

| Severity | Meaning |
|---|---|
| **MUST** | Non-negotiable. A proposal that violates this is rejected. |
| **SHOULD** | Default. Deviation requires explicit founder justification. |
| **MAY** | Permitted option. Use judgement. |

---

## Section 1: When the Proposal Applies

### BP-01: Proposal Triage

**Severity:** MUST

The `/investor-coach:brand-discovery` skill ALWAYS begins with a triage. The
proposal flow runs ONLY when all triage questions return "no":

1. Does the company have a public URL with sufficient brand presence to
   extract? (`brand-md`-style extraction per BR-NN)
2. Does the founder have a logo file, style guide, or design system to
   supply?
3. Does the founder have specific colour or typography preferences to
   start from?

If any answer is "yes", run the extraction or supplied-asset flow. The
proposal flow is the fallback when nothing exists.

| Attribute | Detail |
|---|---|
| **In Practice** | Triage questions are asked individually, not as a batched form. If the founder is unsure, lean toward extraction — even a thin URL is more grounded than a proposal. |
| **Anti-Pattern** | Skipping triage and going directly to proposal. Proposing a brand when the founder has supplied assets. |
| **How to verify** | `EXPLORATION_JOURNAL.md` records the triage answers and the decision to enter proposal flow. |

---

## Section 2: Defining "Professional, Modern, Crisp"

### BP-02: Falsifiable Aesthetic Criteria

**Severity:** MUST

The brief "professional, modern, crisp" is decomposed into measurable
constraints. The proposal MUST satisfy every one.

**Professional:**

| Constraint | Threshold |
|---|---|
| Saturated colour count | ≤ 2 (primary + optional secondary) |
| Maximum colour saturation (HSL) | ≤ 70% |
| Decorative elements (gradients, shadows, ornaments) | None in tokens |
| Logo/monogram complexity | ≤ 3 distinct shapes |

**Modern:**

| Constraint | Threshold |
|---|---|
| Typeface category | Geometric or humanist sans-serif for primary; transitional or modern serif for secondary if used |
| Typeface era | Released or revived post-1980 (excludes Times New Roman, Arial Italic, etc. as primary) |
| Border-radius unit | 4–12px (rounded, but not pill-shaped) |
| Spacing unit | 8px-based scale (4, 8, 12, 16, 24, 32, 48, 64) |

**Crisp:**

| Constraint | Threshold |
|---|---|
| Body text contrast against background | ≥ 7:1 (exceeds WCAG AA) |
| Headline weight differential to body | ≥ 200 weight units (e.g., 400 body / 600+ headline) |
| Decorative typeface usage | Forbidden |
| Maximum typefaces total | 2 (one sans + optional serif) |

| Attribute | Detail |
|---|---|
| **In Practice** | Before presenting a proposal, every constraint above is verified. The proposal includes a "Criteria check" table showing each constraint and its measured value. |
| **Anti-Pattern** | Proposing on intuition without measuring against the criteria. Skipping the criteria check. |
| **How to verify** | The brand-discovery skill emits a `Criteria check` block in `BRAND.md` showing measured values for every BP-02 constraint. |

---

## Section 3: Typography

### BP-03: System-Stack Font Policy

**Severity:** MUST

The proposal MUST use ONE of the following typography strategies:

| Strategy | When applied |
|---|---|
| **System stack** | Default. No bundled fonts. Uses native sans-serif and serif stacks. |
| **Founder-supplied** | Founder supplied a font file or Google Fonts URL during triage. |
| **Brand-supplied** | A brand asset (style guide, design system) declared the typefaces. |

The plugin does NOT ship custom font files. It does NOT propose specific
Google Fonts unless the founder names them. The default is system stack.

**Default system stack:**

```css
--font-sans: system-ui, -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
--font-serif: Georgia, "Times New Roman", "Cambria", serif;
--font-mono: ui-monospace, "SF Mono", "Cascadia Mono", Consolas, monospace;
```

| Attribute | Detail |
|---|---|
| **In Practice** | The proposal sets `--font-sans` as the primary typeface. `--font-serif` MAY be used for the secondary if the brief calls for warmth or editorial weight; otherwise omit. |
| **Anti-Pattern** | Hard-coding a specific Google Font. Bundling a `.woff2` file. Proposing 3+ typefaces. |
| **How to verify** | `brand-assets/type-stack.md` declares which strategy was chosen and why. `tokens.css` references variables, never literal font names. |

---

### BP-04: Type Scale

**Severity:** SHOULD

The proposal uses a modular scale with these defaults, scaled from the
base body size:

| Token | Default size | Use |
|---|---|---|
| `--text-caption` | 12–14px | Captions, legends, footnotes |
| `--text-body` | 16–18px | Body text, bullets |
| `--text-lead` | 20–24px | Lead paragraphs, slide sub-headings |
| `--text-h2` | 28–32px | Section headings |
| `--text-h1` | 40–56px | Slide titles |

| Attribute | Detail |
|---|---|
| **In Practice** | Pick a base size (16, 17, or 18px) and let the scale follow. Document the base in `type-stack.md`. |
| **Anti-Pattern** | Five custom sizes that don't follow a scale. Heading sizes that don't differentiate clearly. |
| **How to verify** | `tokens.css` declares all five tokens. The scale ratio is consistent (≈ 1.25× per step). |

---

## Section 4: Colour

### BP-05: Business-Type Palette Heuristics

**Severity:** SHOULD

When no founder preference exists, the palette starting point is chosen
by business type. The starting point is then refined with the founder.

| Business type | Default `--colour-primary` family | Rationale |
|---|---|---|
| B2B SaaS, fintech, infrastructure | Restrained blue or slate (HSL: 200–230° hue, 30–60% saturation, 40–55% lightness) | Trust and gravitas; matches category convention |
| Consumer, marketplace, prosumer | Bolder hue chosen from analogous category leaders (avoiding direct competitor match) | Recognition and emotional pull |
| Deeptech, scientific, climate | Neutral-forward with a single accent (HSL: any hue, 20–40% saturation, 40–60% lightness) | Lab-credible; emphasises substance over polish |
| Healthcare, regulated industries | Muted blue or green (HSL: 150–210° hue, 25–45% saturation, 45–55% lightness) | Sober, trustworthy, regulated-industry convention |
| Creative tools, design, content | Refined neutral with one bold accent | Lets user content lead; brand is the frame |

| Attribute | Detail |
|---|---|
| **In Practice** | Present the heuristic-derived palette as a starting point. Show alternatives (one shifted hue, one shifted saturation). Let the founder choose. |
| **Anti-Pattern** | Adopting the heuristic palette without showing alternatives. Insisting on the heuristic when the founder has a preference. |
| **How to verify** | The proposal presents the heuristic palette and at least one alternative. The founder's choice is recorded. |

---

### BP-06: Full Token Set

**Severity:** MUST

The proposed `tokens.css` declares the full set of tokens listed in VD-08
plus the typography tokens in BP-04 and spacing tokens in BP-07. Missing
tokens cause build failures.

Required tokens:

```css
--colour-ink
--colour-ink-muted
--colour-surface
--colour-surface-alt
--colour-primary
--colour-positive
--colour-negative
--colour-neutral
--font-sans
--font-serif (optional)
--text-caption / --text-body / --text-lead / --text-h2 / --text-h1
--space-1 through --space-8 (8px scale)
--radius-sm / --radius-md / --radius-lg
```

| Attribute | Detail |
|---|---|
| **In Practice** | The proposal emits both `tokens.css` (CSS custom properties) and `tokens.json` (flat object) for tooling. |
| **Anti-Pattern** | A partial token set that breaks the build script. |
| **How to verify** | `/investor-coach:validate` confirms all required tokens exist with valid values. |

---

### BP-07: Spacing Scale

**Severity:** SHOULD

Spacing tokens follow an 8px-based geometric scale:

| Token | Value |
|---|---|
| `--space-1` | 4px |
| `--space-2` | 8px |
| `--space-3` | 12px |
| `--space-4` | 16px |
| `--space-5` | 24px |
| `--space-6` | 32px |
| `--space-7` | 48px |
| `--space-8` | 64px |

| Attribute | Detail |
|---|---|
| **In Practice** | The build scripts use these tokens for margins, padding, and gutters. No magic-number spacing in slide files. |
| **Anti-Pattern** | Arbitrary spacing values that don't follow the scale. Slides where margins look "off" because of inconsistent spacing. |
| **How to verify** | `tokens.css` declares all eight space tokens. Build scripts reference them. |

---

## Section 5: Contrast and Accessibility

### BP-08: WCAG AA Verification

**Severity:** MUST

Before the proposal is finalised, every text-on-background pairing is
verified against WCAG AA contrast minimums (4.5:1 body, 3:1 large) and
the BP-02 "crisp" requirement (7:1 body).

| Pair | Required ratio |
|---|---|
| `--colour-ink` on `--colour-surface` | ≥ 7:1 |
| `--colour-ink` on `--colour-surface-alt` | ≥ 7:1 |
| `--colour-ink-muted` on `--colour-surface` | ≥ 4.5:1 |
| `--colour-primary` on `--colour-surface` (for headlines / accents) | ≥ 3:1 |
| Chart series colours on `--colour-surface` | ≥ 3:1 |

| Attribute | Detail |
|---|---|
| **In Practice** | If a pairing fails, the proposing skill iterates — adjusting lightness or saturation — until all pairs pass. The contrast table is shown in `BRAND.md`. |
| **Anti-Pattern** | Adopting a proposed palette without verifying contrast. |
| **How to verify** | `BRAND.md` contains a contrast-ratio table for every required pair. All values meet thresholds. |

---

## Section 6: Logo

### BP-09: Monogram Generation

**Severity:** SHOULD

When no logo is supplied, the proposal generates a monogram from the
company's initials.

| Constraint | Rule |
|---|---|
| Characters | 1–3 letters (company first word's initial, optionally first two words' initials) |
| Typeface | Same as `--font-sans` at a heavy weight (700+) |
| Shape | Square or circle container |
| Colour | `--colour-primary` on `--colour-surface`, OR `--colour-surface` on `--colour-primary` |
| Output | SVG saved to `brand-assets/logo.svg` |
| Variants | Light variant (for dark backgrounds) and dark variant (for light backgrounds) |

| Attribute | Detail |
|---|---|
| **In Practice** | `scripts/generate_monogram.py` produces the SVG. The founder reviews and approves before adoption. The monogram is replaceable later when the company has a real logo. |
| **Anti-Pattern** | Auto-adopting the monogram without founder review. Generating a monogram with letters that produce awkward combinations (e.g., the company's name initials read as something unintended). |
| **How to verify** | `brand-assets/logo.svg` exists. The founder has approved in writing. |

---

## Section 7: Approval and Iteration

### BP-10: Founder Approval Gate

**Severity:** MUST

Before `BRAND.md` is marked `page-build-ready: true`, the founder MUST
have explicitly approved the proposal. Approval is recorded in
`EXPLORATION_JOURNAL.md` with date and summary of what was approved.

The approval flow:

1. The skill presents the proposal — palette swatches, type samples,
   monogram, contrast table, criteria check.
2. The founder iterates (typically 1–3 rounds). The skill responds to
   feedback by adjusting tokens and re-verifying every constraint.
3. On approval, the skill writes `BRAND.md` `page-build-ready: true` and
   records the approval entry.

| Attribute | Detail |
|---|---|
| **In Practice** | Present visually — show what the deck title slide would look like with the proposed tokens. Show what a financial chart would look like. Founders evaluate brand by example, not by token table. |
| **Anti-Pattern** | Marking `page-build-ready: true` without founder confirmation. Forcing the founder to read a token table to evaluate the proposal. |
| **How to verify** | `EXPLORATION_JOURNAL.md` contains an approval entry with date and approved fields. |

---

## Section 8: Anti-Patterns

| ID | Anti-Pattern | Violated Standard |
|---|---|---|
| AP-BP-01 | Entering proposal flow without triage | BP-01 |
| AP-BP-02 | Proposing on aesthetic intuition without criteria check | BP-02 |
| AP-BP-03 | Bundling a custom font file | BP-03 |
| AP-BP-04 | Proposing 3+ typefaces | BP-03 |
| AP-BP-05 | Skipping business-type palette heuristic | BP-05 |
| AP-BP-06 | Incomplete token set | BP-06 |
| AP-BP-07 | Non-scale spacing values | BP-07 |
| AP-BP-08 | Adopting palette without WCAG verification | BP-08 |
| AP-BP-09 | Auto-adopting monogram without founder review | BP-09 |
| AP-BP-10 | Marking `page-build-ready: true` without founder approval | BP-10 |

---

## Section 9: Verification Checklist

Before declaring a proposed brand kit complete, verify:

- [ ] Triage was conducted and recorded (BP-01)
- [ ] BP-02 criteria check passes for every constraint
- [ ] Typography strategy declared in `type-stack.md` (BP-03)
- [ ] Type scale tokens present and consistent (BP-04)
- [ ] Palette grounded in business-type heuristic with alternatives shown (BP-05)
- [ ] Full token set present in `tokens.css` and `tokens.json` (BP-06)
- [ ] Spacing scale follows 8px geometric pattern (BP-07)
- [ ] WCAG AA contrast table present and passing (BP-08)
- [ ] Monogram generated and approved (BP-09)
- [ ] Founder approval recorded in `EXPLORATION_JOURNAL.md` (BP-10)
- [ ] None of AP-BP-01 through AP-BP-10 present
- [ ] `BRAND.md` marked `page-build-ready: true`

---

## Relationship to Other Standards

| Standard | Relationship |
|---|---|
| `brand-standard.md` (BR-) | BR- governs extraction from existing material; BP- governs proposal when none exists |
| `visual-design-standard.md` (VD-) | VD-05, VD-08 consume tokens produced by BP- |
| `cognitive-load.md` (CL-) | CL-06 (coherent mental model) requires single, consistent brand — BP- enforces this for the proposal case |
| `coaching-without-conflict.md` | The proposal flow follows Tenets 1 (Show, don't tell — present visually), 5 (Offer alternatives — palette options), 6 (Respect iteration — accept feedback rounds) |

---

## Version History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-05-13 | Initial release. Ten rules across triage, criteria, typography, palette, contrast, monogram, and approval. Ten anti-patterns. |
