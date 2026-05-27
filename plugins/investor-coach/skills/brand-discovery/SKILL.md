---
name: brand-discovery
description: >
  Phase 3 of the Investor Deck Coach. Triages whether the company has a brand
  to extract from supplied assets, or proposes a basic brand kit if none
  exists. Produces BRAND.md and brand-assets/ (tokens.css, tokens.json,
  logo.svg, type-stack.md). Tokens drive every subsequent visual deliverable.
user_invocable: true
---

# Brand Discovery

When invoked, determine the customer brand that the deck and financial
dashboard will wear. The brand applies to every visual deliverable —
PPTX, HTML deck, financial summary HTML — so this phase locks the
visual identity before any narrative or build work.

## When to invoke

- After `/investor-coach:discovery` produces `DISCOVERY.md`.
- When the founder wants to revise the brand on an existing pitch
  (versions the assets in the journal).

## When NOT to invoke

- Before discovery — stage and audience inform brand choices.
- After `/investor-coach:build-deck` has produced final deliverables — a brand
  change at that point invalidates the build. If urgent, re-run
  brand-discovery, then re-run build-deck.

---

## Execution

### Step 1: Triage (BP-01)

Ask one question at a time:

1. Does the company have a public URL with a brand to extract?
2. Does the founder have a logo file, style guide, brand book, or
   design tokens to supply?
3. Does the founder have specific colour or typography preferences?

If any answer is "yes", proceed to **extraction flow**. If all are "no",
proceed to **proposal flow**.

Record the triage decision in `journal/{YYYY-MM-DDTHHMMSSZ}-{topic}.md`.

### Step 2A: Extraction flow

Apply `references/brand-standard.md` (BR-01..06):

1. Crawl the URL (max 8 pages) or read supplied files.
2. Extract palette, typography, voice dimensions, distinctive assets.
3. Quantify voice (per BR-04) with corpus citations (BR-05).
4. Run BR-02 (competitor substitution test) on identity claims.
5. Generate `tokens.css` and `tokens.json` from the extracted palette
   and type stack.
6. Generate `type-stack.md` declaring the typography strategy.
7. Write `BRAND.md` per BR- structure.
8. If logo files were supplied, save to `brand-assets/logo.svg` and
   `brand-assets/logo-*.{png,jpg}` variants.
9. Run `scripts/generate_monogram.py` only if no logo supplied.
10. Verify WCAG AA contrast for every text-on-background pair (VD-09).
11. Present to the founder for review.

### Step 2B: Proposal flow

Apply `references/brand-proposal-standard.md` (BP-01..10):

1. Identify the business type (from `DISCOVERY.md` / `PITCH.yaml`) and
   select a starting palette from BP-05 heuristics.
2. Show the founder the starting palette AND at least one alternative
   (one shifted hue, one shifted saturation).
3. Select typography strategy per BP-03:
   - Default: system stack (no bundled fonts).
   - If founder names a Google Font or supplies a file, use that.
4. Generate the full token set per BP-06: colours, typography, spacing,
   radii.
5. Generate `tokens.css`, `tokens.json`, `type-stack.md`.
6. Run `scripts/generate_monogram.py` to produce `logo.svg` (and dark
   variant).
7. Verify BP-02 (professional / modern / crisp criteria) — emit the
   criteria-check table into `BRAND.md`.
8. Verify WCAG AA + BP-02 "crisp" 7:1 ratio for every text-on-background
   pair. Iterate tokens if any pairing fails.
9. Present to the founder visually — render a mock slide title and a
   mock chart with the proposed tokens. Iterate per founder feedback
   (typically 1–3 rounds).
10. On founder approval, write `BRAND.md` with `page-build-ready: true`
    and record approval in `journal/{YYYY-MM-DDTHHMMSSZ}-{topic}.md` (BP-10).

### Step 3: Lock the brand

Once approved:

- `BRAND.md` is set `page-build-ready: true`.
- `tokens.css`, `tokens.json`, `type-stack.md`, `logo.svg` are written
  to `brand-assets/`.
- Journal entry records: triage decision, flow taken, approval date,
  any deviations from defaults.

### Step 4: Transition

Propose `/investor-coach:market-research` as the next step.

---

## What `brand-assets/` looks like at end of Phase 3

```
brand-assets/
├── tokens.css            # CSS custom properties
├── tokens.json           # Flat object for tooling
├── logo.svg              # Logo (supplied) or monogram (generated)
├── logo-light.svg        # Light variant for dark backgrounds (if applicable)
└── type-stack.md         # Typography strategy declaration
```

---

## Coaching gates

- **Show, don't tell:** present brand visually, not as a token table.
- **Recommend the convention, then offer alternatives:** lead with the
  BP-03 default (system typography stack + professional/modern/crisp
  palette + accessible contrast pair) as the recommended brand, and
  explain why it's the boring-default choice (no font licensing, fast
  load, accessible by construction). Then offer 1–2 alternatives only
  with explicit rationale for the deviation (e.g. "Inter via Google
  Fonts buys you a more distinctive feel at the cost of an external
  dependency"). Never present 2–3 options as a neutral menu — per
  Convention Preference (CP-05), the founder needs the recommendation
  to react to, not a flat list of choices.
- **Respect iteration:** founders refine brand by feedback. Welcome 3
  rounds before considering scope creep.
- **Acknowledge complexity:** the founder may have brand intuitions
  from prior products. Ask before overriding.

---

## Refusals

Refuse if:

- The founder asks you to bundle a custom font file → "I can use a
  system stack, a Google Font, or a file you supply via the project
  folder — but the plugin doesn't ship fonts."
- The founder asks to skip the contrast verification → "WCAG AA is
  a delivery floor. I'll show you which pairs fail and we can fix them
  together."
- The founder wants to use a logo that fails contrast → "The logo is
  fine; what fails is the colour pair. Let me show you alternatives
  that preserve the logo and pass contrast."

---

## Gotchas

- **Don't propose without triage.** Even a thin URL is more grounded
  than a heuristic-only proposal.
- **Don't skip the criteria check.** BP-02 is not aesthetic — it's a
  pass/fail.
- **Don't approve without showing visually.** Founders can't evaluate
  tokens; they evaluate slides.
- **Don't generate a monogram with awkward letter combinations.**
  Check the initials read cleanly before committing.

---

## Output checklist

- [ ] Triage recorded
- [ ] Flow taken (extraction or proposal) recorded
- [ ] `BRAND.md` written, `page-build-ready: true`
- [ ] `tokens.css` complete (all VD-08 + BP-06 tokens)
- [ ] `tokens.json` matches `tokens.css`
- [ ] `type-stack.md` declares strategy
- [ ] `logo.svg` present (supplied or generated)
- [ ] WCAG AA contrast table in `BRAND.md`, all pairs pass
- [ ] (Proposal flow) BP-02 criteria check in `BRAND.md`, all pass
- [ ] (Proposal flow) Founder approval recorded in journal
- [ ] Next step (`/investor-coach:market-research`) proposed
