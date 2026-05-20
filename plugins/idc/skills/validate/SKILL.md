---
name: validate
description: >
  Final completeness check for the Investor Deck Coach. Runs an
  eight-perspective spiral over all artifacts in .pitch/{slug}/ — Sequoia
  coverage, financial rigor, narrative composition, visual layout,
  adversarial rebuttal coverage, claim-to-proof traceability, term
  consistency, brand application. Up to three fix-as-you-go passes. Emits
  VERIFICATION_REPORT.md with PASS or GAPS_FOUND verdict.
user_invocable: true
---

# Validate

When invoked, run multi-perspective verification across all pitch
artifacts and produce `VERIFICATION_REPORT.md`. This is the
pre-handoff check — the verdict determines whether the pitch is
stage-conformant and ready for delivery.

## When to invoke

- After `/idc:build-deck` and (optionally) `/idc:rehearsal` are
  complete.
- Before the founder takes the deck into a real partner meeting.
- Re-run after fixes if a previous pass returned GAPS_FOUND.

## When NOT to invoke

- Before the deck is built — there's not yet a deliverable to
  validate.
- Mid-build — wait until the build completes.

---

## Eight perspectives

Each perspective applies a specific reference standard. A perspective
returns PASS if all its checks pass, GAPS if any fail.

### 1. Sequoia spine coverage (SQ-)

Verify:

- All ten spine slides present (SQ-01 through SQ-10) in order
- Each slide answers a named investor question (ND-01)
- Stage variant applied per `PITCH.yaml.stage` (SQ-V1..V4)
- Slide count between 10 and 15 (SQ-14)
- Speaker notes for SQ-04 contain the pause prompt (SQ-12)

### 2. Financial rigor (FN-)

Verify against `financial-rigor-standard.md` checklist (FN-01..16).
Each rule passes or fails. Common failures:

- TAM/SAM/SOM lacking bottom-up triangulation (FN-04)
- Numbers without proof-points (FN-06)
- Missing pre-mortem (FN-10)
- Hockey-stick projections with no assumptions (FN-09)
- Vanity metrics on financials slide (FN-12)

### 3. Narrative composition (ND-)

Verify against `deck-narrative-standard.md` checklist (ND-01..11).
Common failures:

- Topic-label slide titles instead of conclusions (ND-02, ND-04)
- Missing SCQA on argument slides (ND-03)
- Speaker notes > 80 words or in paragraph form (ND-11)
- Prohibited PL words still present (ND-10)

### 4. Visual layout (VD-)

Verify against `visual-design-standard.md` checklist (VD-01..13).
Common failures:

- Chunk count > 5 on any slide (VD-02)
- WCAG AA contrast failure on any pair (VD-09)
- Decorative imagery without stated purpose (VD-13)
- Truncated y-axes without annotation (VD-12)

### 5. Adversarial rebuttal coverage (IO-)

Verify:

- `ADVERSARIAL_REVIEW.md` exists
- Every Weak / None objection has either been addressed in the
  current slides OR explicitly acknowledged as residual risk by the
  founder
- Cross-cutting themes from the report are reflected in the deck
  (e.g., if three objections converged on TAM credibility, the
  market slide has been strengthened)

### 6. Claim-to-proof traceability

Walk every numerical claim in `slides/`, `NARRATIVE.md`, and the
deck deliverables. Verify each:

- Cites a `pp-NNN` in the slide front matter
- The cited `pp-NNN` exists in `proof-points/`
- The `pp-NNN` references a `src-NNN` that exists in `sources/`
- The `src-NNN` has a tier declared

Flag any orphans (claims without proof-points, proof-points without
claims, sources without proof-points).

### 7. Term consistency (CL-06 / ND-09)

Walk every named term in `slides/`, `NARRATIVE.md`,
`MARKET_RESEARCH.md`, and `03-financials/MODEL.yaml`. Verify each term
appears in `GLOSSARY.md` with a single definition and is used
consistently across artifacts.

Common failures:

- Competitor name inconsistencies ("Stripe" vs "Stripe Connect")
- Metric drift ("CAC" used as blended in one place, paid in another)
- Segment boundary drift ("SMB" defined differently across slides)

### 8. Brand application

Verify:

- `BRAND.md` is `page-build-ready: true`
- `brand-assets/tokens.css` and `brand-assets/tokens.json` exist and
  match each other
- Deck (.pptx and .html) uses only colours from tokens.css
- Deck uses only typefaces from type-stack.md
- Financial dashboard (.html) uses the same tokens

---

## Execution

### Step 1: Run all eight perspectives

Run each perspective in sequence. Capture findings into a working
list with severity:

| Severity | Meaning |
|---|---|
| **CRITICAL** | Must address before delivery. Blocks PASS. |
| **SIGNIFICANT** | Should address. Founder may choose to ship anyway with explicit rationale. |
| **MINOR** | Note for future revision. Does not block PASS. |

### Step 2: Fix-as-you-go (up to 3 passes)

For each CRITICAL finding, attempt to fix in-place if mechanical:

- Wrong tier on a source → ask the founder to confirm and update
- Missing proof-point citation → look up the source, add citation
- Term inconsistency → propose the canonical term, update artifacts
- Missing SCQA on an argument slide → draft from the existing
  narrative

For non-mechanical CRITICAL findings (missing financial-rigor
artifact, missing slide), surface to the founder with the relevant
skill recommendation (e.g., "FN-04 fails — TAM has top-down only,
no bottom-up. Return to `/idc:market-research` to add the bottom-up
math.").

After fixes, re-run the affected perspective. If a perspective still
fails after three passes, escalate to manual review (a fourth
pass would indicate either structural issue or fix loop).

### Step 3: Compose VERIFICATION_REPORT.md

Use the template. Sections:

1. Per-perspective verdict table
2. Per-rule check tables (SQ, FN, ND, VD, IO, traceability, terms, brand)
3. Findings (sorted by severity)
4. Overall verdict (PASS or GAPS_FOUND)
5. Pass history (passes 1, 2, 3 with finding counts)

### Step 4: Verdict

- **PASS:** All perspectives PASS. No CRITICAL findings open. The
  pitch is stage-conformant and ready for delivery.
- **GAPS_FOUND:** ≥1 perspective failed after three passes. Report
  enumerates open CRITICAL findings and recommended skills to invoke.

### Step 5: Closing summary

If PASS, deliver a closing summary to the founder:

- Confirm PASS
- Note the two things about this deck that landed strongest
- Note the single thing you would continue to refine for future
  rounds
- If a rehearsal date is scheduled, surface it

If GAPS_FOUND, deliver:

- The specific perspectives that failed
- The CRITICAL findings still open
- The recommended skills to invoke
- The agent will pause until the founder authorises the next step

---

## Refusals

Refuse if:

- The founder asks to downgrade a CRITICAL to SIGNIFICANT to enable
  PASS → "I won't tilt the severity. If we're shipping despite a
  CRITICAL, that's a founder-acknowledged decision and goes in the
  report — not a severity hack."
- The founder asks to skip a perspective → "All eight protect a
  different failure mode. The point is coverage, not speed."

---

## Coaching gates

- **Show, don't tell:** for each finding, cite the specific rule and
  the specific artifact line — not "this is wrong."
- **Offer alternatives:** every CRITICAL finding includes a
  recommendation (fix in-place or invoke specific skill).
- **Respect iteration:** GAPS_FOUND is not failure. It's signal.
  Fix what's actionable, run again.

---

## Gotchas

- **Don't fix CRITICAL findings without founder visibility.** Some
  fixes (e.g., revising a TAM claim) have business consequences.
  Surface before patching.
- **Don't ship MINOR findings as PASS without recording them.**
  MINORs are future revision targets — the report captures them so
  the next round starts ahead.
- **Don't run validate as a one-shot.** The fix-as-you-go pattern
  catches issues in passes 2–3 that wouldn't surface in a single
  read.
- **Don't infinite-loop the passes.** After three passes with no
  meaningful progress, escalate.

---

## Output checklist

- [ ] All eight perspectives run
- [ ] Findings classified by severity
- [ ] CRITICAL items addressed or explicitly acknowledged
- [ ] Up to 3 fix-as-you-go passes completed
- [ ] `VERIFICATION_REPORT.md` written from template
- [ ] Verdict: PASS or GAPS_FOUND
- [ ] Closing summary delivered to founder
- [ ] Journal entry written
- [ ] If PASS: no next skill required; engagement ready for delivery
- [ ] If GAPS_FOUND: recommended skills proposed
