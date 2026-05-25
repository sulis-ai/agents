# Content Quality Standard

<!-- summary -->

Every substantive artifact serves two audiences: humans who need to understand quickly, and agents who need to parse precisely. This standard codifies a **summary + detail** dual-layer pattern and writing craft requirements to serve both.

The **summary** is the distilled essence — a self-sufficient opening a reader can absorb without scrolling. The **detail** is the complete specification — reference content with stable IDs for targeted loading. Summary appears first. Detail follows. The boundary is explicit.

Six requirements govern content quality: structure (CQ-01, CQ-02), craft (CQ-03, CQ-05), readability (CQ-04), and verification (CQ-06). This standard is **cross-cutting** — it applies wherever content is generated, whether specifications, documentation, or handover artifacts.

**Scope boundary:** This standard governs STRUCTURE (summary + detail layout) and CRAFT (rhythm, readability, anti-patterns). It does not govern SUBSTANCE (accuracy, clarity of meaning, completeness, actionability) — that is the responsibility of the domain-specific standard or review process.

<!-- detail -->

---

## Section 1: Summary + Detail Pattern

### CQ-01: Summary Section

Every substantive artifact MUST open with a summary section.

| Attribute | Requirement |
|-----------|-------------|
| **Length** | 10-30% of total artifact length, with a floor of 5 lines and a ceiling of 80 lines |
| **Position** | First in the artifact, before any detailed content |
| **Boundary** | Explicit delimiter: heading, horizontal rule, `<!-- summary -->` / `<!-- detail -->` markers, or blockquote transition |
| **Self-sufficiency** | A reader who reads ONLY the summary can answer three questions: (1) What is this artifact about? (2) What are the key decisions or requirements? (3) What should I do next? |
| **Severity** | MUST |

The summary does not duplicate the detail. It distils. A correct-but-incomplete mental model is the goal.

### CQ-02: Detail Section

Every substantive artifact MUST provide a detail section following the summary.

| Attribute | Requirement |
|-----------|-------------|
| **Content** | Complete specification: formal definitions, requirements with IDs, schemas, tables, examples |
| **Section IDs** | Stable identifiers (e.g., `CQ-01`, `SEC-03`, `§4.2`) that agents can reference for targeted loading |
| **Agent parseability** | Agents must be able to load specific detail sections without processing the entire artifact |
| **Severity** | MUST |

### Exemptions

The following artifact types are exempt from summary + detail separation:

- Artifacts under 50 lines total
- Pure data artifacts (JSON, YAML)
- Changelogs and version history files
- Generated/derived artifacts (indexes, registries)

### Co-Update Rule

When any detail section is substantively modified, the summary MUST be reviewed and updated if affected. Every key claim in the summary must be traceable to a current detail section.

---

## Section 2: Writing Craft Requirements

### CQ-03: Sentence Rhythm Variation

Prose paragraphs MUST NOT contain 3 or more consecutive sentences in the same length band.

| Band | Word Count | Example |
|------|-----------|---------|
| Short | 1-8 words | "This matters." |
| Medium | 9-20 words | "The standard applies to all content-generating outcomes across delivery functions." |
| Long | 21+ words | "When agents produce artifacts that serve both human readers and machine consumers, the structural separation of summary and detail becomes a force multiplier for comprehension." |

**The Provost Principle:** Vary sentence length deliberately. Short sentences punch. Medium sentences carry ideas. Long sentences build momentum through connected thoughts that reward the reader who stays with them. The combination creates rhythm. Monotone kills it.

**Scope:** CQ-03 applies to consecutive prose sentences within a section only. Structured lists (requirements, steps, table rows, enumerated items, anti-patterns) are exempt. The test does not apply across section boundaries.

**Severity:** MUST

### CQ-04: Plain Language Baseline

Prose sections SHOULD meet Flesch-Kincaid Grade Level targets.

| Layer | FK Target | Enforcement |
|-------|-----------|-------------|
| Summary sections | Grade Level ≤ 10 | **BLOCKING** for user-facing artifacts (READMEs, guides, specifications) |
| Summary sections | Grade Level ≤ 10 | **ADVISORY** for technical artifacts (standards, design documents) |
| Detail sections | Grade Level ≤ 14 | **ADVISORY** for all artifacts |

Technical content uses domain-specific polysyllabic vocabulary ("authentication," "observability," "infrastructure") that inflates FK scores regardless of clarity. Advisory scores are reported for trend analysis but do not trigger rewriting.

**Severity:** SHOULD — see enforcement table above for BLOCKING vs ADVISORY by artifact type.

### CQ-05: AI-Tell Anti-Pattern Avoidance

Prose MUST NOT contain recognised AI-generated content markers.

**Forbidden patterns (minimum set, not exhaustive):**

| Category | Examples |
|----------|---------|
| Filler phrases | "it should be noted that," "it is important to," "it is worth mentioning" |
| Excessive hedging | "might potentially," "could possibly," "it may be the case that" |
| Empty emphasis | "truly," "really," "absolutely," "fundamentally" (when adding no meaning) |
| Uniform structure | 3+ consecutive paragraphs with identical sentence count and structure |
| Formulaic transitions | "Let's delve into," "Moving on to," "Now let's explore" |

This list is maintained as a minimum set. New patterns are added as they are identified.

**Severity:** MUST

---

## Section 3: Verification Methods

### CQ-06: Content Quality Verification

Content quality SHOULD be verified before finalising any artifact.

| Check | Method | Applies To | Severity |
|-------|--------|-----------|----------|
| Summary self-sufficiency | Review: "Can you answer the three questions (What? Key decisions? Next action?) from the summary alone?" | Summary sections | MUST |
| Summary-detail consistency | Review: "Does every key claim in the summary trace to a current detail section?" | Summary + detail pairs | MUST |
| Rhythm analysis | Count consecutive same-band sentences in prose paragraphs | All prose | MUST |
| Readability scoring | Flesch-Kincaid Grade Level assessment | All prose | See CQ-04 table |
| Anti-pattern scan | Check for forbidden phrases and structural uniformity | All prose | MUST |

Verification may be manual or automated. Manual review is acceptable when automated tooling is not available.

---

## Section 4: Template Integration

### Marker Convention

Templates use HTML comment delimiters to mark summary and detail boundaries:

```html
<!-- summary -->
[Summary content here]
<!-- detail -->
[Detail content here]
```

These markers are invisible in rendered output and add minimal cognitive overhead.

### Section ID Convention

Detail sections use stable identifiers for targeted loading:

- Requirements: `CQ-01`, `SEC-03`, `FR-07`
- Sections: `§1`, `§4.2`
- Custom: `{ARTIFACT-PREFIX}-{NUMBER}`

---

## Migration Policy

- **New artifacts** MUST comply with this standard immediately upon creation.
- **Existing artifacts** are migrated to summary + detail structure only when they are next modified for substantive reasons. No batch migration.
- **Substantive modification** means changes to content or requirements — not typo fixes, formatting corrections, or cross-reference updates.

---

## References

| Source | Contribution |
|--------|-------------|
| Provost, G. (1985) *100 Ways to Improve Your Writing* | Sentence rhythm variation principle |
| ISO 24495-1:2023 *Plain Language* | Plain language framework |
| Flesch, R. (1948) *A New Readability Yardstick* | Readability formula basis |
| Kincaid, J.P. et al. (1975) *Derivation of New Readability Formulas* | FK Grade Level metric |
| GOV.UK Content Design Manual | Government plain language patterns |

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2026-03-13 | Adapted from content quality framework. Summary + detail dual-layer pattern, 6 requirements (CQ-01 to CQ-06). |

---

*content-quality v1.0.0*
*"Summary for humans. Detail for agents. Rhythm for both."*
