# Changelog — sulis-security

This file holds the cumulative version history that previously lived in
`plugin.json`'s `description` field. The description is now a one-sentence
summary (per HD-004); historical detail lives here.

For the marketplace-facing summary, see `plugin.json`.

---

## Cumulative history (through v0.4.0)

> Migrated from `plugin.json` description, 2026-05-23.

Security & Viability Reviewer — runs a 25-primitive codebase viability assessment (security, data protection, code quality, supply chain, infrastructure) via an OODA-spiral methodology. Composes with SEA for hardening and with SRD for requirements-traceable findings. v0.3.2: cites Founder English (FE-01..FE-10) at plugins/srd/references/founder-english.md — every founder-facing chat message AND founder-readable artifact write passes the FE-06 five-point check (strip internal IDs, translate filenames, expand acronyms, strip internal taxonomy, read-aloud test). Lead with outcomes; concrete over abstract; no mechanism narration. v0.3.3: adds FE-11 (Inference Over Interrogation) citation — infer from existing context before asking the founder; never relay a specialist's 'open questions' verbatim. v0.4.0: viability-report filenames now use ISO 8601 UTC compact timestamps (viability-report-YYYY-MM-DDTHHMMSSZ.md) instead of date-only stamps. Closes user feedback that same-day reruns of /sulis-security:codebase-assess collide. Source-field schema in /sea Hardening Deltas updated correspondingly (source: sulis-security:viability-report-{timestamp}#SEC-NN).
