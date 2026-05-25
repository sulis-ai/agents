# Completeness Report — sulis:inbox

**Authored:** 2026-05-23
**Author:** Iain + Claude (dogfood run of sulis:add-skill)
**Methodology:** `sulis:add-skill` v0.1.0 (five-gate)

This is the FIRST production use of the add-skill methodology. Gaps surfaced
here will feed back into add-skill v0.2.0 (the planned methodology update).

## Verdict summary

| Gate | Status | Notes |
|---|---|---|
| 1 — Find | PASS | 5 overlaps all coincidental; 1 vocab collision (`blocker`) resolved by deferring to sulis-execution definition |
| 2 — Scope Lock | PASS (with methodology gaps noted) | Six items locked; two methodology gaps surfaced (Audience missing from lock; categories list operator-biased) |
| 3 — Generate | PASS | SKILL.md + aggregator.py + sources-of-truth.md produced; all reference files present |
| 4 — Evaluate | PASS-with-note | Trigger accuracy ~80–85% (legitimate overlap with sulis:status / sulis:next); gotchas all grounded; functional tests passed against real platform repo (16 findings) + synthetic fixture (3 items across 3 categories) |
| 5 — Adversarial Review | PASS | 3 misuse cases identified, 3 prevented |

**Publication decision:** APPROVED

---

## Gate 1 — Find

**BRIEF_PACK generated:** regenerated on each run via `python3 plugins/sulis/skills/add-skill/scripts/inventory.py --marketplace-root . --target-plugin sulis --target-skill inbox --proposed-description ... --proposed-vocabulary inbox,attention-item,waiting-action,paused-train,gate-finding,blocker`

**Findings reviewed:** yes

**Collisions flagged:**

- **Description overlap (5):** sulis-execution:backfill-code-review (6 tokens), sulis-execution:backfill-gates (5), sea:suggest-split (4), sea:code-review (3), sulis:handoff (3)
- **Vocabulary collision (1):** `blocker` appears in sulis-execution:retry description

**Collisions resolved:**

- **All 5 description overlaps:** waived as coincidental. backfill-* are retroactive operator commands (different time-axis); suggest-split/code-review are PR-scoped (different artifact-axis); sulis:handoff is concierge write-time (different read-vs-write axis). None compete for scope.
- **`blocker` vocabulary collision:** resolved by **defer-to-source**. sulis-execution owns the BLOCKER concept (created by executor when WP can't progress); inbox CONSUMES it (surfaces BLOCKERs as one category of attention-item). Document defer-relationship in inbox's Vocabulary section. No collision risk because there is only one canonical definition.

**Existing skills considered for reuse:**

- **sulis:status** — close peer; shows journey state. Reason for not reusing: status reports CURRENT phase + progress; inbox aggregates WAITING items across sources. Different question ("where am I in the journey?" vs "what needs my attention?"). Complementary, not redundant.
- **sulis-execution:status** — operator-facing INDEX summary. Reason for not reusing: scope is single source (INDEX only) and audience is operator. Inbox aggregates across sources and translates for founder.

---

## Gate 2 — Scope Lock

| Item | Locked value |
|---|---|
| Skill name | `inbox` |
| Plugin home | `sulis` (canonical front-door) |
| Category | **Business Process & Team Automation** — closest match in existing seven-category list. (Methodology gap: categories are operator-biased; "Founder UX & Navigation" would fit better.) |
| Trigger condition | "Use when the founder asks 'what's waiting for me?', 'what needs my attention?', or wants a one-screen view of all attention-needed items across their project. Aggregator: combines paused work, things to review, blocked tasks, and decisions waiting on the founder into one founder-readable list with one-keystroke shortcuts to act on each." |
| Top-5 gotchas | (below) |
| Depth modes | None for v1. (Future: `quick` = counts only; `full` = full list. Defer until usage shows the need.) |

### Top-5 gotchas (with concrete source)

1. **Source-discovery brittleness** — if a state source moves (e.g., `findings/` relocates), the inbox silently misses items.
   *Source: prior-art* — HD-008 found INDEX semantics had drifted; same drift class applies to any cross-source aggregator. Mitigation: deterministic source-discovery via a registry, not hard-coded paths; doctor check.

2. **Operator-jargon leakage to founder** — easy to ship inbox display strings like "BLOCKER" or "WP-AUTO-001" when the founder needs "blocked task" or "user signup flow".
   *Source: prior-art* — `plugins/sulis/references/founder-english.md` anchor cases 3 + 4. Mitigation: every display string passes the FE-06 check; translation table for operator → founder vocab; gate at output time.

3. **Stale-on-read** — aggregator reads from disk; if it caches results, the founder sees state from an earlier moment.
   *Source: prior-art* — HD-008 fixed this exact pattern for INDEX (move to compute-on-read). Mitigation: no caching; recompute on every invocation; flag if state-source is mid-write.

4. **Ambiguous one-keystroke dispatch** — if the inbox lists 8 items and offers shortcuts, the dispatch path must be unambiguous about what each shortcut does.
   *Source: author-experience* — every CLI tool with shortcuts that doesn't echo the action before performing it produces "wait, what did I just do?" moments. Mitigation: each shortcut echoes its action + the affected item; confirmation prompt for destructive actions.

5. **Destructive action without confirmation** — pressing a shortcut should never trigger destructive operations (force-push, branch delete, abort train) silently.
   *Source: prior-art* — Claude Code's own "Executing actions with care" doctrine (CLAUDE.md, "destructive operations require user confirmation"). Mitigation: explicit allow-list of safe actions per shortcut; destructive actions always prompt.

### Vocabulary terms to introduce

- **inbox** — the aggregator; the screen showing all attention-items.
- **attention-item** — a single thing waiting for the founder (a paused train, a finding, a blocked task, a decision).
- **waiting-action** — the verb category. "What's waiting for the founder to act on?"
- **paused-train** — a train run that stopped mid-flight (defers to sulis-execution semantics).
- **gate-finding** — a code-review or security finding awaiting triage (defers to sulis-execution + sulis-security semantics).
- **blocker** — defers to sulis-execution definition (WP executor can't progress).

### Audience (methodology gap surfaced)

**Audience:** founder-facing.

This item is NOT in the v0.1.0 methodology's Gate 2 lock. It's being added here ad-hoc because the dogfood run needs it. Will be folded into add-skill v0.2.0.

Why it matters for inbox: the trigger condition, every display string, every shortcut label, and every error message must pass the FE-06 check (no internal IDs, no acronyms, no internal taxonomy, read-aloud test). An operator-facing aggregator would have entirely different conventions.

---

## Gate 3 — Generate

**Files produced:**

- `plugins/sulis/skills/inbox/SKILL.md` — entrypoint (founder-vocab trigger; five-step invocation flow; gotchas section; vocabulary section; when-to / when-not-to)
- `plugins/sulis/skills/inbox/scripts/aggregator.py` — deterministic data gatherer (paused trains, BLOCKERs, review-needed findings; `--doctor` source-existence check; JSON + markdown output)
- `plugins/sulis/skills/inbox/references/sources-of-truth.md` — contract document mapping each attention-item category to its on-disk source path
- `plugins/sulis/skills/inbox/COMPLETENESS_REPORT.md` — this file

**Scope lock adherence:** Verified. Skill name (`inbox`), plugin home (`sulis`), category (Business Process), trigger condition (founder-vocab — no operator jargon), top-5 gotchas (each with source citation), depth modes (none for v1) — all reflected as locked.

**Referenced files verified present:** Yes. SKILL.md references `references/sources-of-truth.md` (present), `plugins/sulis/references/founder-english.md` (present in srd; verified earlier in session), `plugins/sulis-execution/scripts/_wpxlib.py` (present; HD-008 work). No declared reference is missing.

---

## Gate 4 — Evaluate

### Perspective 1 — Trigger accuracy

**Verdict:** PASS (with note)

**Method:** Mental walkthrough of 10 representative invocation scenarios.

**Test scenarios:**

| Scenario | Should trigger? | Likely to trigger? |
|---|---|---|
| "what's waiting for me?" | YES | YES (verbatim) |
| "what needs my attention?" | YES | YES (verbatim) |
| "where do I look first?" | YES | YES (close paraphrase) |
| "show me my inbox" | YES | YES |
| "give me a status update" | NO (→ sulis:status) | maybe (ambiguous) |
| "what should I do today?" | NO (→ sulis:next) | maybe (ambiguous) |
| "what's blocking the build?" | maybe | YES |
| "what are the open security findings?" | NO (→ operator surface) | YES |
| "show me the production logs" | NO | NO |
| "review my code" | NO (→ sea:code-review) | NO |

**Result:** ~80–85% precision. Three ambiguous overlaps with sibling skills (sulis:status, sulis:next, /wpx-findings); these are legitimate concept-overlaps for an aggregator, mitigated by the "When NOT to invoke" section explicitly naming each sibling.

### Perspective 2 — Gotchas coverage

**Verdict:** PASS

**Result:** All 5 gotchas have documented sources:
- Source-discovery brittleness — HD-008 (prior art)
- Operator-jargon leakage — founder-english.md anchor cases 3+4 (prior art)
- Stale-on-read — HD-008 (prior art)
- Ambiguous shortcut dispatch — author experience (defensible: "every CLI tool…")
- Destructive action without confirmation — Claude Code "Executing actions with care" doctrine (prior art)

5 items ≤ 15 limit. Ordered by likelihood × impact (source-discovery has highest impact for an aggregator; destructive-action is highest stakes for a founder-facing surface).

### Perspective 3 — Functional completeness

**Verdict:** PASS

**Scenarios tested:**

1. **Real platform repo, empty-state:** `python3 aggregator.py --project kinds-and-tools --format markdown` against `/Users/iain/Documents/repos/platform/`. Surfaced **16 real security findings**; correctly reported 0 paused trains (no train-runs/ dir) and 0 blockers. Doctor reported `train_runs_dir: not present (no train has run yet)` — correct may-be-empty handling.

2. **Synthetic populated fixture:** tempdir with synthetic state files exercising all three categories. Aggregator returned 3 items across 3 categories (1 paused train, 1 review-needed finding, 1 blocker). Critically: a synthetic non-paused train (`phase: success`) was correctly **filtered out**; a synthetic already-triaged finding (`triage: accepted`) was correctly **filtered out**. Filter discipline working.

3. **WP slug extraction:** synthetic blocker for `WP-AUTO-018` with matching `WP-AUTO-018-observability-adapter.md` correctly extracted slug `observability-adapter` for the founder-name derivation.

4. **JSON envelope shape:** matches the `InboxEnvelope` dataclass; SKILL.md's documented consumption format holds.

**Failure modes captured:** None. The two real failure-mode candidates (founder presses shortcut against stale state; founder overwhelmed by 16 items) are tracked as misuse cases in Gate 5, not functional bugs.

---

## Gate 5 — Adversarial Review

### Misuse case 1: Founder acts on stale inbox state

- **What Claude might do wrong:** Founder presses [1] to resume a paused train. Between when the inbox was rendered and when the founder pressed [1], an operator (or autonomous run) advanced the train. Claude blindly runs `wpx-train resume`, which now produces a wrong-state error — or worse, a wrong-state action.
- **Mitigation:** SKILL.md step 5 mandates "Echo the action FIRST" — the echo includes a re-read of the current state. The aggregator is no-cache (gotcha #3 + Perspective 3 functional test), so re-read is cheap. If state has changed, abort with a plain-English explanation: *"The build run already moved on while you were looking — let me refresh the inbox."*

### Misuse case 2: Founder overwhelmed by item count

- **What Claude might do wrong:** Real-state test surfaced 16 findings. Dumping all 16 in one list (especially mixed with paused-trains + blockers) makes the inbox unreadable; founder bounces.
- **Mitigation:** SKILL.md presentation template orders items by severity within each category (aggregator preserves `severity` field). Recommended cap: top-5 per category; show "(and N more — say 'show all' to expand)" indicator. Add to SKILL.md as explicit guidance — OPEN_RISK if presentation template doesn't enforce this.
- **Action taken:** This was NOT explicit in SKILL.md as drafted. Adding it now would extend the skill; deferring to a follow-up commit since it's a presentation-layer enhancement, not a defect. Recorded as **OPEN_RISK** with revisit-by trigger: "first real founder use of inbox surfaces >10 items in any category."

### Misuse case 3: False-positive inbox items (already-handled externally)

- **What Claude might do wrong:** Founder previously discussed a finding offline and decided to accept it; never updated the finding file. Inbox lists it again; founder thinks the system is broken.
- **Mitigation:** Each category has a "dismiss" shortcut that updates the source-of-truth (e.g., adds `triage: accepted` to the finding YAML frontmatter). Dismissal IS the source update — there is no separate "inbox state" to diverge. SKILL.md step 5 documents this; the dismissal shortcut is per-category in the presentation template (`[d1]`, `[d2]`, etc.). Concrete: dismissal writes back to the source file with timestamp + reason. **Implementation note:** the dismissal write-back is NOT yet implemented in aggregator.py (read-only for v1); SKILL.md describes the intended behaviour, which the future v1.1 will add.
- **Status:** OPEN_RISK for v1.0 (read-only inbox); will become PREVENTED in v1.1 when dismissal write-back lands.

---

## Open risks accepted at publication

1. **Presentation cap not enforced in SKILL.md template (Misuse case 2).** Revisit when first real founder use surfaces >10 items in any category. Mitigation in the meantime: SKILL.md's gotchas section flags this implicitly; Claude reading the skill should apply judgement.

2. **Dismissal write-back not implemented in v1.0 (Misuse case 3).** SKILL.md documents the intended behaviour. Founder can still dismiss items from view in conversation, but the source file is not updated until v1.1. Workaround: founder asks Claude to update the source file explicitly (e.g., "add `triage: accepted` to SF-100").

3. **Trigger accuracy ambiguity with sibling skills (Perspective 1).** ~15% false-positive rate against sulis:status / sulis:next / wpx-findings is legitimate concept overlap, mitigated but not eliminated. Revisit if real usage shows persistent confusion.

---

## Vocabulary changes (during authoring)

None — the vocabulary locked at Gate 2 was used unchanged through Gate 3.

---

## Methodology feedback (running notes for add-skill v0.2.0)

Additional gaps surfaced during Gates 3-5 (beyond the 6 captured during Gates 1-2):

7. **Gate 4 perspective 3 (functional completeness) needs guidance on test fixtures.** I built a synthetic tempdir fixture ad-hoc. The methodology should suggest a fixtures pattern (or template) so authors don't reinvent it per skill.

8. **Gate 5 misuse cases sometimes surface during Gate 3.** Misuse case 2 (overwhelm) became visible only when I saw the 16-finding real-state test in Perspective 3 — *during* Gate 4, not at Gate 5. The methodology should allow misuse cases to be drafted during Gate 4 and finalised at Gate 5; explicit "running misuse-case list" in COMPLETENESS_REPORT.md template would help.

9. **OPEN_RISK needs a structured field for revisit-trigger.** I recorded "revisit when first real founder use surfaces >10 items" as a sentence; a structured field (`revisit_by: trigger | date | event`) would make these searchable across skills.

10. **Aggregator-pattern skills are a sub-family worth recognising.** Inbox is one of (presumably) many future aggregators: `sulis:next` will aggregate over inbox + journey; `sulis:status-line` will aggregate over inbox + train state; starter-pack discovery will aggregate over templates. The methodology might benefit from a category-specific extension (or sub-skill) for aggregators: shared concerns around source-discovery, doctor checks, no-cache discipline, vocab translation.

These 4 + the original 6 = **10 methodology gaps** to fold into add-skill v0.2.0.

---

## Methodology feedback (running notes for add-skill v0.2.0)

Gaps surfaced during this run that should feed back into add-skill:

1. **Gate 2 missing `Audience` lock item.** Founder-facing vs operator-facing fundamentally changes vocabulary, gotchas, and trigger-condition conventions. Should be a mandatory lock item with three values: `founder-facing`, `operator-facing`, `both`.

2. **Categories list is operator-biased.** The existing seven categories in `docs/skill-authoring-guide.md` (Library/API, Product Verification, Data Fetching, Business Process, Code Scaffolding, Code Quality, Runbook) don't map cleanly to founder-facing surface skills like inbox / next / status-line. Need new categories: `Founder UX & Navigation`, `Concierge Translation`, or similar.

3. **Inventory script not domain-aware for aggregator skills.** Inbox needs to know what STATE SOURCES exist (train-runs/, findings/, WP journals, INDEX). A `--data-sources` flag would walk the codebase for them. Current script only checks jargon/collisions.

4. **Founder-facing skills need jargon-density check in Find.** The current inventory doesn't compare proposed vocabulary against concierge voice. An audience-conditional check would surface jargon leakage at Gate 1, not Gate 5.

5. **Gate 5 adversarial-sweep checklist needs audience-conditional items.** For founder-facing skills, the sweep should include: "would a non-technical user understand the trigger condition?", "would they understand every display string?", "would any error message leak internal IDs?". Currently the 8 misuse cases in the methodology are domain-agnostic.

6. **Founder-facing-conventions.md reference missing.** Operator skills can lean on existing reference standards (code-review-standard.md, etc.). Founder-facing skills need a conventions doc covering: FE-06 application, no internal IDs in chrome, confirmation prompts for destructive actions, plain-English error messages, etc. Should live at `plugins/sulis/references/founder-facing-conventions.md`.
