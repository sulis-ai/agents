# Changelog — sulis-security

This file holds the cumulative version history that previously lived in
`plugin.json`'s `description` field. The description is now a one-sentence
summary (per HD-004); historical detail lives here.

For the marketplace-facing summary, see `plugin.json`.

---

## v0.5.0 — 2026-05-24

**Phase 5 of the sulis upsurge plan: scheduled-for-retirement notice.**
codebase-assess remains the canonical depth tool — the deprecation is
deferred pending Phase 2 iteration 2 wrapper build-out + Phase 4
cross-validation parity verification.

### Why not full deprecation now

Per the upsurge plan: "defensible to defer retirement if gaps remain."
Current cross-validation parity (Phase 4 iteration 1 measurement) is 4%
— sulis code-health honestly NOT_ASSESSES 24 of 25 primitives because
the per-tool wrappers (semgrep / gitleaks / trivy / hadolint / testssl /
curl / lizard / jscpd / coverage) are flagged NEW.

Marking codebase-assess [DEPRECATED] in the founder-facing surface today
would mislead — users would be directed to a code-health that doesn't
actually cover the primitives they need.

### What this iteration ships

- SKILL.md: MIGRATION NOTICE added to the `description:` field — informs
  callers that the 25-primitive catalogue is migrating to sulis check-*
  but codebase-assess remains the canonical depth tool through Phase 4
  parity verification.
- Version: 0.4.0 → 0.5.0 (minor — communicates Phase 5 stance without
  changing surface).

### Retirement schedule

- **Now (v0.5.0):** scheduled-for-retirement notice in SKILL.md.
- **Phase 2 iteration 2+ (post-wrapper):** parity climbs as wrappers
  come online. Cross-validation expected_divergence.md tracks per-primitive
  rates.
- **When parity ≥ 95% (verified via Phase 4 iteration 2 compare.py run):**
  add [DEPRECATED] banner to SKILL.md + plugin.json description; redirect
  founders to /sulis:code-health.
- **One major release after [DEPRECATED] banner:** physical removal of
  codebase-assess directory; sulis-security plugin retired.

### Migration roadmap

See `/Users/iain/.claude/plans/eager-crunching-quail.md` Phase 5.

---

## Cumulative history (through v0.4.0)

> Migrated from `plugin.json` description, 2026-05-23.

Security & Viability Reviewer — runs a 25-primitive codebase viability assessment (security, data protection, code quality, supply chain, infrastructure) via an OODA-spiral methodology. Composes with SEA for hardening and with SRD for requirements-traceable findings. v0.3.2: cites Founder English (FE-01..FE-10) at plugins/srd/references/founder-english.md — every founder-facing chat message AND founder-readable artifact write passes the FE-06 five-point check (strip internal IDs, translate filenames, expand acronyms, strip internal taxonomy, read-aloud test). Lead with outcomes; concrete over abstract; no mechanism narration. v0.3.3: adds FE-11 (Inference Over Interrogation) citation — infer from existing context before asking the founder; never relay a specialist's 'open questions' verbatim. v0.4.0: viability-report filenames now use ISO 8601 UTC compact timestamps (viability-report-YYYY-MM-DDTHHMMSSZ.md) instead of date-only stamps. Closes user feedback that same-day reruns of /sulis-security:codebase-assess collide. Source-field schema in /sea Hardening Deltas updated correspondingly (source: sulis-security:viability-report-{timestamp}#SEC-NN).
