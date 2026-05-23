---
name: code-health
description: Use when the founder wants to know if everything is OK — runs a comprehensive code-health check across multiple tiers (safety, works, reliability, readability, maintainability) and produces one prioritised report. Read-only; never modifies code.
---

# Code Health

The one comprehensive check. Walks seven tiers of code health in order, runs
the wired tiers, and produces a single tiered report so the founder sees
the most-load-bearing thing to fix first.

In v1, only **tier 5 (Understandable)** is wired — invokes
`/sulis:check-readability`. Other tiers render as "not yet checked" with
the planned-release noted. The framework establishes the report shape; tiers
slot in as their underlying skills ship.

The audit is read-only. It NEVER modifies code. Findings include rename and
refactor suggestions; they are *advisory text only*.

## The seven tiers

| Tier | Founder question | v1 status |
|---|---|---|
| 1 Exists | Does it build? Do the tests run at all? | ⏳ planned |
| 2 Safe | Could anyone be harmed? (security, leaked credentials, PII) | ⏳ planned |
| 3 Works | Do the tests pass? Does it do what it should? | ⏳ planned |
| 4 Survives | Does it handle failure gracefully? | ⏳ planned |
| **5 Understandable** | **Can a new person read it?** | ✅ wired (`/sulis:check-readability`) |
| 6 Evolves | Can we change it without breaking things? | ⏳ planned |
| 7 Polished | Performance, accessibility, design quality | ⏳ deferred |

Tier registry lives at `references/tier-registry.md` — adding a wired tier
is a registry update + a tier-skill, not a SKILL.md rewrite.

## Two modes

- **Founder mode (default).** Tiered report in plain English with FE-06
  applied. Per-tier traffic-light. Drill-down only for failed tiers. No
  internal IDs in chrome.
- **Operator mode (`--raw`).** Tiered JSON envelope with per-tier raw
  findings. For piping or for engineers wanting machine-readable output.

## Scope auto-detection

Same as `/sulis:check-readability`: PR-scope (local diff vs auto-detected
base branch) or codebase-scope. Override with `--scope`, `--base-branch`,
or `--pr-number`. The orchestrator passes the resolved scope to each wired
tier.

## When invoked

1. **Resolve scope.** Auto-detect PR vs codebase. Echo it:
   *"Checking everything on this branch's changes (comparing against main)."*
   or
   *"Checking the whole codebase — 312 files."*

2. **Run the orchestrator.**
   ```bash
   python3 plugins/sulis/skills/code-health/scripts/orchestrator.py \
     [--scope auto|pr|codebase] \
     [--pr-number N] \
     [--raw]
   ```

3. **Translate to founder English** (founder mode). For each tier:
   - **Wired tier with findings:** translate via the tier skill's own
     translation (check-readability has its own `founder-translation.md`).
     code-health does not re-translate; it composes.
   - **Wired tier passing:** show `✅ {Tier name}: Clear`.
   - **Stubbed tier:** show `⏳ {Tier name}: not yet checked (planned)`.

4. **Present the CHECKUP.** Use this template:

   ```
   🩺 Code Health — {scope description}

   At a glance:
     Tier 1 — Exists:         ⏳ not yet checked (planned)
     Tier 2 — Safe:           ⏳ not yet checked (planned)
     Tier 3 — Works:          ⏳ not yet checked (planned)
     Tier 4 — Survives:       ⏳ not yet checked (planned)
     Tier 5 — Understandable: 🟡 needs attention (1 file)
     Tier 6 — Evolves:        ⏳ not yet checked (planned)
     Tier 7 — Polished:       ⏳ deferred

   What needs your attention:

   🟡 Tier 5 — Understandable
     The work-package-lib file is doing too many jobs (`_wpxlib.py`).
     It's 3,429 lines covering 25 distinct concerns. Worth splitting into
     focused files when convenient.

   What's not yet checked:

   Tier 1-4, 6, 7 checks are planned for upcoming releases. They aren't
   silently passing — they aren't running. When more tier-skills ship,
   they'll be wired in automatically.
   ```

5. **Handle shortcuts** the founder might ask for:
   - **Safe shortcuts:** `[N] drill into tier N findings`,
     `[N] open file at finding`. Echo-before-act.
   - **No fix shortcut.** This skill never modifies code (see Gotcha #4).

## Gotchas

- **Stubbed tiers must look different from passing tiers.** A founder
  glancing at 6 ✅ green lights might think everything passed — but most
  of those were "we didn't look." The presentation template uses
  `⏳ not yet checked (planned)` distinct styling vs `✅ Clear` and
  `🟡 needs attention` / `❌ failed`.
  *Source: canonical partial-coverage UX failure.*

- **Don't fabricate verdicts for stubbed tiers.** Tempting to mark them
  "presumed pass" so the report looks cleaner. They're NOT checked.
  Honesty matters more than visual tidiness.
  *Source: founder-facing-conventions Rule 5 (explain what + what-to-do — applies to "I didn't check" too).*

- **Tier-gating is forward-architecture, not active in v1.** The TDD's
  ADR-002 specifies hard-stop on tier 1/2 critical findings. In v1 those
  tiers aren't wired, so the rule literally never fires. When tiers 1+2
  ship, gating activates. Documented here so future readers don't think
  the gating logic is broken.
  *Source: this skill's scope — 1/7 tiers wired in v1.*

- **Founder might assume code-health can fix things.** Same destructive-
  action ambiguity as check-readability. The wrapper composes read-only
  audits; it never modifies code. Rename, refactor, split — those are
  separate engineering actions requiring explicit founder consent.
  *Source: founder-facing-conventions Rule 3; check-readability gotcha #5 prior art.*

- **Tier names are founder-vocab; operator IDs must stay hidden.** Tier
  names (Exists, Safe, Works, Survives, Understandable, Evolves, Polished)
  were chosen to be founder-readable. Operator-side primitive IDs (MEA-04,
  CQ-01, SEC-07) must NEVER appear in founder mode. The tier-registry
  maps operator IDs to founder names for translation.
  *Source: founder-translation.md pattern from check-readability.*

## Vocabulary

- **code-health** — the umbrella property this skill measures.
  Multi-tier well-formedness of a codebase.
- **tier** — a Maslow-for-code level (1 through 7). Disambiguates from
  `idc:market-research`'s research-source tiers (Tier 1 / Tier 2 sources)
  and `sea:code-review`'s report tiers (founder-tier / technical-tier).
- **checkup** — the report this skill produces (tiered traffic-light +
  findings). The output file is `CHECKUP.md` per session/run.
- **tier-gating** — the rule that lower-tier failures de-prioritise higher
  tiers. Forward-architecture per `.architecture/sulis-checkup/TDD.md`
  ADR-002; no-op in v1 since tiers 1+2 aren't wired.
- **not-yet-checked** — explicit state for tiers without underlying skills
  wired. Distinct from "passed" and "failed." Always renders with `⏳`.
- **wired tier** — a tier whose underlying skill exists and is invoked by
  the orchestrator. v1: tier 5 only.

## When to invoke this skill

- Founder asks "is everything OK?", "give me a comprehensive check",
  "is my code in good shape?", "is the codebase healthy?"
- Founder is preparing for a major release or external review and wants
  a full picture
- Founder is onboarding and wants to understand the codebase's overall
  state across multiple dimensions

## When NOT to invoke this skill

- Founder asks specifically "is the code readable?" — use
  `/sulis:check-readability` directly (single tier; cleaner output;
  faster).
- Founder asks about a specific other tier we have a single-tier skill
  for (when those ship: `/sulis:check-security`, `/sulis:check-tests`,
  etc.) — use the single-tier skill.
- Founder wants to fix something — this skill suggests; it doesn't act.
  Take suggestions into a real engineering session.
- Operator wants per-WP detail or technical findings — use the
  underlying skills directly (in `--raw` mode if needed).
