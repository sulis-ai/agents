# Changelog — sulis-security

This file holds the cumulative version history that previously lived in
`plugin.json`'s `description` field. The description is now a one-sentence
summary (per HD-004); historical detail lives here.

## v0.7.0 — 2026-05-25 — [DEPRECATED]

**This plugin is consolidated into `sulis` at v0.40.0 as the fourth and
final Phase 3 consolidation of the change-as-primitive build.**

Authored via `consolidate-into-sulis` v0.1.2 (with the move-then-sweep
ordering fix). Single combined commit:

- `bdea2e8` — steps 2-4/5 combined — 1 skill moved (codebase-assess —
  already-DEPRECATED, kept name); 1 agent moved (security-reviewer);
  1 reference moved (viability-framework.md). bulk_rewrite.py applied
  52 substitutions across 32 files. 3 manual edits for narrative
  primitive-ID shorthand and the README [DEPRECATED] listing. **No
  fix-forward commits needed** — the v0.1.2 move-then-sweep ordering
  discipline prevented the bug that bit twice during the sea run.
- (this commit) — step 5/5 — wrap-up: this plugin marked DEPRECATED;
  sulis bumped to v0.40.0; marketplace.json updated.

Plugin shell preserved for marketplace compatibility. No shim skills
written. The `/sulis:codebase-assess` skill is itself DEPRECATED
(superseded by `/sulis:code-health`) but remains callable through its
deprecation window per its original retirement schedule.

### Phase 3 complete

This is the fourth and final Phase 3 plugin consolidation:

- sulis-context → sulis (v0.35.0) ✅
- srd → sulis (v0.37.0) ✅
- sea → sulis (v0.38.0) ✅
- sulis-security → sulis (v0.40.0) ✅ ← HERE

Phases 4-7 of the change-as-primitive build remain.

For the marketplace-facing summary, see `plugin.json`.

---

## v0.6.0 — 2026-05-24

**[DEPRECATED] banner applied.** sulis v0.22.0+ check-* tier framework
crossed the ≥ 95% parity threshold (96% — 24 of 25 primitives match
codebase-assess) per the cross-validation ledger at
`plugins/sulis/skills/code-health/tests/cross_validation/expected_divergence.md`.

### Files modified

- `plugins/sulis-security/skills/codebase-assess/SKILL.md`:
  - Description prefixed with `[DEPRECATED — use /sulis:code-health]`
  - Migration path documented (founder-facing audits → /sulis:code-health;
    operator JSON → --raw on check-* skills; hypothesis output → hypotheses[]
    array in --raw output)
  - Retirement schedule clarified: one major release window after banner;
    physical removal follows sulis-concierge → sulis pattern
- `plugins/sulis-security/.claude-plugin/plugin.json`:
  - Description prefixed with `[DEPRECATED]` + parity note
  - Version: 0.5.0 → 0.6.0
- `.claude-plugin/marketplace.json`:
  - sulis-security entry description prefixed with `[DEPRECATED]`
  - Version: 0.5.0 → 0.6.0

### Why [DEPRECATED] now rather than later

Parity verified at 96% in `expected_divergence.md`:

- 24 of 25 primitives ✅ PARITY
- 1 primitive ⏳ EXPECTED-DIVERGENT (CQ-02 full coverage measurement —
  detection-only path works in check-tests; full integration is a
  scheduled follow-up that doesn't require codebase-assess as a fallback)
- 0 UNEXPECTED-DIVERGENT findings

The threshold for advancing from "scheduled for retirement" → [DEPRECATED]
was ≥ 95%. 96% exceeds that. Founders are now directed to /sulis:code-health
as the canonical surface; codebase-assess remains callable as a shim
during the deprecation window.

### What's next

- One major release window where both surfaces are callable (founders
  get [DEPRECATED] banner on codebase-assess + redirect to code-health)
- CQ-02 full-coverage integration (closes the last divergence at full
  100% parity)
- After the window: physical removal of codebase-assess directory +
  sulis-security plugin retirement (only skill in the plugin)

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
