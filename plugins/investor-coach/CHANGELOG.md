# Changelog — idc

This file holds the cumulative version history that previously lived in
`plugin.json`'s `description` field. The description is now a one-sentence
summary (per HD-004); historical detail lives here.

For the marketplace-facing summary, see `plugin.json`.

---

## Cumulative history (through v0.5.0)

> Migrated from `plugin.json` description, 2026-05-23.

Investor Deck Coach — facilitates Sequoia-style pitch deck creation through guided conversation. Stage-aware (angel, pre-seed, seed, Series A, Series B). Produces evidence-backed market research, rigorous financial modelling, adversarial review, customer-branded PowerPoint + HTML decks, Excel + HTML financial models, and a live rehearsal drill. v0.4.0: aligns paths and artifacts with the production convention proven on the sulis pre-seed deck — numbered phase folders (02-research/, 03-financials/, 04-narrative/, 05-adversarial/, 06-verification/), multi-file journal/, ADVERSARIAL_REVIEW.md, VERIFICATION_REPORT.md. Adds three new investor-facing HTML deliverables at .pitch root: PITCH.html (long-form scrollable web pitch for DocSend-style sharing, distinct from the Reveal.js slide deck), FINANCIALS.html (investor-facing financial summary, distinct from the internal 03-financials/DASHBOARD.html), REVIEW.html (investor-facing adversarial-review summary). Three new build scripts (build_web_pitch.py, build_investor_financials.py, build_review_html.py). v0.3.3: FE-11 (Inference Over Interrogation). v0.3.2: cites Founder English (FE-01..FE-10) at plugins/srd/references/founder-english.md. v0.5.0: journal-entry filenames now use ISO 8601 UTC compact timestamps (journal/YYYY-MM-DDTHHMMSSZ-{topic}.md) instead of date-only stamps. Closes user feedback that same-day journal entries on the same topic collide. Affects brand-discovery, discovery, rehearsal, adversarial-review, build-deck, pitch-templates and the investor-deck-coach agent's handover entry.
