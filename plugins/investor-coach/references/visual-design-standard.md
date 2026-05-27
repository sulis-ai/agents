# Visual Design Standard

<!-- summary -->

This standard governs the visual layout of every slide and the financial
HTML dashboard. Thirteen rules (VD-01 through VD-13) translate cognitive
load principles, Tufte's data-ink ratio, and brand-token application into
falsifiable layout constraints.

VD- works alongside `deck-narrative-standard.md` (ND-): ND- governs *what*
each slide says; VD- governs *how* it is presented. VD- consumes the brand
tokens locked in `brand-assets/tokens.css` and `brand-assets/tokens.json`,
never inventing colour, typography, or spacing of its own.

The standard rests on three commitments:

1. **One idea per slide.** Visual layout enforces what ND-06 requires
   semantically. A slide that exceeds the chunk limit visually has failed.
2. **Brand-locked.** Every colour, typeface, weight, spacing unit, and
   logo placement comes from `brand-assets/`. The deck wears the
   customer's brand consistently.
3. **Crisp by default.** Generous whitespace, high contrast, restrained
   data ink. The pitch deck looks like a partner could photograph any
   slide and show it to their colleagues without explanation.

A deck satisfies the standard when all MUST rules pass on every slide and
the financial dashboard.

<!-- detail -->

> **Version:** 1.0.0
> **Status:** Active

---

## Provenance

This standard synthesises:

- Edward Tufte, "The Visual Display of Quantitative Information" (1983) —
  data-ink ratio, chartjunk, small multiples
- Cognitive Load Standard — CL-01 (chunk limit), CL-02 (extraneous load),
  CL-06 (coherent mental model)
- Robert Bringhurst, "The Elements of Typographic Style" — typographic
  hierarchy, line length, leading
- Web Content Accessibility Guidelines (WCAG) 2.2 AA — contrast minimums
- Sequoia and a16z partner-meeting design conventions (public templates)

This is practitioner knowledge consolidated from typography, information
design, and accessibility standards. The accessibility minimums are
peer-reviewed.

---

## Severity Convention

| Severity | Meaning |
|---|---|
| **MUST** | Non-negotiable. A slide that violates this fails validation. |
| **SHOULD** | Default. Deviation requires explicit justification in the slide front matter. |
| **MAY** | Permitted option. Use judgement. |

---

## Section 1: Layout and Density

### VD-01: One Idea Per Slide

**Severity:** MUST

Each slide presents exactly one primary idea. The slide title states it;
the visual body supports it. Secondary points belong in speaker notes or
a separate slide.

| Attribute | Detail |
|---|---|
| **In Practice** | If the slide has two charts of equal weight, split. If the slide has a primary visual and a small secondary callout, keep — provided the callout serves the primary idea. |
| **Anti-Pattern** | "Vision + roadmap + team" on one slide. Two unrelated charts side-by-side. |
| **How to verify** | The slide title states one idea. Every visual element serves that idea. |

---

### VD-02: Chunk Limit Visual Enforcement (CL-01)

**Severity:** MUST

Visual elements per slide MUST NOT exceed 5 independent chunks. Counting:

| Element | Counts as |
|---|---|
| One bullet | 1 chunk |
| One chart | 1 chunk + (annotations as additional chunks) |
| One image | 1 chunk |
| One headline | 0 (the headline frames the chunks) |
| One small caption beneath an image | 0 (caption attaches to image chunk) |

| Attribute | Detail |
|---|---|
| **In Practice** | Count chunks before approving the layout. If over 5, cut or split. |
| **Anti-Pattern** | 7-bullet slides. Charts with 10 series. Logo soups with 12 customer logos. |
| **How to verify** | `/investor-coach:validate` counts visible chunks per slide via the slide's front matter and warns if > 5. |

---

### VD-03: Whitespace Floor

**Severity:** SHOULD

A slide MUST have at least 25% of its area as deliberate whitespace
(non-content margin, padding around blocks, gutter between columns).

| Attribute | Detail |
|---|---|
| **In Practice** | Margins ≥ 8% of slide width on every side. Vertical spacing between distinct blocks ≥ 24px (or brand spacing unit ×2). |
| **Anti-Pattern** | Edge-to-edge content. Blocks pressed against each other with no separation. Charts that fill the slide with no margin. |
| **How to verify** | The PPTX build script enforces minimum margins per VD-03. The HTML build applies the same via CSS. |

---

### VD-04: Hierarchy (Three-Level Maximum)

**Severity:** MUST

Each slide has at most three levels of typographic hierarchy: title (h1),
sub-element (h2 / lead bullet / chart title), supporting (body / sub-bullet
/ caption). No fourth level.

| Attribute | Detail |
|---|---|
| **In Practice** | The brand tokens define type sizes for h1, h2, body, caption. Each slide uses h1 once, h2 or body for the structural elements, caption only if attached to a visual. |
| **Anti-Pattern** | Five font sizes on a slide. Body text used at three different sizes. Multiple "subtitles" with no clear relative hierarchy. |
| **How to verify** | Inspect any slide. No more than three sizes in use. |

---

## Section 2: Typography

### VD-05: Brand-Locked Typography

**Severity:** MUST

All typography on every slide and in the financial dashboard uses ONLY
the typefaces and weights declared in `brand-assets/type-stack.md` and
referenced by `brand-assets/tokens.css`.

| Attribute | Detail |
|---|---|
| **In Practice** | The deck never introduces a typeface not in the brand assets. If a slide design calls for a typeface not present, the brand is updated (Phase 3) before the slide is built. |
| **Anti-Pattern** | "Just this one slide uses a script font for emphasis." Brand drift accumulates across slides and breaks CL-06 (coherent mental model). |
| **How to verify** | Build scripts pull all typefaces from `brand-assets/`. No inline overrides. |

---

### VD-06: Line Length and Leading

**Severity:** SHOULD

Body text line length: 45–75 characters. Headline line length: ≤ 50
characters. Leading (line height): body 1.4–1.6, headline 1.1–1.3.

| Attribute | Detail |
|---|---|
| **In Practice** | A long quote that exceeds 75 characters per line wraps to a second line — that's fine; multi-line text should respect the maximum per line. Headlines that exceed 50 characters MUST be shortened (per ND-04). |
| **Anti-Pattern** | 120-character body lines. Headlines that wrap to three lines. Cramped leading on body text. |
| **How to verify** | The build script logs line-length violations. |

---

### VD-07: Numeral Treatment

**Severity:** SHOULD

Numerals in headline positions and on charts use tabular figures
(monospaced numerals) so columns align. Body-text numerals use
proportional figures unless tabular alignment is required.

| Attribute | Detail |
|---|---|
| **In Practice** | The brand `tokens.css` declares `font-feature-settings: "tnum"` for chart labels and key statistics. |
| **Anti-Pattern** | A "fast facts" 2×3 grid where the numbers don't align vertically because proportional figures are in use. |
| **How to verify** | Chart labels and fast-facts numerals are visually aligned. |

---

## Section 3: Colour and Contrast

### VD-08: Brand-Locked Colour Palette

**Severity:** MUST

All colour on slides and in the financial dashboard comes ONLY from
`brand-assets/tokens.css`. The palette includes:

| Token | Role |
|---|---|
| `--colour-ink` | Primary text colour |
| `--colour-ink-muted` | Secondary text colour |
| `--colour-surface` | Slide background |
| `--colour-surface-alt` | Alternate background (e.g., dark slides, callout blocks) |
| `--colour-primary` | Brand accent — used for emphasis, charts, logo placement |
| `--colour-positive` | Charts: positive deltas, growth |
| `--colour-negative` | Charts: negative deltas, decline |
| `--colour-neutral` | Charts: comparison series, baseline |

| Attribute | Detail |
|---|---|
| **In Practice** | No inline colour overrides. If a slide needs a colour not in the palette, the palette is extended (Phase 3) before the slide is built. |
| **Anti-Pattern** | Hard-coded `#ff5733` in a slide. Different reds across charts because "this one looked better." |
| **How to verify** | The build scripts read only from `tokens.css`. No literal hex values in slide files. |

---

### VD-09: WCAG AA Contrast

**Severity:** MUST

Every text-on-background pairing MUST achieve WCAG 2.2 AA contrast
minimums:

| Pair | Minimum ratio |
|---|---|
| Body text on background | 4.5:1 |
| Large text (≥ 24px) on background | 3:1 |
| Chart data on background | 3:1 |

| Attribute | Detail |
|---|---|
| **In Practice** | The brand-discovery skill verifies WCAG AA when extracting or proposing tokens. The build scripts re-verify per slide and fail loudly if a pairing drops below threshold (e.g., muted text on alternate surface). |
| **Anti-Pattern** | Light-grey-on-white captions. Coloured text on coloured backgrounds without contrast verification. |
| **How to verify** | Build script outputs contrast ratios for every text/background pair. None below threshold. |

---

### VD-10: Colour-Only Encoding Forbidden

**Severity:** MUST

Information conveyed by colour MUST also be conveyed by shape, position,
label, or pattern. Colour-blind viewers must be able to read every chart
and every status indicator.

| Attribute | Detail |
|---|---|
| **In Practice** | Charts use both colour and shape (line + dashed-line, bar + striped-bar). Status indicators use icons + colour, not colour alone. |
| **Anti-Pattern** | A bar chart with green-good and red-bad as the only differentiator. Status labels relying on red / green dots without text. |
| **How to verify** | Each chart and indicator passes a colour-strip test (does it remain legible in greyscale?). |

---

## Section 4: Charts and Data Visualisation

### VD-11: Data-Ink Ratio

**Severity:** SHOULD

Maximise the ink that conveys data; minimise the ink that doesn't. Per
Tufte: remove gridlines that don't aid comprehension, drop axis decoration
that doesn't serve, kill 3D effects, kill chartjunk.

| Element | Rule |
|---|---|
| Gridlines | Removed unless required for value-reading; if kept, use `--colour-ink-muted` at 50% opacity |
| Tick marks | Minimal — major ticks only |
| Borders | None around chart panels |
| Backgrounds | Transparent — chart sits on the slide background |
| 3D effects | Forbidden |
| Drop shadows | Forbidden on chart elements |
| Legend | Only when needed; prefer direct labelling of series |

| Attribute | Detail |
|---|---|
| **In Practice** | A line chart with no gridlines, two labelled series, and a clean y-axis with start-at-zero (unless explicitly noted) — that's the default. |
| **Anti-Pattern** | A 3D pie chart with exploded slices, gradient fills, and a separate legend. |
| **How to verify** | Every chart reviewed against the table above. Build script applies these defaults via Chart.js configuration. |

---

### VD-12: Truthful Axes

**Severity:** MUST

Charts MUST NOT mislead through axis manipulation. Y-axes start at zero
unless the chart explicitly notes the break ("Y-axis starts at $80M to
show variation"). X-axes use consistent intervals.

| Attribute | Detail |
|---|---|
| **In Practice** | A revenue chart that looks like hockey-stick growth because the y-axis starts at $4M instead of $0 is misleading. Either show the full axis or annotate the break clearly. |
| **Anti-Pattern** | Truncated y-axes without annotation. Inconsistent x-axis intervals. Logarithmic scales without explicit labelling as such. |
| **How to verify** | Build script logs any axis with truncation. Truncations require explicit `axis-break-note:` in the chart's metadata. |

---

## Section 5: Logos, Images, and Iconography

### VD-13: Restrained Imagery

**Severity:** SHOULD

Images, logos, and icons serve the slide's idea. Decorative imagery
(stock photos, generic illustrations) is forbidden unless the brand has
declared a deliberate-distinction visual style requiring them.

| Element | Rule |
|---|---|
| Customer logos | Maximum 8 per slide. Greyscale unless brand permits otherwise. Aligned to a grid. |
| Product screenshots | One per slide. Annotated to direct attention. |
| Stock photography | Forbidden unless the brand has declared a deliberate visual style requiring it (BP-NN) |
| Iconography | Single line-weight family from brand assets. Maximum 4 icons per slide. |
| Founder photos | Square crops, consistent treatment, no decorative borders |

| Attribute | Detail |
|---|---|
| **In Practice** | If a slide reaches for a stock photo because the content is thin, fix the content. Imagery does not compensate for weak argument. |
| **Anti-Pattern** | Decorative globe images on the market-size slide. Stock-photo handshakes on the team slide. Cluttered illustration on the solution slide. |
| **How to verify** | Each image on each slide has a stated purpose in the slide front matter (`image-purpose:`). Purposeless imagery is removed. |

---

## Section 6: Anti-Patterns

| ID | Anti-Pattern | Violated Standard |
|---|---|---|
| AP-VD-01 | Multiple ideas on one slide | VD-01 |
| AP-VD-02 | More than 5 chunks per slide | VD-02 |
| AP-VD-03 | Edge-to-edge content with no whitespace | VD-03 |
| AP-VD-04 | More than three typographic levels | VD-04 |
| AP-VD-05 | Inline typeface or weight override | VD-05 |
| AP-VD-06 | Body line length > 75 characters | VD-06 |
| AP-VD-07 | Inline hex colour bypassing tokens | VD-08 |
| AP-VD-08 | Contrast below WCAG AA | VD-09 |
| AP-VD-09 | Colour-only encoding | VD-10 |
| AP-VD-10 | 3D charts, chartjunk, gradient fills | VD-11 |
| AP-VD-11 | Truncated axes without annotation | VD-12 |
| AP-VD-12 | Decorative stock imagery | VD-13 |
| AP-VD-13 | Charts without direct labelling of series (forcing legend lookup) | VD-11 |

---

## Section 7: Verification Checklist

Before declaring the visual layer stage-conformant, verify:

- [ ] Every slide presents one primary idea (VD-01)
- [ ] No slide exceeds 5 visible chunks (VD-02)
- [ ] Whitespace floor met on every slide (VD-03)
- [ ] No more than three typographic levels per slide (VD-04)
- [ ] All typography from `brand-assets/` (VD-05)
- [ ] Line lengths and leading within range (VD-06)
- [ ] Tabular figures used for aligned numerals (VD-07)
- [ ] All colour from `tokens.css` (VD-08)
- [ ] All text/background pairs meet WCAG AA (VD-09)
- [ ] No colour-only encoding (VD-10)
- [ ] Data-ink ratio respected on every chart (VD-11)
- [ ] Y-axes start at zero or annotate breaks (VD-12)
- [ ] No decorative imagery; every image has stated purpose (VD-13)
- [ ] None of AP-VD-01 through AP-VD-13 present

---

## Relationship to Other Standards

| Standard | Relationship |
|---|---|
| `deck-narrative-standard.md` (ND-) | ND-06 (chunk limit) is enforced visually by VD-02 |
| `brand-standard.md` (BR-) | VD-05, VD-08 consume tokens from BR- extraction |
| `brand-proposal-standard.md` (BP-) | When no brand exists, BP- generates tokens consumed by VD- |
| `cognitive-load.md` (CL-) | CL-01 → VD-02; CL-02 → VD-13 (extraneous load); CL-06 → VD-05, VD-08 (consistency) |

---

## Version History

| Version | Date | Change |
|---|---|---|
| 1.0.0 | 2026-05-13 | Initial release. Thirteen rules across layout, typography, colour, charts, and imagery. Thirteen anti-patterns. |
