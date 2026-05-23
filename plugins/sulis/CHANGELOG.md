# Sulis — Changelog

## v0.6.0 — 2026-05-23

Tier 3 (Works) ships. First regression-detection skill. Wires into the
code-health orchestrator so the comprehensive check now answers "did
anything that was working stop working?" for tests.

### Added

- `skills/check-tests/` — the regression check. Detects test framework
  (pytest, jest, vitest, go test in v1; rspec / mocha planned), runs
  the suite (or reads cached results), compares against a baseline,
  reports newly-failing tests as regressions. Pre-existing failures
  stay invisible — only NEW failures surface. Audience=both with
  `--raw` flag. First skill in the marketplace to introduce a
  **baseline mechanism** at `.checkup/{project}/baseline.json` with
  signature-hash dedup.
  - `SKILL.md` — three-mode invocation (cached / fresh / detection-only)
  - `scripts/regression.py` (~480 lines) — framework detection
    registry; per-framework runners; pytest-verbose parser; baseline
    capture + load; delta computation; flaky-test suppression
  - `references/framework-detection.md` — per-framework signals, run
    commands, parser notes; the extensibility contract for adding new
    frameworks
  - `references/check-tests-known-flaky.md` — marketplace-shared
    flaky-test allow-list; per-project overrides documented
  - `COMPLETENESS_REPORT.md` — five-gate audit trail (15 methodology
    gaps now queued for add-skill v0.6.0)

### Changed

- `skills/code-health/scripts/orchestrator.py` — wires tier 3 to
  invoke `check-tests/scripts/regression.py`. Two important fixes
  along the way:
  - Tier scripts resolve from the **marketplace root** (the orchestrator's
    own location), not the target repo. Enables code-health to operate
    on any target repo while tier-scripts live in the sulis cache.
  - New `extra_args` field on `TierSpec` lets each tier pass tier-
    specific flags. Tier 3 passes `--run --timeout 60` so code-health
    actually executes the test suite (with a tighter timeout than
    check-tests' standalone 120s default to avoid blocking the whole
    checkup).
- `skills/code-health/references/tier-registry.md` — tier 3 now marked
  `wired: true`, `wired_in: "0.6.0"`, `founder_skill: "/sulis:check-tests"`,
  `extra_args: ["--run", "--timeout", "60"]`.

### Dogfood findings

This was dogfood run #4 of `sulis:add-skill v0.4.0`. Four new methodology
gaps queued for add-skill v0.6.0 (joining 11 already queued = 15 total):

- Audit-pattern + baseline-pattern compose (this is the first skill
  combining both)
- Framework-detection-registry mirrors code-health's tier-registry —
  worth naming "registry-driven extensibility" as a pattern
- Real-state fixture limitation: marketplace-as-fixture FAILED for
  check-tests (the marketplace's tests aren't discoverable from
  marketplace root); regression-pattern skills need synthetic fixtures
- Mid-flight Gate 4 P3 refinement (pytest -q → -v) strengthens the
  case for v0.4.0's "misuse cases can surface during Gate 4" allowance

### Verification

- Synthetic fixture (3 tests, 1 deliberate regression): first run
  captured baseline at commit `c04d3c5`; second run (with deliberate
  break) correctly flagged `test_one_passing` as newly-failing while
  the pre-existing `test_three_failing` stayed invisible.
- `--raw` mode validates; orchestrator-compatible `findings` array
  populated only with regressions (newly-failing tests).
- End-to-end via code-health: tier 3 reports `❌ failed (1 item)` with
  the regression detail; tier 5 stays `✅ Clear`; stubbed tiers stay
  visually distinct.

### Open risks accepted at publication

1. **First-run UX may confuse founders expecting immediate regression
   output.** Mitigated by explicit "First run. Captured baseline..."
   message but founders may not read carefully. Revisit if real founder
   reports confusion.
2. **Trigger-condition captures test-design questions** (no
   `sea:test-audit` ships yet). check-tests partially answers; founder
   may not realise. Revisit when sea:test-audit lands.

### Versions

  sulis: 0.5.0 → 0.6.0 (minor — tier 3 wires)
  marketplace: 1.46.0 → 1.47.0

## v0.5.0 — 2026-05-23

First two founder-facing tier skills ship. Establishes the Maslow-for-code
architecture: a 7-tier health framework with the wrapper layer in place even
though only 1 of 7 tiers is wired. Adds the CTS analysis (PG-grounded
two-primitive architecture; verb-first naming convention) as a durable
artefact at `.architecture/sulis-checkup/`.

### Added

- `skills/check-readability/` — the stranger-reader audit. Audits naming
  clarity, module cohesion (kitchen-sink-file detection), and jargon
  density. Auto-detects PR-scope (local diff or `--pr-number`) vs
  codebase-scope. Audience=both with `--raw` flag for operator JSON.
  Audit logic lives directly inside the skill — sulis is becoming the
  everything-plugin per user direction; no `sea:code-hygiene` operator
  skill needed.
  - `SKILL.md` — verb-first trigger; founder/operator modes; gotchas; vocab
  - `scripts/audit.py` — three heuristic families with 4 false-positive-
    refinement iterations (238 → 13 findings on this marketplace)
  - `references/founder-translation.md` — operator → founder vocab table
  - `COMPLETENESS_REPORT.md` — five-gate audit trail

- `skills/code-health/` — the comprehensive code-health wrapper. v1 wires
  tier 5 (invokes check-readability); other 6 tiers render as "not yet
  checked (planned)" — visually distinct from passing tiers. Walks the
  tier registry; renders a tiered CHECKUP report. NO LangGraph yet
  (single-tier means no orchestration logic needed).
  - `SKILL.md` — tier-walking flow; founder/operator modes; tier-gating
    semantics (no-op in v1)
  - `scripts/orchestrator.py` — invokes wired tier-skills via subprocess;
    JSON-merges results; renders markdown for founder mode
  - `references/tier-registry.md` — canonical 7-tier list; wired-status
    flags; operator-ID → founder-vocab translation table; "how to wire a
    new tier" instructions
  - `COMPLETENESS_REPORT.md` — five-gate audit trail

- `.architecture/sulis-checkup/` (durable artefacts from prior conversation)
  - `TDD.md` — SEA-authored architectural design (Maslow tiers, healing
    prototypes, graph architecture, founder surface)
  - `adrs/ADR-001` through `ADR-006` — engine, gating, healing, OODA
    bounding, two-tier report format, SRD gap
  - `CTS-ANALYSIS.md` — Critical Thinking Standard verification of the
    layer model: primitive grounding (two primitives, not three), MECE
    + primitive coverage cross-check (4 additional gaps surfaced),
    verb-first naming convention, 5-argument adversarial test, falsification
    criteria + pre-mortem

### Dogfood findings

This was dogfood run #2 and #3 of `sulis:add-skill v0.4.0`. Eleven
methodology gaps queued for `add-skill v0.6.0`:

- From check-readability (5): audit-pattern sub-family; Gate 4 P3
  false-positive iteration is the methodology working; marketplace-as-
  fixture pattern; `--raw` mode-selection works cleanly; shared
  PROTOCOL_METHOD_NAMES set worth extracting
- From code-health (4): wrapper-pattern sub-family (third confirmation
  after aggregator + audit); scope auto-detection is third instance of
  same pattern; three uses of "tier" in marketplace is a vocabulary
  smell; stubbed-vs-active rendering deserves MUC-F6
- Plus 2 deferred from inbox dogfood (inventory.py domain-aware mode +
  founder jargon-density check)

### Verification

- check-readability: real-state test against marketplace (145 files);
  surfaced `_wpxlib.py` kitchen-sink finding exactly as predicted by
  the original session conversation; 13 final findings after refinement
- code-health v1 against marketplace: 1 wired tier (tier 5) reports 13
  findings; 6 stubbed tiers render visually distinct from passing tiers;
  --raw JSON mode validates; --tier 5 filter works; tier-gating logic
  in place but no-op (tiers 1+2 unwired)

### Open risks accepted at publication (across both skills)

1. **Overwhelm risk when more tiers wire** (MUC-F4). 13 findings on a
   145-file codebase is fine; 50+ after wave-2 may overwhelm. Revisit
   when second tier wires.
2. **In-session dismissals not persisted.** Founders manually update
   `check-readability-vocabulary.md`. Revisit if same finding re-flags
   across 3+ runs.
3. **PR-scope auto-detection on non-standard base branches.** Mitigation:
   echo detected base in every report; founder verifies.
4. **Single-tier scope masks future single-tier-skill overlap.** When
   check-security or others ship, code-health's broad trigger may steal
   their intent. Stubbed-tier rendering names what's missing.

## v0.4.0 — 2026-05-23

`add-skill` methodology update from sulis:inbox v0.3.0 dogfood findings.
Closes 8 of the 10 methodology gaps surfaced; the remaining 2 (inventory.py
domain-aware mode + audience-conditional jargon check) deferred to v0.5.0.

### Added

- `references/founder-facing-conventions.md` — the canonical conventions
  for any skill / agent / surface in this marketplace whose Audience lock
  is founder-facing or both. Five rules: apply FE-06 to every founder-
  visible string; lead with founder-readable name (ID parenthetical);
  echo-before-act + prompt-before-destroy; translate operator vocabulary
  at output time (not at storage); error messages explain in founder
  terms what happened AND what to do. Includes a sixth-perspective
  "Founder-readability" Gate 4 check + audience-conditional Gate 5
  misuse-case catalogue (MUC-F1..F5).

### Changed

- `skills/add-skill/SKILL.md` Gate 2 — added `Audience` lock item
  (founder-facing / operator-facing / both). Six → seven items locked.
  Audience determines downstream conventions (founder-facing-conventions.md
  application) and Gate 5 misuse-case catalogue extension.
- `skills/add-skill/SKILL.md` Gate 5 — added audience-conditional
  misuse-case catalogue (MUC-F1..F5 for founder-facing or both skills).
  Mandatory: 3+ of MUC-F1..F5 addressed.
- `skills/add-skill/templates/COMPLETENESS_REPORT.md.template` —
  Audience row added to Scope Lock table; structured `revisit_by:` field
  added to Open Risks (date / event / trigger / never).
- `skills/add-skill/references/methodology.md` — new "Patterns to
  recognise" section (Aggregator-pattern + Founder-facing + Operator-
  facing families with shared concerns); new "Misuse cases sometimes
  surface during Gate 4" subsection explicitly allowing emergent misuse-
  case discovery during functional testing.
- `skills/add-skill/references/completeness-perspectives.md` —
  Perspective 3 extended with fixtures pattern (real-state preferred +
  synthetic populated for full coverage); explicit hand-off for emergent
  misuse cases discovered during P3 to Gate 5.
- Categories list extended in SKILL.md Gate 2: existing seven operator
  categories + three founder categories (Founder UX & Navigation,
  Concierge Translation, Founder Aggregator).

### Methodology gaps closed (8 of 10 from sulis:inbox dogfood)

| # | Gap | Resolution |
|---|---|---|
| 1 | Gate 2 missing Audience lock | Added to SKILL.md + template |
| 2 | Categories list operator-biased | Extended with 3 founder categories |
| 5 | Gate 5 needs audience-conditional items | MUC-F1..F5 added |
| 6 | founder-facing-conventions.md missing | Authored |
| 7 | Gate 4 P3 needs fixture guidance | Real-state + synthetic patterns documented |
| 8 | Misuse cases surface during Gate 4 | Methodology now explicitly allows |
| 9 | OPEN_RISK needs revisit-trigger | Structured field in template |
| 10 | Aggregator-pattern recognition | Documented in methodology.md |

### Deferred to v0.5.0 (2 gaps)

| # | Gap | Why deferred |
|---|---|---|
| 3 | inventory.py not domain-aware (aggregators) | Bigger design question — `--skill-type` vs `--data-sources` vs auto-detect; ship correctly, not quickly |
| 4 | Founder jargon-density check in Find | Pairs with #3 (audience-conditional check needs the domain-aware foundation first) |

## v0.3.0 — 2026-05-23

First founder-facing aggregator skill ships. Also the first dogfood run of
the `add-skill` methodology.

### Added

- `skills/inbox/` — the founder's one-screen view of all attention-items.
  - `SKILL.md` — five-step invocation flow (resolve project → run
    aggregator → translate to founder English → present with shortcuts →
    handle shortcut with echo-first + destructive-prompt-required)
  - `scripts/aggregator.py` — deterministic data gatherer over paused
    trains (`.architecture/{project}/train-runs/*.state.json`), BLOCKERs
    (`.architecture/{project}/work-packages/BLOCKER-WP-*.md`), and
    review-needed security findings (`.security/{project}/findings/*.md`)
    where `triage: pending`. Includes `--doctor` source-existence check.
  - `references/sources-of-truth.md` — contract document mapping each
    attention-item category to its on-disk source path; phase translation
    table; doctor allow-list.
  - `COMPLETENESS_REPORT.md` — five-gate audit trail. Verdict: APPROVED
    with three documented OPEN_RISKs.

### Dogfood findings

This was the first production use of `sulis:add-skill` (v0.1.0). Ten
methodology gaps surfaced; all recorded in
`skills/inbox/COMPLETENESS_REPORT.md` under "Methodology feedback". The
gaps will feed into `add-skill` v0.2.0 (next commit). Notable:

1. Gate 2 needs an `Audience` lock item (founder-facing / operator-facing / both)
2. Categories list in `docs/skill-authoring-guide.md` is operator-biased
3. Inventory script not domain-aware for aggregator skills
4. Founder-facing skills need a `founder-facing-conventions.md` reference
5. Adversarial-sweep checklist needs audience-conditional items
6. Misuse cases sometimes surface during Gate 4 (not just Gate 5)
7. OPEN_RISK needs a structured revisit-trigger field
8. Aggregator-pattern skills are a sub-family worth recognising

### Verification

- Doctor + empty-state path tested against real platform repo
  (`/Users/iain/Documents/repos/platform`, project `kinds-and-tools`):
  surfaced 16 real security findings; 0 paused trains; 0 blockers;
  may-be-empty allow-list working correctly.
- Synthetic populated fixture tested all three categories: 1 paused
  train (filter discipline verified — a `success`-phase train was
  correctly excluded), 1 pending finding (filter discipline verified —
  a `triage: accepted` finding was correctly excluded), 1 BLOCKER (with
  WP slug correctly extracted from sibling WP file).

### Open risks accepted at publication

1. Presentation cap not enforced in SKILL.md template (16 items in one
   category overwhelms founder). Revisit when first real founder use
   surfaces >10 in any category.
2. Dismissal write-back not implemented in v1.0 (read-only inbox).
   Will land in v1.1.
3. Trigger accuracy ~80–85% precision; legitimate concept-overlap with
   sulis:status / sulis:next / wpx-findings.

## v0.2.0 — 2026-05-23

Canonical-plugin scope expansion. Sulis is now the front-door for founders;
the marketplace's other plugins remain operator-facing specialists.

### Added

- `agents/concierge.md` — migrated from `sulis-concierge/agents/concierge.md`.
  Internal cross-references updated (`/sulis-concierge:` → `/sulis:`;
  `claude --agent sulis-concierge` → `claude --agent sulis`).
- `skills/start/` — migrated from sulis-concierge.
- `skills/handoff/` — migrated from sulis-concierge.
- `skills/status/` — migrated from sulis-concierge.
- `references/journey-model.md` — migrated from sulis-concierge.
- `references/subagent-dispatch.md` — migrated from sulis-concierge.

### Changed

- Plugin description rewritten — no longer "meta-skills only". Now describes
  the canonical-plugin role: hosts the concierge + journey skills (founder
  surface) AND the meta-skill methodology (skill-author surface).
- Keywords updated: added `canonical`, `founder-facing`, `concierge`,
  `front-door`. Kept `meta-skill`, `skill-authoring`, `methodology`,
  `marketplace`.
- README expanded with the layered marketplace diagram showing sulis as the
  front door above the specialist plugins.

### Removed

- Nothing removed from sulis itself. The sulis-concierge plugin is deprecated
  separately (see its CHANGELOG).

### Migration notes

- Founders previously running `claude --agent sulis-concierge` now run
  `claude --agent sulis`. Same persona, same journey, same JOURNEY.md
  location.
- `/sulis-concierge:start`, `/sulis-concierge:handoff`, `/sulis-concierge:status`
  → `/sulis:start`, `/sulis:handoff`, `/sulis:status`. Same behaviour.
- Other plugins that reference `sulis-concierge` as a peer (srd, sea,
  sulis-execution) updated separately to point at `sulis`.

### Rationale

Sib's original feedback was that the marketplace's core plugins should
collapse into one front door — the founder shouldn't have to know there are
many plugins. Rather than literally merge every plugin, the cleaner fix is
to make `sulis` the canonical front-door plugin and keep the others as
operator-facing internals. The concierge agent + journey skills were
already the founder-facing surface; moving them into `sulis` makes the
brand-name match the surface.

## v0.1.0 — 2026-05-23

Initial release. Establishes the meta-plugin home for skill-authoring methodology.

### Added

- `add-skill` skill — five-gate authoring methodology (Find → Scope Lock → Generate → Evaluate → Adversarial Review)
  - `SKILL.md` — entrypoint with the five gates
  - `references/methodology.md` — detailed rationale for each gate
  - `references/kinds-and-tools-learnings.md` — the source learnings transplanted from `/Users/iain/Documents/repos/platform/.specifications/kinds-and-tools/`
  - `references/completeness-perspectives.md` — how to evaluate each gate
  - `scripts/inventory.py` — deterministic Find phase: scans marketplace for jargon collisions, existing references, prior-art gotchas
  - `templates/SKILL.md.template` — starter for new SKILL.md files
  - `templates/VOCABULARY.md.template` — vocabulary section pattern
  - `templates/COMPLETENESS_REPORT.md.template` — per-gate completion report

### Rationale

The marketplace previously had `docs/skill-authoring-guide.md` (97 lines —
categories, gotchas, progressive disclosure) as a beginner's how-to. It
described tactics but not methodology. New skills drifted in quality.

This plugin codifies the methodology: a five-gate flow that front-loads
discovery (collisions, jargon, prior art), locks scope before writing,
gates publish on completeness + adversarial review. Grounded in the
patterns the kinds-and-tools spec validated for getting consistent
outcomes from agent-driven authoring.
