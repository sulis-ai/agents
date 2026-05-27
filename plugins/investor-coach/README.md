# Investor Deck Coach (`investor-coach`)

A Claude Code plugin that coaches founders through producing an evidence-backed,
Sequoia-conformant pitch deck — branded in the customer's identity, with rigorous
market research, defensible financial modelling, adversarial review, and a live
rehearsal drill.

## What it does

The plugin runs a guided, one-question-at-a-time facilitation across nine phases:

1. **Orientation** — founder, stage, ask, audience
2. **Discovery** — what's changed, what you do, traction, team
3. **Brand Discovery** — extract or propose the brand applied to all deliverables
4. **Market Research** — evidence-backed TAM/SAM/SOM and competitive landscape
5. **Financial Modelling** — stage-appropriate unit economics and projections
6. **Narrative Synthesis** — Sequoia structure + Pyramid + SCQA per slide
7. **Adversarial Sweep** — in-character investor objections and rebuttal grading
8. **Design & Build** — branded PowerPoint and HTML deck
9. **Rehearsal** — timed delivery and mock Q&A

## Deliverables

Written to `.pitch/{project}/` in the user's repository. As of v0.4 the
layout uses numbered phase folders and adds three investor-facing HTML
pages at root.

### Root — founder + investor-facing

| File | Purpose |
|---|---|
| `PITCH.html` | **Long-form scrollable web pitch** for DocSend-style sharing. Distinct from the presenter deck. |
| `FINANCIALS.html` | **Investor-facing financial summary** page (clean, focused). Distinct from the internal phase-3 dashboard. |
| `REVIEW.html` | **Investor-facing adversarial-review summary** page. Distinct from the working `ADVERSARIAL_REVIEW.md`. |
| `PITCH.yaml` | Project metadata, stage, ask. |
| `BRAND.md` + `brand-assets/` | Customer brand (extracted or proposed); tokens drive every visual deliverable. |
| `DISCOVERY.md` | Founder + company context. |
| `GLOSSARY.md` | Locked vocabulary. |
| `journal/YYYY-MM-DD-{topic}.md` | Multi-file facilitation record (one file per session/topic, not a single rolling file). |

### Phase folders — working artifacts

| Folder | Contents |
|---|---|
| `02-research/` | `MARKET_RESEARCH.md` + `sources/` + `proof-points/` — evidence dossier with tiered sources. |
| `03-financials/` | `MODEL.yaml` (source of truth) + `MODEL.xlsx` (Excel) + `DASHBOARD.html` (internal dashboard) + `FINANCIAL_SUMMARY.md`. |
| `04-narrative/` | `NARRATIVE.md` + `slides/NN-*.md` + `DECK.pptx` (PowerPoint) + `DECK.html` (Reveal.js presenter deck) + `speaker-notes.md`. |
| `05-adversarial/` | `ADVERSARIAL_REVIEW.md` — investor objections and mitigation paths. |
| `06-verification/` | `VERIFICATION_REPORT.md` + `REHEARSAL_NOTES.md`. |

Every numerical claim in any artifact is traceable to a proof-point in
`02-research/proof-points/`, and every proof-point to a tiered source in
`02-research/sources/`.

## Stage-awareness

The plugin adapts to the funding stage captured in `PITCH.yaml`:

| Stage | Financial horizon | Primary emphasis |
|---|---|---|
| Angel / Pre-seed | Thesis + market signal | Team, vision, founder credibility |
| Seed | 12-month bottom-up | Pilot data, path to PMF |
| Series A | 24-month + cohort | Early unit economics, retention |
| Series B | 36-month + sensitivity | Scaled unit economics, sales efficiency |

## Skills

| Slash command | Phase | Output |
|---|---|---|
| `/investor-coach:discovery` | 1–2 | `DISCOVERY.md`, `PITCH.yaml` |
| `/investor-coach:brand-discovery` | 3 | `BRAND.md`, `brand-assets/` |
| `/investor-coach:market-research` | 4 | `02-research/MARKET_RESEARCH.md`, `sources/`, `proof-points/` |
| `/investor-coach:financial-model` | 5 | `03-financials/MODEL.{yaml,xlsx}`, `03-financials/DASHBOARD.html` |
| `/investor-coach:narrative` | 6 | `04-narrative/NARRATIVE.md`, `04-narrative/slides/*.md` |
| `/investor-coach:adversarial-review` | 7 | `05-adversarial/ADVERSARIAL_REVIEW.md` |
| `/investor-coach:build-deck` | 8 | `04-narrative/DECK.{pptx,html}` + `PITCH.html` + `FINANCIALS.html` + `REVIEW.html` |
| `/investor-coach:rehearsal` | 9 | `06-verification/REHEARSAL_NOTES.md` |
| `/investor-coach:validate` | post-9 | `06-verification/VERIFICATION_REPORT.md` |

## Reference standards

Located in `references/`:

- `sequoia-pitch-framework.md` (`SQ-`) — slide structure, timing, conversation model
- `financial-rigor-standard.md` (`FN-`) — TAM/SAM/SOM, unit economics, projections
- `investor-objection-catalogue.md` (`IO-`) — taxonomy and rebuttal patterns
- `deck-narrative-standard.md` (`ND-`) — Pyramid + SCQA per slide
- `visual-design-standard.md` (`VD-`) — slide layout grounded in cognitive load
- `brand-standard.md` (`BR-`) — brand extraction format
- `brand-proposal-standard.md` (`BP-`) — proposing a brand kit when none exists
- `coaching-without-conflict.md` — facilitation pedagogy
- `cognitive-load.md` (`CL-`) — per-slide load limits
- `content-quality.md` (`CQ-`) — prose rigor
- `critical-thinking-standard.md` — three-phase analytical framework

## Tool requirements

- Python 3.10+
- `pip install python-pptx openpyxl pillow` (prompted on first build)

## Installation

```bash
/plugin marketplace add sulis-ai/agents
/plugin install investor-coach@sulis-ai-agents
```

Then in any repository:

```
/investor-coach:discovery
```

## License

MIT. See repository root.
