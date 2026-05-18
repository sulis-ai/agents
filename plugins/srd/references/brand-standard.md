# Brand Identity Standard

<!-- summary -->

BRAND.md is a structured markdown document that gives AI tools — coding agents, copy
generators, design tools — the brand context they need to produce consistent, on-brand
output. It is the brand counterpart to DESIGN.md (visual identity) and AGENTS.md
(behaviour).

A BRAND.md file has two layers: a **YAML frontmatter** block (machine-readable brand
signals: quantified voice dimensions, power words, avoided vocabulary, distinctive
assets, extraction provenance) and a **Markdown body** (human-readable rationale:
identity, positioning, voice guidance with corpus-cited examples, microcopy patterns).

Six quality standards govern a valid BRAND.md:

- **BR-01** — Golden Circle Integrity: identity is discovered WHY → HOW → WHAT, never reversed
- **BR-02** — Competitor Substitution Test: every identity claim fails when a competitor name is substituted
- **BR-03** — Distinctive Asset Strategy: 3–7 Primary Distinctive Assets classified as Convention or Deliberate Distinction
- **BR-04** — Voice Quantification: tonal dimensions expressed as numeric scores, not labels alone
- **BR-05** — Corpus Provenance: all claims traceable to a named source or marked as asserted
- **BR-06** — Cross-Artifact Coherence: BRAND.md claims align with DESIGN.md tokens and TONE_OF_VOICE.md if those artifacts exist

A BRAND.md is **page-build-ready** when it has: a completed YAML block, all required
Markdown sections, BR-01 through BR-05 satisfied, and no unresolved
`[ASSERTED — not corpus-verified]` markers in the voice or identity sections.

<!-- detail -->

---

## Provenance

This standard synthesises:

- Google Labs DESIGN.md specification (April 2026) — two-layer machine-readable format
- thebrand.md open standard — AI-readable brand documentation
- Tria Design Lifecycle methodology — Golden Circle Integrity (IDC-01), Competitor
  Substitution Test (IDC-02), Distinctive Asset Strategy (IDC-03)
- Honest Mobile BRAND.md extraction — quantified voice dimensions, corpus provenance,
  register-specific microcopy patterns

This is practitioner knowledge, not peer-reviewed research.

---

## Severity Convention

| Severity | Meaning |
|----------|---------|
| **MUST** | Non-negotiable. A BRAND.md that violates this is not page-build-ready. |
| **SHOULD** | Default. Deviation requires explicit justification in the Extraction Notes section. |
| **MAY** | Permitted option. Use judgement. |

---

## Section 1: File Format

### BR-FORMAT-01: Two-Layer Architecture

A BRAND.md file MUST consist of two layers in this order:

1. **YAML frontmatter** — delimited by `---` fences, containing machine-readable brand signals
2. **Markdown body** — human-readable guidance, organised by `##` sections

The file MUST be valid Markdown that renders correctly on GitHub and in standard editors
without any pre-processing step.

### BR-FORMAT-02: File Location

| Context | Canonical path |
|---------|---------------|
| Organisation-level brand | `product/organization/BRAND.md` |
| Product sub-brand | `product/{product-name}/BRAND.md` |
| Engagement deliverable | `{engagement}/web-design/BRAND.md` |

A product BRAND.md MAY inherit from an organisation BRAND.md. Where inheritance is used,
the product file MUST declare `inherits-from:` in its YAML frontmatter and MUST document
explicitly which fields it overrides.

---

## Section 2: YAML Frontmatter Schema

### Required Fields

```yaml
---
name: "Organisation or brand name"
version: "1.0.0"
extraction-date: "YYYY-MM-DD"
extraction-confidence: low | medium | high
page-build-ready: true | false

brand-voice:
  tone:
    formal-casual: -3..+3      # negative = formal, positive = casual
    warm-clinical: -3..+3      # negative = clinical, positive = warm
    direct-conversational: -3..+3  # negative = conversational, positive = direct
  person:
    dominant: first-plural | second-person | third-person | brand-as-subject
    secondary: first-plural | second-person | third-person | brand-as-subject | none
  sentence-length: short | medium | long | mixed
  question-usage: rare | occasional | frequent
  exclamation-frequency: rare | occasional | frequent
  oxford-comma: yes | no
  em-dash: yes | no
  jargon-level: low | medium | high
  claim-density: low | medium | high
  capitalisation:
    headings: sentence-case | title-case
    buttons: sentence-case | title-case
    navigation: sentence-case | title-case
---
```

### Optional Fields

```yaml
# Corpus provenance — REQUIRED if the file was extracted from existing content
corpus:
  pages-crawled: N
  word-count: ~XXXX
  i18n-files: N
  sources:
    - url: "https://example.com"
      pages: ["homepage", "about", "product-page"]

# Vocabulary
power-words:
  - word-or-phrase

avoided-vocabulary:
  - "word-or-phrase"

# Inheritance (product sub-brands)
inherits-from: "../organization/BRAND.md"
overrides:
  - field: brand-voice.tone.formal-casual
    value: 1
    reason: "Product targets a more casual developer audience"

# Distinctive Assets — REQUIRED for BR-03 compliance
distinctive-assets:
  - name: "Asset name"
    type: convention | deliberate-distinction
    description: "One sentence on what this asset is and its purpose"
```

### Voice Dimension Scale

The numeric scale for tone dimensions is consistent across all BRAND.md files to
enable comparison and inheritance override reasoning:

| Score | Interpretation |
|-------|---------------|
| -3 | Strongly towards the left pole (e.g. very formal) |
| -2 | Moderately towards the left pole |
| -1 | Slightly towards the left pole |
| 0 | Neutral / balanced |
| +1 | Slightly towards the right pole (e.g. slightly casual) |
| +2 | Moderately towards the right pole |
| +3 | Strongly towards the right pole (e.g. very casual) |

Scores are derived from corpus analysis. If the file is asserted (no corpus), all
scores MUST be marked with an `[ASSERTED]` comment in the YAML.

---

## Section 3: Markdown Body Sections

### Required Sections

The following sections MUST appear in the Markdown body of every page-build-ready
BRAND.md. They MUST appear in this order.

#### 3.1 Brand Essence

A single sentence that distils what the brand is and why it exists. This is not a
tagline — it is a positioning anchor for AI tools.

Format: `{Brand} {verb phrase that expresses the WHY} {for whom}.`

Example:
> Honest Mobile exists to prove that a mobile network can be transparent, affordable, and
> good for the planet — for people who are done being taken advantage of.

#### 3.2 Identity (Golden Circle)

Three subsections in strict order. See BR-01.

```markdown
### WHY
One paragraph on the founding belief or frustration that drives the organisation.

### HOW
2–5 differentiating approaches or values-in-action (not marketing language).

### WHAT
Products and services, described from the customer's perspective.
```

#### 3.3 Positioning

One paragraph. Answer: who is this brand for, what does it replace or displace,
and what is the one thing it does better than any alternative?

#### 3.4 Voice & Tone

A table rendering the YAML voice dimensions in human-readable form:

| Dimension | Score | Interpretation |
|-----------|-------|---------------|
| Formal ←→ Casual | **+2 (Casual)** | Explanation of what this means in practice |
| Warm ←→ Clinical | **+2 (Warm)** | ... |
| Direct ←→ Conversational | **+1 (Slightly direct)** | ... |

Followed by a 2–4 sentence narrative that characterises the voice holistically.

#### 3.5 Person & Voice

Describe the dominant and secondary grammatical person with 2–3 verbatim corpus
citations for each. Mark asserted examples with `[ASSERTED]`.

#### 3.6 Do's and Don'ts

Minimum 5 rules. Each rule MUST follow this structure:

```markdown
**N. Rule statement in plain language.**
- **Do:** Positive example
- **Don't:** Negative example
- **Corpus cite:** Verbatim quote — page name
```

If no corpus is available, cite as `[ASSERTED — not corpus-verified]`.

#### 3.7 Vocabulary

Two lists:

- **Power words** — high-frequency, high-impact words and phrases that define the brand voice
- **Avoided vocabulary** — words absent from the corpus (or actively prohibited) with a brief
  note on why each is avoided

#### 3.8 Microcopy Patterns

A table mapping UI contexts to copy patterns and examples:

| Context | Pattern | Examples |
|---------|---------|---------|
| Button labels | ... | ... |
| Hero CTAs | ... | ... |
| Error states | ... | ... |
| Pricing | ... | ... |
| Social proof | ... | ... |

#### 3.9 Extraction Notes

Provenance transparency. MUST include:

- Corpus sources (URLs, page names, word count) — or `[ASSERTED — no corpus]`
- Extraction date
- Extraction confidence (low / medium / high) with justification
- Known gaps (registers not covered, pages not crawled)
- Improvements recommended for future extractions

### Optional Sections

The following sections SHOULD be included when the relevant information is available.
Their omission MUST be noted in Extraction Notes.

| Section | Content |
|---------|---------|
| **Distinctive Assets** | Narrative on each asset, why it is Convention or Deliberate Distinction, and usage guidance |
| **Registers** | How voice shifts across marketing, FAQ, support, press, legal, and error contexts |
| **Imagery & Photography** | Subject matter, photographic style, illustration approach, aspect ratios |
| **Iconography** | Library used, style (stroke / filled / duo-tone), sizing conventions, custom assets |
| **Logo** | Asset table: file path, colourway, usage context for each logo variant |
| **Copy Examples by Context** | Verbatim examples for hero headings, CTAs, microcopy, pricing, social proof, support |

---

## Section 4: Quality Standards

### BR-01: Golden Circle Integrity

**Severity:** MUST

The Identity section MUST be structured WHY → HOW → WHAT. Reversing this order
produces rationalised identity, not discovered identity — the WHY becomes a
post-hoc justification for existing products rather than the founding belief that
drives them.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Write the WHY section first, without looking at product pages. Ask: what did the founder believe was broken, unfair, or missing in the world? Then derive HOW (the differentiating approach that flows from that belief) and WHAT (products that express the HOW). |
| **Anti-Pattern** | Starting from "we make X product" and working backwards to a mission statement. A brand whose WHY sounds like "to provide excellent service and great value" has reversed the Golden Circle. |
| **How to verify** | The WHY section contains a belief or frustration, not a product description. The HOW section contains approaches and values, not features. The WHAT section contains products and services, not mission language. |

---

### BR-02: Competitor Substitution Test

**Severity:** MUST

Every claim in the Identity and Positioning sections MUST fail when the brand name is
replaced with a named direct competitor. A claim that passes with any named competitor is
generic and MUST be rewritten.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | After drafting each identity claim, substitute the brand name with 2–3 direct competitors. If the sentence still reads as true or plausible, the claim is too generic. Rewrite until it fails for all named competitors. |
| **Anti-Pattern** | "Honest Mobile believes in transparency and fair pricing." → substitute "EE" → "EE believes in transparency and fair pricing." This passes, so it is invalid. |
| **Valid example** | "Honest Mobile believes your mobile network has been taking advantage of you — hiking prices annually, burying you in contracts, and ignoring the planet — and exists to prove a better model is possible." Substituting "EE" or "O2" produces an implausible claim. |
| **How to verify** | Manually substitute 2–3 competitor names into each identity and positioning claim. All substitutions must produce implausible or absurd results. A clean pass (all substitutions sound fine) is treated as an anti-pattern, not a pass. |

---

### BR-03: Distinctive Asset Strategy

**Severity:** SHOULD

The BRAND.md MUST identify 3–7 Primary Distinctive Assets and classify each as either:

- **Convention** — deliberately follows category norms (Jakob's Law: users expect this)
- **Deliberate Distinction** — intentionally deviates to build recall and recognition

| Attribute | Detail |
|-----------|--------|
| **In Practice** | List the brand's most recognisable elements (logo mark, wordmark, signature colour, typography choice, tone of voice register, imagery style, tagline structure). For each, decide: does this conform to category convention (Convention) or does it stand out from category norms (Deliberate Distinction)? A brand with zero Conventions is incoherent (fights users' mental models on every dimension). A brand with zero Deliberate Distinctions is invisible. |
| **Anti-Pattern** | Listing assets without classifying them. Classifying everything as Deliberate Distinction. Listing fewer than 3 assets (insufficient to characterise the brand) or more than 7 (unable to prioritise). |
| **How to verify** | The `distinctive-assets` YAML field contains 3–7 entries. Each entry has a type field of `convention` or `deliberate-distinction`. The Distinctive Assets section (if present) explains the reasoning. |

---

### BR-04: Voice Quantification

**Severity:** MUST

Tonal dimensions MUST be expressed as numeric scores (see YAML schema, Section 2),
not labels alone. Scores MUST be derived from corpus analysis where a corpus exists,
or explicitly marked `[ASSERTED]` where they are not.

| Attribute | Detail |
|-----------|--------|
| **In Practice** | For each dimension (formal-casual, warm-clinical, direct-conversational), read 20+ sentences from the corpus. Place each on the -3 to +3 scale. Average the placements. This produces a defensible score, not an opinion. |
| **Anti-Pattern** | Describing voice as "warm and casual" without a score. Assigning scores without a corpus and not marking them `[ASSERTED]`. Using different scales for different documents (prevents inheritance reasoning). |
| **How to verify** | All three tone dimensions have numeric scores. If corpus data exists, `extraction-confidence` is set. If no corpus, all scores carry `[ASSERTED]` markers. |

---

### BR-05: Corpus Provenance

**Severity:** MUST

Every claim about voice, vocabulary, or microcopy patterns MUST be traceable to either:

1. A verbatim corpus citation (page name + quote), or
2. An explicit `[ASSERTED — not corpus-verified]` marker

| Attribute | Detail |
|-----------|--------|
| **In Practice** | Every Do's and Don'ts rule must have a corpus cite. Every power word must appear in the corpus. The Extraction Notes section must list all sources and their coverage. |
| **Anti-Pattern** | Writing "the brand uses a warm, conversational tone" without a single corpus quote. Inventing examples in Do/Don't rules without marking them as asserted. Omitting Extraction Notes entirely. |
| **How to verify** | Every Do's and Don'ts entry has a `Corpus cite:` line. The Extraction Notes section is present and names all sources. Any asserted content is explicitly marked. |

---

### BR-06: Cross-Artifact Coherence

**Severity:** SHOULD

Where a DESIGN.md or TONE_OF_VOICE.md exists alongside a BRAND.md, pairwise consistency
checks MUST pass:

| Pair | Check |
|------|-------|
| BRAND.md ↔ DESIGN.md | Every brand colour in the Imagery section has a corresponding semantic token in DESIGN.md |
| BRAND.md ↔ TONE_OF_VOICE.md | Brand personality dimension scores align with TONE_OF_VOICE.md voice characteristics |
| BRAND.md ↔ USAGE_GUIDELINES.md | Every visual brand element mentioned in BRAND.md has a usage rule in USAGE_GUIDELINES.md |

| Attribute | Detail |
|-----------|--------|
| **In Practice** | After updating BRAND.md, run a pairwise check against any co-located design artifacts. Flag contradictions as issues. |
| **Anti-Pattern** | A BRAND.md that describes the brand as "minimal and restrained" while the co-located DESIGN.md shows 12 brand colours and decorative illustration. |
| **How to verify** | Manually cross-reference each pair. No contradictions between documents. If any artifact is absent, note it in Extraction Notes. |

---

## Section 5: Anti-Patterns

| ID | Anti-Pattern | Violated Standard |
|----|-------------|------------------|
| AP-BR-01 | **Generic identity** — identity claims pass the competitor substitution test | BR-02 |
| AP-BR-02 | **Reversed Golden Circle** — starting from WHAT and rationalising WHY | BR-01 |
| AP-BR-03 | **Label-only voice** — "warm and friendly" with no numeric scores or corpus grounding | BR-04 |
| AP-BR-04 | **Provenance-free claims** — voice or vocabulary assertions with no corpus citations or ASSERTED markers | BR-05 |
| AP-BR-05 | **Asset-free brand** — no Distinctive Asset Strategy; visual and verbal identity cannot be evaluated for distinctiveness | BR-03 |
| AP-BR-06 | **Stale extraction** — `extraction-date` more than 12 months old with no re-extraction note | BR-05 |
| AP-BR-07 | **Inherited without override reasoning** — sub-brand inherits from organisation BRAND.md but does not document why overrides were made | BR-FORMAT-02 |

---

## Section 6: page-build-ready Signal

The `page-build-ready: true` flag in YAML frontmatter is a machine-readable signal that
the BRAND.md is ready for consumption by AI tools.

A BRAND.md MUST NOT be marked `page-build-ready: true` unless all of the following are satisfied:

- [ ] YAML frontmatter is complete (all required fields present)
- [ ] All required Markdown sections are present (3.1–3.9)
- [ ] BR-01 (Golden Circle Integrity) passes
- [ ] BR-02 (Competitor Substitution Test) passes
- [ ] BR-04 (Voice Quantification) passes — scores present and corpus-grounded or marked ASSERTED
- [ ] BR-05 (Corpus Provenance) passes — no unresolved provenance gaps in required sections
- [ ] No `[TODO]` or `[PENDING]` markers in required sections

BR-03 (Distinctive Assets) and BR-06 (Cross-Artifact Coherence) are SHOULD requirements.
Their absence does not block `page-build-ready: true` but MUST be documented in
Extraction Notes.

---

## Section 7: Relationship to Other Artifacts

```
IDENTITY.md         ← upstream: discovered WHY/HOW/WHAT (Golden Circle)
    ↓
BRAND.md            ← this document: strategic expression of identity
    ↓           ↓
DESIGN.md     TONE_OF_VOICE.md   ← downstream: visual + verbal implementation
    ↓
USAGE_GUIDELINES.md              ← downstream: application rules
```

BRAND.md sits between identity discovery and design/voice implementation. It is the
contract that downstream tools consume. Changes to BRAND.md cascade to DESIGN.md and
TONE_OF_VOICE.md via BR-06 coherence checks.

---

## Version History

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-04-30 | Initial release |
