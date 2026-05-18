---
name: brand-md
description: >
  Extract a BRAND.md brand identity document from a URL. Crawls the target site,
  analyses voice, vocabulary, identity, and microcopy patterns, then produces a
  structured BRAND.md following the Brand Identity Standard (brand-standard.md).
  Applies BR-01 through BR-05 quality gates before setting page-build-ready.
user_invocable: true
---

# Brand MD

Extract a structured BRAND.md from a live website. The output follows the
Brand Identity Standard and is ready for consumption by AI coding agents,
copy generators, and design tools.

---

## Arguments

- **Arg 1 (required):** Target URL — the root of the site to extract from
- **Arg 2 (optional):** Output path — defaults to `./BRAND.md`

---

## Execution

### Step 1: Load the Standard

Read `references/brand-standard.md` completely before doing anything else.
This file governs every decision in this extraction — the YAML schema, required
Markdown sections, quality standards (BR-01 through BR-06), and the
`page-build-ready` checklist.

### Step 2: Crawl the Target Site

Fetch the root URL. From the response, scan for internal navigation and footer
links that point to secondary pages. Prioritise in this order:

1. About / Our Story / Who We Are
2. Product / Service / How It Works pages (up to 3)
3. Impact / Sustainability / Mission
4. Blog / News listing page (listing only, not individual posts)
5. Contact / Help (if short and likely to contain microcopy)

Crawl up to **8 secondary pages**. Stop earlier if content becomes repetitive
(same boilerplate, same CTA patterns). For each page, record its name and
estimated word count.

**JS-rendered sites:** If the `<body>` content of the root URL is under 500
characters, the site is almost certainly a JavaScript SPA (Next.js, React, etc.)
and the static fetch has returned a shell. Report this to the user immediately,
lower `extraction-confidence` to `low`, and continue with what is available.
Do not fabricate copy.

Track throughout:
- `pages-crawled` count
- `word-count` estimate (sum across all pages)
- Page names, for Extraction Notes

### Step 3: Score Voice Dimensions (BR-04)

Sample at least 20 sentences from across the full corpus — not just the homepage.
For each of the three dimensions, read the sentences and assign a position:

| Dimension | Left pole (-) | Right pole (+) |
|-----------|--------------|----------------|
| formal-casual | Formal (-3) | Casual (+3) |
| warm-clinical | Clinical (-3) | Warm (+3) |
| direct-conversational | Conversational (-3) | Direct (+3) |

Average the placements for each dimension. Round to nearest integer.

**Calibration:** A score of 0 is rare — most brands sit to one side. If you
land at 0, re-read 10 more sentences to confirm it is genuinely balanced before
accepting it.

Also determine from the corpus:
- `dominant` and `secondary` grammatical person (first-plural, second-person,
  third-person, brand-as-subject)
- `sentence-length` (short = avg < 12 words, medium = 12–20, long = > 20, mixed)
- `question-usage` and `exclamation-frequency` (rare / occasional / frequent)
- `oxford-comma`, `em-dash` (yes / no — look for consistent usage pattern)
- `jargon-level` (low = all terms explained or plain; medium = some domain terms
  used without definition; high = assumes audience familiarity)
- `claim-density` (low = mostly narrative; medium = mix; high = statistics and
  specifics in most paragraphs)
- `capitalisation.headings`, `.buttons`, `.navigation` (sentence-case or title-case)

### Step 4: Extract Vocabulary

**Power words:** Read the corpus and identify words and short phrases that appear
frequently AND carry high emotional or brand weight. These are the words that
make the brand sound like itself. Aim for 8–12 entries.

**Avoided vocabulary:** Look for surprising absences — category-standard terms
that competitors would use but this brand doesn't. Also look for qualified uses:
"we never say X unqualified" or consistent paraphrasing of a standard term.
Aim for 4–8 entries.

### Step 5: Attempt Golden Circle Extraction (BR-01)

Search the about, our-story, and mission sections for:
- **WHY:** A founding belief, frustration, or injustice — something the founder
  saw broken in the world. Look for "we were fed up with", "we believe", "we
  knew there had to be", "we started X because".
- **HOW:** The differentiating approach — values-in-action, not marketing slogans.
  Look for "the way we do it", "what makes us different", "our approach".
- **WHAT:** Products and services, from the customer's perspective.

Draft each section in strict WHY → HOW → WHAT order. If WHY cannot be confirmed
from the corpus, mark the entire Identity section
`[ASSERTED — not corpus-verified]` and document the gap in Extraction Notes.
Do not fabricate a founding story.

### Step 6: Draft Brand Essence and Positioning

**Brand Essence:** One sentence in the form:
`{Brand} {verb phrase expressing WHY} {for whom}.`

Example: "Honest Mobile exists to prove that a mobile network can be transparent,
affordable, and good for the planet — for people who are done being taken advantage of."

**Positioning:** One paragraph answering: who is this for, what does it replace or
displace, what is the one thing it does better than any alternative?

**BR-02 flag:** Add this note after every identity claim and the positioning
paragraph:

> `[Review: run Competitor Substitution Test — BR-02. Replace the brand name with
> 2–3 named competitors. If the claim still reads as plausible, rewrite it.]`

BR-02 requires human judgment. Do not attempt to automate it or silently skip it.

### Step 7: Build Do's and Don'ts (BR-05)

Write a minimum of 5 rules. Each rule MUST follow this format exactly:

```markdown
**N. Rule statement in plain language.**
- **Do:** Positive example (verbatim or paraphrased from corpus)
- **Don't:** What the brand avoids
- **Corpus cite:** "Verbatim quote from corpus" — Page Name
```

If a rule is observed as a pattern but no single sentence captures it perfectly,
use the closest quote and note the pattern. If a rule cannot be grounded in the
corpus at all, mark it:
`- **Corpus cite:** [ASSERTED — not corpus-verified]`

### Step 8: Build Microcopy Patterns Table

Build a table with these rows as a minimum:

| Context | Pattern | Examples |
|---------|---------|---------|
| Button labels | ... | ... |
| Hero CTAs | ... | ... |
| Pricing | ... | ... |
| Social proof | ... | ... |
| FAQ headers | ... | ... |
| Error states | ... | ... |
| Newsletter/footer | ... | ... |

Populate from corpus. For any row where no corpus evidence exists, write
`[ASSERTED]` in the Examples column.

### Step 9: Attempt Distinctive Assets (BR-03)

From what is visible in the static fetch (inline styles, CSS class names, SVG
elements, meta tags, logo file paths, font references), attempt to identify:

- Logo style (wordmark, icon+wordmark, icon-only, illustrated)
- Primary colour (hex if visible in inline styles or CSS variables)
- Typography approach (geometric sans, humanist, serif, monospace, custom)
- Tagline structure (statement, question, imperative, brand name only)
- Imagery style (photography, illustration, flat icons, mixed)

Classify each as `convention` (follows category norms) or
`deliberate-distinction` (stands out from category).

If assets cannot be confirmed from the static fetch (JS-rendered, no inline
styles), do NOT guess. Omit the `distinctive-assets` field from YAML and
document the gap in Extraction Notes with a recommendation to inspect the
rendered site.

### Step 10: Assemble and Write BRAND.md

Build the YAML frontmatter first. Include all required fields. Include optional
fields where data was confidently extracted.

Set `page-build-ready` using this checklist:

- [ ] All required YAML fields present (name, version, extraction-date,
  extraction-confidence, page-build-ready, brand-voice with all sub-fields)
- [ ] All 9 required Markdown sections present (Brand Essence through
  Extraction Notes)
- [ ] BR-04: All three voice dimension scores present and grounded
- [ ] BR-05: No uncited claims in Do's and Don'ts or Microcopy Patterns
  (either corpus cite or explicit `[ASSERTED]` marker)
- [ ] No `[TODO]` or `[PENDING]` markers in required sections

If all boxes are checked: `page-build-ready: true`.

BR-01 and BR-02 gaps (identity not confirmed from corpus, substitution test
not yet run) do NOT block `page-build-ready: true` as long as they are fully
documented in Extraction Notes.

Write to the output path. Then report to the user:
- What was extracted with high confidence
- What was asserted (and where)
- Recommended follow-up: which pages to crawl next, what to manually verify
  (BR-02 substitution test, distinctive assets if JS-rendered)

---

## Gotchas

- **JS-rendered sites return empty HTML.** Next.js, React SPAs, and similar
  frameworks render in the browser. A static WebFetch returns a near-empty
  `<body>`. Check content length before scoring. Warn the user, lower confidence
  to `low`, and work with what's there. Do not invent copy.

- **Score 0 is a red flag, not a neutral.** If a dimension scores 0, you have
  either not sampled enough sentences or the brand is genuinely split. Confirm
  with 10 more sentences. A true 0 is possible but should be explicitly noted
  in the Voice & Tone narrative.

- **BR-02 is non-automatable.** Never silently pass or skip the Competitor
  Substitution Test. Always flag every identity claim with the `[Review: BR-02]`
  note. The user must run this manually.

- **Power words are not frequency alone.** A word can appear 50 times and be
  generic ("the", "our"). Power words carry brand weight — they define how the
  brand sounds. Frequency is a signal, not the definition.

- **Do not conflate Brand Essence with tagline.** The Brand Essence sentence is
  a positioning anchor for AI tools, not a headline. It should be descriptive
  and explanatory, not punchy. The tagline (if it exists) goes in Copy Examples.

- **Distinctive assets require visible evidence.** If the site is JS-rendered
  and no CSS variables or inline styles are visible, you cannot confirm primary
  colour or typography. Omit from YAML. An absent field is better than a wrong one.

- **`page-build-ready: true` is a contract.** AI tools that consume BRAND.md
  treat this flag as a guarantee. Do not set it unless all checklist items pass.
  A `false` with a complete Extraction Notes is more useful than a `true` with
  silent gaps.
